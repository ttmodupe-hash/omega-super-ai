"""
Batch G — truth engine tests.

Brain calls are faked by patching core.kimi_client.chat_completion via
monkeypatch.setattr (asyncio.to_thread honours monkeypatching, unlike
unittest.mock.patch inside threads). The admin dependency is overridden per
test client. The rate limiter is reset by conftest for hermeticity.
"""
from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("KIMI_API_KEY", "test-key")
os.environ.setdefault("OPS_JOURNAL", "off")

from core import truth_engine  # noqa: E402
import core.kimi_client as kimi_client  # noqa: E402
from core.main import app  # noqa: E402

ADMIN = {"X-Luqi-Admin-Auth": "test-admin-key"}


@pytest.fixture()
def client(monkeypatch):
    # verify_admin reads LUQI_ADMIN_SECRET from the env at request time.
    monkeypatch.setenv("LUQI_ADMIN_SECRET", "test-admin-key")
    return TestClient(app)


def _verdict(ok: bool, confidence: float = 0.9, findings: list | None = None,
             instructions: str = "") -> str:
    import json
    return json.dumps({
        "is_truthful_and_accurate": ok,
        "confidence_score": confidence,
        "audit_findings": findings or [],
        "recalibration_instructions": instructions,
    })


def _draft(answer: str = "Paris is the capital of France.", claims=None,
           uncertainties=None) -> str:
    import json
    return json.dumps({
        "answer": answer,
        "claims": claims if claims is not None else [
            {"claim": "Paris is the capital of France", "source": "Britannica"}],
        "uncertainties": uncertainties if uncertainties is not None else [],
    })


