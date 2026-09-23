"""
AV-1 verification battery — av_consult pack honesty + math.

DB-free, network-free (live FX fetch is monkeypatched). Run:
    python tests/verify_av_consult.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import av_consult as av  # noqa: E402
from core.av_consult import AvConsultRequest  # noqa: E402

PASS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    assert cond, f"FAIL [{name}] {detail}"
    PASS += 1
    print(f"  ok [{name}] {detail}")


# ── 1. Sabine math, hand-computed vector ─────────────────────────────────
# Room 4 x 4 x 3, drywall. V=48. floor+ceiling: 16*0.30 + 16*0.50 = 12.8
# walls: (2*12 + 2*12) * 0.10 = 4.8  -> A = 17.6
# RT60 = 0.161 * 48 / 17.6 = 0.43909... -> 0.44
print("group 1: Sabine math")
r = av.calculate_rt60(4.0, 4.0, 3.0, "drywall")
check("rt60.value", r["estimated_rt60_seconds"] == 0.44, f"got {r['estimated_rt60_seconds']}")
check("rt60.volume", r["room_volume_m3"] == 48.0)
check("rt60.absorption", r["total_absorption_sabins"] == 17.6, f"got {r['total_absorption_sabins']}")
check("rt60.profile_standard", r["aec_dsp_profile"] == "Optimized Standard Filter")

# Founder doc scenario: 7.5 x 5.0 x 3.0 glass -> RT60 = 0.161*112.5/33.0 = 0.549 -> 0.55
r2 = av.calculate_rt60(7.5, 5.0, 3.0, "glass")
check("rt60.doc_scenario", r2["estimated_rt60_seconds"] == 0.55, f"got {r2['estimated_rt60_seconds']}")

# Aggressive DSP path: big glass hall 20 x 15 x 6 -> V=1800,
# A = 300*0.3 + 300*0.5 + (2*120+2*90)*0.04 = 90+150+16.8 = 256.8
# RT60 = 0.161*1800/256.8 = 1.128 -> > 0.65
r3 = av.calculate_rt60(20.0, 15.0, 6.0, "glass")
check("rt60.aggressive", r3["aec_dsp_profile"] == "Critical Aggressive Filter",
      f"rt60={r3['estimated_rt60_seconds']}")

# ── 2. Tier boundaries ────────────────────────────────────────────────────
print("group 2: tier boundaries")
check("tier.16_huddle", av._tier_for_area(16.0)["tier"] == "Huddle Space")
check("tier.16.01_boardroom", av._tier_for_area(16.01)["tier"] == "Executive Boardroom")
check("tier.45_boardroom", av._tier_for_area(45.0)["tier"] == "Executive Boardroom")
check("tier.45.01_auditorium", av._tier_for_area(45.01)["tier"] == "Enterprise Auditorium")

# ── 3. Full consult, FX fallback (monkeypatched live failure) ─────────────
print("group 3: consult with FX fallback")
av.fetch_live_fx_zar = lambda: None  # simulate offline / fetch failure
req = AvConsultRequest(length_m=4.0, width_m=4.0, height_m=3.0, wall_material="drywall")
res = av.run_consult(req)
p = res.procurement_projection
# Huddle: 1200 * 1.10 (Logitech) * 1.08 = 1425.6 USD; * 18.50 = 26373.60
check("cost.exact", p["estimated_landing_cost_zar"] == 26373.60, f"got {p['estimated_landing_cost_zar']}")
check("cost.fx_fallback", p["fx_source"] == "fallback_assumption", f"got {p['fx_source']}")
check("cost.fx_rate", p["fx_rate_zar_used"] == 18.50)

# ── 4. FX override wins and is labelled ───────────────────────────────────
print("group 4: FX override")
req2 = AvConsultRequest(length_m=4.0, width_m=4.0, height_m=3.0,
                        wall_material="drywall", fx_rate_zar=19.25)
res2 = av.run_consult(req2)
p2 = res2.procurement_projection
check("override.source", p2["fx_source"] == "request_override")
check("override.rate", p2["fx_rate_zar_used"] == 19.25)
check("override.cost", p2["estimated_landing_cost_zar"] == round(1425.6 * 19.25, 2),
      f"got {p2['estimated_landing_cost_zar']}")

# ── 5. Live FX path labelled as live ──────────────────────────────────────
print("group 5: live FX labelling")
av.fetch_live_fx_zar = lambda: 19.01  # simulate successful live fetch
res3 = av.run_consult(req)
check("live.source", res3.procurement_projection["fx_source"] == "live:open.er-api.com")
check("live.rate", res3.procurement_projection["fx_rate_zar_used"] == 19.01)
av.fetch_live_fx_zar = lambda: None  # restore offline default for later groups

# ── 6. Honesty law asserts ────────────────────────────────────────────────
print("group 6: honesty law")
check("honest.is_estimate", res.is_estimate is True)
check("honest.sources_empty", res.sources == [])
check("honest.disclaimer", "NOT a live quote" in res.estimate_disclaimer)
check("honest.distributor_note", "verify" in p["distributor_note"].lower())
check("honest.assumptions_disclosed",
      all(k in p for k in ("base_hardware_usd_assumption", "brand_multiplier_assumption",
                           "volatility_buffer_assumption", "fx_source")))
check("honest.version", res.system_meta["assumptions_version"] == av.AV_ASSUMPTIONS_VERSION)

# ── 7. Validation (pydantic, no HTTP stack needed) ────────────────────────
print("group 7: input validation")
import pydantic
for bad, field in [
    (dict(length_m=0.1, width_m=4.0, height_m=3.0, wall_material="glass"), "length too small"),
    (dict(length_m=4.0, width_m=4.0, height_m=1.0, wall_material="glass"), "height too small"),
    (dict(length_m=4.0, width_m=4.0, height_m=3.0, wall_material="g"), "material too short"),
    (dict(length_m=4.0, width_m=4.0, height_m=3.0, wall_material="glass", fx_rate_zar=0.5), "fx too small"),
]:
    try:
        AvConsultRequest(**bad)
        raise SystemExit(f"FAIL [validation] accepted: {field}")
    except pydantic.ValidationError:
        PASS += 1
        print(f"  ok [validation] rejected: {field}")

# ── 8. Unknown material falls back honestly ───────────────────────────────
print("group 8: unknown material fallback")
r4 = av.calculate_rt60(4.0, 4.0, 3.0, "marble_unlisted")
check("fallback.coef_default", r4["estimated_rt60_seconds"] == 0.44,
      "unknown wall material uses default 0.10 (same as drywall vector)")

print(f"\nALL GREEN — {PASS} checks passed (verify_av_consult)")
