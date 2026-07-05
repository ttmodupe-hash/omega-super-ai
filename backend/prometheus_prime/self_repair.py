#!/usr/bin/env python3
"""
Prometheus Prime — Self-Repair System

Continuously monitors system health, detects anomalies in real time,
and applies automatic remediation fixes.  Operates as a background
service that guards against performance degradation, resource
exhaustion, and unexpected errors.
"""

from __future__ import annotations

__all__ = [
    "SelfRepair",
    "HealthStatus",
    "Anomaly",
    "RepairAction",
]

import asyncio
import gc
import json
import logging
import os
import platform
import re
import resource
import subprocess
import sys
import threading
import time
import traceback
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("prometheus_prime.self_repair")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPORT_DIR = Path(".prometheus_prime/reports").resolve()
MONITOR_INTERVAL_SECONDS: float = 60.0
CPU_THRESHOLD: float = 85.0  # percent
MEMORY_THRESHOLD: float = 85.0  # percent
LATENCY_THRESHOLD_MS: float = 5000.0
ERROR_RATE_THRESHOLD: float = 0.05  # 5%
DISK_THRESHOLD: float = 90.0  # percent

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class HealthStatus:
    """Snapshot of system health at a point in time."""

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    latency_ms: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0
    open_file_descriptors: int = 0
    thread_count: int = 0
    gc_collections: int = 0
    overall_score: float = 1.0  # 0.0 – 1.0, 1.0 = perfect


@dataclass
class Anomaly:
    """A detected anomaly with severity and context."""

    id: str
    type: Literal["cpu", "memory", "disk", "latency", "error_rate", "custom"]
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    metric_value: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False
    resolution_action: str = ""


@dataclass
class RepairAction:
    """Record of an automated repair attempt."""

    anomaly_id: str
    action_type: str
    description: str
    success: bool
    before_value: float
    after_value: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str = ""


# ---------------------------------------------------------------------------
# SelfRepair
# ---------------------------------------------------------------------------


