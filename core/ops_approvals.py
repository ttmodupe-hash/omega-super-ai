"""
OMEGA-LUQI Ops Approvals (Issue 33) - human sign-off tickets for sensitive actions.

Any engine can request approval for an action (deploy, config change, prompt
promotion). The request creates a single-use, expiring ticket and notifies the
operator via Slack/Discord webhook with an approve/reject link. Without webhooks
it degrades honestly: the ticket still works, and the notification log says so.

Decisions are single-use (409 on replay), tokens are HMAC-bound to the ticket
(403 on tamper), and expired tickets return 410. Nothing executes here - this
module only records the human decision; core/task_runner.py acts on it.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin
from .security_guards import DEFAULT_ADMIN_SECRET
from . import ops_journal

router = APIRouter(prefix="/v1/ops/approvals", tags=["Ops Approvals"])

SLACK_URL = os.getenv("LUQI_OPS_SLACK_WEBHOOK", "")
DISCORD_URL = os.getenv("LUQI_OPS_DISCORD_WEBHOOK", "")
TICKET_TTL_S = int(os.getenv("OPS_APPROVAL_TTL_S", "900"))          # 15 minutes
MAX_TICKETS = int(os.getenv("OPS_APPROVAL_MAX_TICKETS", "500"))
PUBLIC_BASE_URL = os.getenv("LUQI_PUBLIC_BASE_URL", "").rstrip("/")

# per-worker memory (numReplicas=1 rule)
_tickets: dict[str, dict] = {}
_notify_log: list[str] = []

# Issue 37: token brute-force lockout + expiry hygiene + audit trail
MAX_TOKEN_ATTEMPTS = int(os.getenv("OPS_TOKEN_MAX_ATTEMPTS", "5"))
_fail_counts: dict[str, int] = {}
_audit: list[dict] = []


def _audit_event(event: dict) -> None:
    _audit.append(event)
    if len(_audit) > 500:
        del _audit[: len(_audit) - 500]


def _prune_expired() -> None:
    """Expired pending tickets are marked, journaled, and can never be decided."""
    now = int(time.time())
    for tid, t in _tickets.items():
        if t["status"] == "pending" and t["expires"] <= now:
            t["status"] = "expired"
            _audit_event({"ticket_id": tid, "event": "expired", "ts": now})
            ops_journal.record({"kind": "approval_expired", "ticket_id": tid})


def _secret() -> str:
    return os.getenv("LUQI_ADMIN_SECRET", DEFAULT_ADMIN_SECRET)


def _sign_ticket(ticket_id: str, action_type: str, expires: int) -> str:
    msg = f"{ticket_id}:{action_type}:{expires}".encode()
    return hmac.new(_secret().encode(), msg, hashlib.sha256).hexdigest()


def _evict_oldest() -> None:
    done = [t for t in _tickets.values() if t["status"] != "pending"]
    pool = done or list(_tickets.values())
    oldest = min(pool, key=lambda t: t["created"])
    _tickets.pop(oldest["ticket_id"], None)


async def _notify(ticket: dict, token: str) -> None:
    base = PUBLIC_BASE_URL or "http://localhost:8000"
    tid = ticket["ticket_id"]
    approve = f"{base}/v1/ops/approvals/{tid}/respond?token={token}&decision=approve"
    reject = f"{base}/v1/ops/approvals/{tid}/respond?token={token}&decision=reject"
    text = (f"[OMEGA-LUQI] Approval requested: {ticket['action_type']} - {ticket['summary']}\n"
            f"Approve: {approve}\nReject: {reject}\n"
            f"Ticket {tid} expires at epoch {ticket['expires']}.")
    sent = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            if SLACK_URL:
                await client.post(SLACK_URL, json={"text": text})
                sent = True
            if DISCORD_URL:
                await client.post(DISCORD_URL, json={"content": text})
                sent = True
    except Exception as exc:
        _notify_log.append(f"[webhook-error] ticket {tid}: {type(exc).__name__}: {exc}")
        return
    if sent:
        _notify_log.append(f"[sent] ticket {tid} dispatched to webhook(s)")
    else:
        _notify_log.append(
            f"[no-webhook] ticket {tid} pending - no Slack/Discord URL configured; "
            "decide via the admin console or /decision endpoint")


def _decide(ticket: dict, decision: str, decided_by: str) -> dict:
    """Shared state machine for the token link and the admin console."""
    if int(time.time()) > ticket["expires"]:
        raise HTTPException(status_code=410, detail="ticket expired")
    if ticket["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"ticket already {ticket['status']}")
    d = (decision or "").strip().lower()
    if d not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be approve|reject")
    ticket["status"] = "approved" if d == "approve" else "rejected"
    ticket["decided_by"] = decided_by
    ticket["decided_at"] = int(time.time())
    _notify_log.append(f"[decision] ticket {ticket['ticket_id']} -> {ticket['status']} ({decided_by})")
    _audit_event({"ticket_id": ticket["ticket_id"], "event": ticket["status"],
                  "by": decided_by, "ts": ticket["decided_at"]})
    ops_journal.record({"kind": "approval_decided", "ticket_id": ticket["ticket_id"],
                        "status": ticket["status"], "by": decided_by})
    return {"ticket_id": ticket["ticket_id"], "status": ticket["status"]}


@router.post("/request")
async def request_approval(action_type: str, summary: str, payload: str = "",
                           _: bool = Depends(verify_admin)) -> dict:
    action_type = (action_type or "").strip()
    if not action_type:
        raise HTTPException(status_code=400, detail="action_type required")
    parsed_payload: dict = {}
    if payload.strip():
        import json
        try:
            parsed_payload = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="payload must be valid JSON")
        if not isinstance(parsed_payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
    ticket_id = secrets.token_hex(8)
    now = int(time.time())
    expires = now + TICKET_TTL_S
    token = _sign_ticket(ticket_id, action_type, expires)
    _tickets[ticket_id] = {
        "ticket_id": ticket_id, "action_type": action_type,
        "summary": (summary or "")[:500], "payload": parsed_payload,
        "status": "pending", "created": now, "expires": expires,
        "token": token, "decided_by": None, "decided_at": None,
    }
    if len(_tickets) > MAX_TICKETS:
        _evict_oldest()
    _prune_expired()
    _audit_event({"ticket_id": ticket_id, "event": "requested", "ts": now,
                  "action_type": action_type, "summary": (summary or "")[:500]})
    ops_journal.record({"kind": "approval_requested", "ticket_id": ticket_id,
                        "action_type": action_type, "summary": (summary or "")[:500],
                        "payload": parsed_payload, "expires": expires})
    await _notify(_tickets[ticket_id], token)
    return {"ticket_id": ticket_id, "token": token, "status": "pending", "expires": expires}


@router.get("/pending")
async def list_pending(_: bool = Depends(verify_admin)) -> dict:
    now = int(time.time())
    pending = [{"ticket_id": t["ticket_id"], "action_type": t["action_type"],
                "summary": t["summary"], "created": t["created"], "expires": t["expires"]}
               for t in _tickets.values()
               if t["status"] == "pending" and t["expires"] > now]
    return {"count": len(pending), "pending": pending}


@router.get("/{ticket_id}/respond")
async def respond(ticket_id: str, token: str, decision: str) -> dict:
    """The webhook link. The HMAC token IS the credential - no admin header needed.
    Repeated bad tokens lock the ticket (429) - brute force gets nothing."""
    ticket = _tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="unknown ticket")
    if _fail_counts.get(ticket_id, 0) >= MAX_TOKEN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="ticket locked after repeated bad tokens")
    if not hmac.compare_digest(token or "", ticket["token"]):
        _fail_counts[ticket_id] = _fail_counts.get(ticket_id, 0) + 1
        raise HTTPException(status_code=403, detail="invalid token")
    return _decide(ticket, decision, decided_by="token-link")


@router.post("/{ticket_id}/decision")
async def admin_decision(ticket_id: str, decision: str,
                         _: bool = Depends(verify_admin)) -> dict:
    """Console path: admin key instead of the ticket token."""
    ticket = _tickets.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="unknown ticket")
    return _decide(ticket, decision, decided_by="admin-console")


def restore_from_journal() -> int:
    """Restart recovery: replay the journal, re-create tickets, then apply
    decisions/expirations/executions in write order. The HMAC token is
    deterministic (ticket_id:action_type:expires), so restored tickets keep
    their original sign-off links without the token ever hitting the disk."""
    if not ops_journal.ENABLED:
        return 0
    restored = 0
    for e in ops_journal.replay():
        kind, tid = e.get("kind"), e.get("ticket_id")
        if not tid:
            continue
        if kind == "approval_requested" and tid not in _tickets:
            expires = int(e.get("expires", 0))
            action_type = e.get("action_type", "")
            _tickets[tid] = {
                "ticket_id": tid, "action_type": action_type,
                "summary": e.get("summary", ""), "payload": e.get("payload") or {},
                "status": "pending", "created": int(e.get("ts", 0)),
                "expires": expires,
                "token": _sign_ticket(tid, action_type, expires),
                "decided_by": None, "decided_at": None,
            }
            restored += 1
        elif kind == "approval_decided" and tid in _tickets:
            _tickets[tid]["status"] = e.get("status", _tickets[tid]["status"])
            _tickets[tid]["decided_by"] = e.get("by")
        elif kind == "task_executed" and tid in _tickets:
            _tickets[tid]["status"] = "executed"
    _prune_expired()
    return restored


@router.get("/audit")
async def audit_trail(_: bool = Depends(verify_admin)) -> dict:
    """Admin-only: in-memory audit tail + durable journal tail + journal health."""
    return {"in_memory": _audit[-100:],
            "journal": ops_journal.read_recent(100),
            "journal_enabled": ops_journal.ENABLED,
            "journal_write_errors": ops_journal.write_errors[-10:]}
