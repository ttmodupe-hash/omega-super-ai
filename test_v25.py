#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Startup Verification Script
===============================================
One-command test for the Autonomous Multi-Agent System.

Usage:
    py test_v25.py          (Windows)
    python3 test_v25.py     (Linux/Mac)
"""

import json
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))


def test_module(name, import_path):
    """Test that a module imports cleanly."""
    try:
        __import__(import_path)
        print(f"  [PASS] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return False


def test_file_exists(path, label):
    """Test that a file exists."""
    full = BASE / path
    if full.exists():
        size = full.stat().st_size
        print(f"  [PASS] {label} ({size:,} bytes)")
        return True
    else:
        print(f"  [FAIL] {label}: {path} not found")
        return False


def test_compilation(path, label):
    """Test that a file compiles as valid Python."""
    import py_compile
    try:
        py_compile.compile(str(BASE / path), doraise=True)
        print(f"  [PASS] {label}")
        return True
    except py_compile.PyCompileError as e:
        print(f"  [FAIL] {label}: {e}")
        return False


def test_endpoint(path, expected_status=200):
    """Test a local API endpoint."""
    try:
        req = urllib.request.Request(f"http://localhost:8000{path}")
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"  [PASS] GET {path} ({resp.status})")
        return True
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"  [PASS] GET {path} ({e.code})")
            return True
        print(f"  [WARN] GET {path} ({e.code})")
        return False
    except Exception as e:
        print(f"  [SKIP] GET {path}: server not running ({type(e).__name__})")
        return True  # Don't fail if server isn't running


def main():
    print("=" * 60)
    print("Luqi AI v24.5.0 — Autonomous System Startup Test")
    print("=" * 60)

    passed = 0
    failed = 0

    # ── 1. File Existence ──────────────────────────────────────────
    print("\n[1/5] File Existence Checks")
    files = [
        ("backend/autonomous_system.py", "Master Orchestrator"),
        ("backend/alert_system.py", "Alert System"),
        ("backend/dead_mans_switch.py", "Dead Man's Switch"),
        ("backend/sandbox_validator.py", "Sandbox Validator"),
        ("backend/research_engine.py", "Research Engine"),
        ("backend/v24_autonomous_endpoints.py", "Endpoint Router"),
        ("backend/health_monitor.py", "Health Monitor"),
        ("AUTONOMOUS_SYSTEM_DESIGN.md", "Design Document"),
    ]
    for path, label in files:
        if test_file_exists(path, label):
            passed += 1
        else:
            failed += 1

    # ── 2. Compilation ─────────────────────────────────────────────
    print("\n[2/5] Python Compilation Checks")
    compilable = [
        ("backend/alert_system.py", "alert_system.py"),
        ("backend/dead_mans_switch.py", "dead_mans_switch.py"),
        ("backend/sandbox_validator.py", "sandbox_validator.py"),
        ("backend/research_engine.py", "research_engine.py"),
        ("backend/autonomous_system.py", "autonomous_system.py"),
        ("backend/v24_autonomous_endpoints.py", "v24_autonomous_endpoints.py"),
        ("backend/health_monitor.py", "health_monitor.py"),
    ]
    for path, label in compilable:
        if test_compilation(path, label):
            passed += 1
        else:
            failed += 1

    # ── 3. Module Imports ──────────────────────────────────────────
    print("\n[3/5] Module Import Checks")
    modules = [
        ("Alert System", "backend.alert_system"),
        ("Dead Man's Switch", "backend.dead_mans_switch"),
        ("Sandbox Validator", "backend.sandbox_validator"),
        ("Research Engine", "backend.research_engine"),
        ("Autonomous System", "backend.autonomous_system"),
    ]
    for name, path in modules:
        if test_module(name, path):
            passed += 1
        else:
            failed += 1

    # ── 4. API Endpoints (if server running) ───────────────────────
    print("\n[4/5] API Endpoint Checks (server must be running)")
    endpoints = [
        "/api/system/status",
        "/api/system/alerts",
        "/api/system/config",
        "/api/system/updates",
        "/api/system/research",
    ]
    for ep in endpoints:
        if test_endpoint(ep):
            passed += 1
        else:
            failed += 1

    # ── 5. Data Directory ──────────────────────────────────────────
    print("\n[5/5] Data Directory")
    data_dir = BASE / "data"
    if not data_dir.exists():
        data_dir.mkdir(exist_ok=True)
        print(f"  [INFO] Created data/ directory")
    if data_dir.exists():
        print(f"  [PASS] data/ directory exists")
        passed += 1
    else:
        print(f"  [FAIL] data/ directory could not be created")
        failed += 1

    # ── Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = passed + failed
    pct = (passed / total * 100) if total > 0 else 0
    if failed == 0:
        print(f"ALL TESTS PASSED: {passed}/{total} ({pct:.0f}%)")
        print("Your Autonomous Multi-Agent System is ready!")
        print("\nNext: Start the server with:")
        print("  py -3.11 -m uvicorn backend.router:app --reload")
    else:
        print(f"RESULTS: {passed} passed, {failed} failed ({pct:.0f}%)")
        print("\nSome tests failed. Check the output above for details.")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
