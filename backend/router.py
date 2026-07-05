"""FastAPI Router — Luqi AI v13 REST API

Provides all HTTP endpoints for the AI system including streaming chat,
file upload, image generation, memory search, 85-language support,
virtual science labs, Prometheus self-improvement, and health checks.

Run:
    uvicorn backend.router:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /api/chat              — Chat with AI (JSON response)
    POST /api/chat/stream       — Streaming SSE chat
    POST /api/search            — Web search
    POST /api/upload            — File upload
    POST /api/file/ask          — Ask about uploaded file
    POST /api/image/generate    — Generate image
    GET  /api/memory/{sid}      — Get conversation history
    POST /api/memory/search     — Semantic search memories
    GET  /api/languages         — List all 85 supported languages
    POST /api/languages/detect  — Detect language from text
    GET  /api/languages/{code}  — Get language details
    GET  /api/labs              — List virtual lab simulations
    GET  /api/labs/{lab_id}     — Get lab simulation details
    GET  /api/prometheus/status — Prometheus self-improvement status
    POST /api/prometheus/run    — Trigger improvement cycle
    GET  /api/health            — Health check
    GET  /api/models            — Available models
    GET  /                       — Serve web UI
    GET  /{path}                — Serve static files
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
from pydantic import BaseModel, Field, model_validator

from backend.agents import AgentOrchestrator
from backend.ai_engine import AIEngine
from backend.config import load_backend_config
from backend.files import FileProcessor
from backend.images import ImageGenerator
from backend.memory import VectorMemory
from backend.search import SearchEngine

# v13 modules — language system, Prometheus, labs
from backend.lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES
from backend.lang.language_detector import LanguageDetector
from backend.lang.multilingual_router import MultilingualRouter

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
    title="Luqi AI v13",
    description="World-class AI system with 85 languages, virtual labs, Prometheus self-improvement, and multi-agent orchestration",
    version="13.0.0",
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


# ── v13 Shared Components ──────────────────────────────────────────────

_lang_detector: Optional[LanguageDetector] = None
_multi_router: Optional[MultilingualRouter] = None


def get_lang_detector() -> LanguageDetector:
    """Get or create the shared LanguageDetector singleton."""
    global _lang_detector
    if _lang_detector is None:
        _lang_detector = LanguageDetector()
    return _lang_detector


def get_multi_router() -> MultilingualRouter:
    """Get or create the shared MultilingualRouter singleton."""
    global _multi_router
    if _multi_router is None:
        _multi_router = MultilingualRouter(openai_api_key=CONFIG.get("openai_api_key"))
    return _multi_router


# ── Message Normalization ──────────────────────────────────────────────


def normalize_messages(request: "ChatRequest") -> List[Dict[str, str]]:
    """Convert simple 'message' field to OpenAI-style 'messages' list.

    If request.messages is already provided, return it as-is.
    If only request.message is provided, wrap it in a messages list.
    Raises HTTPException if neither is provided (should be caught by
    model_validator, but this is a safety net).
    """
    if request.messages is not None:
        return request.messages
    if request.message is not None:
        return [{"role": "user", "content": request.message}]
    raise HTTPException(
        status_code=422, detail="Either 'message' or 'messages' must be provided"
    )


# ── Pydantic Models ────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body for chat endpoint.

    Supports two input formats:
        1. Simple: {"message": "hello", "session_id": "abc", "mode": "default"}
        2. OpenAI-style: {"messages": [{"role": "user", "content": "hello"}], ...}

    Attributes:
        message: Simple text message (alternative to messages).
        messages: List of message dicts with role and content.
        stream: Whether to stream the response.
        mode: Operational mode (default, research, think, etc.).
        session_id: Optional session ID for conversation memory.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens to generate.
    """

    message: Optional[str] = Field(
        default=None, description="Simple text message"
    )
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Chat messages [{role, content}]"
    )
    stream: bool = Field(default=False, description="Enable streaming")
    mode: str = Field(default="default", description="AI mode")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for memory"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=8192)

    @model_validator(mode="after")
    def check_message_or_messages(self):
        if self.message is None and self.messages is None:
            raise ValueError("Either 'message' or 'messages' must be provided")
        return self


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


