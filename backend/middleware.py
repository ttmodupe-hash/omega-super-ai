#!/usr/bin/env python3
"""Luqi AI v20 — Production Middleware

Production hardening layer providing:
    * Rate limiting (slowapi)
    * Security headers
    * Request logging with request IDs
    * Error handling with safe responses
    * Module health monitoring

Usage:
    from backend.middleware import setup_all_middleware
    setup_all_middleware(app)  # registers all middleware on FastAPI app
"""

from __future__ import annotations

import logging
import time
import traceback
import uuid
from typing import Callable, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("luqi.middleware")

# ──────────────────────────────────────────────────────────────────────────
# RATE LIMITING
# ──────────────────────────────────────────────────────────────────────────

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter: Optional[Limiter] = Limiter(key_func=get_remote_address)
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    limiter = None
    RATE_LIMITING_AVAILABLE = False
    logger.warning("slowapi not installed — rate limiting disabled")

# Rate limit constants
RATE_GENERAL = "30/minute"
RATE_AUTH = "10/minute"
RATE_UPLOAD = "5/minute"


def add_rate_limiting(app: FastAPI) -> Optional[Limiter]:
    """Register rate limiting on the FastAPI app.

    Returns the limiter instance for use in route decorators, or None
    if slowapi is not available.
    """
    if not RATE_LIMITING_AVAILABLE or limiter is None:
        logger.warning("Rate limiting not available")
        return None

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled: %s general, %s auth, %s upload", 
                RATE_GENERAL, RATE_AUTH, RATE_UPLOAD)
    return limiter


# ──────────────────────────────────────────────────────────────────────────
# SECURITY HEADERS MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdn.tailwindcss.com https://unpkg.com https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' ws: wss:;"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
        for header, value in headers.items():
            response.headers[header] = value
        return response


# ──────────────────────────────────────────────────────────────────────────
# ERROR HANDLING MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return safe JSON responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            logger.error(
                "Unhandled exception [req:%s] %s %s: %s\n%s",
                request_id,
                request.method,
                request.url.path,
                exc,
                traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "message": "An unexpected error occurred. Please try again.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )


# ──────────────────────────────────────────────────────────────────────────
# REQUEST LOGGING MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing, method, path, status, and client IP."""

    # Paths to skip logging (reduce noise)
    SKIP_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable):
        start = time.time()
        request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])

        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000
        path = request.url.path

        if path not in self.SKIP_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            log_msg = (
                f"[{request_id}] {request.method} {path} "
                f"{response.status_code} {duration_ms:.1f}ms {client_ip}"
            )
            if duration_ms > 1000:
                logger.warning("SLOW REQUEST %s", log_msg)
            else:
                logger.info(log_msg)

        response.headers["X-Request-ID"] = request_id
        return response


# ──────────────────────────────────────────────────────────────────────────
# MODULE HEALTH CHECKER
# ──────────────────────────────────────────────────────────────────────────

MODULES_TO_CHECK = [
    # Core
    ("backend.ai_engine", "AI Engine"),
    ("backend.search", "Search"),
    ("backend.memory", "Memory"),
    ("backend.files", "Files"),
    ("backend.images", "Images"),
    # v14
    ("backend.subscriptions", "Subscriptions"),
    ("backend.developer", "Developer"),
    ("backend.website_builder", "Website Builder"),
    ("backend.dashboard", "Dashboard"),
    # v15
    ("backend.cognitive_engine", "Cognitive Engine"),
    ("backend.education_system", "Education System"),
    ("backend.voice_system", "Voice System"),
    ("backend.safety_alignment", "Safety Alignment"),
    ("backend.physics_simulator", "Physics Simulator"),
    # v16
    ("backend.github_integration", "GitHub Integration"),
    ("backend.notifications", "Notifications"),
    ("backend.data_portability", "Data Portability"),
    # v17
    ("backend.captainship", "Captainship"),
    ("backend.companionship", "Companionship"),
    # v18
    ("backend.automotive", "Automotive"),
    ("backend.writing_assistant", "Writing Assistant"),
    # v19
    ("backend.law_studies", "Law Studies"),
    # v20
    ("backend.agricultural_advisor", "Agricultural Advisor"),
    ("backend.healthcare_assistant", "Healthcare Assistant"),
    ("backend.teacher_assistant", "Teacher Assistant"),
    ("backend.business_advisor", "Business Advisor"),
    ("backend.offline_engine", "Offline Engine"),
]


def check_module_health_sync() -> Dict[str, Dict]:
    """Check if all v13-v20 modules can be imported.

    Returns:
        Dict mapping module name to {loaded: bool, error: str|None}
    """
    results: Dict[str, Dict] = {}
    for module_name, display_name in MODULES_TO_CHECK:
        try:
            __import__(module_name)
            results[display_name] = {"loaded": True, "error": None}
        except Exception as exc:
            results[display_name] = {"loaded": False, "error": str(exc)}
    return results


async def check_module_health() -> Dict[str, Dict]:
    """Async wrapper for check_module_health_sync."""
    return check_module_health_sync()


# ──────────────────────────────────────────────────────────────────────────
# SETUP ALL MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────

def setup_all_middleware(app: FastAPI) -> None:
    """Register all production middleware in the correct order.

    Order (outer → inner):
        1. Security headers (first to touch response)
        2. Error handling (catches everything)
        3. Request logging (measures timing)
        4. Rate limiting (closest to handlers)
    """
    # 1. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware enabled")

    # 2. Error handling
    app.add_middleware(ErrorHandlingMiddleware)
    logger.info("Error handling middleware enabled")

    # 3. Request logging
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware enabled")

    # 4. Rate limiting
    add_rate_limiting(app)

    logger.info("All production middleware registered")
