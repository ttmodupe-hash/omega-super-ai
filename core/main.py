
"""
OMEGA-LUQI AI Unified Engine (core/main.py) v2.0.0
Merged from the OMEGA AI baseline and the Project Bug Fixes stream:

- FastAPI orchestrator with strict 30% Human-in-the-Loop gate
- PostgreSQL persistence via SQLAlchemy v2 (lazy-loaded at startup)
- Real-time WebSocket terminal streaming (core/term_websocket.py)
- PWA static asset serving for African low-bandwidth nodes

Design rule: importing this module requires only fastapi + pydantic.
Docker and Postgres are runtime dependencies, never import-time ones.

Run:  uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import uuid
from enum import Enum
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .term_websocket import router as terminal_router, terminal_manager, get_sandbox_manager
from .kimi_gateway import router as kimi_router
from .kimi_plugins import router as kimi_plugins_router
from .action_engine import router as action_router
from .dev_agent import router as dev_router
from .consumer_shield import router as shield_router
from .tax_matrix import router as tax_router
from .auth import router as auth_router, LuqiAuthManager
from .payment_hub import payment_router
from .security_guards import enforce_production_guards
from .admin_auth import API_KEY_NAME, api_key_header, verify_admin
from .notifications import notify_gate_lock
from .db_backup import backup_router
from .token_status import router as token_status_router
from .model_router import router as model_router
from .academic_sources import router as literature_router
from .geocoding import router as geocoding_router
from .tool_router import router as tool_router
from .free_geo_apis import router as free_geo_router
from .memory import router as memory_router
from .feedback import router as feedback_router
from .hybrid_ai import router as hybrid_router
from .knowledge_base import router as kb_router
from .ops_metrics import router as ops_router
from .cost_telemetry import router as cost_router
from .free_knowledge import router as free_knowledge_router
from .api_registry import router as registry_router
from .skill_engine import router as skill_router
from .context_sync import router as sync_router
from .hume_evi import router as hume_router
from .portability import router as portability_router
from .dead_mans_switch import router as legacy_router
from .credential_verification import router as credentials_router
from .submission_consensus import router as consensus_router
from .spatial_telemetry import router as spatial_router
from .feature_flags import router as feature_flags_router
from .health_sources import router as health_router
from .research_sources import router as research_router
from .payment_routers import regional_payment_router
from .mesh_relay import router as mesh_relay_router
from .self_healing import router as self_healing_router
from .automation_engine import automation_router
from .voice_api import router as voice_router
from .pedagogy_engine import pedagogy_router
from .companion_engine import companion_router
from .stripe_payments import stripe_router
from .finlit import router as finlit_router
from .african_history import router as african_history_router
from .everyday_services import router as everyday_services_router
from .reflexion import router as reflexion_router
from .citations import router as citations_router
from .deep_research import router as deep_research_router
from .i18n import router as i18n_router
from .prometheus import router as prometheus_router, metrics_middleware
from .adaptive_learning import router as adaptive_router
from .sovereign_core import sovereign_router
from .integrity_engine import integrity_router
from .universal_learning import universal_router
from .sandbox_reaper import reaper_loop
from .self_diagnose import router as self_diagnose_router
from .ops_approvals import router as approvals_router
from .task_runner import router as task_runner_router
import asyncio as _asyncio
from .webhooks import webhook_router
from .resource_caps import enforce_free_tier_resource_caps
from .wallet_service import credit_ledger_for_task, WalletCreditError, is_wallet_task
from .main_types import TaskStatus, LuqiState
from .state_store import get_state_store
from .kimi_gateway import KIMI_MODEL

app = FastAPI(title="OMEGA-Luqi Unified AI Sovereign Engine", version="5.36.0")

# ---------- CORS for distributed African educational nodes ----------
# NOTE: allow_origins=["*"] combined with allow_credentials=True is rejected by
# browsers - credentialed requests cannot use a wildcard origin. Configure the
# real origins via LUQI_CORS_ORIGINS (comma-separated).
_cors_origins = [o.strip() for o in os.getenv(
    "LUQI_CORS_ORIGINS", "http://localhost:8000,http://localhost:8080"
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Persistence Layer (lazy) ----------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://luqi:luqi@localhost:5432/luqi_ai",
)


@app.on_event("startup")
def init_db() -> None:
    """Boot guards first (refuse insecure production), then create tables."""
    enforce_production_guards()
    try:
        from sqlalchemy import create_engine
        from .models import Base
        from . import enterprise_models, companion_models, reflexion_models, i18n_models  # noqa: F401 - registers tables on shared Base

        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        from .sqlite_wal import configure_sqlite_engine
        configure_sqlite_engine(engine)
        Base.metadata.create_all(engine)
        app.state.db_engine = engine
        print("[OMEGA-LUQI] Database layer initialised.")
        # Free-provider dispatch front (owning adapters registered once)
        from .api_registry import _register_all_dispatches
        _register_all_dispatches()
        # Idle sandbox recycling: frees RAM from abandoned free-tier labs
        _asyncio.get_event_loop().create_task(
            reaper_loop(terminal_manager, get_sandbox_manager()))
        # Adaptive-learning nudge daemon: GOVERNED — only when explicitly enabled
        if os.getenv("LUQI_ADAPTIVE_NUDGES") == "1":
            from .adaptive_learning import run_proactive_checkin_daemon
            _asyncio.get_event_loop().create_task(run_proactive_checkin_daemon())
            print("[OMEGA-LUQI] Adaptive nudge daemon enabled (LUQI_ADAPTIVE_NUDGES=1).")
    except Exception as e:
        print(f"[OMEGA-LUQI] Database layer unavailable ({e}). API routes remain active.")


# ---------- Security / Human-in-the-Loop Gate ----------
CRITICAL_ACTIONS = {
    "process_payment", "modify_api_limits", "deploy_heavy_infrastructure",
    "submit_government_filing",  # tax/filing engine halts here (tax_matrix.py)
    "execute_digital_legacy",     # dead_mans_switch: directives execute only via release
}


STATE_DB = get_state_store()  # memory by default; redis when STATE_BACKEND=redis


# ---------- API Routes ----------
@app.get("/v1/health")
async def health():
    return {"service": "omega-luqi-ai", "status": "operational", "version": "5.36.0"}


@app.post("/v1/agent/execute", response_model=LuqiState)
async def route_agent_workflow(state: LuqiState, request: Request):
    """Autonomous-safe work completes instantly; critical work halts at the human gate."""
    # Free-tier resource perimeter: subsidized tiers get a capped daily
    # allocation of AUTONOMOUS sessions (critical/gate actions exempt).
    enforce_free_tier_resource_caps(
        student_id=str(state.payload.get("student_id", "anonymous")),
        tier=state.student_tier,
        action_type=state.action_type,
        critical_actions=CRITICAL_ACTIONS,
        request=request,
    )
    if state.action_type in CRITICAL_ACTIONS:
        state.status = TaskStatus.PENDING_HUMAN_APPROVAL
        state.required_human_action = (
            f"Human verification required to authorize: {state.payload.get('item', 'unknown')}"
        )
        notify_gate_lock(state)  # alert admin: something awaits sign-off
    else:
        state.status = TaskStatus.COMPLETED

    STATE_DB.set(state.task_id, state)
    return state


@app.post("/v1/human/override/{task_id}", response_model=LuqiState)
async def human_intervention_override(
    request: Request,
    task_id: uuid.UUID,
    approve: bool,
    payment_credentials: Optional[str] = None,
    is_authenticated: bool = Depends(verify_admin),
):
    """The 30% human gate. Admin must authenticate to release or reject a halted task."""
    current = STATE_DB.get(task_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Target tracking transaction state not found.")

    if current.status != TaskStatus.PENDING_HUMAN_APPROVAL:
        raise HTTPException(status_code=400, detail="Transaction is not locked at a human gateway.")

    if not approve:
        current.status = TaskStatus.REJECTED
        current.required_human_action = "Rejected by administrator."
        _write_audit_record(request, current, TaskStatus.REJECTED)
        return current

    # Gateway-verified wallet tasks settle via the ledger hook - their Paystack
    # reference IS the credential. Legacy process_payment tasks still require
    # fresh human-supplied credentials at release.
    if current.action_type == "process_payment" and not is_wallet_task(current):
        if not payment_credentials:
            raise HTTPException(status_code=400, detail="Payment authorization token missing.")
        current.payload["secure_token"] = "ENCRYPTED_VIA_HUMAN_INTERVENTION"

    # Wallet settlement BEFORE release: if the ledger write fails, the gate
    # stays locked - no settlement without a written ledger row (fail-closed).
    if is_wallet_task(current):
        try:
            new_balance = credit_ledger_for_task(current, getattr(app.state, "db_engine", None))
            current.payload["settled_balance"] = new_balance
        except WalletCreditError as e:
            raise HTTPException(status_code=503, detail=f"Gate release blocked: {e}")

    current.status = TaskStatus.APPROVED
    current.required_human_action = None
    current.status = TaskStatus.COMPLETED
    _write_audit_record(request, current, TaskStatus.APPROVED)
    return current




_SNAPSHOT_VALUE_LIMIT = 2048  # chars per payload value before truncation (audit row hygiene)


def _safe_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Cap oversized values before they hit the audit table (JSON blobs from
    compiled blueprints etc.). Small values pass through untouched."""
    safe = {}
    for k, v in payload.items():
        s = str(v)
        safe[k] = s if len(s) <= _SNAPSHOT_VALUE_LIMIT else s[:_SNAPSHOT_VALUE_LIMIT] + "...[truncated]"
    return safe


