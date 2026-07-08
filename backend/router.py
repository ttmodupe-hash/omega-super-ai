"""Luqi AI v24 — Unified Router (all endpoints)"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

import backend

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Luqi AI v24",
    description="World-class AI system with multi-agent orchestration, ASI cognitive engine, SaaS platform, Law Studies, Africa-First capabilities, Jobs & Skills, WhatsApp Bot, Government Services, Real-time Collaborative Workspaces, Network & AI Engineering Training Academy, Global Knowledge Academy, Project Management Training, Digital Workspace Training, and 300+ endpoints",
    version="24.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Admin Dashboard ───────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve the admin dashboard."""
    admin_path = Path("web/admin.html")
    if admin_path.exists():
        return HTMLResponse(content=admin_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Admin page not found")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    import backend
    return {
        "status": "healthy",
        "version": backend.__version__,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Chat Endpoints ───────────────────────────────────────────────────

try:
    import backend.chat_endpoints
except Exception as _e:
    logger.warning("Chat endpoints not loaded: %s", _e)


# ── v13 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v13_endpoints
except Exception as _e:
    logger.warning("v13 endpoints not loaded: %s", _e)


# ── v14 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v14_endpoints
except Exception as _e:
    logger.warning("v14 endpoints not loaded: %s", _e)


# ── v15 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v15_endpoints
except Exception as _e:
    logger.warning("v15 endpoints not loaded: %s", _e)


# ── v16 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v16_endpoints
except Exception as _e:
    logger.warning("v16 endpoints not loaded: %s", _e)


# ── v17 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v17_endpoints
except Exception as _e:
    logger.warning("v17 endpoints not loaded: %s", _e)


# ── v18 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v18_endpoints
except Exception as _e:
    logger.warning("v18 endpoints not loaded: %s", _e)


# ── v19 Endpoints (Law Studies) ──────────────────────────────────────

try:
    import backend.v19_endpoints   # Law Studies: legal research, case briefing, contract drafting
except Exception as _e:
    logger.warning("v19 endpoints not loaded: %s", _e)


# ── v20 Endpoints (Africa-First) ─────────────────────────────────────

try:
    import backend.v20_endpoints   # Africa-First: Agriculture, Health, Education, Business, Offline
except Exception as _e:
    logger.warning("v20 endpoints not loaded: %s", _e)


# ── v21 Endpoints ────────────────────────────────────────────────────

try:
    import backend.v21_endpoints   # v21: Jobs & Skills, WhatsApp Bot, Government Services
except Exception as _e:
    logger.warning("v21 endpoints not loaded: %s", _e)


# ── v22 Endpoints (Collaboration) ────────────────────────────────────

try:
    import backend.workspace_collab   # Workspace Collaboration: CRUD, messaging, files, video, presence
except Exception as _e:
    logger.warning("Workspace collaboration endpoints not loaded: %s", _e)

try:
    import backend.workspace_agent    # Workspace AI Agent Worker: @ai mentions, context-aware responses
except Exception as _e:
    logger.warning("Workspace AI agent not loaded: %s", _e)


# ── v23 Endpoints (NetAI Training) ───────────────────────────────────

try:
    import backend.v23_endpoints      # v23: Network & AI Engineering Training Platform
except Exception as _e:
    logger.warning("v23 NetAI training endpoints not loaded: %s", _e)


# ── v24 Endpoints (Knowledge Academy) ────────────────────────────────

try:
    import backend.v24_endpoints      # v24: Global Knowledge Academy, PM Training, Digital Workspace
except Exception as _e:
    logger.warning("v24 endpoints not loaded: %s", _e)


logger.info("Luqi AI v24 router initialized — 300+ endpoints registered")
