"""verify_history.py — African History Archive (ARCHIVE-1) compliance battery.

Runs against the REAL app router (TestClient). Every check passes or the
script exits 1. Convention: same as verify_finlit.py.
"""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
from fastapi.testclient import TestClient

from core.african_history import router
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
r = c.get("/v1/history")
check("overview 200", r.status_code == 200)
b = r.json()
check("overview version 1.0.0", b["version"] == "1.0.0", f"v={b.get('version')}")
check("overview counts 26", b["entry_count"] == 26, f"got {b.get('entry_count')}")
check("overview has categories + regions", len(b["categories"]) >= 6 and len(b["regions"]) >= 6)
check("overview carries honesty disclaimer", "sources" in b["disclaimer"].lower())

# 2. Entries list + field integrity
r = c.get("/v1/history/entries")
check("entries 200", r.status_code == 200)
b = r.json()
check("26 entries listed", b["count"] == 26, f"got {b['count']}")
REQUIRED = ("id", "title", "category", "region", "start_year", "period", "summary")
check("every summary has all fields", all(all(k in e for k in REQUIRED) for e in b["entries"]))
check("every summary >= 400 chars (depth floor)", all(len(e["summary"]) >= 400 for e in b["entries"]))

# 3. Detail + anti-hallucination law (sources)
r = c.get("/v1/history/entries/adwa")
check("adwa detail 200", r.status_code == 200)
b = r.json()
check("adwa has >= 2 sources", len(b["sources"]) >= 2, str(b["sources"]))
check("adwa mentions Menelik", "Menelik" in b["summary"])
check("adwa has significance", len(b["significance"]) >= 60)
r = c.get("/v1/history/entries/great-zimbabwe")
check("great-zimbabwe has UNESCO source", any("UNESCO" in s for s in r.json()["sources"]))
r = c.get("/v1/history/entries/no-such-entry")
check("unknown entry honest 404", r.status_code == 404)
check("404 detail points to the index", "/v1/history/entries" in r.json()["detail"])

# 4. EVERY entry carries >= 2 verifiable references (law, archive-wide)
r = c.get("/v1/history/timeline").json()
check("all 26 entries in timeline", r["count"] == 26)
full = {e["id"]: c.get(f"/v1/history/entries/{e['id']}").json() for e in r["entries"]}
check("every entry has >= 2 sources", all(len(v["sources"]) >= 2 for v in full.values()))
check("every source string is substantive", all(all(len(s) >= 15 for s in v["sources"]) for v in full.values()))

# 5. Timeline order — Kush (BCE) first, 1994 last
years = [e["start_year"] for e in r["entries"]]
check("timeline sorted ascending", years == sorted(years), str(years[:3]) + "..." + str(years[-2:]))
check("BCE handled: Kush first, negative year", r["entries"][0]["id"] == "kush-meroe" and years[0] < 0)
check("timeline ends at 1994", r["entries"][-1]["id"] == "mandela-release")

# 6. Filters
r = c.get("/v1/history/entries", params={"category": "liberation"})
ids = [e["id"] for e in r.json()["entries"]]
check("category filter liberation", {"sharpeville", "soweto-uprising", "ghana-independence"} <= set(ids), str(ids))
r = c.get("/v1/history/entries", params={"region": "Southern Africa"})
ids = [e["id"] for e in r.json()["entries"]]
check("region filter Southern Africa", {"great-zimbabwe", "mapungubwe", "isandlwana", "robben-island"} <= set(ids), str(ids))
r = c.get("/v1/history/entries", params={"q": "gold"})
check("search q=gold finds gold narratives", r.json()["count"] >= 3, f"got {r.json()['count']}")
r = c.get("/v1/history/entries", params={"q": "Nzima"})
check("search hits inside summaries (Nzima photo)", any(e["id"] == "soweto-uprising" for e in r.json()["entries"]))

# 7. Debate honesty — contested history is labelled as debate
mg = full["mfecane"]
check("mfecane presented as debate", "debate" in (mg["title"] + mg["summary"]).lower())
go = full["goree"]
check("goree carries historian caution", "caution" in go["summary"].lower() or "debate" in go["summary"].lower())

# 8. Mounted on the real app
import core.main as main_app  # noqa: E402
paths = [r_.path for r_ in main_app.app.routes]
check("main.py mounts /v1/history", any(p.startswith("/v1/history") for p in paths),
      str([p for p in paths if "history" in p]))

if _failures:
    print(f"\n{len(_failures)} FAILURES: {_failures}")
    sys.exit(1)
print("\nALL AFRICAN HISTORY ARCHIVE CHECKS PASSED (8 groups)")
