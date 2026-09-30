"""RESILIENCE-1 battery: bounded retry + fail-fast circuit breaker on the ONE
upstream fault path (kimi_client.chat_completion). Zero network — requests.post
is stubbed. Every check passes or the script exits 1.

Proves:
  * Success and chat_dict wrapper contract preserved.
  * Transient network faults and retryable statuses are retried (bounded).
  * 400 is a real answer: never retried, and it proves upstream is alive
    (breaker failure count resets — cost law: no wasted retries).
  * After FAILURE_THRESHOLD consecutive faults the breaker OPENS and calls
    fail FAST: HTTPException 503 naming the circuit, ZERO upstream calls.
  * Cooldown -> half-open single probe -> close on success / re-open on failure.
  * Budget hard-stop stays FIRST and fail-closed (429, no upstream call).
  * Missing key stays fail-closed (500, no upstream call).
  * bump() counts ONCE per logical call, never per retry attempt.
  * Breaker status honestly declares itself process-local.
"""
import os
import sys
import time
import pathlib
import types

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import requests  # real module, only for the exception classes
from fastapi import HTTPException

from core import resilience as rs
from core import kimi_client as kc
from core import cost_telemetry as ct

# Speed law for the battery: backoff delays are behaviour, not timing.
rs.BACKOFF_BASE_S = 0.0
rs.BACKOFF_CAP_S = 0.0

os.environ["KIMI_API_KEY"] = "test-key-not-real"

_failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"[PASS] {name} {extra}")
    else:
        print(f"[FAIL] {name} {extra}")
        _failures.append(name)


class FakeResp:
    def __init__(self, status_code=200, content="ok", text=""):
        self.status_code = status_code
        self.text = text or f"status {status_code}"
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


post_calls = {"n": 0}
bump_calls = {"n": 0}


def install_post(behaviours):
    """behaviours: list of FakeResp or Exception instances, popped in order."""
    queue = list(behaviours)

    def fake_post(*a, **kw):
        post_calls["n"] += 1
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    kc.requests = types.SimpleNamespace(post=fake_post, exceptions=requests.exceptions)


def reset(budget_allowed=True):
    post_calls["n"] = 0
    bump_calls["n"] = 0
    kc.KIMI_BREAKER.after_success()
    ct.bump = lambda *a, **kw: bump_calls.__setitem__("n", bump_calls["n"] + 1)
    ct.maybe_alarm = lambda *a, **kw: None
    ct.enforce_budget = lambda: (budget_allowed, {
        "estimated_spend_usd": 99.0, "hard_stop_pct": 100, "budget_usd": 100.0})


# ── 1. Success contract preserved ─────────────────────────────────────────
reset()
install_post([FakeResp(200, "hello")])
out = kc.chat_completion("sys", "usr")
check("success returns assistant content", out == "hello", f"got {out!r}")
check("exactly one upstream call on success", post_calls["n"] == 1)
check("bump counted once", bump_calls["n"] == 1)

reset()
install_post([FakeResp(200, "wrapped")])
d = kc.chat_dict("sys", "usr")
check("chat_dict wrapper shape preserved",
      d["choices"][0]["message"]["content"] == "wrapped")

# ── 2. Transient network fault retried, then success ──────────────────────
reset()
install_post([requests.exceptions.ConnectionError("boom"), FakeResp(200, "recovered")])
out = kc.chat_completion("sys", "usr")
check("transient network fault retried to success", out == "recovered")
check("two upstream calls (1 fail + 1 retry)", post_calls["n"] == 2)
check("bump still once per LOGICAL call", bump_calls["n"] == 1)

# ── 3. Retryable HTTP status (503) retried ────────────────────────────────
reset()
install_post([FakeResp(503), FakeResp(200, "after-503")])
out = kc.chat_completion("sys", "usr")
check("retryable 503 retried to success", out == "after-503")
check("two upstream calls for 503-then-200", post_calls["n"] == 2)

# ── 4. Exhausted retryable status raises the original fault ───────────────
reset()
install_post([FakeResp(503), FakeResp(503), FakeResp(503), FakeResp(503)])
try:
    kc.chat_completion("sys", "usr")
    check("exhausted retries raise HTTPException", False)
except HTTPException as e:
    check("exhausted retries raise HTTPException 503", e.status_code == 503)
    check("original 'Kimi Engine Fault' detail preserved", "Kimi Engine Fault" in str(e.detail))
check("bounded at MAX_ATTEMPTS (3) upstream calls", post_calls["n"] == 3, f"got {post_calls['n']}")

# ── 5. 400 is a real answer: never retried, proves upstream alive ─────────
reset()
kc.KIMI_BREAKER._consecutive_failures = 3  # pre-existing transient history
install_post([FakeResp(400, text="bad request")])
try:
    kc.chat_completion("sys", "usr")
    check("400 raises HTTPException", False)
except HTTPException as e:
    check("400 raises HTTPException 400", e.status_code == 400)
check("400 NOT retried (cost law)", post_calls["n"] == 1)
check("definitive answer resets failure count (upstream alive)",
      kc.KIMI_BREAKER.status()["consecutive_failures"] == 0)

