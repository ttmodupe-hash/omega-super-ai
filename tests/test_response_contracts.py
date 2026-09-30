"""SCHEMA-1: response-contract guard tests.

Proves three laws:
  1. Valid engine responses pass untouched (floor enforced, ceiling free).
  2. Drifted responses (missing keys, wrong types, out-of-bounds values)
     fail closed as honest 502s - never reaching a user as fact.
  3. Undeclared routes and non-200 responses pass through untouched.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.response_contracts import (CONTRACT_MAP, ContractGuardMiddleware,
                                     HeritageQueryResponse)


def _app():
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)

    @app.post("/v1/hybrid/process")
    def ok_process():
        return {"engine_used": "Phase 2: TF-IDF Machine Learning Classifier",
                "confidence": 0.93, "response": "real answer",
                "intent": "money_skills", "latency_ms": 4.2}

    @app.post("/v1/finlit/scam-check")
    def ok_scam():
        return {"risk_level": "high", "risk_score": 9, "verdict": "v",
                "matched_patterns": [{"name": "Ponzi", "weight": 5}],
                "golden_rules": ["Never pay to receive money."],
                "report_line": "SAPS 10111", "disclaimer": "d"}

    @app.get("/v1/history")
    def ok_overview():
        return {"name": "African History Archive", "version": "1.0.0",
                "entry_count": 29, "categories": [], "regions": []}

    @app.post("/v1/heritage/query")
    def ok_heritage():
        return {"matches": [{"id": "h1", "title": "Ge'ez Canon",
                             "summary": "s", "era": "4th c.",
                             "region": "Ethiopia",
                             "tradition": "ethiopian_orthodox"}],
                "disclaimer": "d"}

    return app


@pytest.fixture
def client():
    return TestClient(_app())


# ── valid responses pass ──────────────────────────────────────────────────

def test_valid_hybrid_passes_with_contract_header(client):
    r = client.post("/v1/hybrid/process", json={"text": "hello"})
    assert r.status_code == 200
    assert r.json()["confidence"] == 0.93
    assert r.headers["X-Luqi-Contract"] == "HybridProcessResponse"


def test_valid_scam_check_passes(client):
    r = client.post("/v1/finlit/scam-check", json={"text": "x"})
    assert r.status_code == 200
    assert r.headers["X-Luqi-Contract"] == "ScamCheckResponse"


def test_valid_overview_passes(client):
    r = client.get("/v1/history")
    assert r.status_code == 200
    assert r.json()["entry_count"] == 29


def test_valid_heritage_passes(client):
    r = client.post("/v1/heritage/query", json={"query": "canon"})
    assert r.status_code == 200


# ── drift fails closed (502), never reaches the user ─────────────────────

@pytest.mark.parametrize("broken", [
    {"confidence": 0.9, "response": "x"},                    # engine_used missing
    {"engine_used": "e", "confidence": 1.7},                 # out of bounds
    {"engine_used": "e", "confidence": "high"},              # wrong type
    {"engine_used": ""},                                     # empty required str
])
def test_drifted_hybrid_is_502(broken):
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)

    @app.post("/v1/hybrid/process")
    def bad():
        return broken

    r = TestClient(app).post("/v1/hybrid/process", json={"text": "q"})
    assert r.status_code == 502
    body = r.json()
    assert body["status"] == "contract_violation"
    assert body["contract"] == "HybridProcessResponse"
    assert "failed structural verification" in body["detail"]


def test_drifted_scam_risk_level_rejected():
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)

    @app.post("/v1/finlit/scam-check")
    def bad():
        return {"risk_level": "apocalyptic", "risk_score": 3, "verdict": "v",
                "matched_patterns": [], "golden_rules": [],
                "report_line": "r", "disclaimer": "d"}

    r = TestClient(app).post("/v1/finlit/scam-check", json={"text": "x"})
    assert r.status_code == 502


# ── heritage invariant: matches XOR honest silence ────────────────────────

def test_heritage_empty_matches_without_status_is_drift():
    with pytest.raises(Exception):
        HeritageQueryResponse.model_validate({"matches": []})


def test_heritage_no_match_requires_honest_note():
    with pytest.raises(Exception):
        HeritageQueryResponse.model_validate(
            {"matches": [], "status": "no_curated_match"})


def test_heritage_no_match_with_note_is_valid():
    HeritageQueryResponse.model_validate(
        {"matches": [], "status": "no_curated_match",
         "honest_note": "No curated archive entry matches this query."})


def test_heritage_match_cannot_claim_no_match():
    with pytest.raises(Exception):
        HeritageQueryResponse.model_validate(
            {"matches": [{"id": "h", "title": "t", "summary": "s"}],
             "status": "no_curated_match", "honest_note": "n"})


# ── pass-through laws ─────────────────────────────────────────────────────

def test_undeclared_route_untouched(client):
    @client.app.get("/v1/ops/internal")
    def internal():
        return {"anything": True}
    r = client.get("/v1/ops/internal")
    assert r.status_code == 200
    assert "X-Luqi-Contract" not in r.headers


def test_error_responses_never_rewritten():
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)

    @app.post("/v1/chat/completions")
    def paused():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="kill switch engaged")

    r = TestClient(app, raise_server_exceptions=False).post(
        "/v1/chat/completions", json={"prompt": "hi"})
    assert r.status_code == 503  # honest error passes through as-is


def test_contract_map_covers_public_modes():
    paths = {p for _, p in CONTRACT_MAP}
    for expected in ["/v1/hybrid/process", "/v1/chat/completions",
                     "/v1/finlit/scam-check", "/v1/services/entries",
                     "/v1/history/entries", "/v1/heritage/query",
                     "/v1/deep-research", "/v1/hybrid/health"]:
        assert expected in paths


def test_real_heritage_router_success_shape_passes():
    """Regression (found by IKS-1's real-router tests): the heritage engine's
    own success response carries status 'success' — the contract must accept
    it, or every matched query would fail closed at the boundary."""
    from core.heritage_engine import router as heritage_router
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)
    app.include_router(heritage_router)
    c = TestClient(app)
    r = c.post("/v1/heritage/query", json={"query": "Ethiopian canon"})
    assert r.status_code == 200
    assert r.headers.get("X-Luqi-Contract") == "HeritageQueryResponse"
    b = r.json()
    assert b["status"] == "success" and b["matches"]
    # and honest silence still passes the same contract
    r2 = c.post("/v1/heritage/query", json={"query": "zz-no-such-entry-qq"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "no_curated_match"