def _write_audit_record(request: Request, task, released_status) -> None:
    """Best-effort, non-fatal audit write for every gate release/rejection.

    The gate NEVER depends on the database being up - if the write fails,
    the decision still stands and the failure is logged to the journal."""
    engine = getattr(app.state, "db_engine", None)
    if engine is None:
        return
    try:
        import hashlib
        from sqlalchemy.orm import Session
        from .enterprise_models import SystemAuditLog, ApprovalStatus

        raw_key = request.headers.get("X-Luqi-Admin-Auth", "unknown")
        log = SystemAuditLog(
            task_id=task.task_id,
            operator_identity=hashlib.sha256(raw_key.encode()).hexdigest(),
            action_type=task.action_type.upper(),
            status=ApprovalStatus(released_status.value),
            payload_snapshot={"payload": task.payload, "student_tier": task.student_tier},
            ip_address_origin=request.client.host if request.client else "unknown",
        )
        with Session(engine) as session:
            session.add(log)
            session.commit()
    except Exception as e:
        print(f"[OMEGA-LUQI] Audit write failed (non-fatal, decision unaffected): {e}")



# ---------- Prometheus request telemetry (best-effort, never breaks business path) ----------
app.middleware("http")(metrics_middleware)


# ---------- Sovereign RLS Context Interceptor ----------
@app.middleware("http")
async def inject_sovereign_database_context(request, call_next):
    """Extract the JWT country claim and attach it to the request state.

    DB-backed endpoints bind it per-transaction via core/rls.attach_rls_context.
    Unauthenticated/undecodable tokens -> empty string -> RLS policies yield
    zero visible rows (fail-closed)."""
    user_country = ""
    authorization: str = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        try:
            class _Creds:
                credentials = authorization.split(" ", 1)[1]
            profile = LuqiAuthManager.verify_session_token(_Creds())
            user_country = profile.country_code.upper()[:3]
        except Exception:
            pass  # empty context = deny-by-default under RLS
    request.state.user_country = user_country
    return await call_next(request)


