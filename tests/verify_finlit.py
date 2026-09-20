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
check("catalogue version present", body["version"] == "1.0.0", f"v={body.get('version')}")
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

print("\nALL FINLIT CHECKS PASSED (10/10 groups)")
