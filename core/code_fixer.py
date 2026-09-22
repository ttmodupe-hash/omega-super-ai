"""
OMEGA-LUQI Code Fixer (Issue 35) - the model side of the capped recalibration loop.

sandbox_runner.run_with_recalibration needs a fixer callback: (code, stderr) ->
fixed code. This module provides the honest version: the configured brain
proposes a fix, and the proposal is RE-GATED through static_gate before it is
ever returned (run_python gates again on retry - belt and braces, so a hostile
or sloppy brain response can never smuggle banned constructs into the sandbox).

Fail-closed without keys: returns None and the loop stops instead of guessing.
Shares the brain env vars with self_diagnose (FIELD_BRAIN_* / KIMI_API_KEY).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin
from . import sandbox_runner as sb

router = APIRouter(prefix="/v1/ops/recalibrate", tags=["Ops Recalibration"])

BRAIN_BASE_URL = os.getenv("FIELD_BRAIN_BASE_URL", "https://api.moonshot.ai/v1")
BRAIN_API_KEY = os.getenv("KIMI_API_KEY") or os.getenv("FIELD_BRAIN_API_KEY") or ""
BRAIN_MODEL = os.getenv("FIELD_BRAIN_MODEL", "kimi-k3")
MAX_RETRIES = int(os.getenv("RECALIBRATE_MAX_RETRIES", "2"))


def _extract_code(text: str) -> str:
    """Strip markdown fences if the brain wrapped the code anyway."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        lines = lines[1:]                          # drop ```python
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip()


async def brain_fixer(code: str, stderr: str) -> str | None:
    """fixer callback for run_with_recalibration. Returns re-gated code or None."""
    if not BRAIN_API_KEY:
        return None
    import httpx
    prompt = (
        "You are repairing a small Python snippet that failed in a sandbox. "
        "Reply with ONLY the corrected, complete Python code - no prose, no "
        "markdown fences. Constraints: no imports of os/sys/subprocess/shutil/"
        "socket/ctypes/pathlib, no eval/exec/compile/open/getattr, no dunder "
        "access. Keep it minimal.\n\n"
        f"Failing code:\n{code[:4000]}\n\nSandbox stderr:\n{(stderr or '')[:2000]}"
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
            text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None                                # honest stop, never a guess
    fixed = _extract_code(text)
    if not fixed or fixed == code.strip():
        return None                                # no-op fix: stop the loop
    ok, _why = sb.static_gate(fixed)
    return fixed if ok else None                   # re-gate: banned fix = no fix


@router.post("")
async def recalibrate(code: str, _: bool = Depends(verify_admin)) -> dict:
    """Admin-gated: run code through the capped self-healing loop. The verdict
    is returned to the human caller - nothing is stored, deployed, or applied."""
    if not (code or "").strip():
        raise HTTPException(status_code=400, detail="empty code")
    return await sb.run_with_recalibration(code, brain_fixer, max_retries=MAX_RETRIES)


@router.get("/metrics")
async def recalibration_metrics(_: bool = Depends(verify_admin)) -> dict:
    return sb.metrics()
