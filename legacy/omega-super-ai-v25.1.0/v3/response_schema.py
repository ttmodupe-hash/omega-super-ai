"""Omega AI v3 — Unified Response Schema
Every module returns a standardized response dict for consistent handling.
"""
from __future__ import annotations

from typing import Any, TypedDict, NotRequired


class ResponseDict(TypedDict):
    """Standardized response format across all Luqi-AI modules."""
    success: bool
    response: str
    data: NotRequired[dict[str, Any]]
    sources: NotRequired[list[dict[str, str]]]
    error: NotRequired[str | None]
    module: NotRequired[str]
    response_time_ms: NotRequired[float]


def ok(response: str, module: str = "", **kwargs: Any) -> ResponseDict:
    """Create a successful response."""
    result: ResponseDict = {
        "success": True,
        "response": response,
        "sources": [],
        "error": None,
        "module": module,
    }
    result.update(kwargs)
    return result


def err(error: str, module: str = "", fallback_response: str = "") -> ResponseDict:
    """Create an error response with optional fallback text."""
    return {
        "success": False,
        "response": fallback_response or f"[Error in {module}] {error}",
        "sources": [],
        "error": error,
        "module": module,
    }


def from_dict(raw: dict[str, Any], module: str = "") -> ResponseDict:
    """Normalize a raw dict into a standard ResponseDict."""
    result: ResponseDict = {
        "success": raw.get("success", True),
        "response": "",
        "sources": raw.get("sources", []),
        "error": raw.get("error"),
        "module": module or raw.get("module", ""),
    }
    for key in ("response", "summary", "text", "result", "output", "content"):
        if key in raw and isinstance(raw[key], str):
            result["response"] = raw[key]
            break
    if not result["response"]:
        result["response"] = str(raw)
    if "data" in raw:
        result["data"] = raw["data"]
    if "response_time_ms" in raw:
        result["response_time_ms"] = raw["response_time_ms"]
    return result