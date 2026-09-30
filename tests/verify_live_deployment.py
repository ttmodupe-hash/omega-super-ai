#!/usr/bin/env python3
"""
Luqi-ai — Live Deployment Verification Gate (LIVE-DEPLOY-VERIFY-1)
===================================================================
Run this AFTER `push-unified-merge.sh` and the Railway redeploy to certify
that the live engine really does what the repo says it does.

    python3 verify-live-deployment.py
    python3 verify-live-deployment.py https://your-engine.up.railway.app

House laws honoured by construction:
  * stdlib only — zero pip installs, zero cost
  * every check is a REAL HTTP probe with REAL assertions
  * NO simulated fallback: any failure -> exit code 1, loudly
  * latencies are measured, percentiles computed with the statistics module
  * nothing is printed as "VERIFIED" unless the checks actually passed
"""

import json
import statistics
import sys
import time
import urllib.request
import urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1
        else "https://luqi-ai-production.up.railway.app").rstrip("/")
TIMEOUT = 30

results = []   # (check_id, ok, latency_ms, detail)


def probe(check_id, method, path, payload=None):
    """One real round-trip. Returns (ok, latency_ms, json_or_None, error_str)."""
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            ms = round((time.perf_counter() - t0) * 1000, 1)
            return resp.status == 200, ms, json.loads(body), ""
    except urllib.error.HTTPError as e:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return False, ms, None, f"HTTP {e.code}"
    except Exception as e:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return False, ms, None, str(e)


def check(check_id, ok, ms, detail):
    results.append((check_id, bool(ok), ms, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {check_id}  ({ms} ms)  {detail}")


print("=" * 74)
print(" LUQI-AI LIVE DEPLOYMENT VERIFICATION GATE")
print(f" Target: {BASE}")
print("=" * 74)

# -- 1. Health endpoint tells the truth -------------------------------------
ok, ms, d, err = probe("HEALTH", "GET", "/v1/hybrid/health")
check("HEALTH-1 engine reachable, honest status keys", ok and isinstance(d, dict)
      and "kill_switch" in d, ms,
      (f"kill_switch={d.get('kill_switch')}, sklearn={d.get('sklearn_available')}, "
       f"ml_fallback={d.get('ml_offline_fallback')}") if d else err)

# -- 2. Scam Shield catches a known fraud pattern ---------------------------
ok, ms, d, err = probe("SCAM", "POST", "/v1/finlit/scam-check",
                       {"text": "Invest R500, get R5000 back in 7 days, guaranteed"})
check("SCAM-1 known Ponzi phrasing matched against catalogue", ok and d
      and d.get("matched_patterns"), ms,
      (f"risk={d.get('risk_level')}, patterns={len(d.get('matched_patterns') or [])}")
      if d else err)

# -- 3. Everyday Services answers a real SRD grant query --------------------
ok, ms, d, err = probe("SERVICES", "GET", "/v1/services/entries?q=SRD%20grant")
check("SERVICES-1 SRD grant guide returned", ok and d and d.get("entries"), ms,
      (f"entries={len(d.get('entries') or [])}") if d else err)

# -- 4. African History archive answers --------------------------------------
ok, ms, d, err = probe("HISTORY", "GET", "/v1/history/entries?q=Great%20Zimbabwe")
check("HISTORY-1 Great Zimbabwe entry returned", ok and d and d.get("entries"), ms,
      (f"entries={len(d.get('entries') or [])}") if d else err)

# -- 5. ROUTER-GUARD-1 regression: stray tokens must not misroute ------------
ok, ms, d, err = probe("GUARD", "POST", "/v1/hybrid/process",
                       {"text": "zzz qqq vvv wobble gribble flense"})
blob = json.dumps(d) if d else ""
check("GUARD-1 nonsense query never produces the Postbank Black Card misroute",
      ok and d is not None and "Postbank Black Card" not in blob, ms,
      (f"engine_used={d.get('engine_used')}, confidence={d.get('confidence')}")
      if d else err)

# -- 6. Hybrid path reports honest measured latency --------------------------
ok, ms, d, err = probe("HYBRID", "POST", "/v1/hybrid/process",
                       {"text": "What is a TFSA?"})
check("HYBRID-1 response carries real latency_ms and confidence", ok and d
      and isinstance(d.get("latency_ms"), (int, float))
      and isinstance(d.get("confidence"), (int, float)), ms,
      (f"latency_ms={d.get('latency_ms')}, confidence={d.get('confidence')}, "
       f"engine_used={d.get('engine_used')}") if d else err)

# -- 7. HERITAGE-1 live (post-redeploy feature) ------------------------------
ok, ms, d, err = probe("HERITAGE", "GET", "/v1/heritage")
check("HERITAGE-1 archive endpoint live (activates on redeploy)", ok and d
      and isinstance(d.get("entry_count"), int), ms,
      (f"entry_count={d.get('entry_count')}") if d
      else err + " — expected before the unified push + redeploy; re-run after")

# -- 8. IKS-1 live (post-redeploy feature) -----------------------------------
ok, ms, d, err = probe("IKS", "GET", "/v1/iks")
check("IKS-1 medicine archive endpoint live (activates on redeploy)", ok and d
      and isinstance(d.get("entry_count"), int), ms,
      (f"entry_count={d.get('entry_count')}") if d
      else err + " — expected before the unified push + redeploy; re-run after")

# -- Honest summary: measured stats, real counts, truthful verdict -----------
lat = sorted(r[2] for r in results)
passed = sum(1 for r in results if r[1])
total = len(results)
print("=" * 74)
print(f" Checks passed : {passed} / {total}")
print(f" Latency p50   : {statistics.median(lat)} ms   (measured)")
if len(lat) >= 2:
    qs = statistics.quantiles(lat, n=100)
    print(f" Latency p99   : {round(qs[98], 1)} ms   (measured)")
else:
    print(f" Latency max   : {lat[-1]} ms   (measured)")
failed = [r for r in results if not r[1]]
if failed:
    print(" Failed checks : " + ", ".join(r[0] for r in failed))
    print(" VERDICT: DEPLOYMENT NOT CERTIFIED — fix the failures above and re-run.")
    print("=" * 74)
    sys.exit(1)
print(" VERDICT: all " + str(total) + " real probes passed against the live engine.")
print("=" * 74)
sys.exit(0)
