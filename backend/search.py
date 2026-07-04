"""Live Web Search Engine with Serper API and DuckDuckGo Fallback

Provides web search capabilities with structured results, news search,
result caching, and automatic fallback when primary API key is unavailable.

Classes:
    SearchEngine: Main search interface with Serper and DuckDuckGo support.

Typical usage:
    from backend.search import SearchEngine
    engine = SearchEngine()
    results = engine.search("quantum computing breakthroughs")
    md = engine.to_markdown(results)
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from backend.config import load_backend_config

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

SERPER_URL = "https://google.serper.dev/search"
SERPER_NEWS_URL = "https://google.serper.dev/news"
CACHE_TTL_SECONDS = 3600  # 1 hour
MAX_CACHE_ENTRIES = 200

# ── Helpers ────────────────────────────────────────────────────────────


def _fallback_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Fallback search using DuckDuckGo when Serper is unavailable.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of result dictionaries with title, link, snippet, source, date.
    """
    try:
        from duckduckgo_search import DDGS

        results: List[Dict[str, str]] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source": _extract_domain(r.get("href", "")),
                        "date": "",
                    }
                )
        return results
    except Exception as exc:
        logger.error("DuckDuckGo fallback failed: %s", exc)
        return []


def _extract_domain(url: str) -> str:
    """Extract domain name from a URL.

    Args:
        url: Full URL string.

    Returns:
        Domain name (e.g., 'example.com').
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return ""


def _now_iso() -> str:
    """Return current ISO-formatted datetime string."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# ── Search Engine ──────────────────────────────────────────────────────


