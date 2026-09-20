"""Adaptive Learning Engine verification — user-contributed kernel, hardened.

BKT assertions use HAND-COMPUTED values (Corbett & Anderson):
p0=0.1, slip=0.15, guess=0.2, transit=0.1.
  correct #1: p_obs=0.085/0.265=0.3208 -> p_next=0.3887
  correct #2: p_obs=0.3304/0.4527=0.7299 -> p_next=0.7569
  correct #3: p_obs=0.6434/0.6920=0.9297 -> p_next=0.9367
  wrong @0.1: p_obs=0.015/(0.015+0.72)=0.0204 -> p_next=0.1184
"""
import sys, time
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.adaptive_learning as al
from core.adaptive_learning import (router, AdvancedAdaptiveEngine, LearnerProfile,
                                    KnowledgeNode, UIChannel, dispatch_nudge)

app = FastAPI()
app.include_router(router)
c = TestClient(app)

passed = []
def check(name, cond, extra=""):
    assert cond, f"FAIL: {name} {extra}"
    passed.append(name)
    print(f"[PASS] {name} {extra}")

def approx(a, b, tol=5e-4):
    return abs(a - b) <= tol

# ── 1. BKT math vs hand-computed values ──────────────────────────────────
p = LearnerProfile(user_id="t-math")
e = AdvancedAdaptiveEngine(p)
m1 = e.update_skill_mastery("solar", True)
check("BKT correct#1 = 0.3887", approx(m1, 0.3887), f"got {m1}")
m2 = e.update_skill_mastery("solar", True)
check("BKT correct#2 = 0.7569", approx(m2, 0.7569), f"got {m2}")
m3 = e.update_skill_mastery("solar", True)
check("BKT correct#3 = 0.9367", approx(m3, 0.9367), f"got {m3}")
p2 = LearnerProfile(user_id="t-math2")
e2 = AdvancedAdaptiveEngine(p2)
mw = e2.update_skill_mastery("solar", False)
check("BKT wrong@0.1 = 0.1184", approx(mw, 0.1184), f"got {mw}")
check("mastery bounded [0,1]", 0.0 <= m3 <= 1.0)

# ── 2. Division guard (degenerate params — review fix #2) ────────────────
p3 = LearnerProfile(user_id="t-guard")
node = KnowledgeNode(concept_id="x", mastery_probability=1.0, p_guess=0.0)
p3.knowledge_graph["x"] = node
e3 = AdvancedAdaptiveEngine(p3)
r = e3.update_skill_mastery("x", False)   # denom would be 0 without guard... slip=0.15 keeps it alive; test true zero:
node2 = KnowledgeNode(concept_id="y", mastery_probability=1.0, p_guess=0.0, p_slip=0.0)
p3.knowledge_graph["y"] = node2
r2 = e3.update_skill_mastery("y", False)  # denom = 1*0 + 0*1 = 0 -> guarded
check("division guard: no ZeroDivisionError, mastery preserved", r2 == 1.0, f"got {r2}")

# ── 3. Activity touch (review fix #4) ────────────────────────────────────
p4 = LearnerProfile(user_id="t-active")
p4.last_active_timestamp = time.time() - 99999
AdvancedAdaptiveEngine(p4).update_skill_mastery("z", True)
check("mastery update touches last_active", time.time() - p4.last_active_timestamp < 5)

# ── 4. Channel routing boundaries ────────────────────────────────────────
p5 = LearnerProfile(user_id="t-chan")
e5 = AdvancedAdaptiveEngine(p5)
for lat, expect in [(0, UIChannel.VISUAL_3D), (149.9, UIChannel.VISUAL_3D),
                    (150, UIChannel.HYBRID_WEB), (349.9, UIChannel.HYBRID_WEB),
                    (350, UIChannel.WHATSAPP_TEXT), (799.9, UIChannel.WHATSAPP_TEXT),
                    (800, UIChannel.SMS_LOW_BANDWIDTH), (5000, UIChannel.SMS_LOW_BANDWIDTH)]:
    got = e5.resolve_ui_channel(lat)
    assert got == expect, f"boundary {lat}: {got} != {expect}"
check("channel boundaries exact (8 cases)", True)
check("original example: 420ms -> whatsapp", AdvancedAdaptiveEngine(
    LearnerProfile(user_id="t-orig", network_latency_ms=420.0)).resolve_ui_channel() == UIChannel.WHATSAPP_TEXT)

# ── 5. ZPD bands ─────────────────────────────────────────────────────────
def zpd(mastery):
    prof = LearnerProfile(user_id="t-zpd")
    prof.knowledge_graph["k"] = KnowledgeNode(concept_id="k", mastery_probability=mastery)
    return AdvancedAdaptiveEngine(prof).calculate_desirable_difficulty_strategy("k")
