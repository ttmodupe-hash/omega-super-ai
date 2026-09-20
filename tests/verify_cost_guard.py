"""verify_cost_guard.py — lock the fail-closed cost circuit-breaker.

Why this exists: the engine is self-funded and pre-revenue. Before this guard,
cost was only MEASURED and an SMS alarm fired at 80% — nothing STOPPED spend.
A runaway agent loop or free-tier abuse could burn the whole monthly budget.
Now enforce_budget() flips closed at COST_HARD_STOP_PCT (default 100) and the
unified client refuses new upstream calls with HTTP 429 BEFORE any money moves.

Covers:
1. Telemetry math: chars/4 token estimate, rates, pct-of-budget.
2. enforce_budget: allowed under limit, blocked at/over, COST_HARD_STOP_PCT env.
3. chat_completion contract: 429 when tripped and ZERO upstream HTTP calls;
   missing-key 500 still takes precedence; success path untouched.
4. Alarm vs breaker: 80-99% warns but does NOT block (default stop=100).

Run: python tests/verify_cost_guard.py   (repo root, fastapi/pydantic/requests installed)
"""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# Controlled env BEFORE importing engine modules
os.environ.pop("MONTHLY_TOKEN_BUDGET_USD", None)
os.environ.pop("COST_HARD_STOP_PCT", None)

import requests  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import core.cost_telemetry as ct  # noqa: E402
from core.kimi_client import chat_completion  # noqa: E402


def reset(budget=None, stop=None):
    ct._counts.clear()
    ct._alarm_day.update(day="", fired=False)
    if budget is None:
        os.environ.pop("MONTHLY_TOKEN_BUDGET_USD", None)
    else:
        os.environ["MONTHLY_TOKEN_BUDGET_USD"] = str(budget)
    if stop is None:
        os.environ.pop("COST_HARD_STOP_PCT", None)
    else:
        os.environ["COST_HARD_STOP_PCT"] = str(stop)


class _FakeResponse:
    status_code = 200
    text = "OK"

    def json(self):
        return {"choices": [{"message": {"content": "{\"ok\": true}"}}]}


class _PostRecorder:
    def __init__(self):
        self.calls = 0

    def __call__(self, *a, **kw):
        self.calls += 1
        return _FakeResponse()


print("== 1. Telemetry math ==")
reset(budget=100)
ct.bump("kimi", 4_000_000)  # 4M chars -> 1M tokens -> $3.00 at kimi in-rate
t = ct.telemetry()
check("estimate: 4M chars = $3.00", t["estimated_spend_usd"] == 3.0, str(t["estimated_spend_usd"]))
check("pct of $100 budget = 3.0%", t["pct_of_budget"] == 3.0)
check("hard stop fields present", "hard_stop_pct" in t and "hard_stop_triggered" in t)
check("unknown provider falls back to kimi rates",
      (reset(budget=100), ct.bump("unknown-llm", 4_000_000), ct.telemetry()["estimated_spend_usd"])[2] == 3.0)

print("== 2. enforce_budget gate ==")
reset(budget=100)
ct.bump("kimi", 4_000_000)  # 3%
allowed, snap = ct.enforce_budget()
check("3% -> allowed", allowed is True)
reset(budget=3)  # spend exactly at 100%
ct.bump("kimi", 4_000_000)  # $3.00 of $3.00
allowed, snap = ct.enforce_budget()
check("100% -> BLOCKED", allowed is False)
check("snapshot reports hard_stop_triggered", snap["hard_stop_triggered"] is True)
reset(budget=10, stop=50)
ct.bump("kimi", 8_000_000)  # $6.00 = 60% of $10
allowed, snap = ct.enforce_budget()
check("COST_HARD_STOP_PCT=50 blocks at 60%", allowed is False and snap["hard_stop_pct"] == 50.0)
reset(budget=10, stop=50)
ct.bump("kimi", 4_000_000)  # $3.00 = 30%
allowed, _ = ct.enforce_budget()
check("30% under custom stop -> allowed", allowed is True)

print("== 3. chat_completion contract ==")
recorder = _PostRecorder()
real_post = requests.post
requests.post = recorder
try:
    reset(budget=3)
    ct.bump("kimi", 4_000_000)  # 100% -> tripped
    os.environ["KIMI_API_KEY"] = "test-key"
    try:
        chat_completion("sys", "user")
        check("tripped budget -> 429 raised", False)
    except HTTPException as e:
        check("tripped budget -> 429 raised", e.status_code == 429, f"got {e.status_code}")
        check("429 detail is honest (no upstream call)", "No upstream call was made" in e.detail)
    check("ZERO upstream HTTP calls when tripped", recorder.calls == 0, f"calls={recorder.calls}")

    reset(budget=3)
    ct.bump("kimi", 4_000_000)  # tripped again
    os.environ.pop("KIMI_API_KEY", None)
    try:
        chat_completion("sys", "user")
        check("missing key still 500 (precedence over breaker)", False)
    except HTTPException as e:
        check("missing key still 500 (precedence over breaker)", e.status_code == 500, f"got {e.status_code}")

    reset(budget=100)
    os.environ["KIMI_API_KEY"] = "test-key"
    out = chat_completion("sys", "user")
    check("success path returns content", out == "{\"ok\": true}", repr(out))
    check("success path made exactly 1 upstream call", recorder.calls == 1, f"calls={recorder.calls}")
    check("successful call counted in telemetry", ct.telemetry()["by_provider"]["kimi"]["calls"] == 1)
finally:
    requests.post = real_post
    os.environ.pop("KIMI_API_KEY", None)

print("== 4. Alarm warns, breaker blocks - they are different ==")
reset(budget=100)  # default stop = 100
ct.bump("kimi", int(4_000_000 * 28.33))  # ~85% -> alarm zone
t = ct.telemetry()
allowed, _ = ct.enforce_budget()
check("85% -> alarm_triggered", t["alarm_triggered"] is True, f"pct={t['pct_of_budget']}")
check("85% -> still ALLOWED (warning only)", allowed is True)

reset()
failed = [r for r in _RESULTS if not r[1]]
print(f"\n{'=' * 50}\nRESULT: {len(_RESULTS) - len(failed)}/{len(_RESULTS)} PASS, {len(failed)} FAIL")
sys.exit(1 if failed else 0)
