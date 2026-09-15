"""
OMEGA-LUQI shared Kimi response parsing.

choices is a LIST. Three pastes indexed it as a dict and shipped a
crash-on-success bug. One shared helper, one test, no fourth occurrence.
"""
from typing import Any, Dict

from fastapi import HTTPException


def extract_assistant_content(payload: Dict[str, Any]) -> str:
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise HTTPException(status_code=502, detail=f"Malformed upstream response: {e}")
