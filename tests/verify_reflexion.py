"""UNIFY-16 verification — Reflexion pipeline with a MOCKED kimi_client
(deterministic, offline), real SQLAlchemy persistence on sqlite, routing
heuristic, A/B harness, fail-closed paths."""
import json
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import core.reflexion as rx
from core.reflexion import router
from core.models import Base
import core.reflexion_models  # noqa: F401 - register table

app = FastAPI()
app.include_router(router)
engine = create_engine("sqlite:///:memory:",
                       connect_args={"check_same_thread": False},
                       poolclass=StaticPool)  # one shared in-memory DB across sessions
Base.metadata.create_all(engine)
app.state.db_engine = engine

# Also give the middleware-free app a request.state.user_country default via middleware
@app.middleware("http")
async def _country(request, call_next):
    request.state.user_country = "ZAF"
    return await call_next(request)

c = TestClient(app)

def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        sys.exit(1)

# ── Mock kimi_client.chat_completion ─────────────────────────────────────
REAL_CHAT = rx.kimi_client.chat_completion  # saved for the fail-closed test
CALLS = []
DRAFT = "The sky is blue because of Rayleigh scattering."
REVISED = "The sky appears blue mainly due to Rayleigh scattering of shorter wavelengths."

def fake_chat(system, user, *, tools=None, timeout=60):
    CALLS.append(system[:20])
    if "fact-checking critic" in system:
        return json.dumps({
            "factuality": {"pass": False, "notes": "imprecise wording"},
            "grounding": {"pass": True, "notes": "on topic"},
            "policy": {"pass": True, "notes": "ok"},
            "verdict": "revise",
            "issues": ["tighten the explanation"],
        })
    if "Rewrite your draft" in system:
        return REVISED
    return DRAFT

rx.kimi_client.chat_completion = fake_chat

# 1. Simple query -> NOT routed, 1 call only, verdict unrouted
CALLS.clear()
r = c.post("/v1/reflexion/answer", json={"question": "Hi, what is your name?"})
check("simple answer 200", r.status_code == 200)
b = r.json()
check("simple query not routed", b["routed"] is False, b["route_reason"])
check("unrouted verdict", b["verdict"] == "unrouted")
check("exactly 1 LLM call (0 added latency)", len(CALLS) == 1, f"calls={len(CALLS)}")
check("critique is None when unrouted", b["critique"] is None)
check("trace persisted", b["trace_persisted"] is True and b["trace_id"])

# 2. Risky query -> routed, critique -> revise -> revised answer ships
CALLS.clear()
risky = "Should I invest in this scheme that guarantees 30% per month returns, and what does the law say about it?"
r = c.post("/v1/reflexion/answer", json={"question": risky})
b = r.json()
check("risky query routed", b["routed"] is True, b["route_reason"])
check("3 LLM calls (draft+critique+revise)", len(CALLS) == 3, f"calls={len(CALLS)}")
check("verdict revised", b["verdict"] == "revised")
check("revised answer ships (not draft)", b["answer"] == REVISED)
check("critique trace in response", b["critique"]["verdict"] == "revise")
check("latency recorded per stage", all(k in b["latency_ms"] for k in ("draft", "critique", "revise", "total")))

# 3. Trace retrievable from DB with full trail
tid = b["trace_id"]
r = c.get(f"/v1/reflexion/traces/{tid}")
check("trace fetch 200", r.status_code == 200)
t = r.json()
check("trace holds draft", t["draft"] == DRAFT)
check("trace holds critique", t["critique"]["issues"] == ["tighten the explanation"])
check("trace holds final", t["final_answer"] == REVISED)
check("trace has latency", t["latency_ms"]["total"] >= 0)

# 4. Accept path: critic says accept -> draft ships, 2 calls
def fake_accept(system, user, *, tools=None, timeout=60):
    CALLS.append(system[:20])
    if "fact-checking critic" in system:
        return json.dumps({"factuality": {"pass": True, "notes": ""},
                           "grounding": {"pass": True, "notes": ""},
                           "policy": {"pass": True, "notes": ""},
                           "verdict": "accept", "issues": []})
    return DRAFT
