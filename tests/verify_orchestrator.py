"""verify_orchestrator.py — Unified Agentic Router (ORCH-1) compliance battery.

Runs against the REAL orchestrator router (TestClient). Every check passes or
the script exits 1. Convention: same as verify_finlit.py / verify_history.py.

NOTE on the scam assertion: the canonical battery prompt
("invest R500 get R5000, guaranteed returns, whatsapp group") scores 9 =
risk_level "high" against the REAL catalogue v1.1.1 (ponzi-guaranteed-returns
+ whatsapp-investment-group). The routing law's hit definition is
risk_level in ("critical","high") OR matched_patterns non-empty — so "high"
IS a scam_shield route. We assert risk in (high, critical) for that prompt,
and separately prove the critical band with an amplified prompt (adds urgency,
which fires the deterministic money-multiplier + guaranteed-amount signals).
"""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
from fastapi.testclient import TestClient

from core.orchestrator import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
c = TestClient(app)

_failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"[PASS] {name} {extra}")
    else:
        print(f"[FAIL] {name} {extra}")
        _failures.append(name)


def ask(prompt, **kw):
    body = {"prompt": prompt}
    body.update(kw)
    return c.post("/v1/ask", json=body)


# 0. GET /v1/ask documents the routing law
r = c.get("/v1/ask")
check("routing-law doc 200", r.status_code == 200)
b = r.json()
check("doc states safety-first scam route", "scam" in b["routing_law"][0] and "SAFETY FIRST" in b["routing_law"][0])
check("doc names valid overrides", b["mode_override"]["valid"] == ["scam", "services", "history"])

# 1. Scam prompt -> scam_shield, verified, risk high/critical (see header note)
r = ask("invest R500 get R5000, guaranteed returns, whatsapp group")
check("scam prompt 200", r.status_code == 200)
b = r.json()
check("scam prompt routes to scam_shield", b["mode_executed"] == "scam_shield", b["mode_executed"])
check("scam hit is_verified", b["is_verified"] is True)
check("scam risk high or critical (real catalogue scores 9=high)", b["payload"]["risk_level"] in ("high", "critical"), b["payload"]["risk_level"])
check("scam payload is the real scam_check shape",
      all(k in b["payload"] for k in ("risk_level", "risk_score", "verdict", "matched_patterns", "disclaimer")))
check("scam matched_patterns non-empty", len(b["payload"]["matched_patterns"]) >= 1)
check("scam cites the catalogue file", any("scam_patterns.json" in s for s in b["sources"]), str(b["sources"]))
check("scam not a knowledge gap", b["knowledge_gap"] is False)

# 1b. Amplified scam prompt reaches the critical band (deterministic signals)
r = ask("Invest R500 today and get a guaranteed R5000 payout tomorrow, join my whatsapp investment group now")
b = r.json()
check("amplified scam is critical", b["payload"]["risk_level"] == "critical",
      f"{b['payload']['risk_level']} score={b['payload']['risk_score']}")

# 2. Services prompt -> everyday_services, sources >= 2 (anti-hallucination law)
r = ask("how do I appeal my SRD grant")
b = r.json()
check("services prompt routes to everyday_services", b["mode_executed"] == "everyday_services", b["mode_executed"])
check("services sources >= 2", len(b["sources"]) >= 2, f"got {len(b['sources'])}")
check("services payload has real entries", b["payload"]["count"] >= 1 and len(b["payload"]["entries"]) >= 1)
check("services top entry is the SRD appeal guide", b["payload"]["entries"][0]["id"] == "srd-grant-appeal",
      b["payload"]["entries"][0]["id"])

# 3. History prompt -> african_history
r = ask("tell me about Great Zimbabwe")
b = r.json()
check("history prompt routes to african_history", b["mode_executed"] == "african_history", b["mode_executed"])
check("history payload includes great-zimbabwe",
      any(e["id"] == "great-zimbabwe" for e in b["payload"]["entries"]),
      str([e["id"] for e in b["payload"]["entries"]]))
check("history sources real (UNESCO present)", any("UNESCO" in s for s in b["sources"]))

# 4. Gap prompt -> honest knowledge_gap, NOTHING fabricated
r = ask("best recipe for chocolate cake")
b = r.json()
check("gap prompt routes to knowledge_gap", b["mode_executed"] == "knowledge_gap", b["mode_executed"])
check("gap knowledge_gap=true", b["knowledge_gap"] is True)
check("gap is_verified=false", b["is_verified"] is False)
check("gap sources == [] (no fabricated citations)", b["sources"] == [])
check("gap guidance names the real modes",
      all(m in b["payload"]["guidance"] for m in ("scam", "services", "history")))
check("gap has NO answer/synthesis keys (anti-hallucination law)",
      "answer" not in b["payload"] and "synthesis" not in b["payload"] and "recipe" not in str(b["payload"]).lower())

# 5. Scam precedence: mixed SASSA + guaranteed-returns prompt -> scam wins
r = ask("SASSA grant status check, guaranteed returns on offer")
b = r.json()
check("mixed scam+services prompt -> scam_shield (safety first)", b["mode_executed"] == "scam_shield", b["mode_executed"])
check("precedence trace shows scam evaluated first", b["routing_trace"][0].startswith("scam:"), str(b["routing_trace"]))

# 6. mode_override honored: history on a scammy prompt -> never scam_shield
r = ask("invest R500 get R5000, guaranteed returns, whatsapp group", mode_override="history")
b = r.json()
check("override=history 200", r.status_code == 200)
check("override honored: history or gap, NEVER scam",
      b["mode_executed"] in ("african_history", "knowledge_gap"), b["mode_executed"])
check("override recorded in trace", any(t.startswith("override: history") for t in b["routing_trace"]))

# 7. Invalid mode_override -> 400 with the valid set
r = ask("anything", mode_override="prophecy")
check("invalid override -> 400", r.status_code == 400, f"got {r.status_code}")
check("400 detail lists the valid set", all(m in r.json()["detail"] for m in ("scam", "services", "history")))

# 8. Timing + trace contract
r = ask("how do I appeal my SRD grant")
b = r.json()
check("execution_time_ms > 0", b["execution_time_ms"] > 0, f"{b['execution_time_ms']}")
check("execution_time_ms < 5000 (zero-cost packs)", b["execution_time_ms"] < 5000)
check("routing_trace non-empty", len(b["routing_trace"]) >= 1)
check("services trace reports hit count", any(t.startswith("services:") for t in b["routing_trace"]), str(b["routing_trace"]))

# 9. Request validation: empty prompt -> 422
r = ask("")
check("empty prompt rejected (422)", r.status_code == 422, f"got {r.status_code}")

# 10. Mounted on the real app
import core.main as main_app  # noqa: E402
paths = [r_.path for r_ in main_app.app.routes]
check("main.py mounts /v1/ask", any(p.startswith("/v1/ask") for p in paths),
      str([p for p in paths if "ask" in p]))

if _failures:
    print(f"\n{len(_failures)} FAILURES: {_failures}")
    sys.exit(1)
print("\nALL ORCHESTRATOR CHECKS PASSED (10 groups)")
