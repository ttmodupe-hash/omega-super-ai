"""NEWS-1 verification — World Pulse endpoints: RSS+Atom parsing, per-topic TTL
cache, failure isolation, fail-closed 503, honesty fields. Standalone: all feed
fetches are patched with deterministic fixtures — zero network, zero LLM."""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import core.news_pulse as news_pulse

RSS_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Fixture News</title>
<item><title>Rand steadies as markets watch rates</title>
<link>https://example.com/a1</link>
<pubDate>Wed, 24 Sep 2026 08:00:00 GMT</pubDate>
<description>Markets summary one.</description></item>
<item><title>New clinic opens in Limpopo</title>
<link>https://example.com/a2</link>
<pubDate>Wed, 24 Sep 2026 07:30:00 GMT</pubDate>
<description>Health summary.</description></item>
<item><title>Third headline</title>
<link>https://example.com/a3</link>
<pubDate>Wed, 24 Sep 2026 07:00:00 GMT</pubDate>
<description>Third.</description></item>
</channel></rss>"""

ATOM_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom story one</title>
<link rel="alternate" href="https://example.org/b1"/>
<published>2026-09-24T06:00:00Z</published>
<summary>Atom summary.</summary></entry>
</feed>"""

app = FastAPI()
app.include_router(news_pulse.router)
c = TestClient(app)

fetch_calls = {"n": 0}


def fake_fetch(url: str) -> bytes:
    fetch_calls["n"] += 1
    if "fail" in url:
        raise TimeoutError("simulated feed timeout")
    if "atom" in url:
        return ATOM_FIXTURE
    return RSS_FIXTURE


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        sys.exit(1)


news_pulse._fetch_feed_bytes = fake_fetch
news_pulse._cache_clear()

# 1. Topics index
r = c.get("/v1/news/topics")
check("topics index 200", r.status_code == 200)
body = r.json()
for t in ("south-africa", "africa", "world", "business", "health", "science", "technology"):
    check(f"topic '{t}' present", t in body["topics"])
check("honesty note present", "never invents news" in body["honesty"])
check("registry lists real source names", "News24 Top Stories" in body["feeds_per_topic"]["south-africa"])

# 2. Headlines — RSS parsing
r = c.get("/v1/news/headlines?topic=south-africa")
check("headlines 200", r.status_code == 200)
body = r.json()
check("items returned", body["count"] > 0, f"count={body['count']}")
check("item has title/url/source/published",
      all(k in body["items"][0] for k in ("title", "url", "source", "published")))
check("publisher timestamp carried verbatim",
      body["items"][0]["published"] == "Wed, 24 Sep 2026 08:00:00 GMT")
check("generated_at present (freshness visible)", body["generated_at"].endswith("Z"))
check("feeds_ok reported", len(body["feeds_ok"]) >= 1)
check("dedup: no duplicate urls", len({i["url"] for i in body["items"]}) == len(body["items"]))

# 3. TTL cache — second call must NOT refetch
n_after_first = fetch_calls["n"]
r2 = c.get("/v1/news/headlines?topic=south-africa")
check("cached second call 200", r2.status_code == 200)
check("cache hit: zero new fetches", fetch_calls["n"] == n_after_first,
      f"before={n_after_first} after={fetch_calls['n']}")

# 4. Limit respected
r = c.get("/v1/news/headlines?topic=south-africa&limit=1")
check("limit=1 respected", r.json()["count"] == 1)

# 5. Atom parsing (patch registry to an atom feed)
orig = news_pulse.FEED_REGISTRY["world"]
news_pulse.FEED_REGISTRY["world"] = [{"source": "Atom Fixture", "url": "https://x/atom"}]
news_pulse._cache_clear()
r = c.get("/v1/news/headlines?topic=world")
check("atom feed parsed 200", r.status_code == 200)
check("atom item parsed", r.json()["items"][0]["title"] == "Atom story one")
news_pulse.FEED_REGISTRY["world"] = orig
news_pulse._cache_clear()

# 6. Failure isolation — one dead feed does not kill the topic
news_pulse.FEED_REGISTRY["business"] = [
    {"source": "Dead Feed", "url": "https://x/fail"},
    {"source": "Live Feed", "url": "https://x/rss"},
]
r = c.get("/v1/news/headlines?topic=business")
check("partial failure still 200", r.status_code == 200)
b = r.json()
check("failed feed honestly reported", b["feeds_failed"][0]["source"] == "Dead Feed",
      str(b["feeds_failed"]))
check("live feed still served", b["count"] > 0)
news_pulse.FEED_REGISTRY["business"] = [
    {"source": "BBC News Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"}]
news_pulse._cache_clear()

# 7. Fail-closed — ALL feeds dead => honest 503, never invented news
news_pulse.FEED_REGISTRY["science"] = [{"source": "Dead", "url": "https://x/fail"}]
r = c.get("/v1/news/headlines?topic=science")
check("all-feeds-dead => 503", r.status_code == 503)
check("503 is honest", "does not invent" in str(r.json()["detail"]))
news_pulse.FEED_REGISTRY["science"] = [
    {"source": "BBC News Science & Environment", "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"}]
news_pulse._cache_clear()

# 8. Unknown topic => 404 with available list
r = c.get("/v1/news/headlines?topic=gossip")
check("unknown topic 404", r.status_code == 404)
check("404 lists available topics", "world" in r.json()["detail"])

print("\nNEWS-1 verification: all checks passed.")
