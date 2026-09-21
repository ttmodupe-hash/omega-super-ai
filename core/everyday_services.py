"""Everyday Services Pack (SERVICES-1).

Plain-language guides to the government services South Africans ask about
most: SASSA grants, the SRD R370 grant, SARS tax, UIF and NSFAS.

Design laws (same as Scam Shield + African History Archive):
- Zero external calls, zero LLM, zero cost — answers are identical every time.
- Anti-hallucination: every entry is built from official sources only
  (gov.za, sassa.gov.za, sars.gov.za, labour.gov.za, nsfas.org.za) and carries
  at least two verifiable references. Volatile facts (amounts, dates) say when
  they were verified and point at the official channel to confirm.
- Scam-first: every entry names the fraud angle, because these services are
  where people get robbed most. Cross-links to Scam Shield.
- Fail-closed: if the pack file is missing or malformed, the endpoints raise
  rather than serve degraded guidance.
- Versioned data file (core/data/everyday_services.json) — content changes
  are reviewable, diffable history.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/v1/services", tags=["everyday-services"])

_PACK_FILE = Path(__file__).resolve().parent / "data" / "everyday_services.json"

_SUMMARY_FIELDS = ("id", "title", "category", "agency", "summary")


def _load_pack() -> Dict[str, Any]:
    """Load the versioned pack. Fail-closed, like the scam catalogue."""
    if not _PACK_FILE.exists():
        raise RuntimeError(f"everyday services pack missing: {_PACK_FILE}")
    data = json.loads(_PACK_FILE.read_text(encoding="utf-8"))
    if not data.get("version") or not data.get("entries"):
        raise RuntimeError("everyday services pack is malformed (needs version + entries)")
    for ent in data["entries"]:
        if len(ent.get("sources", [])) < 2:
            raise RuntimeError(f"services entry '{ent.get('id')}' has fewer than 2 sources — "
                               "the anti-hallucination law applies to services too")
    return data


def _summary(ent: Dict[str, Any]) -> Dict[str, Any]:
    return {k: ent[k] for k in _SUMMARY_FIELDS}


def _search(entries: List[Dict[str, Any]], q: str) -> List[Dict[str, Any]]:
    needle = q.strip().lower()
    return [e for e in entries
            if needle in (e["title"] + " " + e["summary"] + " " + e["agency"]
                          + " " + e["category"] + " "
                          + " ".join(e.get("steps", []))).lower()]


@router.get("")
async def pack_overview() -> Dict[str, Any]:
    """Pack card: version, coverage, and the honesty note."""
    data = _load_pack()
    return {
        "name": "LUQI Everyday Services Pack",
        "version": data["version"],
        "updated": data["updated"],
        "entry_count": len(data["entries"]),
        "categories": data["categories"],
        "agencies": data["agencies"],
        "description": data["description"],
        "disclaimer": ("Guidance built from official sources with a verified-on date — "
                       "amounts and dates change, so confirm on the official channel named "
                       "in each entry. Educational information only, not legal or "
                       "financial advice."),
    }


@router.get("/entries")
async def list_entries(
    category: Optional[str] = Query(None, description="filter by category"),
    agency: Optional[str] = Query(None, description="filter by agency"),
    q: Optional[str] = Query(None, max_length=200, description="free-text search"),
) -> Dict[str, Any]:
    """List entries, optionally filtered by category, agency, or free text."""
    entries = _load_pack()["entries"]
    if category:
        entries = [e for e in entries if e["category"].lower() == category.strip().lower()]
    if agency:
        entries = [e for e in entries if e["agency"].lower() == agency.strip().lower()]
    if q:
        entries = _search(entries, q)
    return {"count": len(entries), "entries": [_summary(e) for e in entries]}


@router.get("/entries/{entry_id}")
async def entry_detail(entry_id: str) -> Dict[str, Any]:
    """Full entry: steps, official channels, scam warning, sources."""
    for ent in _load_pack()["entries"]:
        if ent["id"] == entry_id:
            return ent
    raise HTTPException(
        status_code=404,
        detail=f"no services entry '{entry_id}' — list them all at /v1/services/entries",
    )
