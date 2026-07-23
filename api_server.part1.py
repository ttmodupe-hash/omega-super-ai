# This file is Part 1 of 2 for api_server.py
# Run: python reassemble_v37.py
# =========================================

"""Omega AI v3.7.0 — HTTP API Server
Standard-library-only REST API. Start with: python omega_ai.py --server [--port 8080]

Security features:
- Request size limit (1MB max)
- Input sanitization on all endpoints
- CORS headers for web UI
- Graceful shutdown on SIGTERM

v3.7.0: 60+ endpoints, 18 new modules wired
"""

from __future__ import annotations

import json
import os
import re
import secrets
import signal
import sqlite3
import sys
import threading
import time
import traceback
import zlib
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlparse

# ─── Lazy imports for optional modules ───────────────────────────────────────
_LAZY_MODULES: dict[str, Any] = {}


def _import(module_name: str):
    """Lazy import to avoid startup cost for unused modules."""
    if module_name not in _LAZY_MODULES:
        try:
            _LAZY_MODULES[module_name] = __import__(module_name)
        except ImportError:
            _LAZY_MODULES[module_name] = None
    return _LAZY_MODULES[module_name]


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = Path(os.environ.get("OMEGA_DATA_DIR", ".omega_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PORT = int(os.environ.get("OMEGA_PORT", "8080"))
MAX_REQUEST_SIZE = 1 * 1024 * 1024  # 1 MB
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
}

# API Key auth (simple, no external deps)
_api_keys: set[str] = set()


def _load_api_keys():
    """Load API keys from environment or data file."""
    global _api_keys
    env_keys = os.environ.get("OMEGA_API_KEYS", "")
    if env_keys:
        _api_keys.update(k.strip() for k in env_keys.split(",") if k.strip())
    key_file = DATA_DIR / "api_keys.txt"
    if key_file.exists():
        _api_keys.update(line.strip() for line in key_file.read_text().splitlines() if line.strip())


_load_api_keys()

# Endpoints that DON'T require authentication
PUBLIC_ENDPOINTS = {
    "/api/health",
    "/api/version",
    "/api/status",
    "/api/openapi.json",
    "/api/ws",  # WebSocket upgrade handled separately
}

# v3.7.0: Endpoints that require authentication (all except public)
AUTH_ENDPOINTS = {
    "/api/process",
    "/api/chat",
    "/api/learn",
    "/api/predict",
    "/api/memory/search",
    "/api/memory/store",
    "/api/memory/delete",
    "/api/analytics",
    "/api/export",
    "/api/import",
    "/api/plugins",
    "/api/plugins/install",
    "/api/plugins/uninstall",
    "/api/config",
    "/api/config/update",
    "/api/system/stats",
    "/api/system/logs",
    "/api/system/restart",
    "/api/wisdom",
    "/api/error-repair/stats",
    "/api/error-repair/heal",
    "/api/error-repair/clear",
    "/api/memory-manager/stats",
    "/api/memory-manager/entries",
    "/api/memory-manager/cleanup",
    "/api/memory-manager/purge-proposals",
    "/api/memory-manager/approve-purge",
    "/api/memory-manager/reject-purge",
    "/api/memory-manager/recover",
    "/api/pedagogical/diagnostic",
    "/api/pedagogical/progress",
    "/api/export",  # v3.7.0: Data export
    "/api/plugins",  # v3.7.0: Plugin management
    "/api/crypto/encrypt",
    "/api/crypto/decrypt",
    "/api/crypto/hash",
    "/api/keys/rotate",
    "/api/rate-limit/status",
    "/api/ws/connect",
    "/api/vector/search",
    "/api/vector/store",
    "/api/tenant/stats",
    "/api/marketplace/plugins",
    "/api/marketplace/install",
    "/api/prices/realtime",
    "/api/metrics",
    "/api/notify/email",
    "/api/telegram/send",
    "/api/pdf/generate",
    "/api/backup/create",
    "/api/backup/restore",
    "/api/backup/list",
    "/api/llm/local/status",
    "/api/llm/local/query",
    "/api/mesh/agents",
    "/api/mesh/tasks",
    "/api/blockchain/audit",
    "/api/federated/model-status",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  REQUEST / RESPONSE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


class JsonResponse:
    """Typed response wrapper for consistent JSON output."""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self.data = data or {}
        self.status = status
        self.headers = headers or {}

    def to_bytes(self) -> bytes:
        body = json.dumps(self.data, indent=2, default=str, ensure_ascii=False).encode("utf-8")
        return body


def _json_response(data: dict[str, Any], status: int = 200) -> JsonResponse:
    return JsonResponse(data=data, status=status)


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse(data={"success": False, "error": message}, status=status)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = DATA_DIR / "omega_api.db"
_db_local = threading.local()


def _db() -> sqlite3.Connection:
    """Thread-local database connection."""
    if not hasattr(_db_local, "conn") or _db_local.conn is None:
        _db_local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _db_local.conn.row_factory = sqlite3.Row
        _db_local.conn.execute("PRAGMA journal_mode=WAL")
    return _db_local.conn


def _init_db():
    """Create tables if they don't exist."""
    db = _db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);

        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT UNIQUE NOT NULL,
            data TEXT NOT NULL,
            updated REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT,
            duration_ms REAL,
            status_code INTEGER,
            timestamp REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics(timestamp);

        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT,
            path TEXT,
            status INTEGER,
            duration_ms REAL,
            timestamp REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_logs_time ON api_logs(timestamp);

        CREATE TABLE IF NOT EXISTS memory_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL DEFAULT (unixepoch()),
            created REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS plugin_registry (
            name TEXT PRIMARY KEY,
            version TEXT,
            enabled INTEGER DEFAULT 1,
            installed REAL DEFAULT (unixepoch())
        );
        """
    )
    db.commit()


_init_db()


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════


def _check_auth(headers: dict[str, str]) -> bool:
    """Check API key in Authorization header."""
    if not _api_keys:
        return True  # No keys configured = open
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:] in _api_keys
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  REQUEST BODY PARSING
# ═══════════════════════════════════════════════════════════════════════════════


def _parse_body(body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Parse request body based on Content-Type."""
    if not body:
        return {}
    content_type = headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    elif "application/x-www-form-urlencoded" in content_type:
        result: dict[str, Any] = {}
        parsed = parse_qs(body.decode("utf-8"))
        for key, values in parsed.items():
            result[key] = values[0] if len(values) == 1 else values
        return result
    return {"raw": body.decode("utf-8", errors="replace")}


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

_request_count = 0
_request_lock = threading.Lock()
_start_time = time.time()


def _log_request(method: str, path: str, status: int, duration_ms: float):
    """Log API request to database."""
    try:
        db = _db()
        db.execute(
            "INSERT INTO api_logs (method, path, status, duration_ms) VALUES (?, ?, ?, ?)",
            (method, path, status, duration_ms),
        )
        db.commit()
    except Exception:
        pass
    global _request_count
    with _request_lock:
        _request_count += 1


def _get_stats() -> dict[str, Any]:
    """Get system statistics."""
    db = _db()
    total_requests = db.execute("SELECT COUNT(*) FROM api_logs").fetchone()[0]
    avg_latency = db.execute("SELECT AVG(duration_ms) FROM api_logs WHERE timestamp > unixepoch() - 3600").fetchone()[0]
    error_rate = db.execute(
        "SELECT CAST(SUM(CASE WHEN status >= 400 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) "
        "FROM api_logs WHERE timestamp > unixepoch() - 3600"
    ).fetchone()[0]
    return {
        "uptime_seconds": round(time.time() - _start_time, 1),
        "total_requests": total_requests,
        "requests_per_second": round(_request_count / max(time.time() - _start_time, 1), 2),
        "avg_latency_ms": round(avg_latency or 0, 2),
        "error_rate_percent": round(error_rate or 0, 2),
        "version": "3.7.0",
        "modules_loaded": len(_LAZY_MODULES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE BRAIN INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

_brain_instance: Any = None


def _get_brain():
    """Lazy-load the core brain."""
    global _brain_instance
    if _brain_instance is None:
        try:
            import core_brain
            _brain_instance = core_brain.OmegaBrain()
        except Exception as e:
            _brain_instance = f"ERROR: {e}"
    return _brain_instance


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def _health() -> JsonResponse:
    """Health check endpoint."""
    brain = _get_brain()
    return _json_response(
        {
            "status": "healthy",
            "version": "3.7.0",
            "brain_loaded": not isinstance(brain, str),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": str(DB_PATH),
            "data_dir": str(DATA_DIR),
        }
    )


def _version() -> JsonResponse:
    """Version endpoint."""
    return _json_response(
        {
            "version": "3.7.0",
            "codename": "Prometheus",
            "api_version": "v1",
            "endpoints": len(AUTH_ENDPOINTS) + len(PUBLIC_ENDPOINTS),
            "modules": [
                "core_brain", "memory", "analytics", "plugins",
                "error_repair", "memory_manager", "pedagogical_engine",
                "crypto_utils", "rate_limiter", "ws_server", "vector_db",
                "multi_tenant", "plugin_marketplace", "realtime_prices",
                "metrics_exporter", "email_notifier", "telegram_bot",
                "pdf_generator", "auto_backup", "local_llm", "agent_mesh",
                "blockchain_audit", "federated_learning",
            ],
        }
    )


def _status() -> JsonResponse:
    """Detailed status endpoint."""
    return _json_response(_get_stats())


def _process(body: dict[str, Any]) -> JsonResponse:
    """Process a command through the brain."""
    command = body.get("command", "")
    if not command:
        return _error("Missing 'command' field", 400)
    brain = _get_brain()
    if isinstance(brain, str):
        return _error(f"Brain not available: {brain}", 503)
    try:
        result = brain.process(command)
        return _json_response({"success": True, "result": result})
    except Exception as e:
        return _error(str(e), 500)


def _chat(body: dict[str, Any]) -> JsonResponse:
    """Chat endpoint with conversation history."""
    message = body.get("message", "")
    session_id = body.get("session_id", "default")
    if not message:
        return _error("Missing 'message' field", 400)
    db = _db()
    db.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, "user", message),
    )
    db.commit()
    brain = _get_brain()
    if isinstance(brain, str):
        response_text = f"Echo: {message}"
    else:
        try:
            response_text = brain.chat(message, session_id=session_id)
        except Exception:
            response_text = f"Echo: {message}"
    db.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, "assistant", response_text),
    )
    db.commit()
    history = [
        {"role": row["role"], "content": row["content"]}
        for row in db.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
    ]
    return _json_response({"success": True, "response": response_text, "history": history})


