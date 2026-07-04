"""FastAPI Router — Luqi AI v12 REST API

Provides all HTTP endpoints for the AI system including streaming chat,
file upload, image generation, memory search, and health checks.

Run:
    uvicorn backend.router:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /api/chat           — Chat with AI (JSON response)
    POST /api/chat/stream    — Streaming SSE chat
    POST /api/search         — Web search
    POST /api/upload         — File upload
    POST /api/file/ask       — Ask about uploaded file
    POST /api/image/generate — Generate image
    GET  /api/memory/{sid}   — Get conversation history
    POST /api/memory/search  — Semantic search memories
    GET  /api/health         — Health check
    GET  /api/models         — Available models
    GET  /                   — Serve web UI
    GET  /{path}             — Serve static files
"""

import json
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from pydantic import BaseModel, Field

from backend.agents import AgentOrchestrator
from backend.ai_engine import AIEngine
from backend.config import load_backend_config
from backend.files import FileProcessor
from backend.images import ImageGenerator
from backend.memory import VectorMemory
from backend.search import SearchEngine

# ── Logging ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

CONFIG = load_backend_config()

# ── FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(
    title="Luqi AI v12",
    description="World-class AI system with multi-agent orchestration",
    version="12.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared Components ──────────────────────────────────────────────────

_ai_engine: Optional[AIEngine] = None
_search_engine: Optional[SearchEngine] = None
_vector_memory: Optional[VectorMemory] = None
_file_processor: Optional[FileProcessor] = None
_image_generator: Optional[ImageGenerator] = None
_agent_orchestrator: Optional[AgentOrchestrator] = None


def get_ai() -> AIEngine:
    """Get or create the shared AIEngine singleton."""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine(CONFIG)
    return _ai_engine


def get_search() -> SearchEngine:
    """Get or create the shared SearchEngine singleton."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine(CONFIG)
    return _search_engine


def get_memory() -> VectorMemory:
    """Get or create the shared VectorMemory singleton."""
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory(CONFIG)
    return _vector_memory


def get_files() -> FileProcessor:
    """Get or create the shared FileProcessor singleton."""
    global _file_processor
    if _file_processor is None:
        _file_processor = FileProcessor(CONFIG)
    return _file_processor


def get_images() -> ImageGenerator:
    """Get or create the shared ImageGenerator singleton."""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator(CONFIG)
    return _image_generator


def get_agents() -> AgentOrchestrator:
    """Get or create the shared AgentOrchestrator singleton."""
    global _agent_orchestrator
    if _agent_orchestrator is None:
        _agent_orchestrator = AgentOrchestrator(CONFIG)
    return _agent_orchestrator


# ── Pydantic Models ────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for chat endpoint.

    Attributes:
        messages: List of message dicts with role and content.
        stream: Whether to stream the response.
        mode: Operational mode (default, research, think, etc.).
        session_id: Optional session ID for conversation memory.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens to generate.
    """

    messages: List[Dict[str, str]] = Field(
        ..., description="Chat messages [{role, content}]"
    )
    stream: bool = Field(default=False, description="Enable streaming")
    mode: str = Field(default="default", description="AI mode")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for memory"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=8192)


class SearchRequest(BaseModel):
    """Request body for search endpoint.

    Attributes:
        query: Search query string.
        max_results: Maximum results to return.
        news: Whether to search news specifically.
    """

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=10, ge=1, le=20)
    news: bool = Field(default=False, description="Search news")


class FileAskRequest(BaseModel):
    """Request body for file Q&A endpoint.

    Attributes:
        filepath: Path to the uploaded file.
        question: Question to ask about the file.
    """

    filepath: str = Field(..., description="Path to uploaded file")
    question: str = Field(..., min_length=1, description="Question")


