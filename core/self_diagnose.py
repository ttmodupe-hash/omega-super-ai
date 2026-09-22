"""
OMEGA-LUQI Self-Diagnose (Issue 27a) - honest error diagnosis, NEVER auto-apply.

Any module posts a traceback; the configured brain returns a diagnosis and a
SUGGESTED patch. The suggestion is stored as pending_human and returned to the
caller - nothing is ever applied automatically (the self-modification ban).
Correct provider URLs only (env-driven); fail-closed without keys.

Batch E: /report is admin-gated - an open endpoint would let anyone burn the
brain API quota with synthetic tracebacks.
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin

router = APIRouter(prefix="/v1/self-diagnose", tags=["Self-Diagnose"])

BRAIN_BASE_URL = os.getenv("FIELD_BRAIN_BASE_URL", "https://api.moonshot.ai/v1")
BRAIN_API_KEY = os.getenv("KIMI_API_KEY") or os.getenv("FIELD_BRAIN_API_KEY") or ""
BRAIN_MODEL = os.getenv("FIELD_BRAIN_MODEL", "kimi-k3")
MAX_ENTRIES = int(os.getenv("SELF_DIAG_MAX_ENTRIES", "200"))

# per-worker memory (numReplicas=1 rule)
_log: list[dict] = []


async def _diagnose(traceback_text: str) -> dict:
    if not BRAIN_API_KEY:
        return {"diagnosis": "brain unavailable (no key) - traceback stored for human review",
                "suggested_patch": None, "status": "pending_human"}
    import httpx
    prompt = (
        "You are a senior platform engineer reviewing a crash. Diagnose the root cause "
        "and propose a minimal patch. Reply with STRICT JSON only: "
        "{\"diagnosis\": \"...\", \"suggested_patch\": \"...\"}. "
        "Never invent file contents you have not seen.\n\nTraceback:\n" + traceback_text[:4000]
    )
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{BRAIN_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {BRAIN_API_KEY}"},
                json={"model": BRAIN_MODEL,
                      "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.1})
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        start, end = text.index("{"), text.rindex("}") + 1
        import json
        v = json.loads(text[start:end])
        return {"diagnosis": str(v.get("diagnosis", ""))[:1500],
                "suggested_patch": str(v.get("suggested_patch", ""))[:3000],
                "status": "pending_human"}
    except Exception as exc:
        return {"diagnosis": f"brain call failed: {type(exc).__name__}",
                "suggested_patch": None, "status": "pending_human"}


@router.post("/report")
async def report(traceback_text: str, _: bool = Depends(verify_admin)) -> dict:
    tb = (traceback_text or "").strip()
    if not tb:
        raise HTTPException(status_code=400, detail="empty traceback")
    result = await _diagnose(tb)
    entry = {"ts": time.time(), "trace_excerpt": tb[:500],
             **result, "auto_applied": False}     # always False - permanently
    _log.append(entry)
    if len(_log) > MAX_ENTRIES:
        del _log[: len(_log) - MAX_ENTRIES]
    return {"stored": True, "entry": {k: v for k, v in entry.items() if k != "trace_excerpt"}}


@router.get("/log")
async def get_log(_: bool = Depends(verify_admin)) -> dict:
    return {"entries": len(_log), "pending_human": sum(1 for e in _log if e["status"] == "pending_human"),
            "auto_applied_total": sum(1 for e in _log if e["auto_applied"])}
