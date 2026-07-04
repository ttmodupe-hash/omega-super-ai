#!/usr/bin/env python3
"""
Omega Super AI v10 — Multi-Engine Search Module
================================================
Aggregates results from Google Serper, DuckDuckGo, Wikipedia, and ArXiv.
Provides unified search orchestration with quality scoring, deduplication,
and 24-hour JSON-file caching.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus, urlparse

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_RESULTS: int = 10
CACHE_TTL_SECONDS: int = 86_400  # 24 hours
CACHE_DIR: str = os.path.join(os.path.expanduser("~"), ".omega_cache")

# Quality-scoring lookup
DOMAIN_BONUSES: dict[str, int] = {
    ".gov": 30,
    ".edu": 30,
    ".ac.uk": 30,
    "arxiv.org": 20,
    "github.com": 20,
    "wikipedia.org": 10,
    "reuters.com": 15,
    "bloomberg.com": 15,
    "ft.com": 15,
    "nature.com": 20,
    "science.org": 20,
    "ieee.org": 20,
    "news.bbc.co.uk": 15,
    "bbc.com": 15,
    "nytimes.com": 15,
    "wsj.com": 15,
    "economist.com": 15,
    "mit.edu": 25,
    "stanford.edu": 25,
    "harvard.edu": 25,
    "cam.ac.uk": 25,
    "ox.ac.uk": 25,
}

DOMAIN_PENALTIES: dict[str, int] = {
    "reddit.com": -20,
    "quora.com": -20,
    "yahoo.answers": -20,
    "answers.yahoo": -20,
    "forum": -20,
    "4chan.org": -30,
    "9gag.com": -30,
    "clickbait": -25,
    "taboola": -25,
    "outbrain": -25,
}

TRUSTED_SNIPPET_MIN_LEN: int = 40

_HTTP_TIMEOUT: int = 15
_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_cache_dir() -> None:
    """Create the on-disk cache directory if it does not exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(engine: str, query: str, max_results: int) -> str:
    """Deterministic MD5 cache key."""
    payload = f"{engine}|{query.lower().strip()}|{max_results}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    """Full filesystem path for a cache key."""
    _ensure_cache_dir()
    return os.path.join(CACHE_DIR, f"{key}.json")


def _read_cache(key: str) -> dict[str, Any] | None:
    """Read cached result if present and not expired."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cached_at = datetime.fromisoformat(data.get("cached_at", "1970-01-01T00:00:00"))
        if datetime.now(timezone.utc) - cached_at > timedelta(seconds=CACHE_TTL_SECONDS):
            os.remove(path)
            return None
        return data.get("payload")
    except Exception:
        return None


def _write_cache(key: str, payload: dict[str, Any]) -> None:
    """Persist payload to on-disk JSON cache."""
    path = _cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "payload": payload,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass  # Cache write failures are non-fatal


def _domain_from_url(url: str) -> str:
    """Extract lower-case netloc from a URL."""
    try:
        return urlparse(url).netloc.lower().strip()
    except Exception:
        return ""


def _quality_score(url: str, position: int) -> int:
    """Calculate a quality score for a search result."""
    domain = _domain_from_url(url)
    score = max(0, 100 - (position * 5))
    for suffix, bonus in DOMAIN_BONUSES.items():
        if suffix in domain:
            score += bonus
    for suffix, penalty in DOMAIN_PENALTIES.items():
        if suffix in domain:
            score += penalty
    return max(0, min(score, 200))


