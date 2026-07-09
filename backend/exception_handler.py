#!/usr/bin/env python3
"""
Luqi AI - Centralized Exception Handler
========================================
Custom exception hierarchy and safe execution utilities.
Replaces all bare `except Exception:` patterns with specific exception handling.

Part of Luqi AI v24.4.0 Security Hardening — Built by Limitless Telecoms
"""

import json
import logging
import functools
import asyncio
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTION HIERARCHY
# ═══════════════════════════════════════════════════════════════════

class LuqiException(Exception):
    """Base exception for the Luqi AI platform."""
    status_code = 500
    error_code = "INTERNAL_ERROR"

    def __init__(self, message: str = None, details: dict = None):
        self.message = message or "An internal error occurred"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(LuqiException):
    """Input validation failed. Maps to HTTP 422."""
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed", field: str = None, details: dict = None):
        self.field = field
        super().__init__(message, details)


class AuthenticationError(LuqiException):
    """Authentication failed. Maps to HTTP 401."""
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"


class AuthorizationError(LuqiException):
    """Permission denied. Maps to HTTP 403."""
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"


class ResourceNotFoundError(LuqiException):
    """Requested resource not found. Maps to HTTP 404."""
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found", resource_type: str = None, resource_id: str = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message)


class RateLimitError(LuqiException):
    """Rate limit exceeded. Maps to HTTP 429."""
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message)


class ExternalServiceError(LuqiException):
    """Third-party service failure. Maps to HTTP 502."""
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, message: str = "External service error", service: str = None):
        self.service = service
        super().__init__(message)


class DatabaseError(LuqiException):
    """Database operation failed. Maps to HTTP 500."""
    status_code = 500
    error_code = "DATABASE_ERROR"


class ConfigurationError(LuqiException):
    """Invalid or missing configuration. Maps to HTTP 500."""
    status_code = 500
    error_code = "CONFIGURATION_ERROR"


class ConflictError(LuqiException):
    """Resource conflict (e.g., duplicate). Maps to HTTP 409."""
    status_code = 409
    error_code = "CONFLICT"


# ═══════════════════════════════════════════════════════════════════
# EXCEPTION MAP
# ═══════════════════════════════════════════════════════════════════

# Maps exception types to (status_code, error_code) tuples
EXCEPTION_MAP: Dict[Type[Exception], Tuple[int, str]] = {
    # Luqi exceptions
    ValidationError: (422, "VALIDATION_ERROR"),
    AuthenticationError: (401, "AUTHENTICATION_ERROR"),
    AuthorizationError: (403, "AUTHORIZATION_ERROR"),
    ResourceNotFoundError: (404, "NOT_FOUND"),
    RateLimitError: (429, "RATE_LIMIT_EXCEEDED"),
    ExternalServiceError: (502, "EXTERNAL_SERVICE_ERROR"),
    DatabaseError: (500, "DATABASE_ERROR"),
    ConfigurationError: (500, "CONFIGURATION_ERROR"),
    ConflictError: (409, "CONFLICT"),
    LuqiException: (500, "INTERNAL_ERROR"),
    # Python built-in exceptions
    ValueError: (422, "INVALID_VALUE"),
    TypeError: (422, "INVALID_TYPE"),
    KeyError: (404, "KEY_NOT_FOUND"),
    FileNotFoundError: (404, "FILE_NOT_FOUND"),
    PermissionError: (403, "PERMISSION_DENIED"),
    ConnectionError: (502, "CONNECTION_ERROR"),
    TimeoutError: (504, "TIMEOUT"),
    json.JSONDecodeError: (400, "INVALID_JSON"),
}


# ═══════════════════════════════════════════════════════════════════
# EXCEPTION HANDLER
# ═══════════════════════════════════════════════════════════════════

def handle_exception(exc: Exception) -> JSONResponse:
    """Convert any exception to a structured JSONResponse.

    Walks the exception's MRO to find the most specific handler.
    Logs the full traceback for 500-level errors.

    Args:
        exc: The exception to handle.

    Returns:
        JSONResponse with status code, error code, and message.
    """
    # Walk the MRO to find the most specific match
    for exc_type in type(exc).__mro__:
        if exc_type in EXCEPTION_MAP:
            status_code, error_code = EXCEPTION_MAP[exc_type]
            break
    else:
        status_code, error_code = 500, "INTERNAL_ERROR"

    # Log appropriately
    if status_code >= 500:
        logger.exception("Server error [%s]: %s", error_code, str(exc))
    elif status_code == 429:
        logger.warning("Rate limit: %s", str(exc))
    elif status_code >= 400:
        logger.info("Client error [%s]: %s", error_code, str(exc))

    # Build response
    body = {
        "error": {
            "code": error_code,
            "message": str(exc),
            "status": status_code,
        }
    }

    # Include details for LuqiException subclasses
    if isinstance(exc, LuqiException) and exc.details:
        body["error"]["details"] = exc.details

    if isinstance(exc, RateLimitError):
        body["error"]["retry_after"] = exc.retry_after

    if isinstance(exc, ResourceNotFoundError):
        if exc.resource_type:
            body["error"]["resource_type"] = exc.resource_type
        if exc.resource_id:
            body["error"]["resource_id"] = exc.resource_id

    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=headers,
    )


