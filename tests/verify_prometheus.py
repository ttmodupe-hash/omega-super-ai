"""Verify the Prometheus observability layer (omega-super-ai backlog: /api/prometheus gap)."""
import os, sys, time
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

os.environ.pop("KIMI_API_KEY", None)

passed = []
def check(name, cond):
    assert cond, f"FAIL: {name}"
    passed.append(name)
    print(f"[PASS] {name}")

from core import prometheus as pm

# 1. Pure renderer: format contract
body = pm.render_prometheus(
    http_counts={("GET", "/v1/health", 200): 3, ("POST", "/v1/agent/execute", 200): 1},
    http_durations={"/v1/health": [0.001, 0.01, 0.2]},
    gate_pending=2,
    cost_telemetry={"pct_of_budget": 12.5, "by_provider": {"kimi": {"calls": 4, "est_cost_usd": 0.001}}},
    ops={"deployments": 3, "open_incidents": 1},
    version="5.35.7", now=time.time(),
)
check("HELP/TYPE pairs present", "# HELP luqi_http_requests_total" in body and "# TYPE luqi_http_requests_total counter" in body)
check("counter sample w/ labels", 'luqi_http_requests_total{method="GET",route="/v1/health",status="200"} 3' in body)
check("histogram buckets cumulative", 'luqi_http_request_duration_seconds_bucket{route="/v1/health",le="0.025"} 2' in body)
check("histogram +Inf == count", 'le="+Inf"} 3' in body and 'luqi_http_request_duration_seconds_count{route="/v1/health"} 3' in body)
check("histogram sum", 'luqi_http_request_duration_seconds_sum{route="/v1/health"} 0.211' in body)
check("gate gauge", "luqi_gate_pending 2" in body)
check("llm counter per provider", 'luqi_llm_calls_total{provider="kimi"} 4' in body)
check("est cost labeled gauge", 'luqi_llm_est_cost_usd{provider="kimi"} 0.001' in body and "chars/4 estimate" in body)
check("budget pct gauge", "luqi_cost_budget_pct 12.5" in body)
check("dora gauges", "luqi_ops_deployments_7d 3" in body and "luqi_ops_incidents_open 1" in body)
check("uptime gauge", "luqi_uptime_seconds" in body)
check("build info version stamp", 'luqi_build_info{version="5.35.7"} 1' in body)
check("gate gauge omitted when None (never faked)",
      "luqi_gate_pending" not in pm.render_prometheus({}, {}, None, {"by_provider": {}}, {}, "v").split("# TYPE luqi_gate_pending gauge")[-1])

# 2. Label escaping
check("label escaping", '\\"' in pm._esc('a"b') and "\\\\" in pm._esc("a\\b"))

# 3. Live app: middleware counts, scrape endpoint, content type
from fastapi.testclient import TestClient
from core.main import app
client = TestClient(app)

r = client.get("/v1/health")
check("health 200", r.status_code == 200)
r = client.get("/v1/companion/status")
check("companion status 200", r.status_code == 200)

m = client.get("/metrics")
check("scrape 200", m.status_code == 200)
check("prometheus content type", m.headers["content-type"].startswith("text/plain; version=0.0.4"))
text = m.text
check("live: health counted", 'route="/v1/health"' in text and 'status="200"' in text)
check("live: companion counted", 'route="/v1/companion/status"' in text)
check("live: gate gauge present", "luqi_gate_pending 0" in text)
check("live: budget gauge present", "luqi_cost_budget_pct" in text)
check("live: build info matches app version", f'luqi_build_info{{version="{app.version}"}} 1' in text)

# 4. Scrape itself is not counted (no self-referential cardinality)
before = dict(pm._http_counts)
client.get("/metrics")
after = dict(pm._http_counts)
check("/metrics scrape not counted", before == after)

# 5. Unknown route -> 'unmatched' family (no cardinality blowup)
client.get("/definitely-not-a-route-12345")
check("unknown route -> unmatched family",
      any(k[1] == "unmatched" for k in pm._http_counts))

# 6. Cost bump flows through to exposition
from core import cost_telemetry as ct
ct.bump("kimi", 4000)
text2 = client.get("/metrics").text
check("cost bump visible in exposition", 'luqi_llm_calls_total{provider="kimi"} 1' in text2)

# 7. Duration ring bound
pm._http_durations["/x"] = [1.0] * 3000
with pm._lock:
    buf = pm._http_durations.setdefault("/x", [])
    buf.append(0.5)
    if len(buf) > pm._DURATION_KEEP:
        del buf[: len(buf) - pm._DURATION_KEEP]
check("duration ring bounded", len(pm._http_durations["/x"]) == pm._DURATION_KEEP)

# 8. main.py wiring
src = open(_REPO / "core/main.py").read()
check("main mounts prometheus router", "include_router(prometheus_router)" in src)
check("main registers metrics middleware", "metrics_middleware" in src)

print(f"\nALL PROMETHEUS CHECKS PASSED ({len(passed)} assertions)")
