#!/usr/bin/env python3
"""
Luqi AI v25.1.0 "JARVIS" — Enterprise Asynchronous Test Harness
================================================================
Comprehensive test suite validating JARVIS system sub-components:
- SQLite Memory Persistence
- Asynchronous Tool Registration & Orchestration
- Audio Engine Cleaners & Speech Output Verification
- Built-in Code Sandboxing & File I/O Guardrails
- FastAPI Route/Interface Endpoint Contracts
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── Dynamic Module Resolution ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Pytest Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provides a clean temporary database path for SQLite memory testing."""
    return tmp_path / "test_jarvis_memory.db"


@pytest.fixture
def temp_voice_dir(tmp_path: Path) -> Path:
    """Provides an isolated directory for TTS/STT audio output processing."""
    voice_dir = tmp_path / "voice_output"
    voice_dir.mkdir(parents=True, exist_ok=True)
    return voice_dir


@pytest_asyncio.fixture
async def async_api_client() -> AsyncGenerator[AsyncClient, None]:
    """In-memory ASGI client for probing FastAPI interface endpoints."""
    try:
        from backend.main import app
    except ImportError:
        try:
            from backend.router import app
        except ImportError:
            pytest.skip("FastAPI application instance could not be imported.")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


# ── Section 1: Module Import Integrity ───────────────────────────────────

@pytest.mark.parametrize(
    "module_path, is_critical",
    [
        ("backend.jarvis_agent", True),
        ("backend.voice_engine", True),
        ("backend.v25_jarvis_endpoints", False),
    ],
)
def test_module_import_integrity(module_path: str, is_critical: bool) -> None:
    """Validates the availability of core agent components."""
    try:
        __import__(module_path)
    except ImportError as exc:
        if is_critical:
            pytest.fail(f"Critical module '{module_path}' failed to import: {exc}")
        else:
            pytest.skip(f"Optional module '{module_path}' not found: {exc}")


# ── Section 2: ConversationMemory Persistence ────────────────────────────

@pytest.mark.asyncio
async def test_conversation_memory_lifecycle(temp_db_path: Path) -> None:
    """Tests SQLite-backed conversation context tracking, fact storage, and recall."""
    import backend.jarvis_agent as ja

    memory = ja.ConversationMemory(db_path=str(temp_db_path))

    # Save turns
    memory.save_message("user", "Hello JARVIS", session_id="session_alpha")
    memory.save_message("assistant", "Greetings. How may I assist?", session_id="session_alpha")

    # Verify context
    context = memory.get_recent_context(limit=5, session_id="session_alpha")
    assert len(context) == 2, "Failed to retrieve correct turn count from context memory."
    assert context[0]["role"] == "user"
    assert context[1]["role"] == "assistant"

    # Fact storage and category filtration
    memory.store_fact("favorite_theme", "dark", "preferences")
    memory.store_fact("user_alias", "Developer", "profile")

    pref_facts = memory.get_facts(category="preferences")
    assert any(f["key"] == "favorite_theme" for f in pref_facts)

    all_facts = memory.get_facts()
    assert len(all_facts) >= 2

    # Memory Search
    search_results = memory.search_memories("JARVIS")
    assert len(search_results) >= 1

    # Memory Stats & Cleanup
    stats = memory.get_stats()
    assert stats.get("total_messages", 0) >= 2

    memory.clear_session("session_alpha")
    cleared_context = memory.get_recent_context(session_id="session_alpha")
    assert len(cleared_context) == 0


# ── Section 3: ToolRegistry Dynamic Execution ────────────────────────────

def test_tool_registry_registration_and_invocation() -> None:
    """Validates dynamic tool registration, schema translation, and safety boundaries."""
    import backend.jarvis_agent as ja

    registry = ja.ToolRegistry()

    def sample_executor(query: str) -> str:
        return f"Executed query: {query}"

    tool_schema = {
        "description": "Dynamic execution test tool",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }

    # Register
    registry.register(
        name="test_tool",
        func=sample_executor,
        schema=tool_schema,
        category="testing",
    )

    registered_tools = registry.list_tools()
    assert len(registered_tools) == 1
    assert registered_tools[0]["name"] == "test_tool"

    # OpenAI Schema Translation
    openai_schemas = registry.get_openai_schemas()
    assert len(openai_schemas) == 1
    assert openai_schemas[0]["type"] == "function"
    assert openai_schemas[0]["function"]["name"] == "test_tool"

    # Invocation
    result = registry.invoke("test_tool", {"query": "system check"})
    assert "Executed query: system check" in result

    # Nonexistent Invocation Handling
    missing_result = registry.invoke("undefined_tool", {})
    assert "not found" in missing_result.lower()

    # Unregister
    registry.unregister("test_tool")
    assert registry.get_function("test_tool") is None


# ── Section 4: VoiceEngine Sanitization & Speech Verification ───────────

def test_voice_engine_text_cleaning(temp_voice_dir: Path) -> None:
    """Verifies text sanitization pipelines designed for text-to-speech output."""
    import backend.voice_engine as ve

    engine = ve.VoiceEngine(voice_dir=str(temp_voice_dir))
    status = engine.status()
    assert "stt_available" in status
    assert "tts_available" in status

    raw_input = "Hello **Agent**! Code: `print('hi')` and URL: https://example.com"
    sanitized = engine._clean_for_speech(raw_input)

    assert "**" not in sanitized
    assert "`" not in sanitized
    assert "https://" not in sanitized
    assert "Hello" in sanitized

    # Length Limiting
    long_input = "A" * 1000
    truncated = engine._clean_for_speech(long_input, max_length=50)
    assert len(truncated) <= 53


# ── Section 5: Code Sandbox & Built-In Tool Safety ───────────────────────

def test_code_sandbox_execution_and_restrictions(tmp_path: Path) -> None:
    """Verifies that Python code execution runs safely within bounded environments."""
    import backend.jarvis_agent as ja

    # Basic Computation
    valid_output = ja.run_python_code("print(10 + 15)")
    assert "25" in valid_output

    # Error Catching
    error_output = ja.run_python_code("print(undefined_variable_abc)")
    assert "error" in error_output.lower() or "nameerror" in error_output.lower()

    # Restricted Globals Enforcement
    restricted_output = ja.run_python_code("import sys\nprint(sys.version)")
    assert "error" in restricted_output.lower() or "not" in restricted_output.lower()


# ── Section 6: FastAPI Route Endpoint Verification ───────────────────────

@pytest.mark.asyncio
async def test_fastapi_interface_functions(async_api_client: AsyncClient) -> None:
    """Probes status and utility routes via the in-memory ASGI client."""
    import backend.jarvis_agent as ja

    # Test Agent Stats Interface Function
    stats_res = ja.agent_stats()
    assert stats_res.get("status") == "success"
    assert "available_tools" in stats_res

    # Test Memory Store Fact Interface Function
    fact_res = ja.agent_store_fact("ci_test_key", "ci_test_val", "testing")
    assert fact_res.get("status") == "success"
    assert fact_res["stored"]["key"] == "ci_test_key"

    # Test Direct Route Probes if routes exist
    health_response = await async_api_client.get("/v1/health")
    if health_response.status_code == 200:
        assert health_response.json().get("status") in ("ok", "healthy", "success")
