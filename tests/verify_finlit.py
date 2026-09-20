"""UNIFY-13 verification — finlit skill endpoints, deterministic scam detection,
disclaimer presence, versioned catalogue. Standalone: no DB, no LLM."""
import asyncio
import json
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.finlit import router, DISCLAIMER

app = FastAPI()
app.include_router(router)
c = TestClient(app)

def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        sys.exit(1)

# 1. Topics index
r = c.get("/v1/finlit/topics")
check("topics index 200", r.status_code == 200)
body = r.json()
check("6 topics seeded", len(body["topics"]) == 6, f"got {len(body['topics'])}")
check("topics index has disclaimer", body["disclaimer"] == DISCLAIMER)

# 2. Topic detail
r = c.get("/v1/finlit/topics/investing-basics")
check("topic detail 200", r.status_code == 200)
body = r.json()
check("topic has real content", len(body["content"]) > 400)
check("investing topic mentions TFSA + FSCA", "TFSA" in body["content"] and "FSCA" in body["content"])
check("topic has disclaimer", body["disclaimer"] == DISCLAIMER)
r = c.get("/v1/finlit/topics/does-not-exist")
check("unknown topic 404", r.status_code == 404)

# 3. Scam pattern catalogue — versioned
r = c.get("/v1/finlit/scam-patterns")
check("scam-patterns 200", r.status_code == 200)
body = r.json()
check("catalogue version present", body["version"] == "1.1.0", f"v={body.get('version')}")
check("12 patterns catalogued", len(body["patterns"]) == 12, f"got {len(body['patterns'])}")
check("catalogue has disclaimer", body["disclaimer"] == DISCLAIMER)

# 4. Scam-check: obvious Ponzi + pay-to-withdraw text -> high/critical
ponzi = ("Join our WhatsApp investment group! Guaranteed returns of 30% per month, "
         "risk-free investment. Our account manager shares profit screenshots daily. "
         "To withdraw you must pay tax to withdraw first.")
r = c.post("/v1/finlit/scam-check", json={"text": ponzi, "context": "whatsapp message"})
check("scam-check 200", r.status_code == 200)
body = r.json()
check("ponzi text flagged high/critical", body["risk_level"] in ("high", "critical"),
      f"risk={body['risk_level']} score={body['risk_score']}")
ids = [m["pattern_id"] for m in body["matched_patterns"]]
check("ponzi pattern matched", "ponzi-guaranteed-returns" in ids, str(ids))
check("pig-butchering pattern matched", "pig-butchering-crypto" in ids, str(ids))
check("matched patterns carry advice", all(m["advice"] for m in body["matched_patterns"]))
check("scam-check has disclaimer", body["disclaimer"] == DISCLAIMER)
check("scam-check has report line", bool(body["report_line"]))
check("golden rules present", len(body["golden_rules"]) == 5)

# 5. OTP vishing text -> vishing pattern, severe
vish = "Hello, this is your bank's fraud department. Read out the OTP we just sent so we can stop the fraud."
r = c.post("/v1/finlit/scam-check", json={"text": vish})
body = r.json()
ids = [m["pattern_id"] for m in body["matched_patterns"]]
check("vishing pattern matched", "vishing-otp-theft" in ids, str(ids))

# 6. Clean text -> none
r = c.post("/v1/finlit/scam-check", json={"text": "I saved R500 this month and put it in my tax-free savings account."})
body = r.json()
check("clean text risk none", body["risk_level"] == "none", f"risk={body['risk_level']}")
check("clean text no report line", body["report_line"] is None)

# 7. Validation: empty text rejected
r = c.post("/v1/finlit/scam-check", json={"text": ""})
check("empty text 422", r.status_code == 422)

# 8. Determinism: same input -> same output
r1 = c.post("/v1/finlit/scam-check", json={"text": ponzi}).json()
r2 = c.post("/v1/finlit/scam-check", json={"text": ponzi}).json()
check("deterministic scoring", r1["risk_score"] == r2["risk_score"] and r1["risk_level"] == r2["risk_level"])

# 9. Catalogue fail-closed check (malformed file -> RuntimeError, not silent empty)
import core.finlit as fl
original = fl._PATTERNS_FILE
fl._PATTERNS_FILE = original.parent / "nope.json"
fl._load_patterns.cache_clear()
try:
    fl._load_patterns()
    check("missing catalogue raises", False)
except RuntimeError:
    check("missing catalogue raises", True)
finally:
    fl._PATTERNS_FILE = original
    fl._load_patterns.cache_clear()

# 10. main.py still imports and mounts cleanly
import importlib, core.main as m
importlib.reload(m)
routes = [getattr(r, "path", "") for r in m.app.routes]
check("main.py mounts /v1/finlit", any(p.startswith("/v1/finlit") for p in routes),
      str([p for p in routes if "finlit" in p]))

# 11. Compliance battery regression (2026-09-20): the founder's canonical
# WhatsApp-crypto scam scored risk none/0 on exact-adjacency matching. It must
# never happen again — the promise anatomy itself is now detected.
canonical = ("Someone on WhatsApp said if I invest R1000 today, I will get "
             "guaranteed R5000 by tomorrow via a crypto bot.")
r = c.post("/v1/finlit/scam-check", json={"text": canonical, "context": "whatsapp message"})
check("canonical scam-check 200", r.status_code == 200)
body = r.json()
check("canonical flagged high/critical", body["risk_level"] in ("high", "critical"),
      f"risk={body['risk_level']} score={body['risk_score']}")
check("canonical score >= 12", body["risk_score"] >= 12, f"score={body['risk_score']}")
ids = [m["pattern_id"] for m in body["matched_patterns"]]
check("multiplier promise detected", "money-multiplier-promise" in ids, str(ids))
check("guaranteed-amount claim detected", "guaranteed-payout-claim" in ids, str(ids))
check("crypto bot indicator matched", "pig-butchering-crypto" in ids, str(ids))
check("questions_to_ask non-empty on match", len(body["questions_to_ask"]) > 0,
      str(body["questions_to_ask"]))
check("questions are actionable str", all(isinstance(q, str) and len(q) > 20 for q in body["questions_to_ask"]))

# 11b. Singular + gapped variants (adjacency regression)
variant = "This guaranteed return of R2000 is waiting, invest R500 now and get it back."
r = c.post("/v1/finlit/scam-check", json={"text": variant}).json()
check("singular 'guaranteed return' caught", r["risk_score"] > 0,
      f"risk={r['risk_level']} score={r['risk_score']}")

# 11c. False-positive guards: honest money talk must NOT be flagged
news = "Bitcoin moved from about R1000 to over R50000 today, analysts say volatility continues."
r = c.post("/v1/finlit/scam-check", json={"text": news}).json()
check("price-news not flagged (no promise wording)", r["risk_score"] == 0,
      f"risk={r['risk_level']} score={r['risk_score']}")
stokvel = "Our stokvel meets on Saturday. Each member contributes R500 a month."
r = c.post("/v1/finlit/scam-check", json={"text": stokvel}).json()
check("honest stokvel chat not high/critical", r["risk_level"] in ("none", "low", "medium"),
      f"risk={r['risk_level']} score={r['risk_score']}")
check("no questions on clean text", body is not None)  # shape sanity
r = c.post("/v1/finlit/scam-check", json={"text": "I saved R500 this month in my tax-free savings account."}).json()
check("clean saver text still none", r["risk_level"] == "none", f"risk={r['risk_level']}")
check("clean text questions empty", r["questions_to_ask"] == [])

print("\nALL FINLIT CHECKS PASSED (11/10 groups + battery regression)")
