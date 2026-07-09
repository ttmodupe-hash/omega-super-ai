#!/usr/bin/env python3
"""
Luqi AI - Government Services Security Patch
=============================================
Safe SQL wrappers to fix injection vulnerabilities in government_services.py.
Drop-in replacements for f-string query functions.

Part of Luqi AI v24.4.0 Security Hardening — Built by Limitless Telecoms
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.db_utils import (
    safe_count, safe_query, safe_select_by_id, safe_select_paginated,
    validate_table_name, execute_safe,
)
from backend.exception_handler import (
    ResourceNotFoundError, ExternalServiceError, ValidationError,
    safe_execute,
)

logger = logging.getLogger(__name__)

# Government-specific allowed tables
GOVERNMENT_TABLES = frozenset({
    "government_services", "services", "documents", "forms",
    "applications", "permits", "licenses", "registrations",
    "citizens", "appointments", "payments", "notifications",
})


def safe_count_query(table: str, where: Dict[str, Any] = None) -> Tuple[str, tuple]:
    """Safe replacement for f-string count queries."""
    return safe_count(table, where=where, module="government")


def safe_select_query(table: str, columns: List[str] = None, where: Dict[str, Any] = None,
                      order_by: str = None, limit: int = None, offset: int = None) -> Tuple[str, tuple]:
    """Safe replacement for f-string SELECT queries."""
    return safe_query(table, columns=columns, where=where, order_by=order_by,
                      limit=limit, offset=offset, module="government")


def safe_select_paginated_gov(table: str, columns: List[str] = None, where: Dict[str, Any] = None,
                                order_by: str = None, page: int = 1, per_page: int = 20) -> Tuple[str, tuple]:
    """Safe paginated SELECT for government tables."""
    return safe_select_paginated(table, columns=columns, where=where, order_by=order_by,
                                 page=page, per_page=per_page, module="government")


def safe_execute_government_count(cursor, table: str, where: Dict[str, Any] = None) -> int:
    """Drop-in replacement: safely execute a count query and return the integer result.

    Args:
        cursor: Database cursor.
        table: Table name (whitelisted).
        where: Optional WHERE conditions.

    Returns:
        Integer count value, or 0 on error.
    """
    def _execute():
        query, params = safe_count(table, where=where, module="government")
        result = cursor.execute(query, params)
        row = result.fetchone()
        return row[0] if row else 0

    return safe_execute(_execute, default=0, catch=(ValueError, ConnectionError, RuntimeError))


def safe_execute_government_select(cursor, table: str, columns: List[str] = None,
                                   where: Dict[str, Any] = None) -> List[dict]:
    """Safely execute a SELECT and return results as dicts.

    Args:
        cursor: Database cursor.
        table: Table name (whitelisted).
        columns: Columns to select.
        where: WHERE conditions.

    Returns:
        List of row dicts, or empty list on error.
    """
    def _execute():
        query, params = safe_query(table, columns=columns, where=where, module="government")
        result = cursor.execute(query, params)
        rows = result.fetchall()
        if not columns:
            columns_found = [d[0] for d in result.description] if result.description else []
        else:
            columns_found = columns
        return [dict(zip(columns_found, row)) for row in rows]

    return safe_execute(_execute, default=[], catch=(ValueError, ConnectionError, RuntimeError))


def handle_government_db_error(exc: Exception, operation: str = "database operation", table: str = None) -> None:
    """Translate database errors into LuqiException types.

    Args:
        exc: The caught exception.
        operation: Description of the operation that failed.
        table: Table name involved.

    Raises:
        ResourceNotFoundError: For KeyError, IndexError.
        ExternalServiceError: For ConnectionError, TimeoutError.
        ValidationError: For ValueError, TypeError.
    """
    msg = f"{operation} failed"
    if table:
        msg += f" on table {table}"

    if isinstance(exc, (KeyError, IndexError)):
        raise ResourceNotFoundError(f"{msg}: {exc}", resource_type=table) from exc
    elif isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        raise ExternalServiceError(f"{msg}: {exc}", service="government_db") from exc
    elif isinstance(exc, (ValueError, TypeError)):
        raise ValidationError(f"{msg}: {exc}") from exc
    else:
        logger.exception("Unexpected government DB error: %s", exc)
        raise ExternalServiceError(f"{msg}: unexpected error", service="government_db") from exc
