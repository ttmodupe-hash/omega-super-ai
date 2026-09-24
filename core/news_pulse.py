"""NEWS-1 — World Pulse: real, cited, timestamped news for the Luqi-ai engine.

Why this exists: the founder's directive — "Luqi-ai must strive to be up to date
in world matters." The mission (help people avoid scams, understand finance,
learn) is hollow if the engine goes silent when the world moves.

Honesty architecture (non-negotiable, same law as the rest of the engine):
  * Headlines are RETRIEVED from live publisher feeds — never generated from
    model memory. Every item carries its source name, canonical link and the
    publisher's own timestamp.
  * Every response states exactly when it was produced (generated_at, UTC)
    and which feeds succeeded/failed — freshness is always visible.
  * Fail-closed: if no feed is reachable we return an honest 503 —
    "news unavailable right now" — we NEVER invent headlines.

Cost discipline ("from my pocket"): RSS/Atom feeds only — zero API keys,
zero paid news services, zero new dependencies (Python stdlib parsing).

Security: the feed registry is a STATIC server-side allowlist. No
user-supplied URL is ever fetched (SSRF-safe by construction — see
core/ssrf_guard.py for the platform's outbound policy).

Sources (all public, key-free, documented):
  * BBC News feeds (feeds.bbci.co.uk) — BBC's canonical public RSS endpoints.
  * News24 capi24 feeds — current public endpoints (topstories, southafrica).
  * WHO news RSS — verified live from our sandbox 2026-09-24.
  * Al Jazeera all-news RSS.
"""
from __future__ import annotations

import re
import time
import threading
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/news", tags=["news"])

USER_AGENT = "Luqi-ai WorldPulse/1.0 (+https://luqi-ai.com)"
FETCH_TIMEOUT_S = 12
CACHE_TTL_S = 600  # 10 minutes — protects upstreams and our bandwidth bill
MAX_ITEMS_PER_FEED = 25
ATOM_NS = "{http://www.w3.org/2005/Atom}"

