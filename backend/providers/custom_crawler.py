import os
import json
import re
import urllib.parse
import hashlib
import asyncio
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
from backend.providers.base import SearchProvider

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class CustomCrawlerProvider(SearchProvider):
    def __init__(self):
        self.cache_validity_hours = 24

    def _get_cache_path(self, query: str) -> str:
        # Generate a unique MD5 hash for the query to use as filename
        normalized_query = query.lower().strip()
        query_hash = hashlib.md5(normalized_query.encode('utf-8')).hexdigest()
        return os.path.join(CACHE_DIR, f"{query_hash}.json")

    def _get_cached_results(self, query: str) -> dict:
        cache_file = self._get_cache_path(query)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Check expiration
                timestamp_str = data.get("timestamp", "")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if datetime.utcnow() - timestamp < timedelta(hours=self.cache_validity_hours):
                        print(f"Cache hit for query: '{query}'")
                        return data
            except Exception as e:
                print(f"Error reading cache for query '{query}': {e}")
        return None

    def _set_cached_results(self, query: str, sources: list, context: str, images: list = None):
        cache_file = self._get_cache_path(query)
        try:
            cache_data = {
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "sources": sources,
                "context": context,
                "images": images or []
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            print(f"Cached results saved for query: '{query}'")
        except Exception as e:
            print(f"Error writing cache for query '{query}': {e}")

    async def _fetch_target_content(self, session: aiohttp.ClientSession, url: str) -> dict:
        """
        Asynchronously fetches, cleans the main text content, and extracts image URLs from a target URL.
        """
        res_dict = {"text": "", "images": []}
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return res_dict
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, with Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            # Polite delay before target fetching
            await asyncio.sleep(0.5)
            
            async with session.get(url, headers=headers, timeout=6) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # 1. Extract high-quality images before decomposing elements
                    images = []
                    
                    # Check OpenGraph and Twitter images
                    og_img = soup.find("meta", attrs={"property": "og:image"})
                    if og_img and og_img.get("content"):
                        images.append(urllib.parse.urljoin(url, og_img.get("content")))
                        
                    tw_img = soup.find("meta", attrs={"name": "twitter:image"})
                    if tw_img and tw_img.get("content"):
                        images.append(urllib.parse.urljoin(url, tw_img.get("content")))
                        
                    # Check body images
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if src:
                            full_src = urllib.parse.urljoin(url, src)
                            if not full_src.startswith("data:"):
                                src_lower = full_src.lower()
                                # Filter tracking pixels, icons, user avatars, buttons, loaders
                                if not any(term in src_lower for term in ["logo", "icon", "avatar", "loader", "ad", "button", "spinner", "tracker", "pixel", "banner"]):
                                    if any(ext in src_lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                                        images.append(full_src)
                                        
                    # Deduplicate images preserving order
                    seen_img = set()
                    res_dict["images"] = [img for img in images if not (img in seen_img or seen_img.add(img))][:10]

                    # 2. Decompose scripts, styles, forms, and common navigation items
                    for element in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav", "aside", "form"]):
                        element.decompose()
                        
                    # Decompose structures matching navigation classes/ids
                    for element in soup.find_all(class_=re.compile(r"menu|nav|sidebar|footer|ad-|advertisement|header|cookie|popup|banner", re.I)):
                        element.decompose()
                    for element in soup.find_all(id=re.compile(r"menu|nav|sidebar|footer|ad|header|cookie|popup|banner", re.I)):
                        element.decompose()
                        
                    # Extract text from paragraph-like elements
                    text_elements = soup.find_all(['p', 'article', 'section', 'h1', 'h2', 'h3'])
                    text_blocks = []
                    
                    for el in text_elements:
                        text = el.get_text(strip=True)
                        if len(text) > 40:
                            text_blocks.append(text)
                            
                    combined_text = "\n".join(text_blocks)
                    cleaned_text = re.sub(r'\s+', ' ', combined_text).strip()
                    res_dict["text"] = cleaned_text[:3000]
                    return res_dict
                else:
                    print(f"Crawler: Target URL '{url}' returned status {response.status}")
                    return res_dict
        except Exception as e:
            print(f"Crawler: Error fetching target content from '{url}': {e}")
            return res_dict

    async def search(self, query: str, api_key: str = None) -> dict:
        """
        Main search entry point. Checks cache first. Returns a dictionary:
        {
           "query": str,
           "sources": list of dict,
           "context": str (Rich text context combined from target pages),
           "images": list of str (Image URLs for visual board)
        }
        """
        # 1. Check local cache
        cached = self._get_cached_results(query)
        if cached:
            if "images" not in cached:
                cached["images"] = []
            return cached

        # 2. Perform live DuckDuckGo HTML crawl
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        sources = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=8) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        result_divs = soup.find_all("div", class_="result__body")
                        
                        for div in result_divs[:6]:
                            title_a = div.find("a", class_="result__a")
                            snippet_div = div.find("a", class_="result__snippet") or div.find("div", class_="result__snippet")
                            
                            if title_a:
                                title = title_a.get_text(strip=True)
                                raw_url = title_a.get("href", "")
                                
                                parsed_url = raw_url
                                if "uddg=" in raw_url:
                                    try:
                                        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                                        parsed_url = query_params.get("uddg", [raw_url])[0]
                                    except Exception:
                                        pass
                                elif raw_url.startswith("//"):
                                    parsed_url = "https:" + raw_url
                                    
                                snippet = ""
                                if snippet_div:
                                    snippet = snippet_div.get_text(strip=True)
                                    
                                sources.append({
                                    "title": title,
                                    "url": parsed_url,
                                    "snippet": snippet
                                })
                                
        except Exception as e:
            print(f"Crawler: Error scraping DuckDuckGo: {e}")

        if not sources:
            print("Crawler: No results scraped, constructing search fallback.")
            sources = self._get_dynamic_fallback(query)

        # 3. Retrieve target contents from top 3 search results concurrently
        context_blocks = []
        top_sources = sources[:3]
        all_images = []
        
        print(f"Crawler: Concurrently fetching target content and images from {len(top_sources)} sources...")
        
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [self._fetch_target_content(session, src["url"]) for src in top_sources]
                results = await asyncio.gather(*tasks)
                
                for idx, res_dict in enumerate(results):
                    text = res_dict.get("text", "")
                    imgs = res_dict.get("images", [])
                    if imgs:
                        all_images.extend(imgs)
                    if text:
                        source_info = top_sources[idx]
                        context_blocks.append(f"Source [{idx + 1}] Title: {source_info['title']}\nURL: {source_info['url']}\nContent:\n{text}\n---")
        except Exception as e:
            print(f"Crawler: Error gathering target content: {e}")

        # Deduplicate all gathered images
        seen_img = set()
        unique_images = [img for img in all_images if not (img in seen_img or seen_img.add(img))]

        # Compile final context package
        if context_blocks:
            context = "\n\n".join(context_blocks)
        else:
            print("Crawler: Could not extract target page content, falling back to result snippets context.")
            snippet_blocks = [f"Source [{i+1}] Title: {s['title']}\nSnippet: {s['snippet']}" for i, s in enumerate(sources)]
            context = "\n\n".join(snippet_blocks)

        # 4. Save to cache
        self._set_cached_results(query, sources, context, unique_images)

        return {
            "query": query,
            "sources": sources,
            "context": context,
            "images": unique_images
        }

    def _get_dynamic_fallback(self, query: str) -> list:
        query_esc = urllib.parse.quote(query)
        return [
            {
                "title": f"{query} - Wikipedia",
                "url": f"https://en.wikipedia.org/wiki/{query_esc}",
                "snippet": f"Encyclopedia article about {query}, discussing history, concepts, key statistics, and references."
            },
            {
                "title": f"Latest news on {query}",
                "url": f"https://news.google.com/search?q={query_esc}",
                "snippet": f"Comprehensive up-to-date news reports, analyses, and headlines covering recent developments about {query}."
            },
            {
                "title": f"Britannica: {query} summary",
                "url": f"https://www.britannica.com/search?query={query_esc}",
                "snippet": f"Encyclopedic entry for {query}. Explore major historical events, facts, biographies, and context from Britannica editors."
            }
        ]