check("ZPD low -> SCAFFOLD_DOWN", zpd(0.3)["action"] == "SCAFFOLD_DOWN" and zpd(0.3)["challenge_multiplier"] == 0.8)
check("ZPD mid -> MAINTAIN_FLOW", zpd(0.75)["action"] == "MAINTAIN_FLOW")
check("ZPD high -> CHALLENGE_UP", zpd(0.95)["action"] == "CHALLENGE_UP" and zpd(0.95)["challenge_multiplier"] == 1.4)
check("ZPD target difficulty clamped", zpd(0.05)["target_difficulty"] == 0.1 and zpd(0.99)["target_difficulty"] == 1.0)

# ── 6. Prompt payload contract ───────────────────────────────────────────
prof = LearnerProfile(user_id="t-prompt", network_latency_ms=100.0)
payload = AdvancedAdaptiveEngine(prof).generate_llm_prompt_payload("solar", "How do I wire an inverter?")
check("prompt: 3D channel -> json cards", payload["channel_constraints"]["format_as_json_cards"] is True)
check("prompt: culture context embedded", "Sub-Saharan" in payload["system_instruction"])
prof2 = LearnerProfile(user_id="t-prompt2", network_latency_ms=999.0)
payload2 = AdvancedAdaptiveEngine(prof2).generate_llm_prompt_payload("solar", "q")
check("prompt: SMS channel -> 160 chars", payload2["channel_constraints"]["max_characters"] == 160)
check("prompt: user query passed through", payload2["user_payload"] == "q")

# ── 7. Nudge crafting + honest dispatch (review fix #1) ──────────────────
eng = AdvancedAdaptiveEngine(LearnerProfile(user_id="t-nudge", network_latency_ms=500.0, streak_days=7))
msg = eng._craft_proactive_nudge(UIChannel.WHATSAPP_TEXT)
check("nudge: streak embedded for low-bandwidth", "7-day streak" in msg)
msg2 = eng._craft_proactive_nudge(UIChannel.VISUAL_3D)
check("nudge: level-up message for rich channel", "Level 8" in msg2)
import os
os.environ.pop("LUQI_NUDGE_WEBHOOK_URL", None)
res = dispatch_nudge(UIChannel.SMS_LOW_BANDWIDTH, "test", "t-nudge")
check("dispatch honest when no transport", res["dispatched"] is False and "no LUQI_NUDGE_WEBHOOK_URL" in res["reason"])

# ── 8. Endpoints ──────────────────────────────────────────────────────────
al._PROFILES.clear()
r = c.put("/v1/adaptive/profiles/usr_1", json={"culture_context": "Southern Africa", "network_latency_ms": 420})
check("profile upsert 200", r.status_code == 200 and r.json()["culture_context"] == "Southern Africa")
r = c.get("/v1/adaptive/channel/usr_1")
check("channel endpoint: 420 -> whatsapp", r.json()["channel"] == "whatsapp_text")
check("channel endpoint exposes thresholds", "thresholds_ms" in r.json())
r = c.post("/v1/adaptive/mastery", json={"user_id": "usr_1", "concept_id": "solar", "is_correct": True})
b = r.json()
check("mastery endpoint BKT value", approx(b["mastery_probability"], 0.3887), f"got {b['mastery_probability']}")
check("mastery endpoint returns zpd strategy", b["zpd_strategy"]["action"] == "SCAFFOLD_DOWN")
r = c.get("/v1/adaptive/strategy/usr_1/solar")
check("strategy endpoint mirrors mastery state", approx(r.json()["target_difficulty"], 0.3887 - 0.2, tol=5e-4))
r = c.get("/v1/adaptive/profiles/usr_1")
check("profile snapshot has knowledge graph", "solar" in r.json()["knowledge_graph"])
r = c.get("/v1/adaptive/profiles/usr_missing")
check("missing profile -> 404 (honest)", r.status_code == 404)
r = c.post("/v1/adaptive/prompt-payload", json={"user_id": "usr_1", "concept_id": "solar", "raw_query": "inverter wiring?"})
check("prompt-payload endpoint 200", r.status_code == 200 and "system_instruction" in r.json())
r = c.post("/v1/adaptive/mastery", json={"user_id": "usr_1", "concept_id": "", "is_correct": True})
check("empty concept -> 422", r.status_code == 422)

# ── 9. main.py wiring ─────────────────────────────────────────────────────
src = open(_REPO / "core/main.py").read()
check("main mounts adaptive router", "include_router(adaptive_router)" in src)
check("nudge daemon env-gated", 'os.getenv("LUQI_ADAPTIVE_NUDGES") == "1"' in src)
from core.main import app as main_app
paths = [getattr(r_, "path", "") for r_ in main_app.routes]
check("main app exposes /v1/adaptive", any(p.startswith("/v1/adaptive") for p in paths))

print(f"\nALL ADAPTIVE-LEARNING CHECKS PASSED ({len(passed)} assertions)")
