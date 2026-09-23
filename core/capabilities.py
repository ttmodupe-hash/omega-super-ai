"""
Capability maturity + machine-readable manifest — GAP-1 (luqi-ai)

The engine's honest answer to "what can you do?" — as CODE, so the answer
can never drift from reality:

- GET  /v1/capabilities/maturity  — the modern-AI checklist audit: 9 items,
  honest status per item with file-level evidence
- GET  /v1/capabilities/manifest  — MCP-style tool manifest describing the
  REAL deterministic tools, for external AI systems and agent clients
- POST /v1/capabilities/route     — activates the dormant capability_router:
  cheapest-adequate-model routing verdict (decision only — no upstream LLM
  call is made here; providers without keys are skipped, and when nothing
  configured can do the job the verdict is an HONEST refusal)

Design rules (house law):
- Statuses come from a fixed enum and every claim cites the code that backs it.
- The manifest lists only routes that are actually mounted — the verification
  battery (tests/verify_capabilities.py) cross-checks every entry against the
  live app's route table. A manifest entry for a missing route fails CI.
- live_data is never bare `true` for market/stock data — "optional" means
  "live only when a real configured upstream answered, labelled in-payload".
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import capability_router

router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])

_STATUSES = ("built", "partial", "roadmap", "not_applicable")

# ── The audit, as data. Evidence strings name real files/symbols. ──────────
MATURITY: List[Dict[str, str]] = [
    {
        "id": "agentic",
        "item": "Agentic AI — multi-step plans, autonomous execution, self-correction",
        "status": "partial",
        "evidence": ("core/reflexion.py:run_pipeline (draft→critique→revise, capped); "
                     "core/automation_engine.py:execute_autonomous_step (SSRF-guarded, risk-gated); "
                     "core/task_runner.py:run_ticket (approved-ticket executor, fail-closed); "
                     "core/sandbox_runner.py:run_with_recalibration (retry + code_fixer, max 2)"),
        "note": ("Bounded agentic loops with real self-correction exist. A fully autonomous "
                 "goal-decomposition planner is honestly on the roadmap — /v1/ask is "
                 "deterministic safety-first routing, not planning, by design."),
    },
    {
        "id": "reasoning",
        "item": "Specialized reasoning — step-by-step before answering",
        "status": "built",
        "evidence": ("core/kimi_client.py reasoning_effort param; core/truth_engine.py:truth_seek "
                     "(generate→audit→revise); core/reflexion.py (factuality/grounding/policy critique); "
                     "core/deep_research.py (plan→retrieve→synthesize)"),
        "note": "Multi-pass structured reasoning is real and pervasive across the engine.",
    },
    {
        "id": "multiagent",
        "item": "Multiagent coordination — specialized agents collaborating",
        "status": "partial",
        "evidence": ("core/submission_consensus.py:consensus_verify (3 independent validators vote, "
                     "tie→human); core/truth_engine.py (generator+auditor pair)"),
        "note": ("Consensus-of-independent-verifiers is real. A live inter-agent message bus is "
                 "roadmap — we do not claim communicating agents we don't have."),
    },
    {
        "id": "mcp_interop",
        "item": "MCP / tool-manifest interoperability for external AI systems",
        "status": "built",
        "evidence": "core/capabilities.py — GET /v1/capabilities/manifest (this pack, GAP-1)",
        "note": ("Machine-readable manifest of the real deterministic tools. Battery cross-checks "
                 "every entry against the live route table — a stale entry fails CI."),
    },
    {
        "id": "rag",
        "item": "RAG / vector databases — grounded retrieval over private data",
        "status": "partial",
        "evidence": ("core/knowledge_base.py:KnowledgeBase (token-IDF excerpt retrieval with source "
                     "paths); core/deep_research.py (multi-provider retrieval + citation dedup); "
                     "curated deterministic packs (finlit, african_history, everyday_services, "
                     "av_consult) with versioned sources"),
        "note": ("Retrieval-grounded answering is real. Embedding/vector-store RAG (pgvector/faiss) "
                 "is roadmap — curated deterministic packs were chosen first because they cannot "
                 "hallucinate a source."),
    },
    {
        "id": "multimodal",
        "item": "Native multimodality — audio/image/video input and output",
        "status": "partial",
        "evidence": ("core/voice_api.py:/v1/voice/speak (TTS streaming out); core/hume_evi.py "
                     "(emotion metadata in, HMAC-verified)"),
        "note": ("Audio-out + emotion-metadata-in are real. STT/vision input on the core engine is "
                 "roadmap — no fake 'we see your images' claims."),
    },
    {
        "id": "efficient_models",
        "item": "Small/efficient models & cost-aware routing",
        "status": "built",
        "evidence": ("core/model_router.py:plan_chain (task-type→cost-ordered provider chain); "
                     "core/kimi_client.py hard cost circuit-breaker checked BEFORE upstream calls; "
                     "core/cost_telemetry.py:enforce_budget (MONTHLY_TOKEN_BUDGET_USD); "
                     "core/capability_router.py (cheapest-adequate-by-class) — activated by GAP-1"),
        "note": ("Cost governance is enforced in code before money can be spent. Edge/ternary "
                 "(BitNet-class) local models are a deployment concern, not an API feature — "
                 "honest note, not a claim."),
    },
    {
        "id": "iam_guardrails",
        "item": "IAM-style guardrails & preemptive protection",
        "status": "built",
        "evidence": ("core/auth.py (JWT HS256, pbkdf2 100k, revocation, login rate-limit); "
                     "core/security_guards.py (production REFUSES to boot with default secrets); "
                     "core/rate_limiter.py (slowapi); core/ssrf_guard.py; core/pii_scrub.py applied "
                     "before LLM calls; core/sandbox_runner.py (AST gate + Docker network=none); "
                     "fail-closed money path (webhook never credits directly → human gate → single "
                     "ledger write)"),
        "note": "The strongest layer of the engine. Guardrails are enforced, not described.",
    },
    {
        "id": "confidential_computing",
        "item": "Confidential computing / privacy isolation",
        "status": "partial",
        "evidence": ("core/db_backup.py:encrypt_bytes (real AES-256-GCM, nonce-prefixed, fail-closed "
                     "key, raw purge in finally); core/rls.py (row-level security)"),
        "note": ("Encryption at rest for backups is real. Hardware enclaves (TEE/SGX) are "
                 "not_applicable at our hosting tier — stated honestly, not faked in software."),
    },
]

# ── MCP-style manifest of the REAL deterministic tools ─────────────────────
_TOOLS: List[Dict[str, Any]] = [
    {"name": "ask", "endpoint": "/v1/ask", "method": "POST",
     "description": "Unified front door: safety-first routing to scam check, services pack, history archive, or an honest knowledge gap.",
     "auth_required": False, "live_data": False},
    {"name": "scam_check", "endpoint": "/v1/finlit/scam-check", "method": "POST",
     "description": "Deterministic scam-pattern analysis of any suspicious message; returns risk band, matched patterns, and questions to ask.",
     "auth_required": False, "live_data": False},
    {"name": "finlit_topics", "endpoint": "/v1/finlit/topics", "method": "GET",
     "description": "Financial-literacy topic index (education, not advice).",
     "auth_required": False, "live_data": False},
    {"name": "history_entries", "endpoint": "/v1/history/entries", "method": "GET",
     "description": "African History Archive — every entry carries verifiable sources.",
     "auth_required": False, "live_data": False},
    {"name": "services_entries", "endpoint": "/v1/services/entries", "method": "GET",
     "description": "Everyday Services Pack — SASSA/SRD/SARS/UIF/NSFAS guides from official sources.",
     "auth_required": False, "live_data": False},
    {"name": "av_consult", "endpoint": "/v1/av/consult", "method": "POST",
     "description": "AV room consultancy: Sabine RT60 acoustics, network sizing, scheduling topology, honest ZAR estimate with disclosed assumptions.",
     "auth_required": False, "live_data": "optional"},
    {"name": "av_proposal_pdf", "endpoint": "/v1/av/proposal", "method": "POST",
     "description": "Real PDF proposal for AV consult inputs (deterministic content-hash document ID).",
     "auth_required": False, "live_data": "optional"},
    {"name": "capability_maturity", "endpoint": "/v1/capabilities/maturity", "method": "GET",
     "description": "The engine's honest self-audit against the modern-AI checklist.",
     "auth_required": False, "live_data": False},
    {"name": "capability_manifest", "endpoint": "/v1/capabilities/manifest", "method": "GET",
     "description": "This manifest — machine-readable tool list for external AI systems.",
     "auth_required": False, "live_data": False},
    {"name": "capability_route", "endpoint": "/v1/capabilities/route", "method": "POST",
     "description": "Cheapest-adequate-model routing verdict for a request (decision only, no upstream call).",
     "auth_required": False, "live_data": False},
    {"name": "companion_chat", "endpoint": "/v1/companion/chat", "method": "POST",
     "description": "Relational companion with durable memory, streaks and trust; 6 modes incl. active-listening.",
     "auth_required": True, "live_data": False},
    {"name": "health", "endpoint": "/v1/health", "method": "GET",
     "description": "Liveness probe — always answers, even DB-less.",
     "auth_required": False, "live_data": False},
]


class RouteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.get("/maturity")
def capability_maturity() -> Dict[str, Any]:
    return {
        "checklist": "modern-ai-capabilities",
        "statuses_allowed": list(_STATUSES),
        "items": MATURITY,
        "honesty_law": ("Every status cites the code that backs it; anything not in the "
                        "codebase is marked roadmap or not_applicable — never claimed."),
    }


@router.get("/manifest")
def capability_manifest() -> Dict[str, Any]:
    return {
        "schema": "luqi.tools/v1 (MCP-style)",
        "generated_from": "static-verified — tests/verify_capabilities.py cross-checks "
                          "every endpoint against the live route table",
        "tools": _TOOLS,
    }


@router.post("/route")
def capability_route(req: RouteRequest) -> Dict[str, Any]:
    """Wraps the dormant capability_router. Decision only — no upstream LLM
    call is made here. Providers without keys are skipped; if nothing
    configured fits, the verdict is an honest refusal that says what is missing."""
    verdict = capability_router.route(req.text)
    return {
        "request_id": verdict.request_id,
        "action": verdict.action,
        "provider": verdict.provider,
        "model": verdict.model,
        "task_class": verdict.cls,
        "reason": verdict.reason,
        "note": "Routing decision only — no upstream call was made or billed.",
    }
