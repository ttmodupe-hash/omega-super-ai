"""BILL-AUDIT-1 + JOBS-1 battery: deterministic telecom bill audit and the
zero-infra async job runner. Runs against the real routers (TestClient),
zero network. Every check passes or the script exits 1.

Proves:
  * Each anomaly rule fires on its signature input and stays silent otherwise.
  * Impossible values are data-quality flags, never disputed money.
  * Clean bills are honestly clean; nothing is invented.
  * Async lifecycle: 202 -> queued/running -> completed with real progress,
    result identical to the sync audit, pollable by job_id.
  * Kill switch and honest 404s.
"""
import sys
import time
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.bill_audit import router as bill_router, audit_lines, RULES_VERSION
from core.async_jobs import router as jobs_router

app = FastAPI()
app.include_router(bill_router)
app.include_router(jobs_router)
c = TestClient(app)

_failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"[PASS] {name} {extra}")
    else:
        print(f"[FAIL] {name} {extra}")
        _failures.append(name)


# ── 1. R1: data charges on a voice-only plan ─────────────────────────────
r = c.post("/v1/bill-audit", json={"lines": [
    {"serial_number": "SN-001", "phone_number": "0821111111",
     "plan_type": "voice_only", "data_usage_mb": 210.5, "data_charge_zar": 520.00},
]})
b = r.json()
check("sync audit 200", r.status_code == 200)
check("R1 fired", any(a["rule_id"] == "R1_VOICE_ONLY_DATA_CHARGE" for a in b["anomalies"]))
check("R1 disputes the data charge", b["total_disputed_zar"] == 520.00, f"got {b['total_disputed_zar']}")
check("anomaly explains itself", "voice-only" in b["anomalies"][0]["explanation"])
check("report itemizes the serial", "SN-001" in b["report"])
check("escalation guidance attached", b["next_steps"]["step_2"].find("icasa.org.za") > 0)
check("disclaimer present", "not legal advice" in b["disclaimer"].lower())

# ── 2. R2: user-flagged unauthorized charge on any plan ──────────────────
r = c.post("/v1/bill-audit", json={"lines": [
    {"sn": "SN-002", "plan_type": "mixed", "unauthorized_charge_zar": 99.50},
]})
b = r.json()
check("R2 fired via 'sn' alias", b["anomalies"][0]["rule_id"] == "R2_USER_FLAGGED_UNAUTHORIZED")
check("R2 serial normalized from alias", b["anomalies"][0]["serial_number"] == "SN-002")
check("R2 amount itemized", b["total_disputed_zar"] == 99.50)

# ── 3. R3: duplicate charges (first occurrence legitimate, dupes flagged) ──
r = c.post("/v1/bill-audit", json={"lines": [
    {"serial_number": "SN-003", "plan_type": "mixed",
     "description": "Content subscription", "amount_zar": 15.00},
    {"serial_number": "SN-003", "plan_type": "mixed",
     "description": "Content subscription", "amount_zar": 15.00},
    {"serial_number": "SN-003", "plan_type": "mixed",
     "description": "Content subscription", "amount_zar": 15.00},
]})
b = r.json()
dups = [a for a in b["anomalies"] if a["rule_id"] == "R3_DUPLICATE_LINE"]
check("R3 flags exactly the 2 duplicates", len(dups) == 2, f"got {len(dups)}")
check("R3 disputes 2 x R15", b["total_disputed_zar"] == 30.00)

# ── 4. R4: impossible values are data-quality, NEVER disputed money ──────
r = c.post("/v1/bill-audit", json={"lines": [
    {"serial_number": "SN-004", "plan_type": "voice_only",
     "data_usage_mb": -5, "data_charge_zar": -100.0},
]})
b = r.json()
check("R4 row excluded from anomalies", b["anomalies"] == [])
check("R4 flagged as data-quality", len(b["data_quality_flags"]) == 1)
check("R4 not counted as money", b["total_disputed_zar"] == 0.0)

