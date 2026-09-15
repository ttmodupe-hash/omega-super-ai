"""
OMEGA-LUQI Row-Level Security binding helper.

PostgreSQL GUCs (app.current_user_country) are per-CONNECTION, so the binding
must execute inside the same transaction as the queries it protects. Call
attach_rls_context(session, country) immediately after opening a session that
will touch RLS-protected tables. The HTTP middleware in core/main.py extracts
the country from the JWT and stores it on request.state; DB-backed endpoints
pass it through here.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def attach_rls_context(session: Session, country_code: str) -> None:
    """Bind the sovereign country context for this transaction.

    SET LOCAL scopes the GUC to the current transaction - it cannot leak
    across pooled connections. Empty/None country -> the NULLIF in the
    policies yields NULL -> zero visible rows (fail-closed)."""
    session.execute(
        text("SET LOCAL app.current_user_country = :country"),
        {"country": (country_code or "").upper()[:3]},
    )
