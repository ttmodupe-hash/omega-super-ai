#!/usr/bin/env python3
"""Omega AI v3.7.0 "Prometheus" — Main CLI Entry Point
The central brain. Start with: python omega_ai.py

v3.7.0 adds: 18 new modules, error repair, memory manager,
pedagogical engine, cross-platform apps, wisdom engine.

Modules: core_brain, wisdom, error_repair, memory_manager,
pedagogical_engine, crypto, rate_limit, ws, vector_db,
multi_tenant, marketplace, prices, metrics, email, telegram,
pdf, backup, local_llm, agent_mesh, blockchain, federated.

Author: Omega AI Team
License: MIT
"""

from __future__ import annotations

import argparse
import atexit
import importlib
import json
import os
import re
import readline
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── VERSION ──────────────────────────────────────────────────────────────────
VERSION = "3.7.0"
CODENAME = "Prometheus"
BUILD_DATE = "2026-07-24"

# ─── PATH SETUP ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ─── DATA DIRECTORY ───────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("OMEGA_DATA_DIR", ".omega_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── MODULE CACHE ─────────────────────────────────────────────────────────────
_MODULE_CACHE: dict[str, Any] = {}


def _load_module(name: str) -> Any:
    """Lazy-load a module with caching."""
    if name not in _MODULE_CACHE:
        try:
            _MODULE_CACHE[name] = importlib.import_module(name)
        except ImportError as e:
            _MODULE_CACHE[name] = None
            if os.environ.get("OMEGA_DEBUG"):
                print(f"[DEBUG] Could not load {name}: {e}")
    return _MODULE_CACHE[name]


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE BRAIN
# ═══════════════════════════════════════════════════════════════════════════════

_brain_instance: Any = None


def get_brain() -> Any:
    """Get or create the OmegaBrain instance."""
    global _brain_instance
    if _brain_instance is None:
        try:
            core_brain = _load_module("core_brain")
            if core_brain:
                _brain_instance = core_brain.OmegaBrain()
            else:
                _brain_instance = _FallbackBrain()
        except Exception as e:
            print(f"[WARN] Brain init failed: {e}")
            _brain_instance = _FallbackBrain()
    return _brain_instance


class _FallbackBrain:
    """Minimal fallback when core_brain is unavailable."""

    def process(self, text: str) -> dict[str, Any]:
        return {"response": f"I received: {text}", "intent": "echo"}

    def chat(self, text: str, **kwargs) -> str:
        return f"Echo: {text}"

    def learn(self, topic: str, data: Any) -> str:
        return f"Learned about {topic}"

    def predict(self, values: list[float]) -> dict[str, Any]:
        avg = sum(values) / len(values) if values else 0
        return {"average": avg, "trend": "stable"}

    def status(self) -> dict[str, Any]:
        return {"status": "fallback", "version": VERSION}


# ═══════════════════════════════════════════════════════════════════════════════
#  CONVERSATION HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

_history: list[dict[str, str]] = []
_history_file = DATA_DIR / "cli_history.json"


def _load_history():
    """Load conversation history from disk."""
    global _history
    if _history_file.exists():
        try:
            _history = json.loads(_history_file.read_text())
        except (json.JSONDecodeError, OSError):
            _history = []


def _save_history():
    """Save conversation history to disk."""
    try:
        _history_file.write_text(json.dumps(_history[-500:], indent=2))
    except OSError:
        pass


def _add_to_history(role: str, content: str):
    """Add an entry to conversation history."""
    _history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(_history) > 1000:
        _history[:] = _history[-500:]


_load_history()
atexit.register(_save_history)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI BANNER
# ═══════════════════════════════════════════════════════════════════════════════


def print_banner():
    """Print the Omega AI banner."""
    term_width = shutil.get_terminal_size().columns
    lines = [
        "",
        "  \u03A9 Omega AI " + f"v{VERSION}" + f" \"{CODENAME}\"",
        "  " + "\u2500" * min(50, term_width - 4),
        f"  Build: {BUILD_DATE} | Modules: 52+ | Endpoints: 60+",
        f"  Data: {DATA_DIR} | PID: {os.getpid()}",
        "  Type /help for commands or chat naturally.",
        "  Type /quit to exit.",
        "",
    ]
    for line in lines:
        print(line)


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_help(args: list[str]) -> str:
    """Show help message."""
    return """
Omega AI Commands:
  /help              Show this help
  /version           Show version info
  /status            System status
  /learn <topic>     Learn a topic
  /predict <data>    Make prediction
  /memory <query>    Search memory
  /history           Show chat history
  /clear             Clear history
  /save <file>       Save conversation
  /server            Start API server
  /server-stop       Stop API server
  /server-status     Check server status
  /plugins           List plugins
  /plugin-install    Install plugin
  /plugin-uninstall  Uninstall plugin
  /config            Show configuration
  /config-set        Update configuration
  /export            Export data
  /import            Import data
  /analytics         Show analytics
  /wisdom [tradition] Get wisdom quote
  /repair            Error repair status
  /repair-heal       Trigger self-healing
  /repair-clear      Clear error history
  /memory-manager    Memory management
  /mm-cleanup        Propose memory cleanup
  /mm-approve        Approve purge proposal
  /mm-reject         Reject purge proposal
  /mm-recover        Recover deleted entry
  /ped-diagnostic    Pedagogical diagnostic
  /ped-progress      Student progress
  /quit              Exit Omega AI

v3.7.0 Modules:
  crypto, ratelimit, ws, vectordb, tenant,
  marketplace, prices, metrics, email, telegram,
  pdf, backup, llm, mesh, blockchain, federated
"""


