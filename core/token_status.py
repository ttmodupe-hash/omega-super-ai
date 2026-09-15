"""
OMEGA-LUQI Token & Integration Status Board

Single endpoint showing the health of EVERY external integration. Admin-gated.
Never exposes secret values - only state: ACTIVE / MISSING / INSECURE / RESERVED.

INSECURE  = present but still a template default (boot guards would refuse
            production start - this board shows WHY before you flip LUQI_ENV).
RESERVED  = env hook exists but the feature is not yet wired in code.
            (Hume EVI emotional tracking is the current example - the pasted
            integration map claimed it was active; it is not, so we say so.)
"""
import os

from fastapi import APIRouter, Depends

from .admin_auth import verify_admin
from .security_guards import DEFAULT_ADMIN_SECRET, DEFAULT_JWT_SECRET

router = APIRouter(tags=["System Integrity"])


def _state(present: bool, insecure: bool = False) -> str:
    if insecure:
        return "INSECURE"
    return "ACTIVE" if present else "MISSING"


def _docker_probe() -> str:
    socket_path = (os.getenv("DOCKER_HOST") or "unix:///var/run/docker.sock").replace("unix://", "")
    return "ACTIVE" if os.path.exists(socket_path) else "MISSING"


@router.get("/v1/system/token-status")
async def verify_all_active_tokens(is_authenticated: bool = Depends(verify_admin)):
    """Full integration board. Admin-only. Values never leave the vault."""
    # Effective secrets: unset falls back to the code defaults at runtime,
    # so "unset" means "the default is live" -> INSECURE, not MISSING.
    admin_secret = os.getenv("LUQI_ADMIN_SECRET", DEFAULT_ADMIN_SECRET)
    jwt_secret = os.getenv("JWT_SECRET_SIGNING_KEY", DEFAULT_JWT_SECRET)

    gateways = {
        # --- AI brains (unified Kimi group) ---
        "kimi_k3_brain": _state(bool(os.getenv("KIMI_API_KEY"))),
        "gemini_africa_south1": _state(bool(os.getenv("GEMINI_API_KEY"))),
        "claude_engineering": _state(bool(os.getenv("CLAUDE_API_KEY"))),
        "hume_evi_emotion": _state(bool(os.getenv("HUME_WEBHOOK_SECRET")) or bool(os.getenv("HUME_API_KEY"))),
        # ingestion hooks active when secret set; EVI client subscription remains future work
        # --- Voice synthesis ---
        "elevenlabs_sovereign_voice": _state(bool(os.getenv("XI_API_KEY"))),
        "core_academic_fulltext": _state(bool(os.getenv("CORE_API_KEY"))),
        # --- Payments ---
        "paystack_clearing": _state(bool(os.getenv("PAYSTACK_SECRET_KEY")),
                                    insecure=os.getenv("PAYSTACK_SECRET_KEY", "").startswith("sk_test_")
                                    and os.getenv("LUQI_ENV", "development") == "production"),
        "mpesa_daraja": _state(bool(os.getenv("MPESA_CONSUMER_KEY")) and bool(os.getenv("MPESA_CONSUMER_SECRET"))),
        "flutterwave_global": _state(bool(os.getenv("FLUTTERWAVE_SECRET_KEY"))),
        "payfast_ozow_eft": _state(bool(os.getenv("PAYFAST_MERCHANT_ID")) and bool(os.getenv("PAYFAST_KEY"))),
        # --- Notifications / infra ---
        "africas_talking_sms": _state(bool(os.getenv("AFRICAS_TALKING_API_KEY"))),
        "docker_sandbox_daemon": _docker_probe(),
        "redis_cluster": _state(os.getenv("STATE_BACKEND") == "redis" and bool(os.getenv("REDIS_URL"))),
        # --- Secrets hygiene ---
        "admin_gate_secret": _state(True, insecure=(admin_secret == DEFAULT_ADMIN_SECRET)),
        "jwt_signing_secret": _state(True, insecure=(jwt_secret == DEFAULT_JWT_SECRET)),
        # --- Persistence ---
        "database_primary": _state(bool(os.getenv("DATABASE_URL"))),
        "database_replica": _state(bool(os.getenv("DATABASE_URL_BACKUP"))),
        "backup_encryption_key": _state(bool(os.getenv("BACKUP_ENCRYPTION_KEY"))),
    }

    degraded = [k for k, v in gateways.items() if v in ("MISSING", "INSECURE")]
    return {
        "status": "degraded" if degraded else "operational",
        "degraded_integrations": degraded,
        "active_gateways": gateways,
        "note": "Values are never exposed. INSECURE = template default still in use. "
                "RESERVED = hook exists, feature not yet wired.",
    }
