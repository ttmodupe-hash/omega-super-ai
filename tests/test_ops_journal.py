"""Ops Journal guards - Issues 36/37. State survives restart; bad tokens lock out."""
import os

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")
os.environ.setdefault("OPS_JOURNAL", "off")        # enabled per-test via monkeypatch

from fastapi.testclient import TestClient
from core.main import app
from core import ops_approvals as oa
from core import ops_journal as oj

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


def _request(summary="journal test"):
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "deploy", "summary": summary}, headers=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- journal primitives ----------------
def test_journal_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(tmp_path / "j.jsonl"))
    assert oj.record({"kind": "unit", "value": 1}) is True
    assert oj.record({"kind": "unit", "value": 2}) is True
    events = oj.read_recent(10)
    assert [e["value"] for e in events[-2:]] == [1, 2]


def test_journal_fail_soft_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(tmp_path / "nope\0bad"))
    before = len(oj.write_errors)
    assert oj.record({"kind": "unit"}) is False
    assert len(oj.write_errors) == before + 1


def test_journal_torn_tail_skipped(tmp_path, monkeypatch):
    p = tmp_path / "j.jsonl"
    p.write_text('{"kind": "ok"}\n{"kind": "tor', encoding="utf-8")
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(p))
    assert [e["kind"] for e in oj.read_recent()] == ["ok"]


# ---------------- lockout + pruning (Issue 37) ----------------
def test_token_lockout_after_repeated_failures(monkeypatch):
    monkeypatch.setattr(oa, "MAX_TOKEN_ATTEMPTS", 3)
    t = _request("lockout")
    tid, good = t["ticket_id"], t["token"]
    for _ in range(3):
        r = client.get(f"/v1/ops/approvals/{tid}/respond",
                       params={"token": "deadbeef", "decision": "approve"})
        assert r.status_code == 403
    locked = client.get(f"/v1/ops/approvals/{tid}/respond",
                        params={"token": good, "decision": "approve"})
    assert locked.status_code == 429                # even the real token is now refused
    oa._fail_counts.pop(tid, None)


def test_expired_pending_tickets_pruned():
    t = _request("will expire")
    tid = t["ticket_id"]
    oa._tickets[tid]["expires"] = 1                 # force into the past
    oa._prune_expired()
    assert oa._tickets[tid]["status"] == "expired"
    r = client.get(f"/v1/ops/approvals/{tid}/respond",
                   params={"token": t["token"], "decision": "approve"})
    assert r.status_code == 410


# ---------------- restart recovery (Issue 36) ----------------
def test_restart_restore_recovers_pending_ticket(tmp_path, monkeypatch):
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(tmp_path / "j.jsonl"))
    t = _request("restart me")
    tid, token = t["ticket_id"], t["token"]
    oa._tickets.clear()                             # simulate worker restart
    assert oa.restore_from_journal() == 1
    assert tid in oa._tickets
    r = client.get(f"/v1/ops/approvals/{tid}/respond",
                   params={"token": token, "decision": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_restore_replays_decisions_and_keeps_single_use(tmp_path, monkeypatch):
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(tmp_path / "j.jsonl"))
    t = _request("decide then die")
    tid = t["ticket_id"]
    ok = client.post(f"/v1/ops/approvals/{tid}/decision",
                     params={"decision": "reject"}, headers=ADMIN)
    assert ok.status_code == 200
    oa._tickets.clear()
    oa.restore_from_journal()
    assert oa._tickets[tid]["status"] == "rejected"
    again = client.get(f"/v1/ops/approvals/{tid}/respond",
                       params={"token": t["token"], "decision": "approve"})
    assert again.status_code == 409                 # replay protection survives restart


# ---------------- audit endpoint ----------------
def test_audit_endpoint_admin_gated():
    assert client.get("/v1/ops/approvals/audit").status_code in (401, 403)
    ok = client.get("/v1/ops/approvals/audit", headers=ADMIN)
    assert ok.status_code == 200
    body = ok.json()
    assert "in_memory" in body and "journal_enabled" in body and "journal_write_errors" in body
