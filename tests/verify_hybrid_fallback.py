"""FRONTDOOR-FIX-1 verification — the engine must THINK when sklearn is absent:
Phase 1.6 deterministic knowledge router, honest escalation, no dead ends.
Standalone: sklearn path forced offline, network surfaces patched — zero network."""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import core.hybrid_ai as hybrid
import core.free_knowledge as free_knowledge
import core.news_pulse as news_pulse

app = FastAPI()
app.include_router(hybrid.router)
c = TestClient(app)

DEAD_MESSAGE = "Guardrails active; ML classifier offline on this node."


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        sys.exit(1)


# Force the ML-offline node state (what Railway runs today)
hybrid._engine._ml = False
check("ML forced offline for this battery", hybrid._engine._load_ml() is False)


def ask(text):
    return c.post("/v1/hybrid/process", json={"text": text})


# 0. Guardrails still fire FIRST (Phase 1 unchanged)
r = ask("I am in crisis and danger, emergency")
b = r.json()
check("guardrail fires first", b["engine_used"].startswith("Phase 1"), b["engine_used"])

# 1. THE USER'S BUG: general knowledge question must be answered, not refused
free_knowledge.wikipedia_summary = lambda title: {
    "title": "Earth", "url": "https://en.wikipedia.org/wiki/Earth",
    "extract": "Earth is the third planet from the Sun and the only astronomical "
               "object known to harbor life. It formed about 4.54 billion years ago."}
r = ask("how old is the world ?")
b = r.json()
check("general question 200", r.status_code == 200)
check("no dead message", b["response"] != DEAD_MESSAGE)
check("Phase 1.6 answered", b["engine_used"].startswith("Phase 1.6"), b["engine_used"])
check("real content returned", "4.54 billion" in b["response"])
check("source shown", b["source"]["url"].startswith("https://en.wikipedia.org"))
check("ml_note honest", "sklearn" in b["ml_note"])
check("confidence honestly 0.0", b["confidence"] == 0.0)

# 2. Scam Shield routing (fully offline, real catalogue)
r = ask("Join my WhatsApp investment group! Guaranteed returns of 30% per month, "
        "risk-free. Pay tax to withdraw first.")
b = r.json()
check("scam routed", "Scam Shield" in b["engine_used"], b["engine_used"])
check("scam score >= 4", b["scam"]["risk_score"] >= 4, f"score={b['scam']['risk_score']}")
check("patterns matched", len(b["scam"]["matched_patterns"]) >= 1)
check("full check route given", b["scam"]["catalogue"] == "GET /v1/finlit/scam-patterns")

# 3. Everyday services routing (offline, real pack)
r = ask("How do I apply for the SRD grant from SASSA?")
b = r.json()
check("services routed", "Everyday Services" in b["engine_used"], b["engine_used"])
check("real entry returned", len(b["response"]) > 60)
check("sources route given", "/v1/services" in b["entry"]["sources_via"])

# 4. African history routing (offline, real archive)
r = ask("Tell me about the kingdom of Great Zimbabwe")
b = r.json()
check("history routed", "African History" in b["engine_used"], b["engine_used"])
check("archive entry returned", len(b["response"]) > 60)
check("archive sources route given", "/v1/history" in b["entry"]["sources_via"])

# 5. Technology Radar routing (offline, real catalogue)
r = ask("I need work but I have no money for data")
b = r.json()
check("radar routed", "Technology Radar" in b["engine_used"], b["engine_used"])
check("SAYouth recommended", "sayouth" in b["technology"]["id"], b["technology"]["id"])
check("official link shown", b["technology"]["link"].startswith("https://"))

# 6. World Pulse routing (patched feed)
news_pulse._gather_topic = lambda topic: {
    "topic": topic, "generated_at": "2026-09-24T00:00:00Z", "cache_ttl_seconds": 600,
    "feeds_ok": ["Fixture Feed"], "feeds_failed": [], "count": 1,
    "items": [{"title": "Fixture headline", "url": "https://ex.com/1",
               "source": "Fixture Feed", "published": "Wed, 24 Sep 2026 00:00:00 GMT",
               "summary": "s"}],
    "honesty": "f"}
