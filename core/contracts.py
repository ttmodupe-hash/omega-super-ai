"""
OMEGA-LUQI Engine Output Contracts - verification at the boundary.

Verification asymmetry applies to LLM outputs too: generation is cheap, so
drift is common. Each engine declares its required response keys; a violation
means the model returned prose instead of the promised structure - that must
fail closed (502), not reach a student as drifted output.

Engines with a declared contract: pedagogy, sovereign, universal, integrity.
"""
from typing import Any, Dict

from fastapi import HTTPException

CONTRACTS: Dict[str, set] = {
    "pedagogy": {"optimized_practical_checklist", "mathematical_proof_steps",
                 "hardware_sandbox_instructions"},
    "sovereign": {"practical_execution_steps", "production_source_code"},
    "universal": {"practical_action_blueprint", "scientific_resource_source_code"},
    "integrity": {"similarity_percentage_score", "plagiarism_flags_detected",
                  "jarvis_remedial_feedback"},
}


def check_contract(engine: str, payload: Any) -> Dict[str, Any]:
    """Raise 502 on contract violation; return a verification stamp otherwise."""
    required = CONTRACTS.get(engine)
    if required is None:
        return {"contract": "none"}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502,
                            detail=f"{engine}: engine output was not structured - contract violated")
    missing = required - set(payload.keys())
    if missing:
        raise HTTPException(status_code=502,
                            detail=f"{engine}: output missing required keys {sorted(missing)}")
    return {"contract": engine, "verified_keys": sorted(required)}
