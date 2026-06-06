import os
import json
import uuid
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
    if messages:
        # Pass messages history to rewrite query
        simplified_history = []
        for msg in messages:
            simplified_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        rewritten_query = await search_bot.rewrite_query(request.query, simplified_history, groq_api_key)
        
    # 4. Perform Search (Crawl target content)
    print(f"Searching custom crawler for query: '{rewritten_query}'")
    crawl_results = await provider.search(rewritten_query)
    search_results = crawl_results.get("sources", [])
    context_text = crawl_results.get("context", "")
    
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
        model=groq_model
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
        "sources": search_results
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
