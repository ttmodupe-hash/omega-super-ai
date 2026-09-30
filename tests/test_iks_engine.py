"""IKS-1: ethnobotanical archive + dialect register tests.

Proves four laws:
  1. Real responses satisfy their contracts (floor enforced by the guard).
  2. No-match is honest silence — never a fabricated remedy.
  3. The boundary law holds: every entry carries cautions and >=2 sources;
     the disclaimer travels with every response.
  4. The dialect register never pretends to speak: status is registry-only.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.iks_engine import router as iks_router
from core.i18n import router as i18n_router
from core.response_contracts import (CONTRACT_MAP, ContractGuardMiddleware,
                                     IksQueryResponse)


def _app():
    app = FastAPI()
    app.add_middleware(ContractGuardMiddleware)
    app.include_router(iks_router)
    app.include_router(i18n_router)
    return app


@pytest.fixture
def client():
    return TestClient(_app())


# ── overview: contract + guardrails ───────────────────────────────────────

def test_overview_contract_and_guardrails(client):
    r = client.get("/v1/iks")
    assert r.status_code == 200
    assert r.headers.get("X-Luqi-Contract") == "ArchiveOverviewResponse"
    b = r.json()
    assert b["entry_count"] == 6
    assert b["version"] == "1.0.0"
    assert len(b["categories"]) == 6
    assert "not medical advice" in b["disclaimer"]
    assert any("Catalogue, not clinic" in g for g in b["guardrails"])


# ── entries: deterministic search, honest empties ─────────────────────────

def test_entries_search_deterministic(client):
    r1 = client.get("/v1/iks/entries", params={"q": "cancer bush"})
    r2 = client.get("/v1/iks/entries", params={"q": "cancer bush"})
    assert r1.status_code == 200
    assert r1.json() == r2.json()
    ids = [e["id"] for e in r1.json()["entries"]]
    assert ids == ["motsepelo-sutherlandia"]


def test_entries_search_by_vernacular(client):
    r = client.get("/v1/iks/entries", params={"q": "lengana"})
    assert [e["id"] for e in r.json()["entries"]] == ["lengana-artemisia-afra"]


def test_entries_empty_is_honest(client):
    r = client.get("/v1/iks/entries", params={"q": "zztop-quantum-elixir"})
    assert r.status_code == 200
    assert r.json()["entries"] == []
    assert r.json()["count"] == 0


def test_entries_bad_category_400(client):
    r = client.get("/v1/iks/entries", params={"category": "magic"})
    assert r.status_code == 400


# ── entry detail: sources + cautions law ──────────────────────────────────

def test_entry_detail_carries_sources_and_cautions(client):
    r = client.get("/v1/iks/entries/rooibos-aspalathus")
    assert r.status_code == 200
    b = r.json()
    assert len(b["sources"]) >= 2
    assert b["cautions"]
    assert "benefit-sharing" in b["summary"]
    assert "disclaimer" in b


def test_entry_detail_404_honest(client):
    r = client.get("/v1/iks/entries/nope")
    assert r.status_code == 404


def test_data_law_every_entry_sourced_and_cautioned():
    """The data itself obeys the law — not just the happy-path endpoint."""
    import json, pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / "core" / "data" / "iks_archive.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    for e in data["entries"]:
        assert len(e["sources"]) >= 2, e["id"]
        assert e["cautions"], e["id"]
        assert e["modern_research_note"], e["id"]
        assert e["category"] in data["categories"], e["id"]


# ── query endpoint: matches XOR honest silence ────────────────────────────

def test_query_match_shape(client):
    r = client.post("/v1/iks/query", json={"query": "joint pain Kalahari"})
    assert r.status_code == 200
    assert r.headers.get("X-Luqi-Contract") == "IksQueryResponse"
    b = r.json()
    assert b["status"] == "success"
    assert b["matches"][0]["id"] == "devils-claw-harpagophytum"
    assert "Catalogue, not clinic" in b["boundary"]
    assert b["disclaimer"]


def test_query_no_match_is_honest_silence(client):
    r = client.post("/v1/iks/query", json={"query": "cure my diabetes quickly"})
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "no_curated_match"
    assert b["matches"] == []
    assert "fabricate" in b["honest_note"]
    assert b["escalation"]["available"] is True


def test_query_invariant_model_directly():
    """The contract itself refuses both-half answers."""
    with pytest.raises(Exception):
        IksQueryResponse(matches=[], honest_note=None)  # silent emptiness
    with pytest.raises(Exception):
        IksQueryResponse(status="no_curated_match",
                         matches=[{"id": "x", "title": "t", "summary": "s"}],
                         honest_note="h")


# ── dialect register: never pretends to speak ─────────────────────────────

def test_dialects_registry_honest_status(client):
    r = client.get("/v1/i18n/dialects")
    assert r.status_code == 200
    assert r.headers.get("X-Luqi-Contract") == "DialectRegistryResponse"
    b = r.json()
    assert b["count"] == 1
    p = b["profiles"][0]
    assert p["code"] == "sepetori"
    assert p["status"] == "registry_only_activates_with_language_models"
    assert "not live speech" in b["note"]


# ── contract map coverage ─────────────────────────────────────────────────

def test_iks_routes_are_guarded():
    assert ("GET", "/v1/iks") in CONTRACT_MAP
    assert ("GET", "/v1/iks/entries") in CONTRACT_MAP
    assert ("POST", "/v1/iks/query") in CONTRACT_MAP
    assert ("GET", "/v1/i18n/dialects") in CONTRACT_MAP