def _learn(body: dict[str, Any]) -> JsonResponse:
    """Learning endpoint."""
    topic = body.get("topic", "")
    data = body.get("data", "")
    if not topic:
        return _error("Missing 'topic' field", 400)
    db = _db()
    db.execute(
        "INSERT INTO knowledge (topic, data) VALUES (?, ?) ON CONFLICT(topic) DO UPDATE SET data=excluded.data, updated=unixepoch()",
        (topic, json.dumps(data)),
    )
    db.commit()
    return _json_response({"success": True, "message": f"Learned topic: {topic}"})


def _predict(body: dict[str, Any]) -> JsonResponse:
    """Prediction endpoint."""
    data = body.get("data", [])
    if not data:
        return _error("Missing 'data' field", 400)
    try:
        values = [float(x) for x in data]
        avg = sum(values) / len(values)
        trend = "up" if len(values) > 1 and values[-1] > values[0] else "down" if len(values) > 1 and values[-1] < values[0] else "stable"
        return _json_response(
            {
                "success": True,
                "prediction": {
                    "average": round(avg, 4),
                    "trend": trend,
                    "next_value": round(avg + (values[-1] - values[0]) / max(len(values) - 1, 1), 4) if len(values) > 1 else round(avg, 4),
                }
            }
        )
    except (ValueError, TypeError) as e:
        return _error(f"Invalid numeric data: {e}", 400)


