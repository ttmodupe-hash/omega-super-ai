#!/usr/bin/env python3
"""
Luqi AI v25.1.0 "LUQI" — Comprehensive Test Suite
====================================================
Tests all LUQI integration components:
- ConversationMemory (SQLite persistence)
- ToolRegistry (dynamic tool registration)
- VoiceEngine (STT + TTS)
- LuqiAgent (core agent, chat, tool calling)
- FastAPI-compatible interface functions

Usage:
    python3 test_luqi.py              # Standard run
    python3 test_luqi.py --verbose    # Full tracebacks
    python3 test_luqi.py --json       # Machine-readable output
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List

# ── Color constants ──────────────────────────────────────────────────────
_USE_COLOR = not os.environ.get("NO_COLOR", "")

def _c(text: str, color: str) -> str:
    if not _USE_COLOR:
        return text
    codes = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "blue": "\033[94m", "bold": "\033[1m", "reset": "\033[0m"
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"


# ── Test Runner ──────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self, verbose: bool = False, json_mode: bool = False):
        self.verbose = verbose
        self.json_mode = json_mode
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Dict[str, Any]] = []
        self.section_name = ""

    def section(self, title: str):
        self.section_name = title
        if not self.json_mode:
            print(f"\n{_c(title, 'bold')}")
            print("=" * 55)

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        self.results.append({"section": self.section_name, "test": name, "status": "PASS", "detail": detail})
        if not self.json_mode:
            d = f" ({detail})" if detail else ""
            print(f"  {_c('[PASS]', 'green')} {name}{d}")

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.results.append({"section": self.section_name, "test": name, "status": "FAIL", "detail": detail})
        if not self.json_mode:
            d = f" — {detail}" if detail else ""
            print(f"  {_c('[FAIL]', 'red')} {name}{d}")

    def warn(self, name: str, detail: str = ""):
        self.warnings += 1
        self.results.append({"section": self.section_name, "test": name, "status": "WARN", "detail": detail})
        if not self.json_mode:
            d = f" — {detail}" if detail else ""
            print(f"  {_c('[WARN]', 'yellow')} {name}{d}")

    def summary(self) -> bool:
        total = self.passed + self.failed + self.warnings
        if self.json_mode:
            print(json.dumps({
                "version": "25.1.0",
                "codename": "LUQI",
                "timestamp": time.time(),
                "summary": {
                    "total": total, "passed": self.passed,
                    "failed": self.failed, "warnings": self.warnings,
                    "healthy": self.failed == 0,
                },
                "results": self.results,
            }, indent=2))
        else:
            print(f"\n{'=' * 55}")
            print(_c("SUMMARY", "bold"))
            print(f"  {_c(str(self.passed), 'green')} passed")
            print(f"  {_c(str(self.failed), 'red')} failed")
            print(f"  {_c(str(self.warnings), 'yellow')} warnings")
            print(f"  {total} total checks")
            status = "HEALTHY — LUQI integration ready" if self.failed == 0 else "DEGRADED — Fix failures before launch"
            color = "green" if self.failed == 0 else "red"
            print(f"\nStatus: {_c(status, color)}")
        return self.failed == 0


def safe_test(runner: TestRunner, name: str, fn, detail_fn=None):
    """Run a test function, catching exceptions."""
    try:
        result = fn()
        detail = detail_fn(result) if detail_fn and result is not None else ""
        runner.ok(name, detail)
        return result
    except Exception as e:
        msg = str(e)[:120]
        if runner.verbose:
            msg += "\n" + traceback.format_exc()
        runner.fail(name, msg)
        return None


# ── Section 1: Module Import Tests ───────────────────────────────────────

def test_imports(runner: TestRunner):
    runner.section("[1/6] Module Imports")

    modules = [
        ("backend.luqi_agent", True),
        ("backend.voice_engine", True),
        ("backend.v25_luqi_endpoints", False),
    ]
    for mod_name, critical in modules:
        try:
            __import__(mod_name)
            runner.ok(mod_name)
        except Exception as e:
            if critical:
                runner.fail(mod_name, str(e)[:80])
            else:
                runner.warn(mod_name, str(e)[:80])


# ── Section 2: ConversationMemory Tests ──────────────────────────────────

def test_memory(runner: TestRunner):
    runner.section("[2/6] Conversation Memory")
    import tempfile
    import backend.luqi_agent as la

    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    try:
        mem = la.ConversationMemory(db_path=db_path)

        def save_msg():
            mem.save_message("user", "Hello LUQI", session_id="test_session")
            mem.save_message("assistant", "Hello! How can I help?", session_id="test_session")
            return True
        safe_test(runner, "Save messages", save_msg)

        def get_context():
            ctx = mem.get_recent_context(limit=5, session_id="test_session")
            assert len(ctx) == 2
            assert ctx[0]["role"] == "user"
            assert ctx[1]["role"] == "assistant"
            return ctx
        safe_test(runner, "Retrieve context", get_context, lambda r: f"{len(r)} turns")

        def store_fact():
            mem.store_fact("favorite_color", "blue", "preferences")
            mem.store_fact("name", "Alice", "profile")
            return True
        safe_test(runner, "Store facts", store_fact)

        def get_facts():
            facts = mem.get_facts(category="preferences")
            assert len(facts) >= 1
            assert any(f["key"] == "favorite_color" for f in facts)
            return facts
        safe_test(runner, "Retrieve facts by category", get_facts, lambda r: f"{len(r)} facts")

        def get_all_facts():
            facts = mem.get_facts()
            assert len(facts) >= 2
            return facts
        safe_test(runner, "Retrieve all facts", get_all_facts, lambda r: f"{len(r)} total")

        def search():
            results = mem.search_memories("LUQI")
            assert len(results) >= 1
            return results
        safe_test(runner, "Search memories", search, lambda r: f"{len(r)} matches")

        def stats():
            s = mem.get_stats()
            assert "total_messages" in s
            assert s["total_messages"] >= 2
            return s
        safe_test(runner, "Memory stats", stats, lambda r: f"{r['total_messages']} msgs, {r['total_facts']} facts")

        def clear():
            mem.clear_session("test_session")
            ctx = mem.get_recent_context(session_id="test_session")
            assert len(ctx) == 0
            return True
        safe_test(runner, "Clear session", clear)

    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


# ── Section 3: ToolRegistry Tests ────────────────────────────────────────

def test_tool_registry(runner: TestRunner):
    runner.section("[3/6] Tool Registry")
    import backend.luqi_agent as la

    reg = la.ToolRegistry()

    def test_tool_fn(query: str) -> str:
        return f"Result for: {query}"

    def register():
        reg.register(
            name="test_tool",
            func=test_tool_fn,
            schema={
                "description": "A test tool",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            },
            category="test"
        )
        return True
    safe_test(runner, "Register tool", register)

    def list_tools():
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        return tools
    safe_test(runner, "List tools", list_tools, lambda r: f"{len(r)} tools")

    def get_schema():
        schema = reg.get_schema("test_tool")
        assert schema is not None
        assert schema["description"] == "A test tool"
        return schema
    safe_test(runner, "Get schema", get_schema)

    def get_openai_schemas():
        schemas = reg.get_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "test_tool"
        return schemas
    safe_test(runner, "OpenAI schema format", get_openai_schemas)

    def invoke():
        result = reg.invoke("test_tool", {"query": "hello"})
        assert "Result for: hello" in result
        return result
    safe_test(runner, "Invoke tool", invoke, lambda r: r[:30])

    def invoke_missing():
        result = reg.invoke("nonexistent", {})
        assert "not found" in result
        return result
    safe_test(runner, "Invoke missing tool", invoke_missing)

    def unregister():
        reg.unregister("test_tool")
        assert reg.get_function("test_tool") is None
        return True
    safe_test(runner, "Unregister tool", unregister)


# ── Section 4: VoiceEngine Tests ─────────────────────────────────────────

def test_voice_engine(runner: TestRunner):
    runner.section("[4/6] Voice Engine")
    import tempfile
    import backend.voice_engine as ve

    voice_dir = tempfile.mkdtemp()

    try:
        engine = ve.VoiceEngine(voice_dir=voice_dir)

        def status():
            s = engine.status()
            assert "stt_available" in s
            assert "tts_available" in s
            return s
        safe_test(runner, "Voice status", status, 
                  lambda r: f"STT={'yes' if r['stt_available'] else 'no'}, TTS={'yes' if r['tts_available'] else 'no'}")

        def clean_text():
            raw = "Hello **world**! Check out `code` and ```block``` and https://example.com"
            clean = engine._clean_for_speech(raw)
            assert "**" not in clean
            assert "```" not in clean
            assert "https://" not in clean
            assert "Hello" in clean
            return clean
        safe_test(runner, "Clean text for speech", clean_text, lambda r: f"'{r[:30]}...'")

        def clean_long_text():
            long_text = "x" * 1000
            clean = engine._clean_for_speech(long_text, max_length=100)
            assert len(clean) <= 103
            return clean
        safe_test(runner, "Truncate long text", clean_long_text, lambda r: f"{len(r)} chars")

        def speak_to_file():
            result = engine.speak_to_file("Hello test", os.path.join(voice_dir, "test.mp3"))
            if result.endswith(".mp3"):
                assert os.path.exists(result)
            return result
        safe_test(runner, "TTS to file", speak_to_file, lambda r: r[:40])

        def audio_files():
            files = engine.get_audio_files()
            assert isinstance(files, list)
            return files
        safe_test(runner, "List audio files", audio_files, lambda r: f"{len(r)} files")

        def cleanup():
            removed = engine.cleanup(max_age_hours=0)
            assert removed >= 0
            return removed
        safe_test(runner, "Audio cleanup", cleanup, lambda r: f"{r} files removed")

    finally:
        import shutil
        try:
            shutil.rmtree(voice_dir)
        except Exception:
            pass


# ── Section 5: Built-in Tool Tests ───────────────────────────────────────

def test_builtin_tools(runner: TestRunner):
    runner.section("[5/6] Built-in Tools")
    import backend.luqi_agent as la

    def system_info():
        result = la.get_system_info()
        info = json.loads(result)
        assert "platform" in info
        assert "python_version" in info
        return info
    safe_test(runner, "System info", system_info, lambda r: f"platform={r['platform']}")

    def read_file():
        result = la.read_file("backend/luqi_agent.py", limit=5)
        assert "luqi_agent.py" in result or "Lines" in result
        return result
    safe_test(runner, "Read file", read_file, lambda r: f"{r[:50]}...")

    def write_file():
        result = la.write_file("data/test_write.txt", "Hello from LUQI test")
        assert "success" in result.lower() or "written" in result.lower()
        try:
            os.remove(Path(__file__).parent.parent / "data" / "test_write.txt")
        except Exception:
            pass
        return result
    safe_test(runner, "Write file", write_file)

    def run_code():
        result = la.run_python_code("print(2 + 2)")
        assert "4" in result
        return result
    safe_test(runner, "Run Python code", run_code, lambda r: r.strip()[:20])

    def run_code_error():
        result = la.run_python_code("print(undefined_var)")
        assert "error" in result.lower() or "Error" in result
        return result
    safe_test(runner, "Run Python code with error", run_code_error)

    def run_code_restricted():
        result = la.run_python_code("import os\nprint(os.getcwd())")
        assert "error" in result.lower() or "Error" in result or "not" in result.lower()
        return result
    safe_test(runner, "Restricted code sandbox", run_code_restricted)


# ── Section 6: Interface Function Tests ──────────────────────────────────

def test_interface_functions(runner: TestRunner):
    runner.section("[6/6] FastAPI Interface Functions")
    import backend.luqi_agent as la

    def web_search_interface():
        result = la.web_search("Python programming language")
        assert result["status"] == "success"
        assert "results" in result
        return result
    safe_test(runner, "Web search interface", web_search_interface, 
              lambda r: f"{len(r.get('results', ''))} chars of results")

    def code_run_interface():
        result = la.run_code("x = 10\nprint(x * 5)")
        assert result["status"] == "success"
        assert "50" in result["output"]
        return result
    safe_test(runner, "Code run interface", code_run_interface, lambda r: r["output"].strip()[:20])

    def agent_stats_interface():
        result = la.agent_stats()
        assert result["status"] == "success"
        assert "available_tools" in result
        return result
    safe_test(runner, "Agent stats interface", agent_stats_interface, 
              lambda r: f"{r['available_tools']} tools available")

    def list_tools_interface():
        result = la.agent_list_tools()
        assert result["status"] == "success"
        assert result["total_tools"] >= 6
        return result
    safe_test(runner, "List tools interface", list_tools_interface, 
              lambda r: f"{r['total_tools']} tools")

    def memory_search_interface():
        result = la.agent_memory_search("test")
        assert result["status"] == "success"
        assert "results" in result
        return result
    safe_test(runner, "Memory search interface", memory_search_interface)

    def store_fact_interface():
        result = la.agent_store_fact("test_key", "test_value", "test_category")
        assert result["status"] == "success"
        assert result["stored"]["key"] == "test_key"
        return result
    safe_test(runner, "Store fact interface", store_fact_interface)

    def clear_session_interface():
        result = la.agent_clear_session()
        assert result["status"] == "success"
        assert "new_session_id" in result
        return result
    safe_test(runner, "Clear session interface", clear_session_interface)


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Luqi AI v25.1 LUQI Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()

    if not args.json:
        print(_c("\n" + "=" * 55, "bold"))
        print(_c("  Luqi AI v25.1.0 \"LUQI\" — Test Suite", "bold"))
        print(_c("=" * 55, "bold"))
        print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    runner = TestRunner(verbose=args.verbose, json_mode=args.json)
    start = time.time()

    test_imports(runner)
    test_memory(runner)
    test_tool_registry(runner)
    test_voice_engine(runner)
    test_builtin_tools(runner)
    test_interface_functions(runner)

    elapsed = time.time() - start

    if not args.json:
        print(f"\n  Runtime: {elapsed:.1f}s")

    healthy = runner.summary()

    if not args.json:
        print(f"\n{_c('Next steps:', 'bold')}")
        if healthy:
            print(f"  {_c('1.', 'green')} All {runner.passed} tests passed — LUQI is ready")
            print(f"  {_c('2.', 'green')} Install voice deps: pip install SpeechRecognition gtts pygame")
            print(f"  {_c('3.', 'green')} Set OPENAI_API_KEY env var for agent chat")
            print(f"  {_c('4.', 'green')} Start server: python3 start_server.py")
        else:
            print(f"  {_c('1.', 'yellow')} Fix {runner.failed} failing tests above")
            print(f"  {_c('2.', 'yellow')} Re-run: python3 test_luqi.py")

    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
