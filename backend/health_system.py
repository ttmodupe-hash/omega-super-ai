"""Luqi AI v24 -- Health Check System

Deep health probes for all subsystems with degradation alerts.

Usage:
    from backend.health_system import get_health_router
    app.include_router(get_health_router())
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sqlite3
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Deque, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("luqi.health")

HealthStatus = Literal["healthy", "degraded", "unhealthy", "not_configured"]


@dataclass
class HealthResult:
    """Result of a single health probe."""

    name: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    last_checked: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class HealthReport:
    """Aggregated health report from multiple probes."""

    status: HealthStatus
    timestamp: str
    overall_response_time_ms: float
    results: List[HealthResult]
    summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "overall_response_time_ms": round(self.overall_response_time_ms, 2),
            "summary": self.summary,
            "recommendations": self.recommendations,
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "response_time_ms": r.response_time_ms,
                    "details": r.details,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


# ═══════════════════════════════════════════════════════════════════
# Individual Subsystem Probes
# ═══════════════════════════════════════════════════════════════════

async def redis_probe(timeout: float = 5.0) -> HealthResult:
    """Check Redis connectivity and performance."""
    start = time.perf_counter()
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return HealthResult(
            name="redis", status="not_configured", response_time_ms=0.0,
            details={"note": "REDIS_URL not set"},
        )
    try:
        import redis as redis_lib
        client = redis_lib.from_url(redis_url, socket_connect_timeout=min(2.0, timeout))
        ping_start = time.perf_counter()
        client.ping()
        ping_ms = (time.perf_counter() - ping_start) * 1000
        info = client.info()
        memory = info.get("used_memory_human", "unknown")
        keys = client.dbsize()
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="redis", status="healthy", response_time_ms=total_ms,
            details={"ping_ms": round(ping_ms, 2), "memory_used": memory, "key_count": keys},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="redis", status="unhealthy", response_time_ms=total_ms,
            error=str(exc), details={},
        )


async def sqlite_probe(timeout: float = 5.0) -> HealthResult:
    """Check SQLite database connectivity and integrity."""
    start = time.perf_counter()
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/luqi.db")
    db_path = db_url.replace("sqlite:///", "")
    try:
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=timeout)
        query_start = time.perf_counter()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        query_ms = (time.perf_counter() - query_start) * 1000
        conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="sqlite", status="healthy", response_time_ms=total_ms,
            details={
                "tables": len(tables), "query_ms": round(query_ms, 2),
                "size_bytes": db_size, "sample_tables": tables[:10],
            },
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="sqlite", status="unhealthy", response_time_ms=total_ms,
            error=str(exc), details={},
        )


async def chromadb_probe(timeout: float = 5.0) -> HealthResult:
    """Check ChromaDB vector database connectivity."""
    start = time.perf_counter()
    chroma_path = os.getenv("CHROMA_PATH", "./chroma_db")
    if not os.path.exists(chroma_path):
        return HealthResult(
            name="chromadb", status="not_configured", response_time_ms=0.0,
            details={"note": f"ChromaDB path not found: {chroma_path}"},
        )
    try:
        import chromadb
        client = chromadb.PersistentClient(path=chroma_path)
        list_start = time.perf_counter()
        collections = client.list_collections()
        list_ms = (time.perf_counter() - list_start) * 1000
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="chromadb", status="healthy", response_time_ms=total_ms,
            details={"collections": len(collections), "list_ms": round(list_ms, 2)},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="chromadb", status="unhealthy", response_time_ms=total_ms,
            error=str(exc), details={},
        )


async def openai_probe(timeout: float = 5.0) -> HealthResult:
    """Check OpenAI API connectivity."""
    start = time.perf_counter()
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return HealthResult(
            name="openai", status="not_configured", response_time_ms=0.0,
            details={"note": "OPENAI_API_KEY not set"},
        )
    try:
        import httpx
        async with httpx.AsyncClient(timeout=min(timeout, 10.0)) as client:
            req_start = time.perf_counter()
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=min(timeout, 10.0),
            )
            req_ms = (time.perf_counter() - req_start) * 1000
            total_ms = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                return HealthResult(
                    name="openai", status="healthy", response_time_ms=total_ms,
                    details={"response_ms": round(req_ms, 2), "available_models": len(models)},
                )
            return HealthResult(
                name="openai", status="degraded", response_time_ms=total_ms,
                details={"status_code": resp.status_code}, error=resp.text[:200],
            )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="openai", status="unhealthy", response_time_ms=total_ms,
            error=str(exc), details={},
        )


async def filesystem_probe(timeout: float = 5.0) -> HealthResult:
    """Check filesystem health: upload dir, disk space."""
    start = time.perf_counter()
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    try:
        os.makedirs(upload_dir, exist_ok=True)
        test_file = os.path.join(upload_dir, ".health_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        if hasattr(os, "statvfs"):
            stat = os.statvfs(upload_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            pct_free = (stat.f_bavail / stat.f_blocks) * 100 if stat.f_blocks > 0 else 0
        else:
            free_gb = total_gb = pct_free = 0
        total_ms = (time.perf_counter() - start) * 1000
        status: HealthStatus = "healthy" if pct_free > 10 else "degraded"
        return HealthResult(
            name="filesystem", status=status, response_time_ms=total_ms,
            details={
                "upload_dir": upload_dir, "writable": True,
                "free_gb": round(free_gb, 2), "total_gb": round(total_gb, 2),
                "free_percent": round(pct_free, 1),
            },
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="filesystem", status="unhealthy", response_time_ms=total_ms,
            error=str(exc), details={},
        )


async def serper_probe(timeout: float = 5.0) -> HealthResult:
    """Check Serper API connectivity."""
    start = time.perf_counter()
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return HealthResult(name="serper", status="not_configured", response_time_ms=0.0)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            req_start = time.perf_counter()
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": "test", "num": 1},
                timeout=min(timeout, 10.0),
            )
            req_ms = (time.perf_counter() - req_start) * 1000
            total_ms = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                return HealthResult(
                    name="serper", status="healthy", response_time_ms=total_ms,
                    details={"response_ms": round(req_ms, 2)},
                )
            return HealthResult(
                name="serper", status="degraded", response_time_ms=total_ms,
                details={"status_code": resp.status_code}, error=resp.text[:200],
            )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="serper", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def stripe_probe(timeout: float = 5.0) -> HealthResult:
    """Check Stripe API connectivity."""
    start = time.perf_counter()
    api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not api_key:
        return HealthResult(name="stripe", status="not_configured", response_time_ms=0.0)
    try:
        import stripe
        stripe.api_key = api_key
        req_start = time.perf_counter()
        stripe.Balance.retrieve()
        req_ms = (time.perf_counter() - req_start) * 1000
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="stripe", status="healthy", response_time_ms=total_ms,
            details={"response_ms": round(req_ms, 2)},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="stripe", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def twilio_probe(timeout: float = 5.0) -> HealthResult:
    """Check Twilio API connectivity."""
    start = time.perf_counter()
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    if not account_sid:
        return HealthResult(name="twilio", status="not_configured", response_time_ms=0.0)
    try:
        from twilio.rest import Client
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        client = Client(account_sid, auth_token)
        req_start = time.perf_counter()
        account = client.api.accounts(account_sid).fetch()
        req_ms = (time.perf_counter() - req_start) * 1000
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="twilio", status="healthy", response_time_ms=total_ms,
            details={"response_ms": round(req_ms, 2), "account_status": account.status},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="twilio", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def livekit_probe(timeout: float = 5.0) -> HealthResult:
    """Check Livekit WebRTC service connectivity."""
    start = time.perf_counter()
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")
    if not api_key or not livekit_url:
        return HealthResult(name="livekit", status="not_configured", response_time_ms=0.0)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            req_start = time.perf_counter()
            resp = await client.get(f"{livekit_url}/", timeout=min(timeout, 10.0))
            req_ms = (time.perf_counter() - req_start) * 1000
            total_ms = (time.perf_counter() - start) * 1000
            return HealthResult(
                name="livekit", status="healthy", response_time_ms=total_ms,
                details={"response_ms": round(req_ms, 2), "status_code": resp.status_code},
            )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="livekit", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def cache_probe(timeout: float = 5.0) -> HealthResult:
    """Check cache system health."""
    start = time.perf_counter()
    try:
        from backend.cache_manager import get_cache
        cache = get_cache()
        health = cache.health()
        total_ms = (time.perf_counter() - start) * 1000
        redis_connected = health.get("redis", {}).get("connected", False)
        mem_items = health.get("memory", {}).get("items", 0)
        status: HealthStatus = "healthy" if redis_connected else "degraded"
        return HealthResult(
            name="cache", status=status, response_time_ms=total_ms,
            details={"redis_connected": redis_connected, "memory_items": mem_items},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="cache", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def task_queue_probe(timeout: float = 5.0) -> HealthResult:
    """Check background task queue health."""
    start = time.perf_counter()
    try:
        from backend.background_tasks import get_task_manager
        tm = get_task_manager()
        health = tm.health()
        total_ms = (time.perf_counter() - start) * 1000
        rq_available = health.get("rq", {}).get("available", False)
        return HealthResult(
            name="task_queue", status="healthy", response_time_ms=total_ms,
            details={"rq_available": rq_available, "threading_ready": True},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="task_queue", status="unhealthy", response_time_ms=total_ms, error=str(exc))


async def memory_probe(timeout: float = 5.0) -> HealthResult:
    """Check system memory usage."""
    start = time.perf_counter()
    try:
        import psutil
        proc = psutil.Process()
        proc_mb = proc.memory_info().rss / (1024 * 1024)
        sys_mem = psutil.virtual_memory()
        total_mb = sys_mem.total / (1024 * 1024)
        available_mb = sys_mem.available / (1024 * 1024)
        pct_used = sys_mem.percent
        total_ms = (time.perf_counter() - start) * 1000
        status: HealthStatus = "healthy" if pct_used < 90 else "degraded"
        return HealthResult(
            name="memory", status=status, response_time_ms=total_ms,
            details={
                "process_mb": round(proc_mb, 1),
                "system_total_mb": round(total_mb, 1),
                "system_available_mb": round(available_mb, 1),
                "system_used_percent": pct_used,
            },
        )
    except ImportError:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(
            name="memory", status="healthy", response_time_ms=total_ms,
            details={"note": "Install psutil for detailed memory stats"},
        )
    except Exception as exc:
        total_ms = (time.perf_counter() - start) * 1000
        return HealthResult(name="memory", status="unhealthy", response_time_ms=total_ms, error=str(exc))


# ═══════════════════════════════════════════════════════════════════
# Health Aggregator
# ═══════════════════════════════════════════════════════════════════

PROBE_REGISTRY: Dict[str, Callable[[float], Coroutine[Any, Any, HealthResult]]] = {
    "redis": redis_probe,
    "sqlite": sqlite_probe,
    "chromadb": chromadb_probe,
    "openai": openai_probe,
    "filesystem": filesystem_probe,
    "serper": serper_probe,
    "stripe": stripe_probe,
    "twilio": twilio_probe,
    "livekit": livekit_probe,
    "cache": cache_probe,
    "task_queue": task_queue_probe,
    "memory": memory_probe,
}


class SubsystemNotFoundError(HTTPException):
    def __init__(self, name: str) -> None:
        super().__init__(status_code=404, detail=f"Unknown subsystem: {name}")


class HealthAggregator:
    """Aggregates health results from all subsystem probes."""

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout
        self._history: Deque[HealthReport] = deque(maxlen=100)
        self._last_results: Dict[str, HealthStatus] = {}

    async def run_all_checks(self) -> HealthReport:
        """Run all health probes in parallel."""
        start = time.perf_counter()
        tasks = [probe(self.timeout) for probe in PROBE_REGISTRY.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed: List[HealthResult] = []
        for result in results:
            if isinstance(result, Exception):
                processed.append(HealthResult(
                    name="unknown", status="unhealthy", response_time_ms=0.0, error=str(result),
                ))
            else:
                processed.append(result)
        total_ms = (time.perf_counter() - start) * 1000
        report = self._build_report(processed, total_ms)
        self._detect_status_changes(report)
        self._history.append(report)
        return report

    async def run_quick_check(self) -> HealthReport:
        """Run only core subsystems for a fast check."""
        start = time.perf_counter()
        core = ["sqlite", "openai", "filesystem"]
        tasks = [PROBE_REGISTRY[name](self.timeout) for name in core if name in PROBE_REGISTRY]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed: List[HealthResult] = []
        for r in results:
            if isinstance(r, Exception):
                processed.append(HealthResult(name="unknown", status="unhealthy", response_time_ms=0.0, error=str(r)))
            else:
                processed.append(r)
        total_ms = (time.perf_counter() - start) * 1000
        return self._build_report(processed, total_ms)

    async def run_single_check(self, name: str) -> HealthResult:
        """Run a single subsystem check."""
        if name not in PROBE_REGISTRY:
            raise SubsystemNotFoundError(name)
        return await PROBE_REGISTRY[name](self.timeout)

    def _build_report(self, results: List[HealthResult], total_ms: float) -> HealthReport:
        summary: Dict[str, int] = {"healthy": 0, "degraded": 0, "unhealthy": 0, "not_configured": 0}
        for r in results:
            summary[r.status] = summary.get(r.status, 0) + 1
        if summary["unhealthy"] > 0:
            status: HealthStatus = "unhealthy"
        elif summary["degraded"] > 0:
            status = "degraded"
        else:
            status = "healthy"
        recommendations = self._generate_recommendations(results)
        report = HealthReport(
            status=status, timestamp=datetime.utcnow().isoformat(),
            overall_response_time_ms=total_ms, results=results,
            summary=summary, recommendations=recommendations,
        )
        return report

    def _detect_status_changes(self, report: HealthReport) -> None:
        for result in report.results:
            prev = self._last_results.get(result.name)
            if prev and prev != result.status:
                if prev == "healthy" and result.status in ("degraded", "unhealthy"):
                    logger.warning("Health degradation: %s went %s -> %s", result.name, prev, result.status)
                elif prev in ("degraded", "unhealthy") and result.status == "healthy":
                    logger.info("Health recovery: %s recovered to healthy", result.name)
            self._last_results[result.name] = result.status

    def _generate_recommendations(self, results: List[HealthResult]) -> List[str]:
        recs: List[str] = []
        for r in results:
            if r.status == "unhealthy":
                if r.error:
                    recs.append(f"{r.name}: {r.error[:100]}")
                else:
                    recs.append(f"{r.name}: Check service logs for details")
            elif r.status == "degraded":
                recs.append(f"{r.name}: Service is functional but showing issues")
        return recs

    @property
    def history(self) -> List[HealthReport]:
        return list(self._history)


# ═══════════════════════════════════════════════════════════════════
# Background Health Monitor
# ═══════════════════════════════════════════════════════════════════

class BackgroundHealthMonitor:
    """Periodically checks health and alerts on degradation."""

    def __init__(self, interval_seconds: float = 60.0) -> None:
        self.interval = interval_seconds
        self._aggregator = HealthAggregator()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self.on_degradation: Optional[Callable[[HealthReport], None]] = None
        self.on_recovery: Optional[Callable[[HealthReport], None]] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started (interval: %.0fs)", self.interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                report = await self._aggregator.run_all_checks()
                if report.status in ("degraded", "unhealthy") and self.on_degradation:
                    self.on_degradation(report)
                elif report.status == "healthy" and self.on_recovery:
                    self.on_recovery(report)
            except Exception as exc:
                logger.error("Health monitor error: %s", exc)
            await asyncio.sleep(self.interval)


# ═══════════════════════════════════════════════════════════════════
# FastAPI Router
# ═══════════════════════════════════════════════════════════════════

def get_health_router() -> APIRouter:
    """Create and return the health check API router."""
    router = APIRouter(prefix="/api/health", tags=["Health"])
    aggregator = HealthAggregator()

    @router.get("", summary="Quick health check")
    async def health_check() -> Dict[str, Any]:
        """Quick health check for load balancers. Returns 200 or 503."""
        report = await aggregator.run_quick_check()
        status_code = 200 if report.status == "healthy" else 503
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"status": report.status, "timestamp": report.timestamp},
            status_code=status_code,
        )

    @router.get("/detailed", summary="Detailed health report")
    async def health_detailed() -> Dict[str, Any]:
        """Full diagnostic report with all subsystem details."""
        report = await aggregator.run_all_checks()
        return report.to_dict()

    @router.get("/subsystem/{name}", summary="Individual subsystem check")
    async def health_subsystem(name: str) -> Dict[str, Any]:
        """Check a specific subsystem by name."""
        result = await aggregator.run_single_check(name)
        return {
            "name": result.name, "status": result.status,
            "response_time_ms": result.response_time_ms,
            "details": result.details, "error": result.error,
        }

    return router


# ═══════════════════════════════════════════════════════════════════
# Self Test
# ═══════════════════════════════════════════════════════════════════

def self_test() -> Dict[str, Any]:
    """Run internal validation of the health system."""
    errors: List[str] = []
    if len(PROBE_REGISTRY) != 12:
        errors.append(f"Expected 12 probes, found {len(PROBE_REGISTRY)}")
    required = ["redis", "sqlite", "openai", "filesystem", "memory"]
    for name in required:
        if name not in PROBE_REGISTRY:
            errors.append(f"Missing required probe: {name}")
    if "not_a_probe" in PROBE_REGISTRY:
        errors.append("Unexpected probe found")
    return {"valid": len(errors) == 0, "errors": errors}


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(self_test(), indent=2))
    aggregator = HealthAggregator()
    report = asyncio.run(aggregator.run_all_checks())
    print(json.dumps(report.to_dict(), indent=2))
