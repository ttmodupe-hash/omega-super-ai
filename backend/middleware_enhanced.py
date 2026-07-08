#!/usr/bin/env python3
"""Luqi AI v24 -- Enhanced Production Middleware

Comprehensive middleware stack providing:
- Request correlation IDs for distributed tracing
- Structured JSON logging
- Rate limiting (Redis-backed with in-memory fallback)
- Request validation and sanitization
- Security headers
- Request timing and metrics
- Global exception handling

Usage:
    from backend.middleware_enhanced import setup_middleware
    app = FastAPI()
    setup_middleware(app)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import traceback
import uuid
from typing import Any, Dict, Final, List, Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger: Final = logging.getLogger("luqi.middleware")

# ── Configuration ──────────────────────────────────────────────────
RATE_LIMIT_GENERAL: Final = int(os.getenv("RATE_LIMIT_GENERAL", "100"))
RATE_LIMIT_AUTH: Final = int(os.getenv("RATE_LIMIT_AUTH", "10"))
MAX_BODY_SIZE: Final = int(os.getenv("MAX_BODY_SIZE", "10485760"))
REDIS_URL: Final = os.getenv("REDIS_URL", "")
SENSITIVE_PATHS: Final = ["/api/login", "/api/register", "/api/reset-password"]

SECURITY_HEADERS: Final[Dict[str, str]] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "cross-origin",
}

SENSITIVE_PATTERNS: Final[List[re.Pattern[str]]] = [
    re.compile(r"password\s*[=:]\s*[^\s&]+", re.IGNORECASE),
    re.compile(r"token\s*[=:]\s*[^\s&]+", re.IGNORECASE),
    re.compile(r"secret\s*[=:]\s*[^\s&]+", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[=:]\s*[^\s&]+", re.IGNORECASE),
]

SUSPICIOUS_PATTERNS: Final[List[re.Pattern[str]]] = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"(SELECT|INSERT|UPDATE|DELETE|DROP|UNION).*--", re.IGNORECASE),
    re.compile(r"\.\./|\.\.\\"),
    re.compile(r"`[^`]*`|\$\([^)]*\)"),
    re.compile(r"\{\{.*\}\}"),
]


class RequestContext:
    """Holds per-request context for correlation and logging."""

    _context: Dict[str, Any] = {}

    @classmethod
    def get_request_id(cls) -> str:
        """Get current request ID."""
        return cls._context.get("request_id", "")

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        """Set the current request ID."""
        cls._context["request_id"] = request_id


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        ctx = RequestContext._context
        if ctx:
            log_data["request_id"] = ctx.get("request_id", "")
        for key in ["method", "path", "status_code", "duration_ms", "client_ip", "user_agent"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        if record.exc_info:
            log_data["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_data, default=str)


class RateLimiter:
    """Rate limiter with Redis backend and in-memory fallback."""

    def __init__(self) -> None:
        self._redis: Any = None
        self._memory: Dict[str, List[float]] = {}
        self._init_redis()

    def _init_redis(self) -> None:
        if not REDIS_URL:
            return
        try:
            import redis as redis_lib
            self._redis = redis_lib.from_url(
                REDIS_URL, decode_responses=True, socket_connect_timeout=2
            )
            self._redis.ping()
            logger.info("Rate limiter: Redis connected")
        except Exception as exc:
            logger.warning("Rate limiter: Redis unavailable, using in-memory: %s", exc)
            self._redis = None

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        now = time.time()
        if self._redis:
            return self._redis_check(key, limit, window, now)
        return self._memory_check(key, limit, window, now)

    def _redis_check(self, key: str, limit: int, window: int, now: float) -> bool:
        try:
            redis_key = f"ratelimit:{key}"
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - window)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(now): now})
            pipe.expire(redis_key, window)
            _, current_count, _, _ = pipe.execute()
            return current_count < limit
        except Exception as exc:
            logger.warning("Redis rate limit failed, falling back to memory: %s", exc)
            return self._memory_check(key, limit, window, now)

    def _memory_check(self, key: str, limit: int, window: int, now: float) -> bool:
        cutoff = now - window
        entries = self._memory.get(key, [])
        entries = [t for t in entries if t > cutoff]
        entries.append(now)
        self._memory[key] = entries
        if hash(now) % 100 == 0:
            self._cleanup_memory(cutoff)
        return len(entries) <= limit

    def _cleanup_memory(self, cutoff: float) -> None:
        expired = [k for k, v in self._memory.items() if not v or v[-1] < cutoff]
        for k in expired:
            del self._memory[k]


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class EnhancedMiddleware(BaseHTTPMiddleware):
    """Main enhanced middleware handling requests and responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())[:16]
        RequestContext.set_request_id(request_id)
        request.state.request_id = request_id

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Rate limiting
        if not self._check_rate_limit(request, client_ip):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_request(request, request_id, 429, duration_ms, client_ip, user_agent, "rate_limited")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "request_id": request_id, "retry_after": 60},
                headers={"Retry-After": "60", "X-Request-ID": request_id},
            )

        # Body size check
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_request(request, request_id, 413, duration_ms, client_ip, user_agent, "body_too_large")
            return JSONResponse(
                status_code=413,
                content={"error": f"Request body exceeds {MAX_BODY_SIZE} bytes", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

        # Suspicious pattern detection
        body_preview = ""
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                body_bytes = await request.body()
                body_preview = body_bytes[:2000].decode("utf-8", errors="ignore")
                for pattern in SUSPICIOUS_PATTERNS:
                    if pattern.search(body_preview):
                        logger.warning("Suspicious pattern detected from %s: %s", client_ip, pattern.pattern[:50])
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        self._log_request(request, request_id, 400, duration_ms, client_ip, user_agent, "suspicious_content")
                        return JSONResponse(
                            status_code=400,
                            content={"error": "Suspicious content detected", "request_id": request_id},
                            headers={"X-Request-ID": request_id},
                        )
                # Re-assign body so downstream can read it
                async def receive() -> dict:
                    return {"type": "http.request", "body": body_bytes}
                request = Request(request.scope, receive, request._send)
        except Exception:
            pass

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc(), extra={"request_id": request_id, "method": request.method, "path": request.url.path})
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id, "detail": str(exc) if os.getenv("DEBUG") == "true" else None},
                headers={"X-Request-ID": request_id},
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        status_code = response.status_code
        error_type = None
        if status_code >= 500:
            error_type = "server_error"
        elif status_code >= 400:
            error_type = "client_error"

        self._log_request(request, request_id, status_code, duration_ms, client_ip, user_agent, error_type)
        return response

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, request: Request, client_ip: str) -> bool:
        limiter = get_rate_limiter()
        path = request.url.path
        is_auth = any(path.startswith(p) for p in SENSITIVE_PATHS)
        limit = RATE_LIMIT_AUTH if is_auth else RATE_LIMIT_GENERAL
        key = f"ip:{client_ip}:{path.split('/')[2] if len(path.split('/')) > 2 else 'general'}"
        return limiter.is_allowed(key, limit, window=60)

    def _log_request(
        self, request: Request, request_id: str, status_code: int,
        duration_ms: float, client_ip: str, user_agent: str, error_type: Optional[str] = None,
    ) -> None:
        log_data = {
            "request_id": request_id, "method": request.method,
            "path": request.url.path, "query": str(request.url.query),
            "status_code": status_code, "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip, "user_agent": user_agent[:200] if user_agent else "",
        }
        if error_type:
            log_data["error_type"] = error_type
        if status_code >= 500:
            logger.error("Request completed", extra=log_data)
        elif status_code >= 400:
            logger.warning("Request completed", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Validate request host header against allowed hosts."""

    def __init__(self, app: Any, allowed_hosts: Optional[List[str]] = None) -> None:
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["*"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        host = request.headers.get("host", "").split(":")[0]
        if "*" not in self.allowed_hosts and host not in self.allowed_hosts:
            return JSONResponse(status_code=400, content={"error": "Invalid host header"})
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    """Configure all production middleware on the FastAPI app."""
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(EnhancedMiddleware)
    allowed = os.getenv("ALLOWED_HOSTS", "*").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)
    logger.info("Enhanced middleware setup complete")


def get_request_id(request: Request) -> str:
    """Get the current request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def log_with_context(level: str, message: str, request: Request, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log a message with request context automatically attached."""
    rid = get_request_id(request)
    data: Dict[str, Any] = {"request_id": rid}
    if extra:
        data.update(extra)
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=data)