def _fake_brain(monkeypatch, script):
    """Install a scripted chat_completion. script[i] is the raw text returned
    on the i-th brain call (exceptions allowed as items). Returns call log."""
    calls = []

    def fake(system, user, *, tools=None, timeout=60):
        calls.append({"system": system, "user": user})
        item = script[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(kimi_client, "chat_completion", fake)
    return calls


@pytest.mark.anyio
async def test_verified_first_pass(monkeypatch):
    _fake_brain(monkeypatch, [_draft(), _verdict(True)])
    out = await truth_engine.truth_seek("What is the capital of France?")
    assert out["status"] == "verified"
    assert out["answer"].startswith("Paris")
    assert out["revisions"] == 1
    assert out["claims"] and out["claims"][0]["source"] == "Britannica"
    assert out["audit"]["is_truthful_and_accurate"] is True


@pytest.mark.anyio
async def test_reject_then_recalibrate_then_verify(monkeypatch):
    calls = _fake_brain(monkeypatch, [
        _draft("The moon is made of cheese."),
        _verdict(False, 0.2, ["unsupported claim: moon composition"],
                 "Remove the cheese claim or cite a source."),
        _draft("The moon is rocky.",
               [{"claim": "The moon is rocky", "source": "NASA"}]),
        _verdict(True, 0.95),
    ])
    out = await truth_engine.truth_seek("What is the moon made of?")
    assert out["status"] == "verified"
    assert out["revisions"] == 2
    # The second generator call must carry the auditor's recalibration context.
    assert "RECALIBRATION REQUIRED" in calls[2]["user"]
    assert "unsupported claim" in calls[2]["user"]


@pytest.mark.anyio
async def test_circuit_breaker_never_ships_rejected_answer(monkeypatch):
    _fake_brain(monkeypatch, [
        _draft(), _verdict(False, 0.1, ["bad"], "fix"),
        _draft(), _verdict(False, 0.1, ["still bad"], "fix harder"),
        _draft(), _verdict(False, 0.1, ["no"], "give up"),
    ])
    out = await truth_engine.truth_seek("Anything?", max_revisions=2)
    assert out["status"] == "unverified"
    assert out["verification_failed"] is True
    assert out["revisions"] == 3            # 1 initial + 2 recalibrations
    assert "answer" not in out              # rejected text NEVER under "answer"
    assert out["draft"]["answer"]           # but visible as an unverified draft
    assert out["audit"]["is_truthful_and_accurate"] is False
    assert "did NOT pass verification" in out["note"]


@pytest.mark.anyio
async def test_malformed_auditor_output_fails_closed(monkeypatch):
    _fake_brain(monkeypatch, [_draft(), "I think this is fine honestly.",
                              _draft(), _verdict(True)])
    out = await truth_engine.truth_seek("q")
    # Unparseable auditor output became a rejection, then the loop recovered.
    assert out["status"] == "verified"
    assert out["revisions"] == 2


@pytest.mark.anyio
async def test_confidence_out_of_bounds_rejected_by_schema(monkeypatch):
    _fake_brain(monkeypatch, [_draft(), _verdict(True, confidence=42.0),
                              _draft(), _verdict(True)])
    out = await truth_engine.truth_seek("q")
    # confidence 42 violates Field(le=1.0) -> fail-closed reject -> recalibrate.
    assert out["status"] == "verified"
    assert out["revisions"] == 2


@pytest.mark.anyio
async def test_malformed_generator_json_recalibrates(monkeypatch):
    _fake_brain(monkeypatch, ["not json at all", _draft(), _verdict(True)])
    out = await truth_engine.truth_seek("q")
    assert out["status"] == "verified"
    assert out["revisions"] == 2


@pytest.mark.anyio
async def test_no_key_propagates_http_exception(monkeypatch):
    _fake_brain(monkeypatch, [HTTPException(status_code=500, detail="KIMI_API_KEY not set")])
    with pytest.raises(HTTPException) as exc:
        await truth_engine.truth_seek("q")
    assert exc.value.status_code == 500


def test_endpoint_admin_gated(client):
    r = client.post("/v1/truth/answer", json={"query": "hi"})
    assert r.status_code in (401, 403)


def test_endpoint_verified(monkeypatch, client):
    _fake_brain(monkeypatch, [_draft(), _verdict(True)])
    r = client.post("/v1/truth/answer", json={"query": "capital of France?"}, headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "verified"
    assert body["audit"]["confidence_score"] == 0.9


def test_truth_metrics_shape(client):
    r = client.get("/v1/truth/metrics", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    for key in ("runs", "verified", "unverified", "unavailable", "revisions"):
        assert key in body


# ---- Batch G: kimi_gateway hook (/v1/agent/kimi-reason) ----

def _gateway_post(client, monkeypatch, script, pipeline="0"):
    _fake_brain(monkeypatch, script)
    monkeypatch.setenv("LUQI_TRUTH_PIPELINE", pipeline)
    return client.post("/v1/agent/kimi-reason", json={"prompt": "capital of France?"})


def test_gateway_hook_off_by_default(monkeypatch, client):
    r = _gateway_post(client, monkeypatch, ["Paris."], pipeline="0")
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "Paris."
    assert "verification" not in body          # zero behaviour change when off


def test_gateway_hook_verified_replaces_and_annotates(monkeypatch, client):
    # brain call 1: gateway draft; call 2: auditor approves the draft
    r = _gateway_post(client, monkeypatch, ["Paris.", _verdict(True, 0.97)], pipeline="1")
    assert r.status_code == 200
    body = r.json()
    assert body["verification"]["status"] == "verified"
    assert body["choices"][0]["message"]["content"] == "Paris."


def test_gateway_hook_fault_never_breaks_answer(monkeypatch, client):
    # brain call 1: draft; call 2: auditor path explodes (network fault)
    import requests as _rq
    r = _gateway_post(client, monkeypatch,
                      ["Paris.", _rq.exceptions.ConnectionError("boom")], pipeline="1")
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "Paris."   # untouched
    assert body["verification"]["status"] == "unavailable"


@pytest.mark.anyio
async def test_verify_draft_rejected_runs_full_loop(monkeypatch):
    # call 1: audit of the supplied draft (reject); calls 2-3: regen + audit (approve)
    _fake_brain(monkeypatch, [
        _verdict(False, 0.3, ["unsupported"], "add sources"),
        _draft(), _verdict(True, 0.9),
    ])
    out = await truth_engine.verify_draft("q", "The moon is made of cheese.")
    assert out["status"] == "verified"
    assert "rejected by the auditor" in out["note"]
    assert out["revisions"] == 1   # one generation inside the follow-up loop
