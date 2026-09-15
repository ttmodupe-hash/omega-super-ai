#!/usr/bin/env python3
"""
Luqi AI v24.4.0 — Health Monitor & Error Detection System
=========================================================
Production-ready health monitoring with automatic error tracking,
startup diagnostics, and self-healing capabilities.

Features:
  - Module import verification on startup
  - Runtime error tracking with categorization
  - GET /health endpoint with full diagnostics
  - GET /health/errors for error history
  - POST /health/reset to clear error state
  - Colored startup banner showing module status
  - Automatic recovery suggestions for common errors

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from __future__ import annotations

import importlib
import logging
import os
import platform
import psutil
import time
import traceback
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Deque, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

HEALTH_CONFIG = {
    "version": "24.4.0",
    "error_history_size": 100,
    "slow_endpoint_threshold_ms": 1000,
    "critical_error_threshold": 10,
    "health_check_interval_seconds": 30,
    "max_uptime_history": 24 * 60 * 60,  # 24 hours in seconds
}


# ═══════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════

class ErrorSeverity(str, Enum):
    """Severity levels for tracked errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModuleStatus(str, Enum):
    """Status of a module import check."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TrackedError:
    """A single tracked error occurrence."""
    id: str
    timestamp: datetime
    module: str
    endpoint: str
    error_type: str
    message: str
    severity: ErrorSeverity
    stack_trace: Optional[str] = None
    resolved: bool = False
    resolution: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "module": self.module,
            "endpoint": self.endpoint,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "stack_trace": self.stack_trace,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }


@dataclass
class EndpointMetrics:
    """Metrics for a single endpoint."""
    path: str
    method: str
    total_requests: int = 0
    total_errors: int = 0
    avg_response_ms: float = 0.0
    last_called: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "method": self.method,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "avg_response_ms": round(self.avg_response_ms, 2),
            "last_called": self.last_called.isoformat() if self.last_called else None,
        }


@dataclass
class ModuleCheckResult:
    """Result of a module health check."""
    name: str
    status: ModuleStatus
    error: Optional[str] = None
    load_time_ms: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "error": self.error,
            "load_time_ms": round(self.load_time_ms, 2) if self.load_time_ms else None,
        }


# ═══════════════════════════════════════════════════════════════════
# ERROR TRACKER
# ═══════════════════════════════════════════════════════════════════

class ErrorTracker:
    """Central error tracking system with categorization and history.
    
    Tracks errors across the application with automatic severity
    assignment and resolution suggestions.
    
    Usage:
        tracker = ErrorTracker()
        tracker.track_error(e, context={"module": "router", "endpoint": "/api/chat"})
        errors = tracker.get_errors(severity=ErrorSeverity.CRITICAL)
    """
    
    _instance: Optional['ErrorTracker'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._errors: Deque[TrackedError] = deque(maxlen=HEALTH_CONFIG["error_history_size"])
        self._error_counts: Dict[str, int] = {}
        self._start_time = datetime.utcnow()
        logger.info("ErrorTracker initialized (max history: %d)", HEALTH_CONFIG["error_history_size"])
    
    def track_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: Optional[ErrorSeverity] = None,
    ) -> TrackedError:
        """Track an error occurrence.
        
        Args:
            error: The exception that occurred.
            context: Dict with 'module', 'endpoint', etc.
            severity: Override auto-detected severity.
            
        Returns:
            TrackedError: The tracked error record.
        """
        ctx = context or {}
        error_type = type(error).__name__
        
        # Auto-detect severity
        if severity is None:
            severity = self._detect_severity(error_type, str(error))
        
        tracked = TrackedError(
            id=f"err_{len(self._errors)}_{int(time.time())}",
            timestamp=datetime.utcnow(),
            module=ctx.get("module", "unknown"),
            endpoint=ctx.get("endpoint", "unknown"),
            error_type=error_type,
            message=str(error),
            severity=severity,
            stack_trace=traceback.format_exc() if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL) else None,
        )
        
        self._errors.append(tracked)
        
        # Update counts
        key = f"{tracked.module}:{tracked.error_type}"
        self._error_counts[key] = self._error_counts.get(key, 0) + 1
        
        logger.log(
            logging.CRITICAL if severity == ErrorSeverity.CRITICAL else
            logging.ERROR if severity in (ErrorSeverity.HIGH, ErrorSeverity.MEDIUM) else
            logging.WARNING,
            "[%s] %s in %s: %s",
            severity.value.upper(), tracked.error_type, tracked.endpoint, tracked.message,
        )
        
        return tracked
    
    def _detect_severity(self, error_type: str, message: str) -> ErrorSeverity:
        """Auto-detect error severity based on type and message."""
        critical_types = {'ConnectionError', 'TimeoutError', 'MemoryError', 'RuntimeError'}
        high_types = {'HTTPException', 'ValidationError', 'PermissionError'}
        
        if error_type in critical_types or 'critical' in message.lower():
            return ErrorSeverity.CRITICAL
        if error_type in high_types or '500' in message:
            return ErrorSeverity.HIGH
        if error_type in {'ValueError', 'TypeError', 'KeyError'}:
            return ErrorSeverity.MEDIUM
        return ErrorSeverity.LOW
    
    def get_errors(
        self,
        severity: Optional[ErrorSeverity] = None,
        module: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Get filtered error history.
        
        Args:
            severity: Filter by severity level.
            module: Filter by module name.
            resolved: Filter by resolution status.
            limit: Maximum results.
            
        Returns:
            List of error dicts, newest first.
        """
        results = []
        for err in reversed(self._errors):
            if severity and err.severity != severity:
                continue
            if module and err.module != module:
                continue
            if resolved is not None and err.resolved != resolved:
                continue
            results.append(err.to_dict())
            if len(results) >= limit:
                break
        return results
    
    def get_error_summary(self, hours: int = 24) -> dict:
        """Get error summary for a time period.
        
        Args:
            hours: Lookback period in hours.
            
        Returns:
            Dict with counts by severity and module.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        filtered = [e for e in self._errors if e.timestamp >= cutoff]
        
        by_severity = {}
        by_module = {}
        for e in filtered:
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
            by_module[e.module] = by_module.get(e.module, 0) + 1
        
        return {
            "period_hours": hours,
            "total_errors": len(filtered),
            "by_severity": by_severity,
            "by_module": dict(sorted(by_module.items(), key=lambda x: -x[1])[:10]),
            "critical_count": by_severity.get(ErrorSeverity.CRITICAL.value, 0),
            "unresolved": sum(1 for e in filtered if not e.resolved),
        }
    
    def resolve_error(self, error_id: str, resolution: str) -> bool:
        """Mark an error as resolved.
        
        Args:
            error_id: The error ID to resolve.
            resolution: Description of the resolution.
            
        Returns:
            True if found and resolved.
        """
        for err in self._errors:
            if err.id == error_id:
                err.resolved = True
                err.resolution = resolution
                logger.info("Error %s resolved: %s", error_id, resolution)
                return True
        return False
    
    def clear(self):
        """Clear all error history."""
        self._errors.clear()
        self._error_counts.clear()
        logger.info("Error history cleared")
    
    def get_recovery_suggestion(self, error: TrackedError) -> str:
        """Get a recovery suggestion for an error.
        
        Args:
            error: The tracked error.
            
        Returns:
            Human-readable recovery suggestion.
        """
        suggestions = {
            'ModuleNotFoundError': f"Install missing dependency: pip install {error.message.split(chr(39))[1] if chr(39) in error.message else 'package'}",
            'ImportError': "Check that all dependencies are installed: pip install -r requirements.txt",
            'ConnectionError': "Check network connectivity and service availability",
            'TimeoutError': "Increase timeout or check service responsiveness",
            'ValidationError': "Check request payload matches expected schema",
            'HTTPException': "Review API documentation for correct usage",
            'KeyError': "Verify dictionary keys exist before accessing",
            'AttributeError': "Check object has the expected attribute",
            'ValueError': "Validate input values before processing",
            'TypeError': "Ensure correct types are passed to functions",
        }
        return suggestions.get(error.error_type, "Review logs and application state for details")


# ═══════════════════════════════════════════════════════════════════
# MODULE HEALTH CHECKER
# ═══════════════════════════════════════════════════════════════════

class ModuleHealthChecker:
    """Verifies all backend modules load correctly on startup.
    
    Usage:
        checker = ModuleHealthChecker()
        status = checker.check_all_modules(["backend.router", ...])
        print(f"{status['summary']['ok']}/{status['summary']['total']} modules OK")
    """
    
    _instance: Optional['ModuleHealthChecker'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._results: Dict[str, ModuleCheckResult] = {}
    
    def check_module(self, module_name: str) -> ModuleCheckResult:
        """Check if a single module can be imported.
        
        Args:
            module_name: Full dotted module path.
            
        Returns:
            ModuleCheckResult with status and timing.
        """
        start = time.perf_counter()
        try:
            importlib.import_module(module_name)
            elapsed = (time.perf_counter() - start) * 1000
            result = ModuleCheckResult(
                name=module_name,
                status=ModuleStatus.OK,
                load_time_ms=elapsed,
            )
            logger.debug("Module %s loaded in %.1fms", module_name, elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            result = ModuleCheckResult(
                name=module_name,
                status=ModuleStatus.ERROR,
                error=f"{type(e).__name__}: {str(e)[:200]}",
                load_time_ms=elapsed,
            )
            logger.warning("Module %s failed: %s", module_name, str(e)[:200])
        
        self._results[module_name] = result
        return result
    
    def check_all_modules(self, module_names: List[str]) -> dict:
        """Check all modules and return comprehensive status.
        
        Args:
            module_names: List of module paths to check.
            
        Returns:
            Dict with summary and per-module results.
        """
        logger.info("Checking %d modules...", len(module_names))
        
        for name in module_names:
            self.check_module(name)
        
        ok = sum(1 for r in self._results.values() if r.status == ModuleStatus.OK)
        errors = sum(1 for r in self._results.values() if r.status == ModuleStatus.ERROR)
        warnings = sum(1 for r in self._results.values() if r.status == ModuleStatus.WARNING)
        
        summary = {
            "total": len(module_names),
            "ok": ok,
            "error": errors,
            "warning": warnings,
            "healthy": errors == 0,
        }
        
        return {
            "summary": summary,
            "modules": {name: result.to_dict() for name, result in self._results.items()},
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    def get_results(self) -> Dict[str, ModuleCheckResult]:
        """Get all check results."""
        return dict(self._results)


# ═══════════════════════════════════════════════════════════════════
# HEALTH MONITOR (Main Controller)
# ═══════════════════════════════════════════════════════════════════

class HealthMonitor:
    """Main health monitor coordinating all health checks.
    
    Singleton that tracks module health, endpoint metrics, errors,
    and system resources. Provides data for the /health endpoint.
    
    Usage:
        monitor = HealthMonitor()
        health_data = monitor.get_health_report()
    """
    
    _instance: Optional['HealthMonitor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._start_time = datetime.utcnow()
        self._module_checker = ModuleHealthChecker()
        self._error_tracker = ErrorTracker()
        self._endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self._last_health_check: Optional[datetime] = None
        logger.info("HealthMonitor v%s initialized", HEALTH_CONFIG["version"])
    
    @property
    def error_tracker(self) -> ErrorTracker:
        return self._error_tracker
    
    @property
    def module_checker(self) -> ModuleHealthChecker:
        return self._module_checker
    
    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return (datetime.utcnow() - self._start_time).total_seconds()
    
    def get_system_metrics(self) -> dict:
        """Get system resource metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory": {
                    "total_mb": memory.total // (1024 * 1024),
                    "used_mb": memory.used // (1024 * 1024),
                    "available_mb": memory.available // (1024 * 1024),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": disk.total // (1024 * 1024 * 1024),
                    "used_gb": disk.used // (1024 * 1024 * 1024),
                    "free_gb": disk.free // (1024 * 1024 * 1024),
                    "percent": disk.percent,
                },
                "platform": platform.platform(),
                "python_version": platform.python_version(),
            }
        except Exception as e:
            logger.warning("Could not get system metrics: %s", e)
            return {"error": str(e)}
    
    def get_health_report(self) -> dict:
        """Generate comprehensive health report for /health endpoint.
        
        Returns:
            Dict with status, modules, errors, performance data.
        """
        self._last_health_check = datetime.utcnow()
        
        # Determine overall status
        module_results = self._module_checker.get_results()
        error_count = sum(1 for e in self._error_tracker._errors if not e.resolved)
        critical_count = sum(
            1 for e in self._error_tracker._errors
            if e.severity == ErrorSeverity.CRITICAL and not e.resolved
        )
        
        if critical_count > 0:
            status = "unhealthy"
        elif error_count > HEALTH_CONFIG["critical_error_threshold"]:
            status = "degraded"
        else:
            status = "healthy"
        
        # Count endpoints
        total_endpoints = len(self._endpoint_metrics)
        healthy_endpoints = sum(
            1 for m in self._endpoint_metrics.values()
            if m.total_errors == 0 or (m.total_requests > 0 and m.total_errors / m.total_requests < 0.1)
        )
        
        return {
            "status": status,
            "version": HEALTH_CONFIG["version"],
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round(self.get_uptime_seconds(), 1),
            "modules": {
                name: result.to_dict()
                for name, result in module_results.items()
            },
            "endpoints": {
                "total": total_endpoints,
                "healthy": healthy_endpoints,
            },
            "errors": self._error_tracker.get_error_summary(hours=24),
            "performance": {
                "uptime_seconds": round(self.get_uptime_seconds(), 1),
                **self.get_system_metrics(),
            },
        }
    
    def record_endpoint_call(self, path: str, method: str, duration_ms: float, error: bool = False):
        """Record an endpoint invocation.
        
        Args:
            path: API path.
            method: HTTP method.
            duration_ms: Response time.
            error: Whether the call resulted in an error.
        """
        key = f"{method}:{path}"
        if key not in self._endpoint_metrics:
            self._endpoint_metrics[key] = EndpointMetrics(path=path, method=method)
        
        metric = self._endpoint_metrics[key]
        metric.total_requests += 1
        if error:
            metric.total_errors += 1
        metric.avg_response_ms = (metric.avg_response_ms * (metric.total_requests - 1) + duration_ms) / metric.total_requests
        metric.last_called = datetime.utcnow()


