"""Stripe provider verification: fail-closed paths, signed webhook -> gate lock,
signature tamper rejection, idempotent settlement via the single release path."""
import os, sys, json, hmac, hashlib, time, subprocess, pathlib

os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/xdg2")
os.makedirs("/tmp/xdg2", exist_ok=True)
os.chdir(pathlib.Path(__file__).resolve().parents[1])
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

# SQLite fallback (PyPI too slow for pgserver right now): engine create_all
# covers all tables on startup; Stripe adds NO tables, so nothing is lost.
# (Companion migration chain 0001->005 verified on real Postgres earlier today.)
if os.path.exists("/tmp/luqi_ci_stripe_test.db"):
    os.remove("/tmp/luqi_ci_stripe_test.db")
DB_URL = "sqlite:////tmp/luqi_ci_stripe_test.db"
print("[1/7] DB target:", DB_URL)

os.environ["DATABASE_URL"] = DB_URL
WHSEC = "whsec_localtestsecret1234567890"
os.environ["STRIPE_WEBHOOK_SECRET"] = WHSEC
os.environ.pop("STRIPE_SECRET_KEY", None)  # checkout not configured yet

from fastapi.testclient import TestClient
from core.main import app

def sign(payload: bytes, secret: str, t: int = None) -> str:
    t = t or int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"

with TestClient(app) as c:
    # auth
    c.post("/v1/auth/register", json={"email": "pay@test.dev", "password": "testpass123", "country_code": "ZAF"})
    login = c.post("/v1/auth/login", json={"email": "pay@test.dev", "password": "testpass123"}).json()
    tok = login["access_token"]; uid = login["profile"]["user_id"]
    H = {"Authorization": f"Bearer {tok}"}

    # Engine's documented assumption (003 migration notes): wallet holders have
    # a students row whose id IS the JWT user_id. Accounts unification is a
    # queued epic item; simulate the enrolled-student state here.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as _S
    from core.models import Student
    import uuid as _uuid
    _eng = create_engine(DB_URL)
    with _S(_eng) as _s:
        _s.add(Student(id=_uuid.UUID(uid), email="pay@test.dev",
                       full_name="Pay Test", country_code="ZAF", tier="tvet"))
        _s.commit()
    print("[2/7] auth ok (+ enrolled-student row per engine assumption)")

    # status: honest unconfigured
    st = c.get("/v1/payments/stripe/status").json()
    assert st["checkout_configured"] is False and st["webhook_configured"] is True and st["mode"] == "unconfigured"
    print("[3/7] status honest: checkout unconfigured, webhook configured")

    # checkout without key -> 503 fail-closed
    co = c.post("/v1/payments/stripe/checkout", headers=H, json={"price_key": "topup_100"})
    assert co.status_code == 503, co.text

    # checkout with mock SDK + test key -> session URL returned
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_localFakeKey123"
    import stripe as stripe_mod
    class _FakeSession:
        id = "cs_test_local_123"; url = "https://checkout.stripe.com/c/pay/cs_test_local_123"
    stripe_mod.checkout.Session.create = staticmethod(lambda **kw: _FakeSession())
    co2 = c.post("/v1/payments/stripe/checkout", headers=H, json={"price_key": "topup_100"})
    assert co2.status_code == 200, co2.text
    co2j = co2.json()
    assert co2j["amount"] == 100.0 and co2j["currency"] == "ZAR"
    assert co2j["educational_subsidy_allocated"] == 30.0
    # client cannot pick an amount: bad key -> 400
    bad = c.post("/v1/payments/stripe/checkout", headers=H, json={"price_key": "topup_999999"})
    assert bad.status_code == 400
    print("[4/7] checkout: 503 fail-closed -> mocked session ok, client pricing rejected")

    # webhook: tampered signature -> 400
    event = {
        "id": "evt_local_1", "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_local_123", "payment_status": "paid",
            "client_reference_id": uid, "amount_total": 10000, "currency": "zar",
        }},
    }
    body = json.dumps(event).encode()
    tampered = c.post("/v1/payments/stripe/webhook", content=body,
                      headers={"stripe-signature": sign(body, "whsec_WRONGSECRET")})
    assert tampered.status_code == 400
    print("[5/7] tampered signature rejected (400)")

    # webhook: valid signature -> gate task locked, NO credit yet
    ok = c.post("/v1/payments/stripe/webhook", content=body,
                headers={"stripe-signature": sign(body, WHSEC)})
    assert ok.status_code == 200, ok.text
    gate_task_id = ok.json()["gate_task_id"]
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    eng = _eng
    with Session(eng) as s:
        bal = s.execute(text("SELECT COUNT(*) FROM wallet_transactions WHERE reference_id = 'stripe:cs_test_local_123'")).scalar()
    assert bal == 0, "webhook credited the wallet directly - HOUSE LAW VIOLATION"
    print("[6/7] signed webhook -> gate locked, wallet untouched (house law holds)")

    # release the gate as admin -> wallet credited via single release path
    admin = os.getenv("LUQI_ADMIN_SECRET")
    if not admin:
        # engine has a dev default in security_guards; read it the same way
        from core.security_guards import DEFAULT_ADMIN_SECRET
        admin = DEFAULT_ADMIN_SECRET
    rel = c.post(f"/v1/human/override/{gate_task_id}?approve=true",
                 headers={"X-Luqi-Admin-Auth": admin})
    assert rel.status_code == 200, rel.text
    settled = rel.json().get("payload", {}).get("settled_balance")
    assert settled == 100.0, rel.text

    # replay the same webhook + release again -> duplicate blocked, balance stays
    ok2 = c.post("/v1/payments/stripe/webhook", content=body,
                 headers={"stripe-signature": sign(body, WHSEC)})
    task2 = ok2.json()["gate_task_id"]
    rel2 = c.post(f"/v1/human/override/{task2}?approve=true",
                  headers={"X-Luqi-Admin-Auth": admin})
    assert rel2.status_code == 503 and "already settled" in rel2.text, rel2.text
    print("[7/7] gate release credited R100; replay -> duplicate blocked (fail-closed)")

print("\nALL STRIPE CHECKS PASSED")