def _is_duplicate(new_result: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
    """Check URL equality *or* high snippet similarity for deduplication."""
    new_url = new_result.get("link", "")
    new_snippet = new_result.get("snippet", "")
    for old in existing:
        if new_url and old.get("link") == new_url:
            return True
        # Jaccard similarity on word sets for snippet overlap
        old_snippet = old.get("snippet", "")
        if new_snippet and old_snippet:
            new_words = set(re.findall(r"\b\w{4,}\b", new_snippet.lower()))
            old_words = set(re.findall(r"\b\w{4,}\b", old_snippet.lower()))
            if new_words and old_words:
                intersection = len(new_words & old_words)
                union = len(new_words | old_words)
                similarity = intersection / union if union else 0.0
                if similarity >= 0.75:
                    return True
    return False


def _deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate results keeping highest-scoring occurrence."""
    unique: list[dict[str, Any]] = []
    for r in results:
        if not _is_duplicate(r, unique):
            unique.append(r)
        else:
            # Replace if the new result has a higher score
            for i, existing in enumerate(unique):
                if existing.get("link") == r.get("link"):
                    if r.get("quality_score", 0) > existing.get("quality_score", 0):
                        unique[i] = r
                    break
    return unique


def _requests_session() -> requests.Session:
    """Create a session with sensible defaults."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    )
    return session


# ---------------------------------------------------------------------------
# Search engine implementations
# ---------------------------------------------------------------------------


def serper_search(query: str, api_key: str, max_results: int = DEFAULT_MAX_RESULTS) -> dict[str, Any]:
    """
    Execute a Google search via the Serper API.

    Parameters
    ----------
    query: Search query string.
    api_key: Serper API key.
    max_results: Maximum number of organic results to return.

    Returns
    -------
    dict with ``results`` (list), ``source`` ("serper"), and ``error`` (if any).
    """
    cache_key = _cache_key("serper", query, max_results)
    cached = _read_cache(cache_key)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    if not api_key or api_key.strip().lower() in ("", "none", "your_api_key_here"):
        return {"results": [], "source": "serper", "error": "No valid Serper API key provided", "from_cache": False}

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": min(max_results, 20)}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        return {"results": [], "source": "serper", "error": str(exc), "from_cache": False}
    except Exception as exc:
        return {"results": [], "source": "serper", "error": str(exc), "from_cache": False}

    raw_results: list[dict[str, Any]] = []
    for idx, item in enumerate(data.get("organic", [])[:max_results]):
        raw_results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serper",
                "position": idx,
                "quality_score": _quality_score(item.get("link", ""), idx),
                "full_content": None,
            }
        )

    # Also pull knowledgeGraph / answerBox if present
    kg = data.get("knowledgeGraph", {})
    answer = data.get("answerBox", {})
    metadata = {}
    if kg:
        metadata["knowledge_graph"] = kg
    if answer:
        metadata["answer_box"] = answer

    result = {
        "results": raw_results,
        "source": "serper",
        "metadata": metadata,
        "from_cache": False,
    }
    _write_cache(cache_key, result)
    return result


def duckduckgo_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> dict[str, Any]:
    """
    Search DuckDuckGo via their HTML endpoint (no API key required).

    Parameters
    ----------
    query: Search query string.
    max_results: Maximum number of results to return.

    Returns
    -------
    dict with ``results`` and ``source`` set to ``"duckduckgo"``.
    """
    cache_key = _cache_key("ddg", query, max_results)
    cached = _read_cache(cache_key)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    # DDG requires fetching a token first
    session = _requests_session()
    try:
        # Step 1 — get the token
        token_resp = session.get("https://duckduckgo.com/", timeout=_HTTP_TIMEOUT)
        token_resp.raise_for_status()
        html = token_resp.text

        # Extract vqd token
        vqd_match = re.search(r'vqd=([\d-]+)', html)
        if not vqd_match:
            # Try alternative pattern
            vqd_match = re.search(r'"vqd":"([^"]+)"', html)
        if not vqd_match:
            return {"results": [], "source": "duckduckgo", "error": "Could not extract DDG token", "from_cache": False}

        vqd = vqd_match.group(1)

        # Step 2 — perform search
        search_url = (
            f"https://links.duckduckgo.com/d.js"
            f"?q={quote_plus(query)}"
            f"&vqd={vqd}"
            f"&kl=us-en"
            f"&s=0"
            f"&dc={max_results}"
        )
        search_resp = session.get(search_url, timeout=_HTTP_TIMEOUT)
        search_resp.raise_for_status()
        search_html = search_resp.text

        # Parse results from the response — DDG returns JSON-like blocks
        results: list[dict[str, Any]] = []
        # Extract result blocks
        result_blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
            r'.*?<a[^>]+class="result__url"[^>]*>([^<]+)</a>'
            r'.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            search_html,
            re.DOTALL | re.IGNORECASE,
        )

        if not result_blocks:
            # Fallback: try simpler regex patterns
            links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', search_html)
            titles = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', search_html)
            snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', search_html)

            for i in range(min(len(links), len(titles), max_results)):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                link = links[i].strip()
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
                if link and title:
                    results.append(
                        {
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "duckduckgo",
                            "position": i,
                            "quality_score": _quality_score(link, i),
                            "full_content": None,
                        }
                    )
        else:
            for i, (link, title_raw, _, snippet_raw) in enumerate(result_blocks[:max_results]):
                title = re.sub(r'<[^>]+>', '', title_raw).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()
                if link and title:
                    results.append(
                        {
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "duckduckgo",
                            "position": i,
                            "quality_score": _quality_score(link, i),
                            "full_content": None,
                        }
                    )

        # If still no results, try the lite version
        if not results:
            lite_url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
            lite_resp = session.get(lite_url, timeout=_HTTP_TIMEOUT)
            lite_html = lite_resp.text

            result_rows = re.findall(
                r'<tr[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</tr>.*?<tr[^>]*>.*?<td[^>]+class="result-snippet"[^>]*>(.*?)</td>.*?</tr>',
                lite_html,
                re.DOTALL | re.IGNORECASE,
            )
            for i, (link, title_raw, snippet_raw) in enumerate(result_rows[:max_results]):
                title = re.sub(r'<[^>]+>', '', title_raw).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet_raw).strip()
                if link and title:
                    results.append(
                        {
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "duckduckgo",
                            "position": i,
                            "quality_score": _quality_score(link, i),
                            "full_content": None,
                        }
                    )

        result = {"results": results, "source": "duckduckgo", "from_cache": False}
        _write_cache(cache_key, result)
        return result

    except requests.exceptions.RequestException as exc:
        return {"results": [], "source": "duckduckgo", "error": str(exc), "from_cache": False}
    except Exception as exc:
        return {"results": [], "source": "duckduckgo", "error": str(exc), "from_cache": False}


