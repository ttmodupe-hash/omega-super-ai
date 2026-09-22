"""Code Fixer guards - Issue 35. The loop's brain is gated, re-gated, and fail-closed."""
import os
import asyncio
import sys

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")
os.environ.setdefault("LUQI_ADMIN_SECRET", "TestAdminKey123")
os.environ.setdefault("OPS_JOURNAL", "off")

from fastapi.testclient import TestClient
from core.main import app
from core import code_fixer as cf

client = TestClient(app)
ADMIN = {"X-Luqi-Admin-Auth": "TestAdminKey123"}


def _fake_httpx(content):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    class FakeClient:
        def __init__(self, timeout=None): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None):
            assert "moonshot" in url
            return FakeResp()

    return type("H", (), {"AsyncClient": FakeClient})


def test_fixer_fail_closed_without_key(monkeypatch):
    monkeypatch.setattr(cf, "BRAIN_API_KEY", "")
    assert asyncio.run(cf.brain_fixer("print(1)", "boom")) is None


def test_fixer_strips_fences_and_returns_clean_fix(monkeypatch):
    monkeypatch.setattr(cf, "BRAIN_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx("```python\nprint(2 + 2)\n```"))
    assert asyncio.run(cf.brain_fixer("print(2 + )", "SyntaxError")) == "print(2 + 2)"


def test_fixer_regates_banned_fix(monkeypatch):
    monkeypatch.setattr(cf, "BRAIN_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx("import os\nos.system('ls')"))
    assert asyncio.run(cf.brain_fixer("x()", "err")) is None   # banned fix = no fix


def test_fixer_noop_fix_stops_loop(monkeypatch):
    monkeypatch.setattr(cf, "BRAIN_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx("x()"))
    assert asyncio.run(cf.brain_fixer("x()", "err")) is None


def test_recalibrate_admin_gated():
    anon = client.post("/v1/ops/recalibrate", params={"code": "print(1)"})
    assert anon.status_code in (401, 403)


def test_recalibrate_clean_code_first_try():
    r = client.post("/v1/ops/recalibrate", params={"code": "print(2 + 3)"}, headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["attempts"] == 1 and body["output"] == "5"


def test_recalibrate_uses_fixer_on_failure(monkeypatch):
    calls = {"n": 0}
    async def fake_fixer(code, err):
        calls["n"] += 1
        return "print('repaired')"
    monkeypatch.setattr(cf, "brain_fixer", fake_fixer)
    r = client.post("/v1/ops/recalibrate", params={"code": "print(undefined_name)"},
                    headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["attempts"] == 2 and calls["n"] == 1


def test_metrics_admin_gated():
    assert client.get("/v1/ops/recalibrate/metrics").status_code in (401, 403)
    ok = client.get("/v1/ops/recalibrate/metrics", headers=ADMIN)
    assert ok.status_code == 200 and "recalibrations" in ok.json()
