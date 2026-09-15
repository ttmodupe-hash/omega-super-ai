"""
OMEGA-LUQI Self-Healing Diagnostic Agent

Admin-gated diagnostic endpoint: submit a traceback, receive a Kimi K3
root-cause diagnosis + patch PROPOSAL in structured JSON.

Deliberate boundary: this agent NEVER modifies running code. An agent that
rewrites its own live codebase from LLM output is a supply-chain attack with
extra steps - proposals go to a human, always (the 30% philosophy applied to
the platform itself).

Usage from other modules (optional, fire-and-forget):
    from .self_healing import diagnose_fault
    try: ...
    except Exception as exc:
        proposal = await diagnose_fault(__name__, traceback.format_exc())
        # log it, alert ops - a human decides what ships
"""
import os
import asyncio
import json
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .pii_scrub import scrub_pii
from .admin_auth import verify_admin

router = APIRouter(tags=["Self-Healing Diagnostics"])

HEALING_DIRECTIVE = (
    "You are the senior Luqi-AI Self-Healing Core DevOps Agent. "
    "Analyze the incoming system traceback, diagnose the exact runtime fault, "
    "and output a clean structural patch PROPOSAL. Structure your output strictly "
    "in JSON with two root keys: 'root_cause_diagnosis' and 'recommended_patch_actions'."
)


class FaultReport(BaseModel):
    error_traceback: str
    throwing_module: str


def _call_healing_engine(traceback_text: str, module: str) -> Dict[str, Any]:
    """Multipolar route: diagnosis prefers Claude, falls back Gemini -> Kimi."""
    from .model_router import route_chat
    from .pii_scrub import scrub_pii
    import asyncio as _asyncio
    result = _asyncio.new_event_loop().run_until_complete(
        route_chat("self_healing", HEALING_DIRECTIVE,
                   f"Module: {module}\nTraceback: {scrub_pii(traceback_text)}", timeout=30))
    try:
        import json
        return json.loads(result["content"])
    except json.JSONDecodeError:
        return {"raw_diagnosis": result["content"]}


async def diagnose_fault(module: str, traceback_text: str) -> Optional[Dict[str, Any]]:
    """Fire-and-forget helper for modules that want a diagnosis without a route.
    Returns None when unconfigured - never raises into business logic."""
    try:
        return await asyncio.to_thread(_call_healing_engine, traceback_text, module)
    except Exception:
        return None


@router.post("/v1/agent/self-heal")
async def intercept_and_heal_system_fault(
    report: FaultReport,
    is_authenticated: bool = Depends(verify_admin),
):
    """Submit a traceback -> receive root-cause diagnosis + patch proposal.
    Admin-gated; proposals only - a human ships the fix."""
    try:
        proposal = await asyncio.to_thread(_call_healing_engine, report.error_traceback, report.throwing_module)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Healing Bridge Failure: {str(e)}")
    return {"status": "diagnosis_complete", "proposal": proposal}
