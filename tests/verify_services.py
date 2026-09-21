"""Everyday Services Pack verification battery.

8 groups, mirroring verify_history.py:
1. overview contract (name, version, counts, categories, agencies, disclaimer)
2. entries list — 15 entries, summary floor, summary fields only
3. entry detail — steps/channels/warning/sources present, honest 404
4. pack-wide integrity — every entry >=2 sources, source strings >=15 chars,
   unique ids, valid category/agency
5. freshness law — every summary carries a verification date ("Verified 20")
6. scam-first law — every entry carries a non-empty scam warning
7. filters — category/agency/q behave; q digs inside steps
8. main.py mounts /v1/services

Run: PYTHONPATH=. python3 tests/verify_services.py
"""
import pathlib
import sys

from fastapi.testclient import TestClient

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from core.everyday_services import router  # noqa: E402
from fastapi import FastAPI  # noqa: E402

app = FastAPI()
app.include_router(router)
c = TestClient(app)

PASS = 0


def ok(cond, label, extra=""):
    global PASS
    assert cond, f"FAIL: {label} {extra}"
    PASS += 1
    print(f"[PASS] {label} {extra}")


# ── group 1: overview contract ──────────────────────────────
r = c.get("/v1/services")
ok(r.status_code == 200, "overview 200")
ov = r.json()
ok(ov["name"] == "LUQI Everyday Services Pack", "overview name")
ok(ov["version"] == "1.0.0", "overview version", ov["version"])
ok(ov["entry_count"] == 15, "overview count 15", str(ov["entry_count"]))
ok(set(ov["categories"]) == {"grants", "tax", "unemployment", "education funding", "scam safety"},
   "overview categories")
ok(len(ov["agencies"]) == 7, "overview agencies 7")
ok("not legal or" in ov["disclaimer"] and "financial advice" in ov["disclaimer"],
   "disclaimer honesty")

# ── group 2: entries list ───────────────────────────────────
r = c.get("/v1/services/entries")
d = r.json()
ok(d["count"] == 15 and len(d["entries"]) == 15, "15 entries listed")
for e in d["entries"]:
    ok(len(e["summary"]) >= 400, f"summary floor 400 ({e['id']})", str(len(e["summary"])))
    ok(set(e.keys()) == {"id", "title", "category", "agency", "summary"},
       f"summary fields only ({e['id']})")

# ── group 3: detail + honest 404 ────────────────────────────
r = c.get("/v1/services/entries/srd-grant-apply")
ok(r.status_code == 200, "detail 200")
det = r.json()
for k in ("steps", "official_channels", "warning", "sources", "significance" if False else "title"):
    ok(k in det, f"detail has {k}")
ok(len(det["steps"]) >= 3, "detail steps >=3")
ok(len(det["official_channels"]) >= 2, "detail channels >=2")
r = c.get("/v1/services/entries/free-money")
ok(r.status_code == 404 and "/v1/services/entries" in r.json()["detail"], "honest 404")

# ── group 4: pack-wide integrity ────────────────────────────
all_entries = [c.get(f"/v1/services/entries/{e['id']}").json() for e in d["entries"]]
ids = set()
for e in all_entries:
    ok(e["id"] not in ids, f"unique id ({e['id']})")
    ids.add(e["id"])
    ok(len(e["sources"]) >= 2, f">=2 sources ({e['id']})")
    for s in e["sources"]:
        ok(len(s) >= 15, f"source string >=15 chars ({e['id']})")
    ok(e["category"] in ov["categories"], f"valid category ({e['id']})")
    ok(e["agency"] in ov["agencies"], f"valid agency ({e['id']})")

# ── group 5: freshness law ──────────────────────────────────
for e in all_entries:
    ok("Verified 20" in e["summary"], f"verification date in summary ({e['id']})")

# ── group 6: scam-first law ─────────────────────────────────
for e in all_entries:
    ok(isinstance(e.get("warning"), str) and len(e["warning"]) >= 80,
       f"scam warning present ({e['id']})")

# ── group 7: filters ────────────────────────────────────────
r = c.get("/v1/services/entries", params={"category": "grants"})
ok(r.json()["count"] == 9, "category filter grants=9", str(r.json()["count"]))
r = c.get("/v1/services/entries", params={"agency": "SARS"})
ok(r.json()["count"] == 2, "agency filter SARS=2", str(r.json()["count"]))
r = c.get("/v1/services/entries", params={"q": "appeal"})
ok(r.json()["count"] >= 2, "q=appeal hits >=2", str(r.json()["count"]))
r = c.get("/v1/services/entries", params={"q": "myNSFAS"})
ok(r.json()["count"] >= 1 and any(e["id"] == "nsfas-2027" for e in r.json()["entries"]),
   "q=myNSFAS finds nsfas-2027 (steps searchable)")
r = c.get("/v1/services/entries", params={"q": "zzzz-not-a-service"})
ok(r.json()["count"] == 0, "q no-match returns 0 honestly")

# ── group 8: main.py mounts ─────────────────────────────────
import core.main as main_app  # noqa: E402

paths = {route.path for route in main_app.app.routes}
ok("/v1/services" in paths, "main.py mounts /v1/services")
ok("/v1/services/entries" in paths, "main.py mounts /v1/services/entries")
ok("/v1/services/entries/{entry_id}" in paths, "main.py mounts detail route",
   str(sorted(p for p in paths if p.startswith("/v1/services"))))

print(f"\nALL EVERYDAY SERVICES PACK CHECKS PASSED ({PASS} checks, 8 groups)")