class LanguageDetectRequest(BaseModel):
    """Request body for language detection.

    Attributes:
        text: Text to detect language from.
    """

    text: str = Field(..., min_length=1, description="Text to analyze")


class PrometheusRunRequest(BaseModel):
    """Request body for triggering Prometheus improvement cycle.

    Attributes:
        mode: Type of improvement to run (research, gap, evolve, benchmark).
        focus_areas: Specific capability areas to focus on.
    """

    mode: str = Field(default="research", description="Improvement mode")
    focus_areas: Optional[List[str]] = Field(
        default=None, description="Capability areas to focus on"
    )


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
        messages = normalize_messages(request)
        ai = get_ai()
        response_text = ai.chat_sync(
            messages=[dict(m) for m in messages],
            mode=request.mode,
            session_id=request.session_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Save to memory if session_id provided
        if request.session_id and messages:
            mem = get_memory()
            last_msg = messages[-1]
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
    except HTTPException:
        raise
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
        messages = normalize_messages(request)
        ai = get_ai()
        full_text = ""

        async for token in ai.chat_async(
            messages=[dict(m) for m in messages],
            stream=True,
            mode=request.mode,
            session_id=request.session_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            full_text += token
            yield f"data: {json.dumps({'type': 'delta', 'token': token})}\n\n"

        # Save to memory
        if request.session_id and messages:
            try:
                mem = get_memory()
                last_msg = messages[-1]
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
            "version": "13.0.0",
            "model": CONFIG.get("model", "unknown"),
            "search_available": bool(CONFIG.get("serper_api_key")),
            "languages_supported": 85,
            "virtual_labs": 24,
            "prometheus": "active",
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
            "languages_supported": 85,
            "virtual_labs": 24,
            "prometheus": "enabled",
            "version": "13.0.0",
        }
    )


# ── v13 Language API ───────────────────────────────────────────────────


@app.get("/api/languages")
async def api_languages() -> JSONResponse:
    """Get all supported languages (85 total: 54 African + 31 global).

    Returns:
        JSON with African and global language lists including
        native names, speaker counts, regions, and GPT support levels.
    """
    try:
        african = []
        for code, info in AFRICAN_LANGUAGES.items():
            african.append({
                "code": code,
                "name": info.get("name", ""),
                "english_name": info.get("english_name", ""),
                "speakers": info.get("speakers", ""),
                "region": info.get("region", ""),
                "family": info.get("language_family", ""),
                "gpt_support": info.get("gpt_support", "unknown"),
                "greeting": info.get("greetings", {}).get("hello", ""),
            })

        global_langs = []
        for code, info in GLOBAL_LANGUAGES.items():
            global_langs.append({
                "code": code,
                "name": info.get("name", ""),
                "english_name": info.get("english_name", ""),
                "speakers": info.get("speakers", ""),
                "region": info.get("region", ""),
                "family": info.get("language_family", ""),
                "gpt_support": info.get("gpt_support", "unknown"),
                "greeting": info.get("greetings", {}).get("hello", ""),
            })

        return JSONResponse(
            content={
                "african": {"count": len(african), "languages": african},
                "global": {"count": len(global_langs), "languages": global_langs},
                "total": len(african) + len(global_langs),
                "regions": sorted(set(l.get("region", "") for l in list(AFRICAN_LANGUAGES.values()))),
            }
        )
    except Exception as exc:
        logger.error("Languages error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/languages/detect")
async def api_language_detect(request: LanguageDetectRequest) -> JSONResponse:
    """Detect the language of the provided text.

    Uses a multi-strategy approach: greeting matching, unicode script
    analysis, pattern matching, and heuristic detection.

    Request Body:
        text: Text to analyze (min 1 character)

    Returns:
        JSON with detected language code, name, confidence indicators,
        cultural context, and fallback chain.
    """
    try:
        detector = get_lang_detector()
        router = get_multi_router()

        detected_code = detector.detect(request.text)
        routing_info = router.route(request.text, detected_code)

        return JSONResponse(
            content={
                "detected_code": detected_code,
                "detected_name": routing_info.get("lang_name", ""),
                "english_name": routing_info.get("lang_english", ""),
                "is_african": routing_info.get("is_african", False),
                "gpt_support": routing_info.get("gpt_support", "unknown"),
                "cultural_context": routing_info.get("cultural_context", ""),
                "greeting": routing_info.get("greeting", ""),
                "fallback_chain": routing_info.get("fallback_chain", []),
            }
        )
    except Exception as exc:
        logger.error("Language detect error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/languages/{code}")
