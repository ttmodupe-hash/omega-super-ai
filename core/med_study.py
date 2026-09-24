"""Medical Study Pack (MED-1).

A curated, sourced, deterministic study pack for medical students — high-yield
topics with key points, self-test questions, and verifiable references.
Built for understanding faster: every topic is a concept map you can quiz
yourself against, and the free sources come first (OpenStax, StatPearls,
Merck Manual, WHO) — knowledge without a paywall.

Design laws (same as Scam Shield and the African History Archive):
- Zero external calls, zero LLM, zero cost — answers are identical every time.
- Anti-hallucination: every topic carries at least two real, verifiable
  sources; content that cannot be verified does not ship.
- Study aid, never medical advice: the disclaimer travels with every response.
- Fail-closed: if the data file is missing or malformed, the endpoints raise
  rather than serve degraded medicine.
- Versioned data file (core/data/med_study.json) — content changes are
  reviewable, diffable history themselves.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/medstudy", tags=["medical-study-pack"])

_DATA_FILE = Path(__file__).resolve().parent / "data" / "med_study.json"

_SUMMARY_FIELDS = ("id", "title", "system", "level", "summary")

_REQUIRED_FIELDS = ("id", "title", "system", "level", "summary", "key_points",
                    "self_test", "sources")


def _load_pack() -> Dict[str, Any]:
    """Load the versioned study pack. Fail-closed, like the scam catalogue."""
    if not _DATA_FILE.exists():
        raise RuntimeError(f"medical study pack missing: {_DATA_FILE}")
    data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("topics"):
        raise RuntimeError("medical study pack is malformed (needs version + topics)")
    if not data.get("disclaimer"):
        raise RuntimeError("medical study pack has no disclaimer — the honesty law applies")
    for topic in data["topics"]:
        for field in _REQUIRED_FIELDS:
            if not topic.get(field):
                raise RuntimeError(f"med study topic '{topic.get('id')}' missing '{field}'")
        if len(topic.get("sources", [])) < 2:
            raise RuntimeError(f"med study topic '{topic.get('id')}' has fewer than 2 sources — "
                               "the anti-hallucination law applies to medicine too")
        if topic["system"] not in data.get("systems", []):
            raise RuntimeError(f"med study topic '{topic.get('id')}' uses an unlisted system")
    return data


def _summary(topic: Dict[str, Any]) -> Dict[str, Any]:
    return {k: topic[k] for k in _SUMMARY_FIELDS}


def _search(topics: List[Dict[str, Any]], q: str) -> List[Dict[str, Any]]:
    needle = q.strip().lower()
    return [t for t in topics
            if needle in (t["title"] + " " + t["summary"] + " " + t["system"] + " "
                          + " ".join(t.get("key_points", []))).lower()]


@router.get("")
async def pack_overview() -> Dict[str, Any]:
    """Pack card: version, coverage, and the honesty note."""
    data = _load_pack()
    return {
        "name": data["name"],
        "version": data["version"],
        "updated": data["updated"],
        "topic_count": len(data["topics"]),
        "systems": data["systems"],
        "description": data["description"],
        "disclaimer": data["disclaimer"],
    }


@router.get("/topics")
async def list_topics(
    system: Optional[str] = Query(None, description="filter by body system"),
    level: Optional[str] = Query(None, description="filter by study level"),
    q: Optional[str] = Query(None, max_length=200, description="free-text search"),
) -> Dict[str, Any]:
    """List topics, optionally filtered by system, level, or free text."""
    data = _load_pack()
    topics = data["topics"]
    if system:
        topics = [t for t in topics if t["system"].lower() == system.strip().lower()]
    if level:
        topics = [t for t in topics if t["level"].lower() == level.strip().lower()]
    if q:
        topics = _search(topics, q)
    return {"count": len(topics), "disclaimer": data["disclaimer"],
            "topics": [_summary(t) for t in topics]}


@router.get("/self-test")
async def self_test(
    system: Optional[str] = Query(None, description="limit questions to one body system"),
) -> Dict[str, Any]:
    """Rapid-revision mode: every self-test question flattened into one deck,
    optionally per system. Questions carry their topic id so a wrong answer
    points back to the full explanation."""
    data = _load_pack()
    deck = []
    for t in data["topics"]:
        if system and t["system"].lower() != system.strip().lower():
            continue
        for item in t["self_test"]:
            deck.append({"topic_id": t["id"], "topic": t["title"], "system": t["system"],
                         "q": item["q"], "a": item["a"]})
    return {"count": len(deck), "disclaimer": data["disclaimer"], "deck": deck}


@router.get("/topics/{topic_id}")
async def topic_detail(topic_id: str) -> Dict[str, Any]:
    """Full topic: summary, key points, self-test, clinical pearl, sources."""
    data = _load_pack()
    for t in data["topics"]:
        if t["id"] == topic_id:
            return {**t, "disclaimer": data["disclaimer"]}
    raise HTTPException(
        status_code=404,
        detail=f"no med study topic '{topic_id}' — list them all at /v1/medstudy/topics",
    )
