#!/usr/bin/env python3
"""Luqi AI v24 -- Background Task Queue

Asynchronous task processing with RQ (Redis-backed) and threading fallback.

Features:
- Redis-backed job queue with RQ
- Threading fallback for local development
- Task retry with exponential backoff
- Dead letter queue for failed jobs
- Task status tracking

Usage:
    from backend.background_tasks import enqueue_task, get_task_status, background_task

    job = enqueue_task(send_email, to="user@example.com", subject="Hello")
    status = get_task_status(job.task_id)
"""

from __future__ import annotations

import functools
import logging
import os
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger: logging.Logger = logging.getLogger("luqi.tasks")

# ── Configuration ──────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")
MAX_WORKERS = int(os.getenv("TASK_WORKERS", "4"))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "300"))
MAX_RETRIES = int(os.getenv("TASK_MAX_RETRIES", "3"))
RETRY_DELAY_BASE = int(os.getenv("TASK_RETRY_DELAY", "5"))
DEAD_LETTER_MAX = int(os.getenv("DEAD_LETTER_MAX", "1000"))

F = TypeVar("F", bound=Callable[..., Any])


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None


class DeadLetterQueue:
    """Store failed tasks for later analysis."""

    def __init__(self, max_items: int = DEAD_LETTER_MAX) -> None:
        self._max_items = max_items
        self._tasks: Dict[str, TaskResult] = {}

    def add(self, result: TaskResult) -> None:
        if len(self._tasks) >= self._max_items:
            oldest = min(self._tasks, key=lambda k: self._tasks[k].created_at)
            del self._tasks[oldest]
        self._tasks[result.task_id] = result

    def get(self, task_id: str) -> Optional[TaskResult]:
        return self._tasks.get(task_id)

    def list_recent(self, limit: int = 50) -> List[TaskResult]:
        sorted_tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return sorted_tasks[:limit]

    def health(self) -> Dict[str, Any]:
        return {"dead_tasks": len(self._tasks), "max_size": self._max_items}


class ThreadingBackend:
    """Threading-based task backend for local development."""

    def __init__(self, max_workers: int = MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="luqi_task_")
        self._results: Dict[str, TaskResult] = {}
        self._dlq = DeadLetterQueue()
        self._submitted = 0
        self._completed = 0
        self._failed = 0

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> TaskResult:
        task_id = str(uuid.uuid4())[:16]
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        self._results[task_id] = result
        self._submitted += 1
        self._executor.submit(self._run_task, task_id, func, args, kwargs)
        return result

    def _run_task(self, task_id: str, func: Callable[..., Any], args: tuple, kwargs: dict) -> None:
        result = self._results.get(task_id)
        if not result:
            return
        result.status = TaskStatus.RUNNING
        result.started_at = datetime.utcnow().isoformat()
        start = time.perf_counter()

        for attempt in range(MAX_RETRIES + 1):
            try:
                task_result = func(*args, **kwargs)
                result.status = TaskStatus.SUCCESS
                result.result = task_result
                result.finished_at = datetime.utcnow().isoformat()
                result.duration_ms = (time.perf_counter() - start) * 1000
                self._completed += 1
                return
            except Exception as exc:
                result.retries = attempt
                if attempt < MAX_RETRIES:
                    result.status = TaskStatus.RETRYING
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning("Task %s failed (attempt %d/%d), retrying in %ds: %s",
                                   task_id, attempt + 1, MAX_RETRIES + 1, delay, exc)
                    time.sleep(delay)
                else:
                    result.status = TaskStatus.FAILED
                    result.error = f"{exc}\n{traceback.format_exc()}"
                    result.finished_at = datetime.utcnow().isoformat()
                    result.duration_ms = (time.perf_counter() - start) * 1000
                    self._failed += 1
                    self._dlq.add(result)
                    logger.error("Task %s failed permanently after %d retries", task_id, MAX_RETRIES)

    def get_status(self, task_id: str) -> Optional[TaskResult]:
        return self._results.get(task_id) or self._dlq.get(task_id)

    def health(self) -> Dict[str, Any]:
        return {
            "backend": "threading", "workers": MAX_WORKERS,
            "submitted": self._submitted, "completed": self._completed,
            "failed": self._failed, "dead_letter": self._dlq.health(),
        }


