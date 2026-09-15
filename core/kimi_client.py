"""
OMEGA-LUQI Unified Kimi API Client - ONE GROUP, ONE PIPELINE.

Every engine (gateway, research, tender scan, dev matrix, self-healing,
pedagogy, sovereign, universal, integrity) routes through chat_completion().
One fail-closed key check, one parser, one fault path - no per-engine copies
of credential handling to drift or break.

Contract (preserved for all existing routes and the PWA):
  - missing KIMI_API_KEY  -> HTTPException 500 (fail-closed)
  - upstream non-200      -> HTTPException(status, "Kimi Engine Fault: ...")
  - network failure       -> requests.exceptions.RequestException (routes map to 503)
  - success               -> assistant content string
"""
import os
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException

from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .kimi_parse import extract_assistant_content


def chat_completion(system: str, user: str, *,
                    tools: Optional[list] = None,
                    timeout: int = 60) -> str:
    """Single Kimi call. Returns assistant content. Never returns None."""
    kimi_key = os.getenv("KIMI_API_KEY")
    if not kimi_key:
        raise HTTPException(status_code=500, detail="Kimi Core Integration Break: Access Token undefined.")

    payload: Dict[str, Any] = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "reasoning_effort": KIMI_REASONING_EFFORT,
        "response_format": {"type": "json_object"},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    from .cost_telemetry import bump, maybe_alarm
    bump("kimi", len(system) + len(user))
    res = requests.post(
        f"{KIMI_BASE_URL}/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {kimi_key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail=f"Kimi Engine Fault: {res.text[:400]}")
    maybe_alarm()
    return extract_assistant_content(res.json())


def chat_dict(system: str, user: str, *, tools: Optional[list] = None,
              timeout: int = 60) -> Dict[str, Any]:
    """OpenAI-shaped wrapper - preserves the API contract routes/PWA expect."""
    return {"choices": [{"message": {"content": chat_completion(system, user, tools=tools, timeout=timeout)}}]}