def cmd_version(args: list[str]) -> str:
    """Show version information."""
    brain = get_brain()
    try:
        brain_status = brain.status()
    except Exception:
        brain_status = {"status": "unknown"}
    return f"""
Omega AI v{VERSION} "{CODENAME}"
Build: {BUILD_DATE}
Python: {sys.version.split()[0]}
Platform: {sys.platform}
Brain: {brain_status.get('status', 'unknown')}
Data: {DATA_DIR}
Modules: core_brain + 51 modules
Endpoints: 60+ REST API endpoints
"""


def cmd_status(args: list[str]) -> str:
    """Show system status."""
    brain = get_brain()
    try:
        status = brain.status()
        return json.dumps(status, indent=2, default=str)
    except Exception as e:
        return f"Status error: {e}"


def cmd_learn(args: list[str]) -> str:
    """Learn a topic."""
    if not args:
        return "Usage: /learn <topic> [data]"
    topic = args[0]
    data = " ".join(args[1:]) if len(args) > 1 else ""
    brain = get_brain()
    try:
        result = brain.learn(topic, data or {"learned": True})
        return f"Learned: {topic} -> {result}"
    except Exception as e:
        return f"Learn error: {e}"


def cmd_predict(args: list[str]) -> str:
    """Make a prediction."""
    if not args:
        return "Usage: /predict <num1> <num2> ..."
    try:
        values = [float(x) for x in args]
    except ValueError:
        return "Error: All arguments must be numbers"
    brain = get_brain()
    try:
        result = brain.predict(values)
        return f"Prediction: avg={result.get('average', 'N/A')}, trend={result.get('trend', 'N/A')}"
    except Exception as e:
        return f"Predict error: {e}"


def cmd_memory(args: list[str]) -> str:
    """Search memory."""
    query = " ".join(args) if args else "*"
    brain = get_brain()
    try:
        results = brain.search_memory(query) if hasattr(brain, "search_memory") else []
        if not results:
            return f"No memory entries found for: {query}"
        lines = [f"Memory results for '{query}':"]
        for i, r in enumerate(results[:10], 1):
            lines.append(f"  {i}. {r}")
        return "\n".join(lines)
    except Exception as e:
        return f"Memory error: {e}"


def cmd_history(args: list[str]) -> str:
    """Show conversation history."""
    if not _history:
        return "No conversation history."
    lines = ["Conversation History:"]
    for entry in _history[-20:]:
        role = entry.get("role", "?")
        content = entry.get("content", "")[:80]
        lines.append(f"  [{role}] {content}")
    return "\n".join(lines)


def cmd_clear(args: list[str]) -> str:
    """Clear conversation history."""
    global _history
    count = len(_history)
    _history = []
    return f"Cleared {count} history entries."


def cmd_save(args: list[str]) -> str:
    """Save conversation to file."""
    filename = args[0] if args else f"conversation_{int(time.time())}.json"
    filepath = DATA_DIR / filename
    try:
        filepath.write_text(json.dumps(_history, indent=2))
        return f"Saved to {filepath}"
    except OSError as e:
        return f"Save error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  SERVER COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

_server_proc: subprocess.Popen | None = None


def cmd_server(args: list[str]) -> str:
    """Start the API server."""
    global _server_proc
    if _server_proc and _server_proc.poll() is None:
        return "Server already running."
    port = args[0] if args else "8080"
    try:
        _server_proc = subprocess.Popen(
            [sys.executable, "-c", f"import api_server; api_server.start_server(port={port})"],
            cwd=str(SCRIPT_DIR),
        )
        time.sleep(1)
        if _server_proc.poll() is None:
            return f"API server started on port {port} (PID: {_server_proc.pid})"
        return "Server failed to start."
    except Exception as e:
        return f"Server error: {e}"


