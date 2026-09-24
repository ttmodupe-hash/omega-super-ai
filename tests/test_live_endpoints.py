"""LIVE smoke suite — runs against the PRODUCTION Railway node, not CI-default.

Gated: every test skips unless LUQI_LIVE_BASE is set. The GitHub Action runs
this suite only on manual workflow_dispatch (post-deploy smoke); offline
batteries (verify_*.py) gate every push instead. Rationale: CI proves the CODE;
this suite proves the DEPLOYMENT.

Contract note: /v1/hybrid/process takes {"text": "..."} (HybridInput schema) —
NOT "prompt". Unknown fields are ignored by pydantic, so a wrong key yields a
vacuous 200; these tests assert the response CONTENT, never just the status.

Zero fabrication: every assertion checks the real response contract.
External feeds can legitimately be down; news asserts the honest contract
(200 with items, or fail-closed 503), never a fabricated expectation.
"""
import os

import pytest
import httpx

BASE = os.getenv("LUQI_LIVE_BASE", "").rstrip("/")
pytestmark = pytest.mark.skipif(not BASE, reason="LUQI_LIVE_BASE not set (live smoke only)")

DEAD_MESSAGE = "ML classifier offline on this node."


def ask(client, text):
    r = client.post(f"{BASE}/v1/hybrid/process", json={"text": text}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_engine_health():
    r = httpx.get(f"{BASE}/v1/health", timeout=20)
    assert r.status_code == 200


def test_hybrid_health_ml_live():
    data = httpx.get(f"{BASE}/v1/hybrid/health", timeout=20).json()
    assert data["sklearn_available"] is True           # the screenshot bug, fixed
    assert "Phase 1.6" in data["ml_offline_fallback"]  # offline router named
    assert data["kill_switch"] is False
    assert data["corpus_size"] > 0


def test_general_question_answered_with_source():
    with httpx.Client() as c:
        b = ask(c, "how old is the world ?")
    assert DEAD_MESSAGE not in b["response"]
    assert b["engine_used"].startswith(("Phase 1.6", "Phase 2.5"))
    assert b["source"]["url"].startswith("https://")
    assert isinstance(b["latency_ms"], float)
    assert "pii_redacted" in b


def test_services_pack_routing():
    with httpx.Client() as c:
        b = ask(c, "How do I apply for the SRD grant from SASSA?")
    assert "Everyday Services" in b["engine_used"]
    assert "/v1/services" in b["entry"]["sources_via"]


def test_scam_shield_routing():
    with httpx.Client() as c:
        b = ask(c, "Join my WhatsApp investment group! Guaranteed returns of "
                   "30% per month, risk-free. Pay tax to withdraw first.")
    assert "Scam Shield" in b["engine_used"]
    assert b["scam"]["risk_score"] >= 4
    assert b["scam"]["catalogue"] == "GET /v1/finlit/scam-patterns"


def test_technology_radar_routing():
    with httpx.Client() as c:
        b = ask(c, "I need work but I have no money for data")
    assert "Technology Radar" in b["engine_used"]
    assert b["technology"]["link"].startswith("https://")


def test_african_history_routing():
    with httpx.Client() as c:
        b = ask(c, "Tell me about the kingdom of Great Zimbabwe")
    assert "African History" in b["engine_used"]
    assert "/v1/history" in b["entry"]["sources_via"]


def test_unmatched_input_never_dead():
    with httpx.Client() as c:
        b = ask(c, "zzz qqq xwxwx")
    assert DEAD_MESSAGE not in b["response"]
    assert "escalation" in b
    assert b["escalation"]["route"] == "/v1/deep-research"


def test_news_topics_endpoint():
    r = httpx.get(f"{BASE}/v1/news/topics", timeout=20)
    assert r.status_code == 200
    topics = r.json().get("topics", r.json())
    assert any("world" in str(t) for t in topics)


def test_news_headlines_honest_contract():
    r = httpx.get(f"{BASE}/v1/news/headlines?topic=world", timeout=30)
    assert r.status_code in (200, 503)     # 503 = fail-closed honesty, feeds down
    if r.status_code == 200:
        assert r.json()["count"] >= 1


def test_innovation_status_endpoint():
    r = httpx.get(f"{BASE}/v1/innovation/status", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data.get("catalogue_size", data.get("technologies", 0)) >= 19


def test_stats_heartbeat():
    r = httpx.get(f"{BASE}/v1/stats/heartbeat", timeout=20)
    assert r.status_code in (200, 503)     # 503 = honest DB-down state