class SearchEngine:
    """Web search engine with Serper API and DuckDuckGo fallback.

    Provides structured search results with caching, markdown formatting,
    and news-specific search capabilities.

    Attributes:
        config: Backend configuration dictionary.
        api_key: Serper API key if available.
        _cache: In-memory result cache keyed by query hash.
        _cache_times: Timestamp tracking for cache entries.

    Example:
        >>> engine = SearchEngine()
        >>> results = engine.search("AI safety", max_results=5)
        >>> print(engine.to_markdown(results))
    """

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        """Initialize the search engine.

        Args:
            config: Optional configuration dictionary. Loads from env if omitted.
        """
        self.config = config or load_backend_config()
        self.api_key: str = str(self.config.get("serper_api_key", ""))
        self._cache: Dict[str, List[Dict[str, str]]] = {}
        self._cache_times: Dict[str, float] = {}
        logger.info(
            "SearchEngine initialized (serper=%s)",
            "enabled" if self.api_key else "fallback",
        )

    # ── Public API ──────────────────────────────────────────────────────

    def search(
        self, query: str, max_results: int = 10
    ) -> List[Dict[str, str]]:
        """Execute a web search and return structured results.

        Checks the cache first, then queries Serper if available,
        falling back to DuckDuckGo if Serper is not configured.

        Args:
            query: Search query string.
            max_results: Maximum number of results (default 10).

        Returns:
            List of result dictionaries, each with:
            - title: Result title
            - link: URL
            - snippet: Brief description
            - source: Domain name
            - date: Publication date (if available)
        """
        if not query or not query.strip():
            return []

        cache_key = self._cache_key(query, max_results)
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Cache hit for query=%s", query)
            return cached

        if self.api_key:
            results = self._serper_search(query, max_results)
        else:
            logger.info("Serper unavailable, using DuckDuckGo fallback")
            results = _fallback_duckduckgo(query, max_results)

        self._set_cache(cache_key, results)
        return results

    def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search for recent news articles.

        Args:
            query: News search query string.
            max_results: Maximum number of results (default 10).

        Returns:
            List of news result dictionaries with title, link, snippet,
            source, and date fields.
        """
        if not query or not query.strip():
            return []

        cache_key = self._cache_key(f"news:{query}", max_results)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if self.api_key:
            results = self._serper_news(query, max_results)
        else:
            # DuckDuckGo news fallback
            try:
                from duckduckgo_search import DDGS

                results: List[Dict[str, str]] = []
                with DDGS() as ddgs:
                    for r in ddgs.news(query, max_results=max_results):
                        results.append(
                            {
                                "title": r.get("title", ""),
                                "link": r.get("url", ""),
                                "snippet": r.get("body", ""),
                                "source": r.get("source", ""),
                                "date": r.get("date", ""),
                            }
                        )
            except Exception as exc:
                logger.error("DuckDuckGo news fallback failed: %s", exc)
                results = []

        self._set_cache(cache_key, results)
        return results

    def to_markdown(self, results: List[Dict[str, str]]) -> str:
        """Format search results as markdown citations.

        Args:
            results: List of result dictionaries from search().

        Returns:
            Markdown-formatted string with numbered citations.
        """
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

    def search_and_summarize(
        self, query: str, max_results: int = 10
    ) -> Dict[str, object]:
        """Search and return both raw results and markdown summary.

        Args:
            query: Search query string.
            max_results: Maximum number of results.

        Returns:
            Dictionary with 'results' (list) and 'markdown' (str) keys.
        """
        results = self.search(query, max_results)
        return {
            "results": results,
            "markdown": self.to_markdown(results),
            "query": query,
            "count": len(results),
        }

    def clear_cache(self) -> None:
        """Clear the in-memory search result cache."""
        self._cache.clear()
        self._cache_times.clear()
        logger.info("Search cache cleared")

    # ── Private: Serper API ─────────────────────────────────────────────

    def _serper_search(
        self, query: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Execute search via Serper API."""
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {"q": query, "num": min(max_results, 20)}
            resp = requests.post(
                SERPER_URL, json=payload, headers=headers, timeout=30
            )
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            return self._parse_serper(data)
        except Exception as exc:
            logger.error("Serper search error: %s, falling back", exc)
            return _fallback_duckduckgo(query, max_results)

    def _serper_news(
        self, query: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Execute news search via Serper API."""
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {"q": query, "num": min(max_results, 20)}
            resp = requests.post(
                SERPER_NEWS_URL, json=payload, headers=headers, timeout=30
            )
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            return self._parse_serper(data, is_news=True)
        except Exception as exc:
            logger.error("Serper news error: %s, falling back", exc)
            return []

    def _parse_serper(
        self, data: Dict[str, Any], is_news: bool = False
    ) -> List[Dict[str, str]]:
        """Parse Serper API response into structured results."""
        results: List[Dict[str, str]] = []
        key = "news" if is_news else "organic"
        entries = data.get(key, [])

        for entry in entries:
            results.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "snippet": entry.get("snippet", ""),
                    "source": _extract_domain(entry.get("link", "")),
                    "date": entry.get("date", ""),
                }
            )
        return results

    # ── Private: Cache ──────────────────────────────────────────────────

    @staticmethod
    def _cache_key(query: str, max_results: int) -> str:
        """Generate a cache key from query parameters."""
        raw = f"{query.strip().lower()}:{max_results}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> Optional[List[Dict[str, str]]]:
        """Retrieve cached results if not expired."""
        if key not in self._cache:
            return None
        age = time.time() - self._cache_times.get(key, 0)
        if age > CACHE_TTL_SECONDS:
            del self._cache[key]
            del self._cache_times[key]
            return None
        return list(self._cache[key])

    def _set_cache(self, key: str, results: List[Dict[str, str]]) -> None:
        """Store results in cache with TTL."""
        # Evict oldest if at capacity
        if len(self._cache) >= MAX_CACHE_ENTRIES:
            oldest = min(self._cache_times, key=self._cache_times.get)
            del self._cache[oldest]
            del self._cache_times[oldest]
        self._cache[key] = list(results)
        self._cache_times[key] = time.time()
