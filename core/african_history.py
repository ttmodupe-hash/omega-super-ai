"""African History Archive (ARCHIVE-1).

A curated, sourced, deterministic archive of African history — civilizations,
leaders, resistance, liberation, heritage, knowledge, turning points.

Design laws (same as Scam Shield):
- Zero external calls, zero LLM, zero cost — answers are identical every time.
- Anti-hallucination: every entry carries real, verifiable references
  (UNESCO General History of Africa, UNESCO World Heritage List, primary
  sources, standard scholarly works). Contested history is presented AS a
  debate (see mfecane, goree) — never as settled fiction.
- Fail-closed: if the archive file is missing or malformed, the endpoints
  raise rather than serve degraded history.
- Versioned data file (core/data/african_history.json) — content changes are
  reviewable, diffable history themselves.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/history", tags=["african-history-archive"])

_ARCHIVE_FILE = Path(__file__).resolve().parent / "data" / "african_history.json"

_SUMMARY_FIELDS = ("id", "title", "category", "region", "start_year", "period", "summary")


def _load_archive() -> Dict[str, Any]:
    """Load the versioned archive. Fail-closed, like the scam catalogue."""
    if not _ARCHIVE_FILE.exists():
        raise RuntimeError(f"african history archive missing: {_ARCHIVE_FILE}")
    data = json.loads(_ARCHIVE_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("entries"):
        raise RuntimeError("african history archive is malformed (needs version + entries)")
    for ent in data["entries"]:
        if len(ent.get("sources", [])) < 2:
            raise RuntimeError(f"archive entry '{ent.get('id')}' has fewer than 2 sources — "
                               "the anti-hallucination law applies to history too")
    return data


def _summary(ent: Dict[str, Any]) -> Dict[str, Any]:
    return {k: ent[k] for k in _SUMMARY_FIELDS}


def _search(entries: List[Dict[str, Any]], q: str) -> List[Dict[str, Any]]:
    needle = q.strip().lower()
    return [e for e in entries
            if needle in (e["title"] + " " + e["summary"] + " " + e["significance"]
                          + " " + e["region"] + " " + e["category"]).lower()]


@router.get("")
async def archive_overview() -> Dict[str, Any]:
    """Archive card: version, coverage, and the honesty note."""
    data = _load_archive()
    return {
        "name": "LUQI African History Archive",
        "version": data["version"],
        "updated": data["updated"],
        "entry_count": len(data["entries"]),
        "categories": data["categories"],
        "regions": data["regions"],
        "description": data["description"],
        "disclaimer": ("Curated educational content with verifiable references — "
                       "check the sources yourself. History that is still debated "
                       "is labelled as debate, not presented as settled fact."),
    }


@router.get("/entries")
async def list_entries(
    category: Optional[str] = Query(None, description="filter by category"),
    region: Optional[str] = Query(None, description="filter by region"),
    q: Optional[str] = Query(None, max_length=200, description="free-text search"),
) -> Dict[str, Any]:
    """List entries, optionally filtered by category, region, or free text."""
    entries = _load_archive()["entries"]
    if category:
        entries = [e for e in entries if e["category"].lower() == category.strip().lower()]
    if region:
        entries = [e for e in entries if e["region"].lower() == region.strip().lower()]
    if q:
        entries = _search(entries, q)
    return {"count": len(entries), "entries": [_summary(e) for e in entries]}


@router.get("/timeline")
async def timeline() -> Dict[str, Any]:
    """The full archive ordered by start_year (BCE is negative) — the sweep
    from Kush to 1994 in one call."""
    entries = sorted(_load_archive()["entries"], key=lambda e: e["start_year"])
    return {"count": len(entries), "entries": [_summary(e) for e in entries]}


@router.get("/entries/{entry_id}")
async def entry_detail(entry_id: str) -> Dict[str, Any]:
    """Full entry including significance and the source list."""
    for ent in _load_archive()["entries"]:
        if ent["id"] == entry_id:
            return ent
    raise HTTPException(
        status_code=404,
        detail=f"no archive entry '{entry_id}' — list them all at /v1/history/entries",
    )
