#!/usr/bin/env python3
"""
Luqi AI - Data Portability Security Patch
==========================================
Safe wrappers fixing 17 bare-except handlers and SQL injection
in data_portability.py. Drop-in replacements.

Part of Luqi AI v24.4.0 Security Hardening — Built by Limitless Telecoms
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.db_utils import safe_delete, safe_query, safe_insert, execute_safe
from backend.exception_handler import (
    ValidationError, ResourceNotFoundError, ExternalServiceError, safe_execute,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# SAFE DATABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

PORTABILITY_TABLES = frozenset({
    "users", "subscriptions", "payments", "files", "notifications",
    "messages", "conversations", "projects", "tasks",
})


def safe_delete_from_table(table: str, where: Dict[str, Any], user_id: str) -> Tuple[str, tuple]:
    """Safe DELETE with automatic user_id scoping.

    Args:
        table: Table name (whitelisted).
        where: WHERE conditions.
        user_id: User ID injected for row-level security.

    Returns:
        Tuple of (query_string, parameters).
    """
    if table not in PORTABILITY_TABLES:
        raise ValidationError(f"Table {table!r} not allowed for data portability")
    scoped_where = dict(where)
    scoped_where["user_id"] = user_id
    return safe_delete(table, scoped_where)


def safe_select_portable(table: str, columns: List[str], user_id: str,
                         where: Dict[str, Any] = None) -> Tuple[str, tuple]:
    """Safe SELECT scoped to a specific user."""
    if table not in PORTABILITY_TABLES:
        raise ValidationError(f"Table {table!r} not allowed")
    scoped_where = dict(where or {})
    scoped_where["user_id"] = user_id
    return safe_query(table, columns=columns, where=scoped_where)


def safe_insert_portable_record(table: str, data: Dict[str, Any], user_id: str) -> Tuple[str, tuple]:
    """Safe INSERT with user_id and created_at auto-injection."""
    if table not in PORTABILITY_TABLES:
        raise ValidationError(f"Table {table!r} not allowed")
    from datetime import datetime
    record = dict(data)
    record["user_id"] = user_id
    record["created_at"] = datetime.utcnow().isoformat()
    return safe_insert(table, record)


# ═══════════════════════════════════════════════════════════════════
# EXCEPTION HANDLER WRAPPERS — Replace 17 bare-except locations
# ═══════════════════════════════════════════════════════════════════

def handle_export_error(exc: Exception, context: str = "export") -> None:
    """Handle export-related exceptions with specific types.

    Catches: ValueError, TypeError, KeyError, ConnectionError,
             TimeoutError, OSError, PermissionError, FileNotFoundError
    """
    msg = f"{context} failed: {exc}"
    if isinstance(exc, FileNotFoundError):
        raise ResourceNotFoundError(msg) from exc
    elif isinstance(exc, PermissionError):
        raise ExternalServiceError(msg, service="filesystem") from exc
    elif isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        raise ExternalServiceError(msg, service="database") from exc
    elif isinstance(exc, (ValueError, TypeError, KeyError)):
        raise ValidationError(msg) from exc
    else:
        logger.exception("Unexpected export error: %s", exc)
        raise ExternalServiceError(f"{context}: unexpected error", service="export") from exc


def handle_import_error(exc: Exception, context: str = "import") -> None:
    """Handle import-related exceptions.

    Catches: ValueError, TypeError, json.JSONDecodeError, KeyError, FileNotFoundError
    """
    msg = f"{context} failed: {exc}"
    if isinstance(exc, FileNotFoundError):
        raise ResourceNotFoundError(msg) from exc
    elif isinstance(exc, json.JSONDecodeError):
        raise ValidationError(f"Invalid JSON in {context}: {exc}") from exc
    elif isinstance(exc, (ValueError, TypeError, KeyError)):
        raise ValidationError(msg) from exc
    else:
        logger.exception("Unexpected import error: %s", exc)
        raise ValidationError(f"{context}: unexpected error") from exc


def handle_transform_error(exc: Exception, context: str = "transform") -> None:
    """Handle data transformation exceptions.

    Catches: ValueError, TypeError, KeyError
    """
    raise ValidationError(f"{context} failed: {exc}") from exc


def handle_download_error(exc: Exception, context: str = "download") -> None:
    """Handle download-related exceptions.

    Catches: FileNotFoundError, PermissionError, ConnectionError, TimeoutError
    """
    msg = f"{context} failed: {exc}"
    if isinstance(exc, FileNotFoundError):
        raise ResourceNotFoundError(msg) from exc
    elif isinstance(exc, (PermissionError, ConnectionError, TimeoutError)):
        raise ExternalServiceError(msg, service="storage") from exc
    else:
        logger.exception("Unexpected download error: %s", exc)
        raise ExternalServiceError(f"{context}: unexpected error", service="storage") from exc


# ═══════════════════════════════════════════════════════════════════
# SAFE PARSING UTILITIES
# ═══════════════════════════════════════════════════════════════════

def parse_json_safe(data: str, default: Any = None) -> Any:
    """Safely parse JSON with specific exception handling."""
    def _parse():
        return json.loads(data)
    return safe_execute(_parse, default=default, catch=(json.JSONDecodeError, TypeError, ValueError))


def coerce_int_safe(value: Any, default: int = 0) -> int:
    """Safely coerce a value to int."""
    def _coerce():
        return int(value)
    return safe_execute(_coerce, default=default, catch=(ValueError, TypeError))


def coerce_float_safe(value: Any, default: float = 0.0) -> float:
    """Safely coerce a value to float."""
    def _coerce():
        return float(value)
    return safe_execute(_coerce, default=default, catch=(ValueError, TypeError))


def coerce_bool_safe(value: Any, default: bool = False) -> bool:
    """Safely coerce a value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    def _coerce():
        return bool(value)
    return safe_execute(_coerce, default=default, catch=(TypeError, ValueError))


# ═══════════════════════════════════════════════════════════════════
# DECORATOR
# ═══════════════════════════════════════════════════════════════════

def portability_error_boundary(operation: str = "operation"):
    """Decorator that wraps data-portability functions with safe error handling.

    Usage:
        @portability_error_boundary("user export")
        def export_user_data(user_id: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError) as e:
                handle_transform_error(e, operation)
            except FileNotFoundError as e:
                handle_download_error(e, operation)
            except (ConnectionError, TimeoutError, PermissionError, OSError) as e:
                handle_export_error(e, operation)
        import functools
        return wrapper
    return decorator
