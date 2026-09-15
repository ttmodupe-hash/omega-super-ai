"""
OMEGA-LUQI Sovereign Pedagogical Convergence Engine

Transforms static curriculum text into practical engineering blueprints via a
multi-methodology system prompt (mathematical rigor / industrial scaling /
precision automation personas) grounded in African resource contexts.

Honest framing: the "three global engines" are one Kimi K3 model wearing a
structured persona - not three licensed methodologies. A true multi-model
router (Kimi + Gemini + Claude per-strength) is tracked future work; the
GEMINI_API_KEY / CLAUDE_API_KEY env hooks already exist for it.

Costs money -> AUTH-GATED. Fail-closed without KIMI_API_KEY.
"""
import json
import asyncio
from typing import Any, Dict

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .pii_scrub import scrub_pii

pedagogy_router = APIRouter(prefix="/v1/pedagogy", tags=["Sovereign Learning Science"])

# Run counter (memory, per-boot; exposed honestly as such on the dashboard)
_RUN_STATS = {"runs": 0, "failures": 0}


class LearningProfileSchema(BaseModel):
    group_demographic: str    # e.g., "Gauteng TVET Electronics Class"
    target_subject: str       # e.g., "Robotics & Microcontroller Logic"
    raw_curriculum_text: str


from .kimi_parse import extract_assistant_content as _extract_assistant_content  # shared, regression-tested


PEDAGOGICAL_DIRECTIVE = (
    "You are the Master Luqi-AI Multi-Methodology Global Education Swarm. "
    "Take standard theoretical concepts and expand them into advanced, practical engineering blueprints. "
    "Apply three lenses:\n"
    "1. MATHEMATICAL RIGOR: force optimization, geometry proofs, deep algorithmic thinking.\n"
    "2. INDUSTRIAL SCALING: map practicality, high-efficiency system scaling, solar energy networks, manufacturing.\n"
    "3. PRECISION AUTOMATION: enforce ahead-of-schedule automation benchmarks, high-precision robotics.\n"
    "AFRICAN ECONOMIC FOCUS: ground all outputs in real African resource contexts - food security, "
    "mineral processing, off-grid telecom. "
    "Output strictly valid JSON with keys: 'optimized_practical_checklist', 'mathematical_proof_steps', "
    "'hardware_sandbox_instructions'."
)


def _call_pedagogy_engine(profile: LearningProfileSchema) -> Dict[str, Any]:
    """Unified client: multi-lens curriculum expansion."""
    from .kimi_client import chat_completion
    from .pii_scrub import scrub_pii
    content = chat_completion(
        PEDAGOGICAL_DIRECTIVE,
        scrub_pii(f"Group: {profile.group_demographic}. Subject: {profile.target_subject}. "
                  f"Input: {profile.raw_curriculum_text}"),
        timeout=45,
    )
    try:
        blueprint = json.loads(content)
    except json.JSONDecodeError:
        blueprint = {"raw_blueprint": content}
    from .contracts import check_contract
    check_contract("pedagogy", blueprint)
    return {
        "status": "success",
        "target_group": profile.group_demographic,
        "enhanced_subject_nodes": profile.target_subject,
        "methodology_lenses": ["mathematical_rigor", "industrial_scaling", "precision_automation"],
        "african_growth_impact_vector": "Optimized for local resource processing infrastructure",
        "advanced_blueprint": blueprint,
    }


@pedagogy_router.post("/optimize-learning-path")
async def optimize_and_advance_learning_path(
    profile: LearningProfileSchema,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """World-class practical blueprint for a student group. Auth-gated (token cost)."""
    try:
        result = await asyncio.to_thread(_call_pedagogy_engine, profile)
        _RUN_STATS["runs"] += 1
        return result
    except requests.exceptions.RequestException as e:
        _RUN_STATS["failures"] += 1
        raise HTTPException(status_code=503, detail=f"Sovereign Pedagogical Pipeline Error: {e}")


@pedagogy_router.get("/stats")
async def pedagogy_stats():
    """Live run counters (memory, per-boot - dashboard labels them honestly)."""
    return dict(_RUN_STATS)