def _memory_search(body: dict[str, Any]) -> JsonResponse:
    """Search memory entries."""
    query = body.get("query", "")
    if not query:
        return _error("Missing 'query' field", 400)
    db = _db()
    rows = db.execute(
        "SELECT key, value, access_count, last_accessed FROM memory_entries WHERE key LIKE ? OR value LIKE ? ORDER BY last_accessed DESC LIMIT 50",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
    return _json_response(
        {
            "success": True,
            "results": [
                {
                    "key": r["key"],
                    "value": r["value"],
                    "access_count": r["access_count"],
                    "last_accessed": r["last_accessed"],
                }
                for r in rows
            ],
        }
    )


def _memory_store(body: dict[str, Any]) -> JsonResponse:
    """Store a memory entry."""
    key = body.get("key", "")
    value = body.get("value", "")
    if not key:
        return _error("Missing 'key' field", 400)
    db = _db()
    db.execute(
        "INSERT INTO memory_entries (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, last_accessed=unixepoch()",
        (key, json.dumps(value) if not isinstance(value, str) else value),
    )
    db.commit()
    return _json_response({"success": True, "message": f"Stored: {key}"})


def _memory_delete(body: dict[str, Any]) -> JsonResponse:
    """Delete a memory entry."""
    key = body.get("key", "")
    if not key:
        return _error("Missing 'key' field", 400)
    db = _db()
    db.execute("DELETE FROM memory_entries WHERE key = ?", (key,))
    db.commit()
    return _json_response({"success": True, "message": f"Deleted: {key}"})


def _analytics() -> JsonResponse:
    """Analytics dashboard data."""
    db = _db()
    hourly = [
        {"hour": row[0], "count": row[1]}
        for row in db.execute(
            "SELECT strftime('%Y-%m-%d %H:00', timestamp, 'unixepoch') as hour, COUNT(*) "
            "FROM api_logs WHERE timestamp > unixepoch() - 86400 GROUP BY hour ORDER BY hour DESC LIMIT 24"
        ).fetchall()
    ]
    endpoints = [
        {"endpoint": row[0], "count": row[1], "avg_ms": round(row[2] or 0, 2)}
        for row in db.execute(
            "SELECT path, COUNT(*), AVG(duration_ms) FROM api_logs WHERE timestamp > unixepoch() - 86400 GROUP BY path ORDER BY COUNT(*) DESC LIMIT 20"
        ).fetchall()
    ]
    return _json_response({"success": True, "hourly": hourly, "endpoints": endpoints})


def _export_data(body: dict[str, Any]) -> JsonResponse:
    """Export data endpoint."""
    export_format = body.get("format", "json")
    tables = body.get("tables", ["conversations", "knowledge"])
    db = _db()
    result = {}
    for table in tables:
        try:
            rows = db.execute(f"SELECT * FROM {table}").fetchall()
            result[table] = [dict(r) for r in rows]
        except sqlite3.Error as e:
            result[table] = {"error": str(e)}
    if export_format == "csv":
        import csv
        import io
        output = io.StringIO()
        if result:
            first_table = list(result.keys())[0]
            if isinstance(result[first_table], list) and result[first_table]:
                writer = csv.DictWriter(output, fieldnames=result[first_table][0].keys())
                writer.writeheader()
                writer.writerows(result[first_table])
        return _json_response({"success": True, "format": "csv", "data": output.getvalue()})
    return _json_response({"success": True, "format": "json", "data": result})


def _import_data(body: dict[str, Any]) -> JsonResponse:
    """Import data endpoint."""
    table = body.get("table", "")
    records = body.get("records", [])
    if not table or not records:
        return _error("Missing 'table' or 'records' field", 400)
    db = _db()
    count = 0
    for record in records:
        keys = list(record.keys())
        placeholders = ",".join("?" * len(keys))
        try:
            db.execute(f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})", list(record.values()))
            count += 1
        except sqlite3.Error:
            pass
    db.commit()
    return _json_response({"success": True, "imported": count})


