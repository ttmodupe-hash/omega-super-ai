"""Shared pytest fixtures.

Batch F: rate-limit buckets are per-IP sliding windows, and every TestClient
request shares the IP "testclient". Without a reset between tests, suites would
interfere through the buckets (e.g. the recalibrate limit would trip unrelated
later tests). Resetting here keeps every test hermetic.
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


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    """Pin the anyio plugin to asyncio only (trio is not a dependency)."""
    return request.param
