# LUQI-AI API Integration Map (verified against code)

Every token's actual wiring. Corrects the pasted map: kimi_k3.py and
sandbox_recycler.py never existed, and Hume EVI is RESERVED (not yet built).

| Env key | Wired into | Status |
|---|---|---|
| KIMI_API_KEY | core/kimi_client.py -> all 9 engines (gateway, plugins, scan, dev, self-heal, pedagogy, sovereign, universal, integrity) | ACTIVE |
| XI_API_KEY | core/voice_service.py + core/voice_api.py (/v1/voice/speak) | ACTIVE |
| PAYSTACK_SECRET_KEY | core/payment_hub.py (verify) + core/webhooks.py (HMAC) | ACTIVE |
| MPESA_CONSUMER_KEY/SECRET | core/payment_routers.py (KEN/TZA/UGA route) | stub->live via env |
| FLUTTERWAVE_SECRET_KEY | core/payment_routers.py (default route) | stub->live via env |
| PAYFAST_MERCHANT_ID/KEY | core/payment_routers.py (ZAF/NAM/BWA route) | stub->live via env |
| AFRICAS_TALKING_USERNAME/API_KEY | core/notifications.py (gate-lock SMS) | ACTIVE |
| HUME_API_KEY | (no module) | RESERVED - emotional tracking not yet built |
| DOCKER_HOST / socket | core/docker_sandbox.py, sandbox_reaper.py, dev_agent compile | probed live |
| REDIS_URL (+STATE_BACKEND=redis) | core/state_store.py, core/auth.py revocation | optional |
| DATABASE_URL | models, alembic, wallet, RLS | ACTIVE |
| DATABASE_URL_BACKUP | core/db_replication.py (failover/failback) | ACTIVE |
| BACKUP_ENCRYPTION_KEY | core/db_backup.py (AES-256-GCM) | required for backups |
| JWT_SECRET_SIGNING_KEY | core/auth.py (fail-closed) | required in prod |
| LUQI_ADMIN_SECRET | core/admin_auth.py (30% gate) | required in prod |

Live board: GET /v1/system/token-status (admin-gated).
