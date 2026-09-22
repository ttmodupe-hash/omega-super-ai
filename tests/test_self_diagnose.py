"""Self-Diagnose guards - Issue 27a. The battery that checks before any human eye."""
import os
import asyncio

import pytest

os.environ.setdefault("PHONE_HASH_SALT", "test-salt")

from fastapi.testclient import TestClient
from core.main import app
from core import self_diagnose as sd

client = TestClient(app)


def test_fail_closed_without_key(monkeypatch):
    monkeypatch.setattr(sd, "BRAIN_API_KEY", "")
    out = asyncio.run(sd._diagnose("ValueError: boom"))
    assert out["status"] == "pending_human" and "unavailable" in out["diagnosis"]


def test_correct_parsing_and_urls(monkeypatch):
    import sys

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": 'pre {"diagnosis": "d", "suggested_patch": "p"} post'}}]}

    class FakeClient:
        def __init__(self, timeout=None): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None):
            assert url.endswith("/chat/completions") and "moonshot" in url
            assert headers["Authorization"].startswith("Bearer ")
            return FakeResp()

    monkeypatch.setattr(sd, "BRAIN_API_KEY", "k")
    monkeypatch.setitem(sys.modules, "httpx", type("H", (), {"AsyncClient": FakeClient}))
    out = asyncio.run(sd._diagnose("Traceback: x"))
    assert out["diagnosis"] == "d" and out["suggested_patch"] == "p" and out["status"] == "pending_human"


def test_report_stores_and_never_auto_applies():
    sd._log.clear()
    r = client.post("/v1/self-diagnose/report", params={"traceback_text": "TypeError: x"})
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        assert r.json()["entry"]["auto_applied"] is False
        assert sd._log[-1]["auto_applied"] is False


def test_log_admin_gated():
    anon = client.get("/v1/self-diagnose/log")
    assert anon.status_code in (401, 403)
