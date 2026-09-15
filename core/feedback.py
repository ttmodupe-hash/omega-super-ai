"""
OMEGA-LUQI Feedback Loop - capture outcomes so systems CAN learn later.

Closes the 'learn from interactions' gap at its honest first step: capture.
Every engine response can be rated; aggregates per target power the future
improvement loop. Stated plainly: this collects the signal - the learning
loop that consumes it is a separate, deliberate build.
"""
import threading
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .admin_auth import verify_admin
from .auth import LuqiAuthManager, UserSessionProfile
from .pii_scrub import scrub_pii

router = APIRouter(prefix="/v1/feedback", tags=["Feedback Loop"])

_entries: List[Dict[str, Any]] = []
_lock = threading.Lock()


class FeedbackEntry(BaseModel):
    target: str = Field(min_length=1)          # e.g. "pedagogy", "voice", "dev_agent"
    rating: int = Field(ge=1, le=5)            # clamped by schema
    comment: str = ""


def submit_feedback(user_id: str, entry: FeedbackEntry) -> Dict[str, Any]:
    with _lock:
        _entries.append({"user_id": user_id, "target": entry.target[:50],
                         "rating": entry.rating,
                         "comment": scrub_pii(entry.comment)[:500],
                         "at": time.time()})
    return {"recorded": True}


def feedback_summary() -> Dict[str, Any]:
    with _lock:
        entries = list(_entries)
    by_target: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        agg = by_target.setdefault(e["target"], {"count": 0, "total_rating": 0})
        agg["count"] += 1
        agg["total_rating"] += e["rating"]
    for agg in by_target.values():
        agg["average_rating"] = round(agg["total_rating"] / agg["count"], 2)
        del agg["total_rating"]
    return {"total_entries": len(entries), "by_target": by_target}


@router.post("/submit")
async def submit(entry: FeedbackEntry,
                 user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    return submit_feedback(str(user.user_id), entry)


@router.get("/summary")
async def summary(is_authenticated: bool = Depends(verify_admin)):
    return feedback_summary()
