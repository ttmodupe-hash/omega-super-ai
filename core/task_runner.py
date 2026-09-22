"""
OMEGA-LUQI Task Runner (Issue 34) - executes ONLY human-approved action tickets.

Fail-closed at every step:
  ticket exists -> status == "approved" -> action_type has a registered handler
  -> handler runs (sandboxed where code is involved) -> audit row appended.

A ticket executes exactly once (409 on replay). Pending or rejected tickets can
never run (409). Unknown action types are refused (400) and the ticket stays
approved - it is not consumed by a refusal. Nothing here ever approves a ticket;
that power belongs to core/ops_approvals.py and the human holding the admin key.
"""
from __future__ import annotations

import os
import time
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin
from . import ops_approvals as oa
from . import sandbox_runner as sb

router = APIRouter(prefix="/v1/ops/tasks", tags=["Ops Task Runner"])

MAX_RUNS = int(os.getenv("OPS_TASK_RUN_LOG", "500"))

# per-worker memory (numReplicas=1 rule)
_runs: list[dict] = []


async def _handle_run_python(payload: dict) -> dict:
    """Approved code execution - always through the tiered sandbox, never raw."""
    code = str(payload.get("code", ""))
    if not code.strip():
        raise HTTPException(status_code=400, detail="payload.code required")
    return await sb.run_python(code)


ACTION_HANDLERS: dict[str, Callable[[dict], Awaitable[dict]]] = {
    "run_python": _handle_run_python,
}


@router.post("/run")
async def run_ticket(ticket_id: str, _: bool = Depends(verify_admin)) -> dict:
    ticket = oa._tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="unknown ticket")
    if ticket["status"] == "executed":
        raise HTTPException(status_code=409, detail="ticket already executed")
    if ticket["status"] != "approved":
        raise HTTPException(status_code=409,
                            detail=f"ticket is {ticket['status']} - only approved tickets run")
    handler = ACTION_HANDLERS.get(ticket["action_type"])
    if handler is None:
        raise HTTPException(status_code=400,
                            detail=f"no handler registered for action_type "
                                   f"{ticket['action_type']!r} - ticket left approved")
    t0 = time.perf_counter()
    try:
        result: dict[str, Any] = await handler(ticket.get("payload") or {})
    except HTTPException:
        raise
    except Exception as exc:
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    ticket["status"] = "executed"
    ticket["executed_at"] = int(time.time())
    run = {"ticket_id": ticket_id, "action_type": ticket["action_type"],
           "ts": time.time(), "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
           "ok": bool(result.get("ok", True)), "result": result}
    _runs.append(run)
    if len(_runs) > MAX_RUNS:
        del _runs[: len(_runs) - MAX_RUNS]
    return run


@router.get("/log")
async def run_log(_: bool = Depends(verify_admin)) -> dict:
    return {"runs": len(_runs),
            "entries": [{k: v for k, v in r.items() if k != "result"} for r in _runs[-50:]]}
