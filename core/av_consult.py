"""
AV Consultancy skill — AV-1 (luqi-ai)

Deterministic AV room consultancy: Sabine RT60 acoustics + honest South
African procurement estimation.

- POST /v1/av/consult  — room dimensions + materials -> acoustics payload,
                         cabling blueprint, tier, and a ZAR cost ESTIMATE
- GET  /v1/av/consult  — documents the honesty law of this endpoint

Origin: founder design doc (2026-09-23). The doc's physics (Sabine formula)
and tier/cable logic were sound and are kept; its pricing layer was NOT —
it presented a hardcoded exchange rate and invented multipliers as a "live
market sync". That violates house law, so it was rebuilt:

Design rules (house law):
- Deterministic calculation only — no LLM call, works fully offline, no DB.
- Every cost figure is an ESTIMATE. `is_estimate` is always true and the
  response always carries `estimate_disclaimer`. No exceptions.
- The exchange rate is resolved in a strict, LABELLED order:
    1. `fx_rate_zar` supplied in the request  -> fx_source = "request_override"
    2. Live fetch from open.er-api.com (4s timeout, stdlib urllib, no key)
                                             -> fx_source = "live:open.er-api.com"
    3. Env LUQI_AV_FX_FALLBACK_ZAR (default 18.50)
                                             -> fx_source = "fallback_assumption"
  The caller can always see exactly which rate was used and where it came
  from. We never label a fallback as live.
- Assumption constants (volatility buffer, brand multipliers, hardware
  baselines) are versioned ASSUMPTIONS below — bump AV_ASSUMPTIONS_VERSION
  when they change. They are starting-point heuristics, not market data.
- Supplier names are carried from the founder's doc as EXAMPLES ONLY.
  `sources` stays empty: we claim no live market data and no verified
  authorisation status.
"""
import json
import os
import urllib.request
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/av", tags=["av-consultancy"])

AV_ASSUMPTIONS_VERSION = "1.0.0"

ESTIMATE_DISCLAIMER = (
    "Estimate only — NOT a live quote and NOT procurement advice. "
    "Confirm current pricing and stock with the distributor before budgeting."
)

# --- Acoustic assumptions (absorption coefficients at ~1 kHz, speech band) ---
ABSORPTION_COEFFICIENTS: Dict[str, float] = {
    "glass": 0.04,
    "concrete": 0.02,
    "drywall": 0.10,
    "acoustic_paneling": 0.85,
    "carpet": 0.30,
    "acoustic_tile": 0.50,
}
_DEFAULT_WALL_COEF = 0.10
_FLOOR_DEFAULT = "carpet"          # 0.30
_CEILING_DEFAULT = "acoustic_tile"  # 0.50

# Speech-room heuristic bands for RT60 (seconds)
_RT60_AGGRESSIVE_DSP = 0.65

# --- Tier assumptions (area in m² -> hardware baseline, ecosystem, cabling) ---
_TIERS = [
    {
        "max_area": 16.0,
        "tier": "Huddle Space",
        "base_hardware_usd": 1200.00,
        "primary_brand": "Logitech",
        "cable_spec": "Active USB-C with Alt-Mode DisplayPort (no external receivers needed).",
        "cable_why": (
            "Short runs (<3 m) do not suffer structural signal attenuation; "
            "latency stays at 0 ms organically."
        ),
    },
    {
        "max_area": 45.0,
        "tier": "Executive Boardroom",
        "base_hardware_usd": 6500.00,
        "primary_brand": "Extron",
        "cable_spec": "Category 6A F/UTP (foiled/unshielded twisted pair) running HDBaseT.",
        "cable_why": (
            "Shielding defends video streams against high-voltage EMI lines "
            "commonly routed through ceilings."
        ),
    },
    {
        "max_area": None,  # unbounded
        "tier": "Enterprise Auditorium",
        "base_hardware_usd": 24000.00,
        "primary_brand": "Crestron",
        "cable_spec": "OM3 multi-mode fibre terminated LC directly into core transceivers.",
        "cable_why": (
            "Fibre delivers electrical decoupling and no practical distance "
            "attenuation at these runs."
        ),
    },
]

