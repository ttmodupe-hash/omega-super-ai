"""
OMEGA-LUQI Rate Limiter (Batch F) - sliding-window protection for expensive surfaces.

Three layers, all keyed on the REAL client IP:
  - global bucket (application_limits via SlowAPIMiddleware): every request counts
  - per-route buckets on CPU/LLM-intensive endpoints (decorators below)
  - per-ticket brute-force lockout stays in ops_approvals (separate mechanism)

Keying: behind Railway's proxy, request.client.host is the proxy IP - one shared
bucket for the entire internet. X-Forwarded-For carries the real client, so we
prefer its first hop. Direct connections fall back to the peer address.

SlowAPI semantics verified empirically (0.1.10):
  - default_limits does NOT apply to undecorated routes; application_limits +
    SlowAPIMiddleware is the only true app-wide bucket
  - limiter.reset() clears all buckets (the test suite resets between tests -
    see tests/conftest.py; TestClient shares one IP, so without the reset the
    suites would interfere through the buckets)

Disable entirely with LUQI_RATE_LIMIT=off; tune via RATE_LIMIT_* env vars.
"""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


def client_key(request: Request) -> str:
    """Real client identity: first X-Forwarded-For hop, else the direct peer."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


ENABLED = os.getenv("LUQI_RATE_LIMIT", "on") != "off"
GLOBAL_LIMIT = os.getenv("RATE_LIMIT_GLOBAL", "60/minute")
RECALIBRATE_LIMIT = os.getenv("RATE_LIMIT_RECALIBRATE", "5/minute")    # LLM + sandbox
SELF_DIAG_LIMIT = os.getenv("RATE_LIMIT_SELF_DIAG", "10/minute")       # LLM quota
RESPOND_LIMIT = os.getenv("RATE_LIMIT_RESPOND", "15/minute")           # token endpoint
TRUTH_LIMIT = os.getenv("RATE_LIMIT_TRUTH", "5/minute")               # dual-agent LLM loop

limiter = Limiter(key_func=client_key, enabled=ENABLED,
                  application_limits=[GLOBAL_LIMIT])


def setup_rate_limiting(app) -> None:
    """Bind limiter state, the 429 handler, and the global-bucket middleware."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)   # application_limits only fire via middleware


def reset() -> None:
    """Test hook: clear every bucket (per-IP windows would otherwise leak
    across tests sharing the TestClient IP)."""
    limiter.reset()
