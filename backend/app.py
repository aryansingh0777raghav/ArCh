import os
import re
import json
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Import custom search crawler and searchbot
from backend.providers.custom_crawler import CustomCrawlerProvider
from backend.searchbot import SearchBot
from backend.tts_engine import synthesize_speech
from backend.stt_engine import transcribe_microphone
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from starlette.concurrency import run_in_threadpool

# Load environment variables
load_dotenv()

app = FastAPI(title="ArCh Search Engine API", version="1.0.0")

# Enable CORS for Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(STORAGE_DIR, "history.json")
BOOKMARKS_FILE = os.path.join(STORAGE_DIR, "bookmarks.json")
SETTINGS_FILE = os.path.join(STORAGE_DIR, "settings.json")

# Initialize SearchBot
search_bot = SearchBot()

# Initialize Search Providers (Only custom crawler is used)
PROVIDERS = {
    "custom_crawler": CustomCrawlerProvider()
}

# Helper functions to read/write JSON files safely
def read_json_file(file_path: str, default_val: Any) -> Any:
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_val, f, indent=2)
        return default_val
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return default_val

def write_json_file(file_path: str, data: Any):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

# Settings loading logic (Simplified)
def get_effective_settings() -> dict:
    default_settings = {
        "groq_api_key": "",
        "theme": "dark",
        "groq_model": "llama-3.3-70b-versatile",
        "voice_lang": "en"
    }
    
    saved_settings = read_json_file(SETTINGS_FILE, default_settings)
    
    # Merge with environment variables if saved settings are empty
    merged = {}
    for key, val in default_settings.items():
        merged_val = saved_settings.get(key, "")
        if not merged_val:
            env_key = key.upper()
            merged_val = os.environ.get(env_key, "")
        merged[key] = merged_val
        
    return merged

# Models
class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    theme: Optional[str] = None
    groq_model: Optional[str] = None
    voice_lang: Optional[str] = None

class TTSRequest(BaseModel):
    text: str

class SearchRequest(BaseModel):
    query: str
    history_id: Optional[str] = None
    deep_research: bool = False
    local_dir: Optional[str] = None
    storyboard_mode: bool = False

# Endpoints

@app.get("/api/status")
async def get_status():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/settings")
async def get_settings():
    return get_effective_settings()

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    current = read_json_file(SETTINGS_FILE, get_effective_settings())
    
    # Update fields
    for field, value in settings.model_dump(exclude_unset=True).items():
        current[field] = value
        # Sync to environment variables in memory as well
        os.environ[field.upper()] = value or ""
        
    write_json_file(SETTINGS_FILE, current)
    return current

@app.get("/api/history")
async def get_history():
    history = read_json_file(HISTORY_FILE, [])
    # Return newest first
    return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)

@app.post("/api/history/delete")
async def delete_history_item(payload: dict = Body(...)):
    item_id = payload.get("id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Missing history item id")
        
    history = read_json_file(HISTORY_FILE, [])
    filtered_history = [item for item in history if item.get("id") != item_id]
    write_json_file(HISTORY_FILE, filtered_history)
    return {"status": "success"}

@app.post("/api/history/clear")
async def clear_history():
    write_json_file(HISTORY_FILE, [])
    return {"status": "success"}

@app.get("/api/bookmarks")
async def get_bookmarks():
    bookmarks = read_json_file(BOOKMARKS_FILE, [])
    return bookmarks

