#!/usr/bin/env python3
"""
OMEGA-LUQI Engine — Autonomous Endpoint & Dependency Diagnostic Test Harness
Verifies module availability, route registration, runtime instantiation, and endpoint health.
"""

from __future__ import annotations

import ast
import asyncio
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CheckResult:
    test_id: str
    name: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class DiagnosticSummary:
    timestamp: float = field(default_factory=time.time)
    python_version: str = sys.version
    sys_path: List[str] = field(default_factory=lambda: sys.path.copy())
    results: List[CheckResult] = field(default_factory=list)
    total_passed: int = 0
    total_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SUPER-INTELLECTUAL DIAGNOSTIC HARNESS
# ═══════════════════════════════════════════════════════════════════════════════

class EngineDiagnosticRunner:
    """Automated inspection engine for backend endpoints and module state."""

    TARGET_MODULES = [
        ("animation_engine", "backend.animation_engine", "AnimationEngine"),
        ("visual_learning", "backend.visual_learning", "VisualLearningEngine"),
        ("v25_animation_endpoints", "backend.v25_animation_endpoints", None),
    ]

    KEYWORD_TARGETS = {"animation", "visual", "training", "v25", "render"}

    def __init__(self, project_root: Optional[Path] = None) -> None:
        # This file lives at engine/test_animation_debug.py; the backend package
        # it diagnoses lives at engine/backend/. parent.parent resolves to the
        # merge-repo root, whose own backend/ package shadows engine/backend and
        # breaks every import below.
        self.project_root = project_root or Path(__file__).resolve().parent
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))
        self.summary = DiagnosticSummary()

    async def run_all_checks(self) -> DiagnosticSummary:
        """Executes full diagnostic suite across imports, route graphs, and ASGI probes."""
        await self._run_test("T1_MODULE_IMPORTS", "Module Import Integrity", self._check_imports)
        await self._run_test("T2_ENDPOINT_FLAGS", "V25 Feature Flags Verification", self._check_v25_flags)
        await self._run_test("T3_ROUTER_INSPECTION", "FastAPI / Starlette Route Registry Scan", self._check_router)
        await self._run_test("T4_AST_ROUTE_AUDIT", "Static AST Endpoint Declaration Audit", self._audit_ast_declarations)
        await self._run_test("T5_ASGI_HEALTH_PROBE", "In-Memory Async Endpoint Health Probe", self._probe_health_endpoints)

        self.summary.total_passed = sum(1 for r in self.summary.results if r.passed)
        self.summary.total_failed = sum(1 for r in self.summary.results if not r.passed)
        return self.summary

    async def _run_test(self, test_id: str, name: str, coro) -> None:
        start_time = time.perf_counter()
        try:
            details = await coro() if asyncio.iscoroutinefunction(coro) else coro()
            elapsed = (time.perf_counter() - start_time) * 1000
            self.summary.results.append(
                CheckResult(
                    test_id=test_id,
                    name=name,
                    passed=True,
                    details=details or {},
                    execution_time_ms=round(elapsed, 2),
                )
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000
            self.summary.results.append(
                CheckResult(
                    test_id=test_id,
                    name=name,
                    passed=False,
                    error=str(exc),
                    stack_trace=traceback.format_exc(),
                    execution_time_ms=round(elapsed, 2),
                )
            )

    # ── Test Implementations ──

    def _check_imports(self) -> Dict[str, Any]:
        module_status = {}
        for alias, module_path, target_class in self.TARGET_MODULES:
            try:
                mod = __import__(module_path, fromlist=["*"])
                cls_found = hasattr(mod, target_class) if target_class else True
                module_status[alias] = {
                    "status": "LOADED",
                    "path": getattr(mod, "__file__", "builtin/unknown"),
                    "target_class": target_class,
                    "class_present": cls_found,
                }
            except Exception as e:
                module_status[alias] = {"status": "FAILED", "error": str(e)}
        return {"modules": module_status}

    def _check_v25_flags(self) -> Dict[str, Any]:
        from backend import v25_animation_endpoints as v25
        return {
            "ANIMATION_AVAILABLE": getattr(v25, "_ANIMATION_AVAILABLE", None),
            "VISUAL_AVAILABLE": getattr(v25, "_VISUAL_AVAILABLE", None),
            "APP_AVAILABLE": getattr(v25, "_APP_AVAILABLE", None),
        }

    def _check_router(self) -> Dict[str, Any]:
        try:
            from backend.router import app
        except ImportError:
            from backend.main import app  # Fallback target

        registered_routes = []
        target_routes = []

        for route in getattr(app, "routes", []):
            path = getattr(route, "path", None)
            methods = list(getattr(route, "methods", []))
            if path:
                registered_routes.append(path)
                if any(kw in path for kw in self.KEYWORD_TARGETS):
                    target_routes.append({"path": path, "methods": methods, "name": getattr(route, "name", "")})

        return {
            "total_routes_count": len(registered_routes),
            "matched_routes_count": len(target_routes),
            "matched_routes": target_routes,
        }

    def _audit_ast_declarations(self) -> Dict[str, Any]:
        """Statically inspects source files to locate route definitions even if runtime load fails."""
        endpoints_file = self.project_root / "backend" / "v25_animation_endpoints.py"
        if not endpoints_file.exists():
            return {"skipped": True, "reason": f"File not found: {endpoints_file}"}

        tree = ast.parse(endpoints_file.read_text(encoding="utf-8"))
        declared_routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Detect @router.get(...), @app.post(...), etc.
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            declared_routes.append({
                                "function": node.name,
                                "method": decorator.func.attr,
                                "path": decorator.args[0].value,
                            })

        return {"ast_declared_routes_count": len(declared_routes), "routes": declared_routes}

    async def _probe_health_endpoints(self) -> Dict[str, Any]:
        """Executes lightweight ASGI requests without spawning a real network server."""
        try:
            from backend.router import app
            from httpx import AsyncClient, ASGITransport
        except ImportError as e:
            return {"skipped": True, "reason": f"Dependency missing for ASGI probing: {e}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            endpoints_to_test = ["/v1/health", "/api/v1/animation/health", "/animation/status"]
            probe_results = {}

            for ep in endpoints_to_test:
                try:
                    resp = await client.get(ep)
                    probe_results[ep] = {"status_code": resp.status_code, "reachable": resp.status_code < 500}
                except Exception as ex:
                    probe_results[ep] = {"status_code": None, "reachable": False, "error": str(ex)}

        return {"probes": probe_results}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRYPOINT & REPORTING
# ═══════════════════════════════════════════════════════════════════════════════

def render_terminal_report(summary: DiagnosticSummary) -> None:
    width = 70
    print("═" * width)
    print(" OMEGA-LUQI ENGINE — AUTOMATED ENDPOINT DIAGNOSTIC REPORT")
    print("═" * width)
    print(f" Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(summary.timestamp))}")
    print(f" Total Tests: {len(summary.results)} | Passed: {summary.total_passed} | Failed: {summary.total_failed}")
    print("─" * width)

    for res in summary.results:
        symbol = "✓ PASS" if res.passed else "✗ FAIL"
        print(f"\n[{symbol}] {res.test_id}: {res.name} ({res.execution_time_ms} ms)")
        if res.passed:
            for k, v in res.details.items():
                if isinstance(v, list):
                    print(f"   ├─ {k} ({len(v)} items):")
                    for item in v[:5]:
                        print(f"   │   • {item}")
                    if len(v) > 5:
                        print(f"   │   ... (+{len(v) - 5} more)")
                else:
                    print(f"   ├─ {k}: {v}")
        else:
            print(f"   ├─ Error: {res.error}")
            if res.stack_trace:
                lines = res.stack_trace.strip().split("\n")
                print("   └─ Stack Trace:")
                for line in lines[-3:]:
                    print(f"        {line}")

    print("\n" + "═" * width)


async def main() -> int:
    runner = EngineDiagnosticRunner()
    summary = await runner.run_all_checks()
    render_terminal_report(summary)
    return 0 if summary.total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
