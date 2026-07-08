"""Luqi AI v24 -- Configuration Validator

Validates all environment variables on startup with sensible defaults.
Prevents runtime errors from misconfiguration.

Usage:
    from backend.config_validator import config, ConfigError
    api_key = config.openai.api_key
    if config.whatsapp.enabled:
        ...
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

try:
    from pydantic import Field, ValidationError, field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

logger = logging.getLogger("luqi.config")


# ═══════════════════════════════════════════════════════════════════
# Manual fallback when pydantic-settings is not installed
# ═══════════════════════════════════════════════════════════════════

class _ManualField:
    """Descriptor for manual config fields."""

    def __init__(
        self,
        env_name: str,
        default: Any = None,
        required: bool = False,
        validator: Optional[Any] = None,
        secret: bool = False,
    ) -> None:
        self.env_name = env_name
        self.default = default
        self.required = required
        self.validator = validator
        self.secret = secret
        self.name = ""

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return self
        cache_key = f"_cache_{self.name}"
        if hasattr(obj, cache_key):
            return getattr(obj, cache_key)
        raw = os.getenv(self.env_name, self.default)
        if raw is None and self.required:
            raise ConfigError(f"Missing required env var: {self.env_name}")
        value = self._coerce(raw)
        if self.validator:
            value = self.validator(value)
        setattr(obj, cache_key, value)
        return value

    def _coerce(self, raw: Any) -> Any:
        if raw is None:
            return None
        if isinstance(self.default, bool):
            return str(raw).lower() in ("true", "1", "yes", "on")
        if isinstance(self.default, int):
            return int(raw)
        if isinstance(self.default, float):
            return float(raw)
        if isinstance(self.default, list):
            return [s.strip() for s in str(raw).split(",") if s.strip()]
        return str(raw)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str, var_name: str = "", fix_hint: str = "") -> None:
        super().__init__(message)
        self.var_name = var_name
        self.fix_hint = fix_hint


# ═══════════════════════════════════════════════════════════════════
# Pydantic-based configuration (preferred)
# ═══════════════════════════════════════════════════════════════════

if HAS_PYDANTIC:

    class CoreConfig(BaseSettings):
        """Core application configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        openai_api_key: str = Field(..., description="OpenAI API key", pattern=r"^sk-")
        app_env: Literal["development", "staging", "production"] = Field(default="development")
        debug: bool = Field(default=False)
        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")

        @field_validator("openai_api_key")
        @classmethod
        def validate_openai_key(cls, v: str) -> str:
            if not v or not v.startswith("sk-"):
                raise ValueError("OPENAI_API_KEY must start with 'sk-'")
            return v

    class ServerConfig(BaseSettings):
        """Server configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        host: str = Field(default="0.0.0.0")
        port: int = Field(default=8000, ge=1, le=65535)
        workers: int = Field(default=1, ge=1)
        cors_origins: List[str] = Field(default=["*"])
        allowed_hosts: List[str] = Field(default=["*"])

        @field_validator("cors_origins", "allowed_hosts", mode="before")
        @classmethod
        def parse_list(cls, v: Any) -> List[str]:
            if isinstance(v, str):
                return [s.strip() for s in v.split(",") if s.strip()]
            return v

    class DatabaseConfig(BaseSettings):
        """Database configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        database_url: str = Field(default="sqlite:///./data/luqi.db")
        chroma_path: str = Field(default="./chroma_db")

    class RedisConfig(BaseSettings):
        """Redis configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        redis_url: str = Field(default="")

        @property
        def enabled(self) -> bool:
            return bool(self.redis_url)

    class AIModelConfig(BaseSettings):
        """AI model configuration."""

        model_config = SettingsConfigDict(env_prefix="OMEGA_", case_sensitive=False)

        model: str = Field(default="gpt-4o-mini")
        vision_model: str = Field(default="gpt-4o")
        embed_model: str = Field(default="text-embedding-3-small")
        max_tokens: int = Field(default=4096, ge=256, le=128000)
        temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    class UploadConfig(BaseSettings):
        """File upload configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        upload_dir: str = Field(default="./uploads")
        max_upload_size: int = Field(default=52428800)  # 50MB
        allowed_extensions: List[str] = Field(default=["pdf", "docx", "txt", "png", "jpg", "jpeg"])

        @field_validator("allowed_extensions", mode="before")
        @classmethod
        def parse_extensions(cls, v: Any) -> List[str]:
            if isinstance(v, str):
                return [s.strip().lower() for s in v.split(",") if s.strip()]
            return v

    class ExternalAPIConfig(BaseSettings):
        """External API configuration (all optional)."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        serper_api_key: str = Field(default="")
        stripe_secret_key: str = Field(default="", pattern=r"^(|sk_test_|sk_live_).*$")
        stripe_webhook_secret: str = Field(default="")
        twilio_account_sid: str = Field(default="", pattern=r"^(|AC).*$")
        twilio_auth_token: str = Field(default="")
        twilio_phone_number: str = Field(default="")
        livekit_api_key: str = Field(default="")
        livekit_api_secret: str = Field(default="")
        livekit_url: str = Field(default="")

    class SecurityConfig(BaseSettings):
        """Security configuration."""

        model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

        secret_key: str = Field(default="")
        jwt_algorithm: str = Field(default="HS256")
        jwt_expiry_hours: int = Field(default=24, ge=1)
        rate_limit_general: int = Field(default=100, ge=1)
        rate_limit_auth: int = Field(default=10, ge=1)

    class FeatureFlags(BaseSettings):
        """Feature toggle configuration."""

        model_config = SettingsConfigDict(env_prefix="ENABLE_", case_sensitive=False)

        workspace_collab: bool = Field(default=True)
        netai_training: bool = Field(default=True)
        knowledge_academy: bool = Field(default=True)
        whatsapp_bot: bool = Field(default=True)
        gov_services: bool = Field(default=True)

    class LuqiConfig:
        """Aggregated configuration container."""

        def __init__(self) -> None:
            self.core = CoreConfig()
            self.server = ServerConfig()
            self.database = DatabaseConfig()
            self.redis = RedisConfig()
            self.ai = AIModelConfig()
            self.upload = UploadConfig()
            self.external = ExternalAPIConfig()
            self.security = SecurityConfig()
            self.features = FeatureFlags()
            self._ensure_secret_key()

        def _ensure_secret_key(self) -> None:
            if not self.security.secret_key:
                if self.core.app_env == "production":
                    raise ConfigError(
                        "SECRET_KEY is required in production",
                        var_name="SECRET_KEY",
                        fix_hint="Set a strong SECRET_KEY env var",
                    )
                self.security.secret_key = secrets.token_urlsafe(32)
                logger.warning("Auto-generated SECRET_KEY for development. Set explicitly for consistency.")

        @property
        def is_production(self) -> bool:
            return self.core.app_env == "production"

        @property
        def is_development(self) -> bool:
            return self.core.app_env == "development"

        def health_report(self) -> Dict[str, Any]:
            report: Dict[str, Any] = {
                "status": "ok",
                "environment": self.core.app_env,
                "checks": {},
                "features": {},
                "warnings": [],
            }
            # Core checks
            report["checks"]["openai"] = "ok" if self.core.openai_api_key else "missing"
            report["checks"]["redis"] = "connected" if self.redis.enabled else "not_configured"
            report["checks"]["stripe"] = "configured" if self.external.stripe_secret_key else "not_configured"
            report["checks"]["twilio"] = "configured" if self.external.twilio_account_sid else "not_configured"
            report["checks"]["serper"] = "configured" if self.external.serper_api_key else "not_configured"
            report["checks"]["livekit"] = "configured" if self.external.livekit_api_key else "not_configured"

            # Feature flags
            report["features"] = {
                "workspace_collab": self.features.workspace_collab,
                "netai_training": self.features.netai_training,
                "knowledge_academy": self.features.knowledge_academy,
                "whatsapp_bot": self.features.whatsapp_bot and bool(self.external.twilio_account_sid),
                "gov_services": self.features.gov_services,
            }

            # Warnings
            if self.is_production and self.core.debug:
                report["warnings"].append("DEBUG is enabled in production")
            if not self.redis.enabled:
                report["warnings"].append("Redis not configured - caching and background tasks will use in-memory fallback")

            # Overall status
            if report["checks"]["openai"] == "missing":
                report["status"] = "critical"
            elif report["warnings"]:
                report["status"] = "degraded"

            return report

        def masked_dict(self) -> Dict[str, Any]:
            """Return config with all secrets redacted. Safe for logging."""
            result: Dict[str, Any] = {
                "core": {"app_env": self.core.app_env, "debug": self.core.debug, "log_level": self.core.log_level},
                "server": {"host": self.server.host, "port": self.server.port, "workers": self.server.workers},
                "database": {"database_url": "***REDACTED***", "chroma_path": self.database.chroma_path},
                "redis": {"enabled": self.redis.enabled},
                "ai": {"model": self.ai.model, "vision_model": self.ai.vision_model, "embed_model": self.ai.embed_model},
                "upload": {"upload_dir": self.upload.upload_dir, "max_upload_size": self.upload.max_upload_size},
                "external": {
                    "serper": "configured" if self.external.serper_api_key else "not_configured",
                    "stripe": "configured" if self.external.stripe_secret_key else "not_configured",
                    "twilio": "configured" if self.external.twilio_account_sid else "not_configured",
                    "livekit": "configured" if self.external.livekit_api_key else "not_configured",
                },
                "security": {
                    "jwt_algorithm": self.security.jwt_algorithm,
                    "jwt_expiry_hours": self.security.jwt_expiry_hours,
                    "rate_limit_general": self.security.rate_limit_general,
                },
                "features": self.features.model_dump(),
            }
            return result

        def update(self, group: str, key: str, value: Any) -> None:
            """Update a configuration value at runtime."""
            target = getattr(self, group, None)
            if target is None:
                raise ConfigError(f"Unknown config group: {group}")
            if not hasattr(target, key):
                raise ConfigError(f"Unknown config key: {group}.{key}")
            setattr(target, key, value)
            logger.info("Runtime config update: %s.%s = %s", group, key, value)

else:
    # Manual fallback without pydantic
    class LuqiConfig:
        """Manual configuration container (fallback when pydantic is not installed)."""

        openai_api_key = _ManualField("OPENAI_API_KEY", required=True)
        app_env = _ManualField("APP_ENV", default="development")
        debug = _ManualField("DEBUG", default=False)
        log_level = _ManualField("LOG_LEVEL", default="INFO")
        host = _ManualField("HOST", default="0.0.0.0")
        port = _ManualField("PORT", default=8000)
        database_url = _ManualField("DATABASE_URL", default="sqlite:///./data/luqi.db")
        chroma_path = _ManualField("CHROMA_PATH", default="./chroma_db")
        redis_url = _ManualField("REDIS_URL", default="")
        omega_model = _ManualField("OMEGA_MODEL", default="gpt-4o-mini")
        upload_dir = _ManualField("UPLOAD_DIR", default="./uploads")
        max_upload_size = _ManualField("MAX_UPLOAD_SIZE", default=52428800)
        secret_key = _ManualField("SECRET_KEY", default="")
        cors_origins = _ManualField("CORS_ORIGINS", default=["*"])
        allowed_hosts = _ManualField("ALLOWED_HOSTS", default=["*"])

        @property
        def is_production(self) -> bool:
            val = os.getenv("APP_ENV", "development")
            return val == "production"

        @property
        def is_development(self) -> bool:
            val = os.getenv("APP_ENV", "development")
            return val == "development"

        def health_report(self) -> Dict[str, Any]:
            return {"status": "ok", "note": "Install pydantic-settings for full validation"}

        def masked_dict(self) -> Dict[str, Any]:
            return {"note": "Install pydantic-settings for full config"}

        def update(self, group: str, key: str, value: Any) -> None:
            raise NotImplementedError("Install pydantic-settings for runtime updates")


# ═══════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def _get_config() -> LuqiConfig:
    return LuqiConfig()


config: LuqiConfig = _get_config()


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    try:
        cfg = config
        print("=== Luqi AI Configuration ===")
        print(f"Environment: {cfg.core.app_env if HAS_PYDANTIC else cfg.app_env}")
        print(f"Debug: {cfg.core.debug if HAS_PYDANTIC else cfg.debug}")
        print(f"Production: {cfg.is_production}")
        print("\n=== Health Report ===")
        print(json.dumps(cfg.health_report(), indent=2))
        print("\n=== Masked Config (safe for logs) ===")
        print(json.dumps(cfg.masked_dict(), indent=2))
    except ConfigError as e:
        print(f"Configuration Error: {e}")
        if e.fix_hint:
            print(f"Fix: {e.fix_hint}")
        sys.exit(1)
