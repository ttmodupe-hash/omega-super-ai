"""Luqi AI v25.0.0 — FastAPI Router

Main FastAPI application serving the web UI and all API endpoints.
v13-v25 endpoint modules are auto-imported at the bottom to register
their routes on the shared `app` instance.
v25: Omega AI Prometheus integration — Error Repair, Memory Manager,
Pedagogical Engine, Wisdom, Crypto, Rate Limiting, WebSocket, Vector DB,
Multi-Tenant, Plugin Marketplace, Realtime Prices, Metrics, Email,
Telegram, PDF, Backup, Local LLM, Agent Mesh, Blockchain Audit,
Federated Learning.
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
    title="Luqi AI v25.0.0",
    description="World-class AI system with multi-agent orchestration, ASI cognitive engine, SaaS platform, Law Studies, Africa-First capabilities, Jobs & Skills, WhatsApp Bot, Government Services, Real-time Collaborative Workspaces, Network & AI Engineering Training Academy, Global Knowledge Academy, Project Management Training, Digital Workspace Training, IT Security Training Academy, Digital Wellness, Animated Learning, Accessibility for Deaf Users, and Omega AI Prometheus Engines (Error Repair, Memory Manager, Pedagogical Engine, Wisdom, Crypto, Rate Limiting, WebSocket, Vector DB, Multi-Tenant, Plugin Marketplace, Realtime Prices, Metrics, Email, Telegram, PDF, Backup, Local LLM, Agent Mesh, Blockchain Audit, Federated Learning). 400+ endpoints. Built by Limitless Telecoms.",
    version="25.0.0",
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
    return HTMLResponse("<h1>Luqi AI v25</h1><p>Frontend not found. Place web/index.html</p>")


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
        try:
            from backend.files import FileProcessor
            processor = FileProcessor()
            result = processor.process(str(file_path))
            return JSONResponse({"status": "processed", "result": result, "file": file.filename})
        except ImportError:
            return JSONResponse({
                "status": "uploaded",
                "message": "File uploaded successfully. File processing module not available.",
                "file": file.filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path) if file_path.exists() else 0,
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload error: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ── Image Generation ─────────────────────────────────────────────────

@app.post("/api/image/generate")
async def api_generate_image(request: Request):
    """Generate an image from a text prompt."""
    try:
        data = json.loads(await request.body())
        prompt = data.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=422, detail="Prompt is required")
        try:
            import openai
            client = openai.AsyncOpenAI()
            size = data.get("size", "1024x1024")
            valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
            if size not in valid_sizes:
                size = "1024x1024"
            response = await client.images.generate(
                model=data.get("model", "dall-e-3"),
                prompt=prompt,
                size=size,
                quality=data.get("quality", "standard"),
                n=1,
            )
            image_url = response.data[0].url
            return JSONResponse({"status": "success", "url": image_url, "prompt": prompt})
        except ImportError:
            return JSONResponse({
                "status": "unavailable",
                "message": "Image generation requires OpenAI API key. Configure OPENAI_API_KEY environment variable.",
                "prompt": prompt,
            }, status_code=503)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Image generation error: %s", e)
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


# ── Search ───────────────────────────────────────────────────────────

@app.post("/api/search")
async def api_search(request: Request):
    """Perform a web search."""
    try:
        data = json.loads(await request.body())
        query = data.get("query", "")
        if not query:
            raise HTTPException(status_code=422, detail="Query is required")
        try:
            from backend.search import SearchEngine
            engine = SearchEngine()
            results = engine.search(query)
            return JSONResponse({"status": "success", "query": query, "results": results})
        except ImportError:
            return JSONResponse({
                "status": "fallback",
                "query": query,
                "message": "Search engine module not available. Install dependencies or configure search API.",
                "results": [],
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ── Memory ───────────────────────────────────────────────────────────

@app.post("/api/memory/save")
async def api_memory_save(request: Request):
    """Save a memory entry."""
    try:
        data = json.loads(await request.body())
        text = data.get("text", "")
        if not text:
            raise HTTPException(status_code=422, detail="Text is required")
        try:
            from backend.memory import VectorMemory
            memory = VectorMemory()
            memory_id = memory.add(text, data.get("metadata", {}))
            return JSONResponse({"status": "saved", "id": memory_id})
        except ImportError:
            mem_file = UPLOAD_DIR / "memory_fallback.json"
            memories = []
            if mem_file.exists():
                memories = json.loads(mem_file.read_text(encoding="utf-8"))
            entry = {
                "id": f"mem_{int(time.time())}",
                "text": text,
                "metadata": data.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat(),
            }
            memories.append(entry)
            mem_file.write_text(json.dumps(memories, indent=2), encoding="utf-8")
            return JSONResponse({"status": "saved_fallback", "id": entry["id"]})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory save error: %s", e)
        raise HTTPException(status_code=500, detail=f"Memory save failed: {str(e)}")


@app.post("/api/memory/search")
async def api_memory_search(request: Request):
    """Search memory entries."""
    try:
        data = json.loads(await request.body())
        query = data.get("query", "")
        if not query:
            raise HTTPException(status_code=422, detail="Query is required")
        try:
            from backend.memory import VectorMemory
            memory = VectorMemory()
            results = memory.query(query, data.get("limit", 5))
            return JSONResponse({"status": "success", "query": query, "results": results})
        except ImportError:
            mem_file = UPLOAD_DIR / "memory_fallback.json"
            if not mem_file.exists():
                return JSONResponse({"status": "fallback", "query": query, "results": []})
            memories = json.loads(mem_file.read_text(encoding="utf-8"))
            q_lower = query.lower()
            results = [m for m in memories if q_lower in m.get("text", "").lower()]
            return JSONResponse({"status": "fallback", "query": query, "results": results[:data.get("limit", 5)]})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Memory search error: %s", e)
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")


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


# ── v14-v25 Endpoint Module Imports ──────────────────────────────────
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
    import backend.v24_wellness_endpoints   # v24.3: Digital Wellness
except Exception as _e:
    logger.warning("v24 wellness endpoints not loaded: %s", _e)

try:
    import backend.v24_branding_endpoints   # v24.3: Limitless Telecoms branding API
except Exception as _e:
    logger.warning("v24 branding endpoints not loaded: %s", _e)

try:
    import backend.v24_security_endpoints  # v24.4: IT Security Training Academy
except Exception as _e:
    logger.warning("v24 security endpoints not loaded: %s", _e)

try:
    import backend.v24_autonomous_endpoints  # v24.5: Autonomous Multi-Agent System
except Exception as _e:
    logger.warning("v24 autonomous endpoints not loaded: %s", _e)

try:
    import backend.v25_animation_endpoints  # v25: Animated Practical Learning System
except Exception as _e:
    logger.warning("v25 animation endpoints not loaded: %s", _e)

try:
    import backend.v25_accessibility_endpoints  # v25: Accessibility for Deaf Users
except Exception as _e:
    logger.warning("v25 accessibility endpoints not loaded: %s", _e)

try:
    import backend.v25_endpoints  # v25: Omega AI Prometheus — 20 modules, 50+ endpoints
except Exception as _e:
    logger.warning("v25 Prometheus endpoints not loaded: %s", _e)

# ═══════════════════════════════════════════════════════════════════
# Exception Handlers & Health Monitor
# ═══════════════════════════════════════════════════════════════════

try:
    from backend.exception_handler import register_exception_handlers
    register_exception_handlers(app)
    logger.info("Custom exception handlers registered")
except Exception as _e:
    logger.warning("Exception handlers not registered: %s", _e)

try:
    from backend.health_monitor import register_health_endpoints, ModuleHealthChecker
    register_health_endpoints(app)
    logger.info("Health monitoring endpoints registered")
    try:
        from backend.health_monitor import print_startup_banner
        checker = ModuleHealthChecker()
        status = checker.check_all_modules([
            "backend.router",
            "backend.exception_handler",
            "backend.validators",
            "backend.db_utils",
            "backend.chat",
            "backend.financial",
            "backend.health_monitor",
            "backend.v24_security_endpoints",
            "backend.autonomous_system",
            "backend.alert_system",
            "backend.sandbox_validator",
            "backend.research_engine",
            "backend.dead_mans_switch",
            "backend.v25_endpoints",
        ])
        print_startup_banner(status)
    except Exception as banner_err:
        logger.debug("Startup banner not displayed: %s", banner_err)
except Exception as _e:
    logger.warning("Health monitor not registered: %s", _e)