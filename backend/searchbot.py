import os
import json
import re
from groq import AsyncGroq

REWRITE_SYSTEM_PROMPT = """
You are an AI assistant for a search engine. Your task is to rewrite the user's latest follow-up question into a standalone, self-contained search query, using the conversation history for context.
Do NOT answer the question. Only output the standalone search query.

Note: If the user refers to 'me', 'my', or 'myself' (e.g., 'tell me about myself', 'explain my films', 'who am I'), they refer to the creator, Aryan Singh. You MUST rewrite the query to search for 'Aryan Singh' followed by the requested topic.

Examples:
History:
User: Who is Atif Aslam?
Assistant: Atif Aslam is a Pakistani singer...
User: When was he born?
Output: Atif Aslam birth date

History:
User: What is FastAPI?
Assistant: FastAPI is a modern web framework...
User: Give me a code example
Output: FastAPI code example python

History:
User: Tell me about myself
Assistant: You are Aryan Singh, a developer and filmmaker...
User: What are my projects?
Output: Aryan Singh developer projects portfolio

Return ONLY the standalone query, without any explanations, formatting, or quotation marks.
"""

ANSWER_SYSTEM_PROMPT = """
You are ArCh, an advanced AI search engine assistant created by developer Aryan Singh.
Your goal is to provide a precise, rich, and detailed answer to the user's query using the search results provided below.

Rules:
1. Cite facts using [1], [2], etc., corresponding to the indices of the search results.
2. Put the citation numbers immediately after the sentence or phrase they support, e.g., "Atif Aslam was born in Wazirabad [1] and started his career in 2003 [2]."
3. Format the answer beautifully in Markdown. Use headers, bullet points, bold text, lists, and tables where appropriate to make it visually premium.
4. If the search results do not contain enough information to answer the question, state it, but do your best with the available context.
5. You MUST return a JSON object. Do not wrap it in markdown code blocks. The JSON must have the following structure:
{
  "answer": "Markdown answer here...",
  "key_facts": ["Fact 1", "Fact 2", "Fact 3"],
  "follow_ups": ["Follow up query 1", "Follow up query 2", "Follow up query 3"]
}
6. If the context contains a section labeled `LOCAL ENVIRONMENT FILES CONTEXT (ATTACHED DIRECTORY)`, and the user asks about "local file", "code", or specific filenames, you MUST prioritize reading, describing, and explaining the local files from that section. Do not get distracted by general web search results (such as Local File Inclusion vulnerabilities) unless the query explicitly asks about them. Focus on the actual code, structure, and text of the attached files.
"""

