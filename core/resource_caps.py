"""
OMEGA-LUQI Free-Tier Token & Session Cap Enforcement

The subsidy model's biggest financial risk: unchecked free-tier usage of
expensive Kimi K3 loops. This module caps autonomous agent sessions per user
per day for subsidized tiers (primary / high_school / tvet).

Design rules:
  - Per-user keys (JWT identity when present, anonymous fallback) - never a
    single global counter.
  - Date-bucketed: counters reset daily without a cron job.
  - CRITICAL_ACTIONS are EXEMPT: payment attempts halt at the 30% gate and
    cost nothing to queue; capping them would break gate integrity tests and
    block legitimate settlements.
  - Memory dict for single-node; swap for Redis counters in multi-node.
"""
import os
import threading
from datetime import date
from typing import Optional

from fastapi import HTTPException, status, Request

FREE_TIER_TIERS = {"primary", "high_school", "tvet"}
MAX_FREE_DAILY_SESSIONS = int(os.getenv("MAX_FREE_DAILY_SESSIONS", "5"))

_counters: dict = {}
_lock = threading.Lock()


def _extract_user_key(request: Optional[Request]) -> Optional[str]:
    """JWT identity when a valid bearer is present; None when unauthenticated
    (the caller's own student_id is then used as the bucket key)."""
    if request is None:
        return None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from .auth import LuqiAuthManager, is_token_revoked
            token = auth.split(" ", 1)[1]
            if is_token_revoked(token):
                return "anonymous"
            class _Creds:
                credentials = token
            return str(LuqiAuthManager.verify_session_token(_Creds()).user_id)
        except Exception:
            return "anonymous"
    return "anonymous"


def enforce_free_tier_resource_caps(
    student_id: str,
    tier: str,
    action_type: str,
    critical_actions: set,
    request: Optional[Request] = None,
) -> None:
    """Raise 429 when a subsidized tier exceeds its daily autonomous allocation."""
    if tier not in FREE_TIER_TIERS:
        return
    if action_type in critical_actions:
        return  # gate-halted actions cost nothing to queue

    # JWT identity wins; otherwise the caller-supplied student_id scopes the
    # bucket per user - never one shared anonymous counter.
    identity = _extract_user_key(request) or student_id or "anonymous"
    key = f"{identity}:{date.today().isoformat()}"
    with _lock:
        usage = _counters.get(key, 0)
        if usage >= MAX_FREE_DAILY_SESSIONS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Resource Cap Exceeded: daily free laboratory allocation reached. "
                    "Upgrade to University or Global Premium tier for unlimited high-capacity processing."
                ),
            )
        _counters[key] = usage + 1