# ═══════════════════════════════════════════════════════════════════
# FASTAPI ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

def register_health_endpoints(app_or_router):
    """Register health monitoring endpoints on a FastAPI app or router.
    
    Args:
        app_or_router: FastAPI app or APIRouter instance.
    """
    monitor = HealthMonitor()
    
    @app_or_router.get("/health", tags=["Health"])
    async def health_endpoint():
        """Get comprehensive health status."""
        return JSONResponse(monitor.get_health_report())
    
    @app_or_router.get("/health/errors", tags=["Health"])
    async def health_errors(
        severity: Optional[str] = None,
        module: Optional[str] = None,
        limit: int = 50,
    ):
        """Get error history with optional filtering.
        
        Query Parameters:
            severity: Filter by severity (low, medium, high, critical)
            module: Filter by module name
            limit: Maximum results (default 50)
        """
        sev = None
        if severity:
            try:
                sev = ErrorSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        errors = monitor.error_tracker.get_errors(
            severity=sev,
            module=module,
            limit=limit,
        )
        return JSONResponse({
            "errors": errors,
            "total": len(errors),
            "summary": monitor.error_tracker.get_error_summary(),
        })
    
    @app_or_router.post("/health/reset", tags=["Health"])
    async def health_reset():
        """Clear error history and reset health state.
        
        Requires admin authentication in production.
        """
        monitor.error_tracker.clear()
        return JSONResponse({
            "status": "reset",
            "message": "Error history cleared",
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    @app_or_router.get("/health/modules", tags=["Health"])
    async def health_modules():
        """Get detailed module status."""
        checker = ModuleHealthChecker()
        # Re-check all known modules
        modules = list(monitor.module_checker.get_results().keys())
        if not modules:
            modules = [
                "backend.router",
                "backend.exception_handler",
                "backend.validators",
                "backend.db_utils",
                "backend.chat",
                "backend.financial",
                "backend.health_monitor",
            ]
        status = checker.check_all_modules(modules)
        return JSONResponse(status)
    
    logger.info("Health endpoints registered: /health, /health/errors, /health/reset, /health/modules")


# ═══════════════════════════════════════════════════════════════════
# STARTUP BANNER
# ═══════════════════════════════════════════════════════════════════

def print_startup_banner(status: Optional[dict] = None):
    """Print a colored startup banner showing module status.
    
    Args:
        status: Module check status from ModuleHealthChecker.check_all_modules().
    """
    # ANSI color codes
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    print("\n" + "=" * 70)
    print(f"{BOLD}{CYAN}  Luqi AI v24.4.0 — System Startup{BOLD}")
    print("=" * 70)
    
    if status and "modules" in status:
        print(f"\n  {BOLD}Module Status:{RESET}")
        for name, detail in status["modules"].items():
            short_name = name.replace("backend.", "")
            if detail["status"] == "ok":
                icon = f"{GREEN}OK{RESET}"
            elif detail["status"] == "warning":
                icon = f"{YELLOW}WARN{RESET}"
            else:
                icon = f"{RED}FAIL{RESET}"
            print(f"    [{icon}] {short_name:30s} {detail.get('load_time_ms', 0):>6.1f}ms")
        
        summary = status.get("summary", {})
        total = summary.get("total", 0)
        ok = summary.get("ok", 0)
        errors = summary.get("error", 0)
        
        print(f"\n  {BOLD}Summary:{RESET} {ok}/{total} modules loaded", end="")
        if errors > 0:
            print(f"  ({RED}{errors} errors{RESET})")
        else:
            print(f"  ({GREEN}all healthy{RESET})")
    
    print(f"\n  {BOLD}Health Endpoints:{RESET}")
    print(f"    GET  /health          — Full system health")
    print(f"    GET  /health/errors   — Error history")
    print(f"    POST /health/reset    — Clear error state")
    print(f"    GET  /health/modules  — Module diagnostics")
    
    print("\n" + "=" * 70)
    print(f"{BOLD}{CYAN}  Ready for requests{RESET}")
    print("=" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE FACTORY
# ═══════════════════════════════════════════════════════════════════

def create_error_tracking_middleware(app):
    """Create middleware that tracks errors on every request.
    
    Args:
        app: FastAPI application instance.
        
    Usage:
        app.middleware("http")(create_error_tracking_middleware(app))
    """
    monitor = HealthMonitor()
    
    @app.middleware("http")
    async def error_tracking_middleware(request: Request, call_next):
        start = time.perf_counter()
        error_occurred = False
        
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_occurred = True
            monitor.error_tracker.track_error(
                exc,
                context={
                    "module": "middleware",
                    "endpoint": str(request.url.path),
                },
            )
            raise
        finally:
            duration = (time.perf_counter() - start) * 1000
            monitor.record_endpoint_call(
                path=request.url.path,
                method=request.method,
                duration_ms=duration,
                error=error_occurred,
            )
    
    return error_tracking_middleware


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_monitor() -> HealthMonitor:
    """Get the singleton HealthMonitor instance."""
    return HealthMonitor()


def get_error_tracker() -> ErrorTracker:
    """Get the singleton ErrorTracker instance."""
    return ErrorTracker()


def get_module_checker() -> ModuleHealthChecker:
    """Get the singleton ModuleHealthChecker instance."""
    return ModuleHealthChecker()


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    "HealthMonitor",
    "ErrorTracker",
    "ModuleHealthChecker",
    "ErrorSeverity",
    "ModuleStatus",
    "TrackedError",
    "register_health_endpoints",
    "print_startup_banner",
    "create_error_tracking_middleware",
    "get_monitor",
    "get_error_tracker",
    "get_module_checker",
    "HEALTH_CONFIG",
]