class SearchBot:
    def __init__(self):
        # We will instantiate the client dynamically per-request using the key passed
        pass

    async def generate_sub_queries(self, query: str, api_key: str) -> list:
        """
        Splits the search query into 3 distinct self-contained sub-queries using Groq.
        """
        if not api_key:
            return [query]
            
        try:
            client = AsyncGroq(api_key=api_key)
            system_prompt = (
                "You are an AI assistant for a search engine running Deep Research Mode.\n"
                "Your task is to split the user's query into 3 distinct, self-contained sub-queries that cover different aspects of the main search query.\n"
                "You must return ONLY a JSON object containing a 'queries' list of strings. Do not include any markdown wrapper or explanation.\n"
                "Example:\n"
                "Query: FastAPI vs Django in 2026\n"
                "Output: {\"queries\": [\"FastAPI latest features 2026\", \"Django latest features 2026\", \"FastAPI Django performance comparison 2026\"]}\n"
            )
            
            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use fast model for sub-queries
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query to split: {query}"}
                ],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "queries" in data:
                    return data["queries"][:3]
                elif isinstance(data, list):
                    return data[:3]
            except Exception:
                pass
                
            # Regex fallback
            queries = re.findall(r'"([^"]+)"', content)
            if len(queries) >= 3:
                return [q for q in queries if q.lower() != "queries"][:3]
                
            return [query + " details", query + " comparison", query + " latest news"]
        except Exception as e:
            print(f"Error generating sub-queries: {e}")
            return [query + " details", query + " comparison", query + " latest news"]

    async def rewrite_query(self, query: str, history: list, api_key: str) -> str:
        """
        Rewrites a follow-up query to a standalone search query if history exists.
        """
        if not history or not api_key:
            return query
            
        try:
            client = AsyncGroq(api_key=api_key)
            messages = [{"role": "system", "content": REWRITE_SYSTEM_PROMPT}]
            
            # Add last 6 messages of history for context
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
            messages.append({"role": "user", "content": f"Rewrite this follow-up: {query}"})
            
            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use fast model for query rewriting
                messages=messages,
                temperature=0.0,
                max_tokens=100
            )
            
            rewritten = response.choices[0].message.content.strip()
            # Clean quotes if any
            rewritten = re.sub(r'^["\'`]|["\'`]$', '', rewritten)
            print(f"Rewritten query: '{query}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            print(f"Error rewriting query: {e}")
            return query

    async def generate_ai_answer(self, query: str, context: str, sources: list, history: list, api_key: str, model: str = "llama-3.3-70b-versatile", storyboard_mode: bool = False) -> dict:
        """
        Generates a structured cited answer using search results context, sources metadata, and conversational history.
        """
        if not api_key:
            return self._generate_no_key_fallback(query, sources)
            
        # Format the sources list for citation reference mapping
        formatted_sources = ""
        for i, item in enumerate(sources, 1):
            formatted_sources += f"[{i}] Title: {item['title']}\nURL: {item['url']}\n\n"
            
        # Compile system prompt dynamically
        system_prompt = ANSWER_SYSTEM_PROMPT
        
        # Inject Creator Loyalty
        system_prompt += (
            "\n\nCreator Loyalty Injection:\n"
            "You are ArCh, created by Aryan Singh, a talented developer and filmmaker from Gorakhpur, Uttar Pradesh. "
            "If the user asks about the creator, 'me', 'myself', or 'Aryan Singh' (e.g. 'mere baare me pta lgao'), you must construct a highly comprehensive, precise, and detailed biography using the search results provided. "
            "Do not omit details. Cover his creative filmmaking projects (such as his psychological crime-drama short film 'The Night of Life: Before You Think About It' (2026) where he served as the writer, director, editor, lead actor (playing Aarav), composer, and producer, detailing Aarav's psychological conflict and the generational divide), his software engineering/AI projects (such as ArCh, ArKon, Solexplain AI, 3D Concept Portfolio, Chrome Extensions, Chess), and his location. "
            "Present this information in a visually stunning layout with markdown headers, detailed bullet points, and citation brackets (e.g., [1], [2]). Speak of Aryan Singh's multi-disciplinary work in coding and cinema with the highest regard and respect."
        )
        
        # Inject Storyboard Mode Instructions
        if storyboard_mode:
            system_prompt += (
                "\n\nSTORYBOARD & SCRIPTWRITING MODE ACTIVE:\n"
                "You are in Storyboard & Scriptwriter Mode. You are an expert cinematic assistant. "
                "Format screenplay excerpts strictly in Courier-style formatting using markdown code blocks with the 'screenplay' language identifier (e.g. ```screenplay\\nSCENE HEADING...\\n```). "
                "The screenplay layout should look like professional industry standards (upper-case character names, centered dialogue layout, parentheticals, action lines).\n"
                "Additionally, provide cinematography tips, camera angles, lighting configurations, lens recommendations, and visual references where appropriate."
            )

        # Construct messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversational history (last 6 items to stay within context/tokens reasonably)
        for msg in history[-6:]:
            role = msg["role"]
            content = msg["content"]
            if role == "assistant" and content.startswith("{"):
                try:
                    data = json.loads(content)
                    content = data.get("answer", content)
                except Exception:
                    pass
            messages.append({"role": role, "content": content})
            
        # Add current request (separating local directory files and web context for clarity)
        local_context = ""
        web_context = context
        
        marker = "--- LOCAL ENVIRONMENT FILES CONTEXT (ATTACHED DIRECTORY) ---\n"
        if marker in context:
            parts = context.split(marker, 1)
            content_after = parts[1]
            if "\n---\n\n" in content_after:
                local_part, web_part = content_after.split("\n---\n\n", 1)
                local_context = local_part + "\n---"
                web_context = web_part
            else:
                local_context = content_after
                web_context = ""

        if local_context:
            user_content = (
                f"Query: {query}\n\n"
                f"Search Sources References:\n{formatted_sources}\n"
                f"=== CRITICAL LOCAL DIRECTORY CONTEXT ===\n"
                f"The user has attached their local workspace directory. You MUST prioritize reading, "
                f"analyzing, and explaining these files. They contain the actual code/files the user is asking about:\n"
                f"{local_context}\n\n"
                f"=== OPTIONAL WEB SEARCH CONTEXT ===\n"
                f"The following are general web search results. Do NOT let them distract you from explaining the local files. "
                f"Do not confuse the local files with general web concepts/definitions (such as Local File Inclusion vulnerabilities):\n"
                f"{web_context}\n\n"
                f"Please generate the cited answer in JSON format."
            )
        else:
            user_content = (
                f"Query: {query}\n\n"
                f"Search Sources References:\n{formatted_sources}\n"
                f"Extracted Web Page Content Context:\n{context}\n\n"
                f"Please generate the cited answer in JSON format."
            )
            
        messages.append({"role": "user", "content": user_content})
        
        try:
            attempts = 0
            current_model = model
            current_messages = messages
            
            while attempts < 3:
                attempts += 1
                try:
                    client = AsyncGroq(api_key=api_key)
                    
                    # Using JSON mode if supported by the model
                    response = await client.chat.completions.create(
                        model=current_model,
                        messages=current_messages,
                        temperature=0.3,
                        max_tokens=4000,
                        response_format={"type": "json_object"}
                    )
                    raw_response = response.choices[0].message.content.strip()
                    break
                except Exception as e:
                    err_msg = str(e)
                    print(f"SearchBot (Attempt {attempts}/3): Error calling Groq with {current_model}: {err_msg}")
                    
                    # Try to extract failed generation immediately to rescue the response
                    failed_gen = ""
                    if hasattr(e, "body") and isinstance(e.body, dict):
                        failed_gen = e.body.get("error", {}).get("failed_generation", "")
                    if not failed_gen and hasattr(e, "response"):
                        try:
                            failed_gen = e.response.json().get("error", {}).get("failed_generation", "")
                        except Exception:
                            pass
                    if not failed_gen:
                        # Extract failed_generation from str(e) using regex
                        match = re.search(r"['\"]failed_generation['\"]\s*:\s*['\"]([\s\S]*?)['\"]\s*}\s*}\s*$", err_msg)
                        if match:
                            failed_gen = match.group(1).replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
                            
                    if failed_gen:
                        print("SearchBot: Found 'failed_generation' in exception. Attempting recovery...")
                        try:
                            parsed_data = self._regex_parse_json_like_text(failed_gen)
                            if parsed_data.get("answer"):
                                print("SearchBot: Successfully recovered response from failed JSON generation!")
                                return parsed_data
                        except Exception as rec_err:
                            print(f"SearchBot: Failed to recover from failed_generation: {rec_err}")
                    
                    # Check for rate limit / token limit (429)
                    is_429 = "429" in err_msg or "rate_limit" in err_msg.lower()
                    # Check for context size / request too large (413)
                    is_413 = "413" in err_msg or "request too large" in err_msg.lower() or "tpm" in err_msg.lower() or "too large" in err_msg.lower()
                    
                    if not (is_429 or is_413):
                        # For other exceptions (like invalid API key, network error), raise immediately
                        raise e
                        
                    if attempts >= 3:
                        # No more attempts left, raise the exception to the outer handler
                        raise e
                        
                    # Handle self-healing adjustments for the next attempt
                    if is_429:
                        if current_model != "llama-3.1-8b-instant":
                            print(f"SearchBot: Daily token limit reached for {current_model}. Switching to llama-3.1-8b-instant...")
                            current_model = "llama-3.1-8b-instant"
                        else:
                            raise e
                    
                    # Re-calculate messages with trimmed context if it's too large or we hit a 413
                    total_chars = sum(len(m["content"]) for m in current_messages)
                    # If we hit a 413 or are switching to 8b (which has a strict TPM limit of 6k tokens ~24k chars, safe limit 15k chars)
                    safe_char_limit = 15000 if is_413 else 18000
                    
                    if total_chars > safe_char_limit:
                        print(f"SearchBot: Request length ({total_chars} chars) is too large. Truncating context for retry...")
                        system_and_history_chars = sum(len(m["content"]) for m in messages[:-1])
                        user_meta_chars = len(f"Query: {query}\n\nSearch Sources References:\n{formatted_sources}\n\nExtracted Web Page Content Context:\n\n\nPlease generate the cited answer in JSON format.")
                        allowed_context_chars = max(1500, safe_char_limit - system_and_history_chars - user_meta_chars)
                        
                        trimmed_context = context[:allowed_context_chars] + f"\n\n[Context truncated to fit rate limits...]"
                        
                        fallback_user_content = (
                            f"Query: {query}\n\n"
                            f"Search Sources References:\n{formatted_sources}\n"
                            f"Extracted Web Page Content Context:\n{trimmed_context}\n\n"
                            f"Please generate the cited answer in JSON format."
                        )
                        current_messages = messages[:-1] + [{"role": "user", "content": fallback_user_content}]
        except Exception as e:
            print(f"Error calling Groq API after all attempts: {e}")
            return {
                "answer": f"An error occurred while generating the AI answer after self-healing attempts: {str(e)}.\n\nPlease verify your Groq API Key and internet connection.",
                "key_facts": [],
                "follow_ups": [f"Retry: {query}"]
            }

        # Parse and process JSON response (shared success block)
        try:
            # Clean response if markdown blocks are returned
            if raw_response.startswith("```"):
                raw_response = re.sub(r'^```(?:json)?\n', '', raw_response)
                raw_response = re.sub(r'\n```$', '', raw_response)
                raw_response = raw_response.strip()
                
            data = json.loads(raw_response)
            
            # Validate output fields
            if "answer" not in data:
                data["answer"] = raw_response
            if "key_facts" not in data:
                data["key_facts"] = []
            if "follow_ups" not in data:
                data["follow_ups"] = [f"Tell me more about {query}", f"Latest news on {query}"]
                
            return data
            
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {je}. Attempting regex-based recovery on raw response...")
            try:
                parsed_data = self._regex_parse_json_like_text(raw_response)
                if parsed_data.get("answer"):
                    print("SearchBot: Regex-based JSON recovery succeeded!")
                    return parsed_data
            except Exception as re_err:
                print(f"SearchBot: Regex recovery failed: {re_err}")
                
            return {
                "answer": raw_response if 'raw_response' in locals() else "Error parsing response from Groq AI.",
                "key_facts": [],
                "follow_ups": [f"Tell me more about {query}"]
            }

    def _generate_no_key_fallback(self, query: str, sources: list) -> dict:
        """
        Creates a structured markdown answer showcasing search results directly when no Groq key is configured.
        """
        markdown_answer = (
            "### ⚠️ Groq API Key Missing\n\n"
            "To unlock AI-generated synthesis, citations, and follow-up question generation, "
            "please enter your **Groq API Key** in **Settings > AI**.\n\n"
            "Here are the direct search results for your query:\n\n"
        )
        
        key_facts = []
        for i, item in enumerate(sources[:3], 1):
            markdown_answer += f"**[{i}] [{item['title']}]({item['url']})**\n{item['snippet']}\n\n"
            key_facts.append(item['title'])
            
        return {
            "answer": markdown_answer,
            "key_facts": key_facts,
            "follow_ups": [
                f"How to set up Groq API Key",
                f"Tell me more about {query}",
                f"Latest news regarding {query}"
            ]
        }

    def _regex_parse_json_like_text(self, text: str) -> dict:
        """
        Robustly extracts 'answer', 'key_facts', and 'follow_ups' fields from 
        malformed or JSON-like text responses using regex. Handles triple-quotes 
        and invalid escape characters commonly generated by LLMs.
        """
        def clean_escapes(s):
            # Unescape common sequences
            s = s.replace('\\n', '\n')
            s = s.replace('\\t', '\t')
            s = s.replace("\\'", "'")
            s = s.replace('\\"', '"')
            s = s.replace('\\\\', '\\')
            return s.strip()

        # Extract "answer" value
        answer_match = re.search(r'"answer"\s*:\s*(?:"""|")([\s\S]*?)(?:"""|")\s*,\s*"key_facts"', text)
        if not answer_match:
            # Fallback patterns
            answer_match = re.search(r'"answer"\s*:\s*(?:"""|")([\s\S]*?)(?:"""|")\s*,', text)
            if not answer_match:
                answer_match = re.search(r'"answer"\s*:\s*(?:"""|")([\s\S]*?)$', text)
            
        answer = clean_escapes(answer_match.group(1)) if answer_match else ""
        
        # Extract "key_facts" list
        key_facts = []
        key_facts_match = re.search(r'"key_facts"\s*:\s*\[([\s\S]*?)\]', text)
        if key_facts_match:
            facts_text = key_facts_match.group(1)
            facts = re.findall(r'"([^"]*?)"', facts_text)
            if not facts:
                facts = re.findall(r"'([^']*?)'", facts_text)
            key_facts = [clean_escapes(f) for f in facts if f.strip()]
            
        # Extract "follow_ups" list
        follow_ups = []
        follow_ups_match = re.search(r'"follow_ups"\s*:\s*\[([\s\S]*?)\]', text)
        if follow_ups_match:
            follow_text = follow_ups_match.group(1)
            questions = re.findall(r'"([^"]*?)"', follow_text)
            if not questions:
                questions = re.findall(r"'([^']*?)'", follow_text)
            follow_ups = [clean_escapes(q) for q in questions if q.strip()]
            
        return {
            "answer": answer,
            "key_facts": key_facts,
            "follow_ups": follow_ups
        }