def cmd_server_stop(args: list[str]) -> str:
    """Stop the API server."""
    global _server_proc
    if _server_proc:
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
        _server_proc = None
        return "Server stopped."
    return "No server running."


def cmd_server_status(args: list[str]) -> str:
    """Check server status."""
    if _server_proc and _server_proc.poll() is None:
        return f"Server running (PID: {_server_proc.pid})"
    return "Server not running."


# ═══════════════════════════════════════════════════════════════════════════════
#  PLUGIN COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_plugins(args: list[str]) -> str:
    """List plugins."""
    brain = get_brain()
    try:
        plugins = brain.list_plugins() if hasattr(brain, "list_plugins") else []
        if not plugins:
            return "No plugins installed."
        lines = ["Installed Plugins:"]
        for p in plugins:
            name = p.get("name", "?")
            ver = p.get("version", "?")
            en = "enabled" if p.get("enabled") else "disabled"
            lines.append(f"  {name} v{ver} [{en}]")
        return "\n".join(lines)
    except Exception as e:
        return f"Plugin error: {e}"


def cmd_plugin_install(args: list[str]) -> str:
    """Install a plugin."""
    if not args:
        return "Usage: /plugin-install <name> [version]"
    name = args[0]
    version = args[1] if len(args) > 1 else "latest"
    brain = get_brain()
    try:
        result = brain.install_plugin(name, version) if hasattr(brain, "install_plugin") else f"Install {name} v{version}"
        return f"Plugin install: {result}"
    except Exception as e:
        return f"Install error: {e}"


def cmd_plugin_uninstall(args: list[str]) -> str:
    """Uninstall a plugin."""
    if not args:
        return "Usage: /plugin-uninstall <name>"
    name = args[0]
    brain = get_brain()
    try:
        result = brain.uninstall_plugin(name) if hasattr(brain, "uninstall_plugin") else f"Uninstall {name}"
        return f"Plugin uninstall: {result}"
    except Exception as e:
        return f"Uninstall error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

_config_file = DATA_DIR / "config.json"


def cmd_config(args: list[str]) -> str:
    """Show configuration."""
    if _config_file.exists():
        return _config_file.read_text()
    return "No configuration set."


def cmd_config_set(args: list[str]) -> str:
    """Update configuration."""
    if len(args) < 2:
        return "Usage: /config-set <key> <value>"
    key, value = args[0], args[1]
    config = {}
    if _config_file.exists():
        config = json.loads(_config_file.read_text())
    try:
        config[key] = json.loads(value)
    except json.JSONDecodeError:
        config[key] = value
    _config_file.write_text(json.dumps(config, indent=2))
    return f"Set {key} = {config[key]}"


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_export(args: list[str]) -> str:
    """Export data."""
    fmt = args[0] if args else "json"
    brain = get_brain()
    try:
        data = brain.export_data(fmt) if hasattr(brain, "export_data") else {"history": _history}
        filename = f"export_{int(time.time())}.{fmt}"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(data, indent=2, default=str))
        return f"Exported to {filepath}"
    except Exception as e:
        return f"Export error: {e}"


def cmd_import_data(args: list[str]) -> str:
    """Import data."""
    if not args:
        return "Usage: /import <filepath>"
    filepath = Path(args[0])
    if not filepath.exists():
        return f"File not found: {filepath}"
    try:
        data = json.loads(filepath.read_text())
        return f"Imported: {len(data)} records"
    except Exception as e:
        return f"Import error: {e}"


