"""
OMEGA-LUQI Kimi / Moonshot High-Context Reasoning Gateway

Injects Moonshot's long-context engine into the student diagnostic pipeline.
External HTTP runs in a thread pool so slow LLM responses never block the
event loop for other students.

Env:
    KIMI_API_KEY      - required
    KIMI_BASE_URL     - default https://api.moonshot.cn/v1
    KIMI_MODEL        - default moonshot-v1-auto
"""
import os
import asyncio
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
# MIGRATION (2026-09): moonshot-v1-auto was sunset by Moonshot on 2026-08-31
# (calls now return 404). Default migrated to kimi-k3.
# For high-volume codegen, override KIMI_MODEL=kimi-k2.7-code ($0.95/$4 vs K3 $3/$15,
# and K3 thinking is always-on which inflates output-token spend).
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k3")
# K3 reasoning levels: low | high | max. Default "high" balances cost vs depth;
# use "max" for the hardest architectural reasoning only.
KIMI_REASONING_EFFORT = os.getenv("KIMI_REASONING_EFFORT", "high")


def _call_kimi(prompt: str, context_history: Optional[list]) -> dict:
    """Unified client. Context history folds into the user turn (single call)."""
    from .kimi_client import chat_dict
    from .pii_scrub import scrub_pii
    system = "You are the advanced Luqi-AI core reasoning loop, managing technical labs."
    user = scrub_pii(prompt)  # DATA SOVEREIGNTY SCREEN
    if context_history:
        history_text = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in context_history)
        user = f"{history_text}\nuser: {user}"
    return chat_dict(system, user, timeout=30)


class ReasonRequest(BaseModel):
    prompt: str
    context_history: Optional[list] = None


@router.post("/v1/agent/kimi-reason")
async def execute_kimi_reasoning_node(req: ReasonRequest):
    """High-context reasoning endpoint. Blocking call offloaded to the thread pool."""
    try:
        out = await asyncio.to_thread(_call_kimi, req.prompt, req.context_history)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Reasoning bridge unavailable: {str(e)}")

    # Batch G: opt-in adversarial verification of the draft answer. Additive by
    # contract - the response gains a "verification" block and the content is
    # only ever REPLACED when the pipeline returns status="verified". Any
    # pipeline fault degrades to {"status": "unavailable"} and the original
    # answer is returned untouched: the gateway's answer path never breaks.
    if os.getenv("LUQI_TRUTH_PIPELINE", "0") == "1":
        try:
            from .truth_engine import verify_draft
            draft = out["choices"][0]["message"]["content"]
            report = await verify_draft(req.prompt, draft)
            out["verification"] = report
            if report["status"] == "verified":
                out["choices"][0]["message"]["content"] = report["answer"]
        except Exception as exc:
            out["verification"] = {"status": "unavailable", "error": type(exc).__name__}
    return out