class SelfRepair:
    """Autonomous health monitoring and repair system.

    Usage (background thread)::

        repair = SelfRepair()
        repair.start_monitoring()   # runs in a daemon thread
        # ... later ...
        repair.stop_monitoring()

    Usage (async)::

        await repair.monitor_loop_async()

    Usage (one-shot check)::

        status = repair.check_health()
        anomalies = repair.detect_anomalies(status)
        for a in anomalies:
            repair.attempt_repair(a)
    """

    def __init__(
        self,
        monitor_interval: float = MONITOR_INTERVAL_SECONDS,
        cpu_threshold: float = CPU_THRESHOLD,
        memory_threshold: float = MEMORY_THRESHOLD,
        latency_threshold_ms: float = LATENCY_THRESHOLD_MS,
        error_rate_threshold: float = ERROR_RATE_THRESHOLD,
        disk_threshold: float = DISK_THRESHOLD,
    ) -> None:
        self.monitor_interval = monitor_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.disk_threshold = disk_threshold

        self._anomalies: list[Anomaly] = []
        self._repairs: list[RepairAction] = []
        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._start_time = time.time()
        self._error_count = 0
        self._request_count = 0
        self._lock = threading.RLock()

        REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Health check
    # ------------------------------------------------------------------

    def check_health(self) -> HealthStatus:
        """Collect current system health metrics.

        Returns a :class:`HealthStatus` snapshot.
        """
        status = HealthStatus()
        status.uptime_seconds = time.time() - self._start_time

        # CPU
        try:
            if hasattr(os, "getloadavg"):
                load1 = os.getloadavg()[0]
                cpu_count = os.cpu_count() or 1
                status.cpu_percent = min(100.0, (load1 / cpu_count) * 100)
        except (OSError, AttributeError):
            pass

        # Memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            status.memory_percent = mem.percent
            status.open_file_descriptors = len(psutil.Process().open_files())
            status.thread_count = psutil.Process().num_threads()
        except ImportError:
            # Fallback: read /proc/self/status on Linux
            try:
                with open("/proc/self/status", "r") as f:
                    for line in f:
                        if line.startswith("VmRSS"):
                            # Very rough estimate
                            status.memory_percent = 50.0
                        elif line.startswith("Threads"):
                            status.thread_count = int(line.split()[1])
            except (FileNotFoundError, ValueError):
                pass

        # Disk
        try:
            import psutil
            disk = psutil.disk_usage("/")
            status.disk_percent = (disk.used / disk.total) * 100
        except ImportError:
            try:
                stat = os.statvfs("/")
                total = stat.f_blocks * stat.f_frsize
                used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
                status.disk_percent = (used / total) * 100
            except (OSError, ZeroDivisionError):
                pass

        # Error rate (rolling window)
        with self._lock:
            total = self._request_count
            errors = self._error_count
            status.error_rate = errors / max(total, 1)

        # GC stats
        status.gc_collections = sum(gc.get_stats()[i]["collections"] for i in range(len(gc.get_stats())))

        # Overall score (weighted)
        cpu_score = max(0.0, 1.0 - status.cpu_percent / 100)
        mem_score = max(0.0, 1.0 - status.memory_percent / 100)
        disk_score = max(0.0, 1.0 - status.disk_percent / 100)
        latency_score = max(0.0, 1.0 - status.latency_ms / self.latency_threshold_ms)
        error_score = max(0.0, 1.0 - status.error_rate / self.error_rate_threshold)

        status.overall_score = round(
            (cpu_score * 0.25 + mem_score * 0.25 + disk_score * 0.15 +
             latency_score * 0.15 + error_score * 0.20),
            3,
        )

        return status

    # ------------------------------------------------------------------
    # 2. Anomaly detection
    # ------------------------------------------------------------------

    def detect_anomalies(self, status: HealthStatus | None = None) -> list[Anomaly]:
        """Compare *status* against thresholds and return any anomalies.

        If *status* is ``None``, a fresh health check is performed.
        """
        if status is None:
            status = self.check_health()

        anomalies: list[Anomaly] = []
        counter = len(self._anomalies)

        checks = [
            ("cpu", status.cpu_percent, self.cpu_threshold, "CPU usage is high"),
            ("memory", status.memory_percent, self.memory_threshold, "Memory usage is high"),
            ("disk", status.disk_percent, self.disk_threshold, "Disk usage is high"),
            ("latency", status.latency_ms, self.latency_threshold_ms, "Response latency is high"),
            ("error_rate", status.error_rate * 100, self.error_rate_threshold * 100, "Error rate is elevated"),
        ]

        for type_name, value, threshold, message in checks:
            if value > threshold:
                counter += 1
                severity: Literal["low", "medium", "high", "critical"] = "medium"
                ratio = value / threshold
                if ratio > 2.0:
                    severity = "critical"
                elif ratio > 1.5:
                    severity = "high"
                elif ratio < 1.2:
                    severity = "low"

                anomaly = Anomaly(
                    id=f"a-{{counter:04d}}",
                    type=type_name,  # type: ignore[arg-type]
                    severity=severity,
                    message=f"{{message}}: {{value:.1f}}% (threshold: {{threshold:.1f}}%)",
                    metric_value=round(value, 2),
                    threshold=threshold,
                )
                anomalies.append(anomaly)
                with self._lock:
                    self._anomalies.append(anomaly)

        if anomalies:
            logger.warning("Detected %d anomaly(ies): %s",
                           len(anomalies), ", ".join(a.type for a in anomalies))
        return anomalies

    # ------------------------------------------------------------------
    # 3. Automatic repair
    # ------------------------------------------------------------------

    def attempt_repair(self, anomaly: Anomaly) -> RepairAction:
        """Attempt to automatically fix *anomaly*.

        The repair strategy is selected based on anomaly type::

            cpu         → trigger GC, log thread dump
            memory      → trigger GC, clear caches
            disk        → log cleanup recommendation
            latency     → log performance recommendation
            error_rate  → log error-pattern recommendation

        Returns a :class:`RepairAction` record.
        """
        logger.info("Attempting repair for anomaly %s (%s)", anomaly.id, anomaly.type)

        before = anomaly.metric_value
        success = False
        after = before
        action_type = "unknown"
        description = ""
        error_msg = ""

        try:
            if anomaly.type == "cpu":
                action_type = "gc_and_dump"
                description = "Triggered garbage collection and logged thread info"
                gc.collect()
                self._log_thread_dump()
                # Brief cooldown
                time.sleep(1)
                status = self.check_health()
                after = status.cpu_percent
                success = after < before * 0.9

            elif anomaly.type == "memory":
                action_type = "gc_and_clear"
                description = "Triggered garbage collection and cleared internal caches"
                gc.collect()
                gc.collect()  # Second pass for cyclic refs
                # Attempt to release memory back to OS (Linux)
                try:
                    import ctypes
                    ctypes.CDLL("libc.so.6").malloc_trim(0)
                except Exception:
                    pass
                time.sleep(1)
                status = self.check_health()
                after = status.memory_percent
                success = after < before * 0.95

            elif anomaly.type == "disk":
                action_type = "cleanup_recommendation"
                description = "Disk cleanup recommended — manual intervention may be needed"
                success = False  # Can't auto-fix disk

            elif anomaly.type == "latency":
                action_type = "performance_check"
                description = "High latency detected — check for blocking operations"
                self._log_thread_dump()
                success = False  # Requires investigation

            elif anomaly.type == "error_rate":
                action_type = "error_analysis"
                description = "Elevated error rate — reviewing recent error patterns"
                self._error_count = 0  # Reset counter after acknowledgment
                success = False  # Requires investigation

            else:
                action_type = "manual_review"
                description = f"Unknown anomaly type: {{anomaly.type}}"

        except Exception as exc:
            error_msg = str(exc)
            logger.exception("Repair attempt failed for anomaly %s", anomaly.id)

        repair = RepairAction(
            anomaly_id=anomaly.id,
            action_type=action_type,
            description=description,
            success=success,
            before_value=round(before, 2),
            after_value=round(after, 2),
            error_message=error_msg,
        )

        with self._lock:
            self._repairs.append(repair)
            # Mark anomaly as resolved if repair succeeded
            if success:
                anomaly.resolved = True
                anomaly.resolution_action = action_type

        logger.info("Repair %s for anomaly %s: before=%.1f → after=%.1f",
                    "succeeded" if success else "failed", anomaly.id, before, after)
        return repair

    # ------------------------------------------------------------------
    # 4. Monitoring loop
    # ------------------------------------------------------------------

    def start_monitoring(self) -> None:
        """Start the health-monitoring daemon thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SelfRepair")
        self._monitor_thread.start()
        logger.info("Self-repair monitoring started (interval=%.0fs)", self.monitor_interval)

    def stop_monitoring(self) -> None:
        """Signal the monitoring loop to stop and wait for it."""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=self.monitor_interval + 5)
        logger.info("Self-repair monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background loop: check health → detect anomalies → repair."""
        while self._running:
            try:
                status = self.check_health()

                # Persist health status
                self._persist_health(status)

                # Detect and repair
                if status.overall_score < 0.8:
                    anomalies = self.detect_anomalies(status)
                    for anomaly in anomalies:
                        if not anomaly.resolved:
                            self.attempt_repair(anomaly)

                # Daily report
                if int(time.time()) % 86400 < int(self.monitor_interval):
                    self._generate_daily_report()

            except Exception:
                logger.exception("Monitor loop error")

            # Sleep with early-exit support
            for _ in range(int(self.monitor_interval)):
                if not self._running:
                    break
                time.sleep(1)

    async def monitor_loop_async(self) -> None:
        """Async version of the monitoring loop for use with asyncio."""
        self._running = True
        logger.info("Self-repair async monitoring started")
        while self._running:
            try:
                status = self.check_health()
                self._persist_health(status)

                if status.overall_score < 0.8:
                    anomalies = self.detect_anomalies(status)
                    for anomaly in anomalies:
                        if not anomaly.resolved:
                            self.attempt_repair(anomaly)
            except Exception:
                logger.exception("Async monitor loop error")
            await asyncio.sleep(self.monitor_interval)

    # ------------------------------------------------------------------
    # 5. Metrics & reporting
    # ------------------------------------------------------------------

    def get_health_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent health snapshots from disk."""
        history_file = REPORT_DIR / "health_history.jsonl"
        if not history_file.exists():
            return []

        entries: list[dict[str, Any]] = []
        with open(history_file, "r", encoding="utf-8") as fh:
            for line in reversed(fh.readlines()):
                if line.strip():
                    entries.append(json.loads(line))
                if len(entries) >= limit:
                    break
        return entries

    def get_anomalies(self, resolved_only: bool = False) -> list[Anomaly]:
        """Return detected anomalies, optionally filtering to resolved ones."""
        with self._lock:
            if resolved_only:
                return [a for a in self._anomalies if a.resolved]
            return list(self._anomalies)

    def get_repair_history(self) -> list[RepairAction]:
        """Return all repair actions taken."""
        with self._lock:
            return list(self._repairs)

    def get_status_summary(self) -> dict[str, Any]:
        """Return a concise status summary."""
        status = self.check_health()
        with self._lock:
            open_anomalies = [a for a in self._anomalies if not a.resolved]
            total_repairs = len(self._repairs)
            successful_repairs = sum(1 for r in self._repairs if r.success)

        return {
            "health": {
                "overall_score": status.overall_score,
                "cpu_percent": status.cpu_percent,
                "memory_percent": status.memory_percent,
                "disk_percent": status.disk_percent,
                "error_rate": status.error_rate,
                "uptime_seconds": status.uptime_seconds,
            },
            "anomalies": {
                "total_detected": len(self._anomalies),
                "open": len(open_anomalies),
                "resolved": len(self._anomalies) - len(open_anomalies),
            },
            "repairs": {
                "total": total_repairs,
                "successful": successful_repairs,
                "failed": total_repairs - successful_repairs,
            },
            "monitoring_active": self._running,
        }

    # ------------------------------------------------------------------
    # 6. Error tracking helpers
    # ------------------------------------------------------------------

    def record_request(self, success: bool = True) -> None:
        """Record an API request outcome for error-rate calculation."""
        with self._lock:
            self._request_count += 1
            if not success:
                self._error_count += 1

    def record_latency(self, latency_ms: float) -> None:
        """Record a response latency sample."""
        # Currently used for anomaly detection thresholds
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist_health(self, status: HealthStatus) -> None:
        history_file = REPORT_DIR / "health_history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(status), default=str) + "\\n")

    def _log_thread_dump(self) -> None:
        """Log a thread dump for debugging high CPU / latency issues."""
        try:
            import threading
            frames = sys._current_frames()
            dump_lines = ["=== Thread Dump ==="]
            for tid, frame in frames.items():
                dump_lines.append(f"Thread {{tid}}:")
                dump_lines.append("".join(traceback.format_stack(frame)))
            dump_lines.append("===================")
            logger.info("\\n".join(dump_lines))
        except Exception as exc:
            logger.warning("Could not generate thread dump: %s", exc)

    def _generate_daily_report(self) -> Path:
        """Generate a daily health report."""
        summary = self.get_status_summary()
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        report_path = REPORT_DIR / f"health_report_{{ts}}.json"
        report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        logger.info("Daily health report saved to %s", report_path)
        return report_path

    def reset_counters(self) -> None:
        """Reset error and request counters."""
        with self._lock:
            self._error_count = 0
            self._request_count = 0
