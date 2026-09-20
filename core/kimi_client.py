"""
OMEGA-LUQI Unified Kimi API Client - ONE GROUP, ONE PIPELINE.

Every engine (gateway, research, tender scan, dev matrix, self-healing,
pedagogy, sovereign, universal, integrity) routes through chat_completion().
One fail-closed key check, one parser, one fault path - no per-engine copies
of credential handling to drift or break.

Contract (preserved for all existing routes and the PWA):
  - missing KIMI_API_KEY  -> HTTPException 500 (fail-closed)
  - budget hard-stop      -> HTTPException 429, NO upstream call made (fail-closed)
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

    # Fail-closed cost circuit-breaker: checked BEFORE the upstream call so a
    # tripped budget spends exactly $0.00 more. The 80% SMS alarm warns; this
    # hard stop protects (see cost_telemetry.enforce_budget).
    from .cost_telemetry import bump, maybe_alarm, enforce_budget
    allowed, snap = enforce_budget()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Cost circuit-breaker OPEN: estimated spend ${snap['estimated_spend_usd']} "
                f"reached {snap['hard_stop_pct']}% of the ${snap['budget_usd']} monthly budget. "
                "No upstream call was made. Raise MONTHLY_TOKEN_BUDGET_USD / "
                "COST_HARD_STOP_PCT or wait for the next billing month."
            ),
        )

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