def _plugins_list() -> JsonResponse:
    """List installed plugins."""
    db = _db()
    rows = db.execute("SELECT name, version, enabled, installed FROM plugin_registry").fetchall()
    return _json_response(
        {
            "success": True,
            "plugins": [
                {"name": r["name"], "version": r["version"], "enabled": bool(r["enabled"]), "installed": r["installed"]}
                for r in rows
            ],
        }
    )


def _plugins_install(body: dict[str, Any]) -> JsonResponse:
    """Install a plugin."""
    name = body.get("name", "")
    version = body.get("version", "1.0.0")
    if not name:
        return _error("Missing 'name' field", 400)
    db = _db()
    db.execute(
        "INSERT OR REPLACE INTO plugin_registry (name, version, enabled) VALUES (?, ?, 1)",
        (name, version),
    )
    db.commit()
    return _json_response({"success": True, "message": f"Installed plugin: {name}"})


def _plugins_uninstall(body: dict[str, Any]) -> JsonResponse:
    """Uninstall a plugin."""
    name = body.get("name", "")
    if not name:
        return _error("Missing 'name' field", 400)
    db = _db()
    db.execute("DELETE FROM plugin_registry WHERE name = ?", (name,))
    db.commit()
    return _json_response({"success": True, "message": f"Uninstalled plugin: {name}"})


def _config_get() -> JsonResponse:
    """Get configuration."""
    config_file = DATA_DIR / "config.json"
    if config_file.exists():
        return _json_response({"success": True, "config": json.loads(config_file.read_text())})
    return _json_response({"success": True, "config": {}})


def _config_update(body: dict[str, Any]) -> JsonResponse:
    """Update configuration."""
    config_file = DATA_DIR / "config.json"
    config = json.loads(config_file.read_text()) if config_file.exists() else {}
    config.update(body)
    config_file.write_text(json.dumps(config, indent=2))
    return _json_response({"success": True, "config": config})


def _system_stats() -> JsonResponse:
    """System statistics."""
    import os
    stats = {
        "cpu_count": os.cpu_count(),
        "memory_mb": "N/A",
        "disk_free_gb": "N/A",
        "python_version": sys.version,
        "platform": sys.platform,
    }
    try:
        import psutil
        mem = psutil.virtual_memory()
        stats["memory_mb"] = round(mem.total / (1024 * 1024), 0)
        stats["memory_used_percent"] = mem.percent
        disk = psutil.disk_usage("/")
        stats["disk_free_gb"] = round(disk.free / (1024 * 1024 * 1024), 2)
    except ImportError:
        pass
    return _json_response({"success": True, **stats})


def _system_logs() -> JsonResponse:
    """Get recent API logs."""
    db = _db()
    logs = [
        {"method": r["method"], "path": r["path"], "status": r["status"], "duration_ms": r["duration_ms"]}
        for r in db.execute(
            "SELECT method, path, status, duration_ms FROM api_logs ORDER BY timestamp DESC LIMIT 100"
        ).fetchall()
    ]
    return _json_response({"success": True, "logs": logs})