@app.post("/api/bookmarks/add")
async def add_bookmark(payload: dict = Body(...)):
    history_id = payload.get("history_id")
    if not history_id:
        raise HTTPException(status_code=400, detail="Missing history_id to bookmark")
        
    # Find history item
    history = read_json_file(HISTORY_FILE, [])
    history_item = next((item for item in history if item.get("id") == history_id), None)
    
    if not history_item:
        raise HTTPException(status_code=404, detail="History thread not found")
        
    bookmarks = read_json_file(BOOKMARKS_FILE, [])
    
    # Check if already bookmarked
    if any(b.get("history_id") == history_id for b in bookmarks):
        return {"status": "already_exists"}
        
    bookmark = {
        "id": str(uuid.uuid4()),
        "history_id": history_id,
        "title": history_item.get("title", "Saved Search"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    bookmarks.append(bookmark)
    write_json_file(BOOKMARKS_FILE, bookmarks)
    return {"status": "success", "bookmark": bookmark}

@app.post("/api/bookmarks/remove")
async def remove_bookmark(payload: dict = Body(...)):
    history_id = payload.get("history_id")
    if not history_id:
        raise HTTPException(status_code=400, detail="Missing history_id")
        
    bookmarks = read_json_file(BOOKMARKS_FILE, [])
    filtered_bookmarks = [b for b in bookmarks if b.get("history_id") != history_id]
    write_json_file(BOOKMARKS_FILE, filtered_bookmarks)
    return {"status": "success"}

def scan_and_rank_local_files(query: str, local_dir: str) -> tuple:
    """
    Scans local directory recursively (ignoring common build/meta dirs),
    chunks readable files (including PDFs via PyPDF2),
    scores them against the query, and returns (context_str, sources_list).
    """
    if not os.path.exists(local_dir) or not os.path.isdir(local_dir):
        return "", []
        
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "of", "about", "my", "your", "our", "their", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did"}
    
    keywords = [w.strip(".,;:?!'\"()[]{}").lower() for w in query.split()]
    keywords = [w for w in keywords if len(w) >= 2 and w not in stop_words]
    
    if not keywords:
        keywords = [w.lower() for w in query.split() if w]
        
    ignored_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "env", "dist", "build", "storage", "cache"}
    allowed_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".fountain", ".sh", ".bat", ".cpp", ".h", ".cs", ".java", ".pdf"}
    
    chunks = []
    fallback_chunks = []
    base_depth = local_dir.rstrip(os.sep).count(os.sep)
    
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        
        current_depth = root.count(os.sep) - base_depth
        if current_depth > 4:
            dirs[:] = []
            continue
            
        for file in files:
            name, ext = os.path.splitext(file)
            ext = ext.lower()
            if ext not in allowed_exts:
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, local_dir)
            file_text = ""
            
            try:
                if ext == ".pdf":
                    import PyPDF2
                    with open(file_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        text_list = []
                        for page_num in range(min(len(reader.pages), 25)):
                            p_text = reader.pages[page_num].extract_text()
                            if p_text:
                                text_list.append(p_text)
                        file_text = "\n".join(text_list)
                else:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_text = f.read()
            except Exception as e:
                print(f"RAG: Error reading file {file_path}: {e}")
                continue
                
            if not file_text or not file_text.strip():
                continue
                
            chunk_size = 800
            overlap = 100
            start = 0
            while start < len(file_text):
                end = start + chunk_size
                chunk_body = file_text[start:end]
                
                score = 0
                chunk_lower = chunk_body.lower()
                
                for kw in keywords:
                    count = chunk_lower.count(kw)
                    score += count * 2
                    
                    if kw in rel_path.lower():
                        score += 5
                        
                if score > 0:
                    chunks.append({
                        "file_path": file_path,
                        "rel_path": rel_path,
                        "snippet": chunk_body.strip(),
                        "score": score
                    })
                else:
                    fallback_chunks.append({
                        "file_path": file_path,
                        "rel_path": rel_path,
                        "snippet": chunk_body.strip(),
                        "score": 0.001
                    })
                    
                start += chunk_size - overlap
                
    if not chunks:
        chunks = fallback_chunks
        
    chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = chunks[:8]
    
    if not top_chunks:
        return "", []
        
    context_list = []
    sources_list = []
    
    for idx, c in enumerate(top_chunks):
        context_list.append(f"Local Source [{idx+1}] File: {c['rel_path']}\nContent:\n{c['snippet']}\n---")
        snippet_summary = c['snippet'][:150].replace('\n', ' ') + "..."
        file_url = "file:///" + c['file_path'].replace('\\', '/')
        sources_list.append({
            "title": f"[Local File] {c['rel_path']}",
            "url": file_url,
            "snippet": snippet_summary
        })
        
    local_context = "\n\n".join(context_list)
    return local_context, sources_list

@app.post("/api/search")
async def perform_search(request: SearchRequest):
    settings = get_effective_settings()
    
    # Use Custom Crawler
    provider = PROVIDERS["custom_crawler"]
    groq_api_key = settings.get("groq_api_key", "")
    groq_model = settings.get("groq_model", "llama-3.3-70b-versatile")
    
    # 2. Manage conversational history
    history = read_json_file(HISTORY_FILE, [])
    history_item = None
    messages = []
    history_id = request.history_id
    
    if history_id:
        history_item = next((item for item in history if item.get("id") == history_id), None)
        
    if history_item:
        messages = history_item.get("messages", [])
    else:
        # Create a new history thread
        history_id = str(uuid.uuid4())
        history_item = {
            "id": history_id,
            "title": request.query,
            "provider": "custom_crawler",
            "timestamp": datetime.utcnow().isoformat(),
            "messages": []
        }
        history.append(history_item)
        
    # 3. Rewrite query for conversational search
    rewritten_query = request.query
    
    # Intercept "about me" / "mere baare me" / creator queries to fetch full info of Aryan Singh
    lower_q = request.query.lower().strip()
    about_me_phrases = [
        "mere baare me", "mere bare me", "mere baare mein", "mere bare mein", "mere baare m", "mere bare m",
        "who am i", "know about me", "tell me about myself", "find about me", "search about me", "find out about me",
        "mere baare me pta lgao", "mere bare me pata lagao", "mere bare me pata karo", "mere baare me pta karo",
        "mere baare me search karo", "mere bare me search karo",
        "tell me about yourself", "who are you", "what is your name", "introduce yourself", "about yourself",
        "describe yourself", "who are u", "tell me about u",
        "who created you", "who created u", "who made you", "who made u", "who is your creator", "who is your developer",
        "who created arch", "who made arch", "who is the creator of arch", "who is the developer of arch",
        "arch ko kisne banaya", "arch kisne banaya", "apko kisne banaya", "tumhe kisne banaya"
    ]
    
    is_about_me = any(phrase in lower_q for phrase in about_me_phrases)
    if is_about_me:
        rewritten_query = "Aryan Singh developer filmmaker Gorakhpur"
        request.deep_research = True  # Force deep research to get full internet search results
    elif messages:
        # Pass messages history to rewrite query
        simplified_history = []
        for msg in messages:
            simplified_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        rewritten_query = await search_bot.rewrite_query(request.query, simplified_history, groq_api_key)
        
    # 4. Perform Search (Crawl target content)
    context_text = ""
    search_results = []
    crawl_images = []
    
    if request.deep_research:
        print(f"Deep Research Mode active. Splitting query: '{rewritten_query}'")
        sub_queries = await search_bot.generate_sub_queries(rewritten_query, groq_api_key)
        print(f"Sub-queries generated: {sub_queries}")
        
        all_queries = [rewritten_query] + sub_queries
        tasks = [provider.search(q) for q in all_queries]
        results = await asyncio.gather(*tasks)
        
        seen_urls = set()
        seen_images = set()
        context_blocks = []
        
        for idx, res in enumerate(results):
            for src in res.get("sources", []):
                if src["url"] not in seen_urls:
                    seen_urls.add(src["url"])
                    search_results.append(src)
            q_context = res.get("context", "")
            if q_context:
                context_blocks.append(f"--- Sub-Research Context for query '{all_queries[idx]}': ---\n{q_context}")
            for img in res.get("images", []):
                if img not in seen_images:
                    seen_images.add(img)
                    crawl_images.append(img)
                    
        context_text = "\n\n".join(context_blocks)
    else:
        print(f"Searching custom crawler for query: '{rewritten_query}'")
        crawl_results = await provider.search(rewritten_query)
        search_results = crawl_results.get("sources", [])
        context_text = crawl_results.get("context", "")
        crawl_images = crawl_results.get("images", [])

    # 4.5 Handle Local Directory RAG
    if request.local_dir and os.path.exists(request.local_dir):
        print(f"Local Hybrid Search active on path: {request.local_dir}")
        local_context, local_sources = scan_and_rank_local_files(rewritten_query, request.local_dir)
        if local_context:
            context_text = f"--- LOCAL ENVIRONMENT FILES CONTEXT (ATTACHED DIRECTORY) ---\n{local_context}\n\n" + context_text
            search_results = local_sources + search_results
            print(f"RAG: Added {len(local_sources)} local files to context and search sources.")

    # 5. Generate AI Answer using Groq
    simplified_history = []
    for msg in messages:
        simplified_history.append({
            "role": msg["role"],
            "content": msg["content"]
        })
        
    ai_response = await search_bot.generate_ai_answer(
        query=request.query,
        context=context_text,
        sources=search_results,
        history=simplified_history,
        api_key=groq_api_key,
        model=groq_model,
        storyboard_mode=request.storyboard_mode
    )
    
    # 6. Update History Messages
    new_user_message = {
        "role": "user",
        "content": request.query
    }
    
    new_assistant_message = {
        "role": "assistant",
        "content": json.dumps({
            "answer": ai_response.get("answer", ""),
            "key_facts": ai_response.get("key_facts", []),
            "follow_ups": ai_response.get("follow_ups", [])
        }),
        "sources": search_results,
        "images": crawl_images,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    messages.append(new_user_message)
    messages.append(new_assistant_message)
    
    # Update the thread in memory
    history_item["messages"] = messages
    history_item["timestamp"] = datetime.utcnow().isoformat()
    
    # Save history to file
    write_json_file(HISTORY_FILE, history)
    
    # 7. Formulate Response
    return {
        "history_id": history_id,
        "title": history_item["title"],
        "query": request.query,
        "rewritten_query": rewritten_query,
        "ai_answer": ai_response.get("answer", ""),
        "key_facts": ai_response.get("key_facts", []),
        "follow_ups": ai_response.get("follow_ups", []),
        "sources": search_results,
        "images": crawl_images
    }

@app.get("/api/stt")
async def get_stt(lang: Optional[str] = "en"):
    text = await run_in_threadpool(transcribe_microphone, lang)
    return {"text": text}

@app.post("/api/tts")
async def get_tts(request: TTSRequest):
    text = request.text
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")
        
    audio_path = await run_in_threadpool(synthesize_speech, text)
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=500, detail="Speech synthesis failed")
        
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        os.remove(audio_path)
        print(f"Cleaned up temp TTS file: {audio_path}")
    except Exception as e:
        print(f"Error reading/deleting temp TTS file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read generated audio")
        
    return Response(content=audio_bytes, media_type="audio/wav")

@app.on_event("startup")
async def startup_event():
    print("[Startup] Pre-warming STT and TTS models in background...")
    try:
        from backend.stt_engine import get_vosk_model
        from backend.tts_engine import get_piper_voice
        
        async def warm_models():
            try:
                print("[Startup] Loading STT (EN)...")
                await run_in_threadpool(get_vosk_model, "en")
                print("[Startup] Loading TTS (EN)...")
                await run_in_threadpool(get_piper_voice, "en")
                print("[Startup] English voice models pre-warmed successfully.")
            except Exception as e:
                print(f"[Startup] Error loading English voice models: {e}")
                
            try:
                print("[Startup] Loading STT (HI)...")
                await run_in_threadpool(get_vosk_model, "hi")
                print("[Startup] Loading TTS (HI)...")
                await run_in_threadpool(get_piper_voice, "hi")
                print("[Startup] Hindi voice models pre-warmed successfully.")
            except Exception as e:
                print(f"[Startup] Error loading Hindi voice models: {e}")

        import asyncio
        asyncio.create_task(warm_models())
    except Exception as e:
        print(f"[Startup] Setup pre-warming task failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
