"""
OMEGA-LUQI Wallet Chain Integration Test - CI ONLY.

Exercises the full money path against a real PostgreSQL service:
  gateway-styled task -> gate release -> ledger credit -> audit row -> RLS visibility.
Skips everywhere sqlalchemy is unavailable (local dev without DB).

Requires the workflow's Postgres service + DATABASE_URL (already configured
in .github/workflows/omega_luqi_sync.yml).
"""
import importlib.util
import os
import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("sqlalchemy") is None,
    reason="requires sqlalchemy + the CI Postgres service",
)

ADMIN_SECRET = os.getenv("LUQI_ADMIN_SECRET", "SuperSecretAdminKey123")
ADMIN_HEADERS = {"X-Luqi-Admin-Auth": ADMIN_SECRET}


@pytest.fixture
def client_with_db():
    from core.main import app
    with TestClient(app) as client:   # context manager RUNS startup -> init_db -> engine
        assert getattr(app.state, "db_engine", None) is not None, \
            "CI must provide DATABASE_URL so the wallet chain can settle"
        yield client
    app.state.db_engine = None  # never leak a live engine into other tests


@pytest.fixture
def funded_student():
    from core.main import app
    from core.models import Student, TierType
    from core.rls import attach_rls_context
    from sqlalchemy.orm import Session

    uid = uuid.uuid4()
    with Session(app.state.db_engine) as s:
        attach_rls_context(s, "ZAF")
        s.add(Student(id=uid, email=f"itest-{uid}@luqi.ai",
                      full_name="CI Wallet Test", country_code="ZAF", tier=TierType.TVET))
        s.commit()
    return uid


def _wallet_task(client, reference, student_id):
    return client.post("/v1/agent/execute", json={
        "student_tier": "tvet", "action_type": "process_payment",
        "payload": {"item": "wallet top-up", "reference": reference,
                     "student_id": str(student_id), "amount": 450.00},
    }).json()


def test_full_wallet_settlement_happy_path(client_with_db, funded_student):
    from core.main import app
    from core.rls import attach_rls_context
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    task = _wallet_task(client_with_db, f"PSK-CI-{uuid.uuid4().hex[:12]}", funded_student)
    assert task["status"] == "pending_human_approval"

    released = client_with_db.post(
        f"/v1/human/override/{task['task_id']}?approve=true", headers=ADMIN_HEADERS)
    assert released.status_code == 200
    assert released.json()["payload"]["settled_balance"] == pytest.approx(450.00)

    # Ledger row is visible under the student's RLS country context
    with Session(app.state.db_engine) as s:
        attach_rls_context(s, "ZAF")
        bal = s.execute(
            text("SELECT balance FROM wallet_ledgers WHERE student_id = :i"),
            {"i": funded_student}).scalar()
    assert float(bal) == pytest.approx(450.00)

    # Audit trail recorded the human release
    with Session(app.state.db_engine) as s:
        n = s.execute(
            text("SELECT count(*) FROM system_audit_logs WHERE task_id = :t"),
            {"t": task["task_id"]}).scalar()
    assert n == 1

    # Released task cannot be re-released
    again = client_with_db.post(
        f"/v1/human/override/{task['task_id']}?approve=true", headers=ADMIN_HEADERS)
    assert again.status_code == 400


def test_duplicate_payment_reference_refused(client_with_db, funded_student):
    from core.main_types import LuqiState
    from core.wallet_service import credit_ledger_for_task, WalletCreditError

    ref = f"PSK-DUP-{uuid.uuid4().hex[:12]}"
    _wallet_task(client_with_db, ref, funded_student)
    released = client_with_db.post(
        f"/v1/human/override/{client_with_db.get('/v1/monitor/gate-queue', headers=ADMIN_HEADERS).json()['pending'][-1]['task_id']}?approve=true",
        headers=ADMIN_HEADERS)
    assert released.status_code == 200

    # Same reference a second time must be refused - at the service level
    from core.main import app
    dup = LuqiState(student_tier="tvet", action_type="process_payment",
                    payload={"reference": ref, "student_id": str(funded_student), "amount": 450.00})
    with pytest.raises(WalletCreditError):
        credit_ledger_for_task(dup, app.state.db_engine)
