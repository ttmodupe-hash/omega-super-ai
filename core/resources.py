"""
API-CATALOG-1 — curated free-API resource catalogue (GET /v1/resources/free-apis).

Serves the adjudicated, sandbox-verified catalogue of free data APIs that
serve the mission (finance literacy, education, agriculture). Pattern follows
finlit.py: versioned JSON in core/data/, loaded once, served read-only.

Honesty contract (enforced by tests/verify_free_apis.py):
  - verified_no_key entries must carry sandbox_verified=true + verified_on.
  - free_key_tier entries are honestly labelled (registration required).
  - No betting/gambling content — anti-mission.
"""
import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/v1/resources", tags=["resources"])

_CATALOGUE_FILE = Path(__file__).resolve().parent / "data" / "free_apis.json"


def load_catalogue() -> Dict[str, Any]:
    """Load the versioned catalogue. Fail-closed: a missing/corrupt catalogue
    is a server error, never a silently empty list."""
    return json.loads(_CATALOGUE_FILE.read_text(encoding="utf-8"))


@router.get("/free-apis")
async def free_apis() -> Dict[str, Any]:
    """The curated free-API catalogue with honest verification metadata."""
    cat = load_catalogue()
    return {
        **cat,
        "served_meta": {
            "verified_no_key_count": len(cat["verified_no_key"]),
            "free_key_tier_count": len(cat["free_key_tier"]),
            "rejected_groups": len(cat["rejected_from_source"]),
            "note": "Curated under house law: mission-aligned, sandbox-verified "
                    "where claimed, betting/odds content rejected as anti-mission.",
        },
    }
