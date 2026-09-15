"""
OMEGA-LUQI Sovereign Bio-Mineral Exploration Engine

Multipolar research compilation: botanical synthesis paths and mechatronics
blueprints grounded in African resource contexts, via Kimi K3 with the
$web_search builtin.

DESIGN BOUNDARIES (read before extending):
  - Compiles are READ-ONLY and return immediately. The 30% gate is NOT applied
    to compiles - there is no side effect to authorize, and freezing pure
    generation would be gate theater.
  - DEPLOYMENT is a separate, explicit intent (request_deployment=true). It
    registers a gate task; the actual write to any production system remains
    PROPOSAL-ONLY until a human executes it (same boundary as self_healing).
    No agent in this engine writes to robots, databases, or infrastructure.
  - MEDICAL LIABILITY: outputs are research assistance, not medical advice.
    The UI and docs carry this disclaimer; keep it that way.

Costs tokens -> AUTH-GATED. Fail-closed without KIMI_API_KEY.
"""
import asyncio
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .kimi_plugins import NATIVE_PLUGINS  # shared, correct $web_search builtin
from .kimi_parse import extract_assistant_content
from .main_types import LuqiState, TaskStatus
from .state_store import get_state_store
from .pii_scrub import scrub_pii

sovereign_router = APIRouter(prefix="/v1/sovereign", tags=["Sovereign Multipolar Infrastructure"])

_RUN_STATS = {"compiles": 0, "deploy_intents": 0, "failures": 0}


class BioMineralRequestSchema(BaseModel):
    exploration_type: str               # "botanical_medicine" | "robotic_metallurgy"
    target_objective: str
    raw_material_inputs: List[str]
    request_deployment: bool = False    # explicit intent -> registers a 30% gate task


SOVEREIGN_DIRECTIVE = (
    "You are the Master Luqi-AI Sovereign Bio-Mineral Exploration Swarm. Process the objective "
    "and output production-grade engineering blueprints, biochemical synthesis paths, or robotics "
    "code trees. Apply three lenses: mathematical/structural rigor, industrial scaling, and "
    "high-precision automation. Ground outputs in African resource contexts (native flora, "
    "Lithium/Cobalt/Platinum). Output strictly valid JSON with two keys: "
    "'practical_execution_steps' and 'production_source_code'. "
    "This is research assistance, not medical or engineering certification."
)


def _call_sovereign_engine(schema: BioMineralRequestSchema) -> Dict[str, Any]:
    """Unified client: bio-mineral compilation with $web_search."""
    from .kimi_client import chat_completion
    import json as _json
    content = chat_completion(
        SOVEREIGN_DIRECTIVE,
        scrub_pii(f"Type: {schema.exploration_type}. Objective: {schema.target_objective}. "
                  f"Inputs: {schema.raw_material_inputs}"),
        tools=NATIVE_PLUGINS,
        timeout=60,
    )
    try:
        return _json.loads(content)
    except _json.JSONDecodeError:
        return {"raw_blueprint": content}


@sovereign_router.post("/compile-blueprint")
async def compile_sovereign_blueprint(
    request_data: BioMineralRequestSchema,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Compile a blueprint (returns immediately). Deployment intent -> 30% gate task."""
    try:
        blueprint = await asyncio.to_thread(_call_sovereign_engine, request_data)
        _RUN_STATS["compiles"] += 1
    except requests.exceptions.RequestException as e:
        _RUN_STATS["failures"] += 1
        raise HTTPException(status_code=503, detail=f"Sovereign Infrastructure Pipeline Failure: {e}")

    from .contracts import check_contract
    contract_stamp = None
    if isinstance(blueprint, dict) and "raw_blueprint" not in blueprint:
        contract_stamp = check_contract("sovereign", blueprint)
    response: Dict[str, Any] = {
        "status": "compiled",
        "contract": contract_stamp or "unstructured-fallback",
        "exploration_type": request_data.exploration_type,
        "disclaimer": "Research assistance only - not medical, legal, or engineering certification.",
        "blueprint": blueprint,
    }

    if request_data.request_deployment:
        task = LuqiState(
            student_tier=current_user.tier,
            action_type="deploy_heavy_infrastructure",
            payload={
                "item": f"Sovereign deployment intent: {request_data.target_objective[:120]}",
                "exploration_type": request_data.exploration_type,
                # Blueprint NOT embedded: gate payloads stay lean; audit snapshots are size-capped.
                "blueprint_size_bytes": len(str(blueprint)),
            },
        )
        task.status = TaskStatus.PENDING_HUMAN_APPROVAL
        task.required_human_action = (
            "Deployment intent registered. Review the compiled blueprint, then execute the "
            "deployment MANUALLY - agent auto-deployment is intentionally not implemented."
        )
        get_state_store().set(task.task_id, task)
        from .notifications import notify_gate_lock
        notify_gate_lock(task)
        _RUN_STATS["deploy_intents"] += 1
        response["deployment_intent"] = {
            "gate_task_id": str(task.task_id),
            "status": "locked_at_30pct_gate",
            "message": "Deployment is proposal-only; a human executes after review.",
        }

    return response


@sovereign_router.get("/stats")
async def sovereign_stats():
    return dict(_RUN_STATS)