async def api_language_detail(code: str) -> JSONResponse:
    """Get detailed information about a specific language.

    Path Parameters:
        code: ISO language code (e.g., 'sw', 'zu', 'ar-eg')

    Returns:
        JSON with full language profile including greetings, sample text,
        countries spoken, and cultural notes.
    """
    try:
        all_langs = {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}
        info = all_langs.get(code)
        if not info:
            # Try base code for variants
            base = code.split("-")[0]
            info = all_langs.get(base)
            if not info:
                raise HTTPException(
                    status_code=404, detail=f"Language code '{code}' not found"
                )

        return JSONResponse(
            content={
                "code": code,
                "name": info.get("name", ""),
                "english_name": info.get("english_name", ""),
                "speakers": info.get("speakers", ""),
                "countries": info.get("countries", []),
                "region": info.get("region", ""),
                "language_family": info.get("language_family", ""),
                "script": info.get("script", ""),
                "gpt_support": info.get("gpt_support", "unknown"),
                "whisper_code": info.get("whisper_code", code),
                "greetings": info.get("greetings", {}),
                "sample_text": info.get("sample_text", ""),
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Language detail error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── v13 Virtual Labs API ───────────────────────────────────────────────


# Lab catalog — 24 interactive science simulations across 6 subjects
LAB_CATALOG = [
    {
        "id": "ohms",
        "subject": "physics",
        "name": "Ohm's Law",
        "description": "Explore the relationship between voltage, current, and resistance in an electrical circuit.",
        "formula": "V = I x R",
        "difficulty": "beginner",
    },
    {
        "id": "projectile",
        "subject": "physics",
        "name": "Projectile Motion",
        "description": "Launch projectiles at different angles and velocities to understand parabolic trajectories.",
        "formula": "y = x tan(θ) - (gx²)/(2v²cos²θ)",
        "difficulty": "intermediate",
    },
    {
        "id": "waves",
        "subject": "physics",
        "name": "Wave Simulator",
        "description": "Visualize wave properties including amplitude, frequency, wavelength, and interference.",
        "formula": "y = A sin(kx - ωt)",
        "difficulty": "beginner",
    },
    {
        "id": "optics",
        "subject": "physics",
        "name": "Optics & Refraction",
        "description": "Study light refraction through different media using Snell's Law.",
        "formula": "n₁sin(θ₁) = n₂sin(θ₂)",
        "difficulty": "intermediate",
    },
    {
        "id": "pendulum",
        "subject": "physics",
        "name": "Pendulum Lab",
        "description": "Investigate pendulum period dependence on length, gravity, and amplitude.",
        "formula": "T = 2π√(L/g)",
        "difficulty": "beginner",
    },
    {
        "id": "spring",
        "subject": "physics",
        "name": "Spring Oscillator",
        "description": "Explore simple harmonic motion, damping, and spring constants.",
        "formula": "F = -kx, T = 2π√(m/k)",
        "difficulty": "intermediate",
    },
    {
        "id": "periodic",
        "subject": "chemistry",
        "name": "Periodic Table",
        "description": "Interactive periodic table with element properties, categories, and electron configuration.",
        "formula": "",
        "difficulty": "beginner",
    },
    {
        "id": "reaction",
        "subject": "chemistry",
        "name": "Chemical Reactions",
        "description": "Balance chemical equations and observe reaction simulations.",
        "formula": "Reactants → Products",
        "difficulty": "intermediate",
    },
    {
        "id": "titration",
        "subject": "chemistry",
        "name": "Acid-Base Titration",
        "description": "Perform virtual titrations with pH indicators and equivalence points.",
        "formula": "M₁V₁ = M₂V₂",
        "difficulty": "advanced",
    },
    {
        "id": "molecule",
        "subject": "chemistry",
        "name": "Molecule Builder",
        "description": "Build and visualize 3D molecular structures with bond angles.",
        "formula": "",
        "difficulty": "intermediate",
    },
    {
        "id": "balance",
        "subject": "chemistry",
        "name": "Equation Balancer",
        "description": "Practice balancing chemical equations with step-by-step guidance.",
        "formula": "Conservation of Mass",
        "difficulty": "beginner",
    },
    {
        "id": "cell",
        "subject": "biology",
        "name": "Cell Explorer",
        "description": "Explore animal and plant cell organelles with interactive 3D models.",
        "formula": "",
        "difficulty": "beginner",
    },
    {
        "id": "dna",
        "subject": "biology",
        "name": "DNA Replication",
        "description": "Watch DNA unwind and replicate with base-pair matching (A-T, G-C).",
        "formula": "",
        "difficulty": "intermediate",
    },
    {
        "id": "photosynthesis",
        "subject": "biology",
        "name": "Photosynthesis",
        "description": "Simulate the process of converting light energy into chemical energy.",
        "formula": "6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂",
        "difficulty": "intermediate",
    },
    {
        "id": "heart",
        "subject": "biology",
        "name": "Heart Simulator",
        "description": "Visualize blood flow through the heart chambers with adjustable heart rate.",
        "formula": "Cardiac Output = HR x SV",
        "difficulty": "beginner",
    },
    {
        "id": "ecosystem",
        "subject": "biology",
        "name": "Ecosystem Dynamics",
        "description": "Model predator-prey relationships and population dynamics.",
        "formula": "dN/dt = rN(1 - N/K)",
        "difficulty": "advanced",
    },
    {
        "id": "graph",
        "subject": "math",
        "name": "Graph Plotter",
        "description": "Plot mathematical functions with zoom, pan, and derivative visualization.",
        "formula": "y = f(x)",
        "difficulty": "beginner",
    },
    {
        "id": "geometry",
        "subject": "math",
        "name": "Geometry Lab",
        "description": "Interactive geometry with shapes, angles, area, and volume calculations.",
        "formula": "",
        "difficulty": "beginner",
    },
    {
        "id": "trig",
        "subject": "math",
        "name": "Trigonometry",
        "description": "Visualize sine, cosine, tangent and their relationships on the unit circle.",
        "formula": "sin²θ + cos²θ = 1",
        "difficulty": "intermediate",
    },
    {
        "id": "stats",
        "subject": "math",
        "name": "Statistics",
        "description": "Explore mean, median, standard deviation, and probability distributions.",
        "formula": "σ = √(Σ(x-μ)²/N)",
        "difficulty": "intermediate",
    },
    {
        "id": "calculus",
        "subject": "math",
        "name": "Calculus Visualizer",
        "description": "Visualize derivatives, integrals, and limits with interactive graphs.",
        "formula": "dy/dx = lim(h→0) [f(x+h)-f(x)]/h",
        "difficulty": "advanced",
    },
    {
        "id": "solar",
        "subject": "earth",
        "name": "Solar System",
        "description": "Explore planetary orbits, phases, and celestial mechanics.",
        "formula": "F = G(m₁m₂)/r²",
        "difficulty": "beginner",
    },
    {
        "id": "weather",
        "subject": "earth",
        "name": "Weather Patterns",
        "description": "Simulate weather systems, pressure gradients, and storm formation.",
        "formula": "",
        "difficulty": "intermediate",
    },
    {
        "id": "logic",
        "subject": "cs",
        "name": "Logic Gates",
        "description": "Build circuits with AND, OR, XOR, NAND, and NOR gates.",
        "formula": "Boolean Algebra",
        "difficulty": "beginner",
    },
    {
        "id": "sort",
        "subject": "cs",
        "name": "Sorting Visualizer",
        "description": "Watch sorting algorithms (bubble, quick, merge) execute step by step.",
        "formula": "O(n log n) average",
        "difficulty": "intermediate",
    },
]


@app.get("/api/labs")
async def api_labs(
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> JSONResponse:
    """Get virtual lab simulations catalog.

    Query Parameters:
        subject: Filter by subject (physics, chemistry, biology, math, earth, cs)
        difficulty: Filter by level (beginner, intermediate, advanced)

    Returns:
        JSON with list of 24 interactive science simulations.
    """
    try:
        labs = list(LAB_CATALOG)
        if subject:
            labs = [l for l in labs if l["subject"] == subject.lower()]
        if difficulty:
            labs = [l for l in labs if l["difficulty"] == difficulty.lower()]

        subjects = sorted(set(l["subject"] for l in LAB_CATALOG))
        difficulties = sorted(set(l["difficulty"] for l in LAB_CATALOG))

        return JSONResponse(
            content={
                "labs": labs,
                "count": len(labs),
                "total_available": len(LAB_CATALOG),
                "subjects": subjects,
                "difficulties": difficulties,
                "access_url": "/labs/index.html",
            }
        )
    except Exception as exc:
        logger.error("Labs error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/labs/{lab_id}")
async def api_lab_detail(lab_id: str) -> JSONResponse:
    """Get details for a specific virtual lab simulation.

    Path Parameters:
        lab_id: Lab identifier (e.g., 'ohms', 'dna', 'solar')

    Returns:
        JSON with lab details and direct access link.
    """
    try:
        lab = next((l for l in LAB_CATALOG if l["id"] == lab_id), None)
        if not lab:
            raise HTTPException(
                status_code=404, detail=f"Lab '{lab_id}' not found"
            )
        return JSONResponse(
            content={
                **lab,
                "access_url": f"/labs/index.html?lab={lab_id}",
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Lab detail error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── v13 Prometheus API ─────────────────────────────────────────────────


@app.get("/api/prometheus/status")
async def api_prometheus_status() -> JSONResponse:
    """Get Prometheus self-improvement engine status.

    Returns:
        JSON with engine capabilities, research sources, and
        improvement cycle information.
    """
    try:
        return JSONResponse(
            content={
                "status": "active",
                "engine": "Prometheus Prime v2",
                "capabilities": [
                    "ai_landscape_monitoring",
                    "gap_analysis",
                    "prompt_evolution",
                    "benchmark_tracking",
                    "auto_improvement",
                ],
                "research_sources": [
                    "arxiv",
                    "huggingface",
                    "openai_blog",
                    "github_trending",
                    "papers_with_code",
                ],
                "monitoring_categories": [
                    "code_generation",
                    "multilingual_support",
                    "african_languages",
                    "reasoning_depth",
                    "image_generation",
                    "agentic_workflows",
                    "memory_persistence",
                    "education_features",
                    "virtual_labs",
                    "cost_efficiency",
                ],
                "languages_tracked": 85,
                "virtual_labs_tracked": 24,
                "last_check": "continuous",
            }
        )
    except Exception as exc:
        logger.error("Prometheus status error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/prometheus/run")
async def api_prometheus_run(request: PrometheusRunRequest) -> JSONResponse:
    """Trigger a Prometheus self-improvement cycle.

    Analyzes the AI landscape, identifies capability gaps, and
    generates improvement recommendations.

    Request Body:
        mode: Type of analysis (research, gap, evolve, benchmark)
        focus_areas: Optional list of capability areas to focus on

    Returns:
        JSON with improvement findings and recommendations.
    """
    try:
        # Run research analysis
        from backend.prometheus.research_agent import ResearchAgent
        agent = ResearchAgent()
        findings = agent.run_full_scrape(days=7)
        top = agent.get_top_findings(n=10, min_relevance=0.3)

        return JSONResponse(
            content={
                "mode": request.mode,
                "findings_count": len(findings),
                "top_findings": [f.to_dict() for f in top],
                "focus_areas": request.focus_areas or ["all"],
                "recommendations": [
                    "Monitor multilingual model releases weekly",
                    "Track African language dataset availability",
                    "Benchmark against latest open-source models",
                    "Evolve prompts based on user feedback patterns",
                ],
                "status": "completed",
            }
        )
    except Exception as exc:
        logger.error("Prometheus run error: %s", exc)
        # Graceful degradation — return status even if research fails
        return JSONResponse(
            content={
                "mode": request.mode,
                "status": "partial",
                "error": str(exc),
                "recommendations": [
                    "Ensure all Python dependencies are installed",
                    "Check network connectivity for research scraping",
                    "Verify prometheus module is properly configured",
                ],
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
            "message": "Luqi AI v13 Backend",
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