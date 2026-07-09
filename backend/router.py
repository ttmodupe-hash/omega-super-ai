"""Luqi AI v24.4.0 — FastAPI Router

Main FastAPI application serving the web UI and all API endpoints.
v14-v24.4 endpoint modules are auto-imported at the bottom to register
their routes on the shared `app` instance.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ── Ensure directories exist ─────────────────────────────────────────
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)
GENERATED_DIR = Path("./generated_images")
GENERATED_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Luqi AI v24.4.0",
    description="World-class AI system with multi-agent orchestration, ASI cognitive engine, SaaS platform, Law Studies, Africa-First capabilities, Jobs & Skills, WhatsApp Bot, Government Services, Real-time Collaborative Workspaces, Network & AI Engineering Training Academy, Global Knowledge Academy, Project Management Training, Digital Workspace Training, Digital Wellness, IT Security Training Academy, and 350+ endpoints. Built by Limitless Telecoms.",
    version="24.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# Middleware
# ═══════════════════════════════════════════════════════════════════

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.0f}ms)")
    return response


# ═══════════════════════════════════════════════════════════════════
# Static Files
# ═══════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("web/index.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return FileResponse("web/admin.html")


@app.get("/wellness", response_class=HTMLResponse)
async def wellness_page():
    return FileResponse("web/wellness.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("web/icons/favicon-32x32.png")


@app.get("/manifest.json")
async def manifest():
    return FileResponse("web/manifest.json")


# ═══════════════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "24.4.0", "timestamp": datetime.utcnow().isoformat()}


# ═══════════════════════════════════════════════════════════════════
# Core API Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """Upload a file."""
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": safe_name, "path": str(file_path), "size": file_path.stat().st_size}


@app.get("/api/download/{filename}")
async def api_download(filename: str):
    """Download a file."""
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=safe_name)


# ═══════════════════════════════════════════════════════════════════
# Chat Endpoints
# ═══════════════════════════════════════════════════════════════════

try:
    from backend.chat import chat_with_ai, stream_chat_with_ai
    logger.info("Chat module loaded successfully")
except Exception as e:
    logger.warning("Chat module not available: %s", e)
    chat_with_ai = None
    stream_chat_with_ai = None


if chat_with_ai:
    @app.post("/api/chat")
    async def api_chat(request: Request):
        try:
            data = json.loads(await request.body())
            result = await chat_with_ai(
                message=data.get("message", ""),
                model=data.get("model"),
                system_prompt=data.get("system_prompt"),
                context=data.get("context"),
                temperature=float(data.get("temperature", 0.7)),
                max_tokens=int(data.get("max_tokens", 2000)),
            )
            return JSONResponse(result)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            logger.error("Chat error: %s", e)
            raise HTTPException(status_code=500, detail="Chat service unavailable")

    @app.post("/api/chat/stream")
    async def api_chat_stream(request: Request):
        try:
            data = json.loads(await request.body())
            async def generate():
                async for chunk in stream_chat_with_ai(
                    message=data.get("message", ""),
                    model=data.get("model"),
                    system_prompt=data.get("system_prompt"),
                    context=data.get("context"),
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")
        except Exception as e:
            logger.error("Stream chat error: %s", e)
            raise HTTPException(status_code=500, detail="Streaming unavailable")


# ═══════════════════════════════════════════════════════════════════
# Financial Analysis Endpoint
# ═══════════════════════════════════════════════════════════════════

try:
    from backend.financial import analyze_financials
    logger.info("Financial module loaded successfully")
except Exception as e:
    logger.warning("Financial module not available: %s", e)
    analyze_financials = None


if analyze_financials:
    @app.post("/api/financial/analyze")
    async def api_financial_analyze(request: Request):
        try:
            data = json.loads(await request.body())
            result = await analyze_financials(
                data=data.get("data", {}),
                analysis_type=data.get("analysis_type", "general"),
                currency=data.get("currency", "USD"),
            )
            return JSONResponse(result)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        except Exception as e:
            logger.error("Financial analysis error: %s", e)
            raise HTTPException(status_code=500, detail="Analysis failed")


# ═══════════════════════════════════════════════════════════════════
# Import all endpoint modules (v14 through v24.4)
# Each module registers its own routes on the shared `app` instance
# ═══════════════════════════════════════════════════════════════════

try:
    import backend.v14_endpoints   # SaaS: subscriptions, developer, website, dashboard
except Exception as _e:
    logger.warning("v14 endpoints not loaded: %s", _e)

try:
    import backend.v15_endpoints   # ASI: cognitive, education, voice, safety, physics
except Exception as _e:
    logger.warning("v15 endpoints not loaded: %s", _e)

try:
    import backend.v16_endpoints   # Production: github, notifications, data_portability
except Exception as _e:
    logger.warning("v16 endpoints not loaded: %s", _e)

try:
    import backend.v17_endpoints   # Captainship & Companionship
except Exception as _e:
    logger.warning("v17 endpoints not loaded: %s", _e)

try:
    import backend.v18_endpoints   # Automotive & Writing Assistant
except Exception as _e:
    logger.warning("v18 endpoints not loaded: %s", _e)

try:
    import backend.v19_endpoints   # Law Studies & Legal AI Assistant
except Exception as _e:
    logger.warning("v19 endpoints not loaded: %s", _e)

try:
    import backend.v20_endpoints   # Africa-First: Agriculture, Health, Education, Business, Offline
except Exception as _e:
    logger.warning("v20 endpoints not loaded: %s", _e)

try:
    import backend.v21_endpoints   # v21: Jobs & Skills, WhatsApp Bot, Government Services
except Exception as _e:
    logger.warning("v21 endpoints not loaded: %s", _e)

try:
    import backend.workspace_collab   # Workspace Collaboration: CRUD, messaging, files, video, presence
except Exception as _e:
    logger.warning("Workspace collaboration endpoints not loaded: %s", _e)

try:
    import backend.workspace_agent    # Workspace AI Agent Worker: @ai mentions, context-aware responses
except Exception as _e:
    logger.warning("Workspace AI agent not loaded: %s", _e)

try:
    import backend.v23_endpoints      # v23: Network & AI Engineering Training Platform
except Exception as _e:
    logger.warning("v23 NetAI training endpoints not loaded: %s", _e)

try:
    import backend.v24_endpoints      # v24: Global Knowledge Academy, PM Training, Digital Workspace
except Exception as _e:
    logger.warning("v24 endpoints not loaded: %s", _e)

try:
    import backend.v24_wellness_endpoints   # v24.3: Digital Wellness - fatigue prevention, Pomodoro, break suggestions
except Exception as _e:
    logger.warning("v24 wellness endpoints not loaded: %s", _e)

try:
    import backend.v24_branding_endpoints   # v24.3: Limitless Telecoms branding API
except Exception as _e:
    logger.warning("v24 branding endpoints not loaded: %s", _e)

try:
    import backend.v24_security_endpoints   # v24.4: IT Security Training Academy - 15 courses, CTF challenges
except Exception as _e:
    logger.warning("v24 security endpoints not loaded: %s", _e)