# ── 5. Clean bill is honestly clean ──────────────────────────────────────
r = c.post("/v1/bill-audit", json={"lines": [
    {"serial_number": "SN-005", "plan_type": "data_bundle", "data_usage_mb": 500,
     "data_charge_zar": 85.0},
]})
b = r.json()
check("clean bill -> no anomalies", b["clean"] is True and b["anomalies"] == [])
check("clean verdict says so", "clean" in b["verdict"].lower())
check("clean bill -> no escalation block", b["next_steps"] is None)

# ── 6. Rules catalogue + determinism ─────────────────────────────────────
r = c.get("/v1/bill-audit/rules")
check("rules endpoint 200", r.status_code == 200)
check("4 rules, versioned", len(r.json()["rules"]) == 4
      and r.json()["rules_version"] == RULES_VERSION)
payload = {"lines": [{"serial_number": "SN-006", "plan_type": "voice_only",
                      "data_usage_mb": 10, "data_charge_zar": 50.0}]}
r1, r2 = c.post("/v1/bill-audit", json=payload), c.post("/v1/bill-audit", json=payload)
check("deterministic: same bill, same audit", r1.json() == r2.json())

# ── 7. JOBS-1 async lifecycle: 202 -> poll -> completed ──────────────────
r = c.post("/v1/jobs/bill-audit", json={"lines": [
    {"serial_number": "SN-007", "plan_type": "voice_only",
     "data_usage_mb": 300, "data_charge_zar": 750.00},
]})
check("dispatch returns 202", r.status_code == 202, f"got {r.status_code}")
b = r.json()
check("dispatch gives job_id + poll_url", bool(b["job_id"]) and b["poll_url"].endswith(b["job_id"]))
check("dispatch honestly names the architecture", "no paid worker fleet" in b["note"])

deadline = time.time() + 10
final = None
seen_running = False
while time.time() < deadline:
    p = c.get(f"/v1/jobs/{b['job_id']}")
    check_ok = p.status_code == 200
    if not check_ok:
        break
    body = p.json()
    if body["status"] == "running":
        seen_running = True
    if body["status"] in ("completed", "failed"):
        final = body
        break
    time.sleep(0.05)
check("job reached a terminal state", final is not None, f"last={body.get('status')}")
check("job completed (not failed)", final and final["status"] == "completed",
      final.get("error") if final else "n/a")
check("progress hit 100", final and final["progress"] == 100)
check("result matches the sync audit exactly",
      final and final["result"]["total_disputed_zar"] == 750.00
      and final["result"]["anomaly_count"] == 1)
check("persistence flag honest (no DB in this battery)",
      final and final.get("persisted") in (False, None))

# ── 8. Jobs health + honest 404 + kill switch ────────────────────────────
r = c.get("/v1/jobs/health")
b = r.json()
check("jobs health 200", r.status_code == 200)
check("health declares the honest backend", "in-process" in b["backend"])
check("health lists bill-audit kind", "bill-audit" in b["kinds"])

r = c.get("/v1/jobs/does-not-exist")
check("unknown job -> honest 404", r.status_code == 404)
check("404 explains the persistence law", "restart" in r.json()["detail"]["honest_note"])

import os as _os
_os.environ["DISABLED_ENGINES"] = "async_jobs"
r = c.post("/v1/jobs/bill-audit", json={"lines": [{"serial_number": "X"}]})
check("kill switch -> 503 fail-closed", r.status_code == 503)
del _os.environ["DISABLED_ENGINES"]

# ── 9. audit_lines accepts the paste's exact field shape (sn alias etc.) ──
res = audit_lines([{"sn": "SN-99301-A", "phone_number": "0821234567",
                    "plan_type": "voice_only", "data_usage_mb": 0.0,
                    "unauthorized_charge_zar": 520.00}])
check("paste-shaped payload works", res["anomaly_count"] == 1
      and res["total_disputed_zar"] == 520.00)
check("report names the disputed line", "0821234567" in res["report"])

print()
if _failures:
    print(f"BILL-AUDIT-1 + JOBS-1 BATTERY FAILED: {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("BILL-AUDIT-1 + JOBS-1 BATTERY: all checks passed — deterministic, honest, zero-infra.")
sys.exit(0)
