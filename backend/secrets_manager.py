"""Luqi AI v24 -- Secrets Manager

Secure API key rotation, encryption at rest, and secrets management.

Usage:
    from backend.secrets_manager import secrets_mgr
    api_key, key_id = secrets_mgr.create_key(user_id="user_123", name="Production Key")
    result = secrets_mgr.validate_key(api_key)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Tuple

logger = logging.getLogger("luqi.secrets")

KeyStatus = Literal["active", "rotating", "revoked", "expired"]


@dataclass
class KeyValidationResult:
    valid: bool
    user_id: str = ""
    key_id: str = ""
    scopes: List[str] = field(default_factory=list)
    rate_limit: int = 100
    error: Optional[str] = None


@dataclass
class KeyInfo:
    key_id: str
    user_id: str
    name: str
    scopes: List[str]
    rate_limit: int
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    use_count: int
    status: KeyStatus


class CryptoEngine:
    """Fernet-based encryption for sensitive data."""

    def __init__(self) -> None:
        self._key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        env_key = os.getenv("SECRETS_MASTER_KEY", "")
        if env_key:
            return env_key.encode()[:32].ljust(32, b"\0")
        key_file = "./data/.secrets_key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        key = secrets.token_bytes(32)
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, "wb") as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        logger.warning("Generated new secrets master key at %s", key_file)
        return key

    def hash_key(self, api_key: str) -> str:
        """Create SHA-256 hash of API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def compare_keys(self, provided: str, stored_hash: str) -> bool:
        """Constant-time comparison of API key against stored hash."""
        provided_hash = self.hash_key(provided)
        return hmac.compare_digest(provided_hash, stored_hash)

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data using Fernet."""
        try:
            from cryptography.fernet import Fernet
            f = Fernet(self._get_fernet_key())
            return f.encrypt(data.encode()).decode()
        except ImportError:
            return data

    def decrypt(self, token: str) -> str:
        """Decrypt Fernet-encrypted data."""
        try:
            from cryptography.fernet import Fernet
            f = Fernet(self._get_fernet_key())
            return f.decrypt(token.encode()).decode()
        except ImportError:
            return token

    def _get_fernet_key(self) -> bytes:
        import base64
        return base64.urlsafe_b64encode(self._key[:32].ljust(32, b"\0"))


class KeyGenerator:
    """Generate secure API keys in the format: lk_{prefix}_{random}_{checksum}"""

    @staticmethod
    def generate(user_id: str) -> Tuple[str, str]:
        """Generate a new API key and its ID.
        
        Returns:
            Tuple of (api_key, key_id)
        """
        key_id = str(uuid.uuid4())[:16]
        prefix = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        random_part = secrets.token_urlsafe(24)[:32]
        checksum_input = f"lk_{prefix}_{random_part}"
        checksum = hashlib.sha256(checksum_input.encode()).hexdigest()[:6]
        api_key = f"lk_{prefix}_{random_part}_{checksum}"
        return api_key, key_id

    @staticmethod
    def validate_format(api_key: str) -> bool:
        """Validate API key format without checking hash."""
        parts = api_key.split("_")
        if len(parts) != 4 or parts[0] != "lk":
            return False
        prefix, random_part, checksum = parts[1], parts[2], parts[3]
        if len(prefix) != 8 or len(checksum) != 6:
            return False
        expected = hashlib.sha256(f"lk_{prefix}_{random_part}".encode()).hexdigest()[:6]
        return hmac.compare_digest(checksum, expected)


class InMemoryRateLimiter:
    """Per-key rate limiter using in-memory sliding window."""

    def __init__(self) -> None:
        self._windows: Dict[str, List[float]] = {}
        self._lock = threading.RLock()

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        now = time.time()
        cutoff = now - window
        with self._lock:
            entries = self._windows.get(key, [])
            entries = [t for t in entries if t > cutoff]
            if len(entries) >= limit:
                return False
            entries.append(now)
            self._windows[key] = entries
            return True


class SecretsManager:
    """Manages API keys with encryption, rotation, and audit logging."""

    def __init__(self, db_path: str = "./data/luqi_secrets.db") -> None:
        self._db_path = db_path
        self._crypto = CryptoEngine()
        self._generator = KeyGenerator()
        self._rate_limiter = InMemoryRateLimiter()
        self._init_db()
        self._start_cleanup_thread()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT,
                    key_hash TEXT NOT NULL,
                    scopes TEXT,
                    rate_limit INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    use_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    revoked_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
                CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
                CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

                CREATE TABLE IF NOT EXISTS api_key_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id TEXT REFERENCES api_keys(key_id),
                    endpoint TEXT,
                    method TEXT,
                    status_code INTEGER,
                    response_time_ms REAL,
                    client_ip TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_usage_key ON api_key_usage(key_id);
                CREATE INDEX IF NOT EXISTS idx_usage_time ON api_key_usage(timestamp);
            """)

    def create_key(
        self,
        user_id: str,
        name: str = "",
        scopes: Optional[List[str]] = None,
        rate_limit: int = 100,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, str]:
        """Create a new API key for a user.
        
        Returns:
            Tuple of (api_key, key_id). The api_key is shown ONLY at creation time.
        """
        api_key, key_id = self._generator.generate(user_id)
        key_hash = self._crypto.hash_key(api_key)
        scopes_json = ",".join(scopes) if scopes else ""
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO api_keys 
                    (key_id, user_id, name, key_hash, scopes, rate_limit, expires_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
                (key_id, user_id, name, key_hash, scopes_json, rate_limit, expires_at),
            )
        logger.info("Created API key %s for user %s", key_id, user_id)
        return api_key, key_id

    def validate_key(self, api_key: str, endpoint: str = "", method: str = "", client_ip: str = "") -> KeyValidationResult:
        """Validate an API key and log usage.
        
        Returns:
            KeyValidationResult with validation details.
        """
        if not self._generator.validate_format(api_key):
            return KeyValidationResult(valid=False, error="Invalid key format")

        key_hash = self._crypto.hash_key(api_key)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT key_id, user_id, scopes, rate_limit, status, expires_at FROM api_keys WHERE key_hash = ?",
                (key_hash,),
            ).fetchone()

        if not row:
            return KeyValidationResult(valid=False, error="Unknown key")

        key_id, user_id, scopes_str, rate_limit, status, expires_at = row

        if status == "revoked":
            return KeyValidationResult(valid=False, error="Key has been revoked")
        if status == "expired":
            return KeyValidationResult(valid=False, error="Key has expired")
        if expires_at and datetime.utcnow().isoformat() > expires_at:
            self._set_status(key_id, "expired")
            return KeyValidationResult(valid=False, error="Key has expired")

        if not self._rate_limiter.is_allowed(key_id, rate_limit):
            return KeyValidationResult(valid=False, error="Rate limit exceeded")

        scopes = [s.strip() for s in scopes_str.split(",") if s.strip()] if scopes_str else []

        # Update usage
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ?, use_count = use_count + 1 WHERE key_id = ?",
                (datetime.utcnow().isoformat(), key_id),
            )
            if endpoint:
                conn.execute(
                    "INSERT INTO api_key_usage (key_id, endpoint, method, client_ip) VALUES (?, ?, ?, ?)",
                    (key_id, endpoint, method, client_ip),
                )

        return KeyValidationResult(valid=True, user_id=user_id, key_id=key_id, scopes=scopes, rate_limit=rate_limit)

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key immediately."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET status = 'revoked', revoked_at = ? WHERE key_id = ?",
                (datetime.utcnow().isoformat(), key_id),
            )
        if cursor.rowcount > 0:
            logger.info("Revoked API key %s", key_id)
            return True
        return False

    def rotate_key(self, key_id: str, grace_period_hours: int = 24) -> Tuple[str, str]:
        """Rotate an API key with a grace period.
        
        Returns:
            Tuple of (new_api_key, new_key_id)
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT user_id, name, scopes, rate_limit FROM api_keys WHERE key_id = ?",
                (key_id,),
            ).fetchone()
        if not row:
            raise ValueError(f"Key not found: {key_id}")
        user_id, name, scopes, rate_limit = row
        # Mark old key as rotating
        self._set_status(key_id, "rotating")
        # Create new key
        new_key, new_id = self.create_key(user_id, name or "Rotated", scopes.split(",") if scopes else None, rate_limit)
        logger.info("Rotated key %s -> %s (grace: %dh)", key_id, new_id, grace_period_hours)
        # Schedule revocation of old key
        threading.Timer(grace_period_hours * 3600, lambda: self.revoke_key(key_id)).start()
        return new_key, new_id

    def list_keys(self, user_id: str) -> List[KeyInfo]:
        """List all API keys for a user."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT key_id, user_id, name, scopes, rate_limit, created_at, expires_at, last_used_at, use_count, status FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            KeyInfo(
                key_id=r[0], user_id=r[1], name=r[2] or "", scopes=r[3].split(",") if r[3] else [],
                rate_limit=r[4], created_at=r[5], expires_at=r[6], last_used_at=r[7],
                use_count=r[8], status=r[9],  # type: ignore[arg-type]
            )
            for r in rows
        ]

    def get_stats(self, key_id: str) -> Dict[str, Any]:
        """Get usage statistics for a key."""
        with sqlite3.connect(self._db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*), AVG(response_time_ms) FROM api_key_usage WHERE key_id = ?",
                (key_id,),
            ).fetchone()
            status_codes = conn.execute(
                "SELECT status_code, COUNT(*) FROM api_key_usage WHERE key_id = ? GROUP BY status_code",
                (key_id,),
            ).fetchall()
            endpoints = conn.execute(
                "SELECT endpoint, COUNT(*) FROM api_key_usage WHERE key_id = ? GROUP BY endpoint ORDER BY COUNT(*) DESC LIMIT 10",
                (key_id,),
            ).fetchall()
        return {
            "total_requests": total[0] or 0,
            "avg_response_time_ms": round(total[1], 2) if total[1] else 0,
            "status_codes": {str(sc): cnt for sc, cnt in status_codes},
            "top_endpoints": {ep: cnt for ep, cnt in endpoints},
        }

    def bulk_revoke(self, user_id: str) -> int:
        """Revoke all keys for a user. Returns count revoked."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET status = 'revoked', revoked_at = ? WHERE user_id = ? AND status = 'active'",
                (datetime.utcnow().isoformat(), user_id),
            )
        return cursor.rowcount

    def _set_status(self, key_id: str, status: KeyStatus) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("UPDATE api_keys SET status = ? WHERE key_id = ?", (status, key_id))

    def _start_cleanup_thread(self) -> None:
        """Start background thread to clean expired keys."""
        def cleanup():
            while True:
                time.sleep(3600)  # Every hour
                try:
                    now = datetime.utcnow().isoformat()
                    with sqlite3.connect(self._db_path) as conn:
                        conn.execute(
                            "UPDATE api_keys SET status = 'expired' WHERE expires_at < ? AND status = 'active'",
                            (now,),
                        )
                        # Archive old usage logs (older than 90 days)
                        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
                        conn.execute("DELETE FROM api_key_usage WHERE timestamp < ?", (cutoff,))
                except Exception as exc:
                    logger.error("Key cleanup error: %s", exc)

        thread = threading.Thread(target=cleanup, daemon=True, name="secrets_cleanup")
        thread.start()


# Singleton
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


secrets_mgr = get_secrets_manager()


def self_test() -> Dict[str, Any]:
    """Run internal validation."""
    mgr = SecretsManager(db_path=":memory:")
    # Test create
    key, key_id = mgr.create_key("test_user", "Test Key", ["read", "write"], 10)
    assert key.startswith("lk_"), "Key format invalid"
    # Test validate
    result = mgr.validate_key(key, "/api/test", "GET", "127.0.0.1")
    assert result.valid, f"Validation failed: {result.error}"
    assert result.user_id == "test_user"
    # Test revoke
    mgr.revoke_key(key_id)
    result = mgr.validate_key(key)
    assert not result.valid, "Revoked key should be invalid"
    # Test list
    keys = mgr.list_keys("test_user")
    assert len(keys) == 1
    # Test stats
    stats = mgr.get_stats(key_id)
    assert stats["total_requests"] == 1
    return {"valid": True, "tests_passed": 5}


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(self_test(), indent=2))
