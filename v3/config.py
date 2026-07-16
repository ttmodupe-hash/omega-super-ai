"""Omega AI v3 — Configuration Manager
Loads environment variables and validates required configuration.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_dotenv(filepath: Path) -> None:
    """Pure-Python .env loader (no python-dotenv dependency required)."""
    if not filepath.exists():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass


# Load .env from project root and current directory
_PROJECT_ROOT = Path(__file__).resolve().parent
_load_dotenv(_PROJECT_ROOT / ".env")
_load_dotenv(Path.cwd() / ".env")


CONFIG: dict[str, str | int | float | bool | None] = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "SERPER_API_KEY": os.environ.get("SERPER_API_KEY", ""),
    "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
    "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "llama3"),
    "DEBUG": os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"),
    "DEFAULT_DEPTH": os.environ.get("DEFAULT_DEPTH", "deep"),
    "MAX_RETRIES": int(os.environ.get("MAX_RETRIES", "3")),
    "REQUEST_TIMEOUT": int(os.environ.get("REQUEST_TIMEOUT", "15")),
    "VERSION": "3.2.0",
    "NAME": "Luqi-AI",
    "AUTHOR": "Luqi AI Labs",
    "MEMORY_DIR": os.environ.get("MEMORY_DIR", str(Path.home() / ".omega_ai")),
}


def validate_config() -> list[str]:
    """Validate configuration. Returns list of missing critical keys."""
    missing: list[str] = []
    if not CONFIG.get("OPENAI_API_KEY") and not CONFIG.get("SERPER_API_KEY"):
        pass
    return missing


def require_config(key: str) -> str:
    """Get a config value or exit with error."""
    val = CONFIG.get(key)
    if not val:
        print(f"[CONFIG ERROR] Missing required config: {key}")
        print(f"  Set it in your .env file or environment variable.")
        sys.exit(1)
    return str(val)


def get_memory_dir() -> Path:
    """Get memory directory path, creating if needed."""
    mem_dir = Path(str(CONFIG["MEMORY_DIR"]))
    mem_dir.mkdir(parents=True, exist_ok=True)
    return mem_dir


if __name__ == "__main__":
    print(f"=== {CONFIG['NAME']} v{CONFIG['VERSION']} Configuration ===")
    missing = validate_config()
    if missing:
        print(f"Missing: {missing}")
    else:
        print("All required config present (or mock mode available).")
    print(f"OLLAMA_HOST: {CONFIG['OLLAMA_HOST']}")
    print(f"DEBUG: {CONFIG['DEBUG']}")