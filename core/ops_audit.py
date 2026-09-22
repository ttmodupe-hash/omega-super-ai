"""
OMEGA-LUQI Ops Audit & Telemetry (Batch F) - one admin feed for the Ops Console.

The console polls this endpoint (every 3s while an admin key is set) to render
live ticket states, recent task runs, sandbox counters, and the durable journal
tail without page refreshes.

Security rules:
  - admin-gated like every ops surface (verify_admin)
  - ticket snapshots NEVER include the HMAC token - tokens are credentials and
    stay off the wire (request/notify paths excepted, where they ARE the payload)
  - cheap to poll: the sandbox meter dict is copied as-is; we do NOT call
    metrics(), which pings the Docker daemon on every invocation
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from .admin_auth import verify_admin
from . import ops_approvals, ops_journal, sandbox_runner, task_runner

router = APIRouter(prefix="/v1/ops", tags=["Ops Audit"])

START_TS = time.time()
MAX_LIMIT = 200


@router.get("/audit")
async def get_ops_audit_log(limit: int = 50, _: bool = Depends(verify_admin)) -> dict:
    """Live snapshot: tickets (token-free), recent runs, sandbox counters, journal tail."""
    limit = max(1, min(limit, MAX_LIMIT))
    entries = ops_journal.read_recent(limit)
    tickets = [
        {"ticket_id": t["ticket_id"], "action_type": t["action_type"],
         "summary": t["summary"], "status": t["status"],
         "created": t["created"], "expires": t["expires"],
         "decided_by": t.get("decided_by"), "decided_at": t.get("decided_at")}
        for t in sorted(ops_approvals._tickets.values(), key=lambda x: x["created"])
    ]
    return {
        "status": "active",
        "uptime_s": round(time.time() - START_TS, 1),
        "journal_enabled": ops_journal.ENABLED,
        "journal_write_errors": ops_journal.write_errors[-10:],
        "tickets": tickets[-50:],
        "recent_runs": [{k: v for k, v in r.items() if k != "result"}
                        for r in task_runner._runs[-10:]],
        "sandbox": dict(sandbox_runner._meter),
        "total_records": len(entries),
        "audit_trail": entries,
    }