# ── 6. Breaker OPENS after threshold, then fails FAST ─────────────────────
reset()
always_down = [requests.exceptions.ConnectionError("down")] * 20
install_post(always_down)
try:
    kc.chat_completion("sys", "usr")
    check("first failing call raises RequestException", False)
except requests.exceptions.RequestException:
    check("first failing call raises RequestException (contract -> 503)", True)
check("3 attempts consumed on first failing call", post_calls["n"] == 3, f"got {post_calls['n']}")
try:
    kc.chat_completion("sys", "usr")
    check("second call surfaces a fault", False)
except HTTPException as e:
    check("breaker opened mid-call -> HTTPException 503", e.status_code == 503)
    check("503 detail names the circuit", "circuit" in str(e.detail))
check("breaker state is OPEN", kc.KIMI_BREAKER.status()["state"] == "open")
calls_at_open = post_calls["n"]
try:
    kc.chat_completion("sys", "usr")
    check("open breaker surfaces a fault", False)
except HTTPException as e:
    check("OPEN breaker fails fast with 503", e.status_code == 503)
    check("fail-fast says no upstream call made", "no upstream call made" in str(e.detail))
check("ZERO upstream calls while OPEN", post_calls["n"] == calls_at_open,
      f"calls frozen at {calls_at_open}")

# ── 7. Budget hard-stop stays FIRST and fail-closed ───────────────────────
reset(budget_allowed=False)
install_post([FakeResp(200)])
try:
    kc.chat_completion("sys", "usr")
    check("tripped budget raises", False)
except HTTPException as e:
    check("tripped budget -> 429", e.status_code == 429)
    check("budget fault declares zero upstream spend", "No upstream call was made" in str(e.detail))
check("budget stop made NO upstream call", post_calls["n"] == 0)

# ── 8. Missing key stays fail-closed ──────────────────────────────────────
reset()
install_post([FakeResp(200)])
saved = os.environ.pop("KIMI_API_KEY")
try:
    kc.chat_completion("sys", "usr")
    check("missing key raises", False)
except HTTPException as e:
    check("missing key -> 500 fail-closed", e.status_code == 500)
finally:
    os.environ["KIMI_API_KEY"] = saved
check("missing key made NO upstream call", post_calls["n"] == 0)

# ── 9. Breaker unit semantics: cooldown, half-open probe, re-open ─────────
b = rs.CircuitBreaker("unit", threshold=1, cooldown_s=0.05)
try:
    rs.call_with_resilience(lambda: (_ for _ in ()).throw(OSError("x")),
                            b, (OSError,), lambda e: False, max_attempts=1)
except OSError:
    pass
check("unit breaker opens at threshold 1", b.status()["state"] == "open")
try:
    b.before_call()
    check("open breaker blocks call", False)
except rs.CircuitOpenError:
    check("open breaker blocks call (CircuitOpenError)", True)
time.sleep(0.06)
b.before_call()  # half-open probe admitted
check("cooldown admits half-open probe", b.status()["state"] == "half-open")
try:
    b.before_call()
    check("second concurrent probe blocked", False)
except rs.CircuitOpenError as e:
    check("second concurrent probe blocked", "HALF-OPEN" in str(e))
b.after_success()  # the admitted probe completes successfully
check("successful probe closes breaker", b.status()["state"] == "closed")

# Probe success through the real wrapper: open -> cooldown -> probe ok -> closed
b2 = rs.CircuitBreaker("unit2", threshold=1, cooldown_s=0.05)
try:
    rs.call_with_resilience(lambda: (_ for _ in ()).throw(OSError("x")),
                            b2, (OSError,), lambda e: False, max_attempts=1)
except OSError:
    pass
time.sleep(0.06)
out = rs.call_with_resilience(lambda: "probe-ok", b2, (OSError,), lambda e: False, max_attempts=1)
check("wrapper probe success closes breaker", out == "probe-ok" and b2.status()["state"] == "closed")

# Probe failure through the real wrapper: open -> cooldown -> probe fails -> re-open
b3 = rs.CircuitBreaker("unit3", threshold=1, cooldown_s=0.05)
try:
    rs.call_with_resilience(lambda: (_ for _ in ()).throw(OSError("x")),
                            b3, (OSError,), lambda e: False, max_attempts=1)
except OSError:
    pass
time.sleep(0.06)
try:
    rs.call_with_resilience(lambda: (_ for _ in ()).throw(OSError("y")),
                            b3, (OSError,), lambda e: False, max_attempts=1)
except OSError:
    pass
check("failed probe RE-OPENS breaker", b3.status()["state"] == "open")

# ── 10. Honest introspection ──────────────────────────────────────────────
st = kc.kimi_breaker_status()
check("breaker named honestly", st["name"] == "kimi-upstream")
check("status honestly declares process-local scope", "process-local" in st["scope"])

# ── Verdict ───────────────────────────────────────────────────────────────
if _failures:
    print(f"\nRESILIENCE-1 BATTERY: {len(_failures)} FAILURES -> {_failures}")
    sys.exit(1)
print("\nRESILIENCE-1 BATTERY: all checks passed — bounded retries, fail-fast "
      "breaker, fail-closed cost/key gates, zero-dep.")
