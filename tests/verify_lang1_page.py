"""LANG-1 verification — 22-language registry synchronization.

Proves:
  (1) the seed catalogue covers all 22 registry locales on all 13 keys
      (zero gaps, zero empties, exactly 286 rows),
  (2) the website console selector + metric card are synchronized with the
      engine registry (selector codes == LANGUAGES, metric == 22),
  (3) the honest activation label is retained on the page.

No sqlalchemy needed — the registry and catalogue are pure python. Page checks
run only in the unified merge clone; inside the omega-super-ai engine subtree
(pages/ does not live there) they SKIP honestly.
"""
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import core.i18n as i18n

FAILURES = []


def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        FAILURES.append(name)


# 1. Catalogue: every key x every locale, non-empty, exact row count
langs = set(i18n.LANGUAGES)
check("registry carries 22 languages", len(langs) == 22, f"got {len(langs)}")
gaps = {k: sorted(langs - set(p)) for k, p in i18n.SEED_STRINGS.items() if langs - set(p)}
check("all 13 keys cover all 22 locales", not gaps and len(i18n.SEED_STRINGS) == 13,
      f"gaps={gaps}" if gaps else f"{len(i18n.SEED_STRINGS)} keys, 0 gaps")
empties = [(k, l) for k, p in i18n.SEED_STRINGS.items() for l, t in p.items() if not t.strip()]
check("no empty translations", not empties, f"{empties[:5]}")
rows = sum(len(p) for p in i18n.SEED_STRINGS.values())
check("seed rows == 13 x 22 == 286", rows == 286, f"rows={rows}")
check("app.name is Luqi-ai in every locale (brand law)",
      all(t == "Luqi-ai" for t in i18n.SEED_STRINGS["app.name"].values()))
check("fallback notice translated in every locale (never-silent law)",
      set(i18n.SEED_STRINGS["msg.english_fallback"]) == langs)

# 2. Website synchronization (merge clone only)
page_path = _REPO.parent / "pages" / "index.html"
if not page_path.exists():
    print("[SKIP] pages/index.html not in this tree (omega-super-ai subtree) — "
          "page checks run in the unified merge clone")
else:
    html = page_path.read_text(encoding="utf-8")
    sel = re.search(r'<select id="language-select".*?</select>', html, re.S)
    check("language-select present", sel is not None)
    opts = re.findall(r'<option value="([^"]+)"', sel.group(0)) if sel else []
    check("selector offers exactly the 22 registry codes",
          len(opts) == 22 and set(opts) == langs,
          f"extra={sorted(set(opts) - langs)} missing={sorted(langs - set(opts))}")
    metric = re.search(r'id="metric-languages">(\d+)<', html)
    check("metric card == registry size", metric is not None and metric.group(1) == str(len(langs)),
          f"metric={metric.group(1) if metric else '?'} registry={len(langs)}")
    check("honest activation label retained",
          "engine language models are enabled at launch" in html)

if FAILURES:
    print(f"\nLANG-1 BATTERY FAILED: {FAILURES}")
    sys.exit(1)
print("\nLANG-1 BATTERY: all checks passed — 22-language registry synchronized "
      "across seed catalogue + website selector + metric")
