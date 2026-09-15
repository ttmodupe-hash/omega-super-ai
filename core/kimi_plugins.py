"""
OMEGA-LUQI Kimi Native Plugin Engine

Routes deep-research student queries through Moonshot's built-in tool-calling
framework, giving Jarvis live web search without custom search infrastructure.

Queries pass through LuqiPromptSupport first when tier/track are supplied,
so even poorly written student questions reach Kimi in structured form.

NOTE: Moonshot's built-in search tool is named "$web_search" (with the dollar
sign). The pasted blueprint used "web_search" - that name is rejected by the
Kimi API with a tools-schema error.
"""
import os
import asyncio
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .prompt_support import LuqiPromptSupport

router = APIRouter()

# Kimi's permitted native plugins (Moonshot builtin_function registry)
NATIVE_PLUGINS = [
    {
        "type": "builtin_function",
        "function": {
            "name": "$web_search",
            "description": "Searches the live internet for up-to-date documentation, coding standards, and security flaws."
        }
    }
]


class ResearchRequest(BaseModel):
    student_query: str
    system_context: Optional[str] = None
    academic_tier: Optional[str] = None
    lab_track: Optional[str] = None
    auto_enhance: bool = True


def _call_kimi_plugins(query: str, system_context: Optional[str]) -> dict:
    """Unified client with $web_search plugins."""
    from .kimi_client import chat_dict
    from .pii_scrub import scrub_pii
    system = system_context or "You are the advanced Luqi-AI core reasoning loop, managing technical labs."
    return chat_dict(system, scrub_pii(query), tools=NATIVE_PLUGINS, timeout=60)


class EnhanceRequest(BaseModel):
    raw_prompt: str
    academic_tier: str = "tvet"
    lab_track: str = "software_dev"


@router.post("/v1/prompt/enhance")
async def enhance_student_prompt_endpoint(req: EnhanceRequest):
    """Real prompt-support endpoint backing the PWA suggestion box.
    Pure wrapping - no LLM call, so it works offline of AI keys and costs zero tokens."""
    try:
        enhanced = LuqiPromptSupport.enhance_student_prompt(req.raw_prompt, req.academic_tier, req.lab_track)
        return {"enhanced_prompt": enhanced}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/v1/agent/kimi-research")
async def execute_kimi_research_node(req: ResearchRequest):
    """Deep-research endpoint with web search plugin + optional prompt enhancement."""
    query = req.student_query
    if req.auto_enhance and req.academic_tier and req.lab_track:
        try:
            query = LuqiPromptSupport.enhance_student_prompt(query, req.academic_tier, req.lab_track)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        return await asyncio.to_thread(_call_kimi_plugins, query, req.system_context)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Plugin Pipeline Bridge Failure: {str(e)}")
