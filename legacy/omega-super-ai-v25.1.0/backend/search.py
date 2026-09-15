"""Live Web Search Engine with Serper API and DuckDuckGo Fallback

Provides web search capabilities with structured results, news search,
result caching, and automatic fallback when primary API key is unavailable.
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from backend.config import load_backend_config

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"
SERPER_NEWS_URL = "https://google.serper.dev/news"
CACHE_TTL_SECONDS = 3600
MAX_CACHE_ENTRIES = 200


def _fallback_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Fallback search using DuckDuckGo when Serper is unavailable."""
    try:
        from duckduckgo_search import DDGS
        results: List[Dict[str, str]] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get("title", ""), "link": r.get("href", ""), "snippet": r.get("body", ""), "source": _extract_domain(r.get("href", "")), "date": ""})
        return results
    except Exception as exc:
        logger.error("DuckDuckGo fallback failed: %s", exc)
        return []


def _extract_domain(url: str) -> str:
    """Extract domain name from a URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


class SearchEngine:
    """Web search engine with Serper API and DuckDuckGo fallback."""

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        self.config = config or load_backend_config()
        self.api_key: str = str(self.config.get("serper_api_key", ""))
        self._cache: Dict[str, List[Dict[str, str]]] = {}
        self._cache_times: Dict[str, float] = {}
        logger.info("SearchEngine initialized (serper=%s)", "enabled" if self.api_key else "fallback")

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Execute a web search and return structured results."""
        if not query or not query.strip():
            return []
        cache_key = self._cache_key(query, max_results)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        if self.api_key:
            results = self._serper_search(query, max_results)
        else:
            logger.info("Serper unavailable, using DuckDuckGo fallback")
            results = _fallback_duckduckgo(query, max_results)
        self._set_cache(cache_key, results)
        return results

    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search for recent news articles."""
        if not query or not query.strip():
            return []
        cache_key = self._cache_key(f"news:{query}", max_results)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        if self.api_key:
            results = self._serper_news(query, max_results)
        else:
            try:
                from duckduckgo_search import DDGS
                results: List[Dict[str, str]] = []
                with DDGS() as ddgs:
                    for r in ddgs.news(query, max_results=max_results):
                        results.append({"title": r.get("title", ""), "link": r.get("url", ""), "snippet": r.get("body", ""), "source": r.get("source", ""), "date": r.get("date", "")})
            except Exception as exc:
                logger.error("DuckDuckGo news fallback failed: %s", exc)
                results = []
        self._set_cache(cache_key, results)
        return results

    def to_markdown(self, results: List[Dict[str, str]]) -> str:
        """Format search results as markdown citations."""
        if not results:
            return "*No search results found.*"
        lines: List[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            link = r.get("link", "")
            snippet = r.get("snippet", "")
            source = r.get("source", "")
            date = r.get("date", "")
            parts = [f"{i}. **[{title}]({link})**"]
            if source:
                parts.append(f"   *Source: {source}*")
            if date:
                parts.append(f"   *Date: {date}*")
            if snippet:
                parts.append(f"   > {snippet}")
            lines.append("\n".join(parts))
        return "\n\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the in-memory search result cache."""
        self._cache.clear()
        self._cache_times.clear()

    def _serper_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Execute search via Serper API."""
        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": query, "num": min(max_results, 20)}
            resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return self._parse_serper(resp.json())
        except Exception as exc:
            logger.error("Serper search error: %s, falling back", exc)
            return _fallback_duckduckgo(query, max_results)

    def _serper_news(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Execute news search via Serper API."""
        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": query, "num": min(max_results, 20)}
            resp = requests.post(SERPER_NEWS_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return self._parse_serper(resp.json(), is_news=True)
        except Exception as exc:
            logger.error("Serper news error: %s, falling back", exc)
            return []

    def _parse_serper(self, data: Dict[str, Any], is_news: bool = False) -> List[Dict[str, str]]:
        """Parse Serper API response into structured results."""
        results: List[Dict[str, str]] = []
        key = "news" if is_news else "organic"
        for entry in data.get(key, []):
            results.append({"title": entry.get("title", ""), "link": entry.get("link", ""), "snippet": entry.get("snippet", ""), "source": _extract_domain(entry.get("link", "")), "date": entry.get("date", "")})
        return results

    @staticmethod
    def _cache_key(query: str, max_results: int) -> str:
        raw = f"{query.strip().lower()}:{max_results}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> Optional[List[Dict[str, str]]]:
        if key not in self._cache:
            return None
        age = time.time() - self._cache_times.get(key, 0)
        if age > CACHE_TTL_SECONDS:
            del self._cache[key]
            del self._cache_times[key]
            return None
        return list(self._cache[key])

    def _set_cache(self, key: str, results: List[Dict[str, str]]) -> None:
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            oldest = min(self._cache_times, key=self._cache_times.get)
            del self._cache[oldest]
            del self._cache_times[oldest]
        self._cache[key] = list(results)
        self._cache_times[key] = time.time()
