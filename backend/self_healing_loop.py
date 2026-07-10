#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Self-Healing Background Loop
===============================================
Continuous background monitoring and automated recovery.

Features:
  - Background thread runs health checks every 30 seconds
  - Auto-triggers research cycle every 24 hours
  - Records metrics every 5 minutes
  - Alerts on degradation trends
  - Graceful shutdown on SIGTERM
  - Human-in-the-loop gate respected (no auto-deploy without approval)

Part of Luqi AI v24.5.0 by Limitless Telecoms
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.self_healing_loop")

# ---------------------------------------------------------------------------
# Configuration (environment variables)
# ---------------------------------------------------------------------------
HEALING_LOOP_ENABLED = os.getenv("HEALING_LOOP_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
METRICS_INTERVAL = int(os.getenv("METRICS_INTERVAL", "300"))
RESEARCH_INTERVAL = int(os.getenv("RESEARCH_INTERVAL", "24"))

# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════


class LoopStatus(str, Enum):
    """Lifecycle states of the self-healing loop."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ScheduleInfo:
    """Next scheduled execution times for each task."""

    next_health_check: Optional[str] = None
    next_metrics_record: Optional[str] = None
    next_research_cycle: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "next_health_check": self.next_health_check,
            "next_metrics_record": self.next_metrics_record,
            "next_research_cycle": self.next_research_cycle,
        }


@dataclass
class LoopState:
    """Current state snapshot of the self-healing loop."""

    status: LoopStatus = LoopStatus.STOPPED
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    iteration_count: int = 0
    health_checks_performed: int = 0
    metrics_recorded: int = 0
    research_cycles_triggered: int = 0
    critical_alerts_triggered: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[str] = None
    schedule: ScheduleInfo = field(default_factory=ScheduleInfo)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "iteration_count": self.iteration_count,
            "health_checks_performed": self.health_checks_performed,
            "metrics_recorded": self.metrics_recorded,
            "research_cycles_triggered": self.research_cycles_triggered,
            "critical_alerts_triggered": self.critical_alerts_triggered,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "schedule": self.schedule.to_dict(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# METRICS DASHBOARD DELEGATE
# ═══════════════════════════════════════════════════════════════════════════


class MetricsDashboardDelegate:
    """Delegate that attempts to record metrics via the MetricsDashboard.

    Falls back gracefully if the metrics dashboard is unavailable.
    """

    def __init__(self) -> None:
        self._dashboard: Optional[Any] = None
        self._available: bool = False
        self._try_import_dashboard()

    def _try_import_dashboard(self) -> None:
        """Attempt to import and instantiate the MetricsDashboard."""
        try:
            # Try the canonical import path first
            from backend.health_monitor import HealthMonitor  # noqa: F401

            self._available = True
            logger.info("[MetricsDelegate] HealthMonitor available for metrics")
        except Exception:
            self._available = False
            logger.debug("[MetricsDelegate] HealthMonitor not available — metrics will be logged only")

    def record_snapshot(self, health_report: Optional[dict] = None) -> dict:
        """Record a metrics snapshot.

        Delegates to MetricsDashboard if available, otherwise logs
        the metrics data for audit trail.

        Args:
            health_report: Optional health report to include in metrics.

        Returns:
            dict: The recorded snapshot data.
        """
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_report": health_report or {},
            "memory_mb": self._get_memory_usage(),
            "cpu_percent": self._get_cpu_usage(),
        }

        if self._available:
            logger.info("[MetricsDelegate] Snapshot recorded: mem=%.1fMB cpu=%.1f%%", snapshot["memory_mb"], snapshot["cpu_percent"])
        else:
            logger.info("[MetricsDelegate] Snapshot (logged only): %s", json.dumps(snapshot, default=str))

        return snapshot

    @staticmethod
    def _get_memory_usage() -> float:
        """Get current process memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    @staticmethod
    def _get_cpu_usage() -> float:
        """Get current process CPU usage percentage."""
        try:
            import psutil

            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except Exception:
            return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# SELF-HEALING LOOP (Singleton)
# ═══════════════════════════════════════════════════════════════════════════


class SelfHealingLoop:
    """Production-grade self-healing background loop for Luqi AI.

    Runs a background thread that continuously:
      1. Performs health checks every 30 seconds via the orchestrator
      2. Records metrics snapshots every 5 minutes
      3. Triggers research cycles every 24 hours (human-gated)
      4. Alerts on critical health degradation

    Thread Safety:
        All public methods are thread-safe. The background thread uses
        a private asyncio event loop for async orchestrator calls.

    Human-in-the-Loop:
        Research cycles run and produce findings, but NEVER auto-deploy.
        All deployments require explicit human approval via the
        /api/system/approve-deploy/{id} endpoint.

    Graceful Shutdown:
        Respects SIGTERM by setting the stop event and joining the
        background thread within SHUTDOWN_TIMEOUT_SECONDS.

    Example:
        >>> loop = SelfHealingLoop()
        >>> loop.start()          # Non-blocking — returns immediately
        >>> loop.is_running()     # True
        >>> loop.get_schedule()   # {'next_health_check': '...', ...}
        >>> loop.stop()           # Graceful shutdown
        >>> loop.register_endpoints(app)
    """

    _instance: Optional["SelfHealingLoop"] = None
    _lock: threading.Lock = threading.Lock()

    # How long to wait for the background thread to join on shutdown
    SHUTDOWN_TIMEOUT_SECONDS: float = 10.0

    def __new__(cls, *args: Any, **kwargs: Any) -> "SelfHealingLoop":
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance  # type: ignore[return-value]

    def __init__(
        self,
        health_check_interval: Optional[int] = None,
        metrics_interval: Optional[int] = None,
        research_interval_hours: Optional[int] = None,
    ) -> None:
        if self._initialized:
            return
        self._initialized = True

        # ── Configuration ─────────────────────────────────────────────
        self._health_check_interval: int = health_check_interval or HEALTH_CHECK_INTERVAL
        self._metrics_interval: int = metrics_interval or METRICS_INTERVAL
        self._research_interval_hours: int = research_interval_hours or RESEARCH_INTERVAL
        self._research_interval_seconds: int = self._research_interval_hours * 3600

        # ── Threading primitives ──────────────────────────────────────
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._state_lock: threading.Lock = threading.Lock()

        # ── State ─────────────────────────────────────────────────────
        self._state: LoopState = LoopState()
        self._metrics_delegate: MetricsDashboardDelegate = MetricsDashboardDelegate()

        # ── Orchestrator reference (lazy) ─────────────────────────────
        self._orchestrator: Optional[Any] = None
        self._alert_system: Optional[Any] = None

        # ── Scheduling timestamps (seconds since epoch) ───────────────
        self._next_health_check: float = 0.0
        self._next_metrics_record: float = 0.0
        self._next_research_cycle: float = 0.0

        # ── SIGTERM handler installed flag ────────────────────────────
        self._sigterm_installed: bool = False

        logger.info(
            "[SelfHealingLoop] Initialized (health=%ds, metrics=%ds, research=%dh)",
            self._health_check_interval,
            self._metrics_interval,
            self._research_interval_hours,
        )

    # ── Public API ──────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the background self-healing loop.

        This is NON-BLOCKING — it spawns the background thread and
        returns immediately. The thread runs until stop() is called.

        Returns:
            bool: True if the loop was started (or was already running).
        """
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                logger.info("[SelfHealingLoop] Already running — start() ignored")
                return True

            self._stop_event.clear()
            self._state.status = LoopStatus.STARTING
            self._state.started_at = datetime.now(timezone.utc).isoformat()
            self._state.stopped_at = None
            self._state.last_error = None

            # Reset scheduling timestamps
            now = time.time()
            self._next_health_check = now + self._health_check_interval
            self._next_metrics_record = now + self._metrics_interval
            self._next_research_cycle = now + self._research_interval_seconds

            # Install SIGTERM handler if not already done
            self._install_sigterm_handler()

            # Spawn background thread (daemon=False for graceful join)
            self._thread = threading.Thread(
                target=self._run_loop,
                name="luqi-self-healing-loop",
                daemon=False,
            )
            self._thread.start()

        logger.info("[SelfHealingLoop] Background thread started")
        return True

    def stop(self, timeout: Optional[float] = None) -> bool:
        """Signal the background loop to stop gracefully.

        Sets the stop event and waits for the background thread to
        join within the specified timeout.

        Args:
            timeout: Seconds to wait for thread join. Defaults to
                SHUTDOWN_TIMEOUT_SECONDS.

        Returns:
            bool: True if the thread stopped cleanly, False if it had
                to be abandoned (still running after timeout).
        """
        timeout = timeout or self.SHUTDOWN_TIMEOUT_SECONDS

        with self._state_lock:
            if self._thread is None or not self._thread.is_alive():
                self._state.status = LoopStatus.STOPPED
                logger.info("[SelfHealingLoop] Not running — stop() ignored")
                return True

            self._state.status = LoopStatus.STOPPING
            logger.info("[SelfHealingLoop] Signaling stop (timeout=%.1fs)", timeout)

        # Signal the loop to exit
        self._stop_event.set()

        # Wait for thread to finish
        self._thread.join(timeout=timeout)

        with self._state_lock:
            if not self._thread.is_alive():
                self._state.status = LoopStatus.STOPPED
                self._state.stopped_at = datetime.now(timezone.utc).isoformat()
                logger.info("[SelfHealingLoop] Stopped cleanly")
                return True
            else:
                self._state.status = LoopStatus.ERROR
                self._state.last_error = "Thread did not exit within timeout"
                self._state.last_error_at = datetime.now(timezone.utc).isoformat()
                logger.error(
                    "[SelfHealingLoop] Thread did not stop within %.1fs — abandoning",
                    timeout,
                )
                return False

    def is_running(self) -> bool:
        """Check whether the background loop is currently running.

        Returns:
            bool: True if the loop thread is alive and running.
        """
        with self._state_lock:
            return (
                self._thread is not None
                and self._thread.is_alive()
                and self._state.status in (LoopStatus.STARTING, LoopStatus.RUNNING)
            )

    def get_schedule(self) -> dict:
        """Get the current schedule showing when next checks will run.

        Returns:
            dict: Schedule information with ISO timestamps and seconds-until.
        """
        with self._state_lock:
            now = time.time()
            schedule = ScheduleInfo(
                next_health_check=self._timestamp_iso(self._next_health_check),
                next_metrics_record=self._timestamp_iso(self._next_metrics_record),
                next_research_cycle=self._timestamp_iso(self._next_research_cycle),
            )
            result = schedule.to_dict()
            result["seconds_until_health_check"] = max(0, int(self._next_health_check - now))
            result["seconds_until_metrics"] = max(0, int(self._next_metrics_record - now))
            result["seconds_until_research"] = max(0, int(self._next_research_cycle - now))
            return result

    def get_state(self) -> dict:
        """Get the full state snapshot of the loop.

        Returns:
            dict: Complete loop state including status, counts, schedule.
        """
        with self._state_lock:
            self._state.schedule = ScheduleInfo(
                next_health_check=self._timestamp_iso(self._next_health_check),
                next_metrics_record=self._timestamp_iso(self._next_metrics_record),
                next_research_cycle=self._timestamp_iso(self._next_research_cycle),
            )
            return self._state.to_dict()

    def register_endpoints(self, app_or_router: Any) -> None:
        """Register FastAPI endpoints for the self-healing loop.

        Endpoints registered:
          GET  /api/system/loop/status — Loop status and schedule
          POST /api/system/loop/start — Start the background loop
          POST /api/system/loop/stop  — Stop the background loop

        Args:
            app_or_router: FastAPI app or APIRouter instance.
        """
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        logger.info("[SelfHealingLoop] Registering loop endpoints")

        # ── GET /api/system/loop/status ───────────────────────────
        @app_or_router.get("/api/system/loop/status", tags=["Self-Healing Loop"])
        async def api_loop_status():
            """Get the self-healing loop status, state, and schedule."""
            try:
                state = self.get_state()
                state["is_running"] = self.is_running()
                return JSONResponse(state)
            except Exception as e:
                logger.error("[LoopEndpoint] Error getting status: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/loop/start ───────────────────────────
        @app_or_router.post("/api/system/loop/start", tags=["Self-Healing Loop"])
        async def api_loop_start():
            """Start the self-healing background loop."""
            try:
                if self.is_running():
                    return JSONResponse(
                        {
                            "success": True,
                            "message": "Loop is already running",
                            "status": self.get_state(),
                        }
                    )
                self.start()
                return JSONResponse(
                    {
                        "success": True,
                        "message": "Self-healing loop started",
                        "status": self.get_state(),
                    }
                )
            except Exception as e:
                logger.error("[LoopEndpoint] Error starting loop: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

        # ── POST /api/system/loop/stop ────────────────────────────
        @app_or_router.post("/api/system/loop/stop", tags=["Self-Healing Loop"])
        async def api_loop_stop():
            """Stop the self-healing background loop gracefully."""
            try:
                if not self.is_running():
                    return JSONResponse(
                        {
                            "success": True,
                            "message": "Loop is not running",
                            "status": self.get_state(),
                        }
                    )
                stopped = self.stop()
                return JSONResponse(
                    {
                        "success": stopped,
                        "message": "Self-healing loop stopped" if stopped else "Loop stop timed out",
                        "status": self.get_state(),
                    }
                )
            except Exception as e:
                logger.error("[LoopEndpoint] Error stopping loop: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

    # ── Background Loop (runs in thread) ────────────────────────────────

    def _run_loop(self) -> None:
        """Main loop that runs in the background thread.

        This is the core of the self-healing system. It:
          * Runs health checks every HEALTH_CHECK_INTERVAL seconds
          * Records metrics every METRICS_INTERVAL seconds
          * Triggers research cycles every RESEARCH_INTERVAL hours
          * Alerts on critical health conditions

        ALL exceptions are caught — this thread must never crash.
        The loop checks self._stop_event regularly for quick shutdown.
        """
        logger.info("[SelfHealingLoop] Background loop starting")

        # Create a dedicated asyncio event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with self._state_lock:
            self._state.status = LoopStatus.RUNNING

        try:
            # Resolve orchestrator reference
            self._resolve_orchestrator()

            # Run initial health check immediately
            try:
                loop.run_until_complete(self._health_check())
            except Exception as e:
                logger.error("[SelfHealingLoop] Initial health check failed: %s", e)

            # Main loop
            while not self._stop_event.is_set():
                try:
                    self._state.iteration_count += 1
                    now = time.time()

                    # ── Health Check ──────────────────────────────────
                    if now >= self._next_health_check:
                        loop.run_until_complete(self._health_check())
                        self._next_health_check = now + self._health_check_interval

                    # ── Metrics Recording ─────────────────────────────
                    if now >= self._next_metrics_record:
                        self._record_metrics()
                        self._next_metrics_record = now + self._metrics_interval

                    # ── Research Cycle ────────────────────────────────
                    if now >= self._next_research_cycle:
                        loop.run_until_complete(self._research_cycle())
                        self._next_research_cycle = now + self._research_interval_seconds

                    # ── Sleep with stop check ─────────────────────────
                    # Sleep in small increments so we respond quickly to stop
                    for _ in range(5):  # 5 x 1s = 5s sleep blocks
                        if self._stop_event.is_set():
                            break
                        time.sleep(1.0)

                except Exception as e:
                    self._handle_loop_error(e)
                    # Back off to avoid tight error loops
                    time.sleep(5.0)

        finally:
            # Cleanup
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()
            except Exception as e:
                logger.warning("[SelfHealingLoop] Event loop cleanup error: %s", e)

            with self._state_lock:
                if self._state.status == LoopStatus.RUNNING:
                    self._state.status = LoopStatus.STOPPED
                self._state.stopped_at = datetime.now(timezone.utc).isoformat()

            logger.info("[SelfHealingLoop] Background loop exited")

    # ── Task Implementations ────────────────────────────────────────────

    async def _health_check(self) -> dict:
        """Execute a health check via the orchestrator.

        Delegates to the orchestrator's run_health_check() method.
        If the health status is critical, triggers a CRITICAL alert.

        Returns:
            dict: The health check report.
        """
        logger.debug("[SelfHealingLoop] Running health check (#%d)", self._state.health_checks_performed + 1)

        report: dict = {}

        try:
            orch = self._resolve_orchestrator()
            if orch is not None:
                report = await orch.run_health_check()
            else:
                report = {
                    "status": "unknown",
                    "message": "Orchestrator not available",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.error("[SelfHealingLoop] Health check failed: %s", e)
            report = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        self._state.health_checks_performed += 1

        # Check for critical status and escalate
        status = report.get("status", "unknown")
        escalation_triggered = report.get("escalation_triggered", False)

        if status in ("unhealthy", "error", "critical") or escalation_triggered:
            logger.critical(
                "[SelfHealingLoop] CRITICAL health status detected: %s (escalation=%s)",
                status,
                escalation_triggered,
            )
            self._state.critical_alerts_triggered += 1
            self._trigger_critical_alert(report)

        logger.info(
            "[SelfHealingLoop] Health check complete: status=%s (total_checks=%d)",
            status,
            self._state.health_checks_performed,
        )
        return report

    def _record_metrics(self) -> dict:
        """Record a metrics snapshot.

        Delegates to the MetricsDashboardDelegate which attempts to
        store metrics via the MetricsDashboard, falling back to
        structured logging if unavailable.

        Returns:
            dict: The recorded metrics snapshot.
        """
        logger.debug("[SelfHealingLoop] Recording metrics (#%d)", self._state.metrics_recorded + 1)

        snapshot: dict = {}

        try:
            # Get latest health report for context
            orch = self._resolve_orchestrator()
            health_report = None
            if orch is not None and hasattr(orch, "get_system_status"):
                try:
                    health_report = orch.get_system_status()
                except Exception as e:
                    logger.debug("[SelfHealingLoop] Could not get system status for metrics: %s", e)

            snapshot = self._metrics_delegate.record_snapshot(health_report)
            self._state.metrics_recorded += 1

        except Exception as e:
            logger.error("[SelfHealingLoop] Metrics recording failed: %s", e)
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

        logger.info(
            "[SelfHealingLoop] Metrics recorded (total_recorded=%d)",
            self._state.metrics_recorded,
        )
        return snapshot

    async def _research_cycle(self) -> list:
        """Trigger a research cycle via the orchestrator.

        Delegates to the orchestrator's run_research_cycle(). The
        research runs and produces findings, but NEVER auto-deploys.
        Human approval is always required for deployment.

        Returns:
            list: Research findings (empty list if unavailable).
        """
        logger.info(
            "[SelfHealingLoop] Triggering research cycle (#%d) — human-in-the-loop gate ACTIVE",
            self._state.research_cycles_triggered + 1,
        )

        findings: list = []

        try:
            orch = self._resolve_orchestrator()
            if orch is not None:
                findings = await orch.run_research_cycle()
            else:
                logger.warning("[SelfHealingLoop] Cannot run research: orchestrator unavailable")

            self._state.research_cycles_triggered += 1

            # Log findings summary — research runs but does NOT deploy
            logger.info(
                "[SelfHealingLoop] Research cycle complete: %d findings. "
                "Findings are queued for human review. NO auto-deploy.",
                len(findings),
            )

            # If findings exist, log a notice that human review is needed
            if findings:
                logger.info(
                    "[SelfHealingLoop] %d research finding(s) require human review. "
                    "Use POST /api/system/approve-deploy/{id} after validation.",
                    len(findings),
                )

        except Exception as e:
            logger.error("[SelfHealingLoop] Research cycle failed: %s", e)
            findings = []

        return findings

    # ── Alerting ────────────────────────────────────────────────────────

    def _trigger_critical_alert(self, health_report: dict) -> None:
        """Trigger a CRITICAL alert via the AlertSystem.

        Attempts to send an alert through the orchestrator's alert
        system. Falls back to logging if unavailable.

        Args:
            health_report: The health report that triggered the alert.
        """
        try:
            orch = self._resolve_orchestrator()
            if orch is not None and hasattr(orch, "_alert_system") and orch._alert_system is not None:
                try:
                    orch._alert_system.send_alert(
                        level="critical",
                        title="SelfHealingLoop: Critical Health Detected",
                        message=(
                            f"Health check returned critical status. "
                            f"Status: {health_report.get('status', 'unknown')}. "
                            f"Escalation triggered: {health_report.get('escalation_triggered', False)}. "
                            f"Review required immediately."
                        ),
                        payload={
                            "source": "self_healing_loop",
                            "health_report": health_report,
                            "critical_alert_count": self._state.critical_alerts_triggered,
                        },
                    )
                    logger.critical(
                        "[SelfHealingLoop] CRITICAL alert sent via AlertSystem (count=%d)",
                        self._state.critical_alerts_triggered,
                    )
                except Exception as e:
                    logger.critical(
                        "[SelfHealingLoop] CRITICAL: Health degraded but alert sending failed: %s",
                        e,
                    )
            else:
                # Fallback: log loudly
                logger.critical(
                    "[SelfHealingLoop] CRITICAL HEALTH ALERT (#%d): %s",
                    self._state.critical_alerts_triggered,
                    json.dumps(health_report, default=str),
                )
        except Exception as e:
            logger.critical(
                "[SelfHealingLoop] CRITICAL: Failed to trigger alert: %s | Health: %s",
                e,
                json.dumps(health_report, default=str),
            )

    # ── Helpers ─────────────────────────────────────────────────────────

    def _resolve_orchestrator(self) -> Optional[Any]:
        """Resolve the orchestrator instance (lazy singleton access).

        Tries multiple import strategies to find the orchestrator:
          1. Use cached reference if available
          2. Import from backend.autonomous_system
          3. Fall back to None

        Returns:
            The orchestrator instance, or None if unavailable.
        """
        if self._orchestrator is not None:
            return self._orchestrator

        # Try canonical import path
        try:
            from backend.autonomous_system import AutonomousOrchestrator

            self._orchestrator = AutonomousOrchestrator()
            if not getattr(self._orchestrator, "_initialized_agents", False):
                try:
                    self._orchestrator.initialize()
                except Exception as e:
                    logger.warning("[SelfHealingLoop] Orchestrator init warning: %s", e)
            logger.info("[SelfHealingLoop] Orchestrator resolved via AutonomousOrchestrator")
            return self._orchestrator
        except Exception as e:
            logger.debug("[SelfHealingLoop] Could not resolve orchestrator: %s", e)

        # Try alternate import path
        try:
            from autonomous_system import AutonomousOrchestrator  # type: ignore[no-redef]

            self._orchestrator = AutonomousOrchestrator()
            logger.info("[SelfHealingLoop] Orchestrator resolved via alternate import")
            return self._orchestrator
        except Exception:
            pass

        logger.warning("[SelfHealingLoop] No orchestrator available — running in degraded mode")
        return None

    def _handle_loop_error(self, error: Exception) -> None:
        """Handle an error inside the main loop.

        Records the error in state and logs it. The loop continues
        running after handling the error.

        Args:
            error: The exception that occurred.
        """
        error_msg = f"{type(error).__name__}: {str(error)}"
        self._state.last_error = error_msg
        self._state.last_error_at = datetime.now(timezone.utc).isoformat()

        logger.error(
            "[SelfHealingLoop] Loop error (iteration=%d): %s\n%s",
            self._state.iteration_count,
            error_msg,
            traceback.format_exc(),
        )

    def _install_sigterm_handler(self) -> None:
        """Install a SIGTERM handler for graceful shutdown.

        The handler signals the loop to stop and can be called
        multiple times safely. It is idempotent.
        """
        if self._sigterm_installed:
            return

        def _on_sigterm(signum: int, frame: Any) -> None:
            """Handle SIGTERM by gracefully stopping the loop."""
            logger.info(
                "[SelfHealingLoop] SIGTERM received (signum=%d) — initiating graceful shutdown",
                signum,
            )
            self.stop(timeout=self.SHUTDOWN_TIMEOUT_SECONDS)
            logger.info("[SelfHealingLoop] Graceful shutdown complete — exiting process")
            # Re-raise the signal for the default handler
            signal.default_int_handler(signum, frame)

        try:
            signal.signal(signal.SIGTERM, _on_sigterm)
            self._sigterm_installed = True
            logger.info("[SelfHealingLoop] SIGTERM handler installed")
        except Exception as e:
            logger.warning("[SelfHealingLoop] Could not install SIGTERM handler: %s", e)

    @staticmethod
    def _timestamp_iso(timestamp: float) -> Optional[str]:
        """Convert a Unix timestamp to an ISO 8601 string.

        Args:
            timestamp: Unix timestamp in seconds.

        Returns:
            ISO 8601 formatted string, or None if timestamp is 0.
        """
        if timestamp <= 0:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY & MODULE-LEVEL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[SelfHealingLoop] = None


def create_healing_loop(
    health_check_interval: Optional[int] = None,
    metrics_interval: Optional[int] = None,
    research_interval_hours: Optional[int] = None,
) -> SelfHealingLoop:
    """Factory function to create or retrieve the SelfHealingLoop singleton.

    Args:
        health_check_interval: Seconds between health checks.
        metrics_interval: Seconds between metrics recording.
        research_interval_hours: Hours between research cycles.

    Returns:
        SelfHealingLoop: The singleton instance.
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = SelfHealingLoop(
            health_check_interval=health_check_interval,
            metrics_interval=metrics_interval,
            research_interval_hours=research_interval_hours,
        )
    return _orchestrator_instance


def get_healing_loop() -> Optional[SelfHealingLoop]:
    """Get the module-level SelfHealingLoop instance if it exists.

    Returns:
        SelfHealingLoop instance, or None if not yet created.
    """
    return _orchestrator_instance


def register_loop_endpoints(app_or_router: Any) -> None:
    """Convenience function to register loop endpoints.

    Creates the singleton if needed and registers all endpoints.

    Args:
        app_or_router: FastAPI app or APIRouter instance.
    """
    loop = create_healing_loop()
    loop.register_endpoints(app_or_router)


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-START (if enabled via environment)
# ═══════════════════════════════════════════════════════════════════════════

def _auto_start() -> None:
    """Auto-start the healing loop if HEALING_LOOP_ENABLED is true.

    This is called at module import time. It starts the loop in a
    background thread only if the environment variable is set.
    """
    if HEALING_LOOP_ENABLED:
        logger.info(
            "[SelfHealingLoop] HEALING_LOOP_ENABLED=true — auto-starting background loop"
        )
        loop = create_healing_loop()
        loop.start()
    else:
        logger.debug(
            "[SelfHealingLoop] HEALING_LOOP_ENABLED=false — loop will not auto-start"
        )


# Run auto-start check at module load
_auto_start()
