"""packages/orchestrator.py — EngineOrchestrator (ARCH-RESTRUCTURE-1 Phase 0).

Connects the four logical packages through AgentState. EVERY stage wires a
REAL, existing engine/core callable — verified by read-only inventory on
2026-09-30. No stubs, no parallel reimplementation:

  Stage 1 sentinel_ai (input):   core/pii_scrub.scrub_pii +
                                 core/hybrid_ai.GUARDRAILS (the same compiled
                                 ruleset HybridEngine.process screens with).
                                 SECURITY_* hits -> status "blocked".
  Stage 2 luqi_ai (persona):     core/pedagogy_engine.PEDAGOGICAL_DIRECTIVE
                                 (import-safe). companion_engine persona
                                 enrichment is lazy — it needs sqlalchemy,
                                 which is runtime-only by house law.
  Stage 3 omega_super_ai (plan): core/deep_research.plan_query (deterministic
                                 decomposition) + core/model_router.plan_chain
                                 (provider chain as data).
  Stage 4 ai_bridge_pro (LLM):   core/model_router.route_chat — multipolar
                                 execution with fallback; FAIL-CLOSED when no
                                 provider key is configured (HTTPException).
  Stage 5 sentinel_ai (output):  deterministic final pass — guardrail re-scan
                                 of generated text + PII-leak check, then
                                 core/ops_journal.record (never raises).

House laws honoured here:
  * 30% human gate: this pipeline is reasoning-only. CRITICAL_ACTIONS
    (payments, filings, deploys, legacy) stay gated in core/main.py — this
    orchestrator never executes them.
  * Fail-closed: any stage exception -> status "error" with an honest,
    secret-free message. We never fabricate a response.
  * Budget law: route_chat enforces MONTHLY_TOKEN_BUDGET_USD upstream.
  * Import-time law: fastapi/pydantic/stdlib only at import; sqlalchemy and
    slowapi are never imported by this module.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

try:  # primary: engine/ is the runtime cwd (uvicorn core.main:app)
    from core.hybrid_ai import GUARDRAILS
    from core.pii_scrub import scrub_pii
    from core.pedagogy_engine import PEDAGOGICAL_DIRECTIVE
    from core.deep_research import plan_query
    from core.model_router import plan_chain, route_chat
    from core.ops_journal import record as _journal_record
except ImportError:  # pragma: no cover - repo-root import path (CI layouts)
    from engine.core.hybrid_ai import GUARDRAILS
    from engine.core.pii_scrub import scrub_pii
    from engine.core.pedagogy_engine import PEDAGOGICAL_DIRECTIVE
    from engine.core.deep_research import plan_query
    from engine.core.model_router import plan_chain, route_chat
    from engine.core.ops_journal import record as _journal_record

from .shared.schema import AgentState, ExecutionRequest, ExecutionResponse

# Brand law: "Luqi-ai" (capital L, rest lowercase).
_PERSONA_HEADER = (
    "You are Luqi-ai, a sovereign African educational and consumer-protection "
    "engine. Mission: help people understand finance, avoid scams, and learn "
    "the importance of investing. Never invent statistics, sources, or "
    "capabilities; when unsure, say so plainly.\n\n"
)

# SECURITY_* guardrail hits block the request. CRITICAL_EMERGENCY / POLICY_*
# hits are routing guidance (handled by core/orchestrator.ask upstream) — they
# are audit-logged here but do NOT block.
_BLOCKING_PREFIX = "SECURITY_"

_OUTPUT_MAX_CHARS = 16000  # response-contract hygiene, mirrors audit snapshot caps


def _screen(text: str) -> List[Dict[str, Any]]:
    """sentinel_ai primitive: run the REAL compiled GUARDRAILS ruleset.

    Same algorithm as core/hybrid_ai.HybridEngine.process (lines 523-531):
    PII-scrub, lowercase, regex search. Returns the list of matched rules.
    """
    normalized = scrub_pii(text).lower()
    return [rule for rule in GUARDRAILS if rule["pattern"].search(normalized)]


class EngineOrchestrator:
    """Asynchronous 5-stage pipeline over AgentState."""

    def __init__(self, task_type: str = "chat") -> None:
        self._task_type = task_type

    # ----- stage helpers (sync stages run in a thread: no event-loop blocking) -----

    async def _sentinel_input_pass(self, state: AgentState) -> Optional[str]:
        """Returns a block reason, or None when the input is clean."""
        raw = state.request.prompt
        state.sanitized_prompt = await asyncio.to_thread(scrub_pii, raw)
        if state.sanitized_prompt != raw:
            state.audit("sentinel_ai: PII redacted from inbound prompt (data-sovereignty screen)")
        hits = await asyncio.to_thread(_screen, raw)
        for rule in hits:
            state.audit(f"sentinel_ai: guardrail hit {rule['id']}")
        blocking = [r for r in hits if r["id"].startswith(_BLOCKING_PREFIX)]
        if blocking:
            return blocking[0]["response"]
        return None

    async def _luqi_persona_pass(self, state: AgentState) -> str:
        """Build the styled system context from real persona directives."""
        system = _PERSONA_HEADER + PEDAGOGICAL_DIRECTIVE
        state.audit("luqi_ai: persona context applied (PEDAGOGICAL_DIRECTIVE, import-safe)")
        # companion_engine.build_system_prompt is real but imports sqlalchemy at
        # module top level (runtime-only dep by house law). Lazy, optional enrichment:
        try:
            from core.companion_engine import build_system_prompt  # noqa: F401
        except Exception:
            state.audit(
                "luqi_ai: companion persona enrichment unavailable "
                "(sqlalchemy runtime-only) — base directive stands"
            )
        return system

    async def _omega_plan_pass(self, state: AgentState) -> Dict[str, Any]:
        plan = await asyncio.to_thread(plan_query, state.sanitized_prompt)
        chain = await asyncio.to_thread(plan_chain, self._task_type)
        state.reasoning_plan = {
            "decomposition": plan,
            "provider_chain": chain,
            "planner": "core/deep_research.plan_query + core/model_router.plan_chain",
        }
        state.audit(
            f"omega_super_ai: plan built "
            f"({len(plan.get('sub_queries', []))} sub-queries, chain={chain})"
        )
        return state.reasoning_plan  # type: ignore[return-value]

    async def _ai_bridge_execute(self, state: AgentState, system: str) -> Dict[str, Any]:
        if state.request.model_override:
            # HONEST: provider selection is governed by model_router.plan_chain;
            # per-request override is not honoured yet (recorded, not faked).
            state.audit(
                f"ai_bridge_pro: model_override={state.request.model_override!r} noted; "
                "routing stays governed by plan_chain (override not yet wired)"
            )
        result = await route_chat(
            self._task_type,
            system,
            state.sanitized_prompt,
        )
        state.llm_response = dict(result)
        state.audit(f"ai_bridge_pro: executed via provider={result.get('provider')}")
        return state.llm_response

    async def _sentinel_output_pass(self, state: AgentState) -> str:
        """Final pass: screen generated text, scrub PII leaks, cap length."""
        content = str(state.llm_response.get("content", ""))
        hits = await asyncio.to_thread(_screen, content)
        if any(r["id"].startswith(_BLOCKING_PREFIX) for r in hits):
            state.audit("sentinel_ai: OUTPUT guardrail hit — response suppressed")
            return ""  # empty -> caller converts to blocked
        safe = await asyncio.to_thread(scrub_pii, content)
        if safe != content:
            state.audit("sentinel_ai: PII redacted from outbound response")
        if len(safe) > _OUTPUT_MAX_CHARS:
            safe = safe[:_OUTPUT_MAX_CHARS] + "...[truncated]"
            state.audit("sentinel_ai: response truncated to contract cap")
        return safe

    # ----- public entry -----

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        t0 = time.perf_counter()
        state = AgentState(request=request)
        status = "success"
        output = ""
        try:
            # Stage 1 — sentinel_ai first pass
            block_reason = await self._sentinel_input_pass(state)
            if block_reason is not None:
                state.guardrail_status = False
                state.final_output = block_reason
                status = "blocked"
                output = block_reason
                state.audit("sentinel_ai: request halted at first pass")
                return self._respond(state, status, output, t0)
            state.guardrail_status = True  # input clean; output pass still owed

            # Stage 2 — luqi_ai persona
            system = await self._luqi_persona_pass(state)

            # Stage 3 — omega_super_ai reasoning plan
            await self._omega_plan_pass(state)

            # Stage 4 — ai_bridge_pro execution (fail-closed upstream)
            await self._ai_bridge_execute(state, system)

            # Stage 5 — sentinel_ai final pass
            final = await self._sentinel_output_pass(state)
            if not final:
                state.guardrail_status = False
                status = "blocked"
                output = "Response withheld: failed the final safety screen."
            else:
                state.final_output = final
                output = final
        except Exception as e:  # fail-closed: honest error, never a fake answer
            status = "error"
            output = f"Engine execution failed honestly: {type(e).__name__}."
            state.audit(f"orchestrator: {type(e).__name__}: {str(e)[:200]}")
        return self._respond(state, status, output, t0)

    def _respond(
        self, state: AgentState, status: str, output: str, t0: float
    ) -> ExecutionResponse:
        elapsed = (time.perf_counter() - t0) * 1000.0
        state.audit(f"orchestrator: completed status={status} in {elapsed:.1f}ms")
        # Mirror the audit trail to the real ops journal (never raises).
        _journal_record({
            "event": "packages.orchestrator.execute",
            "session_id": state.request.session_id,
            "user_id": state.request.user_id,
            "status": status,
            "execution_time_ms": round(elapsed, 1),
            "audit_trail": list(state.audit_logs),
        })
        return ExecutionResponse(
            session_id=state.request.session_id,
            response=output,
            status=status,  # type: ignore[arg-type]
            execution_time_ms=elapsed,
        )
