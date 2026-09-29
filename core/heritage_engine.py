"""Sovereign Heritage & Theological Archive Engine (HERITAGE-1).

A curated, sourced, deterministic archive spanning the Ethiopian canon and
Ge'ez manuscript tradition, Islamic verification science and Golden Age
scholarship, and deep human history in Africa.

Design laws (same as Scam Shield, MED-1, and the African History Archive):
- Zero external calls, zero LLM, zero cost — answers are identical every time.
- Anti-hallucination: every entry carries at least two real, checkable
  primary sources, and contested claims carry their scholarly caveat in the
  open (see scholarly_note fields). Content that cannot be verified does not
  ship.
- Archive, not authority: the disclaimer travels with every response. This is
  a study index pointing to primary sources, never a religious ruling.
- Fail-closed: if the data file is missing or malformed, the endpoints raise
  rather than serve degraded history.
- Versioned data file (core/data/heritage_archive.json) — content changes
  are reviewable, diffable history themselves.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/heritage", tags=["heritage-archive"])

_DATA_FILE = Path(__file__).resolve().parent / "data" / "heritage_archive.json"

_SUMMARY_FIELDS = ("id", "tradition", "title", "era", "region", "summary")

_REQUIRED_FIELDS = ("id", "tradition", "title", "era", "region", "summary",
                    "key_points", "primary_sources")


class HeritageQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    tradition: Optional[str] = None  # restrict to one tradition


def _load_archive() -> Dict[str, Any]:
    """Load the versioned archive. Fail-closed, like the med study pack."""
    if not _DATA_FILE.exists():
        raise RuntimeError(f"heritage archive missing: {_DATA_FILE}")
    data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("entries"):
        raise RuntimeError("heritage archive is malformed (needs version + entries)")
    if not data.get("disclaimer"):
        raise RuntimeError("heritage archive has no disclaimer — the honesty law applies")
    seen = set()
    for entry in data["entries"]:
        for field in _REQUIRED_FIELDS:
            if not entry.get(field):
                raise RuntimeError(f"heritage entry '{entry.get('id')}' missing '{field}'")
        if entry["id"] in seen:
            raise RuntimeError(f"heritage entry id duplicated: '{entry['id']}'")
        seen.add(entry["id"])
        if len(entry.get("primary_sources", [])) < 2:
            raise RuntimeError(f"heritage entry '{entry['id']}' has fewer than 2 sources — "
                               "the anti-hallucination law applies to history too")
        if entry["tradition"] not in data.get("traditions", []):
            raise RuntimeError(f"heritage entry '{entry['id']}' uses an unlisted tradition")
    return data


def _summary(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {k: entry[k] for k in _SUMMARY_FIELDS}


_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "who", "what",
    "when", "where", "was", "were", "did", "does", "how", "why", "are",
    "is", "of", "in", "on", "a", "an", "to", "tell", "about", "show",
})


def _search(entries: List[Dict[str, Any]], q: str) -> List[Dict[str, Any]]:
    """Deterministic keyword matching over every searchable field. No LLM,
    no ranking voodoo — the same query always returns the same entries.
    Stop words are dropped and a multi-term query must hit at least two
    distinctive terms, so generic phrasing cannot flood the result set."""
    needles = [w.strip("?.,!'\"*") for w in q.strip().lower().split()]
    needles = [w for w in needles if len(w) > 2 and w not in _STOP_WORDS]
    if not needles:
        return []
    min_score = 2 if len(needles) >= 2 else 1
    hits = []
    for e in entries:
        haystack = " ".join([
            e["title"], e["summary"], e["era"], e["region"], e["tradition"],
            " ".join(e.get("key_points", [])),
            " ".join(e.get("primary_sources", [])),
            e.get("scholarly_note", ""),
        ]).lower()
        score = sum(1 for n in needles if n in haystack)
        if score >= min_score:
            hits.append((score, e))
    hits.sort(key=lambda t: (-t[0], t[1]["id"]))
    return [e for _, e in hits]


@router.get("")
async def archive_overview() -> Dict[str, Any]:
    """Archive card: version, coverage, and the honesty note."""
    data = _load_archive()
    return {
        "name": data["name"],
        "version": data["version"],
        "updated": data["updated"],
        "entry_count": len(data["entries"]),
        "traditions": data["traditions"],
        "description": data["description"],
        "disclaimer": data["disclaimer"],
    }


@router.get("/entries")
async def list_entries(
    tradition: Optional[str] = Query(None, description="filter by tradition"),
    q: Optional[str] = Query(None, max_length=200, description="free-text search"),
) -> Dict[str, Any]:
    """List archive entries, optionally filtered by tradition or free text."""
    data = _load_archive()
    entries = data["entries"]
    if tradition:
        if tradition not in data["traditions"]:
            raise HTTPException(
                status_code=400,
                detail=f"unknown tradition '{tradition}' — valid: {data['traditions']}",
            )
        entries = [e for e in entries if e["tradition"] == tradition]
    if q:
        entries = _search(entries, q)
    return {"count": len(entries), "disclaimer": data["disclaimer"],
            "entries": [_summary(e) for e in entries]}


@router.get("/entries/{entry_id}")
async def entry_detail(entry_id: str) -> Dict[str, Any]:
    """Full entry: summary, key points, primary sources, scholarly caveats."""
    data = _load_archive()
    for e in data["entries"]:
        if e["id"] == entry_id:
            return {**e, "disclaimer": data["disclaimer"]}
    raise HTTPException(
        status_code=404,
        detail=f"no heritage entry '{entry_id}' — list them all at /v1/heritage/entries",
    )


@router.post("/query")
async def query_heritage(payload: HeritageQuery) -> Dict[str, Any]:
    """Cross-reference a question against the curated archive.

    Honest contract: this endpoint returns matching CURATED entries with their
    sources. It never invents a verdict. When nothing matches, it says so and
    points at Deep Research for sourced expansion.
    """
    data = _load_archive()
    entries = data["entries"]
    if payload.tradition:
        if payload.tradition not in data["traditions"]:
            raise HTTPException(
                status_code=400,
                detail=f"unknown tradition '{payload.tradition}' — valid: {data['traditions']}",
            )
        entries = [e for e in entries if e["tradition"] == payload.tradition]

    matches = _search(entries, payload.query)
    if not matches:
        return {
            "status": "no_curated_match",
            "query": payload.query,
            "matches": [],
            "honest_note": "No curated archive entry matches this query. "
                           "Rather than fabricate an answer, the archive stays silent.",
            "escalation": {
                "available": True,
                "endpoint": "/v1/deep-research",
                "note": "Deep Research retrieves real external sources for uncovered topics.",
            },
            "disclaimer": data["disclaimer"],
        }
    return {
        "status": "success",
        "query": payload.query,
        "match_count": len(matches),
        "matches": [_summary(e) for e in matches],
        "how_to_verify": "Open any entry at /v1/heritage/entries/{id} — every "
                         "claim carries named primary sources you can check.",
        "disclaimer": data["disclaimer"],
    }
