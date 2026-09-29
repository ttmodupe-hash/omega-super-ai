"""
core/chat_gateway.py — /v1/chat/completions adapter (Chat Gateway v1.0.0)

Purpose: give the luqi-ai.com homepage chat widget a single, stable endpoint.

HOUSE LAW COMPLIANCE
- BACKEND-FIRST: this is a thin adapter over the REAL hybrid front door
  (core/hybrid_ai.py). No parallel intelligence, no client-side fabrication.
- No new money path: zero external API calls. No OpenAI proxy — the founder
  funds this out of pocket; a raw cloud proxy here would be an unguarded
  spend tap. Cloud synthesis, if ever wanted, must go through the existing
  budget-guarded deep_research pipeline, not this adapter.
- Anti-hallucination: when the engine cannot answer, the adapter returns the
  engine's honest boundary/escalation payload — never invented text.
- Kill-switch aware: if the hybrid engine is disabled (DISABLED_ENGINES),
  the endpoint answers 503 with an honest reason, not a fake reply.
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .hybrid_ai import _engine  # the single shared HybridEngine instance

router = APIRouter(prefix="/v1/chat", tags=["Chat Gateway"])

MAX_PROMPT_CHARS = 4000
MAX_HISTORY_TURNS = 20


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., max_length=MAX_PROMPT_CHARS)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_CHARS)
    mode: Optional[str] = "auto"
    # Accepted for frontend compatibility. The hybrid front door is a
    # single-turn classifier/router today; history is carried for future
    # conversational context and is NOT silently discarded — it is echoed
    # in meta.history_turns so callers can see what was received.
    history: Optional[List[ChatMessage]] = None


def _kill_switch_on() -> bool:
    return "hybrid_ai" in os.getenv("DISABLED_ENGINES", "")


@router.post("/completions")
async def chat_completions(payload: ChatRequest) -> Dict[str, Any]:
    """Homepage chat entry point → real hybrid engine. Honest or nothing."""
    if _kill_switch_on():
        # Honest pause — answers held for human review (dead man's switch law)
        raise HTTPException(
            status_code=503,
            detail="Engine paused: kill switch engaged — answers are held for human review.")

    t0 = time.perf_counter()
    result = await asyncio.to_thread(_engine.process, payload.prompt, None)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    history_turns = len(payload.history or [])
    response_text = result.get("response") or ""
    if not response_text.strip():
        # The engine returned nothing — say so. Never invent filler.
        raise HTTPException(
            status_code=502,
            detail="Engine produced an empty response — nothing was invented to fill the gap.")

    out: Dict[str, Any] = {
        "status": "success",
        "response": response_text,
        # Real metadata — the homepage may render it or ignore it.
        "engine_used": result.get("engine_used"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "suggested_tool": result.get("suggested_tool"),
        "latency_ms": latency_ms,
        "pii_redacted": result.get("pii_redacted", False),
        "meta": {"history_turns": history_turns, "mode": payload.mode},
    }
    # If the hybrid gate wants escalation, surface it honestly instead of
    # pretending the front-door answer is complete.
    if result.get("required_gate"):
        out["escalation"] = {
            "available": True,
            "endpoint": "/v1/deep-research",
            "note": "Front-door confidence is low — Deep Research retrieves real sources.",
        }
    return out


@router.get("/health")
async def chat_health() -> Dict[str, Any]:
    """Public gateway status — mirrors hybrid health, nothing assumed."""
    return {
        "gateway": "chat-completions-adapter",
        "version": "1.0.0",
        "kill_switch": _kill_switch_on(),
        "upstream": "/v1/hybrid/process",
        "sklearn_available": _engine._load_ml() is not False,
    }
