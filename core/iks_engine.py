"""Indigenous Knowledge Systems (IKS) Ethnobotanical Archive Engine (IKS-1).

A curated, sourced, deterministic registry of documented Southern African
traditional plant knowledge: historical usage, honest research status,
cautions, and the intellectual-property record of the communities who
carried the knowledge.

Design laws (same as Scam Shield, HERITAGE-1, and the History Archive):
- Zero external calls, zero LLM, zero cost — answers are identical every time.
- Anti-hallucination: every entry carries at least two named, checkable
  sources. Content that cannot be sourced does not ship.
- Catalogue, not clinic: entries document what the ethnobotanical literature
  records — never what a person should take. The disclaimer and guardrails
  travel with every response.
- Scam-aware: entries exploited by miracle-cure sellers carry a scam_alert
  field, tying the archive to the platform's core mission.
- Fail-closed: if the data file is missing or malformed, the endpoints raise
  rather than serve degraded content.
- Versioned data file (core/data/iks_archive.json) — content changes are
  reviewable, diffable history themselves.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/iks", tags=["iks-archive"])

_DATA_FILE = Path(__file__).resolve().parent / "data" / "iks_archive.json"

_SUMMARY_FIELDS = ("id", "category", "title", "latin_name", "region", "summary")

_REQUIRED_FIELDS = ("id", "category", "title", "latin_name", "region",
                    "summary", "traditional_use", "modern_research_note",
                    "cautions", "key_points", "sources")


class IksQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None  # restrict to one category


def _load_archive() -> Dict[str, Any]:
    """Load the versioned archive. Fail-closed, like the med study pack."""
    if not _DATA_FILE.exists():
        raise RuntimeError(f"iks archive missing: {_DATA_FILE}")
    data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("entries"):
        raise RuntimeError("iks archive is malformed (needs version + entries)")
    if not data.get("disclaimer"):
        raise RuntimeError("iks archive has no disclaimer — the honesty law applies")
    if not data.get("guardrails"):
        raise RuntimeError("iks archive has no guardrails — the boundary law applies")
    seen = set()
    for entry in data["entries"]:
        for field in _REQUIRED_FIELDS:
            if not entry.get(field):
                raise RuntimeError(f"iks entry '{entry.get('id')}' missing '{field}'")
        if entry["id"] in seen:
            raise RuntimeError(f"iks entry id duplicated: '{entry['id']}'")
        seen.add(entry["id"])
        if len(entry.get("sources", [])) < 2:
            raise RuntimeError(f"iks entry '{entry['id']}' has fewer than 2 sources — "
                               "the anti-hallucination law applies to botany too")
        if not entry.get("cautions"):
            raise RuntimeError(f"iks entry '{entry['id']}' has no cautions — "
                               "the boundary law applies: catalogue, not clinic")
        if entry["category"] not in data.get("categories", []):
            raise RuntimeError(f"iks entry '{entry['id']}' uses an unlisted category")
    return data


def _summary(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {k: entry[k] for k in _SUMMARY_FIELDS}


_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "who", "what",
    "when", "where", "was", "were", "did", "does", "how", "why", "are",
    "is", "of", "in", "on", "a", "an", "to", "tell", "about", "show",
    "used", "use",
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
            e["title"], e["summary"], e["latin_name"], e["region"], e["category"],
            " ".join(e.get("vernacular_names", [])),
            " ".join(e.get("traditional_use", [])),
            " ".join(e.get("key_points", [])),
            " ".join(e.get("sources", [])),
            e.get("modern_research_note", ""),
        ]).lower()
        score = sum(1 for n in needles if n in haystack)
        if score >= min_score:
            hits.append((score, e))
    hits.sort(key=lambda t: (-t[0], t[1]["id"]))
    return [e for _, e in hits]


@router.get("")
async def archive_overview() -> Dict[str, Any]:
    """Archive card: version, coverage, guardrails, and the honesty note."""
    data = _load_archive()
    return {
        "name": data["name"],
        "version": data["version"],
        "updated": data["updated"],
        "entry_count": len(data["entries"]),
        "categories": data["categories"],
        "description": data["description"],
        "guardrails": data["guardrails"],
        "disclaimer": data["disclaimer"],
    }


@router.get("/entries")
async def list_entries(
    category: Optional[str] = Query(None, description="filter by category"),
    q: Optional[str] = Query(None, max_length=200, description="free-text search"),
) -> Dict[str, Any]:
    """List archive entries, optionally filtered by category or free text."""
    data = _load_archive()
    entries = data["entries"]
    if category:
        if category not in data["categories"]:
            raise HTTPException(
                status_code=400,
                detail=f"unknown category '{category}' — valid: {data['categories']}",
            )
        entries = [e for e in entries if e["category"] == category]
    if q:
        entries = _search(entries, q)
    return {"count": len(entries), "disclaimer": data["disclaimer"],
            "entries": [_summary(e) for e in entries]}


@router.get("/entries/{entry_id}")
async def entry_detail(entry_id: str) -> Dict[str, Any]:
    """Full entry: usage record, research status, cautions, sources."""
    data = _load_archive()
    for e in data["entries"]:
        if e["id"] == entry_id:
            return {**e, "disclaimer": data["disclaimer"]}
    raise HTTPException(
        status_code=404,
        detail=f"no iks entry '{entry_id}' — list them all at /v1/iks/entries",
    )


@router.post("/query")
async def query_iks(payload: IksQuery) -> Dict[str, Any]:
    """Cross-reference a question against the curated archive.

    Honest contract: this endpoint returns matching CURATED entries with
    their sources. It never invents a remedy. When nothing matches, it says
    so and points at Deep Research for sourced expansion.
    """
    data = _load_archive()
    entries = data["entries"]
    if payload.category:
        if payload.category not in data["categories"]:
            raise HTTPException(
                status_code=400,
                detail=f"unknown category '{payload.category}' — valid: {data['categories']}",
            )
        entries = [e for e in entries if e["category"] == payload.category]

    matches = _search(entries, payload.query)
    if not matches:
        return {
            "status": "no_curated_match",
            "query": payload.query,
            "matches": [],
            "honest_note": "No curated archive entry matches this query. "
                           "Rather than fabricate a remedy, the archive stays silent.",
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
        "boundary": "Catalogue, not clinic: this archive documents recorded "
                    "traditional use. It cannot evaluate your health, "
                    "prescribe, or recommend doses.",
        "how_to_verify": "Open any entry at /v1/iks/entries/{id} — every "
                         "claim carries named sources you can check.",
        "disclaimer": data["disclaimer"],
    }
