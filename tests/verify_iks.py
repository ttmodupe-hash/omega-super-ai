"""verify_iks.py — IKS Ethnobotanical Archive (IKS-1) compliance battery.

Runs against the REAL app router (TestClient). Every check passes or the
script exits 1. Convention: same as verify_history.py / verify_finlit.py.
"""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
from fastapi.testclient import TestClient

from core.iks_engine import router
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


# 1. Overview contract
r = c.get("/v1/iks")
check("overview 200", r.status_code == 200)
b = r.json()
check("overview version 1.0.0", b["version"] == "1.0.0", f"v={b.get('version')}")
check("overview counts 6", b["entry_count"] == 6, f"got {b.get('entry_count')}")
check("overview has 6 categories", len(b["categories"]) == 6)
check("overview carries honesty disclaimer", "not medical advice" in b["disclaimer"])
check("overview carries guardrails", any("Catalogue, not clinic" in g for g in b["guardrails"]))

# 2. Entries list + field integrity
r = c.get("/v1/iks/entries")
check("entries 200", r.status_code == 200)
entries = r.json()["entries"]
check("6 entries", len(entries) == 6, f"got {len(entries)}")
check("summary fields present", all(
    set(("id", "category", "title", "latin_name", "region", "summary")) <= set(e)
    for e in entries))
check("disclaimer travels with list", "not medical advice" in r.json()["disclaimer"])

# 3. Search behaviour
r = c.get("/v1/iks/entries", params={"q": "cancer bush"})
check("search 'cancer bush' -> sutherlandia",
      [e["id"] for e in r.json()["entries"]] == ["motsepelo-sutherlandia"])
r = c.get("/v1/iks/entries", params={"q": "lengana"})
check("search vernacular 'lengana' -> artemisia",
      [e["id"] for e in r.json()["entries"]] == ["lengana-artemisia-afra"])
r = c.get("/v1/iks/entries", params={"q": "zz-elixir-qq"})
check("no match -> honest empty list", r.json()["entries"] == [])
r = c.get("/v1/iks/entries", params={"category": "magic"})
check("unknown category -> 400", r.status_code == 400)
r = c.get("/v1/iks/entries", params={"category": "everyday_infusion"})
check("category filter works", [e["id"] for e in r.json()["entries"]] == ["rooibos-aspalathus"])

# 4. Entry detail + data law
r = c.get("/v1/iks/entries/rooibos-aspalathus")
check("detail 200", r.status_code == 200)
d = r.json()
check("detail has >=2 sources", len(d["sources"]) >= 2, f"got {len(d['sources'])}")
check("detail has cautions", bool(d["cautions"]))
check("detail has research note", bool(d["modern_research_note"]))
check("rooibos records benefit-sharing", "benefit-sharing" in d["summary"])
r = c.get("/v1/iks/entries/nope")
check("unknown id -> 404", r.status_code == 404)

r = c.get("/v1/iks/entries/motsepelo-sutherlandia")
check("sutherlandia carries scam_alert", "scam_alert" in r.json(),
      "(anti-miracle-cure law)")
r = c.get("/v1/iks/entries/lengana-artemisia-afra")
check("lengana names the species-confusion fact", "artemisinin" in r.json()["modern_research_note"])

# 5. Query endpoint: matches XOR honest silence
r = c.post("/v1/iks/query", json={"query": "joint pain Kalahari"})
check("query 200", r.status_code == 200)
b = r.json()
check("query match -> devil's claw", b["matches"][0]["id"] == "devils-claw-harpagophytum")
check("query success carries boundary", "Catalogue, not clinic" in b["boundary"])
check("query success carries disclaimer", bool(b["disclaimer"]))
r = c.post("/v1/iks/query", json={"query": "zz-no-such-plant-qq"})
b = r.json()
check("query no-match status", b["status"] == "no_curated_match")
check("query no-match empty matches", b["matches"] == [])
check("query no-match honest note", "fabricate" in b["honest_note"])
check("query no-match escalation to deep research",
      b["escalation"]["endpoint"] == "/v1/deep-research")

print()
if _failures:
    print(f"IKS-1 BATTERY FAILED: {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("IKS-1 BATTERY: all checks passed — sourced, bounded, honest.")