class ImageGenerateRequest(BaseModel):
    """Request body for image generation.

    Attributes:
        prompt: Image description prompt.
        size: Image dimensions.
        quality: Image quality (standard/hd).
        style: Image style (vivid/natural).
    """

    prompt: str = Field(..., min_length=1, description="Image prompt")
    size: str = Field(default="1024x1024")
    quality: str = Field(default="standard")
    style: str = Field(default="vivid")


class MemorySearchRequest(BaseModel):
    """Request body for memory semantic search.

    Attributes:
        query: Search query text.
        n_results: Number of results.
    """

    query: str = Field(..., min_length=1)
    n_results: int = Field(default=5, ge=1, le=50)


# ── API Endpoints ──────────────────────────────────────────────────────


@app.post("/api/chat")
async def api_chat(request: ChatRequest) -> JSONResponse:
    """Chat with the AI — returns a complete JSON response.

    Request Body:
        messages: List of {role, content} dicts
        stream: false (this endpoint is non-streaming)
        mode: AI mode (default, research, think, mentor, etc.)
        session_id: Optional session for memory
        temperature: 0.0-2.0
        max_tokens: 1-8192

    Returns:
        JSON with response text and metadata.
    """
    try:
        ai = get_ai()
        response_text = ai.chat_sync(
            messages=[dict(m) for m in request.messages],
            mode=request.mode,
            session_id=request.session_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Save to memory if session_id provided
        if request.session_id and request.messages:
            mem = get_memory()
            last_msg = request.messages[-1]
            mem.save_message(
                request.session_id, last_msg.get("role", "user"), last_msg.get("content", "")
            )
            mem.save_message(
                request.session_id, "assistant", response_text
            )

        return JSONResponse(
            content={
                "response": response_text,
                "mode": request.mode,
                "session_id": request.session_id,
            }
        )
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest) -> StreamingResponse:
    """Streaming chat via Server-Sent Events (SSE).

    Returns an event stream with 'delta' events for each token
    and a 'done' event at completion.

    Request Body: Same as /api/chat but stream=true.

    Response:
        text/event-stream with JSON data lines.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        ai = get_ai()
        full_text = ""

        async for token in ai.chat_async(
            messages=[dict(m) for m in request.messages],
            stream=True,
            mode=request.mode,
            session_id=request.session_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            full_text += token
            yield f"data: {json.dumps({'type': 'delta', 'token': token})}\n\n"

        # Save to memory
        if request.session_id and request.messages:
            try:
                mem = get_memory()
                last_msg = request.messages[-1]
                mem.save_message(
                    request.session_id,
                    last_msg.get("role", "user"),
                    last_msg.get("content", ""),
                )
                mem.save_message(request.session_id, "assistant", full_text)
            except Exception as exc:
                logger.error("Memory save error: %s", exc)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/search")
async def api_search(request: SearchRequest) -> JSONResponse:
    """Execute a web search and return structured results.

    Request Body:
        query: Search string
        max_results: 1-20 (default 10)
        news: true for news search

    Returns:
        JSON with results list and markdown-formatted citations.
    """
    try:
        engine = get_search()
        if request.news:
            results = engine.search_news(request.query, request.max_results)
        else:
            results = engine.search(request.query, request.max_results)

        return JSONResponse(
            content={
                "query": request.query,
                "results": results,
                "markdown": engine.to_markdown(results),
                "count": len(results),
            }
        )
    except Exception as exc:
        logger.error("Search error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
) -> JSONResponse:
    """Upload a file for processing.

    Form Data:
        file: The file to upload (max 10MB)

    Returns:
        JSON with saved path, size, and extracted text preview.
    """
    try:
        content = await file.read()
        max_size = int(CONFIG.get("max_upload_size", 10485760))
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content)} bytes (max {max_size})",
            )

        processor = get_files()
        filepath = processor.save_upload(content, file.filename or "upload")

        # Extract text preview
        try:
            text = processor.process_file(filepath)
            preview = text[:2000] if len(text) > 2000 else text
        except Exception as exc:
            preview = f"[Preview unavailable: {exc}]"
            text = ""

        return JSONResponse(
            content={
                "filename": file.filename,
                "path": filepath,
                "size": len(content),
                "preview": preview,
                "length": len(text),
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/file/ask")
async def api_file_ask(request: FileAskRequest) -> JSONResponse:
    """Ask a question about an uploaded file.

    Request Body:
        filepath: Path returned from /api/upload
        question: Your question about the file

    Returns:
        JSON with the AI's answer.
    """
    try:
        processor = get_files()
        answer = processor.answer_from_file(request.filepath, request.question)
        return JSONResponse(
            content={
                "question": request.question,
                "answer": answer,
                "filepath": request.filepath,
            }
        )
    except Exception as exc:
        logger.error("File ask error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/image/generate")
async def api_image_generate(
    request: ImageGenerateRequest,
) -> JSONResponse:
    """Generate an image using DALL-E 3.

    Request Body:
        prompt: Image description
        size: "1024x1024" | "1024x1792" | "1792x1024"
        quality: "standard" | "hd"
        style: "vivid" | "natural"

    Returns:
        JSON with generated image file path.
    """
    try:
        gen = get_images()
        path = gen.generate(
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
        )
        return JSONResponse(
            content={
                "prompt": request.prompt,
                "path": path,
                "size": request.size,
                "quality": request.quality,
            }
        )
    except Exception as exc:
        logger.error("Image generation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/memory/{session_id}")
async def api_memory_get(session_id: str) -> JSONResponse:
    """Get conversation history for a session.

    Path Parameters:
        session_id: The session identifier.

    Returns:
        JSON with list of messages.
    """
    try:
        mem = get_memory()
        history = mem.get_conversation(session_id)
        return JSONResponse(
            content={"session_id": session_id, "messages": history}
        )
    except Exception as exc:
        logger.error("Memory get error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/memory/search")
async def api_memory_search(
    request: MemorySearchRequest,
) -> JSONResponse:
    """Semantic search across all stored memories.

    Request Body:
        query: Search text
        n_results: Number of results (default 5)

    Returns:
        JSON with matching memories.
    """
    try:
        mem = get_memory()
        results = mem.query(request.query, request.n_results)
        return JSONResponse(
            content={"query": request.query, "results": results}
        )
    except Exception as exc:
        logger.error("Memory search error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/health")
async def api_health() -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSON with status and version info.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "version": "12.0.0",
            "model": CONFIG.get("model", "unknown"),
            "search_available": bool(CONFIG.get("serper_api_key")),
        }
    )


@app.get("/api/models")
async def api_models() -> JSONResponse:
    """Get available AI models and configuration.

    Returns:
        JSON with model names and system info.
    """
    return JSONResponse(
        content={
            "chat_model": CONFIG.get("model"),
            "vision_model": CONFIG.get("vision_model"),
            "embedding_model": CONFIG.get("embedding_model"),
            "modes": [
                "default",
                "research",
                "think",
                "mentor",
                "expert",
                "finance",
                "scam",
                "learn",
                "opps",
            ],
            "version": "12.0.0",
        }
    )


# ── Static File Serving ────────────────────────────────────────────────

WEB_DIR = Path(__file__).parent.parent / "web"


@app.get("/")
async def serve_index() -> FileResponse:
    """Serve the main web UI (index.html)."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    # Fallback: return API info if no UI built yet
    return FileResponse(str(index_file)) if index_file.exists() else JSONResponse(
        content={
            "message": "Luqi AI v12 Backend",
            "docs": "/docs",
            "status": "No frontend built yet. Place files in ./web/",
        }
    )


@app.get("/{path:path}")
async def serve_static(request: Request, path: str) -> FileResponse:
    """Serve static files from the web/ directory."""
    file_path = WEB_DIR / path
    # Security: prevent directory traversal
    try:
        file_path.resolve().relative_to(WEB_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")
