"""
Luqi AI v25.1.0 "JARVIS" — Agent Engine Endpoints
===================================================
Extension to v25_endpoints.py adding 15+ new endpoints for:
- Autonomous agent chat with tool calling
- Voice processing (STT + TTS)
- Persistent memory management
- Web search and code execution
- Tool registry inspection

All endpoints registered under /api/v25/jarvis/*
"""

import json
import logging
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.router import app

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  JARVIS AGENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

_jarvis_agent = None
_voice_engine = None


def _get_jarvis():
    global _jarvis_agent
    if _jarvis_agent is None:
        try:
            from backend.jarvis_agent import (
                agent_chat, agent_stats, agent_memory_search,
                agent_memory_facts, agent_store_fact, agent_list_tools,
                agent_clear_session, web_search, run_code,
                agent_voice_listen, agent_speak
            )
            _jarvis_agent = {
                "chat": agent_chat,
                "stats": agent_stats,
                "memory_search": agent_memory_search,
                "memory_facts": agent_memory_facts,
                "store_fact": agent_store_fact,
                "list_tools": agent_list_tools,
                "clear_session": agent_clear_session,
                "web_search": web_search,
                "run_code": run_code,
                "voice_listen": agent_voice_listen,
                "speak": agent_speak,
            }
        except Exception as e:
            logger.error(f"JARVIS agent import failed: {e}")
            _jarvis_agent = {}
    return _jarvis_agent


def _get_voice():
    global _voice_engine
    if _voice_engine is None:
        try:
            from backend.voice_engine import (
                voice_status, voice_listen, voice_speak,
                voice_files, voice_cleanup
            )
            _voice_engine = {
                "status": voice_status,
                "listen": voice_listen,
                "speak": voice_speak,
                "files": voice_files,
                "cleanup": voice_cleanup,
            }
        except Exception as e:
            logger.error(f"Voice engine import failed: {e}")
            _voice_engine = {}
    return _voice_engine


# ── Agent Chat ──────────────────────────────────────────────────────

@app.post("/api/v25/jarvis/chat")
async def api_v25_jarvis_chat(request: Request):
    """Chat with the JARVIS autonomous agent."""
    try:
        j = _get_jarvis()
        if not j:
            raise HTTPException(status_code=503, detail="JARVIS agent not available")
        
        data = json.loads(await request.body())
        result = j["chat"](
            message=data.get("message", ""),
            session_id=data.get("session_id"),
            use_tools=data.get("use_tools", True)
        )
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JARVIS chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/jarvis/stats")
async def api_v25_jarvis_stats():
    """Get JARVIS agent statistics."""
    try:
        j = _get_jarvis()
        if not j or "stats" not in j:
            raise HTTPException(status_code=503, detail="JARVIS agent not available")
        result = j["stats"]()
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JARVIS stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Voice Processing ────────────────────────────────────────────────

@app.get("/api/v25/jarvis/voice/status")
async def api_v25_jarvis_voice_status():
    """Get voice engine status and capabilities."""
    try:
        v = _get_voice()
        if not v or "status" not in v:
            return JSONResponse({
                "status": "unavailable",
                "message": "Voice engine not installed. Run: pip install SpeechRecognition gtts pygame"
            })
        result = v["status"]()
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Voice status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/voice/listen")
async def api_v25_jarvis_voice_listen(request: Request):
    """Listen for voice input and return transcription."""
    try:
        v = _get_voice()
        if not v or "listen" not in v:
            raise HTTPException(status_code=503, detail="Voice engine not available")
        
        data = json.loads(await request.body())
        result = v["listen"](
            timeout=data.get("timeout", 5),
            language=data.get("language", "en-US")
        )
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice listen error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/voice/speak")
async def api_v25_jarvis_voice_speak(request: Request):
    """Convert text to speech."""
    try:
        v = _get_voice()
        j = _get_jarvis()
        
        data = json.loads(await request.body())
        text = data.get("text", "")
        
        if v and "speak" in v:
            result = v["speak"](
                text=text,
                language=data.get("language", "en"),
                accent=data.get("accent", "uk"),
                slow=data.get("slow", False)
            )
        elif j and "speak" in j:
            result = j["speak"](text)
        else:
            raise HTTPException(status_code=503, detail="TTS not available")
        
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice speak error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/voice/interact")
async def api_v25_jarvis_voice_interact(request: Request):
    """Full voice interaction: listen → agent process → speak response."""
    try:
        j = _get_jarvis()
        if not j or "voice_listen" not in j:
            raise HTTPException(status_code=503, detail="Voice agent not available")
        
        data = json.loads(await request.body())
        result = j["voice_listen"](timeout=data.get("timeout", 5))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice interact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/jarvis/voice/files")
