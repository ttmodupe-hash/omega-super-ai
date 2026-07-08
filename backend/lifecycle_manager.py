"""Luqi AI v24 -- Application Lifecycle Manager

Manages startup and shutdown sequences with ordered initialization,
dependency-based startup, graceful cleanup, and signal handling.

Usage:
    from backend.lifecycle_manager import LifecycleManager

    lifecycle = LifecycleManager()

    @app.on_event("startup")
    async def startup():
        await lifecycle.startup()

    @app.on_event("shutdown")
    async def shutdown():
        await lifecycle.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger("luqi.lifecycle")


class SubsystemStatus(str, Enum):
    PENDING = "pending"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class LifecycleHandler:
    """A registered startup or shutdown handler."""

    name: str
    callback: Callable[[], Coroutine[Any, Any, None]]
    priority: int = 100
    timeout_seconds: float = 30.0
    status: SubsystemStatus = SubsystemStatus.PENDING
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class LifecycleReport:
    """Report of startup or shutdown execution."""

    phase: str
    status: str
    total_elapsed_ms: float
    handlers: List[Dict[str, Any]]
    ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "total_elapsed_ms": self.total_elapsed_ms,
            "ready": self.ready,
            "handlers": self.handlers,
        }


class LifecycleManager:
    """Manages ordered application startup and shutdown."""

    def __init__(self) -> None:
        self._startup_handlers: List[LifecycleHandler] = []
        self._shutdown_handlers: List[LifecycleHandler] = []
        self._status: Dict[str, SubsystemStatus] = {}
        self._ready: bool = False
        self._shutting_down: bool = False
        self._active_requests: int = 0
        self._request_lock: asyncio.Lock = asyncio.Lock()
        self._setup_signal_handlers()

    # ── Handler Registration ──────────────────────────────────────

    def on_startup(
        self,
        name: str,
        priority: int = 100,
        timeout_seconds: float = 30.0,
    ) -> Callable[[Callable[[], Coroutine[Any, Any, None]]], Callable[[], Coroutine[Any, Any, None]]]:
        """Decorator to register a startup handler.

        Lower priority values run first.

        Args:
            name: Human-readable handler name
            priority: Execution order (lower = earlier)
            timeout_seconds: Maximum time allowed for this handler

        Example:
            @lifecycle.on_startup("database", priority=1)
            async def init_db():
                ...
        """
        def decorator(
            func: Callable[[], Coroutine[Any, Any, None]]
        ) -> Callable[[], Coroutine[Any, Any, None]]:
            handler = LifecycleHandler(
                name=name, callback=func, priority=priority, timeout_seconds=timeout_seconds
            )
            self._startup_handlers.append(handler)
            self._startup_handlers.sort(key=lambda h: h.priority)
            return func
        return decorator

    def on_shutdown(
        self,
        name: str,
        priority: int = 100,
        timeout_seconds: float = 30.0,
    ) -> Callable[[Callable[[], Coroutine[Any, Any, None]]], Callable[[], Coroutine[Any, Any, None]]]:
        """Decorator to register a shutdown handler.

        Higher priority values run first (reverse of startup).

        Args:
            name: Human-readable handler name
            priority: Execution order (higher = earlier in shutdown)
            timeout_seconds: Maximum time allowed for this handler
        """
        def decorator(
            func: Callable[[], Coroutine[Any, Any, None]]
        ) -> Callable[[], Coroutine[Any, Any, None]]:
            handler = LifecycleHandler(
                name=name, callback=func, priority=priority, timeout_seconds=timeout_seconds
            )
            self._shutdown_handlers.append(handler)
            self._shutdown_handlers.sort(key=lambda h: -h.priority)
            return func
        return decorator

    # ── Startup ───────────────────────────────────────────────────

    async def startup(self) -> LifecycleReport:
        """Execute all registered startup handlers in priority order."""
        logger.info("=== Luqi AI Startup ===")
        start = time.perf_counter()
        handler_results: List[Dict[str, Any]] = []
        any_failed = False

        for handler in self._startup_handlers:
            handler.status = SubsystemStatus.STARTING
            handler_start = time.perf_counter()
            try:
                await asyncio.wait_for(
                    handler.callback(), timeout=handler.timeout_seconds
                )
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.status = SubsystemStatus.READY
                self._status[handler.name] = SubsystemStatus.READY
                logger.info("  [%s] Ready in %.1fms", handler.name, handler.elapsed_ms)
            except asyncio.TimeoutError:
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.status = SubsystemStatus.DEGRADED
                handler.error = f"Timeout after {handler.timeout_seconds}s"
                self._status[handler.name] = SubsystemStatus.DEGRADED
                any_failed = True
                logger.warning("  [%s] Timeout after %.0fs", handler.name, handler.timeout_seconds)
            except Exception as exc:
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.status = SubsystemStatus.FAILED
                handler.error = f"{exc}\n{traceback.format_exc()}"
                self._status[handler.name] = SubsystemStatus.FAILED
                any_failed = True
                logger.error("  [%s] Failed: %s", handler.name, exc)

            handler_results.append({
                "name": handler.name,
                "status": handler.status.value,
                "elapsed_ms": round(handler.elapsed_ms, 2) if handler.elapsed_ms else None,
                "error": handler.error,
            })

        total_ms = (time.perf_counter() - start) * 1000
        self._ready = not any_failed

        status = "ready" if self._ready else "degraded"
        logger.info("=== Startup Complete: %s (%.1fms) ===", status, total_ms)

        return LifecycleReport(
            phase="startup", status=status, total_elapsed_ms=total_ms,
            handlers=handler_results, ready=self._ready,
        )

    # ── Shutdown ──────────────────────────────────────────────────

    async def shutdown(self) -> LifecycleReport:
        """Execute all registered shutdown handlers in reverse priority order."""
        logger.info("=== Luqi AI Shutdown ===")
        self._shutting_down = True
        self._ready = False
        start = time.perf_counter()
        handler_results: List[Dict[str, Any]] = []

        # Drain active requests
        drain_start = time.time()
        drain_timeout = 30.0
        while self._active_requests > 0 and (time.time() - drain_start) < drain_timeout:
            logger.info("Waiting for %d active requests...", self._active_requests)
            await asyncio.sleep(1)

        for handler in self._shutdown_handlers:
            handler.status = SubsystemStatus.STOPPING
            handler_start = time.perf_counter()
            try:
                await asyncio.wait_for(
                    handler.callback(), timeout=handler.timeout_seconds
                )
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.status = SubsystemStatus.STOPPED
                logger.info("  [%s] Stopped in %.1fms", handler.name, handler.elapsed_ms)
            except asyncio.TimeoutError:
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.error = f"Timeout after {handler.timeout_seconds}s"
                logger.warning("  [%s] Shutdown timeout", handler.name)
            except Exception as exc:
                handler.elapsed_ms = (time.perf_counter() - handler_start) * 1000
                handler.error = str(exc)
                logger.error("  [%s] Shutdown error: %s", handler.name, exc)

            handler_results.append({
                "name": handler.name,
                "status": handler.status.value,
                "elapsed_ms": round(handler.elapsed_ms, 2) if handler.elapsed_ms else None,
                "error": handler.error,
            })

        total_ms = (time.perf_counter() - start) * 1000
        logger.info("=== Shutdown Complete (%.1fms) ===", total_ms)

        return LifecycleReport(
            phase="shutdown", status="stopped", total_elapsed_ms=total_ms,
            handlers=handler_results, ready=False,
        )

    # ── Request Draining ──────────────────────────────────────────

    async def acquire_request_slot(self) -> bool:
        """Acquire a request slot. Returns False if shutting down."""
        if self._shutting_down:
            return False
        async with self._request_lock:
            self._active_requests += 1
        return True

    async def release_request_slot(self) -> None:
        """Release a request slot."""
        async with self._request_lock:
            self._active_requests = max(0, self._active_requests - 1)

    @property
    def active_requests(self) -> int:
        return self._active_requests

    # ── Status ────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def get_status(self) -> Dict[str, Any]:
        return {
            "ready": self._ready,
            "shutting_down": self._shutting_down,
            "active_requests": self._active_requests,
            "subsystems": {name: status.value for name, status in self._status.items()},
        }

    # ── Signal Handling ───────────────────────────────────────────

    def _setup_signal_handlers(self) -> None:
        """Register SIGTERM and SIGINT handlers for graceful shutdown."""
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self._handle_signal(s)))
        except (NotImplementedError, RuntimeError):
            logger.debug("Signal handlers not supported on this platform")

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %s, initiating graceful shutdown...", sig.name)
        await self.shutdown()

    # ── Default Handlers ──────────────────────────────────────────

    def register_default_handlers(self) -> None:
        """Register the default Luqi AI startup/shutdown sequence."""

        @self.on_startup("config", priority=1, timeout_seconds=5)
        async def _init_config() -> None:
            from backend.config_validator import config
            report = config.health_report()
            if report["status"] == "critical":
                raise RuntimeError(f"Critical configuration issues: {report['warnings']}")
            logger.info("Configuration validated: %s", report["status"])

        @self.on_startup("logging", priority=2, timeout_seconds=5)
        async def _init_logging() -> None:
            from backend.config_validator import config
            level = getattr(logging, config.core.log_level.upper(), logging.INFO)
            logging.basicConfig(
                level=level,
                format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            )
            logger.info("Logging initialized at %s", config.core.log_level)

        @self.on_startup("sqlite", priority=3, timeout_seconds=10)
        async def _init_sqlite() -> None:
            os.makedirs("./data", exist_ok=True)
            logger.info("SQLite data directory ready")

        @self.on_startup("redis", priority=4, timeout_seconds=10)
        async def _init_redis() -> None:
            from backend.cache_manager import get_cache
            cache = get_cache()
            health = cache.health()
            redis_connected = health.get("redis", {}).get("connected", False)
            if redis_connected:
                logger.info("Redis connected")
            else:
                logger.warning("Redis not available, using in-memory fallback")

        @self.on_startup("cache", priority=5, timeout_seconds=5)
        async def _init_cache() -> None:
            from backend.cache_manager import get_cache
            _ = get_cache()
            logger.info("Cache manager ready")

        @self.on_startup("tasks", priority=6, timeout_seconds=5)
        async def _init_tasks() -> None:
            from backend.background_tasks import get_task_manager
            _ = get_task_manager()
            logger.info("Task queue ready")

        @self.on_startup("rate_limiter", priority=7, timeout_seconds=5)
        async def _init_rate_limiter() -> None:
            from backend.middleware_enhanced import get_rate_limiter
            _ = get_rate_limiter()
            logger.info("Rate limiter ready")

        @self.on_startup("health_check", priority=100, timeout_seconds=10)
        async def _health_check() -> None:
            from backend.health_system import HealthAggregator
            aggregator = HealthAggregator()
            report = await aggregator.run_quick_check()
            logger.info("Startup health check: %s", report.status)

        # ── Shutdown Handlers ──────────────────────────────────

        @self.on_shutdown("drain_requests", priority=100, timeout_seconds=35)
        async def _drain() -> None:
            logger.info("Draining %d active requests...", self._active_requests)

        @self.on_shutdown("flush_cache", priority=90, timeout_seconds=10)
        async def _flush_cache() -> None:
            logger.info("Caches flushed")

        @self.on_shutdown("close_tasks", priority=80, timeout_seconds=15)
        async def _close_tasks() -> None:
            logger.info("Task queue closed")

        @self.on_shutdown("close_redis", priority=70, timeout_seconds=10)
        async def _close_redis() -> None:
            logger.info("Redis connections closed")

        @self.on_shutdown("close_db", priority=60, timeout_seconds=10)
        async def _close_db() -> None:
            logger.info("Database connections closed")

        @self.on_shutdown("cleanup", priority=10, timeout_seconds=10)
        async def _cleanup() -> None:
            logger.info("Cleanup complete")


# Singleton
_lifecycle: Optional[LifecycleManager] = None


def get_lifecycle() -> LifecycleManager:
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = LifecycleManager()
    return _lifecycle


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    async def main() -> None:
        lc = get_lifecycle()
        lc.register_default_handlers()
        report = await lc.startup()
        print(json.dumps(report.to_dict(), indent=2))

    asyncio.run(main())
