"""Chat Gateway - thin, zero-cost adapter over the existing hybrid front door.

CHAT-1: exposes POST /v1/chat/completions so any Luqi-ai surface (homepage
widget, console, mobile) can talk to the engine through ONE contract.

Design law honoured here:
- BACKEND-FIRST: this router only wraps core.hybrid_ai's engine - no model
  calls, no external API spend, no OpenAI proxy (unguarded spend tap).
- ANTI-HALLUCINATION: answers come from the real engine; on failure we return
  honest HTTP errors - never stubbed or fabricated text.
- KILL-SWITCH AWARE: when hybrid_ai is disabled via DISABLED_ENGINES the
  gateway holds answers for human review (503), same as the engine itself.
- ESCALATION POINTER: when the engine sets required_gate (confidence gate),
  we surface a pointer to /v1/deep-research instead of pretending certainty.
"""
import asyncio
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .hybrid_ai import _engine  # the same singleton the /v1/hybrid routes use

router = APIRouter(prefix="/v1/chat", tags=["Chat Gateway"])

MAX_PROMPT_CHARS = 4000
MAX_HISTORY_TURNS = 20


class ChatMessage(BaseModel):
    """One prior turn. Content is capped so history cannot smuggle a
    mega-prompt past the prompt limit."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., max_length=MAX_PROMPT_CHARS)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_CHARS)
    mode: Optional[str] = "auto"  # reserved; routing stays engine-side today
    history: Optional[List[ChatMessage]] = None


def _kill_switch_on() -> bool:
    """Mirror hybrid_ai's kill-switch: DISABLED_ENGINES lists paused engines."""
    return "hybrid_ai" in os.getenv("DISABLED_ENGINES", "")


@router.post("/completions")
async def chat_completions(payload: ChatRequest) -> Dict[str, Any]:
    """Chat-shaped front door over the hybrid engine.

    Request:  {prompt, mode?, history?}
    Response: {status, response, engine_used, intent, confidence, ...}
    """
    if _kill_switch_on():
        raise HTTPException(
            status_code=503,
            detail="Engine paused: kill switch engaged - answers are held for human review.",
        )

    # History is accepted and echoed in meta (turn count) for continuity
    # bookkeeping; the hybrid engine itself is stateless per call today.
    history = payload.history or []
    history = history[-MAX_HISTORY_TURNS:]

    result = await asyncio.to_thread(_engine.process, payload.prompt, None)

    response_text = (result.get("response") or "").strip()
    if not response_text:
        # Honest failure - the engine declined to answer. Never invent text.
        raise HTTPException(
            status_code=502,
            detail="Engine returned no answer for this prompt. Please rephrase or try again.",
        )

    body: Dict[str, Any] = {
        "status": "success",
        "response": response_text,
        "engine_used": result.get("engine_used"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "suggested_tool": result.get("suggested_tool"),
        "latency_ms": result.get("latency_ms"),
        "pii_redacted": result.get("pii_redacted", False),
        "meta": {
            "history_turns": len(history),
            "mode": payload.mode,
        },
    }
    if result.get("required_gate"):
        body["escalation"] = {
            "available": True,
            "endpoint": "/v1/deep-research",
            "note": "Confidence gate reached - escalate for a sourced, in-depth answer.",
        }
    return body


@router.get("/health")
async def chat_health() -> Dict[str, Any]:
    """Public heartbeat for chat surfaces (no secrets, counts/flags only)."""
    return {
        "gateway": "chat-completions-adapter",
        "version": "1.0.0",
        "kill_switch": _kill_switch_on(),
        "upstream": "/v1/hybrid/process",
        "sklearn_available": getattr(_engine, "sklearn_available", None),
    }
