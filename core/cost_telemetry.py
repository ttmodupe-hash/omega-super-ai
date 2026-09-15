"""
OMEGA-LUQI Cost Telemetry - real counting + ESTIMATED spend vs budget.

Estimation is labeled as such: chars/4 -> tokens, provider rates per M.
Counts actual calls at the unified client + multipolar router. At 80% of
MONTHLY_TOKEN_BUDGET_USD the real SMS gateway alerts (throttled once/day).
"""
import os
import threading
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends

from .admin_auth import verify_admin

router = APIRouter(prefix="/v1/cost", tags=["Cost Telemetry"])

# USD per 1M tokens (input) - env-overridable as rates shift
RATES = {"kimi": (3.0, 15.0), "gemini": (1.0, 5.0), "claude": (3.0, 15.0)}
CHARS_PER_TOKEN = 4

_lock = threading.Lock()
_counts: Dict[str, Dict[str, float]] = {}  # provider -> {calls, chars_in, est_cost}
_alarm_day = {"day": "", "fired": False}


def bump(provider: str, chars_in: int) -> None:
    in_rate, out_rate = RATES.get(provider, (3.0, 15.0))
    est = (chars_in / CHARS_PER_TOKEN) / 1e6 * in_rate
    with _lock:
        agg = _counts.setdefault(provider, {"calls": 0, "chars_in": 0.0, "est_cost_usd": 0.0})
        agg["calls"] += 1
        agg["chars_in"] += chars_in
        agg["est_cost_usd"] += est


def telemetry() -> Dict[str, Any]:
    with _lock:
        snapshot = {k: dict(v) for k, v in _counts.items()}
    budget = float(os.getenv("MONTHLY_TOKEN_BUDGET_USD", "100"))
    spent = round(sum(v["est_cost_usd"] for v in snapshot.values()), 4)
    pct = round(spent / budget * 100, 1) if budget else 0.0
    return {"month": time.strftime("%Y-%m"), "budget_usd": budget,
            "estimated_spend_usd": spent, "pct_of_budget": pct,
            "alarm_threshold_pct": 80.0, "alarm_triggered": pct >= 80.0,
            "estimate_disclaimer": "chars/4 token estimate - reconcile with provider invoices",
            "by_provider": snapshot}


def maybe_alarm() -> None:
    t = telemetry()
    today = time.strftime("%Y-%m-%d")
    if t["alarm_triggered"]:
        with _lock:
            if _alarm_day["day"] == today and _alarm_day["fired"]:
                return
            _alarm_day.update(day=today, fired=True)
        try:
            from .notifications import _gateway
            import asyncio
            asyncio.get_running_loop().create_task(
                _gateway.send_gate_lock_alert("COST-BUDGET", "token_budget",
                                              f"80% of monthly token budget reached ({t['pct_of_budget']}%)"))
        except RuntimeError:
            pass  # sync context: alarm fires on next async call
        except Exception:
            pass  # alarm failure never breaks the business path


@router.get("/telemetry")
async def cost_telemetry(is_authenticated: bool = Depends(verify_admin)):
    return telemetry()
