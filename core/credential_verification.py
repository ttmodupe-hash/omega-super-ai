"""
OMEGA-LUQI Credential Verification Service.

Makes the engine's certificate authority (core/skill_engine.py) externally
verifiable: employers, universities, or anyone holding a CERT- serial can
confirm it against the real ledger - no account needed (read-only, public).

Honest scope:
  - Verifies OUR issued certificates against the actual cert ledger.
  - External provider verification (API Learning Network, Google Skills, etc.)
    is RESERVED: no real API contract exists without partnerships/keys. The
    providers endpoint lists candidates honestly labeled as pending.
  - The pasted blueprint's "verifier" hashed whatever serial it received and
    always returned an affirmative verdict - an always-yes verifier is resume
    fraud infrastructure, not security. This one says no (404) when the
    serial is not in the ledger.
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/credentials", tags=["Credential Verification"])

# Whitelisted external credential networks - integrations PENDING real API
# contracts (keys/partnerships). Listed for transparency, not faked as live.
PROVIDER_REGISTRY = {
    "API_LEARNING_NET": {
        "name": "African Professionalisation Initiative Learning Network",
        "url": "https://professionalisation.africa",
        "status": "PENDING_INTEGRATION",
        "note": "Requires partnership API credentials before live verification.",
    },
    "GOOGLE_SKILLS": {
        "name": "Google Cloud Skills Boost",
        "url": "https://www.cloudskillsboost.google",
        "status": "PENDING_INTEGRATION",
        "note": "Requires OAuth client credentials before live verification.",
    },
}


def verify_certificate_serial(serial: str) -> Dict[str, Any]:
    """Look up a CERT- serial in the real ledger. Raises 404 when absent."""
    from .skill_engine import verify_certificate
    record = verify_certificate(serial.strip())
    if not record:
        raise HTTPException(status_code=404, detail="certificate not found in ledger")
    return record


@router.get("/verify/{serial}")
async def verify_cert(serial: str) -> Dict[str, Any]:
    """PUBLIC employer verification: confirm a certificate is genuine."""
    return verify_certificate_serial(serial)


@router.get("/providers")
async def list_providers() -> Dict[str, Any]:
    """External verification networks we intend to support - honestly labeled."""
    return {"providers": PROVIDER_REGISTRY,
            "scope_note": "Only serials issued by this platform are verifiable live today; "
                          "external networks require partnership credentials (no simulation)."}