@app.get("/v1/companion/status")
async def companion_status():
    """Public, secret-free heartbeat for the Jarvis avatar: counts only.
    The companion enters 'alert' whenever anything sits at the 30% gate."""
    pending = [t for t in get_state_store().all()
               if t.status == TaskStatus.PENDING_HUMAN_APPROVAL]
    degraded = len(pending) > 0
    return {"pending_gate_count": len(pending), "status": "alert" if degraded else "operational"}

# ---------- Ops Cockpit Feeds (admin-gated) ----------
@app.get("/v1/monitor/telemetry")
async def fetch_live_system_metrics(is_authenticated: bool = Depends(verify_admin)):
    """Secure data feed for the Master Operations Cockpit (static/dashboard.html)."""
    active_sandboxes = None
    sandbox_engine_error = None
    try:
        from .term_websocket import get_sandbox_manager
        client = get_sandbox_manager().client
        active_sandboxes = len(client.containers.list(filters={"name": "luqi-lab-"}))
    except Exception as e:
        # Honest degradation - the dashboard shows "engine offline", never a fake count
        sandbox_engine_error = str(e)

    pending = [t for t in get_state_store().all()
               if t.status == TaskStatus.PENDING_HUMAN_APPROVAL]

    return {
        "system_status": "healthy" if sandbox_engine_error is None else "degraded",
        "active_sandbox_containers": active_sandboxes,
        "sandbox_engine_error": sandbox_engine_error,
        "max_capacity_limit": int(os.getenv("MAX_SANDBOX_CONTAINERS", "500")),
        "kimi_gateway_model": KIMI_MODEL,
        "kimi_reasoning_effort": os.getenv("KIMI_REASONING_EFFORT", "high"),
        "data_sovereignty_node": os.getenv("AWS_REGION", "AWS-af-south-1-CapeTown"),
        "pending_human_gate_count": len(pending),
    }


