#!/usr/bin/env python3
"""
Luqi AI v24.5.0 — Metrics Dashboard
====================================
Time-series metrics tracking for the autonomous system.

Features:
  - Tracks CPU, memory, disk usage over time
  - Records API response times and error rates
  - Stores historical data in JSON file (data/metrics.jsonl)
  - Provides trend analysis (is system getting worse?)
  - FastAPI endpoints for dashboard data
  - Configurable retention (default: keep 7 days)

Part of Luqi AI v24.5.0 by Limitless Telecoms
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import warnings
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

# ---------------------------------------------------------------------------
# Graceful optional imports
# ---------------------------------------------------------------------------
try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False
    warnings.warn(
        "psutil is not installed. System metrics will report zeros. "
        "Install psutil for accurate system monitoring.",
        RuntimeWarning,
        stacklevel=2,
    )

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from fastapi.routing import APIRouter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.metrics")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_RETENTION_DAYS: int = 7
DEFAULT_HISTORY_HOURS: int = 24
MAX_IN_MEMORY_METRICS: int = 10_000  # hard cap to prevent unbounded growth
METRICS_FILENAME: str = "metrics.jsonl"
DATA_DIR_ENV_VAR: str = "LUQI_DATA_DIR"

TrendLabel = Literal["improving", "stable", "degrading"]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class SystemMetric:
    """A single point-in-time snapshot of system health.

    Attributes:
        timestamp: ISO-8601 UTC timestamp when the snapshot was taken.
        cpu_percent: CPU utilisation (0.0-100.0).
        memory_percent: RAM utilisation (0.0-100.0).
        disk_percent: Disk utilisation (0.0-100.0).
        api_latency_ms: Rolling average API latency in milliseconds.
        error_count_1h: Number of errors observed in the last hour.
        active_requests: Currently in-flight requests.
        module_status: Per-module health map, e.g. {"orchestrator": "ok"}.
    """

    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    api_latency_ms: float
    error_count_1h: int
    active_requests: int
    module_status: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for JSON serialisation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemMetric:
        """Reconstruct a ``SystemMetric`` from a dict."""
        # Filter only known fields so the dataclass stays forward-compatible
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Metrics engine (Singleton)
# ---------------------------------------------------------------------------
class MetricsDashboard:
    """Centralised time-series metrics collector and analyser.

    This class is a singleton — repeated instantiations return the same
    object, ensuring a single consistent metrics history across the process.

    Example::

        dashboard = MetricsDashboard()
        snapshot = dashboard.record_snapshot()
        summary = dashboard.get_summary()
        trends = dashboard.get_trends()
    """

    _instance: MetricsDashboard | None = None
    _lock: threading.Lock = threading.Lock()

    # --- singleton machinery ------------------------------------------------

    def __new__(cls, *args: Any, **kwargs: Any) -> MetricsDashboard:  # noqa: ARG003
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        *,
        data_dir: str | None = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        max_in_memory: int = MAX_IN_MEMORY_METRICS,
    ) -> None:
        """Initialise the dashboard.

        Args:
            data_dir: Directory for metrics persistence.  Defaults to
                ``data/`` relative to the current working directory, or the
                value of the ``LUQI_DATA_DIR`` environment variable.
            retention_days: How many days of metrics to retain on disk.
            max_in_memory: Maximum number of recent metrics kept in RAM.
        """
        # Guard against re-initialisation in singleton pattern
        if hasattr(self, "_initialised"):
            return

        self._initialised = True
        self._retention_days = retention_days
        self._max_in_memory = max_in_memory

        # Determine data directory
        if data_dir is not None:
            self._data_dir = Path(data_dir).resolve()
        elif DATA_DIR_ENV_VAR in os.environ:
            self._data_dir = Path(os.environ[DATA_DIR_ENV_VAR]).resolve()
        else:
            self._data_dir = Path.cwd() / "data"

        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._metrics_file = self._data_dir / METRICS_FILENAME

        # In-memory ring buffer — newest at the right
        self._metrics: deque[SystemMetric] = deque(maxlen=max_in_memory)
        self._error_count_1h: int = 0
        self._error_window: deque[float] = deque()  # timestamps of recent errors
        self._api_latencies: deque[float] = deque(maxlen=100)  # ms

        # Process start time for uptime calculation
        self._start_time: float = time.monotonic()

        # Internal lock for thread-safe mutations
        self._mutex = threading.RLock()

        # Load existing metrics from disk
        self._load_metrics()

        logger.info(
            "MetricsDashboard initialised — data_dir=%s retention=%dd",
            self._data_dir,
            self._retention_days,
        )

    # --- public API ---------------------------------------------------------

    def record_snapshot(
        self,
        *,
        module_status: dict[str, str] | None = None,
        active_requests: int | None = None,
    ) -> SystemMetric:
        """Capture a fresh system snapshot.

        Args:
            module_status: Optional per-module health overrides.
            active_requests: Optional override for in-flight request count.

        Returns:
            The captured ``SystemMetric``.
        """
        with self._mutex:
            now = datetime.now(timezone.utc).isoformat()

            # psutil-driven metrics (zeros when psutil is absent)
            if _HAS_PSUTIL and psutil is not None:
                try:
                    cpu = psutil.cpu_percent(interval=None)
                    mem = psutil.virtual_memory().percent
                    disk = psutil.disk_usage("/").percent
                except Exception as exc:  # pragma: no cover
                    logger.warning("psutil read failed: %s", exc)
                    cpu, mem, disk = 0.0, 0.0, 0.0
            else:
                cpu, mem, disk = 0.0, 0.0, 0.0

            # Rolling API latency
            avg_latency = self._avg_api_latency()

            # Decay error count window (1-hour sliding window)
            self._decay_error_window()

            # Active requests (default to zero if not supplied)
            if active_requests is None:
                active_requests = 0

            metric = SystemMetric(
                timestamp=now,
                cpu_percent=round(cpu, 2),
                memory_percent=round(mem, 2),
                disk_percent=round(disk, 2),
                api_latency_ms=round(avg_latency, 2),
                error_count_1h=self._error_count_1h,
                active_requests=active_requests,
                module_status=module_status or {},
            )

            self._metrics.append(metric)
            self._save_metric(metric)

            return metric

    def record_api_latency(self, latency_ms: float) -> None:
        """Record a single API latency observation.

        Args:
            latency_ms: Latency of the request in milliseconds.
        """
        with self._mutex:
            self._api_latencies.append(latency_ms)

    def record_error(self) -> None:
        """Increment the rolling 1-hour error counter."""
        with self._mutex:
            self._error_window.append(time.monotonic())
            self._error_count_1h = len(self._error_window)

    def get_latest(self) -> SystemMetric | None:
        """Return the most recent snapshot, or *None* if no data exists."""
        with self._mutex:
            return self._metrics[-1] if self._metrics else None

    def get_history(self, hours: int = DEFAULT_HISTORY_HOURS) -> list[dict[str, Any]]:
        """Return metrics recorded within the last *hours*.

        Args:
            hours: Look-back window in hours.

        Returns:
            List of ``SystemMetric`` dicts, oldest first.
        """
        with self._mutex:
            cutoff = time.time() - (hours * 3600)
            return [
                m.to_dict()
                for m in self._metrics
                if self._iso_to_timestamp(m.timestamp) >= cutoff
            ]

    def get_trends(self) -> dict[str, Any]:
        """Analyse recent trends to determine if the system is degrading.

        Returns:
            A dict containing trend labels, uptime, and raw slope data.
        """
        with self._mutex:
            history = list(self._metrics)
            if len(history) < 2:
                return {
                    "cpu_trend": "stable",
                    "memory_trend": "stable",
                    "error_rate_trend": "stable",
                    "uptime_seconds": round(time.monotonic() - self._start_time, 1),
                    "data_points": len(history),
                }

            cpu_slope = self._linear_slope([m.cpu_percent for m in history])
            mem_slope = self._linear_slope([m.memory_percent for m in history])

            # Error trend: compare first half vs second half of window
            mid = len(history) // 2
            first_half_errors = sum(m.error_count_1h for m in history[:mid])
            second_half_errors = sum(m.error_count_1h for m in history[mid:])

            if second_half_errors > first_half_errors * 1.5:
                error_trend: TrendLabel = "degrading"
            elif second_half_errors < first_half_errors * 0.5:
                error_trend = "improving"
            else:
                error_trend = "stable"

            return {
                "cpu_trend": self._slope_to_trend(cpu_slope),
                "memory_trend": self._slope_to_trend(mem_slope),
                "error_rate_trend": error_trend,
                "uptime_seconds": round(time.monotonic() - self._start_time, 1),
                "data_points": len(history),
                "cpu_slope_per_hour": round(cpu_slope, 4),
                "memory_slope_per_hour": round(mem_slope, 4),
            }

    def get_summary(self) -> dict[str, Any]:
        """Return a high-level summary of current and historical metrics.

        Returns:
            Dict with ``current``, ``averages``, and ``peaks`` sections.
        """
        with self._mutex:
            latest = self.get_latest()
            history = list(self._metrics)

            if not history:
                return {
                    "current": None,
                    "averages": None,
                    "peaks": None,
                    "uptime_seconds": round(time.monotonic() - self._start_time, 1),
                }

            cpu_vals = [m.cpu_percent for m in history]
            mem_vals = [m.memory_percent for m in history]
            disk_vals = [m.disk_percent for m in history]
            lat_vals = [m.api_latency_ms for m in history]

            return {
                "current": latest.to_dict() if latest else None,
                "averages": {
                    "cpu_percent": round(sum(cpu_vals) / len(cpu_vals), 2),
                    "memory_percent": round(sum(mem_vals) / len(mem_vals), 2),
                    "disk_percent": round(sum(disk_vals) / len(disk_vals), 2),
                    "api_latency_ms": round(sum(lat_vals) / len(lat_vals), 2),
                },
                "peaks": {
                    "cpu_percent": round(max(cpu_vals), 2),
                    "memory_percent": round(max(mem_vals), 2),
                    "disk_percent": round(max(disk_vals), 2),
                    "api_latency_ms": round(max(lat_vals), 2),
                },
                "uptime_seconds": round(time.monotonic() - self._start_time, 1),
                "total_snapshots": len(history),
            }

    def cleanup_old_data(self, retention_days: int | None = None) -> int:
        """Remove metrics older than the retention period.

        Args:
            retention_days: Override the default retention.  Uses the value
                passed to ``__init__`` when *None*.

        Returns:
            Number of records removed.
        """
        days = retention_days or self._retention_days
        cutoff = time.time() - (days * 86400)
        removed = 0

        # 1. Filter in-memory buffer
        with self._mutex:
            kept = deque(maxlen=self._max_in_memory)
            for m in self._metrics:
                if self._iso_to_timestamp(m.timestamp) >= cutoff:
                    kept.append(m)
                else:
                    removed += 1
            self._metrics = kept

        # 2. Rewrite the JSONL file to drop old lines
        if self._metrics_file.exists():
            tmp_path = self._metrics_file.with_suffix(".jsonl.tmp")
            try:
                with (
                    open(self._metrics_file, "r", encoding="utf-8") as src,
                    open(tmp_path, "w", encoding="utf-8") as dst,
                ):
                    for line in src:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            ts = json.loads(line).get("timestamp", "")
                            if self._iso_to_timestamp(ts) >= cutoff:
                                dst.write(line + "\n")
                            else:
                                removed += 1
                        except (json.JSONDecodeError, ValueError):
                            dst.write(line + "\n")  # preserve malformed lines
                tmp_path.replace(self._metrics_file)
            except OSError as exc:
                logger.error("Failed to clean up old metrics: %s", exc)
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)

        logger.info("Cleaned up %d metric records older than %d days", removed, days)
        return removed

    def register_endpoints(self, app_or_router: Any) -> None:
        """Wire FastAPI endpoints into the provided app or router.

        Args:
            app_or_router: A ``FastAPI`` application or ``APIRouter``.
        """
        from fastapi import HTTPException, Query

        async def _get_current_and_summary() -> dict[str, Any]:
            latest = self.get_latest()
            summary = self.get_summary()
            return {
                "snapshot": latest.to_dict() if latest else None,
                "summary": summary,
            }

        async def _get_history(
            hours: int = Query(default=DEFAULT_HISTORY_HOURS, ge=1, le=720),
        ) -> dict[str, Any]:
            return {
                "hours": hours,
                "count": 0,
                "data": self.get_history(hours=hours),
            }

        async def _get_trends() -> dict[str, Any]:
            return self.get_trends()

        async def _post_cleanup(
            retention_days: int = Query(default=self._retention_days, ge=1),
        ) -> dict[str, Any]:
            try:
                removed = self.cleanup_old_data(retention_days=retention_days)
                return {"status": "ok", "removed": removed, "retention_days": retention_days}
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

        # Support both FastAPI app and APIRouter
        add = getattr(app_or_router, "add_api_route", None)
        if add is None:
            add = getattr(app_or_router, "get", None)
            if add is None:
                raise TypeError(
                    f"Expected FastAPI or APIRouter, got {type(app_or_router).__name__}"
                )
            # Fallback for router-like objects with decorator syntax
            app_or_router.get("/api/system/metrics")(_get_current_and_summary)
            app_or_router.get("/api/system/metrics/history")(_get_history)
            app_or_router.get("/api/system/metrics/trends")(_get_trends)
            app_or_router.post("/api/system/metrics/cleanup")(_post_cleanup)
            return

        add("/api/system/metrics", _get_current_and_summary, methods=["GET"])
        add("/api/system/metrics/history", _get_history, methods=["GET"])
        add("/api/system/metrics/trends", _get_trends, methods=["GET"])
        add("/api/system/metrics/cleanup", _post_cleanup, methods=["POST"])

    # --- persistence --------------------------------------------------------

    def _load_metrics(self) -> None:
        """Hydrate the in-memory buffer from the JSONL file."""
        if not self._metrics_file.exists():
            logger.debug("No existing metrics file at %s", self._metrics_file)
            return

        loaded = 0
        dropped = 0
        cutoff = time.time() - (self._retention_days * 86400)

        try:
            with open(self._metrics_file, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        ts = data.get("timestamp", "")
                        if self._iso_to_timestamp(ts) >= cutoff:
                            self._metrics.append(SystemMetric.from_dict(data))
                            loaded += 1
                        else:
                            dropped += 1
                    except (json.JSONDecodeError, TypeError, KeyError) as exc:
                        logger.warning("Skipping malformed metric line: %s — %s", exc, line[:120])
            logger.info(
                "Loaded %d metrics from disk (dropped %d expired)", loaded, dropped
            )
        except OSError as exc:
            logger.error("Failed to load metrics from %s: %s", self._metrics_file, exc)

    def _save_metric(self, metric: SystemMetric) -> None:
        """Append a single metric to the JSONL file (append-only, O(1))."""
        try:
            with open(self._metrics_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(metric.to_dict(), separators=(",", ":")) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            logger.error("Failed to persist metric: %s", exc)

    # --- helpers ------------------------------------------------------------

    @staticmethod
    def _iso_to_timestamp(iso_string: str) -> float:
        """Parse an ISO-8601 string to a Unix timestamp.

        Handles both ``Z`` suffix and ``+00:00`` offset forms.
        """
        try:
            # Python 3.11+ handles Z suffix natively
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return 0.0

    def _avg_api_latency(self) -> float:
        """Return the mean of the rolling API latency buffer."""
        if not self._api_latencies:
            return 0.0
        return sum(self._api_latencies) / len(self._api_latencies)

    def _decay_error_window(self) -> None:
        """Evict error timestamps older than 1 hour."""
        cutoff = time.monotonic() - 3600
        while self._error_window and self._error_window[0] < cutoff:
            self._error_window.popleft()
        self._error_count_1h = len(self._error_window)

    @staticmethod
    def _linear_slope(values: list[float]) -> float:
        """Compute the least-squares slope of *values* vs. their index.

        A positive slope means the metric is increasing over time.
        """
        n = len(values)
        if n < 2:
            return 0.0
        mean_x = (n - 1) / 2.0
        mean_y = sum(values) / n
        numerator = sum((i - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((i - mean_x) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _slope_to_trend(slope: float, threshold: float = 0.5) -> TrendLabel:
        """Classify a slope as *improving*, *stable*, or *degrading*.

        Args:
            slope: Computed slope value.
            threshold: Absolute slope above which we consider a trend.

        Returns:
            One of ``"improving"``, ``"stable"``, ``"degrading"``.
        """
        if slope > threshold:
            return "degrading"
        if slope < -threshold:
            return "improving"
        return "stable"

    # --- introspection / debug ----------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"snapshots={len(self._metrics)} "
            f"data_dir={self._data_dir!s}>"
        )
