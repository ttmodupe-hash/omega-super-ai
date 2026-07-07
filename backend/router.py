"""Luqi AI v20 — FastAPI Router

Main FastAPI application serving the web UI and all API endpoints.
v13-v20 endpoint modules are auto-imported at the bottom to register
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
    title="Luqi AI v20",
    description="World-class AI system with multi-agent orchestration, ASI cognitive engine, SaaS platform, Law Studies, Africa-First capabilities, and 195+ endpoints",
    version="20.0.0",
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
# v13 Core Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI (index.html)."""
    index_path = Path("web/index.html")
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Luqi AI v20</h1><p>Frontend not found. Place web/index.html</p>")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
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

@app.post("/api/chat")
async def api_chat(request: Request):
    """Standard chat endpoint."""
    try:
        data = json.loads(await request.body())
        from backend.chat import chat_with_ai
        response = chat_with_ai(
            message=data.get("message", ""),
            history=data.get("history", []),
            mode=data.get("mode", "default"),
        )
        return JSONResponse({"response": response})
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def api_chat_stream(request: Request):
    """Streaming chat endpoint."""
    try:
        data = json.loads(await request.body())
        from backend.chat import stream_chat_with_ai

        async def event_generator():
            async for chunk in stream_chat_with_ai(
                message=data.get("message", ""),
                history=data.get("history", []),
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error("Stream chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── File Upload & Processing ─────────────────────────────────────────

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """Upload and process a file (PDF, image, doc, txt)."""
    try:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        from backend.files import process_file
        result = process_file(str(file_path))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Upload error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Image Generation ─────────────────────────────────────────────────

@app.post("/api/image/generate")
async def api_generate_image(request: Request):
    """Generate an image from a text prompt."""
    try:
        data = json.loads(await request.body())
        from backend.images import generate_image
        result = generate_image(
            prompt=data.get("prompt", ""),
            size=data.get("size", "1024x1024"),
        )
        return JSONResponse(result)
    except Exception as e:
        logger.error("Image generation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Search ───────────────────────────────────────────────────────────

@app.post("/api/search")
async def api_search(request: Request):
    """Perform a web search."""
    try:
        data = json.loads(await request.body())
        from backend.search import web_search
        results = web_search(data.get("query", ""))
        return JSONResponse({"results": results})
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory ───────────────────────────────────────────────────────────

@app.post("/api/memory/save")
async def api_memory_save(request: Request):
    """Save a memory entry."""
    try:
        data = json.loads(await request.body())
        from backend.memory import save_memory
        save_memory(data.get("text", ""), data.get("metadata", {}))
        return JSONResponse({"status": "saved"})
    except Exception as e:
        logger.error("Memory save error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def api_memory_search(request: Request):
    """Search memory entries."""
    try:
        data = json.loads(await request.body())
        from backend.memory import search_memory
        results = search_memory(data.get("query", ""), data.get("limit", 5))
        return JSONResponse({"results": results})
    except Exception as e:
        logger.error("Memory search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Financial ────────────────────────────────────────────────────────

@app.post("/api/financial/analyze")
async def api_financial_analyze(request: Request):
    """Analyze financial data."""
    try:
        data = json.loads(await request.body())
        from backend.financial import analyze_financials
        result = analyze_financials(data.get("data", {}))
        return JSONResponse(result)
    except Exception as e:
        logger.error("Financial analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Static Files ─────────────────────────────────────────────────────

@app.get("/web/{filename}")
async def serve_web_file(filename: str):
    """Serve static web files."""
    file_path = Path(f"web/{filename}")
    if file_path.exists():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")


# ── v14-v20 Endpoint Module Imports ──────────────────────────────────
# These modules import `app` from backend.router and register their
# endpoints using @app decorators.

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