# --- Procurement assumptions (heuristics, NOT market data) ---
VOLATILITY_BUFFER = float(os.environ.get("LUQI_AV_VOLATILITY_BUFFER", "1.08"))
BRAND_PRICE_MULTIPLIERS: Dict[str, float] = {
    "Crestron": 1.45,
    "Extron": 1.35,
    "Shure": 1.25,
    "Logitech": 1.10,
    "Kramer": 1.15,
}
_DEFAULT_BRAND_MULTIPLIER = 1.15
_FX_FALLBACK = float(os.environ.get("LUQI_AV_FX_FALLBACK_ZAR", "18.50"))
_FX_LIVE_URL = "https://open.er-api.com/v6/latest/USD"
_FX_TIMEOUT_S = 4

# Names carried from the founder's design doc — examples, not endorsements.
_EXAMPLE_SA_DISTRIBUTORS = ["Electrosonic SA", "Peripheral Vision", "StageOne"]
_DISTRIBUTOR_NOTE = (
    "Example SA distributors only — verify current authorisation status "
    "directly with the manufacturer before ordering."
)


def fetch_live_fx_zar() -> Optional[float]:
    """Try a real live USD->ZAR fetch. Returns None on any failure.

    Stdlib urllib only — no new dependency, no API key, hard timeout.
    A None return is honest: callers must fall back and LABEL the fallback.
    """
    try:
        with urllib.request.urlopen(_FX_LIVE_URL, timeout=_FX_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rate = data.get("rates", {}).get("ZAR")
        return float(rate) if rate else None
    except Exception:
        return None


def calculate_rt60(length: float, width: float, height: float,
                   wall_material: str,
                   floor_material: str = _FLOOR_DEFAULT,
                   ceiling_material: str = _CEILING_DEFAULT) -> Dict[str, Any]:
    """Sabine's formula: RT60 = 0.161 * V / A  (V in m³, A in metric sabins)."""
    volume = length * width * height
    floor_area = length * width
    walls_area = 2 * (length * height) + 2 * (width * height)

    wall_coef = ABSORPTION_COEFFICIENTS.get(wall_material.lower(), _DEFAULT_WALL_COEF)
    floor_coef = ABSORPTION_COEFFICIENTS.get(floor_material.lower(), ABSORPTION_COEFFICIENTS[_FLOOR_DEFAULT])
    ceil_coef = ABSORPTION_COEFFICIENTS.get(ceiling_material.lower(), ABSORPTION_COEFFICIENTS[_CEILING_DEFAULT])

    total_absorption = (floor_area * floor_coef) + (floor_area * ceil_coef) + (walls_area * wall_coef)
    rt60 = (0.161 * volume) / max(total_absorption, 0.1)  # zero-division guard

    if rt60 > _RT60_AGGRESSIVE_DSP:
        aec_profile = "Critical Aggressive Filter"
        notes = (
            f"High reverberation detected ({rt60:.2f}s). Specify active DSP with "
            "tail-length cancellation >250 ms and consider adding absorptive surfaces."
        )
    else:
        aec_profile = "Optimized Standard Filter"
        notes = (
            f"Favourable room acoustics ({rt60:.2f}s). Standard hardware-based AEC "
            "via USB/Dante endpoint is sufficient."
        )

    return {
        "room_volume_m3": round(volume, 2),
        "total_absorption_sabins": round(total_absorption, 2),
        "estimated_rt60_seconds": round(rt60, 2),
        "aec_dsp_profile": aec_profile,
        "acoustic_remediation_notes": notes,
        "method": "Sabine: RT60 = 0.161 * V / A (coefficients at ~1 kHz)",
    }


def _tier_for_area(area: float) -> Dict[str, Any]:
    for t in _TIERS:
        if t["max_area"] is None or area <= t["max_area"]:
            return t
    return _TIERS[-1]  # unreachable, kept for type safety


def _resolve_fx(override: Optional[float]) -> (tuple):
    """Strict labelled resolution: override > live > fallback."""
    if override is not None:
        return override, "request_override"
    live = fetch_live_fx_zar()
    if live is not None:
        return live, "live:open.er-api.com"
    return _FX_FALLBACK, "fallback_assumption"


class AvConsultRequest(BaseModel):
    length_m: float = Field(..., gt=0.5, le=100.0, description="Room length in metres")
    width_m: float = Field(..., gt=0.5, le=100.0, description="Room width in metres")
    height_m: float = Field(..., gt=2.0, le=20.0, description="Room height in metres")
    wall_material: str = Field(..., min_length=2, max_length=40,
                               description="e.g. glass, concrete, drywall, acoustic_paneling")
    floor_material: Optional[str] = Field(None, max_length=40)
    ceiling_material: Optional[str] = Field(None, max_length=40)
    applied_standard: str = Field("Standard", max_length=80)
    fx_rate_zar: Optional[float] = Field(None, gt=1.0, le=100.0,
                                         description="Optional USD->ZAR override; wins over live fetch")


class AvConsultResponse(BaseModel):
    system_meta: Dict[str, Any]
    spatial_metrics: Dict[str, Any]
    cabling_infrastructure: Dict[str, Any]
    procurement_projection: Dict[str, Any]
    sources: List[str]            # always empty — no live market data claimed
    is_estimate: bool             # always true
    estimate_disclaimer: str


def run_consult(req: AvConsultRequest) -> AvConsultResponse:
    """Pure consult logic, separated from the route for direct testing."""
    area = req.length_m * req.width_m
    tier = _tier_for_area(area)

    acoustics = calculate_rt60(
        req.length_m, req.width_m, req.height_m, req.wall_material,
        req.floor_material or _FLOOR_DEFAULT,
        req.ceiling_material or _CEILING_DEFAULT,
    )

    fx_rate, fx_source = _resolve_fx(req.fx_rate_zar)
    multiplier = BRAND_PRICE_MULTIPLIERS.get(tier["primary_brand"], _DEFAULT_BRAND_MULTIPLIER)
    buffered_usd = tier["base_hardware_usd"] * multiplier * VOLATILITY_BUFFER
    estimated_zar = round(buffered_usd * fx_rate, 2)

    return AvConsultResponse(
        system_meta={
            "assumptions_version": AV_ASSUMPTIONS_VERSION,
            "architectural_profile": tier["tier"],
            "applied_standard": req.applied_standard,
        },
        spatial_metrics={
            "floor_area_sqm": round(area, 2),
            "acoustics_payload": acoustics,
        },
        cabling_infrastructure={
            "recommended_cable": tier["cable_spec"],
            "engineering_justification": tier["cable_why"],
        },
        procurement_projection={
            "recommended_hardware_ecosystem": tier["primary_brand"],
            "base_hardware_usd_assumption": tier["base_hardware_usd"],
            "brand_multiplier_assumption": multiplier,
            "volatility_buffer_assumption": VOLATILITY_BUFFER,
            "fx_rate_zar_used": fx_rate,
            "fx_source": fx_source,
            "estimated_landing_cost_zar": estimated_zar,
            "example_sa_distributors": list(_EXAMPLE_SA_DISTRIBUTORS),
            "distributor_note": _DISTRIBUTOR_NOTE,
        },
        sources=[],
        is_estimate=True,
        estimate_disclaimer=ESTIMATE_DISCLAIMER,
    )


@router.post("/consult", response_model=AvConsultResponse)
def av_consult(req: AvConsultRequest) -> AvConsultResponse:
    return run_consult(req)


@router.get("/consult")
def av_consult_info() -> Dict[str, Any]:
    return {
        "endpoint": "POST /v1/av/consult",
        "honesty_law": [
            "Every cost is an estimate: is_estimate is always true.",
            "fx_source labels exactly where the exchange rate came from:",
            "  request_override | live:open.er-api.com | fallback_assumption",
            "A fallback rate is never labelled as live.",
            "sources is always empty — this endpoint claims no live market data.",
            "Supplier names are examples only; verify authorisation yourself.",
        ],
        "assumptions_version": AV_ASSUMPTIONS_VERSION,
        "materials_known": sorted(ABSORPTION_COEFFICIENTS.keys()),
        "tiers": [
            {"tier": t["tier"], "max_area_sqm": t["max_area"]} for t in _TIERS
        ],
    }