r = ask("what is the latest news happening today?")
b = r.json()
check("news routed", "World Pulse" in b["engine_used"], b["engine_used"])
check("headline cited", "Fixture headline" in b["response"])
check("freshness shown", b["news"]["generated_at"].endswith("Z"))

# 7. Unmatchable input => honest guided escalation, STILL no dead end
# Unpatch Wikipedia first: the fixture from test 1 must not intercept gibberish.
free_knowledge.wikipedia_summary = lambda title: {}
r = ask("zzz qqq xwxwx")
b = r.json()
check("escalation phase", "Guided Escalation" in b["engine_used"], b["engine_used"])
check("escalation lists capabilities", "scam" in b["response"].lower()
      and "research" in b["response"].lower())
check("deep-research opt-in offered", b["escalation"]["route"] == "/v1/deep-research")
check("never the dead message", b["response"] != DEAD_MESSAGE)

# 8. Kill switch intact
import os as _os
_os.environ["DISABLED_ENGINES"] = "hybrid_ai"
r = ask("anything")
check("kill switch works", r.json()["engine_used"] == "KillSwitch")
del _os.environ["DISABLED_ENGINES"]

# 9. Telemetry intact on fallback path (re-patch fixture: stays zero-network)
free_knowledge.wikipedia_summary = lambda title: {
    "title": "Earth", "url": "https://en.wikipedia.org/wiki/Earth",
    "extract": "Earth formed about 4.54 billion years ago."}
r = ask("how old is the world ?")
b = r.json()
check("latency present", isinstance(b["latency_ms"], float))
check("pii flag present", "pii_redacted" in b)

# 10. /health names the fallback
r = c.get("/v1/hybrid/health")
check("health 200", r.status_code == 200)
check("health names Phase 1.6 fallback", "Phase 1.6" in r.json()["ml_offline_fallback"])

# 11. ML-1 / Phase 2.5: sklearn PRESENT but sub-gate => router still answers.
# Deterministic stubbed ML (no sklearn dependency in this battery): predicts
# class 0 at 17.4% — exactly the production noise-floor observation.
class _StubVec:
    def transform(self, texts):
        return texts


class _StubModel:
    def predict(self, X):
        return [0]

    def predict_proba(self, X):
        return [[0.174, 0.118, 0.118, 0.118, 0.118, 0.118, 0.118, 0.118]]


hybrid._engine._ml = (_StubVec(), _StubModel())
free_knowledge.wikipedia_summary = lambda title: {
    "title": "Earth", "url": "https://en.wikipedia.org/wiki/Earth",
    "extract": "Earth formed about 4.54 billion years ago."}
r = ask("how old is the world ?")
b = r.json()
check("Phase 2.5 answered", b["engine_used"].startswith("Phase 2.5"), b["engine_used"])
check("Phase 2.5 real content", "4.54 billion" in b["response"])
check("Phase 2.5 honest confidence", b["ml_confidence"] == 0.174)
check("Phase 2.5 note names the gate", "below gate" in b["ml_note"])

# 12. Phase 2.5 pack hit: sub-gate SRD question gets the services answer
r = ask("How do I apply for the SRD grant from SASSA?")
b = r.json()
check("Phase 2.5 services routed", "Everyday Services" in b["engine_used"], b["engine_used"])
check("Phase 2.5 entry returned", len(b["response"]) > 60)

# 13. Phase 2.5 no-match: Phase 3 escalation preserved (unchanged behaviour)
free_knowledge.wikipedia_summary = lambda title: {}
r = ask("zzz qqq xwxwx")
b = r.json()
check("Phase 3 still escalates", "Phase 3" in b["engine_used"], b["engine_used"])
check("Phase 3 honest boundary", "below the" in b["boundary"])
check("Phase 3 offers research", b["escalation"]["route"] == "/v1/deep-research")
hybrid._engine._ml = False  # restore the offline-node state

print("\nFRONTDOOR-FIX-1 + ML-1 verification: all checks passed.")
