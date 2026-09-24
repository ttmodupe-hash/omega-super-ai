"""INNOV-1 verification — Technology Radar catalogue integrity, deterministic
problem-solving, honest journal states, daily digest builder. Standalone:
catalogue from disk, digest feeds patched with fixtures — zero network."""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import core.tech_radar as radar
import core.news_pulse as news_pulse

app = FastAPI()
app.include_router(radar.router)
c = TestClient(app)

REQUIRED_FIELDS = {"id", "name", "category", "problem", "description",
                   "cost", "platforms", "link", "source"}


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        sys.exit(1)


# 1. Catalogue integrity
r = c.get("/v1/innovation/technologies")
check("technologies 200", r.status_code == 200)
body = r.json()
check("19 technologies", body["count"] == 19, f"got {body['count']}")
check("version + updated present", body["version"] == "1.0.0" and body["updated"] == "2026-09-24")
ids = [t["id"] for t in body["technologies"]]
check("ids unique", len(ids) == len(set(ids)))
for t in body["technologies"]:
    check(f"entry '{t['id']}' has all fields", REQUIRED_FIELDS <= set(t.keys()))
    check(f"entry '{t['id']}' links are https", t["link"].startswith("https://") and t["source"].startswith("https://"))
    check(f"entry '{t['id']}' cost stated honestly", len(t["cost"]) > 3)
check("11 categories", len(body["categories"]) == 11)

# 2. Category filter
r = c.get("/v1/innovation/technologies?category=payments")
check("category filter 200", r.status_code == 200)
check("payments has 3 entries", r.json()["count"] == 3, f"got {r.json()['count']}")
check("all filtered are payments", all(t["category"] == "payments" for t in r.json()["technologies"]))
r = c.get("/v1/innovation/technologies?category=nonsense")
check("unknown category => empty, honest", r.json()["count"] == 0)

# 3. Deterministic problem solving
r = c.get("/v1/innovation/solve", params={"problem": "I have no data but I need to find work"})
check("solve 200", r.status_code == 200)
body = r.json()
check("SAYouth matched for no-data work problem",
      body["matches"] and body["matches"][0]["technology"]["id"] == "sayouth-mobi",
      str([m["technology"]["id"] for m in body["matches"][:3]]))
check("matches carry scores", all("score" in m for m in body["matches"]))

r = c.get("/v1/innovation/solve", params={"problem": "load shedding is killing my business"})
ids = [m["technology"]["id"] for m in r.json()["matches"]]
check("load shedding => EskomSePush", "esp-loadshedding" in ids, str(ids))

r = c.get("/v1/innovation/solve", params={"problem": "I cannot afford a lawyer"})
ids = [m["technology"]["id"] for m in r.json()["matches"]]
check("legal problem => Legal Aid SA", "legal-aid-sa" in ids, str(ids))

r = c.get("/v1/innovation/solve", params={"problem": "xyzzy quantum frobnicate"})
body = r.json()
check("nonsense problem => zero matches, honest message",
      body["count"] == 0 and "No catalogue technology" in body["message"])

# 4. Journal — honest when daemon disabled and empty
radar._journal.clear()
radar._daemon_started = False
r = c.get("/v1/innovation/journal")
check("journal 200", r.status_code == 200)
body = r.json()
check("daemon state honest (disabled)", "disabled" in body["daemon"])
check("empty journal says so", body["entries_available"] == 0 and body["entries"] == [])
check("storage labelled per-process", "per-process" in body["storage"])

# 5. Digest builder — feeds patched deterministically
def fake_gather(topic):
    return {
        "topic": topic, "generated_at": "2026-09-24T00:00:00Z", "cache_ttl_seconds": 600,
        "feeds_ok": ["Fixture Feed"], "feeds_failed": [],
        "count": 1,
        "items": [{"title": f"{topic} breakthrough", "url": f"https://ex.com/{topic}",
                   "source": "Fixture Feed", "published": "Wed, 24 Sep 2026 00:00:00 GMT",
                   "summary": "fixture"}],
        "honesty": "fixture",
    }

orig_gather = news_pulse._gather_topic
news_pulse._gather_topic = fake_gather
entry = radar.build_daily_digest()
check("digest built from feeds", entry is not None and entry["kind"] == "daily-research-digest")
check("digest has 3 topics", set(entry["topics"].keys()) == {"science", "technology", "health"})
check("digest entries cited", entry["topics"]["science"]["headlines"][0]["url"].startswith("https://"))
check("digest carries date + generated_at", entry["date"] == "2026-09-24" and entry["generated_at"].endswith("Z"))

radar._journal_append(entry)
r = c.get("/v1/innovation/journal")
check("journal serves appended digest", r.json()["entries_available"] == 1)
check("journal entry has note on human-gated upgrades", "human-gated" in r.json()["entries"][0]["note"])

# 6. All feeds dead => no digest, journal untouched (fail-closed)
def dead_gather(topic):
    return {"topic": topic, "generated_at": "x", "cache_ttl_seconds": 0, "feeds_ok": [],
            "feeds_failed": [{"source": "Dead", "error": "TimeoutError"}],
            "count": 0, "items": [], "honesty": "fixture"}

news_pulse._gather_topic = dead_gather
check("all-feeds-dead => digest None (never fabricated)", radar.build_daily_digest() is None)
check("journal unchanged after dead cycle", len(radar._journal) == 1)
news_pulse._gather_topic = orig_gather
radar._journal.clear()

# 7. Status endpoint
r = c.get("/v1/innovation/status")
check("status 200", r.status_code == 200)
body = r.json()
check("status counts 19 technologies", body["technologies"] == 19)
check("status names upgrade pipeline", "Railway" in body["upgrade_pipeline"])
check("status shows daemon state", isinstance(body["research_daemon"], str))

print("\nINNOV-1 verification: all checks passed.")
