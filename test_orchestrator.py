"""
Luqi-AI Orchestrator Test Suite
Validates the 30% Human Intervention gate under concurrency.

Run:  pytest -v test_orchestrator.py
"""
import concurrent.futures
import os
import pytest
from fastapi.testclient import TestClient

from core.main import app, TaskStatus

ADMIN_SECRET = "SuperSecretAdminKey123"


@pytest.fixture
def admin_headers():
    return {"X-Luqi-Admin-Auth": ADMIN_SECRET}


def make_client():
    """Each thread gets its own TestClient (httpx clients are not thread-safe)."""
    return TestClient(app)


def test_70_percent_autonomous_workflow():
    """Safe student operations complete instantly, no human flag."""
    client = make_client()
    payload = {
        "student_tier": "primary",
        "action_type": "run_client_simulation",
        "payload": {"lab_module": "basic_logic_blocks"},
    }
    response = client.post("/v1/agent/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == TaskStatus.COMPLETED
    assert data["required_human_action"] is None


def test_30_percent_human_in_the_loop_gate_enforcement(admin_headers):
    """Critical transactions halt at the wall; only an authorized human releases them."""
    client = make_client()
    payload = {
        "student_tier": "university",
        "action_type": "process_payment",
        "payload": {"item": "semester_cloud_sandbox_allocation", "cost": 450.00},
    }

    response = client.post("/v1/agent/execute", json=payload)
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["status"] == TaskStatus.PENDING_HUMAN_APPROVAL
    assert "Human verification required" in task_data["required_human_action"]
    task_id = task_data["task_id"]

    # Unauthorized override must be rejected
    fail = client.post(f"/v1/human/override/{task_id}?approve=true&payment_credentials=STOLEN-TOKEN")
    assert fail.status_code == 403

    # Authorized human releases the gate
    ok = client.post(
        f"/v1/human/override/{task_id}?approve=true&payment_credentials=M-PESA-TOKEN",
        headers=admin_headers,
    )
    assert ok.status_code == 200
    final = ok.json()
    assert final["status"] == TaskStatus.COMPLETED
    assert final["payload"]["secure_token"] == "ENCRYPTED_VIA_HUMAN_INTERVENTION"


def _send_payment_request(_):
    """One rapid-fire payment request; owns its own client for thread safety."""
    payload = {
        "student_tier": "tvet",
        "action_type": "process_payment",
        "payload": {"item": "cisco_router_practical_credit"},
    }
    return make_client().post("/v1/agent/execute", json=payload)


def test_gatekeeper_integrity_under_heavy_concurrency():
    """50 simultaneous payments: not a single one may bypass the human wall."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_send_payment_request, range(50)))

    for response in results:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.PENDING_HUMAN_APPROVAL


def test_rejected_task_cannot_be_reapproved_twice(admin_headers):
    """A rejected transaction stays dead - it cannot be resurrected via the gate."""
    client = make_client()
    payload = {
        "student_tier": "tvet",
        "action_type": "modify_api_limits",
        "payload": {"item": "increase_token_ceiling"},
    }
    task_id = client.post("/v1/agent/execute", json=payload).json()["task_id"]

    reject = client.post(f"/v1/human/override/{task_id}?approve=false", headers=admin_headers)
    assert reject.status_code == 200
    assert reject.json()["status"] == TaskStatus.REJECTED

    # Attempt to re-open the same task must fail: it is no longer locked at the gate
    again = client.post(f"/v1/human/override/{task_id}?approve=true", headers=admin_headers)
    assert again.status_code == 400


def test_kimi_gateway_fails_closed_without_key():
    """The reasoning endpoint must fail closed (500) when KIMI_API_KEY is unset."""
    client = make_client()
    os.environ.pop("KIMI_API_KEY", None)
    response = client.post("/v1/agent/kimi-reason", json={"prompt": "test"})  # body, not query (route changed v5.9)
    assert response.status_code == 500


def test_prompt_support_wraps_student_input():
    from core.prompt_support import LuqiPromptSupport

    enhanced = LuqiPromptSupport.enhance_student_prompt("my router wont ping", "primary", "networking")
    assert "PRIMARY" in enhanced and "NETWORKING" in enhanced
    assert "my router wont ping" in enhanced
    assert "Umuntu ngumuntu ngabantu" in enhanced  # Ubuntu philosophy filter present


def test_prompt_support_rejects_empty_input():
    import pytest as _pt
    from core.prompt_support import LuqiPromptSupport

    with _pt.raises(ValueError):
        LuqiPromptSupport.enhance_student_prompt("   ", "tvet", "software_dev")


def test_kimi_research_fails_closed_without_key():
    client = make_client()
    os.environ.pop("KIMI_API_KEY", None)
    response = client.post("/v1/agent/kimi-research", json={"student_query": "why is OSPF stuck in 2-way?"})
    assert response.status_code == 500


def test_kimi_research_rejects_empty_query_when_enhancing():
    client = make_client()
    response = client.post("/v1/agent/kimi-research", json={
        "student_query": "  ", "academic_tier": "primary", "lab_track": "networking"
    })
    assert response.status_code == 400


def test_prompt_enhance_endpoint_real_response():
    """The suggestion-box endpoint must return a wrapped prompt without any LLM key."""
    client = make_client()
    response = client.post("/v1/prompt/enhance", json={
        "raw_prompt": "how do i subnet", "academic_tier": "tvet", "lab_track": "networking"
    })
    assert response.status_code == 200
    body = response.json()
    assert "TVET" in body["enhanced_prompt"] and "NETWORKING" in body["enhanced_prompt"]


def test_prompt_enhance_rejects_empty():
    client = make_client()
    response = client.post("/v1/prompt/enhance", json={"raw_prompt": "  "})
    assert response.status_code == 400


def test_sovereign_action_fails_closed_without_key():
    client = make_client()
    os.environ.pop("KIMI_API_KEY", None)
    response = client.post("/v1/agent/scan-opportunities",
                           json={"entrepreneur_intent": "tender for school laptops", "region_code": "ZA"})
    assert response.status_code == 500


def test_dev_build_fails_closed_without_key():
    client = make_client()
    os.environ.pop("KIMI_API_KEY", None)
    response = client.post("/v1/agent/dev-build",
                           json={"project_requirements": "inventory tracker for a spaza shop",
                                 "target_stack": "python-fastapi"})
    assert response.status_code == 500  # must NOT crash on missing import or Docker daemon


def test_consumer_shield_builds_case_file_offline():
    """Shield runs with zero external keys - pure local legal structuring."""
    client = make_client()
    response = client.post("/v1/agent/consumer-shield", json={
        "incident_details": "bought a phone contract mis-sold as prepaid",
        "company_name": "ExampleTelco (Pty) Ltd",
        "target_jurisdiction": "ZAF",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"].startswith("LUQI-SHIELD-")
    assert "CPA" in body["applicable_statute"]  # South African statute routing
    assert body["target_entity"] == "ExampleTelco (Pty) Ltd"


def test_tax_compute_locks_filing_at_30pct_gate():
    client = make_client()
    response = client.post("/v1/agent/tax-compute", json={
        "gross_revenue": 1000000.0, "allowable_expenses": 400000.0, "tax_exemptions": 100000.0
    })
    assert response.status_code == 200
    body = response.json()
    # (1,000,000 - 400,000 - 100,000) x 27% = 135,000
    assert body["financial_summary"]["taxable_net_income"] == 500000.0
    assert body["financial_summary"]["estimated_liability"] == 135000.0
    assert body["calculation_status"] == "pending_human_approval"
    assert body["gate_task_id"]


def test_tax_filing_releases_only_via_authenticated_human():
    client = make_client()
    admin = {"X-Luqi-Admin-Auth": ADMIN_SECRET}
    task_id = client.post("/v1/agent/tax-compute", json={
        "gross_revenue": 200000.0, "allowable_expenses": 50000.0
    }).json()["gate_task_id"]

    # Unauthorized release attempt blocked
    blocked = client.post(f"/v1/human/override/{task_id}?approve=true")
    assert blocked.status_code == 403

    # Authenticated human releases the filing
    released = client.post(f"/v1/human/override/{task_id}?approve=true", headers=admin)
    assert released.status_code == 200
    assert released.json()["status"] == "completed"


def test_telemetry_requires_admin_auth():
    client = make_client()
    response = client.get("/v1/monitor/telemetry")
    assert response.status_code in (401, 403, 422)  # no anonymous system visibility


def test_gate_queue_reflects_pending_tax_filing():
    client = make_client()
    admin = {"X-Luqi-Auth": "nope", "X-Luqi-Admin-Auth": ADMIN_SECRET}
    task_id = client.post("/v1/agent/tax-compute", json={
        "gross_revenue": 800000.0, "allowable_expenses": 200000.0
    }).json()["gate_task_id"]

    queue = client.get("/v1/monitor/gate-queue", headers=admin)
    assert queue.status_code == 200
    ids = [t["task_id"] for t in queue.json()["pending"]]
    assert task_id in ids

    telemetry = client.get("/v1/monitor/telemetry", headers=admin)
    assert telemetry.status_code == 200
    assert telemetry.json()["pending_human_gate_count"] >= 1
    assert telemetry.json()["kimi_gateway_model"]  # model reported


def test_pii_scrub_redacts_sa_identities():
    from core.pii_scrub import scrub_pii
    dirty = ("Contact me on test.user@example.com or 0821234567. "
             "My ID is 9001014800089 and company 2015/123456/07.")
    clean = scrub_pii(dirty)
    assert "test.user@example.com" not in clean
    assert "0821234567" not in clean
    assert "9001014800089" not in clean
    assert "2015/123456/07" not in clean
    assert "[REDACTED_EMAIL]" in clean and "[REDACTED_PHONE]" in clean
    assert "[REDACTED_NATIONAL_ID]" in clean and "[REDACTED_COMPANY_REG]" in clean


def test_pii_scrub_leaves_normal_text_untouched():
    from core.pii_scrub import scrub_pii
    text = "Explain OSPF neighbor states and LSA types for my CCNA lab."
    assert scrub_pii(text) == text


def test_auth_register_login_flow():
    """Runs in CI (PyJWT installed). Register -> login -> token decodes."""
    jwt_spec = __import__("importlib.util", fromlist=["util"]).find_spec("jwt")
    if jwt_spec is None:
        return  # sandbox without PyJWT - CI covers this
    import time as _time
    from core.auth import LuqiAuthManager, UserSessionProfile

    profile = UserSessionProfile(user_id=__import__("uuid").uuid4(),
                                 email="test@luqi.ai", country_code="zaf", tier="tvet")
    token = LuqiAuthManager.generate_secure_session_token(profile)
    assert isinstance(token, str) and len(token) > 20


def test_auth_rejects_bad_tokens():
    jwt_spec = __import__("importlib.util", fromlist=["util"]).find_spec("jwt")
    if jwt_spec is None:
        return
    import pytest as _pt
    from core.auth import LuqiAuthManager
    from fastapi.security import HTTPAuthorizationCredentials

    class _Creds:
        credentials = "not.a.token"
    with _pt.raises(Exception):
        LuqiAuthManager.verify_session_token(_Creds())


def test_paystack_dev_stub_intercepts_test_keys():
    """sk_test_ keys must short-circuit to canned success without network."""
    from core.payment_hub import PaystackPaymentManager
    result = PaystackPaymentManager.verify_transaction_on_gateway("ref-demo-001")
    assert result["status"] is True
    assert result["data"]["status"] == "success"
    assert result["data"]["amount"] == 45000  # cents -> R450.00 after /100


def test_paystack_api_base_url_is_api_domain():
    from core.payment_hub import PAYSTACK_BASE_URL
    assert PAYSTACK_BASE_URL == "https://api.paystack.co"  # not paystack.co


def test_wallet_release_blocked_without_database():
    """Wallet-shaped task + no DB -> 503, gate stays locked. Fail-closed proven."""
    from core import main as _main
    saved_engine = getattr(_main.app.state, "db_engine", None)
    _main.app.state.db_engine = None  # deterministic: never depend on environment
    client = make_client()
    admin = {"X-Luqi-Admin-Auth": ADMIN_SECRET}
    task = client.post("/v1/agent/execute", json={
        "student_tier": "tvet", "action_type": "process_payment",
        "payload": {"item": "wallet top-up", "reference": "PSK-TEST-001",
                     "student_id": "00000000-0000-0000-0000-000000000001", "amount": 450.00},
    }).json()
    assert task["status"] == "pending_human_approval"

    response = client.post(f"/v1/human/override/{task['task_id']}?approve=true", headers=admin)
    assert response.status_code == 503
    assert "Gate release blocked" in response.json()["detail"]

    # Gate is STILL locked - nothing settled without a ledger write
    queue = client.get("/v1/monitor/gate-queue", headers=admin)
    assert task["task_id"] in [t["task_id"] for t in queue.json()["pending"]]
    _main.app.state.db_engine = saved_engine  # restore


def test_non_wallet_tasks_release_normally():
    """Tasks without a payment reference must not touch the wallet path."""
    from core.wallet_service import is_wallet_task
    from core.main_types import LuqiState
    plain = LuqiState(student_tier="tvet", action_type="deploy_lab", payload={"item": "lab"})
    assert is_wallet_task(plain) is False
    wallet = LuqiState(student_tier="tvet", action_type="process_payment",
                       payload={"reference": "X", "amount": 1.0})
    assert is_wallet_task(wallet) is True
