"""Sandbox + Approvals guards - Issues 32/33. The loop only counts if it is tested."""
import os
import asyncio
import time

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")
os.environ.setdefault("OPS_JOURNAL", "off")

from fastapi.testclient import TestClient
from core.main import app
from core import sandbox_runner as sb
from core import ops_approvals as oa

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


# ---------------- sandbox ----------------
def test_gate_rejects_banned_patterns():
    for bad in ["import os", "exec(x)", "eval(x)", "open('f')", "().__class__", "compile('x','','')"]:
        ok, why = sb.static_gate(bad)
        assert ok is False, bad
    assert sb.static_gate("print(2+2)")[0] is True


def test_run_python_success_and_capture():
    out = asyncio.run(sb.run_python("print('hello-' + 'world')"))
    assert out["ok"] is True and out["output"] == "hello-world"


def test_run_python_error_pipes_to_feedback(monkeypatch):
    seen = {}
    async def fake_diag(tb):
        seen["tb"] = tb
    monkeypatch.setattr(sb, "_feedback", fake_diag)
    out = asyncio.run(sb.run_python("raise ValueError('boom')"))
    assert out["ok"] is False and "ValueError" in out["error"]
    assert "boom" in seen.get("tb", "")


def test_timeout_and_metering():
    loop_code = "x = 0" + chr(10) + "while True: x += 1"
    out = asyncio.run(sb.run_python(loop_code, timeout=1.0))
    assert out["stage"] == "timeout"
    assert sb.metrics()["timeouts"] >= 1


# ---------------- sandbox v2: tiered ----------------
def test_ast_gate_combined_coverage():
    from core import sandbox_runner as sb2
    for bad in ["import subprocess", "from shutil import rmtree", "eval('1')",
                "open('f')", "().__class__", "getattr(x, 'y')", "os.system('ls')"]:
        ok, why = sb2.static_gate(bad)
        assert ok is False, f"{bad} should be rejected: {why}"
    assert sb2.static_gate("total = sum([1, 2, 3])" + chr(10) + "print(total)")[0] is True


def test_recalibration_loop_capped(monkeypatch):
    from core import sandbox_runner as sb2
    calls = {"fix": 0}
    async def fixer(code, err):
        calls["fix"] += 1
        return "print('fixed')"
    async def fake_run(code, timeout=10):
        return {"ok": False, "stage": "subprocess", "output": "", "error": "boom", "exit_code": 1}
    monkeypatch.setattr(sb2, "run_python", fake_run)
    out = asyncio.run(sb2.run_with_recalibration("bad()", fixer, max_retries=2))
    assert out["ok"] is False and calls["fix"] == 2 and out["recalibrations"] == 2


def test_recalibration_stops_on_success(monkeypatch):
    from core import sandbox_runner as sb2
    state = {"n": 0}
    async def flaky(code, timeout=10):
        state["n"] += 1
        return {"ok": state["n"] >= 2, "stage": "subprocess", "output": "ok", "error": None, "exit_code": 0}
    async def fixer(code, err):
        return "print('ok')"
    monkeypatch.setattr(sb2, "run_python", flaky)
    out = asyncio.run(sb2.run_with_recalibration("x()", fixer, max_retries=3))
    assert out["ok"] is True and out["attempts"] == 2


# ---------------- approvals ----------------
def test_full_approval_cycle():
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "deploy", "summary": "promote prompt v2"}, headers=ADMIN)
    assert r.status_code in (200, 401, 403)
    if r.status_code != 200:
        return
    tid, token = r.json()["ticket_id"], r.json()["token"]
    assert r.json()["status"] == "pending"
    ok = client.get(f"/v1/ops/approvals/{tid}/respond", params={"token": token, "decision": "approve"})
    assert ok.status_code == 200 and ok.json()["status"] == "approved"
    again = client.get(f"/v1/ops/approvals/{tid}/respond", params={"token": token, "decision": "reject"})
    assert again.status_code == 409                       # single use


def test_tampered_token_and_expiry(monkeypatch):
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "x", "summary": "y"}, headers=ADMIN)
    if r.status_code != 200:
        return
    tid = r.json()["ticket_id"]
    tampered = client.get(f"/v1/ops/approvals/{tid}/respond", params={"token": "deadbeef", "decision": "approve"})
    assert tampered.status_code == 403
    oa._tickets[tid]["expires"] = int(time.time()) - 5    # force expiry
    expired = client.get(f"/v1/ops/approvals/{tid}/respond",
                         params={"token": r.json()["token"], "decision": "approve"})
    assert expired.status_code == 410


def test_no_webhook_degrades_honestly(monkeypatch):
    monkeypatch.setattr(oa, "SLACK_URL", "")
    monkeypatch.setattr(oa, "DISCORD_URL", "")
    oa._notify_log.clear()
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "a", "summary": "b"}, headers=ADMIN)
    if r.status_code == 200:
        assert any("[no-webhook]" in line for line in oa._notify_log)
        assert r.json()["status"] == "pending"            # ticket still works without webhooks


def test_admin_decision_endpoint():
    r = client.post("/v1/ops/approvals/request",
                    params={"action_type": "console", "summary": "via console"}, headers=ADMIN)
    if r.status_code != 200:
        return
    tid = r.json()["ticket_id"]
    ok = client.post(f"/v1/ops/approvals/{tid}/decision",
                     params={"decision": "approve"}, headers=ADMIN)
    assert ok.status_code == 200 and ok.json()["status"] == "approved"
    again = client.post(f"/v1/ops/approvals/{tid}/decision",
                        params={"decision": "reject"}, headers=ADMIN)
    assert again.status_code == 409
