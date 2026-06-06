import asyncio
import time
import os
from backend.providers.custom_crawler import CustomCrawlerProvider

async def test_crawler():
    print("Initializing Custom Crawler...")
    crawler = CustomCrawlerProvider()
    query = "FastAPI Python"
    
    # 1. Live Crawl & Content Retrieval
    print(f"\n--- TEST 1: Live search and page crawling for '{query}' ---")
    start_time = time.time()
    result = await crawler.search(query)
    duration_live = time.time() - start_time
    
    sources = result.get("sources", [])
    context = result.get("context", "")
    
    print(f"Time taken for live crawl: {duration_live:.2f} seconds")
    print(f"Fetched {len(sources)} search sources:")
    
    for idx, r in enumerate(sources[:3], 1):
        safe_title = r['title'].encode('ascii', errors='ignore').decode()
        print(f"[{idx}] {safe_title} -> {r['url']}")
        
    print(f"\nExtracted Context Preview (length={len(context)} chars):")
    safe_context = context[:300].encode('ascii', errors='ignore').decode()
    print(f"{safe_context}...")
    
    assert len(sources) > 0, "Crawler should return search results"
    assert len(context) > 0, "Crawler should return rich page text context"
    
    # Verify Cache file creation
    cache_path = crawler._get_cache_path(query)
    print(f"Cache file path: {cache_path}")
    assert os.path.exists(cache_path), "Cache file should be created"
    
    # 2. Cache Hit Testing
    print(f"\n--- TEST 2: Repeated search (should hit cache) ---")
    start_time = time.time()
    result_cached = await crawler.search(query)
    duration_cached = time.time() - start_time
    
    sources_cached = result_cached.get("sources", [])
    context_cached = result_cached.get("context", "")
    
    print(f"Time taken for cached load: {duration_cached:.4f} seconds")
    assert len(sources_cached) == len(sources), "Cached sources count should match"
    assert len(context_cached) == len(context), "Cached context length should match"
    assert duration_cached < 0.1, "Cached load should be extremely fast (<0.1s)"
    
    print("\nCrawler & Cache System Test: PASSED!")

if __name__ == "__main__":
    asyncio.run(test_crawler())
