"""
AV Consultancy skill — AV-1 + AV-2 (luqi-ai)

Deterministic AV room consultancy: Sabine RT60 acoustics, AV-over-IP network
sizing, scheduling-panel topology, honest inventory status, honest South
African procurement estimation, and a REAL PDF proposal.

- POST /v1/av/consult   — room dims + materials + streams -> full payload
- POST /v1/av/proposal  — same inputs -> real PDF (reportlab), honest 503 if
                          the PDF engine is unavailable
- GET  /v1/av/consult   — documents the honesty law of this endpoint

AV-2 additions (assumptions v1.1.0): network_infrastructure, facility_scheduling,
inventory (never fabricated), PDF proposal with deterministic content-hash ID.

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
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/av", tags=["av-consultancy"])

AV_ASSUMPTIONS_VERSION = "1.1.0"

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


# --- AV-2: network stream bandwidth assumptions (Gbps per 4K stream) -------
# Engineering approximations, NOT measured data — labelled as such.
STREAM_PROTOCOL_BASELINES_GBPS: Dict[str, float] = {
    "sdvoe_uncompressed": 9.0,     # uncompressed 4K60 4:4:4 needs 10GbE-class pipes
    "jpeg_xs_compressed": 1.2,     # high-fidelity low-latency compression
    "h264_h265_streaming": 0.025,  # compressed VC/BYOD streams (~25 Mbps baseline)
}
_STREAM_OVERHEAD = 1.20  # 20% burst/engineering buffer

# --- AV-2: honest inventory client -----------------------------------------
# There is NO public live ERP feed for SA AV distributors. If the operator
# configures LUQI_AV_STOCK_API_URL (a real supplier endpoint they have
# credentials for), we query it for real and label the result live.
# Otherwise we say so. We never invent stock numbers.
_STOCK_API_URL = os.environ.get("LUQI_AV_STOCK_API_URL", "").strip()
_STOCK_TIMEOUT_S = 4

_INVENTORY_NOT_INTEGRATED = {
    "status": "not_integrated",
    "is_live": False,
    "note": ("No live distributor ERP feed is integrated. "
             "Confirm stock and lead times with the distributor before ordering."),
}


def check_inventory(brand: str) -> Dict[str, Any]:
    """Honest inventory check. Live only if a real supplier API is configured
    AND answers; otherwise an explicit non-live status. Never fabricated."""
    if not _STOCK_API_URL:
        return dict(_INVENTORY_NOT_INTEGRATED)
    try:
        url = f"{_STOCK_API_URL}{'&' if '?' in _STOCK_API_URL else '?'}brand={urllib.parse.quote(brand)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=_STOCK_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "status": data.get("status", "unknown"),
            "is_live": True,
            "source": urllib.parse.urlparse(_STOCK_API_URL).netloc,
            "component": data.get("component"),
            "available_units": data.get("units"),
            "lead_time": data.get("lead_time"),
            "note": "Live supplier API response — verify at order time anyway.",
        }
    except Exception:
        return {
            "status": "unreachable",
            "is_live": False,
            "note": ("A supplier API is configured but did not answer within "
                     f"{_STOCK_TIMEOUT_S}s — confirm stock manually with the distributor."),
        }


def calculate_throughput(num_streams: int, protocol: str,
                         overhead: float = _STREAM_OVERHEAD) -> Dict[str, Any]:
    """AV-over-IP bandwidth estimate. Baselines are engineering approximations."""
    key = protocol.lower()
    if key not in STREAM_PROTOCOL_BASELINES_GBPS:
        raise HTTPException(400, detail={
            "error": f"unknown stream_protocol '{protocol}'",
            "valid": sorted(STREAM_PROTOCOL_BASELINES_GBPS.keys()),
        })
    base = STREAM_PROTOCOL_BASELINES_GBPS[key]
    raw = num_streams * base
    engineered = raw * overhead

    if engineered > 10.0:
        switch = "Enterprise core 40/100GbE stacked fibre switch"
        warning = ("Aggregated streams exceed 10GbE backbones — IGMP snooping and "
                   "spanning-tree design are mandatory.")
    elif engineered > 1.0:
        switch = "Dedicated managed 10GbE Layer-3 switch (non-blocking backplane)"
        warning = "10G pipeline sufficient — enable jumbo frames (9000-byte MTU)."
    else:
        switch = "Standard 1GbE managed PoE+ switch"
        warning = "Fits common network runs — prioritise AV VLAN QoS tagging."

    return {
        "active_streams": num_streams,
        "stream_protocol": key,
        "baseline_gbps_per_stream_assumption": base,
        "raw_payload_gbps": round(raw, 3),
        "engineered_load_gbps": round(engineered, 3),
        "overhead_factor_assumption": overhead,
        "recommended_switch_fabric": switch,
        "network_topology_note": warning,
    }


def design_scheduling_layer(tier: str, wall_material: str) -> Dict[str, Any]:
    """Room-booking panel topology — panel class from tier, mount from wall."""
    if "huddle" in tier.lower():
        panel = "7-inch scheduling panel class (e.g. Logitech Tap Scheduler)"
        power = "PoE 802.3af Class 1"
    else:
        panel = "10-inch enterprise scheduling touchscreen class (e.g. Crestron TSS series)"
        power = "PoE 802.3af Class 2"

    if wall_material.lower() == "glass":
        mount = ("Glass-mount kit with high-bond structural adhesive and rear-side "
                 "cosmetic cover shroud")
        pathway = ("Surface-mount low-profile raceway to the ceiling plenum — glass has "
                   "no internal cavity for in-wall drops")
        reason = ("Glass panels have no wall cavity; adhesive mounting plus a cosmetic "
                  "shroud keeps the corridor side clean.")
    else:
        mount = "Flush single-gang backbox (drywall) or masonry anchors"
        pathway = "In-wall solid-copper drop in 20 mm conduit — fully hidden"
        reason = "A structural wall cavity allows fully concealed cabling."

    return {
        "scheduling_panel_class": panel,
        "power_draw": power,
        "mounting_hardware": mount,
        "cabling_pathway": pathway,
        "selection_justification": reason,
    }


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
    num_video_streams: int = Field(4, ge=0, le=64, description="Concurrent AV-over-IP streams")
    stream_protocol: str = Field("jpeg_xs_compressed", max_length=40,
                                 description="sdvoe_uncompressed | jpeg_xs_compressed | h264_h265_streaming")


class AvConsultResponse(BaseModel):
    system_meta: Dict[str, Any]
    spatial_metrics: Dict[str, Any]
    cabling_infrastructure: Dict[str, Any]
    network_infrastructure: Dict[str, Any]
    facility_scheduling: Dict[str, Any]
    procurement_projection: Dict[str, Any]
    inventory: Dict[str, Any]     # honest: is_live false unless a real supplier API answered
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
        network_infrastructure=calculate_throughput(req.num_video_streams, req.stream_protocol),
        facility_scheduling=design_scheduling_layer(tier["tier"], req.wall_material),
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
        inventory=check_inventory(tier["primary_brand"]),
        sources=[],
        is_estimate=True,
        estimate_disclaimer=ESTIMATE_DISCLAIMER,
    )


@router.post("/consult", response_model=AvConsultResponse)
def av_consult(req: AvConsultRequest) -> AvConsultResponse:
    return run_consult(req)


# --- AV-2: REAL PDF proposal ------------------------------------------------
# The founder doc faked this as a text "mock-stream" with a random document
# ID. This is a real PDF (reportlab) with a deterministic content-hash ID —
# the same consult payload always yields the same document ID.

def _proposal_doc_id(res: AvConsultResponse) -> str:
    canonical = json.dumps(res.model_dump(), sort_keys=True, separators=(",", ":"))
    return "LUQI-AV-" + hashlib.sha256(canonical.encode()).hexdigest()[:10].upper()


def build_proposal_pdf(res: AvConsultRequest) -> bytes:
    """Run the consult and render a real one-page PDF proposal."""
    data = run_consult(res)
    ac = data.spatial_metrics["acoustics_payload"]
    cab = data.cabling_infrastructure
    net = data.network_infrastructure
    sched = data.facility_scheduling
    fin = data.procurement_projection
    inv = data.inventory
    doc_id = _proposal_doc_id(data)

    from reportlab.lib.pagesizes import A4  # lazy: honest 503 if missing
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 20 * mm
    left = 18 * mm

    def line(text: str, dy: float = 5.2, bold: bool = False, size: int = 9) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(left, y, text[:105])
        y -= dy * mm

    line("LUQI-AI — AV ARCHITECTURE PROPOSAL", 7, bold=True, size=14)
    line(f"Document ID: {doc_id}  (deterministic content hash — same inputs, same ID)")
    line(f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC")
    line(f"Assumptions version: {data.system_meta['assumptions_version']}  ·  "
         f"Profile: {data.system_meta['architectural_profile']}  ·  "
         f"Standard: {data.system_meta['applied_standard']}", 7)

    line("1. ACOUSTICS (Sabine RT60 = 0.161·V/A)", 5, bold=True, size=10)
    line(f"Volume {ac['room_volume_m3']} m3 · Absorption {ac['total_absorption_sabins']} sabins · "
         f"RT60 {ac['estimated_rt60_seconds']}s · {ac['aec_dsp_profile']}")
    line(ac["acoustic_remediation_notes"], 7)

    line("2. CABLING INFRASTRUCTURE", 5, bold=True, size=10)
    line(cab["recommended_cable"])
    line(cab["engineering_justification"], 7)

    line("3. NETWORK (AV-over-IP)", 5, bold=True, size=10)
    line(f"{net['active_streams']} streams · {net['stream_protocol']} · "
         f"raw {net['raw_payload_gbps']} Gbps · engineered {net['engineered_load_gbps']} Gbps "
         f"(x{net['overhead_factor_assumption']} overhead)")
    line(f"Switch fabric: {net['recommended_switch_fabric']}")
    line(net["network_topology_note"], 7)

    line("4. SCHEDULING PANEL", 5, bold=True, size=10)
    line(f"{sched['scheduling_panel_class']} · {sched['power_draw']}")
    line(f"Mount: {sched['mounting_hardware']}")
    line(f"Pathway: {sched['cabling_pathway']}", 7)

    line("5. COST ESTIMATE (ZAR) — ESTIMATE ONLY, NOT A QUOTE", 5, bold=True, size=10)
    line(f"R {fin['estimated_landing_cost_zar']:,.2f} estimated landing cost "
         f"({fin['recommended_hardware_ecosystem']} ecosystem)")
    line(f"= USD {fin['base_hardware_usd_assumption']} base x {fin['brand_multiplier_assumption']} brand "
         f"x {fin['volatility_buffer_assumption']} buffer x R{fin['fx_rate_zar_used']}/$ "
         f"[fx_source: {fin['fx_source']}]", 7)

    line("6. INVENTORY STATUS", 5, bold=True, size=10)
    inv_line = f"status: {inv['status']} · is_live: {inv['is_live']}"
    if inv.get("component"):
        inv_line += f" · {inv['component']}: {inv.get('available_units')} units · {inv.get('lead_time')}"
    line(inv_line)
    line(inv["note"], 7)

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(left, y, data.estimate_disclaimer[:110])
    y -= 4.5 * mm
    c.drawString(left, y, "Sources: none claimed — deterministic calculation with disclosed assumptions."[:110])
    c.showPage()
    c.save()
    return buf.getvalue()


@router.post("/proposal")
def av_proposal(req: AvConsultRequest) -> Response:
    """Real PDF proposal for the same consult inputs. 503 if the PDF engine
    is unavailable (fail-closed honesty — never a fake document)."""
    try:
        pdf = build_proposal_pdf(req)
    except ImportError:
        raise HTTPException(503, detail={
            "error": "PDF engine unavailable",
            "note": "reportlab is not installed on this node — no proposal was generated.",
        })
    doc_id = _proposal_doc_id(run_consult(req))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc_id}.pdf"'},
    )


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
            "Inventory is never fabricated: is_live is true only when a real",
            "  configured supplier API (LUQI_AV_STOCK_API_URL) actually answered.",
            "POST /v1/av/proposal returns a REAL PDF (reportlab), never a mock.",
        ],
        "assumptions_version": AV_ASSUMPTIONS_VERSION,
        "materials_known": sorted(ABSORPTION_COEFFICIENTS.keys()),
        "stream_protocols": sorted(STREAM_PROTOCOL_BASELINES_GBPS.keys()),
        "tiers": [
            {"tier": t["tier"], "max_area_sqm": t["max_area"]} for t in _TIERS
        ],
    }