def _system_restart() -> JsonResponse:
    """Trigger graceful restart."""
    _shutdown_requested = True
    return _json_response({"success": True, "message": "Restart scheduled"})


# ═══════════════════════════════════════════════════════════════════════════════
#  WISDOM ENDPOINT (v3.5.0)
# ═══════════════════════════════════════════════════════════════════════════════

_wisdom_instance: Any = None


def _get_wisdom():
    """Lazy-load wisdom engine."""
    global _wisdom_instance
    if _wisdom_instance is None:
        try:
            import wisdom_engine
            _wisdom_instance = wisdom_engine.WisdomEngine()
        except Exception:
            _wisdom_instance = None
    return _wisdom_instance


def _wisdom(body: dict[str, Any]) -> JsonResponse:
    """Get a wisdom proverb or quote."""
    tradition = body.get("tradition", "")
    wisdom = _get_wisdom()
    if wisdom is None:
        return _error("Wisdom engine not available", 503)
    try:
        result = wisdom.get_wisdom(tradition=tradition or None)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# ═══════════════════════════════════════════════════════════════════════════════
#  ERROR REPAIR ENDPOINTS (v3.6.1)
# ═══════════════════════════════════════════════════════════════════════════════

_error_repair_instance: Any = None


def _get_error_repair():
    """Lazy-load error repair engine."""
    global _error_repair_instance
    if _error_repair_instance is None:
        try:
            import error_repair
            _error_repair_instance = error_repair.ErrorRepairEngine()
        except Exception:
            _error_repair_instance = None
    return _error_repair_instance


def _error_repair_stats() -> JsonResponse:
    """Get error repair statistics."""
    engine = _get_error_repair()
    if engine is None:
        return _error("Error repair engine not available", 503)
    try:
        return _json_response({"success": True, "stats": engine.get_stats()})
    except Exception as e:
        return _error(str(e), 500)


def _error_repair_heal(body: dict[str, Any]) -> JsonResponse:
    """Trigger self-healing for a module."""
    engine = _get_error_repair()
    if engine is None:
        return _error("Error repair engine not available", 503)
    module_name = body.get("module", "")
    try:
        result = engine.heal_module(module_name)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _error_repair_clear(body: dict[str, Any]) -> JsonResponse:
    """Clear error history."""
    engine = _get_error_repair()
    if engine is None:
        return _error("Error repair engine not available", 503)
    try:
        older_than_days = body.get("older_than_days", 7)
        result = engine.clear_history(older_than_days)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# ═══════════════════════════════════════════════════════════════════════════════
#  MEMORY MANAGER ENDPOINTS (v3.6.2)
# ═══════════════════════════════════════════════════════════════════════════════

_memory_mgr_instance: Any = None


def _get_memory_manager():
    """Lazy-load memory manager."""
    global _memory_mgr_instance
    if _memory_mgr_instance is None:
        try:
            import memory_manager
            _memory_mgr_instance = memory_manager.MemoryManager()
        except Exception:
            _memory_mgr_instance = None
    return _memory_mgr_instance


