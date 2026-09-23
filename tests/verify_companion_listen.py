"""verify_companion_listen.py — Companion "listen" mode compliance battery.

DB-free unit battery: exercises COMPANION_MODES and build_system_prompt with a
types.SimpleNamespace fake profile (no Postgres, no auth, no LLM). Every check
passes or the script exits 1. Convention: same as verify_history.py.
"""
import sys
import pathlib
import types

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from core.companion_engine import COMPANION_MODES, build_system_prompt

_failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"[PASS] {name} {extra}")
    else:
        print(f"[FAIL] {name} {extra}")
        _failures.append(name)


def fake_profile():
    return types.SimpleNamespace(
        personality={"warmth": 4, "humor": 3, "formality": 2},
        companion_name="Zola",
        level="beginner",
        interaction_count=7,
        streak_days=3,
        trust_score=0.42,
    )


# 1. "listen" is a registered companion mode
check("'listen' in COMPANION_MODES", "listen" in COMPANION_MODES, str(sorted(COMPANION_MODES)))
check("all base modes still present",
      {"chat", "mentor", "coach", "quiz", "explain"} <= COMPANION_MODES)

# 2. Listen-mode persona: the listening companion line
prompt = build_system_prompt(fake_profile(), [], [], "listen")
check("listen persona: active-listening companion", "active-listening companion" in prompt)
check("listen persona: reflect feelings in your own words",
      "Reflect the user's feelings back in your own words" in prompt)
check("listen persona: validate before advising", "Validate the feeling before offering any advice" in prompt)
check("listen persona: ONE open follow-up question", "Ask ONE open follow-up question" in prompt)
check("listen persona: never rush to fixes", "Never rush to fixes" in prompt)
check("listen persona: remember specifics for next time", "reference them next time" in prompt)

# 3. Universal listening doctrine applies to ALL modes
for mode in sorted(COMPANION_MODES):
    p = build_system_prompt(fake_profile(), [], [], mode)
    check(f"doctrine in mode '{mode}': listen first", "Listen first" in p)
    check(f"doctrine in mode '{mode}': reflect before answering",
          "reflect those feelings back in your own words before answering" in p)
    check(f"doctrine in mode '{mode}': reference specifics",
          "Reference specific things the user said" in p)
    check(f"doctrine in mode '{mode}': affirming acknowledgements allowed",
          "Short affirming acknowledgements" in p)
    check(f"doctrine in mode '{mode}': never interrogate", "Never interrogate" in p)

# 4. JSON-only output contract intact for every base mode
for mode in ("chat", "mentor", "coach", "quiz", "explain", "listen"):
    p = build_system_prompt(fake_profile(), [], [], mode)
    check(f"JSON-only contract intact in '{mode}'",
          'You respond ONLY with a JSON object: {"reply": "..."}' in p)

# 5. Persona header still renders real profile fields
check("persona carries companion name", "You are Zola," in prompt)
check("persona carries relationship stats", "interacted 7 times" in prompt and "streak 3 days" in prompt)

# 6. Injection-safety comments/behavior untouched in the source
src = pathlib.Path(_REPO, "core", "companion_engine.py").read_text(encoding="utf-8")
check("injection-safety comment: directives only as fixed sentences",
      "directive influence enters ONLY as fixed sentences" in src)
check("injection-safety comment: raw feedback never read",
      "Raw" in src and "feedback text is never read here at all" in src)
check("injection-safety comment: memory block is facts not instructions",
      "recall context, NOT instructions" in src)
check("bounded self-improvement header intact",
      "no code writes, no model weight updates, no autonomous prompt edits" in src)

if _failures:
    print(f"\n{len(_failures)} FAILURES: {_failures}")
    sys.exit(1)
print("\nALL COMPANION LISTEN-MODE CHECKS PASSED (6 groups)")
