"""CIVIC-1 battery: neutral, sourced, honest civic & voter education.
Runs against the real router (TestClient), zero network. Every check passes
or the script exits 1.

Proves:
  * Neutrality by construction: alphabetical order, identical field shape
    and depth for every party, no evaluative language markers.
  * Anti-hallucination: the paste's fake "synchronized with latest public
    manifesto records" claim can NEVER appear; update_status is honest;
    knowledge_version is the real file constant, not an incremented float.
  * Every response carries the non-partisan disclaimer.
  * Balanced education: voting importance AND apathy risks both present.
  * Honest 404 for parties outside the curated snapshot; kill switch 503.
"""
import os
import sys
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.civic_engine import router as civic_router, KNOWLEDGE_VERSION, POLITICAL_PARTIES

app = FastAPI()
app.include_router(civic_router)
c = TestClient(app)

_failures = []

def check(name, cond, extra=""):
    if cond:
        print(f"[PASS] {name} {extra}")
    else:
        print(f"[FAIL] {name} {extra}")
        _failures.append(name)


# ── 1. Party landscape: neutrality by construction ───────────────────────
r = c.get("/v1/civic/parties")
check("parties 200", r.status_code == 200)
b = r.json()
names = [p["party_name"] for p in b["parties"]]
check("6 curated parties", len(names) == 6, f"got {len(names)}")
check("alphabetical order (no ranking)", names == sorted(names), f"got {names}")
shapes = {tuple(sorted(p.keys())) for p in b["parties"]}
check("identical field shape for every party", len(shapes) == 1)
depths = {len(p["key_pillars"]) for p in b["parties"]}
check("equal pillar depth (3 each)", depths == {3}, f"got {depths}")
check("every party names its manifesto source",
      all("Manifesto" in p["source"] for p in b["parties"]))
check("every party carries the verification caveat",
      all("confirm against the current official manifesto" in p["verification"] for p in b["parties"]))
check("ordering disclaimer declared", "alphabetical" in b["ordering"])
check("disclaimer present + non-partisan",
      "NOT political advice" in b["disclaimer"] and "does not endorse" in b["disclaimer"])
check("version is the real file constant", b["knowledge_version"] == KNOWLEDGE_VERSION)

# ── 2. Anti-hallucination: the paste's fake sync claim can never appear ──
r = c.post("/v1/civic/empowerment-guidance",
           json={"user_query": "How do parties approach job creation?"})
check("guidance 200", r.status_code == 200)
g = r.json()
blob = str(g).lower()
check("NO fabricated 'synchronized' claim", "synchronized" not in blob)
check("NO fabricated 'validated' claim", "validated and" not in blob)
check("update_status is honest (curated, no live sync)",
      "no live sync" in g["update_status"].lower())
check("learning loop answered honestly",
      "not a live agent" in g["learning_loop_honest_status"])
check("version NOT an incremented float", g["knowledge_version"] == KNOWLEDGE_VERSION
      and isinstance(g["knowledge_version"], str))
check("query echoed back", g["query_received"] == "How do parties approach job creation?")
check("full landscape returned (no editorial filtering)",
      len(g["party_landscape"]) == len(POLITICAL_PARTIES))
check("query_note explains non-filtering", "editorialize" in g["query_note"])

# ── 3. Balanced education: both sides, every time ────────────────────────
check("voting importance present", len(g["voting_importance"]) == 3)
check("apathy risks present", len(g["apathy_risks"]) == 3)
check("historical context attached", len(g["historical_context"]) == 2)
check("history summary honours the struggle", "sacrifice" in g["history_summary"])

r = c.get("/v1/civic/voter-education")
check("voter-education 200", r.status_code == 200)
v = r.json()
check("registration steps present", len(v["how_to_register"]) == 3)
check("IEC official channel named", "elections.org.za" in v["official_channels"]["iec"])
check("IEC details honestly flagged as changeable", "can change" in v["official_channels"]["iec"])
check("balanced: importance + risks", len(v["why_voting_matters"]) == 3
      and len(v["risks_of_disengagement"]) == 3)
check("disclaimer on education endpoint", "NOT political advice" in v["disclaimer"])

# ── 4. History endpoint + archive cross-link ─────────────────────────────
r = c.get("/v1/civic/history")
check("history 200", r.status_code == 200)
h = r.json()
check("2 curated history entries", len(h["entries"]) == 2)
check("every entry links the sourced archive",
      all("/v1/history/entries?q=" in e["sources_via"] for e in h["entries"]))
check("deeper archive route declared", h["deeper_archive"].startswith("GET /v1/history"))

# ── 5. Party detail + honest 404 ─────────────────────────────────────────
r = c.get("/v1/civic/parties/anc")
check("party detail 200", r.status_code == 200)
check("detail has source + caveat", "Manifesto" in r.json()["party"]["source"])
r = c.get("/v1/civic/parties/invented-party")
check("unknown party -> 404", r.status_code == 404)
d = r.json()["detail"]
check("404 is honest (curation gap, not judgement)", "curation gap" in d["honest_note"])
check("404 lists what IS curated", len(d["available"]) == 6)

# ── 6. Determinism ───────────────────────────────────────────────────────
p1 = c.post("/v1/civic/empowerment-guidance", json={"user_query": "land reform"})
p2 = c.post("/v1/civic/empowerment-guidance", json={"user_query": "land reform"})
check("deterministic: same query, same guidance", p1.json() == p2.json())

# ── 7. Kill switch ───────────────────────────────────────────────────────
os.environ["DISABLED_ENGINES"] = "civic_engine"
r = c.get("/v1/civic/parties")
check("kill switch -> 503 fail-closed", r.status_code == 503)
r = c.post("/v1/civic/empowerment-guidance", json={"user_query": "x"})
check("kill switch covers POST too", r.status_code == 503)
del os.environ["DISABLED_ENGINES"]

# ── 8. Neutrality tripwire: banned evaluative language in party data ─────
BANNED = ["best", "worst", "corrupt party", "vote for", "do not vote", "superior", "inferior"]
data_blob = str(POLITICAL_PARTIES).lower()
check("no evaluative/endorsement language in party data",
      not any(w in data_blob for w in BANNED))

print()
if _failures:
    print(f"CIVIC-1 BATTERY FAILED: {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("CIVIC-1 BATTERY: all checks passed — neutral, sourced, honest, zero-infra.")
sys.exit(0)
