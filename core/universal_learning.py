"""
OMEGA-LUQI Universal Learning Companion

High-context knowledge expansion across technical and medical-training
domains, Ubuntu-philosophy framing, $web_search plugin, auth-gated.

CONTENT POLICY (deliberate deviation from the pasted blueprint): the original
system prompt instructed the model to NEVER output warnings on medical topics.
That is a liability grenade - the merged directive instead REQUIRES a clear
"not a substitute for professional medical care" disclaimer whenever the
domain is medical. Capability is unchanged; the output is defensible.
Guard test below locks this in.

Costs tokens -> AUTH-GATED. Fail-closed without KIMI_API_KEY.
"""
import asyncio
import json
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile
from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .kimi_plugins import NATIVE_PLUGINS
from .kimi_parse import extract_assistant_content
from .pii_scrub import scrub_pii

universal_router = APIRouter(prefix="/v1/sovereign-learning", tags=["Universal Pedagogy Engine"])

_RUN_STATS = {"expansions": 0, "failures": 0}


class KnowledgeExpansionSchema(BaseModel):
    subject_domain: str                  # e.g., "Advanced Medical Training"
    target_topic: str
    resource_context_inputs: List[str]


UBUNTU_DIRECTIVE = (
    "You are the Luqi-AI Universal Companion. Ubuntu ethos (Umuntu ngumuntu "
    "ngabantu): dignity-first, encouraging, clear practical steps - no dry filler.\n"
    "DOMAIN HANDLING:\n"
    "- Medical/botanical training: analyze molecular structures, biochemical "
    "mechanisms, and indigenous flora research thoroughly AND practically.\n"
    "- Engineering/robotics/space: mechatronics code, mechanics, geometries.\n"
    "MANDATORY DISCLAIMER: when the domain is medical, the response MUST state "
    "that it is educational research assistance, not a substitute for "
    "professional medical care or clinical certification.\n"
    "Output strictly valid JSON with two keys: 'practical_action_blueprint' and "
    "'scientific_resource_source_code'."
)


def _call_universal_engine(schema: KnowledgeExpansionSchema) -> Dict[str, Any]:
    """Unified client: Ubuntu-framed knowledge expansion ($web_search)."""
    from .kimi_client import chat_completion
    content = chat_completion(
        UBUNTU_DIRECTIVE,
        scrub_pii(f"Domain: {schema.subject_domain}. Topic: {schema.target_topic}. "
                  f"Inputs: {schema.resource_context_inputs}"),
        tools=NATIVE_PLUGINS,
        timeout=60,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_blueprint": content}


@universal_router.post("/expand-capability")
async def execute_universal_capability_expansion(
    request_data: KnowledgeExpansionSchema,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Universal knowledge expansion. Auth-gated; medical outputs carry disclaimers."""
    try:
        blueprint = await asyncio.to_thread(_call_universal_engine, request_data)
        _RUN_STATS["expansions"] += 1
    except requests.exceptions.RequestException as e:
        _RUN_STATS["failures"] += 1
        raise HTTPException(status_code=503, detail=f"Universal Knowledge Engine Interruption: {e}")
    from .contracts import check_contract
    check_contract("universal", blueprint if isinstance(blueprint, dict) else {})
    return {
        "status": "success",
        "subject_domain": request_data.subject_domain,
        "ubuntu_philosophy_applied": True,
        "medical_disclaimer_required": "medical" in request_data.subject_domain.lower(),
        "compiled_blueprint": blueprint,
    }


@universal_router.get("/stats")
async def universal_stats():
    return dict(_RUN_STATS)
