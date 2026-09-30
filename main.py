"""main.py — "LUQI Unified Engine" packages entrypoint (ARCH-RESTRUCTURE-1 Phase 0).

DORMANT BY DESIGN: Railway starts the engine via `bash start.sh` ->
`uvicorn core.main:app` (railway.toml line 19). This entrypoint goes live only
when the user flips the start command (Phase 1, user gate). Until then it is
import-verified by tests/verify_packages_skeleton.py and runnable manually:
    uvicorn main:app --host 0.0.0.0 --port 8000

Deviations from the pasted spec (deliberate, house law):
  * CORS: NO wildcard. allow_origins comes from LUQI_CORS_ORIGINS — wildcard +
    credentials is browser-rejected and banned by the CORS law.
  * The 30% human gate, budget hard-stop, and fail-closed LLM behaviour are
    inherited from the real engine/core modules this facade wires.
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from packages.orchestrator import EngineOrchestrator
from packages.shared.schema import ExecutionRequest, ExecutionResponse

# Real modules behind each logical package (for honest /health probes).
_MODULE_MAP = {
    "sentinel_ai": ["core.hybrid_ai", "core.pii_scrub", "core.ops_journal"],
    "luqi_ai": ["core.pedagogy_engine"],
    "omega_super_ai": ["core.deep_research", "core.model_router"],
    "ai_bridge_pro": ["core.model_router", "core.kimi_client"],
}


def _probe_modules() -> dict:
    """Real import checks — no fake 'ok'. Returns per-package availability."""
    import importlib

    report = {}
    for package, modules in _MODULE_MAP.items():
        missing = []
        for mod in modules:
            try:
                importlib.import_module(mod)
            except Exception as e:
                missing.append(f"{mod} ({type(e).__name__})")
        report[package] = "available" if not missing else f"degraded: {missing}"
    return report


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ai_bridge_pro holds NO global async clients (verified 2026-09-30:
    # model_router/kimi_client create connections per call). Lifespan therefore
    # does the honest thing: log gateway configuration as key-PRESENCE
    # booleans — never values — so operators can see readiness.
    app.state.orchestrator = EngineOrchestrator()
    gateway_keys = {
        "kimi": bool(os.getenv("KIMI_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
    }
    print(f"[LUQI] packages facade up. ai_bridge_pro key presence: {gateway_keys}")
    yield
    # Nothing to close: no pooled async clients exist to leak.
    print("[LUQI] packages facade down.")


app = FastAPI(title="LUQI Unified Engine", version="0.1.0", lifespan=lifespan)

# ---------- CORS (house law: explicit origins, never wildcard+credentials) ----------
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


# ---------- Request ID tracking ----------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    t0 = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Request-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
    return response


# ---------- Endpoints ----------
@app.post("/v1/execute", response_model=ExecutionResponse)
async def execute(request: ExecutionRequest) -> ExecutionResponse:
    orchestrator: EngineOrchestrator = app.state.orchestrator
    return await orchestrator.execute(request)


@app.get("/health")
async def health():
    modules = _probe_modules()
    degraded = any(v != "available" for v in modules.values())
    # Honest contract: "degraded" when any package probe fails — never fake green.
    return {"status": "degraded" if degraded else "healthy", "modules": modules}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
