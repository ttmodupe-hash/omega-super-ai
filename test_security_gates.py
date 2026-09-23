"""
OMEGA-LUQI High-Load Security Validation Suite.

Stress-tests the 30% Human Intervention Gate under extreme concurrency to
guarantee sensitive corporate financial actions never slip past the sign-off wall.

Fixed from the pasted version:
- assertions now match the real orchestrator contract ("Human verification required")
- each thread owns its own TestClient (httpx clients are not thread-safe)
- admin secret read from env with the engine's real default
"""
import os
import concurrent.futures

import pytest
from fastapi.testclient import TestClient

from core.main import app, TaskStatus

ADMIN_SECRET = os.getenv("LUQI_ADMIN_SECRET", "SuperSecretAdminKey123")


@pytest.fixture
def secure_admin_header():
    """Security key for valid human override gates."""
    return {"X-Luqi-Admin-Auth": ADMIN_SECRET}


def make_client():
    return TestClient(app)


def test_tax_engine_strict_human_gate_lock(secure_admin_header):
    """Tax/financial pipelines compute but enforce a hard halt - no auto-execution."""
    client = make_client()
    payload = {
        "student_tier": "university",
        "action_type": "process_payment",
        "payload": {
            "item": "SARS_Corporate_Tax_Return_Q3",
            "gross_revenue": 1500000.00,
            "allowable_expenses": 450000.00,
        },
    }

    response = client.post("/v1/agent/execute", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == TaskStatus.PENDING_HUMAN_APPROVAL
    assert "Human verification required" in data["required_human_action"]


def _send_concurrent_tax_request(_):
    """Simulates rapid corporate accounting inputs hitting the cluster."""
    payload = {
        "student_tier": "global_premium",
        "action_type": "process_payment",
        "payload": {"item": "Automated_SARS_Filing_Batch_Load"},
    }
    return make_client().post("/v1/agent/execute", json=payload)


def test_gate_integrity_under_extreme_server_stress():
    """100 simultaneous filing attempts: none may bypass the human boundary.

    Rate limiting is disabled for this test's duration: it exercises the GATE
    under concurrency, not the throttle (100 requests in seconds would trip the
    60/minute global bucket, and a 429 proves nothing about the gate - the
    request never reaches it). Batch F owns limit coverage."""
    from core.rate_limiter import limiter
    limiter.enabled = False
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(_send_concurrent_tax_request, range(100)))
    finally:
        limiter.enabled = True

    for response in results:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.PENDING_HUMAN_APPROVAL