def get_error_response(exc: Exception) -> dict:
    """Get error response dict without creating JSONResponse.

    Args:
        exc: The exception.

    Returns:
        Dict with error code, message, and status.
    """
    for exc_type in type(exc).__mro__:
        if exc_type in EXCEPTION_MAP:
            status_code, error_code = EXCEPTION_MAP[exc_type]
            break
    else:
        status_code, error_code = 500, "INTERNAL_ERROR"

    return {
        "code": error_code,
        "message": str(exc),
        "status": status_code,
    }


# ═══════════════════════════════════════════════════════════════════
# SAFE EXECUTE WRAPPER
# ═══════════════════════════════════════════════════════════════════

def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    catch: Tuple[Type[Exception], ...] = None,
    log_level: str = "error",
    **kwargs,
) -> Any:
    """Execute a function catching only specific exception types.

    NEVER uses bare except — only catches explicitly listed exceptions.

    Args:
        func: Function to execute.
        *args: Positional arguments for func.
        default: Value to return if an exception is caught.
        catch: Tuple of exception types to catch. Defaults to common safe types.
        log_level: Logging level ("error", "warning", "info", "exception").
        **kwargs: Keyword arguments for func.

    Returns:
        func's return value, or default if an exception is caught.
    """
    if catch is None:
        catch = (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError)

    try:
        return func(*args, **kwargs)
    except catch as e:
        log_func = getattr(logger, log_level, logger.error)
        log_func("safe_execute caught %s in %s: %s", type(e).__name__, func.__name__, e)
        return default


async def safe_execute_async(
    func: Callable,
    *args,
    default: Any = None,
    catch: Tuple[Type[Exception], ...] = None,
    log_level: str = "error",
    **kwargs,
) -> Any:
    """Async version of safe_execute.

    Args:
        func: Async function to execute.
        *args: Positional arguments.
        default: Default return on exception.
        catch: Exception types to catch.
        log_level: Logging level.
        **kwargs: Keyword arguments.

    Returns:
        func's return value, or default if an exception is caught.
    """
    if catch is None:
        catch = (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError)

    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)
    except catch as e:
        log_func = getattr(logger, log_level, logger.error)
        log_func("safe_execute_async caught %s in %s: %s", type(e).__name__, func.__name__, e)
        return default


# ═══════════════════════════════════════════════════════════════════
# FASTAPI INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def register_exception_handlers(app):
    """Register all exception handlers on a FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    # Register handlers for all LuqiException types
    for exc_type in [LuqiException, ValidationError, AuthenticationError,
                     AuthorizationError, ResourceNotFoundError, RateLimitError,
                     ExternalServiceError, DatabaseError, ConfigurationError,
                     ConflictError]:
        @app.exception_handler(exc_type)
        async def _handler(request, exc):
            return handle_exception(exc)

    # Generic fallback handler
    @app.exception_handler(Exception)
    async def _fallback_handler(request, exc):
        logger.exception("Unhandled exception: %s", exc)
        return handle_exception(exc)

    logger.info("Registered %d exception handlers", len(EXCEPTION_MAP))


# ═══════════════════════════════════════════════════════════════════
# RETRY WITH BACKOFF
# ═══════════════════════════════════════════════════════════════════

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    catch: Tuple[Type[Exception], ...] = None,
):
    """Decorator that retries a function with exponential backoff.

    Catches only specific exception types — never bare except.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Multiplier for exponential backoff.
        catch: Tuple of exception types to catch and retry.
    """
    if catch is None:
        catch = (ConnectionError, TimeoutError, ExternalServiceError)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except catch as e:
                    if attempt == max_retries:
                        logger.error("Failed after %d retries: %s", max_retries, e)
                        raise
                    logger.warning("Attempt %d/%d failed: %s. Retrying in %.1fs",
                                   attempt, max_retries, e, delay)
                    import time
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            # Should never reach here
            raise RuntimeError("Unexpected exit from retry loop")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return func(*args, **kwargs)
                except catch as e:
                    if attempt == max_retries:
                        logger.error("Failed after %d retries: %s", max_retries, e)
                        raise
                    logger.warning("Attempt %d/%d failed: %s. Retrying in %.1fs",
                                   attempt, max_retries, e, delay)
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            raise RuntimeError("Unexpected exit from retry loop")

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# EXCEPTION TRANSLATION CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════

class translate_exceptions:
    """Context manager that translates third-party exceptions to LuqiException.

    Usage:
        with translate_exceptions({ConnectionError: ExternalServiceError}):
            response = requests.get(url)
    """

    def __init__(self, mapping: Dict[Type[Exception], Type[LuqiException]]):
        self.mapping = mapping

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and exc_type in self.mapping:
            target = self.mapping[exc_type]
            raise target(str(exc_val)) from exc_val
        return False  # Don't suppress unmapped exceptions