# ---------------------------------------------------------------------------
# Static feed registry (server-side allowlist — the ONLY URLs ever fetched)
# ---------------------------------------------------------------------------
FEED_REGISTRY: dict[str, list[dict]] = {
    "south-africa": [
        {"source": "News24 Top Stories", "url": "https://feeds.capi24.com/v1/Search/articles/news24/topstories/rss"},
        {"source": "News24 South Africa", "url": "https://feeds.capi24.com/v1/Search/articles/news24/southafrica/rss"},
    ],
    "africa": [
        {"source": "BBC News Africa", "url": "https://feeds.bbci.co.uk/news/world/africa/rss.xml"},
        {"source": "News24 Top Stories", "url": "https://feeds.capi24.com/v1/Search/articles/news24/topstories/rss"},
    ],
    "world": [
        {"source": "BBC News World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"source": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    ],
    "business": [
        {"source": "BBC News Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    ],
    "health": [
        {"source": "World Health Organization", "url": "https://www.who.int/rss-feeds/news-english.xml"},
        {"source": "BBC News Health", "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    ],
    "science": [
        {"source": "BBC News Science & Environment", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    ],
    "technology": [
        {"source": "BBC News Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    ],
}

HONESTY_NOTE = (
    "Headlines are retrieved live from the publishers' own feeds and shown with "
    "source, link and timestamp. Luqi-ai never invents news: if every feed is "
    "unreachable this API says so (503) instead of guessing."
)

# ---------------------------------------------------------------------------
# In-memory TTL cache (per-topic) — thread-safe, per-process
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_cache: dict[str, dict] = {}  # topic -> {"ts": float, "payload": dict}


def _cache_get(topic: str) -> dict | None:
    with _cache_lock:
        entry = _cache.get(topic)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL_S:
            return entry["payload"]
    return None


def _cache_put(topic: str, payload: dict) -> None:
    with _cache_lock:
        _cache[topic] = {"ts": time.time(), "payload": payload}


def _cache_clear() -> None:
    """Test hook."""
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# Fetch + parse (stdlib only)
# ---------------------------------------------------------------------------
def _fetch_feed_bytes(url: str) -> bytes:
    """Single outbound call. Separated so tests can patch it deterministically."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as resp:
        return resp.read()


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_feed(xml_bytes: bytes, source_name: str) -> list[dict]:
    """Parse RSS 2.0 or Atom into normalised headline dicts.

    Every item keeps the publisher's own timestamp string verbatim —
    we display it, we don't reinterpret it.
    """
    root = ET.fromstring(xml_bytes)
    items: list[dict] = []

    # RSS 2.0
    for item in root.findall(".//item"):
        link = _text(item.find("link"))
        guid = item.find("guid")
        if not link and guid is not None and guid.get("isPermaLink", "true") == "true":
            link = _text(guid)
        title = _text(item.find("title"))
        if not title or not link:
            continue
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published": _text(item.find("pubDate")),
            "summary": re.sub(r"<[^>]+>", "", _text(item.find("description")))[:400],
        })
        if len(items) >= MAX_ITEMS_PER_FEED:
            return items

    # Atom
    for entry in root.findall(f"{ATOM_NS}entry"):
        title = _text(entry.find(f"{ATOM_NS}title"))
        link = ""
        for ln in entry.findall(f"{ATOM_NS}link"):
            if ln.get("rel", "alternate") == "alternate" and ln.get("href"):
                link = ln.get("href")
                break
        if not title or not link:
            continue
        published = _text(entry.find(f"{ATOM_NS}published")) or _text(entry.find(f"{ATOM_NS}updated"))
        summary = re.sub(r"<[^>]+>", "", _text(entry.find(f"{ATOM_NS}summary")))[:400]
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published": published,
            "summary": summary,
        })
        if len(items) >= MAX_ITEMS_PER_FEED:
            return items

    return items


def _gather_topic(topic: str) -> dict:
    """Fetch every feed for a topic in parallel; isolate failures honestly."""
    feeds = FEED_REGISTRY[topic]
    items: list[dict] = []
    feeds_ok: list[str] = []
    feeds_failed: list[dict] = []

    with ThreadPoolExecutor(max_workers=min(4, len(feeds))) as pool:
        futures = {pool.submit(_fetch_feed_bytes, f["url"]): f for f in feeds}
        for fut in as_completed(futures):
            feed = futures[fut]
            try:
                parsed = _parse_feed(fut.result(), feed["source"])
                if parsed:
                    feeds_ok.append(feed["source"])
                    items.extend(parsed)
                else:
                    feeds_failed.append({"source": feed["source"], "error": "parsed zero items"})
            except Exception as exc:  # noqa: BLE001 — failure is data, not a crash
                feeds_failed.append({"source": feed["source"], "error": type(exc).__name__})

    # Deduplicate by URL, preserve first-seen order (registry order = trust order)
    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        if it["url"] not in seen:
            seen.add(it["url"])
            deduped.append(it)

    return {
        "topic": topic,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cache_ttl_seconds": CACHE_TTL_S,
        "feeds_ok": feeds_ok,
        "feeds_failed": feeds_failed,
        "count": len(deduped),
        "items": deduped,
        "honesty": HONESTY_NOTE,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/topics")
def list_topics() -> dict:
    """What World Pulse covers, and how honestly it covers it."""
    return {
        "topics": sorted(FEED_REGISTRY.keys()),
        "feeds_per_topic": {t: [f["source"] for f in feeds] for t, feeds in FEED_REGISTRY.items()},
        "cache_ttl_seconds": CACHE_TTL_S,
        "honesty": HONESTY_NOTE,
    }


@router.get("/headlines")
def get_headlines(
    topic: str = Query("world", description="One of: " + ", ".join(sorted(FEED_REGISTRY))),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Live headlines for a topic. Fail-closed: 503 if no feed responds —
    an honest outage, never invented news."""
    topic = topic.strip().lower()
    if topic not in FEED_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown topic '{topic}'. Available: {', '.join(sorted(FEED_REGISTRY))}",
        )

    payload = _cache_get(topic)
    if payload is None:
        payload = _gather_topic(topic)
        if payload["count"] > 0:
            _cache_put(topic, payload)

    if payload["count"] == 0:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "news_unavailable",
                "message": "No news feed is reachable right now. Luqi-ai does not invent "
                           "headlines — try again shortly.",
                "feeds_failed": payload["feeds_failed"],
                "generated_at": payload["generated_at"],
            },
        )

    body = dict(payload)
    body["items"] = payload["items"][:limit]
    body["count"] = len(body["items"])
    body["returned_of"] = payload["count"]
    return body