def cmd_analytics(args: list[str]) -> str:
    """Show analytics."""
    brain = get_brain()
    try:
        stats = brain.get_analytics() if hasattr(brain, "get_analytics") else {"requests": len(_history)}
        return json.dumps(stats, indent=2, default=str)
    except Exception as e:
        return f"Analytics error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  WISDOM COMMAND (v3.5.0)
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_wisdom(args: list[str]) -> str:
    """Get a wisdom proverb."""
    tradition = args[0] if args else ""
    try:
        import wisdom_engine
        engine = wisdom_engine.WisdomEngine()
        result = engine.get_wisdom(tradition=tradition or None)
        text = result.get("text", "")
        source = result.get("source", "")
        trad = result.get("tradition", "")
        return f'"{text}"\n  \u2014 {source} ({trad})'
    except Exception as e:
        return f"Wisdom error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  ERROR REPAIR COMMANDS (v3.6.1)
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_repair(args: list[str]) -> str:
    """Show error repair status."""
    try:
        import error_repair
        engine = error_repair.ErrorRepairEngine()
        stats = engine.get_stats()
        lines = ["Error Repair Status:"]
        lines.append(f"  Total errors: {stats.get('total_errors', 0)}")
        lines.append(f"  Active issues: {stats.get('active_issues', 0)}")
        lines.append(f"  Healed: {stats.get('healed_count', 0)}")
        lines.append(f"  Circuit breakers: {stats.get('circuit_breakers', 0)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Repair error: {e}"


def cmd_repair_heal(args: list[str]) -> str:
    """Trigger self-healing."""
    module = args[0] if args else "all"
    try:
        import error_repair
        engine = error_repair.ErrorRepairEngine()
        result = engine.heal_module(module)
        return f"Heal result: {result.get('status', 'unknown')}"
    except Exception as e:
        return f"Heal error: {e}"


def cmd_repair_clear(args: list[str]) -> str:
    """Clear error history."""
    days = int(args[0]) if args else 7
    try:
        import error_repair
        engine = error_repair.ErrorRepairEngine()
        result = engine.clear_history(days)
        return f"Cleared {result.get('cleared', 0)} entries"
    except Exception as e:
        return f"Clear error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  MEMORY MANAGER COMMANDS (v3.6.2)
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_memory_manager(args: list[str]) -> str:
    """Show memory manager status."""
    try:
        import memory_manager
        mgr = memory_manager.MemoryManager()
        stats = mgr.get_stats()
        lines = ["Memory Manager Status:"]
        lines.append(f"  Total entries: {stats.get('total_entries', 0)}")
        lines.append(f"  Active: {stats.get('active', 0)}")
        lines.append(f"  Stale: {stats.get('stale', 0)}")
        lines.append(f"  Pending purges: {stats.get('pending_purges', 0)}")
        return "\n".join(lines)
    except Exception as e:
        return f"Memory manager error: {e}"


def cmd_mm_cleanup(args: list[str]) -> str:
    """Propose memory cleanup."""
    try:
        import memory_manager
        mgr = memory_manager.MemoryManager()
        proposals = mgr.propose_cleanup()
        if not proposals:
            return "No cleanup proposals."
        lines = ["Cleanup Proposals:"]
        for p in proposals:
            lines.append(f"  {p.entry_key}: {p.reason} (saves {p.space_saved} bytes)")
        return "\n".join(lines)
    except Exception as e:
        return f"Cleanup error: {e}"


def cmd_mm_approve(args: list[str]) -> str:
    """Approve a purge proposal."""
    if not args:
        return "Usage: /mm-approve <proposal_id>"
    try:
        import memory_manager
        mgr = memory_manager.MemoryManager()
        result = mgr.approve_purge(args[0])
        return f"Approved: {result.get('message', 'OK')}"
    except Exception as e:
        return f"Approve error: {e}"


def cmd_mm_reject(args: list[str]) -> str:
    """Reject a purge proposal."""
    if not args:
        return "Usage: /mm-reject <proposal_id>"
    try:
        import memory_manager
        mgr = memory_manager.MemoryManager()
        result = mgr.reject_purge(args[0])
        return f"Rejected: {result.get('message', 'OK')}"
    except Exception as e:
        return f"Reject error: {e}"


def cmd_mm_recover(args: list[str]) -> str:
    """Recover a deleted entry."""
    if not args:
        return "Usage: /mm-recover <entry_id>"
    try:
        import memory_manager
        mgr = memory_manager.MemoryManager()
        result = mgr.recover_entry(args[0])
        return f"Recovered: {result.get('message', 'OK')}"
    except Exception as e:
        return f"Recover error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  PEDAGOGICAL COMMANDS (v3.6.3)
# ═══════════════════════════════════════════════════════════════════════════════


def cmd_ped_diagnostic(args: list[str]) -> str:
    """Run pedagogical diagnostic."""
    student_id = args[0] if args else "default"
    domain = args[1] if len(args) > 1 else "general"
    try:
        import pedagogical_engine
        engine = pedagogical_engine.PedagogicalEngine()
        result = engine.diagnostic_assessment(student_id, domain)
        lines = [f"Diagnostic for {student_id} ({domain}):"]
        lines.append(f"  Bloom level: {result.get('bloom_level', 'N/A')}")
        lines.append(f"  Mastery: {result.get('mastery_percent', 0):.1f}%")
        lines.append(f"  Recommendation: {result.get('recommendation', 'N/A')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Diagnostic error: {e}"


def cmd_ped_progress(args: list[str]) -> str:
    """Show student progress."""
    student_id = args[0] if args else "default"
    try:
        import pedagogical_engine
        engine = pedagogical_engine.PedagogicalEngine()
        result = engine.get_progress(student_id)
        lines = [f"Progress for {student_id}:"]
        for domain, data in result.get("domains", {}).items():
            level = data.get("bloom_level", "N/A")
            pct = data.get("mastery_percent", 0)
            lines.append(f"  {domain}: {level} ({pct:.1f}%)")
        return "\n".join(lines)
    except Exception as e:
        return f"Progress error: {e}"