def wikipedia_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search Wikipedia via the MediaWiki API.

    Parameters
    ----------
    query: Search query string.
    max_results: Maximum number of results to return.

    Returns
    -------
    dict with ``results`` and ``source`` set to ``"wikipedia"``.
    """
    cache_key = _cache_key("wiki", query, max_results)
    cached = _read_cache(cache_key)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    session = _requests_session()
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": max_results,
        "format": "json",
        "origin": "*",
    }

    try:
        resp = session.get(search_url, params=params, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        results: list[dict[str, Any]] = []
        for idx, item in enumerate(data.get("query", {}).get("search", [])):
            title = item.get("title", "")
            page_id = item.get("pageid", "")
            snippet = re.sub(r'<[^>]+>', '', item.get("snippet", "")).strip()
            link = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
            results.append(
                {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "source": "wikipedia",
                    "position": idx,
                    "quality_score": _quality_score(link, idx) + 10,
                    "full_content": None,
                    "page_id": page_id,
                }
            )

        result = {"results": results, "source": "wikipedia", "from_cache": False}
        _write_cache(cache_key, result)
        return result

    except requests.exceptions.RequestException as exc:
        return {"results": [], "source": "wikipedia", "error": str(exc), "from_cache": False}
    except Exception as exc:
        return {"results": [], "source": "wikipedia", "error": str(exc), "from_cache": False}


def arxiv_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search ArXiv for academic papers via the ArXiv API.

    Parameters
    ----------
    query: Search query string.
    max_results: Maximum number of results to return.

    Returns
    -------
    dict with ``results`` and ``source`` set to ``"arxiv"``.
    """
    cache_key = _cache_key("arxiv", query, max_results)
    cached = _read_cache(cache_key)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    session = _requests_session()
    search_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        resp = session.get(search_url, params=params, timeout=_HTTP_TIMEOUT)
        resp.raise_for_status()
        xml_text = resp.text

        results: list[dict[str, Any]] = []
        # Parse Atom XML with regex (lightweight, no heavy deps)
        entries = re.findall(r'<entry>(.*?)</entry>', xml_text, re.DOTALL)

        for idx, entry in enumerate(entries[:max_results]):
            title = re.sub(r"\s+", " ", re.findall(r'<title>(.*?)</title>', entry, re.DOTALL)[0].strip()) if re.findall(r'<title>(.*?)</title>', entry, re.DOTALL) else ""
            summary = re.sub(r"\s+", " ", re.findall(r'<summary>(.*?)</summary>', entry, re.DOTALL)[0].strip()) if re.findall(r'<summary>(.*?)</summary>', entry, re.DOTALL) else ""
            link_match = re.findall(r'<link[^>]+href="([^"]+)"[^>]*rel="alternate"', entry)
            link = link_match[0] if link_match else ""
            if not link:
                link_match = re.findall(r'<id>(.*?)</id>', entry)
                link = link_match[0] if link_match else ""

            authors = re.findall(r'<name>([^<]+)</name>', entry)
            published = re.findall(r'<published>([^<]+)</published>', entry)
            categories = re.findall(r'<category[^>]+term="([^"]+)"', entry)

            results.append(
                {
                    "title": title,
                    "link": link,
                    "snippet": summary[:500],
                    "source": "arxiv",
                    "position": idx,
                    "quality_score": _quality_score(link, idx) + 20,
                    "full_content": None,
                    "authors": authors,
                    "published": published[0] if published else "",
                    "categories": categories,
                }
            )

        result = {"results": results, "source": "arxiv", "from_cache": False}
        _write_cache(cache_key, result)
        return result

    except requests.exceptions.RequestException as exc:
        return {"results": [], "source": "arxiv", "error": str(exc), "from_cache": False}
    except Exception as exc:
        return {"results": [], "source": "arxiv", "error": str(exc), "from_cache": False}


