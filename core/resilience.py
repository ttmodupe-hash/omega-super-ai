"""
OMEGA-LUQI Upstream Resilience (RESILIENCE-1) — 2026-09-30

Origin: an external paste asked for "circuit breakers & exponential backoff"
via tenacity + Celery/RabbitMQ + LangGraph state machines.

House verdicts:
  * Celery/RabbitMQ worker fleets: REJECTED (REJECT-6 precedent, cost law).
  * LangGraph immutable StateGraph: REJECTED (REJECT-6/7 precedent).
  * tenacity: REJECTED as a dependency — the needed behaviour is ~60 lines
    of stdlib code; a paid-weight dependency for that is image bloat.
  * Circuit breaker + bounded jittered backoff: HARVESTED — as this zero-dep
    module, injected at the ONE upstream fault path (kimi_client), not
    sprinkled speculatively across the tree (scope law).

Semantics (deterministic, honest):
  * CLOSED   — normal operation; failures are counted.
  * OPEN     — after FAILURE_THRESHOLD consecutive transient faults, calls
               fail FAST (no upstream request, no 30s timeout stall) for
               COOLDOWN_S seconds. The caller gets an explicit fault naming
               the breaker — never a silent fake answer.
  * HALF-OPEN— after the cooldown, exactly ONE probe call is allowed through;
               success closes the breaker, failure re-opens it.

Thread-safe (the engine calls upstream from a thread pool). State is
process-local and honestly reported by breaker_status() — it resets on
restart, and says so.
"""
import random
import threading
import time
from typing import Any, Callable, Dict, Tuple, Type

FAILURE_THRESHOLD = 5      # consecutive transient faults before OPEN
COOLDOWN_S = 60.0          # fail-fast window before the half-open probe
MAX_ATTEMPTS = 3           # 1 initial + 2 retries, bounded
BACKOFF_BASE_S = 0.5       # 0.5s, then ~1.0s (+ jitter), capped
BACKOFF_CAP_S = 2.0

# Transient = worth retrying. 4xx client faults (except 408/429) are real
# answers about the request itself — retrying them wastes money (cost law).
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class CircuitOpenError(RuntimeError):
    """Raised when the breaker is OPEN: fail-fast, honestly named."""


class CircuitBreaker:
    def __init__(self, name: str,
                 threshold: int = FAILURE_THRESHOLD,
                 cooldown_s: float = COOLDOWN_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._clock = clock
        self._lock = threading.Lock()
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._probe_in_flight = False

    def before_call(self) -> None:
        """Gate every upstream attempt. Raises CircuitOpenError to fail fast."""
        with self._lock:
            if self._state == "open":
                if self._clock() - self._opened_at >= self.cooldown_s:
                    self._state = "half-open"   # allow exactly one probe
                    self._probe_in_flight = True
                    return
                raise CircuitOpenError(
                    f"upstream circuit '{self.name}' OPEN — failing fast "
                    f"(cooldown {self.cooldown_s:.0f}s; no upstream call made)")
            if self._state == "half-open":
                if self._probe_in_flight:
                    raise CircuitOpenError(
                        f"upstream circuit '{self.name}' HALF-OPEN — probe in "
                        "flight, failing fast")
                self._probe_in_flight = True

    def after_success(self) -> None:
        with self._lock:
            self._state = "closed"
            self._consecutive_failures = 0
            self._probe_in_flight = False

    def after_failure(self) -> None:
        with self._lock:
            self._probe_in_flight = False
            self._consecutive_failures += 1
            if self._state == "half-open" or self._consecutive_failures >= self.threshold:
                self._state = "open"
                self._opened_at = self._clock()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"name": self.name, "state": self._state,
                    "consecutive_failures": self._consecutive_failures,
                    "threshold": self.threshold, "cooldown_s": self.cooldown_s,
                    "scope": "process-local — resets on restart (honest)"}


def call_with_resilience(fn: Callable[[], Any],
                         breaker: CircuitBreaker,
                         transient_exceptions: Tuple[Type[BaseException], ...],
                         is_transient_status: Callable[[BaseException], bool],
                         max_attempts: int = MAX_ATTEMPTS) -> Any:
    """Bounded retry with jittered exponential backoff behind the breaker.

    fn() performs ONE upstream attempt. transient exceptions and retryable
    statuses consume another attempt; anything else propagates immediately
    (a 400 is a real answer about the request — never retried, cost law).
    """
    attempt = 0
    while True:
        attempt += 1
        breaker.before_call()
        try:
            out = fn()
        except transient_exceptions as exc:
            fault = exc                      # transient network-class fault
        except Exception as exc:
            if not is_transient_status(exc):
                breaker.after_success()      # a definitive answer (even a 400) means upstream is alive
                raise
            fault = exc                      # retryable upstream status
        else:
            breaker.after_success()
            return out
        breaker.after_failure()
        if attempt >= max_attempts:
            raise fault
        delay = min(BACKOFF_BASE_S * (2 ** (attempt - 1)), BACKOFF_CAP_S)
        time.sleep(delay + random.uniform(0, delay * 0.5))
