"""API-CATALOG-1 verification — curated free-API resource catalogue.

Proves the honesty contract: catalogue loads, schema complete, verification
labels truthful, mission law enforced (no betting/gambling content), and the
router is mounted in main.py (static check — sqlalchemy absent in sandbox).
"""
import json
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from core.resources import load_catalogue, router

FAILURES = []


def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        FAILURES.append(name)


cat = load_catalogue()

# 1. Catalogue structure
check("catalogue versioned", bool(cat.get("catalogue_version")), cat.get("catalogue_version"))
check("honesty notes present", len(cat.get("honesty_notes", [])) >= 3)
check("CoinMarketCap correction recorded",
      any("CoinMarketCap" in n for n in cat["honesty_notes"]))

# 2. Entry schema + verification labels
REQUIRED = {"name", "url_example", "category", "mission_pillar", "auth",
            "sandbox_verified", "verified_on", "note"}
all_entries = cat["verified_no_key"] + cat["free_key_tier"]
check("all entries carry full schema", all(REQUIRED <= set(e) for e in all_entries))
check("verified_no_key entries all truly verified",
      all(e["sandbox_verified"] is True and e["verified_on"] == cat["built"]
          for e in cat["verified_no_key"]))
check("free_key_tier honestly unverified (need registration key)",
      all(e["sandbox_verified"] is False and e["verified_on"] is None
          for e in cat["free_key_tier"]))
check("auth labels restricted to none | free-key",
      all(e["auth"] in ("none", "free-key") for e in all_entries))
check("6 verified no-key + 2 free-key entries",
      len(cat["verified_no_key"]) == 6 and len(cat["free_key_tier"]) == 2,
      f"{len(cat['verified_no_key'])}+{len(cat['free_key_tier'])}")

# 3. Mission law — no betting/gambling/odds content served
BANNED = re.compile(r"betting|gambling|odds|poker|casino", re.I)
served_text = json.dumps(cat["verified_no_key"] + cat["free_key_tier"])
check("no betting/gambling content in served entries", not BANNED.search(served_text))
check("rejections documented with reasons",
      all(e.get("reason") for e in cat["rejected_from_source"]))

# 4. URL hygiene — https everywhere except the documented Hipolabs http case
urls = [e["url_example"] for e in all_entries]
check("all URLs https (or documented http exception)",
      all(u.startswith("https://") or "universities.hipolabs.com" in u for u in urls))

# 5. Router shape + main.py mount (static — CI is the runtime gate)
routes = [r.path for r in router.routes]
check("router serves /v1/resources/free-apis", "/v1/resources/free-apis" in routes, str(routes))
main_src = (_REPO / "core" / "main.py").read_text(encoding="utf-8")
check("main.py imports resources_router", "from .resources import router as resources_router" in main_src)
check("main.py mounts resources_router", "app.include_router(resources_router)" in main_src)

if FAILURES:
    print(f"\nAPI-CATALOG-1 BATTERY FAILED: {FAILURES}")
    sys.exit(1)
print("\nAPI-CATALOG-1 BATTERY: all checks passed — catalogue honest, verified, mission-aligned")
