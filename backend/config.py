"""Backend configuration loader."""

import os
from pathlib import Path
from typing import Dict, List

def load_backend_config() -> Dict:
    """Load configuration from environment variables."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass

    return {
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "serper_api_key": os.environ.get("SERPER_API_KEY", ""),
        "model": os.environ.get("MODEL", "gpt-4o-mini"),
        "vision_model": os.environ.get("VISION_MODEL", "gpt-4o"),
        "embedding_model": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        "cors_origins": os.environ.get("CORS_ORIGINS", "*").split(","),
        "max_upload_size": int(os.environ.get("MAX_UPLOAD_SIZE", "10485760")),
        "chroma_persist_dir": os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db"),
    }
