"""
OMEGA-LUQI Admin Verification

Shared by main.py (gate override, monitor feeds) and any admin-gated router
(self-healing, etc.). Lives in its own module so routers never import main -
that direction is always a circular import.
"""
import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .security_guards import DEFAULT_ADMIN_SECRET

API_KEY_NAME = "X-Luqi-Admin-Auth"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def verify_admin(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("LUQI_ADMIN_SECRET", DEFAULT_ADMIN_SECRET):
        raise HTTPException(status_code=403, detail="Unauthorized Human Intervention Attempt.")
    return True
