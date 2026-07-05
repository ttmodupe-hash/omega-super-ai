#!/usr/bin/env python3
"""Luqi AI Self-Test — Startup diagnostics and health verification.

Usage:
    py -3.11 self_test.py        # Full diagnostic check
    py -3.11 self_test.py --quick # Quick check (no imports)
    py -3.11 self_test.py --fix  # Auto-fix common issues

Checks:
  1. Python version (3.11+)
  2. Required dependencies installed
  3. API key configured
  4. Directory structure
  5. Backend modules importable
  6. Router endpoints registered
  7. Web UI files present
"""

import importlib
import os
import sys
from pathlib import Path

# ── Colors ─────────────────────────────────────────────────────────────

class Colors:
    PASS = "\033[92m"      # Green
    FAIL = "\033[91m"      # Red
    WARN = "\033[93m"      # Yellow
    INFO = "\033[96m"      # Cyan
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"

PASS = f"{Colors.PASS}PASS{Colors.END}"
FAIL = f"{Colors.FAIL}FAIL{Colors.END}"
WARN = f"{Colors.WARN}WARN{Colors.END}"

# ── Test Results ───────────────────────────────────────────────────────

results = {"passed": 0, "failed": 0, "warnings": 0}


def check(name: str, condition: bool, fix_msg: str = "") -> bool:
    """Print a check result."""
    if condition:
        print(f"  {PASS} {name}")
        results["passed"] += 1
        return True
    else:
        print(f"  {FAIL} {name}")
        if fix_msg:
            print(f"       {Colors.DIM}{fix_msg}{Colors.END}")
        results["failed"] += 1
        return False


def warn(name: str, message: str):
    """Print a warning."""
    print(f"  {WARN} {name}")
    print(f"       {Colors.DIM}{message}{Colors.END}")
    results["warnings"] += 1


# ── Test Functions ─────────────────────────────────────────────────────

def test_python_version():
    """Check Python is 3.11+."""
    print(f"\n{Colors.BOLD}[1] Python Environment{Colors.END}")
    version = sys.version_info
    check(
        f"Python {version.major}.{version.minor}.{version.micro}",
        version.major == 3 and version.minor >= 11,
        "Install Python 3.11 or newer from python.org",
    )
    check("64-bit", sys.maxsize > 2**32, "Use 64-bit Python for best compatibility")


def test_dependencies():
    """Check required packages are installed."""
    print(f"\n{Colors.BOLD}[2] Dependencies{Colors.END}")
    required = [
        "fastapi", "uvicorn", "pydantic", "openai",
        "httpx", "chromadb", "numpy",
    ]
    optional = [
        "python-dotenv", "requests", "pillow", "aiofiles",
    ]

    for pkg in required:
        try:
            importlib.import_module(pkg)
            check(f"{pkg}", True)
        except ImportError:
            check(f"{pkg}", False, f"pip install {pkg}")

    for pkg in optional:
        try:
            importlib.import_module(pkg)
            check(f"{pkg} (optional)", True)
        except ImportError:
            warn(f"{pkg} (optional)", f"pip install {pkg} for full features")


def test_api_key():
    """Check API key is configured."""
    print(f"\n{Colors.BOLD}[3] API Configuration{Colors.END}")
    key = os.environ.get("OPENAI_API_KEY", "")
    check("OPENAI_API_KEY env var", bool(key), "Set: $env:OPENAI_API_KEY='sk-...'")

    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text()
        has_key = "OPENAI_API_KEY" in content and "sk-" in content
        check(".env file with key", has_key, "Add OPENAI_API_KEY=sk-... to .env")
    else:
        warn(".env file", "Create .env file from .env.example")


def test_directories():
    """Check project structure."""
    print(f"\n{Colors.BOLD}[4] Project Structure{Colors.END}")
    dirs = ["backend", "web", "backend/lang", "docs"]
    for d in dirs:
        check(f"{d}/", Path(d).is_dir(), f"mkdir {d}")

    files = ["start_server.py", "server.py", "requirements.txt"]
    for f in files:
        check(f, Path(f).is_file(), f"File missing: {f}")