class RQBackend:
    """Redis Queue backend for production deployments."""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._redis_url = redis_url
        self._queue: Any = None
        self._connection: Any = None
        self._connect()

    def _connect(self) -> None:
        if not self._redis_url:
            return
        try:
            from redis import Redis
            from rq import Queue
            self._connection = Redis.from_url(self._redis_url, socket_connect_timeout=3)
            self._connection.ping()
            self._queue = Queue("luqi-default", connection=self._connection)
            logger.info("Task queue: RQ connected")
        except Exception as exc:
            logger.warning("Task queue: RQ unavailable: %s", exc)
            self._queue = None

    def is_available(self) -> bool:
        return self._queue is not None

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> TaskResult:
        if not self._queue:
            raise RuntimeError("RQ not available")
        try:
            from rq.job import Job
            job = self._queue.enqueue(func, *args, **kwargs, job_timeout=TASK_TIMEOUT, retry=MAX_RETRIES)
            return TaskResult(task_id=job.id, status=TaskStatus.PENDING)
        except Exception as exc:
            logger.error("RQ enqueue failed: %s", exc)
            raise

    def get_status(self, task_id: str) -> Optional[TaskResult]:
        if not self._connection:
            return None
        try:
            from rq.job import Job
            job = Job.fetch(task_id, connection=self._connection)
            status_map = {"queued": TaskStatus.PENDING, "started": TaskStatus.RUNNING,
                          "finished": TaskStatus.SUCCESS, "failed": TaskStatus.FAILED,
                          "deferred": TaskStatus.PENDING}
            return TaskResult(
                task_id=job.id, status=status_map.get(job.get_status(), TaskStatus.PENDING),
                result=job.result, error=str(job.exc_info) if job.exc_info else None,
            )
        except Exception:
            return None

    def health(self) -> Dict[str, Any]:
        queue_size = 0
        if self._queue:
            try:
                queue_size = len(self._queue)
            except Exception:
                pass
        return {"backend": "rq", "available": self.is_available(), "queue_size": queue_size}


class TaskManager:
    """Unified task manager with RQ -> threading fallback."""

    def __init__(self) -> None:
        self._rq = RQBackend()
        self._threading = ThreadingBackend()

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> TaskResult:
        if self._rq.is_available():
            try:
                return self._rq.enqueue(func, *args, **kwargs)
            except Exception as exc:
                logger.warning("RQ enqueue failed, using threading: %s", exc)
        return self._threading.enqueue(func, *args, **kwargs)

    def get_status(self, task_id: str) -> Optional[TaskResult]:
        result = self._rq.get_status(task_id)
        if result:
            return result
        return self._threading.get_status(task_id)

    def health(self) -> Dict[str, Any]:
        return {"rq": self._rq.health(), "threading": self._threading.health()}


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def enqueue_task(func: Callable[..., Any], *args: Any, **kwargs: Any) -> TaskResult:
    """Enqueue a function for background execution."""
    return get_task_manager().enqueue(func, *args, **kwargs)


def get_task_status(task_id: str) -> Optional[TaskResult]:
    """Get the status of a queued task."""
    return get_task_manager().get_status(task_id)


def task_health() -> Dict[str, Any]:
    """Get task queue health for monitoring."""
    return get_task_manager().health()


def background_task(func: F) -> F:
    """Decorator to make a function enqueueable as a background task."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    wrapper.enqueue = lambda *a, **kw: enqueue_task(func, *a, **kw)  # type: ignore[attr-defined]
    wrapper.get_status = get_task_status  # type: ignore[attr-defined]
    return wrapper
