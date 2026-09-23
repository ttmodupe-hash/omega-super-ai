"""
GAP-1 verification battery — capability maturity + manifest honesty.

The manifest test is the anti-hallucination guarantee at machine level:
every endpoint the manifest advertises MUST exist in the live app's route
table. A stale or invented tool entry fails this battery.

DB-free, network-free. Run:
    python tests/verify_capabilities.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import capabilities as caps  # noqa: E402

PASS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    assert cond, f"FAIL [{name}] {detail}"
    PASS += 1
    print(f"  ok [{name}] {detail}")


# ── 1. Maturity matrix completeness ───────────────────────────────────────
print("group 1: maturity matrix")
m = caps.capability_maturity()
check("maturity.nine_items", len(m["items"]) == 9, f"got {len(m['items'])}")
ids = [i["id"] for i in m["items"]]
check("maturity.unique_ids", len(set(ids)) == 9)
expected = {"agentic", "reasoning", "multiagent", "mcp_interop", "rag",
            "multimodal", "efficient_models", "iam_guardrails", "confidential_computing"}
check("maturity.covers_checklist", set(ids) == expected, f"missing: {expected - set(ids)}")
allowed = {"built", "partial", "roadmap", "not_applicable"}
for item in m["items"]:
    check(f"maturity.{item['id']}.status_valid", item["status"] in allowed, item["status"])
    check(f"maturity.{item['id']}.evidence", len(item["evidence"]) > 20)
    check(f"maturity.{item['id']}.note", len(item["note"]) > 20)

# ── 2. Honest status distribution (not everything 'built') ────────────────
print("group 2: honesty distribution")
statuses = [i["status"] for i in m["items"]]
check("honest.not_all_built", statuses.count("built") < 9,
      "claiming everything built would itself be a hallucination")
check("honest.has_partial", "partial" in statuses)

# ── 3. Manifest structure ─────────────────────────────────────────────────
print("group 3: manifest structure")
man = caps.capability_manifest()
check("manifest.schema", man["schema"].startswith("luqi.tools/"))
check("manifest.min_tools", len(man["tools"]) >= 8, f"got {len(man['tools'])}")
required_keys = {"name", "endpoint", "method", "description", "auth_required", "live_data"}
for t in man["tools"]:
    check(f"manifest.{t['name']}.keys", required_keys <= set(t.keys()))
    check(f"manifest.{t['name']}.method", t["method"] in ("GET", "POST"))
    check(f"manifest.{t['name']}.live_data_honest", t["live_data"] in (False, "optional"),
          "bare live_data:true is forbidden — 'optional' must be labelled in-payload")
names = [t["name"] for t in man["tools"]]
check("manifest.unique_names", len(set(names)) == len(names))

# ── 4. Manifest vs reality — the anti-hallucination gate ──────────────────
print("group 4: manifest matches live route table")
from core.main import app  # noqa: E402
live = {(r.path, tuple(sorted(getattr(r, "methods", None) or ()))) for r in app.routes}
missing = []
for t in man["tools"]:
    if not any(path == t["endpoint"] and t["method"] in methods for path, methods in live):
        missing.append(f"{t['method']} {t['endpoint']}")
check("manifest.all_routes_live", not missing, f"advertised but not mounted: {missing}")

# ── 5. Capability route wrapper — honest verdicts ─────────────────────────
print("group 5: capability routing verdicts")
import os
for k in ("KIMI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
    os.environ.pop(k, None)  # simulate no providers configured
r = caps.capability_route(caps.RouteRequest(text="solve the derivative of x^2"))
check("route.math_class", r["task_class"] == "math", f"got {r['task_class']}")
check("route.honest_refusal", r["action"] in ("refuse", "answer", "escalate"))
if r["action"] == "refuse":
    check("route.refusal_reason", len(r["reason"]) > 10, r["reason"])
check("route.no_upstream_call", "no upstream call" in r["note"])
check("route.request_id", len(r["request_id"]) >= 8)

# ── 6. Self-reference honesty — capabilities endpoints are in the manifest ─
print("group 6: self-reference")
self_eps = {t["endpoint"] for t in man["tools"]}
check("self.maturity_listed", "/v1/capabilities/maturity" in self_eps)
check("self.manifest_listed", "/v1/capabilities/manifest" in self_eps)
check("self.route_listed", "/v1/capabilities/route" in self_eps)

print(f"\nALL GREEN — {PASS} checks passed (verify_capabilities)")
