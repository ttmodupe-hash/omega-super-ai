"""Task Runner guards - Issue 34. Nothing runs without a human-approved ticket."""
import os

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")

from fastapi.testclient import TestClient
from core.main import app
from core import ops_approvals as oa
from core import task_runner as tr

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


def _ticket(action_type="run_python", payload="", approve=True):
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": action_type, "summary": "test", "payload": payload},
                    headers=ADMIN)
    assert r.status_code == 200, r.text
    tid = r.json()["ticket_id"]
    if approve:
        ok = client.post(f"/v1/ops/approvals/{tid}/decision",
                         params={"decision": "approve"}, headers=ADMIN)
        assert ok.status_code == 200 and ok.json()["status"] == "approved"
    return tid


def test_pending_ticket_cannot_run():
    tid = _ticket(approve=False)
    r = client.post("/v1/ops/tasks/run", params={"ticket_id": tid}, headers=ADMIN)
    assert r.status_code == 409
    assert oa._tickets[tid]["status"] == "pending"


def test_rejected_ticket_cannot_run():
    tid = _ticket(approve=False)
    client.post(f"/v1/ops/approvals/{tid}/decision",
                params={"decision": "reject"}, headers=ADMIN)
    r = client.post("/v1/ops/tasks/run", params={"ticket_id": tid}, headers=ADMIN)
    assert r.status_code == 409


def test_unknown_ticket_404():
    r = client.post("/v1/ops/tasks/run", params={"ticket_id": "deadbeefdeadbeef"}, headers=ADMIN)
    assert r.status_code == 404


def test_run_requires_admin():
    anon = client.post("/v1/ops/tasks/run", params={"ticket_id": "whatever"})
    assert anon.status_code in (401, 403)


def test_approved_run_python_executes_exactly_once():
    tid = _ticket(payload='{"code": "print(2 + 3)"}')
    r = client.post("/v1/ops/tasks/run", params={"ticket_id": tid}, headers=ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["result"]["output"] == "5"
    assert tr._runs[-1]["ticket_id"] == tid
    again = client.post("/v1/ops/tasks/run", params={"ticket_id": tid}, headers=ADMIN)
    assert again.status_code == 409                     # single execution


def test_unregistered_action_type_refused_not_consumed():
    tid = _ticket(action_type="deploy")
    r = client.post("/v1/ops/tasks/run", params={"ticket_id": tid}, headers=ADMIN)
    assert r.status_code == 400
    assert oa._tickets[tid]["status"] == "approved"     # refusal never consumes the ticket


def test_run_log_admin_gated():
    anon = client.get("/v1/ops/tasks/log")
    assert anon.status_code in (401, 403)
    ok = client.get("/v1/ops/tasks/log", headers=ADMIN)
    assert ok.status_code == 200 and "runs" in ok.json()
