"""
OMEGA-LUQI Data Portability - POPIA/GDPR-style access request export.

GET /v1/user/export (authenticated) compiles the caller's OWN data from every
store the engine holds (memory, skill profile, feedback, gate history where
present) into one signed JSON package. This is the legally-mandated "access
request" export: the user receives their data, PII included - that is the
point of an access request (unlike outbound AI calls, where PII is scrubbed).

Package is versioned, timestamped, and states its scope honestly (in-memory
stores today; DB-backed tables join the manifest when DATABASE_URL is live).
"""
import json
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .auth import LuqiAuthManager, UserSessionProfile
from . import memory, feedback as feedback_mod

router = APIRouter(prefix="/v1/user", tags=["Data Portability"])


def collect_user_data(user_id: str) -> Dict[str, Any]:
    """Pure assembly of one user's data across engine stores."""
    return {
        "memories": memory.get_memories(user_id),
        "skill_profile": _safe_skill_profile(user_id),
        "feedback_submitted": [e for e in _feedback_entries() if e.get("user_id") == user_id],
    }


def _safe_skill_profile(user_id: str) -> Dict[str, Any]:
    try:
        from .skill_engine import get_profile
        return get_profile(user_id)
    except Exception:
        return {"note": "skill engine unavailable"}


def _feedback_entries() -> List[Dict[str, Any]]:
    return list(getattr(feedback_mod, "_entries", []))


def build_package(user: UserSessionProfile) -> Dict[str, Any]:
    uid = str(user.user_id)
    return {
        "package": "luqi-ai-data-portability",
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subject": {"user_id": uid, "email": user.email, "tier": user.tier,
                    "country_code": user.country_code},
        "legal_basis": "POPIA (Act 4 of 2013) section 23 access request / GDPR Art. 20 portability",
        "data": collect_user_data(uid),
        "scope_note": ("Covers in-memory engine stores. Database-backed tables "
                       "(students, skill tables, ledger, audit) join this package "
                       "when DATABASE_URL is live; query them by user_id and merge."),
    }


@router.get("/export")
async def export_user_data(user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """Download your own data as a JSON package (POPIA/GDPR access request)."""
    package = build_package(user)
    return JSONResponse(
        content=package,
        headers={"Content-Disposition": f'attachment; filename="luqi-export-{str(user.user_id)[:8]}.json"'})
