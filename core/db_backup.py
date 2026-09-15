"""
OMEGA-LUQI Sovereign Encrypted Backup Pipeline

AES-256-GCM encrypted pg_dump archives. Admin-gated (backups contain ALL
student data - not a premium-user feature).

FIXED from the pasted version (all four were critical):
  1. Ephemeral key: Fernet.generate_key() as default meant the key changed
     every process start - every backup became undecryptable after restart.
     Now BACKUP_ENCRYPTION_KEY (base64 of 32 bytes) is REQUIRED; fail-closed.
  2. Hardcoded DB password in source + process args - credentials now come
     only from DATABASE_URL and travel via environment, never argv.
  3. env={"PGPASSWORD": ...} REPLACED the whole environment: pg_dump lost
     PATH and could not even be found. Environment is merged now.
  4. Fernet is AES-128-CBC+HMAC, NOT AES-256-GCM - the label was false.
     This engine uses real AES-256-GCM via cryptography.hazmat.
"""
import base64
import logging
import os
import subprocess
import time
from typing import Any, Dict
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

from .admin_auth import verify_admin

backup_router = APIRouter(prefix="/v1/backup", tags=["System Administration"])
logger = logging.getLogger("LuqiBackupKernel")

BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/backups/luqi-ai")
ALGO_LABEL = "AES-256-GCM"


def _load_key() -> bytes:
    """32-byte AES-256 key from BACKUP_ENCRYPTION_KEY (base64). Fail-closed."""
    raw = os.getenv("BACKUP_ENCRYPTION_KEY")
    if not raw:
        raise RuntimeError(
            "BACKUP_ENCRYPTION_KEY is required for backups - set it to the "
            "base64 encoding of 32 random bytes. Backups without a stable key "
            "are undecryptable after restart, so none are performed."
        )
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes.")
    return key


def _pg_env_and_args(output_file: str):
    """Parse DATABASE_URL; return (env, args) with the password in env ONLY -
    never in argv (visible via ps) and never in source."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL required for backups.")
    p = urlparse(url)
    env = dict(os.environ)  # MERGE - do not replace (the pasted bug)
    if p.password:
        env["PGPASSWORD"] = p.password
    dbname = (p.path or "/").lstrip("/")
    args = ["pg_dump", "-h", p.hostname or "localhost", "-p", str(p.port or 5432),
            "-U", p.username or "postgres", "-d", dbname or "postgres",
            "--format=custom", f"--file={output_file}"]
    return env, args


def encrypt_bytes(plain: bytes, key: bytes) -> bytes:
    """AES-256-GCM; nonce (12B) prepended to ciphertext for storage."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plain, None)


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def execute_encrypted_dump(base_path: str) -> Dict[str, Any]:
    """pg_dump -> encrypt -> purge raw temp. Raw file removed in finally."""
    key = _load_key()
    raw_path = f"{base_path}.raw"
    enc_path = f"{base_path}.enc"
    try:
        env, args = _pg_env_and_args(raw_path)
        subprocess.run(args, env=env, check=True, capture_output=True)
        with open(raw_path, "rb") as f:
            encrypted = encrypt_bytes(f.read(), key)
        with open(enc_path, "wb") as f:
            f.write(encrypted)
        return {
            "archive_path": enc_path,
            "encryption": ALGO_LABEL,
            "size_bytes": os.path.getsize(enc_path),
        }
    except subprocess.CalledProcessError as e:
        logger.error("pg_dump failed: %s", e.stderr.decode(errors="replace")[:500])
        raise RuntimeError(f"pg_dump exit {e.returncode} - see server log")
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)  # never leave plaintext on disk


@backup_router.post("/trigger-backup")
async def trigger_sovereign_backup(is_authenticated: bool = Depends(verify_admin)):
    """Admin-only encrypted backup. Fail-closed without key or DATABASE_URL."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        result = execute_encrypted_dump(os.path.join(BACKUP_DIR, f"luqi_snapshot_{int(time.time())}"))
        return {"status": "success", "timestamp": int(time.time()), **result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
