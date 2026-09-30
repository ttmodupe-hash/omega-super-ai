"""packages/shared/schema.py — ARCH-RESTRUCTURE-1 Phase 0.

Shared Pydantic v2 contracts for state flow across the four logical packages:

    sentinel_ai     -> guardrails, monitoring, state auditing
                       (core/hybrid_ai.GUARDRAILS + core/pii_scrub + core/ops_journal)
    luqi_ai         -> persona & interaction
                       (core/pedagogy_engine + core/companion_engine)
    omega_super_ai  -> reasoning & execution planning
                       (core/deep_research.plan_query + core/model_router.plan_chain)
    ai_bridge_pro   -> model router & LLM gateway
                       (core/model_router.route_chat, fail-closed)

Relationship to the existing engine: core/main_types.py LuqiState + TaskStatus
remain the law for the 30% human gate (PENDING_HUMAN_APPROVAL on
CRITICAL_ACTIONS). AgentState below is the *reasoning-pipeline* lifecycle for
the packages facade; it never executes critical actions and never bypasses
that gate.

Import-time law: pydantic + stdlib only.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ExecutionRequest(BaseModel):
    """Input payload for one orchestrated execution."""

    user_id: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=32000)
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    model_override: Optional[str] = Field(default=None, max_length=64)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Full lifecycle state threaded through all four packages.

    Stage ownership:
      sanitized_prompt  <- sentinel_ai first pass (PII scrub + guardrail screen)
      reasoning_plan    <- omega_super_ai (deterministic decomposition + provider chain)
      llm_response      <- ai_bridge_pro (multipolar routed execution)
      guardrail_status  <- sentinel_ai (True = both passes clean)
      audit_logs        <- sentinel_ai (append-only, mirrors ops_journal entries)
      final_output      <- sentinel_ai final pass (PII-safe, screen-clean text)
    """

    request: ExecutionRequest
    sanitized_prompt: str = ""
    reasoning_plan: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    llm_response: Dict[str, Any] = Field(default_factory=dict)
    guardrail_status: bool = False
    audit_logs: List[str] = Field(default_factory=list)
    final_output: str = ""

    def audit(self, message: str) -> None:
        """Append-only in-state audit trail (mirrored to ops_journal by the orchestrator)."""
        self.audit_logs.append(message)


class ExecutionResponse(BaseModel):
    """Public output format. Status law: success | blocked | error — nothing else."""

    session_id: str
    response: str
    status: Literal["success", "blocked", "error"]
    execution_time_ms: float = Field(ge=0.0)
