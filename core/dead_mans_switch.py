"""
OMEGA-LUQI Digital Legacy Guard (Dead Man's Switch).

Watches account inactivity over a configurable window. On breach, it does NOT
destroy or transfer anything automatically - it registers a task at the proven
30% Human Gate and alerts the configured trusted contact. Only an
authenticated human release executes the legacy directive (data escrow release
intent; sanitization only after explicit release). The sacred rule applies to
death too: no autonomous irreversible action.

Wire note: call touch(user_id) on login - hooked in auth.login below.
"""
import os
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .admin_auth import verify_admin
from .auth import LuqiAuthManager, UserSessionProfile

router = APIRouter(prefix="/v1/legacy", tags=["Digital Legacy Guard"])

_lock = threading.Lock()
_last_seen: Dict[str, float] = {}
_directives: Dict[str, Dict[str, Any]] = {}
DEFAULT_THRESHOLD_DAYS = float(os.getenv("LEGACY_THRESHOLD_DAYS", "90"))


def touch(user_id: str, now: Optional[float] = None) -> None:
    with _lock:
        _last_seen[user_id] = now if now is not None else time.time()


def configure(user_id: str, trusted_contact: str, note: str = "") -> Dict[str, Any]:
    with _lock:
        _directives[user_id] = {"trusted_contact": trusted_contact,
                                "note": note[:500],
                                "configured_at": time.time()}
    return {"configured": True}


def overdue_users(now: Optional[float] = None, threshold_days: float = None,
                  last_seen: Dict[str, float] = None, directives: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Pure inactivity analysis (inject clock/maps for tests)."""
    now = now if now is not None else time.time()
    threshold = (threshold_days if threshold_days is not None else DEFAULT_THRESHOLD_DAYS) * 86400
    seen = last_seen if last_seen is not None else _last_seen
    dirs = directives if directives is not None else _directives
    out = []
    for uid, directive in dirs.items():
        last = seen.get(uid)
        idle = (now - last) if last is not None else float("inf")
        if idle > threshold:
            out.append({"user_id": uid, "idle_days": round(idle / 86400, 1),
                        "trusted_contact": directive["trusted_contact"],
                        "note": directive.get("note", "")})
    return out


class LegacyConfig(BaseModel):
    trusted_contact: str = Field(..., min_length=5)  # phone for SMS alert
    note: str = ""


@router.post("/configure")
async def configure_legacy(cfg: LegacyConfig,
                           user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    touch(str(user.user_id))  # configuring counts as activity
    return configure(str(user.user_id), cfg.trusted_contact, cfg.note)


@router.get("/check")
async def check_legacy(is_authenticated: bool = Depends(verify_admin)):
    """Cron/cron-workflow target: find breached accounts, register gate tasks,
    alert trusted contacts. Never executes the directive itself."""
    from .main_types import LuqiState, TaskStatus
    from .state_store import get_state_store
    from .notifications import notify_gate_lock

    breached = overdue_users()
    registered = []
    for entry in breached:
        task = LuqiState(
            student_tier="legacy",
            action_type="execute_digital_legacy",
            payload={"item": f"Digital legacy directive for idle account {entry['user_id'][:8]}",
                     "user_id": entry["user_id"],
                     "trusted_contact": entry["trusted_contact"],
                     "note": entry["note"]},
        )
        task.status = TaskStatus.PENDING_HUMAN_APPROVAL
        task.required_human_action = (
            "Digital legacy threshold breached. Review the directive; release executes the "
            "documented intent ONLY (contact alert now; data actions per the note, proposal-first)."
        )
        get_state_store().set(task.task_id, task)
        notify_gate_lock(task)
        try:
            from .context_sync import broadcast_legacy_trip
            broadcast_legacy_trip(entry)
        except Exception:
            pass  # ops-channel alert never blocks the guard
        registered.append({"user_id": entry["user_id"][:8] + "...",
                           "idle_days": entry["idle_days"],
                           "gate_task_id": str(task.task_id)})
    return {"breached_accounts": len(breached), "gate_tasks_registered": registered,
            "safety_note": "No autonomous action: directives execute only via the 30% human gate."}


@router.get("/status")
async def legacy_status(user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    uid = str(user.user_id)
    with _lock:
        last = _last_seen.get(uid)
        directive = dict(_directives.get(uid, {}))
    return {"last_seen_days_ago": round((time.time() - last) / 86400, 1) if last else None,
            "threshold_days": DEFAULT_THRESHOLD_DAYS,
            "directive_configured": bool(directive),
            "trusted_contact": directive.get("trusted_contact", "(not configured)")}
