"""Batch F guards - rate limiting enforced, audit feed live, credentials never leak.

The limit tests post code that fails the static gate ("import os") so no
subprocess ever spawns - the limiter is what is under test, not the sandbox.
"""
import os

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")
os.environ.setdefault("OPS_JOURNAL", "off")

from fastapi.testclient import TestClient
from core.main import app
from core import ops_approvals as oa
from core.rate_limiter import limiter

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


# ---------------- rate limiter ----------------
def test_recalibrate_limited_after_5_per_minute():
    limiter.reset()
    for i in range(5):
        r = client.post("/v1/ops/recalibrate", json={"code": "import os"}, headers=ADMIN)
        assert r.status_code == 200, f"request {i + 1} unexpectedly {r.status_code}"
    sixth = client.post("/v1/ops/recalibrate", json={"code": "import os"}, headers=ADMIN)
    assert sixth.status_code == 429                     # 6th inside the window: refused


def test_self_diagnose_report_limited_after_10():
    limiter.reset()
    for i in range(10):
        r = client.post("/v1/self-diagnose/report",
                        params={"traceback_text": "TypeError: x"}, headers=ADMIN)
        assert r.status_code == 200, f"request {i + 1} unexpectedly {r.status_code}"
    eleventh = client.post("/v1/self-diagnose/report",
                           params={"traceback_text": "TypeError: x"}, headers=ADMIN)
    assert eleventh.status_code == 429


def test_respond_limited_after_15_per_ip():
    limiter.reset()
    for i in range(15):
        r = client.get("/v1/ops/approvals/nothere/respond",
                       params={"token": "x", "decision": "approve"})
        assert r.status_code == 404, f"request {i + 1} unexpectedly {r.status_code}"
    sixteenth = client.get("/v1/ops/approvals/nothere/respond",
                           params={"token": "x", "decision": "approve"})
    assert sixteenth.status_code == 429


def test_limits_keyed_by_forwarded_ip():
    limiter.reset()
    spoofed = {**ADMIN, "X-Forwarded-For": "203.0.113.7"}
    for _ in range(5):
        client.post("/v1/ops/recalibrate", json={"code": "import os"}, headers=spoofed)
    blocked = client.post("/v1/ops/recalibrate", json={"code": "import os"}, headers=spoofed)
    assert blocked.status_code == 429                   # that IP is exhausted
    other = client.post("/v1/ops/recalibrate", json={"code": "import os"},
                        headers={**ADMIN, "X-Forwarded-For": "198.51.100.9"})
    assert other.status_code == 200                     # a different IP has its own bucket


def test_global_bucket_counts_undecorated_routes():
    limiter.reset()
    last, hit_at = None, None
    for i in range(61):
        last = client.get("/v1/health").status_code
        if last == 429:
            hit_at = i + 1
            break
    assert last == 429 and hit_at == 61                 # 60/min global, then refused


# ---------------- audit & telemetry feed ----------------
def test_audit_route_admin_gated():
    assert client.get("/v1/ops/audit").status_code in (401, 403)
    ok = client.get("/v1/ops/audit", headers=ADMIN)
    assert ok.status_code == 200
    body = ok.json()
    assert body["status"] == "active"
    assert isinstance(body["audit_trail"], list)
    assert "uptime_s" in body and "tickets" in body and "sandbox" in body


def test_audit_snapshot_shows_ticket_state():
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "deploy", "summary": "audit snapshot check"},
                    headers=ADMIN)
    assert r.status_code == 200, r.text
    tid = r.json()["ticket_id"]
    body = client.get("/v1/ops/audit", headers=ADMIN).json()
    match = [t for t in body["tickets"] if t["ticket_id"] == tid]
    assert match and match[0]["status"] == "pending"
    oa._tickets.pop(tid, None)


def test_audit_never_leaks_ticket_tokens():
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "deploy", "summary": "leak check"},
                    headers=ADMIN)
    assert r.status_code == 200, r.text
    tid, token = r.json()["ticket_id"], r.json()["token"]
    body = client.get("/v1/ops/audit", headers=ADMIN).json()
    assert token not in str(body)                       # the credential value is off the wire
    for t in body["tickets"]:
        assert "token" not in t                         # no token KEY in any snapshot
    oa._tickets.pop(tid, None)


def test_audit_limit_param_bounded():
    ok = client.get("/v1/ops/audit", params={"limit": 999999}, headers=ADMIN)
    assert ok.status_code == 200                        # clamped, not exploded