def _memory_mgr_stats() -> JsonResponse:
    """Get memory manager statistics."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    try:
        return _json_response({"success": True, "stats": mgr.get_stats()})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_entries() -> JsonResponse:
    """List memory entries."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    try:
        return _json_response({"success": True, "entries": mgr.list_entries()})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_cleanup(body: dict[str, Any]) -> JsonResponse:
    """Analyze and propose cleanup."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    try:
        proposals = mgr.propose_cleanup()
        return _json_response({"success": True, "proposals": [p.to_dict() for p in proposals]})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_purge_proposals() -> JsonResponse:
    """Get pending purge proposals."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    try:
        return _json_response({"success": True, "proposals": mgr.get_purge_proposals()})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_approve_purge(body: dict[str, Any]) -> JsonResponse:
    """Approve a purge proposal."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    proposal_id = body.get("proposal_id", "")
    try:
        result = mgr.approve_purge(proposal_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_reject_purge(body: dict[str, Any]) -> JsonResponse:
    """Reject a purge proposal."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    proposal_id = body.get("proposal_id", "")
    try:
        result = mgr.reject_purge(proposal_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _memory_mgr_recover(body: dict[str, Any]) -> JsonResponse:
    """Recover a soft-deleted entry."""
    mgr = _get_memory_manager()
    if mgr is None:
        return _error("Memory manager not available", 503)
    entry_id = body.get("entry_id", "")
    try:
        result = mgr.recover_entry(entry_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# ═══════════════════════════════════════════════════════════════════════════════
#  PEDAGOGICAL ENGINE ENDPOINTS (v3.6.3)
# ═══════════════════════════════════════════════════════════════════════════════

_pedagogical_instance: Any = None


def _get_pedagogical():
    """Lazy-load pedagogical engine."""
    global _pedagogical_instance
    if _pedagogical_instance is None:
        try:
            import pedagogical_engine
            _pedagogical_instance = pedagogical_engine.PedagogicalEngine()
        except Exception:
            _pedagogical_instance = None
    return _pedagogical_instance


def _pedagogical_diagnostic(body: dict[str, Any]) -> JsonResponse:
    """Run diagnostic assessment for a student."""
    engine = _get_pedagogical()
    if engine is None:
        return _error("Pedagogical engine not available", 503)
    student_id = body.get("student_id", "")
    domain = body.get("domain", "general")
    if not student_id:
        return _error("Missing 'student_id' field", 400)
    try:
        result = engine.diagnostic_assessment(student_id, domain)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _pedagogical_progress(body: dict[str, Any]) -> JsonResponse:
    """Get student progress."""
    engine = _get_pedagogical()
    if engine is None:
        return _error("Pedagogical engine not available", 503)
    student_id = body.get("student_id", "")
    if not student_id:
        return _error("Missing 'student_id' field", 400)
    try:
        result = engine.get_progress(student_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# ═══════════════════════════════════════════════════════════════════════════════
#  v3.7.0 NEW MODULE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# --- Crypto Utils ---
_crypto_instance: Any = None


def _get_crypto():
    global _crypto_instance
    if _crypto_instance is None:
        try:
            import crypto_utils
            _crypto_instance = crypto_utils.CryptoManager()
        except Exception:
            _crypto_instance = None
    return _crypto_instance


def _crypto_encrypt(body: dict[str, Any]) -> JsonResponse:
    mgr = _get_crypto()
    if mgr is None:
        return _error("Crypto manager not available", 503)
    plaintext = body.get("plaintext", "")
    key = body.get("key", "")
    if not plaintext:
        return _error("Missing 'plaintext'", 400)
    try:
        result = mgr.encrypt(plaintext, key)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _crypto_decrypt(body: dict[str, Any]) -> JsonResponse:
    mgr = _get_crypto()
    if mgr is None:
        return _error("Crypto manager not available", 503)
    ciphertext = body.get("ciphertext", "")
    key = body.get("key", "")
    if not ciphertext:
        return _error("Missing 'ciphertext'", 400)
    try:
        result = mgr.decrypt(ciphertext, key)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _crypto_hash(body: dict[str, Any]) -> JsonResponse:
    mgr = _get_crypto()
    if mgr is None:
        return _error("Crypto manager not available", 503)
    data = body.get("data", "")
    algorithm = body.get("algorithm", "sha256")
    if not data:
        return _error("Missing 'data'", 400)
    try:
        result = mgr.hash(data, algorithm)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Key Rotation ---
_keyrot_instance: Any = None


def _get_key_rotation():
    global _keyrot_instance
    if _keyrot_instance is None:
        try:
            import key_rotation
            _keyrot_instance = key_rotation.KeyRotationManager()
        except Exception:
            _keyrot_instance = None
    return _keyrot_instance


def _keys_rotate(body: dict[str, Any]) -> JsonResponse:
    mgr = _get_key_rotation()
    if mgr is None:
        return _error("Key rotation manager not available", 503)
    try:
        result = mgr.rotate_keys(body.get("key_id"))
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Rate Limiter ---
_ratelimit_instance: Any = None


def _get_rate_limiter():
    global _ratelimit_instance
    if _ratelimit_instance is None:
        try:
            import rate_limiter
            _ratelimit_instance = rate_limiter.RateLimiter()
        except Exception:
            _ratelimit_instance = None
    return _ratelimit_instance


def _rate_limit_status() -> JsonResponse:
    rl = _get_rate_limiter()
    if rl is None:
        return _error("Rate limiter not available", 503)
    try:
        return _json_response({"success": True, "status": rl.get_status()})
    except Exception as e:
        return _error(str(e), 500)


# --- WebSocket Server ---
_ws_instance: Any = None


def _get_ws_server():
    global _ws_instance
    if _ws_instance is None:
        try:
            import ws_server
            _ws_instance = ws_server.WSServer()
        except Exception:
            _ws_instance = None
    return _ws_instance


def _ws_connect() -> JsonResponse:
    ws = _get_ws_server()
    if ws is None:
        return _error("WebSocket server not available", 503)
    try:
        return _json_response({"success": True, "endpoint": "/api/ws", "protocol": "ws"})
    except Exception as e:
        return _error(str(e), 500)


# --- Vector DB ---
_vectordb_instance: Any = None


def _get_vector_db():
    global _vectordb_instance
    if _vectordb_instance is None:
        try:
            import vector_db
            _vectordb_instance = vector_db.VectorDB()
        except Exception:
            _vectordb_instance = None
    return _vectordb_instance


def _vector_search(body: dict[str, Any]) -> JsonResponse:
    db = _get_vector_db()
    if db is None:
        return _error("Vector DB not available", 503)
    query = body.get("query", "")
    if not query:
        return _error("Missing 'query'", 400)
    try:
        results = db.search(query)
        return _json_response({"success": True, "results": results})
    except Exception as e:
        return _error(str(e), 500)


def _vector_store(body: dict[str, Any]) -> JsonResponse:
    db = _get_vector_db()
    if db is None:
        return _error("Vector DB not available", 503)
    doc_id = body.get("id", "")
    text = body.get("text", "")
    if not doc_id or not text:
        return _error("Missing 'id' or 'text'", 400)
    try:
        result = db.store(doc_id, text)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Multi-Tenant ---
_tenant_instance: Any = None


def _get_tenant():
    global _tenant_instance
    if _tenant_instance is None:
        try:
            import multi_tenant
            _tenant_instance = multi_tenant.TenantManager()
        except Exception:
            _tenant_instance = None
    return _tenant_instance


def _tenant_stats() -> JsonResponse:
    mgr = _get_tenant()
    if mgr is None:
        return _error("Tenant manager not available", 503)
    try:
        return _json_response({"success": True, "tenants": mgr.get_stats()})
    except Exception as e:
        return _error(str(e), 500)


# --- Plugin Marketplace ---
_marketplace_instance: Any = None


def _get_marketplace():
    global _marketplace_instance
    if _marketplace_instance is None:
        try:
            import plugin_marketplace
            _marketplace_instance = plugin_marketplace.Marketplace()
        except Exception:
            _marketplace_instance = None
    return _marketplace_instance


def _marketplace_plugins() -> JsonResponse:
    m = _get_marketplace()
    if m is None:
        return _error("Marketplace not available", 503)
    try:
        return _json_response({"success": True, "plugins": m.list_plugins()})
    except Exception as e:
        return _error(str(e), 500)


def _marketplace_install(body: dict[str, Any]) -> JsonResponse:
    m = _get_marketplace()
    if m is None:
        return _error("Marketplace not available", 503)
    plugin_id = body.get("plugin_id", "")
    if not plugin_id:
        return _error("Missing 'plugin_id'", 400)
    try:
        result = m.install(plugin_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Realtime Prices ---
_prices_instance: Any = None


def _get_prices():
    global _prices_instance
    if _prices_instance is None:
        try:
            import realtime_prices
            _prices_instance = realtime_prices.PriceTracker()
        except Exception:
            _prices_instance = None
    return _prices_instance


def _prices_realtime(body: dict[str, Any]) -> JsonResponse:
    t = _get_prices()
    if t is None:
        return _error("Price tracker not available", 503)
    symbols = body.get("symbols", ["BTC", "ETH"])
    try:
        result = t.get_prices(symbols)
        return _json_response({"success": True, "prices": result})
    except Exception as e:
        return _error(str(e), 500)


# --- Metrics Exporter ---
_metrics_instance: Any = None


def _get_metrics():
    global _metrics_instance
    if _metrics_instance is None:
        try:
            import metrics_exporter
            _metrics_instance = metrics_exporter.MetricsExporter()
        except Exception:
            _metrics_instance = None
    return _metrics_instance


def _metrics_export() -> JsonResponse:
    m = _get_metrics()
    if m is None:
        return _error("Metrics exporter not available", 503)
    try:
        return _json_response({"success": True, "metrics": m.export()})
    except Exception as e:
        return _error(str(e), 500)


# --- Email Notifier ---
_email_instance: Any = None


def _get_email():
    global _email_instance
    if _email_instance is None:
        try:
            import email_notifier
            _email_instance = email_notifier.EmailNotifier()
        except Exception:
            _email_instance = None
    return _email_instance


def _notify_email(body: dict[str, Any]) -> JsonResponse:
    notifier = _get_email()
    if notifier is None:
        return _error("Email notifier not available", 503)
    to = body.get("to", "")
    subject = body.get("subject", "")
    message = body.get("message", "")
    if not to or not subject or not message:
        return _error("Missing 'to', 'subject', or 'message'", 400)
    try:
        result = notifier.send(to, subject, message)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Telegram Bot ---
_telegram_instance: Any = None


def _get_telegram():
    global _telegram_instance
    if _telegram_instance is None:
        try:
            import telegram_bot
            _telegram_instance = telegram_bot.TelegramBot()
        except Exception:
            _telegram_instance = None
    return _telegram_instance


def _telegram_send(body: dict[str, Any]) -> JsonResponse:
    bot = _get_telegram()
    if bot is None:
        return _error("Telegram bot not available", 503)
    chat_id = body.get("chat_id", "")
    message = body.get("message", "")
    if not chat_id or not message:
        return _error("Missing 'chat_id' or 'message'", 400)
    try:
        result = bot.send_message(chat_id, message)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- PDF Generator ---
_pdf_instance: Any = None


def _get_pdf():
    global _pdf_instance
    if _pdf_instance is None:
        try:
            import pdf_generator
            _pdf_instance = pdf_generator.PDFGenerator()
        except Exception:
            _pdf_instance = None
    return _pdf_instance


def _pdf_generate(body: dict[str, Any]) -> JsonResponse:
    gen = _get_pdf()
    if gen is None:
        return _error("PDF generator not available", 503)
    content = body.get("content", "")
    title = body.get("title", "Report")
    if not content:
        return _error("Missing 'content'", 400)
    try:
        result = gen.generate(content, title)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Auto Backup ---
_backup_instance: Any = None


def _get_backup():
    global _backup_instance
    if _backup_instance is None:
        try:
            import auto_backup
            _backup_instance = auto_backup.BackupManager()
        except Exception:
            _backup_instance = None
    return _backup_instance


def _backup_create() -> JsonResponse:
    mgr = _get_backup()
    if mgr is None:
        return _error("Backup manager not available", 503)
    try:
        result = mgr.create_backup()
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _backup_restore(body: dict[str, Any]) -> JsonResponse:
    mgr = _get_backup()
    if mgr is None:
        return _error("Backup manager not available", 503)
    backup_id = body.get("backup_id", "")
    if not backup_id:
        return _error("Missing 'backup_id'", 400)
    try:
        result = mgr.restore(backup_id)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


def _backup_list() -> JsonResponse:
    mgr = _get_backup()
    if mgr is None:
        return _error("Backup manager not available", 503)
    try:
        return _json_response({"success": True, "backups": mgr.list_backups()})
    except Exception as e:
        return _error(str(e), 500)


# --- Local LLM ---
_llm_instance: Any = None


def _get_local_llm():
    global _llm_instance
    if _llm_instance is None:
        try:
            import local_llm
            _llm_instance = local_llm.LocalLLM()
        except Exception:
            _llm_instance = None
    return _llm_instance


def _llm_status() -> JsonResponse:
    llm = _get_local_llm()
    if llm is None:
        return _error("Local LLM not available", 503)
    try:
        return _json_response({"success": True, "status": llm.get_status()})
    except Exception as e:
        return _error(str(e), 500)


def _llm_query(body: dict[str, Any]) -> JsonResponse:
    llm = _get_local_llm()
    if llm is None:
        return _error("Local LLM not available", 503)
    prompt = body.get("prompt", "")
    if not prompt:
        return _error("Missing 'prompt'", 400)
    try:
        result = llm.query(prompt)
        return _json_response({"success": True, **result})
    except Exception as e:
        return _error(str(e), 500)


# --- Agent Mesh ---
_mesh_instance: Any = None


def _get_mesh():
    global _mesh_instance
    if _mesh_instance is None:
        try:
            import agent_mesh
            _mesh_instance = agent_mesh.AgentMesh()
        except Exception:
            _mesh_instance = None
    return _mesh_instance


def _mesh_agents() -> JsonResponse:
    mesh = _get_mesh()
    if mesh is None:
        return _error("Agent mesh not available", 503)
    try:
        return _json_response({"success": True, "agents": mesh.list_agents()})
    except Exception as e:
        return _error(str(e), 500)


def _mesh_tasks(body: dict[str, Any]) -> JsonResponse:
    mesh = _get_mesh()
    if mesh is None:
        return _error("Agent mesh not available", 503)
    try:
        tasks = mesh.list_tasks(body.get("agent_id"))
        return _json_response({"success": True, "tasks": tasks})
    except Exception as e:
        return _error(str(e), 500)


# --- Blockchain Audit ---
_blockchain_instance: Any = None


def _get_blockchain():
    global _blockchain_instance
    if _blockchain_instance is None:
        try:
            import blockchain_audit
            _blockchain_instance = blockchain_audit.BlockchainAuditor()
        except Exception:
            _blockchain_instance = None
    return _blockchain_instance


def _blockchain_audit() -> JsonResponse:
    auditor = _get_blockchain()
    if auditor is None:
        return _error("Blockchain auditor not available", 503)
    try:
        return _json_response({"success": True, "audit": auditor.get_audit_log()})
    except Exception as e:
        return _error(str(e), 500)


# --- Federated Learning ---
_federated_instance: Any = None


def _get_federated():
    global _federated_instance
    if _federated_instance is None:
        try:
            import federated_learning
            _federated_instance = federated_learning.FederatedLearning()
        except Exception:
            _federated_instance = None
    return _federated_instance


def _federated_status() -> JsonResponse:
    fl = _get_federated()
    if fl is None:
        return _error("Federated learning not available", 503)
    try:
        return _json_response({"success": True, "status": fl.get_status()})
    except Exception as e:
        return _error(str(e), 500)
