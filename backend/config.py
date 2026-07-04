"""Backend configuration management.

Handles loading of environment variables from .env files and provides
type-safe access to all configuration settings used across the Luqi AI system.

Typical usage:
    from backend.config import load_backend_config
    config = load_backend_config()
    api_key = config["openai_api_key"]
"""

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv


def load_backend_config() -> Dict[str, object]:
    """Load configuration from .env file.

    Searches for .env files in the project root and current working directory.
    Loads the first one found. Falls back to default values for all settings.

    Returns:
        Dictionary containing all configuration values with typed values.
        Keys include: openai_api_key, serper_api_key, model, vision_model,
        embedding_model, db_path, chroma_path, upload_dir, max_upload_size,
        debug, cors_origins.
    """
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for p in env_paths:
        if p.exists():
            load_dotenv(p)
            break

    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "serper_api_key": os.getenv("SERPER_API_KEY", ""),
        "model": os.getenv("OMEGA_MODEL", "gpt-4o-mini"),
        "vision_model": os.getenv("OMEGA_VISION_MODEL", "gpt-4o"),
        "embedding_model": os.getenv("OMEGA_EMBED_MODEL", "text-embedding-3-small"),
        "db_path": os.getenv("OMEGA_DB_PATH", "luqi_memory.db"),
        "chroma_path": os.getenv("CHROMA_PATH", "./chroma_db"),
        "upload_dir": os.getenv("UPLOAD_DIR", "./uploads"),
        "max_upload_size": int(os.getenv("MAX_UPLOAD_SIZE", "10485760")),  # 10MB
        "debug": os.getenv("OMEGA_DEBUG", "false").lower() == "true",
        "cors_origins": os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:8080,http://luqi-ai.com,https://luqi-ai.com",
        ).split(","),
    }
