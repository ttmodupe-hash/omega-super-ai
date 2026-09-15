"""
OMEGA-LUQI Sovereign Action Engine

Economic emancipation layer: routes entrepreneur queries through Moonshot's
deep-research web plugin to aggregate tender data, historical success
frameworks, and regional compliance requirements (BBBEE, local content laws)
into an executable blueprint.
"""
import os
import asyncio
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .kimi_gateway import KIMI_BASE_URL, KIMI_MODEL, KIMI_REASONING_EFFORT
from .kimi_plugins import NATIVE_PLUGINS

router = APIRouter()

SYSTEM_INSTRUCTION = (
    "You are the high-standard Luqi-AI Sovereign Action Engine. The user is an "
    "entrepreneur seeking economic growth. Analyze their request by scanning "
    "historical project parameters, public procurement registers, and industry "
    "success frameworks. Strip out all non-essential filler text. Provide a "
    "concrete execution timeline, itemized resource constraints, and a strict "
    "compliance checklist matching their local regulations (e.g., BBBEE in "
    "South Africa, local content laws in Kenya)."
)


class ScanRequest(BaseModel):
    entrepreneur_intent: str
    region_code: Optional[str] = "ZA"


def _call_action_engine(intent: str, region: str) -> dict:
    """Unified client: sovereign tender scan with $web_search."""
    from .kimi_client import chat_dict
    from .pii_scrub import scrub_pii
    return chat_dict(SYSTEM_INSTRUCTION, f"Target Region: {region}. Objectives: {scrub_pii(intent)}",
                     tools=NATIVE_PLUGINS, timeout=60)


@router.post("/v1/agent/scan-opportunities")
async def scan_global_opportunities(req: ScanRequest):
    """Tender/business scan endpoint. Fail-closed without KIMI_API_KEY."""
    try:
        return await asyncio.to_thread(_call_action_engine, req.entrepreneur_intent, req.region_code or "ZA")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Sovereign Network Gateway Disturbance: {str(e)}")
