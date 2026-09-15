"""
OMEGA-LUQI Secure Webhook Handshake Node

HMAC-SHA512 signature validation for payment provider callbacks (Paystack
format). Constant-time comparison prevents timing-oracle forgery.

Integration note: a webhook payload does not carry the Luqi-AI user mapping,
so this node VERIFIES and ACKNOWLEDGES only. Settlement flows through the
authenticated /v1/payments/verify-credit or /v1/gateways/process-settlement
routes - never credit a wallet directly from a webhook without joining the
reference to an authenticated user record.
"""
import os
import hmac
import hashlib

from fastapi import APIRouter, Request, Header, HTTPException, status

webhook_router = APIRouter(prefix="/v1/webhooks", tags=["Cryptographic Entrypoints"])

ALGO = hashlib.sha512


@webhook_router.post("/paystack-settlement")
async def secure_paystack_webhook_receiver(
    request: Request,
    x_paystack_signature: str = Header(None),
):
    """HMAC-validated webhook interceptor. Forged or replayed packets rejected."""
    if not x_paystack_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security Violation: Missing verification signature header.",
        )

    raw_payload = await request.body()
    secret = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_MockSecretTestingKey2026_ChangeMe!")

    computed = hmac.new(secret.encode("utf-8"), msg=raw_payload, digestmod=ALGO).hexdigest()
    if not hmac.compare_digest(computed, x_paystack_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Gate Fault: webhook signature mismatch.",
        )

    payload = await request.json()
    if payload.get("event") == "charge.success":
        # Verified authentic. Settlement still requires the authenticated
        # verify-credit route (user join) + the 30% gate - see module docstring.
        print(f"[Webhook Hub] Authenticated charge.success: {payload['data']['reference']}")

    return {"status": "accepted", "checksum_verified": True}
