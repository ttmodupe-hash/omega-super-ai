"""
OMEGA-LUQI Feature Flags - progressive delivery, env-first.

Complements the DISABLED_ENGINES kill switch (emergency cousin) with
rollout-oriented toggles: FEATURE_FLAGS="voice:on,sovereign:beta,medical:off".
Public read endpoint so clients can show what's live. Future path:
percentage rollouts backed by Redis (documented, deliberately not built).

Flags never override safety: the 30% gate and guardrails are not flaggable.
"""
import os
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/v1/features", tags=["Feature Flags"])

_UNFLAGGABLE = {"gate", "guardrails", "pii_scrub"}  # safety is not a feature flag


def parse_flags(env_value: str = None) -> Dict[str, str]:
    """FEATURE_FLAGS env -> {name: state}. Default: everything on."""
    raw = env_value if env_value is not None else os.getenv("FEATURE_FLAGS", "")
    flags: Dict[str, str] = {}
    for pair in raw.split(","):
        if ":" in pair:
            name, state = pair.split(":", 1)
            flags[name.strip()] = state.strip()
    return flags


def is_enabled(name: str, flags: Dict[str, str] = None) -> bool:
    """Default-on unless explicitly off/beta-gated. Safety layers unflaggable.
    flags injectable for testing; production callers read env via default."""
    if name in _UNFLAGGABLE:
        return True
    flags = flags if flags is not None else parse_flags()
    return flags.get(name, "on").lower() not in ("off", "disabled")


@router.get("")
async def feature_flags() -> Dict[str, Any]:
    flags = parse_flags()
    return {"flags": flags, "safety_layers_unflaggable": sorted(_UNFLAGGABLE)}
