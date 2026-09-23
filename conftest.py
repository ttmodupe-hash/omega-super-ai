"""Shared pytest fixtures (repo-root suites).

Batch F: rate-limit buckets are per-IP sliding windows, and every TestClient
request shares the IP "testclient". Without a reset between tests, suites
interfere through the buckets (the 60/minute global application limit trips
mid-suite and cascades 429s onto unrelated tests). Resetting here keeps every
test hermetic. Mirrors tests/conftest.py (that file only governs tests/).
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    try:
        from core.rate_limiter import limiter
        limiter.reset()
    except Exception:
        pass
    yield