async def api_v25_jarvis_voice_files():
    """List generated audio files."""
    try:
        v = _get_voice()
        if not v or "files" not in v:
            return JSONResponse({"status": "success", "files": [], "total_files": 0})
        result = v["files"]()
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Voice files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/voice/cleanup")
async def api_v25_jarvis_voice_cleanup(request: Request):
    """Clean up old audio files."""
    try:
        v = _get_voice()
        if not v or "cleanup" not in v:
            return JSONResponse({"status": "success", "files_removed": 0})
        
        data = json.loads(await request.body())
        result = v["cleanup"](max_age_hours=data.get("max_age_hours", 24))
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Voice cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory Management ───────────────────────────────────────────────

@app.get("/api/v25/jarvis/memory/search")
async def api_v25_jarvis_memory_search(keyword: str):
    """Search conversation memory by keyword."""
    try:
        j = _get_jarvis()
        if not j or "memory_search" not in j:
            raise HTTPException(status_code=503, detail="Memory not available")
        result = j["memory_search"](keyword)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v25/jarvis/memory/facts")
async def api_v25_jarvis_memory_facts(category: Optional[str] = None):
    """Get stored facts about the user."""
    try:
        j = _get_jarvis()
        if not j or "memory_facts" not in j:
            raise HTTPException(status_code=503, detail="Memory not available")
        result = j["memory_facts"](category)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory facts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/memory/fact")
async def api_v25_jarvis_memory_store_fact(request: Request):
    """Store a fact about the user."""
    try:
        j = _get_jarvis()
        if not j or "store_fact" not in j:
            raise HTTPException(status_code=503, detail="Memory not available")
        
        data = json.loads(await request.body())
        result = j["store_fact"](
            key=data.get("key", ""),
            value=data.get("value", ""),
            category=data.get("category", "general")
        )
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Store fact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v25/jarvis/memory/clear")
async def api_v25_jarvis_memory_clear(request: Request):
    """Clear a conversation session."""
    try:
        j = _get_jarvis()
        if not j or "clear_session" not in j:
            raise HTTPException(status_code=503, detail="Memory not available")
        
        data = json.loads(await request.body())
        result = j["clear_session"](data.get("session_id"))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Tool Registry ───────────────────────────────────────────────────

@app.get("/api/v25/jarvis/tools")
async def api_v25_jarvis_tools():
    """List all available tools the agent can use."""
    try:
        j = _get_jarvis()
        if not j or "list_tools" not in j:
            raise HTTPException(status_code=503, detail="Tool registry not available")
        result = j["list_tools"]()
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tools list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Web Search ──────────────────────────────────────────────────────

@app.get("/api/v25/jarvis/search")
async def api_v25_jarvis_search(query: str):
    """Search the web via DuckDuckGo."""
    try:
        j = _get_jarvis()
        if not j or "web_search" not in j:
            raise HTTPException(status_code=503, detail="Web search not available")
        result = j["web_search"](query)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Code Execution ──────────────────────────────────────────────────

@app.post("/api/v25/jarvis/code/run")
async def api_v25_jarvis_code_run(request: Request):
    """Execute Python code in a restricted sandbox."""
    try:
        j = _get_jarvis()
        if not j or "run_code" not in j:
            raise HTTPException(status_code=503, detail="Code runner not available")
        
        data = json.loads(await request.body())
        result = j["run_code"](data.get("code", ""))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


logger.info("JARVIS v25.1.0 endpoints registered: 15+ endpoints for agent, voice, memory, tools")