rx.kimi_client.chat_completion = fake_accept
CALLS.clear()
r = c.post("/v1/reflexion/answer", json={"question": risky, "force": True})
b = r.json()
check("accept path: 2 calls", len(CALLS) == 2, f"calls={len(CALLS)}")
check("accept path: verdict accepted", b["verdict"] == "accepted")
check("accept path: draft ships", b["answer"] == DRAFT)

# 5. Flag path: unparseable critique -> fail-closed flag, draft NOT shipped
rx.kimi_client.chat_completion = lambda system, user, **kw: (
    "NOT JSON AT ALL" if "fact-checking critic" in system else DRAFT)
r = c.post("/v1/reflexion/answer", json={"question": risky})
b = r.json()
check("unparseable critique -> flagged", b["verdict"] == "flagged")
check("flagged: draft NOT shipped", b["answer"] == rx._FLAGGED_MESSAGE)

# 6. Routing heuristic unit checks
check("force=False never routes", rx.should_route(risky, force=False)[0] is False)
check("force=True always routes", rx.should_route("hi", force=True)[0] is True)
check("multi-part routes", rx.should_route("What is tax? When is the deadline?")[0] is True)
check("long question routes", rx.should_route("x" * 300)[0] is True)
check("short simple skips", rx.should_route("Hello there")[0] is False)

# 7. A/B harness
rx.kimi_client.chat_completion = fake_chat
r = c.post("/v1/reflexion/ab", json={"question": risky})
check("ab 200", r.status_code == 200)
b = r.json()
check("ab arms linked by group", bool(b["ab_group"]))
check("direct arm unrouted", b["arm_direct"]["verdict"] == "unrouted")
check("critique arm revised", b["arm_critique"]["verdict"] == "revised")
check("ab detects differing answers", b["comparison"]["answers_differ"] is True)
check("ab latency cost reported", "latency_cost_ms" in b["comparison"])
# both traces in DB under the same group
from sqlalchemy.orm import Session
from core.reflexion_models import ReflexionTrace
with Session(engine) as s:
    rows = s.query(ReflexionTrace).filter_by(ab_group=b["ab_group"]).all()
check("both ab traces persisted", len(rows) == 2, f"rows={len(rows)}")
check("ab arms labelled", {r_.ab_arm for r_ in rows} == {"direct", "critique"})

# 8. Config endpoint documents the budget
r = c.get("/v1/reflexion/config")
b = r.json()
check("config: 0 added calls for simple", b["latency_budget"]["simple_query_added_calls"] == 0)
check("config: max 2 added calls", b["latency_budget"]["max_added_calls"] == 2)
check("config: no recursive loops", b["latency_budget"]["no_recursive_loops"] is True)

# 9. Fail-closed without API key (real kimi_client, mock removed)
rx.kimi_client.chat_completion = REAL_CHAT
from fastapi import HTTPException
import os
os.environ.pop("KIMI_API_KEY", None)
r = c.post("/v1/reflexion/answer", json={"question": "hello"})
check("missing key -> 500 fail-closed", r.status_code == 500, f"got {r.status_code}")

# 10. main.py mounts + migration chain
import importlib
import core.main as m
importlib.reload(m)
paths = [getattr(r_, "path", "") for r_ in m.app.routes]
check("main.py mounts /v1/reflexion", any(p.startswith("/v1/reflexion") for p in paths),
      str([p for p in paths if "reflexion" in p]))
import re
mig = open(_REPO / "alembic/versions/006_reflexion_traces.py").read()
check("006 chains on 005", re.search(r'^down_revision = "005_companion_system"$', mig, re.M) is not None)
check("006 has RLS force", "FORCE ROW LEVEL SECURITY" in mig)
check("006 has country policy", "country_tenant_isolation" in mig and "luqi_app_user" in mig)

print("\nALL REFLEXION CHECKS PASSED (10/10 groups)")
