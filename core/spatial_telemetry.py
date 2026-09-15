"""
OMEGA-LUQI Spatial Telemetry - server-side physics for client-rendered 3D labs.

Architecture (from the reviewed blueprint, corrected): the browser renders
lightweight native WebGL meshes locally (no heavy asset streaming over mobile
networks); the ENGINE computes the physics server-side via this module.

FIXED from the paste: it imported a tenant dependency that does not exist
in core.auth - the module would have crashed the app at import time. Uses
the real LuqiAuthManager dependency.

ADVANCED beyond the paste: a passing simulation EARNS CREDIT. trade_id maps
to a registered skill; on safety-compliant success the engine records the
verified skill (which fires the WhatsApp/SMS unlock alert and counts toward
certificates). A failed simulation awards nothing.
"""
import math
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import LuqiAuthManager, UserSessionProfile

router = APIRouter(prefix="/v1/spatial", tags=["Spatial Telemetry"])

# Spatial trade simulations map to registered skills on success
SPATIAL_SKILL_MAP = {
    "plumbing_hydraulics": "Plumbing Quote",
    "electrical_installation": "Electrical Installation Plan",
    "solar_array_layout": "Solar Array Design",
}


class Vector3D(BaseModel):
    x: float
    y: float
    z: float


class PhysicsTimeStep(BaseModel):
    elapsed_seconds: float = Field(gt=0.0, le=3600.0)
    applied_force_newtons: float = Field(ge=0.0)
    system_stress_tolerance: float = Field(default=500.0, gt=0.0)


class SpatialTelemetryPayload(BaseModel):
    session_id: str
    trade_id: str
    coordinates: Vector3D
    telemetry: PhysicsTimeStep


def evaluate_structural_load(coords: Vector3D, tel: PhysicsTimeStep) -> Dict[str, Any]:
    """Pure physics: vector magnitude -> distributed load -> safety envelope."""
    magnitude = math.sqrt(coords.x ** 2 + coords.y ** 2 + coords.z ** 2 + 1e-9)
    load = (tel.applied_force_newtons / (magnitude * 2 * math.pi)) * tel.elapsed_seconds
    return {
        "vector_magnitude": round(magnitude, 3),
        "computed_load_kpa": round(load, 2),
        "structural_fatigue": round(min(1.0, load / tel.system_stress_tolerance), 3),
        "safety_envelope_breached": load > tel.system_stress_tolerance,
    }


@router.post("/verify")
async def verify_spatial_telemetry(payload: SpatialTelemetryPayload,
                                   user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token)):
    """Server-side physics validation; on success, records real skill credit."""
    report = evaluate_structural_load(payload.coordinates, payload.telemetry)

    if report["safety_envelope_breached"]:
        return {"status": "SIMULATION_FAILED", "practical_passed": False,
                "feedback": (f"Mechanical failure: load {report['computed_load_kpa']} kPa exceeded "
                             f"tolerance {payload.telemetry.system_stress_tolerance}."),
                "telemetry": report}

    result: Dict[str, Any] = {"status": "SIMULATION_SUCCESS", "practical_passed": True,
                              "feedback": "Spatial placement within industrial safety standards.",
                              "telemetry": report}
    skill = SPATIAL_SKILL_MAP.get(payload.trade_id)
    if skill:
        from .skill_engine import record_verified
        credit = record_verified(str(user.user_id), skill,
                                 f"spatial sim {payload.session_id[:12]} load={report['computed_load_kpa']}kPa")
        result["skill_credit"] = {"skill": skill, **credit}
    else:
        result["skill_credit"] = {"skill": None,
                                  "note": f"trade '{payload.trade_id}' has no skill mapping - no credit recorded"}
    return result
