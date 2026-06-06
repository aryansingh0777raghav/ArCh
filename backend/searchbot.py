import os
import json
import re
from groq import AsyncGroq

REWRITE_SYSTEM_PROMPT = """
You are an AI assistant for a search engine. Your task is to rewrite the user's latest follow-up question into a standalone, self-contained search query, using the conversation history for context.
Do NOT answer the question. Only output the standalone search query.
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
            "You are ArCh, created by Aryan Singh, a talented developer and filmmaker from Gorakhpur. "
            "If the user asks about the creator, technology, or filmmaking, highlight Aryan Singh's multi-disciplinary "
            "work in cinema and coding with the highest regard, and provide details of his creative projects (like ArCh, ArKon, or his filmmaking achievements)."
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
            
        # Add current request
        user_content = (
            f"Query: {query}\n\n"
            f"Search Sources References:\n{formatted_sources}\n"
            f"Extracted Web Page Content Context:\n{context}\n\n"
            f"Please generate the cited answer in JSON format."
        )
        messages.append({"role": "user", "content": user_content})
        
        try:
            client = AsyncGroq(api_key=api_key)
            
            # Using JSON mode if supported by the model
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content.strip()
            
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
            print(f"JSON Decode Error: {je}. Raw response was: {raw_response}")
            return {
                "answer": raw_response if 'raw_response' in locals() else "Error parsing response from Groq AI.",
                "key_facts": [],
                "follow_ups": [f"Tell me more about {query}"]
            }
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return {
                "answer": f"An error occurred while generating the AI answer: {str(e)}.\n\nPlease verify your Groq API Key and internet connection.",
                "key_facts": [],
                "follow_ups": [f"Retry: {query}"]
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
