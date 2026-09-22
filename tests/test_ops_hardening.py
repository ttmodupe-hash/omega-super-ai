"""Ops hardening guards - Batch E. Gated report, body recalibrate, no leaks, no re-journal."""
import os
import json
import time
import asyncio
import tempfile

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")
os.environ.setdefault("OPS_JOURNAL", "off")

from fastapi.testclient import TestClient
from core.main import app
from core import sandbox_runner as sb
from core import ops_approvals as oa
from core import ops_journal as oj
from core import self_diagnose as sd

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


# ---------------- E1: self-diagnose report is admin-gated ----------------
def test_report_requires_admin():
    anon = client.post("/v1/self-diagnose/report", params={"traceback_text": "TypeError: x"})
    assert anon.status_code in (401, 403)
    sd._log.clear()
    ok = client.post("/v1/self-diagnose/report",
                     params={"traceback_text": "TypeError: x"}, headers=ADMIN)
    assert ok.status_code == 200
    assert ok.json()["entry"]["auto_applied"] is False
    assert sd._log[-1]["auto_applied"] is False


# ---------------- E2/E3: sandbox hardened, still correct ----------------
def test_sandbox_success_through_thread_wrapper():
    out = asyncio.run(sb.run_python("print(6 * 7)"))
    assert out["ok"] is True and out["output"] == "42"


def test_tempfile_removed_on_error_and_timeout(monkeypatch):
    names = []
    real = tempfile.NamedTemporaryFile
    def spy(*a, **k):
        f = real(*a, **k)
        names.append(f.name)
        return f
    monkeypatch.setattr(sb.tempfile, "NamedTemporaryFile", spy)
    out = asyncio.run(sb.run_python("raise ValueError('boom')"))
    assert out["ok"] is False
    out = asyncio.run(sb.run_python("while True: pass", timeout=1.0))
    assert out["stage"] == "timeout"
    assert names, "spy never saw a temp file"
    for p in names:
        assert not os.path.exists(p), f"leaked payload file: {p}"


# ---------------- E4: recalibrate accepts a JSON body ----------------
def test_recalibrate_accepts_json_body():
    r = client.post("/v1/ops/recalibrate", json={"code": "print(6 * 7)"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["output"] == "42" and body["attempts"] == 1


def test_recalibrate_empty_everywhere_400():
    r = client.post("/v1/ops/recalibrate", headers=ADMIN)
    assert r.status_code == 400


# ---------------- E5: replay never re-journals ----------------
def test_restore_does_not_rejournal_expiry(tmp_path, monkeypatch):
    past = int(time.time()) - 100
    p = tmp_path / "j.jsonl"
    p.write_text(json.dumps({"kind": "approval_requested", "ticket_id": "abc123ef",
                             "action_type": "deploy", "summary": "s", "expires": past,
                             "ts": past}) + "\n", encoding="utf-8")
    monkeypatch.setattr(oj, "ENABLED", True)
    monkeypatch.setattr(oj, "JOURNAL_PATH", str(p))
    calls = []
    monkeypatch.setattr(oj, "record", lambda e: calls.append(e) or True)
    oa._tickets.clear()
    assert oa.restore_from_journal() == 1
    assert oa._tickets["abc123ef"]["status"] == "expired"
    assert calls == []                                # zero journal writes during replay
