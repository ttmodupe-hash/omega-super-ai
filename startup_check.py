#!/usr/bin/env python3
"""Luqi AI v20 — Startup Validation Script

Validates the entire platform before going live. Run this before
starting the server in production.

Usage:
    python3 startup_check.py              # Standard validation
    python3 startup_check.py --verbose    # Show full tracebacks
    python3 startup_check.py --json       # Machine-readable JSON output
    python3 startup_check.py -v -j        # Both verbose and JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Color constants (respects NO_COLOR env var) ──────────────────────────
_USE_COLOR = not os.environ.get("NO_COLOR", "")


def _c(text: str, color: str) -> str:
    """Return colored text if color is enabled."""
    if not _USE_COLOR:
        return text
    codes = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
             "blue": "\033[94m", "bold": "\033[1m", "reset": "\033[0m"}
    return f"{codes.get(color, '')}{text}{codes['reset']}"


# ── Test Configuration ───────────────────────────────────────────────────

VERSION = "20.0.0"
PROJECT_ROOT = Path(__file__).parent

MODULES = [
    # Core
    ("backend.config", True),
    ("backend.ai_engine", True),
    ("backend.search", True),
    ("backend.memory", True),
    ("backend.files", True),
    ("backend.images", True),
    ("backend.chat", True),
    ("backend.financial", False),
    ("backend.taxes", False),
    # v14
    ("backend.subscriptions", True),
    ("backend.developer", True),
    ("backend.website_builder", True),
    ("backend.dashboard", True),
    ("backend.auto_upgrader", False),
    # v15
    ("backend.cognitive_engine", True),
    ("backend.education_system", True),
    ("backend.voice_system", True),
    ("backend.safety_alignment", True),
    ("backend.physics_simulator", True),
    # v16
    ("backend.github_integration", True),
    ("backend.notifications", True),
    ("backend.data_portability", True),
    # v17
    ("backend.captainship", True),
    ("backend.companionship", True),
    # v18
    ("backend.automotive", True),
    ("backend.writing_assistant", True),
    # v19
    ("backend.law_studies", True),
    # v20
    ("backend.agricultural_advisor", True),
    ("backend.healthcare_assistant", True),
    ("backend.teacher_assistant", True),
    ("backend.business_advisor", True),
    ("backend.offline_engine", True),
    # Endpoints
    ("backend.v14_endpoints", True),
    ("backend.v15_endpoints", True),
    ("backend.v16_endpoints", True),
    ("backend.v17_endpoints", True),
    ("backend.v18_endpoints", True),
    ("backend.v19_endpoints", True),
    ("backend.v20_endpoints", True),
    # Critical
    ("backend.router", True),
    ("backend.stripe_integration", False),
    ("backend.email_system", False),
    ("backend.middleware", True),
]

ENV_REQUIRED = [
    ("OPENAI_API_KEY", r"^sk-[A-Za-z0-9]{20,}$"),
    ("STRIPE_SECRET_KEY", r"^sk_(test|live)_[A-Za-z0-9]{20,}$"),
    ("STRIPE_PUBLISHABLE_KEY", r"^pk_(test|live)_[A-Za-z0-9]{20,}$"),
]

ENV_OPTIONAL = [
    "STRIPE_WEBHOOK_SECRET",
    "SENDGRID_API_KEY",
    "SERPER_API_KEY",
    "VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
]

DIRECTORIES = [
    "uploads",
    "chroma_db",
    "generated_images",
    "web",
]

FRONTEND_FILES = [
    ("web/index.html", 50000),
    ("web/sw.js", 1000),
    ("web/manifest.json", 100),
]

# ── Reporter ─────────────────────────────────────────────────────────────

class Reporter:
    """Collect and format validation results."""

    def __init__(self, verbose: bool = False, json_mode: bool = False):
        self.verbose = verbose
        self.json_mode = json_mode
        self.results: List[Dict[str, Any]] = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def ok(self, message: str, detail: str = ""):
        self.passed += 1
        self.results.append({"status": "pass", "message": message, "detail": detail})
        if not self.json_mode:
            detail_str = f" ({detail})" if detail else ""
            print(f"  {_c('[OK]', 'green')}  {message}{detail_str}")

    def fail(self, message: str, detail: str = ""):
        self.failed += 1
        self.results.append({"status": "fail", "message": message, "detail": detail})
        if not self.json_mode:
            detail_str = f" — {detail}" if detail else ""
            print(f"  {_c('[FAIL]', 'red')} {message}{detail_str}")

    def warn(self, message: str, detail: str = ""):
        self.warnings += 1
        self.results.append({"status": "warn", "message": message, "detail": detail})
        if not self.json_mode:
            detail_str = f" — {detail}" if detail else ""
            print(f"  {_c('[WARN]', 'yellow')} {message}{detail_str}")

    def section(self, title: str):
        if not self.json_mode:
            print(f"\n{_c(title, 'bold')}")
            print("=" * 50)

    def summary(self):
        total = self.passed + self.failed + self.warnings
        if self.json_mode:
            print(json.dumps({
                "version": VERSION,
                "timestamp": time.time(),
                "summary": {
                    "total": total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "warnings": self.warnings,
                    "healthy": self.failed == 0,
                },
                "results": self.results,
            }, indent=2))
        else:
            print(f"\n{'=' * 50}")
            print(_c("SUMMARY", "bold"))
            print(f"  {_c(str(self.passed), 'green')} passed")
            print(f"  {_c(str(self.failed), 'red')} failed")
            print(f"  {_c(str(self.warnings), 'yellow')} warnings")
            print(f"  {total} total checks")
            print(f"\nStatus: {_c('HEALTHY', 'green') if self.failed == 0 else _c('DEGRADED', 'red')}")
            if self.failed > 0:
                print(f"\n{_c('Fix failures before launching to production.', 'red')}")
        return self.failed == 0


# ── Validation Functions ─────────────────────────────────────────────────

def check_modules(r: Reporter):
    r.section("[1/6] Module Imports")
    for module_name, critical in MODULES:
        try:
            importlib.import_module(module_name)
            r.ok(module_name)
        except Exception as exc:
            msg = f"{exc}"[:100]
            if critical:
                r.fail(module_name, msg)
            else:
                r.warn(module_name, f"optional — {msg}")


def check_environment(r: Reporter):
    r.section("[2/6] Environment Variables")
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        r.fail(".env file", "Run: cp .env.example .env")
        return
    r.ok(".env file exists")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        r.warn("python-dotenv not installed", "skipping .env loading")

    # Check required
    for var_name, pattern in ENV_REQUIRED:
        value = os.environ.get(var_name, "")
        placeholder = value.lower() in ["", "your-key-here", "sk-your-openai-key-here",
                                         "sk_test_your-key-here", "pk_test_your-key-here"]
        if not value or placeholder:
            r.fail(var_name, "not set or is placeholder")
        elif not __import__("re").match(pattern, value):
            r.warn(var_name, f"format looks invalid (got {value[:10]}...)")
        else:
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else value[:6] + "..."
            r.ok(var_name, masked)

    # Check optional
    for var_name in ENV_OPTIONAL:
        value = os.environ.get(var_name, "")
        if value and "your" not in value.lower():
            masked = value[:8] + "..." if len(value) > 12 else "set"
            r.ok(var_name, f"{masked} (optional)")
        else:
            r.warn(var_name, "not set — feature will use mock/fallback")


def check_directories(r: Reporter):
    r.section("[3/6] Directory Structure")
    for dirname in DIRECTORIES:
        dir_path = PROJECT_ROOT / dirname
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                r.warn(dirname, "created automatically")
            except Exception as exc:
                r.fail(dirname, f"cannot create: {exc}")
        else:
            r.ok(dirname)

    # Check frontend files
    for filename, min_size in FRONTEND_FILES:
        file_path = PROJECT_ROOT / filename
        if not file_path.exists():
            r.fail(filename, "missing")
        elif file_path.stat().st_size < min_size:
            r.warn(filename, f"only {file_path.stat().st_size}B (expected >{min_size}B)")
        else:
            r.ok(filename, f"{file_path.stat().st_size:,} bytes")


def check_database(r: Reporter):
    r.section("[4/6] Database Connectivity")
    # SQLite
    try:
        test_db = PROJECT_ROOT / ".startup_test.db"
        conn = sqlite3.connect(str(test_db))
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        row = conn.execute("SELECT * FROM test").fetchone()
        conn.execute("DROP TABLE test")
        conn.close()
        test_db.unlink()
        r.ok("SQLite", "read/write OK")
    except Exception as exc:
        r.fail("SQLite", str(exc))

    # ChromaDB
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_db"))
        coll = client.get_or_create_collection("startup_test")
        coll.add(ids=["test"], documents=["test"])
        result = coll.query(query_texts=["test"], n_results=1)
        client.delete_collection("startup_test")
        r.ok("ChromaDB", "vector search OK")
    except ImportError:
        r.warn("ChromaDB", "not installed")
    except Exception as exc:
        r.warn("ChromaDB", str(exc)[:100])


def check_frontend(r: Reporter):
    r.section("[5/6] Frontend Integrity")
    index_path = PROJECT_ROOT / "web" / "index.html"
    if not index_path.exists():
        r.fail("Frontend", "web/index.html not found")
        return

    content = index_path.read_text()

    # Check version marker
    if "v20" in content or "20.0" in content:
        r.ok("Version marker", "v20 detected")
    else:
        r.warn("Version marker", "v20 not found in HTML")

    # Check required HTML elements
    for tag in ["<!DOCTYPE", "<html", "<head>", "<body", "<script>"]:
        if tag in content:
            r.ok(f"HTML structure: {tag}")
        else:
            r.fail(f"HTML structure: {tag}", "missing")

    # Check v20 page components
    v20_pages = ["LawPage", "AgriculturePage", "HealthcarePage", 
                 "EducationPage", "BusinessPage", "OfflinePage"]
    for page in v20_pages:
        if page in content:
            r.ok(f"Page: {page}")
        else:
            r.fail(f"Page: {page}", "not found in frontend")

    # Check PWA support
    if "serviceWorker" in content:
        r.ok("PWA service worker registration")
    else:
        r.warn("PWA service worker", "not found")


def check_network(r: Reporter):
    r.section("[6/6] Port & Network")
    # Port availability
    port = 8000
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result == 0:
            r.warn(f"Port {port}", "already in use")
        else:
            r.ok(f"Port {port}", "available")
    except Exception as exc:
        r.warn(f"Port check", str(exc))

    # Local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("8.8.8.8", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        r.ok("Local IP", ip)
    except Exception:
        r.ok("Local IP", "127.0.0.1")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Luqi AI v20 Startup Validation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full tracebacks")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--version", action="version", version=f"Luqi AI v{VERSION}")
    args = parser.parse_args()

    if not args.json:
        print(_c(f"\n{'='*50}", "bold"))
        print(_c(f"  Luqi AI v{VERSION} — Startup Validation", "bold"))
        print(_c(f"{'='*50}", "bold"))

    reporter = Reporter(verbose=args.verbose, json_mode=args.json)

    try:
        check_modules(reporter)
        check_environment(reporter)
        check_directories(reporter)
        check_database(reporter)
        check_frontend(reporter)
        check_network(reporter)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(130)

    healthy = reporter.summary()

    if not args.json:
        print(f"\n{_c('Next steps:', 'bold')}")
        if healthy:
            print(f"  {_c('1.', 'green')} Run: python3 start_server.py")
            print(f"  {_c('2.', 'green')} Open: http://localhost:8000")
            print(f"  {_c('3.', 'green')} API docs: http://localhost:8000/docs")
        else:
            print(f"  {_c('1.', 'yellow')} Fix failures above")
            print(f"  {_c('2.', 'yellow')} Re-run: python3 startup_check.py")

    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
