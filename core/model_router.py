"""
OMEGA-LUQI Sovereign Multipolar Model Router

REAL provider adapters with capability routing and graceful fallback:
  claude  -> api.anthropic.com/v1/messages   (codegen, self-healing)
  gemini  -> generativelanguage.googleapis.com (default workhorse)
  kimi    -> unified core/kimi_client.py      (deep research / 1M context)

Honesty note: the pasted blueprint version returned hardcoded placeholder
strings from every adapter - convincing structure over zero function. This
router makes REAL calls or fails loudly; there is no fake-success mode.

States:
  provider key missing          -> provider skipped (chain continues)
  no provider has a key         -> HTTPException 500 (fail-closed)
  all configured providers fail -> HTTPException 503 (degraded, tell ops)
"""
import asyncio
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin
from .auth import LuqiAuthManager, UserSessionProfile
from .pii_scrub import scrub_pii
from . import kimi_client

logger = logging.getLogger("LuqiModelRouter")
router = APIRouter(prefix="/v1/router", tags=["Multipolar AI Orchestration"])

# --- telemetry (locked; surfaced on the admin board) ---
_TELEMETRY: Dict[str, Dict[str, int]] = {
    "kimi": {"calls": 0, "failures": 0},
    "gemini": {"calls": 0, "failures": 0},
    "claude": {"calls": 0, "failures": 0},
}
_tel_lock = threading.Lock()

# --- routing table (env-overridable default chain) ---
ROUTING_TABLE: Dict[str, List[str]] = {
    "codegen": ["claude", "gemini", "kimi"],
    "self_healing": ["claude", "gemini", "kimi"],
    "deep_research": ["kimi", "gemini"],
    "default": None,  # resolved from env below
}

_KEY_ENVS = {"kimi": "KIMI_API_KEY", "gemini": "GEMINI_API_KEY", "claude": "CLAUDE_API_KEY"}
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")


def telemetry() -> Dict[str, Dict[str, int]]:
    with _tel_lock:
        return {k: dict(v) for k, v in _TELEMETRY.items()}


def _bump(provider: str, failed: bool = False) -> None:
    with _tel_lock:
        _TELEMETRY[provider]["calls"] += 1
        if failed:
            _TELEMETRY[provider]["failures"] += 1


# ---------------- REAL ADAPTERS (blocking; called via to_thread) ----------------

def _kimi_adapter(system: str, user: str, timeout: int) -> str:
    return kimi_client.chat_completion(system, user, timeout=timeout)


def _gemini_adapter(system: str, user: str, timeout: int) -> str:
    key = os.environ["GEMINI_API_KEY"]
    res = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent",
        params={"key": key},
        json={"system_instruction": {"parts": [{"text": system}]},
              "contents": [{"parts": [{"text": user}]}]},
        timeout=timeout,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Gemini fault {res.status_code}: {res.text[:300]}")
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]


def _claude_adapter(system: str, user: str, timeout: int) -> str:
    key = os.environ["CLAUDE_API_KEY"]
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        json={"model": _CLAUDE_MODEL, "max_tokens": 4096,
              "system": system, "messages": [{"role": "user", "content": user}]},
        timeout=timeout,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Claude fault {res.status_code}: {res.text[:300]}")
    return res.json()["content"][0]["text"]


ADAPTERS: Dict[str, Callable[[str, str, int], str]] = {
    "kimi": _kimi_adapter,
    "gemini": _gemini_adapter,
    "claude": _claude_adapter,
}


def plan_chain(task_type: str) -> List[str]:
    """Routing decision as data. Default chain env-overridable."""
    if task_type in ROUTING_TABLE and ROUTING_TABLE[task_type]:
        return ROUTING_TABLE[task_type]
    default = os.getenv("ROUTER_DEFAULT_CHAIN", "gemini,kimi,claude")
    return [p.strip() for p in default.split(",") if p.strip()]


async def route_chat(task_type: str, system: str, user: str, *, timeout: int = 60) -> Dict[str, Any]:
    """Route one chat through the multipolar chain. Real calls, real fallback."""
    user = scrub_pii(user)
    chain = plan_chain(task_type)
    configured = [p for p in chain if os.getenv(_KEY_ENVS[p])]
    if not configured:
        raise HTTPException(
            status_code=500,
            detail="No AI provider configured: set KIMI_API_KEY and/or GEMINI_API_KEY and/or CLAUDE_API_KEY.",
        )
    failures = []
    for provider in configured:
        try:
            from .cost_telemetry import bump, maybe_alarm
            bump(provider, len(system) + len(user))
            content = await asyncio.to_thread(ADAPTERS[provider], system, user, timeout)
            maybe_alarm()
            _bump(provider)
            return {"provider": provider, "content": content}
        except HTTPException:
            raise  # fail-closed key errors propagate, not fallback-masked
        except Exception as e:
            _bump(provider, failed=True)
            logger.warning("Provider %s failed (%s) - trying next in chain", provider, e)
            failures.append(f"{provider}: {e}")
    raise HTTPException(status_code=503,
                        detail=f"All configured providers failed: {'; '.join(failures)[:400]}")


@router.post("/execute-routed-task")
async def execute_multipolar_routed_task(
    task_type: str,
    prompt: str,
    system_prompt: str = "",
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Auth-gated general routing endpoint for new workflows."""
    return await route_chat(task_type, system_prompt, prompt)


@router.get("/telemetry")
async def router_telemetry(is_authenticated: bool = Depends(verify_admin)):
    """Per-provider call/failure counters for the ops board."""
    return telemetry()