def test_backend_imports():
    """Test backend module imports."""
    print(f"\n{Colors.BOLD}[5] Backend Modules{Colors.END}")
    modules = [
        "backend.chat", "backend.memory", "backend.search",
        "backend.financial", "backend.taxes", "backend.auth",
        "backend.config", "backend.models",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
            check(mod, True)
        except ImportError as e:
            check(mod, False, str(e))

    # Language modules
    lang_modules = [
        "backend.lang.african_languages",
        "backend.lang.language_detector",
        "backend.lang.greeting_handler",
        "backend.lang.multilingual_router",
    ]
    for mod in lang_modules:
        try:
            importlib.import_module(mod)
            check(mod, True)
        except ImportError as e:
            warn(mod, str(e))


def test_router():
    """Test FastAPI router loads."""
    print(f"\n{Colors.BOLD}[6] API Router{Colors.END}")
    try:
        from backend.router import app
        routes = [r.path for r in app.routes]
        check("Router imports", True)

        # Check key endpoints
        endpoints = [
            "/api/health",
            "/api/chat",
            "/api/chat/stream",
            "/api/search",
            "/api/languages",
            "/api/labs",
            "/api/prometheus/status",
        ]
        for ep in endpoints:
            check(f"  {ep}", ep in routes, f"Endpoint {ep} not registered")
    except Exception as e:
        check("Router imports", False, str(e))


def test_web_ui():
    """Check web UI files."""
    print(f"\n{Colors.BOLD}[7] Web UI{Colors.END}")
    web_dir = Path("web")
    check("web/ directory", web_dir.is_dir())

    index = web_dir / "index.html"
    if check("web/index.html", index.is_file()):
        size = index.stat().st_size
        check(f"  Size: {size:,} bytes", size > 1000, "File may be truncated")

    # Check for labs UI
    labs_dir = web_dir / "labs"
    if labs_dir.is_dir():
        check("web/labs/", True)
    else:
        warn("web/labs/", "Virtual labs UI not built yet")


def test_server_connectivity():
    """Test if server is running."""
    print(f"\n{Colors.BOLD}[8] Server Status{Colors.END}")
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            "http://localhost:8000/api/health",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode()
            import json
            health = json.loads(data)
            ver = health.get("version", "unknown")
            check(f"Server running (v{ver})", True)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            warn("Server running", "Health endpoint not found (old version?)")
        else:
            warn("Server check", f"HTTP {e.code}")
    except Exception as e:
        warn("Server not running", f"Start with: py -3.11 start_server.py")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    print(f"""
{Colors.INFO}{Colors.BOLD}
   _                _     _ 
  | |    _   _ _ __| | __| |
  | |   | | | | '__| |/ _` |
  | |___| |_| | |  | | (_| |
  |_____|\__,_|_|  |_|\__,_|
{Colors.END}
  {Colors.BOLD}Luqi AI v13 — Self-Test Diagnostics{Colors.END}
  {Colors.DIM}{'='*40}{Colors.END}
""")

    test_python_version()
    test_dependencies()
    test_api_key()
    test_directories()
    test_backend_imports()
    test_router()
    test_web_ui()
    test_server_connectivity()

    # Summary
    print(f"\n{Colors.BOLD}{'='*40}{Colors.END}")
    total = results["passed"] + results["failed"] + results["warnings"]
    print(f"  {Colors.PASS} {results['passed']}{Colors.END} passed")
    if results["failed"]:
        print(f"  {Colors.FAIL} {results['failed']}{Colors.END} failed")
    if results["warnings"]:
        print(f"  {Colors.WARN} {results['warnings']}{Colors.END} warnings")
    print(f"  {Colors.DIM}Total: {total} checks{Colors.END}")

    if results["failed"] == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}All critical checks passed!{Colors.END}")
        print(f"  {Colors.DIM}Start server: py -3.11 start_server.py{Colors.END}")
        return 0
    else:
        print(f"\n  {Colors.FAIL}{Colors.BOLD}Some checks failed.{Colors.END}")
        print(f"  {Colors.DIM}Fix issues above, then run: py -3.11 self_test.py{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