@app.get("/v1/monitor/gate-queue")
async def fetch_gate_queue(is_authenticated: bool = Depends(verify_admin)):
    """Live view of every task halted at the 30% gate - renders the cockpit queue table."""
    pending = [t for t in get_state_store().all()
               if t.status == TaskStatus.PENDING_HUMAN_APPROVAL]
    return {
        "pending": [
            {
                "task_id": str(t.task_id),
                "student_tier": t.student_tier,
                "action_type": t.action_type,
                "item": t.payload.get("item", t.payload.get("source", "unknown")),
                "required_human_action": t.required_human_action,
                "status": t.status,
            }
            for t in pending
        ]
    }

# ---------- Real-Time Terminal Channel ----------
app.include_router(terminal_router)
app.include_router(kimi_router)
app.include_router(kimi_plugins_router)
app.include_router(action_router)
app.include_router(dev_router)
app.include_router(shield_router)
app.include_router(tax_router)
app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(regional_payment_router)
app.include_router(webhook_router)
app.include_router(mesh_relay_router)
app.include_router(self_healing_router)
app.include_router(automation_router)
app.include_router(voice_router)
app.include_router(pedagogy_router)
app.include_router(companion_router)
app.include_router(stripe_router)
app.include_router(finlit_router)
app.include_router(african_history_router)
app.include_router(everyday_services_router)
app.include_router(reflexion_router)
app.include_router(citations_router)
app.include_router(deep_research_router)
app.include_router(i18n_router)
app.include_router(prometheus_router)
app.include_router(adaptive_router)
app.include_router(sovereign_router)
app.include_router(integrity_router)
app.include_router(universal_router)
app.include_router(backup_router)
app.include_router(token_status_router)
app.include_router(model_router)
app.include_router(literature_router)
app.include_router(geocoding_router)
app.include_router(tool_router)
app.include_router(free_geo_router)
app.include_router(memory_router)
app.include_router(feedback_router)
app.include_router(hybrid_router)
app.include_router(kb_router)
app.include_router(ops_router)
app.include_router(cost_router)
app.include_router(free_knowledge_router)
app.include_router(registry_router)
app.include_router(skill_router)
app.include_router(sync_router)
app.include_router(hume_router)
app.include_router(portability_router)
app.include_router(legacy_router)
app.include_router(credentials_router)
app.include_router(consensus_router)
app.include_router(spatial_router)
app.include_router(feature_flags_router)
app.include_router(health_router)
app.include_router(research_router)
app.include_router(self_diagnose_router)
app.include_router(approvals_router)
app.include_router(task_runner_router)


# ---------- PWA Static Serving (LAST) ----------
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