# ---------------------------------------------------------------------------
# Unified orchestration
# ---------------------------------------------------------------------------


def unified_search(
    query: str,
    api_key: str,
    max_results: int = 15,
    engines: list[str] | None = None,
) -> dict[str, Any]:
    """
    Orchestrate multiple search engines, deduplicate results, score them,
    and return a comprehensive unified response.

    Parameters
    ----------
    query: The user's search query.
    api_key: Serper API key (used for Google Serper).
    max_results: Maximum number of final results to return.
    engines: List of engine names to query. Defaults to all available.

    Returns
    -------
    dict containing:
        - ``query``: original query
        - ``results``: deduplicated, scored, sorted results
        - ``sources``: list of source names used
        - ``summary``: auto-generated summary string
        - ``engines_used``: list of engine names that returned results
        - ``from_cache``: whether the unified result was fully cached
    """
    if engines is None:
        engines = ["serper", "duckduckgo", "wikipedia", "arxiv"]

    query = query.strip()
    if not query:
        return {
            "query": query,
            "results": [],
            "sources": [],
            "summary": "Empty query provided.",
            "engines_used": [],
            "from_cache": False,
        }

    # Check unified cache
    cache_key = _cache_key("unified", query, max_results)
    cached = _read_cache(cache_key)
    if cached is not None:
        cached["from_cache"] = True
        return cached

    # Execute all engines in parallel
    engine_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures: dict[Any, str] = {}
        if "serper" in engines:
            futures[pool.submit(serper_search, query, api_key, max_results)] = "serper"
        if "duckduckgo" in engines:
            futures[pool.submit(duckduckgo_search, query, max_results)] = "duckduckgo"
        if "wikipedia" in engines:
            futures[pool.submit(wikipedia_search, query, 5)] = "wikipedia"
        if "arxiv" in engines:
            futures[pool.submit(arxiv_search, query, 5)] = "arxiv"

        for future in as_completed(futures):
            engine_name = futures[future]
            try:
                engine_results[engine_name] = future.result(timeout=30)
            except Exception as exc:
                engine_results[engine_name] = {
                    "results": [],
                    "source": engine_name,
                    "error": str(exc),
                    "from_cache": False,
                }

    # Merge, deduplicate, and sort
    all_results: list[dict[str, Any]] = []
    engines_with_results: list[str] = []

    for engine_name in engines:
        res = engine_results.get(engine_name, {})
        if res.get("results"):
            engines_with_results.append(engine_name)
            for r in res["results"]:
                if r.get("title") or r.get("snippet"):
                    all_results.append(r)

    deduped = _deduplicate(all_results)
    deduped.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    final_results = deduped[:max_results]

    # Generate summary
    summary = _generate_summary(query, final_results)

    result = {
        "query": query,
        "results": final_results,
        "sources": list({r.get("source", "unknown") for r in final_results}),
        "summary": summary,
        "engines_used": engines_with_results,
        "from_cache": False,
    }

    _write_cache(cache_key, result)
    return result


def _generate_summary(query: str, results: list[dict[str, Any]]) -> str:
    """Generate a brief summary string from search results."""
    if not results:
        return f"No results found for '{query}'."

    source_counts: dict[str, int] = {}
    for r in results:
        src = r.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    top_result = results[0]
    parts = [
        f"Found {len(results)} result(s) for '{query}'.",
        f"Top result: {top_result.get('title', 'N/A')} "
        f"({top_result.get('link', 'N/A')}) — "
        f"score {top_result.get('quality_score', 0)}.",
        f"Sources: {', '.join(f'{k}({v})' for k, v in sorted(source_counts.items(), key=lambda x: -x[1]))}.",
    ]
    return " ".join(parts)
