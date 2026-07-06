#!/usr/bin/env python3
"""
Luqi AI v13 — Startup Self-Test

Validates all system components before starting the server.
Run: py -3.11 self_test.py
"""

import importlib
import os
import sys
from pathlib import Path

# ── Colors ─────────────────────────────────────────────────────────────

class C:
    PASS = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def ok(msg): print(f"  {C.PASS}✓{C.RESET} {msg}")
def err(msg): print(f"  {C.FAIL}✗{C.RESET} {msg}")
def warn(msg): print(f"  {C.WARN}⚠{C.RESET} {msg}")
def info(msg): print(f"  {C.INFO}ℹ{C.RESET} {msg}")


# ── Tests ──────────────────────────────────────────────────────────────

def test_python_version():
    """Check Python version is 3.11+."""
    v = sys.version_info
    if v.major == 3 and v.minor >= 11:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        err(f"Python {v.major}.{v.minor}.{v.micro} — requires 3.11+")
        return False


def test_dependencies():
    """Check all required packages are installed."""
    required = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("openai", "OpenAI"),
        ("chromadb", "ChromaDB"),
        ("requests", "Requests"),
    ]
    optional = [
        ("duckduckgo_search", "DuckDuckGo Search"),
        ("PyPDF2", "PyPDF2"),
        ("pdfplumber", "pdfplumber"),
        ("docx", "python-docx"),
        ("PIL", "Pillow"),
        ("python_dotenv", "python-dotenv"),
    ]
    
    all_ok = True
    for module, name in required:
        try:
            importlib.import_module(module)
            ok(f"{name}")
        except ImportError:
            err(f"{name} — run: pip install {name.lower().replace(' ', '-')}")
            all_ok = False
    
    for module, name in optional:
        try:
            importlib.import_module(module)
            ok(f"{name} (optional)")
        except ImportError:
            warn(f"{name} (optional) — install for full features")
    
    return all_ok


def test_api_key():
    """Check API key configuration."""
    key = os.environ.get("OPENAI_API_KEY", "")
    
    if not key:
        env_file = Path(".env")
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        if line.strip().startswith("OPENAI_API_KEY="):
                            key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    
    if key and key != "sk-your-openai-key-here" and len(key) > 20:
        masked = key[:8] + "..." + key[-4:]
        ok(f"OPENAI_API_KEY: {masked}")
        return True
    else:
        warn("OPENAI_API_KEY not configured — AI chat will be unavailable")
        info("Set it in .env or environment variable")
        return False


def test_directories():
    """Check required directories exist."""
    dirs = ["uploads", "generated_images", "chroma_db"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
        ok(f"Directory: {d}/")
    return True


def test_backend_modules():
    """Test importing all backend modules."""
    modules = [
        "backend.config",
        "backend.ai_engine",
        "backend.search",
        "backend.memory",
        "backend.files",
        "backend.images",
        "backend.agents",
    ]
    
    # Optional v13 modules
    optional_modules = [
        "backend.lang.african_languages",
        "backend.lang.language_detector",
        "backend.lang.multilingual_router",
    ]
    
    all_ok = True
    for mod in modules:
        try:
            importlib.import_module(mod)
            ok(f"Module: {mod}")
        except Exception as e:
            err(f"Module: {mod} — {e}")
            all_ok = False
    
    for mod in optional_modules:
        try:
            importlib.import_module(mod)
            ok(f"Module: {mod} (v13)")
        except Exception as e:
            warn(f"Module: {mod} — {e}")
    
    return all_ok


def test_router_import():
    """Test importing the main router."""
    try:
        from backend.router import app
        ok("Router app imports successfully")
        
        # Check endpoints
        routes = [r.path for r in app.routes]
        v13_endpoints = [
            "/api/languages",
            "/api/languages/{code}",
            "/api/languages/detect",
            "/api/labs",
            "/api/labs/{lab_id}",
            "/api/prometheus/status",
            "/api/prometheus/run",
        ]
        for ep in v13_endpoints:
            if ep in routes:
                ok(f"Endpoint: {ep}")
            else:
                warn(f"Endpoint: {ep} — not found")
        
        return True
    except Exception as e:
        err(f"Router import failed: {e}")
        return False


def test_server_connectivity():
    """Test if server is already running."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8000/api/health", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            version = data.get("version", "unknown")
            ok(f"Server running — v{version}")
            return True
    except Exception:
        info("Server not running (expected before startup)")
        return True


# ── Main ───────────────────────────────────────────────────────────────

def run_all_tests():
    """Run all self-tests and return overall status."""
    print(f"\n{C.BOLD}{C.INFO}Luqi AI v13 — Startup Diagnostics{C.RESET}\n")
    
    results = []
    
    print(f"{C.BOLD}Python Environment{C.RESET}")
    results.append(test_python_version())
    
    print(f"\n{C.BOLD}Dependencies{C.RESET}")
    results.append(test_dependencies())
    
    print(f"\n{C.BOLD}Configuration{C.RESET}")
    results.append(test_api_key())
    
    print(f"\n{C.BOLD}Directories{C.RESET}")
    results.append(test_directories())
    
    print(f"\n{C.BOLD}Backend Modules{C.RESET}")
    results.append(test_backend_modules())
    
    print(f"\n{C.BOLD}Router & Endpoints{C.RESET}")
    results.append(test_router_import())
    
    print(f"\n{C.BOLD}Server Status{C.RESET}")
    results.append(test_server_connectivity())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'=' * 50}")
    if passed == total:
        print(f"{C.PASS}{C.BOLD}All {total}/{total} checks passed — ready to start!{C.RESET}")
        print(f"\nStart with: py -3.11 start_server.py")
        return 0
    elif passed >= total - 1:
        print(f"{C.WARN}{C.BOLD}{passed}/{total} checks passed — server will start with limited features{C.RESET}")
        return 0
    else:
        print(f"{C.FAIL}{C.BOLD}{passed}/{total} checks passed — fix issues before starting{C.RESET}")
        return 1


if __name__ == "__main__":
    import json  # needed for server connectivity test
    sys.exit(run_all_tests())
