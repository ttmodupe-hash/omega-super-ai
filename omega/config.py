"""Configuration management for Omega Super AI."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]


def load_config() -> dict:
    """Load API keys and settings from .env file.

    Searches for a ``.env`` file in the following locations (first match wins):

    1. ``project/.env`` (sibling of the ``omega/`` package)
    2. Current working directory
    3. ``~/.omega/.env`` (user home directory)

    Returns:
        Dictionary containing all configuration keys:

        - ``openai_api_key`` (str): OpenAI API key
        - ``serper_api_key`` (str): Serper.dev API key
        - ``db_path`` (str): Path to SQLite database file
        - ``cache_ttl_hours`` (int): Cache time-to-live in hours
        - ``max_search_results`` (int): Maximum web search results per query
        - ``max_workers`` (int): ThreadPoolExecutor max worker threads
        - ``session_timeout`` (int): Session idle timeout in seconds
        - ``model`` (str): Default OpenAI model identifier
        - ``debug`` (bool): Debug mode flag

    Example:
        >>> config = load_config()
        >>> print(config["model"])
        gpt-4o-mini
    """
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
        Path.home() / ".omega" / ".env",
    ]

    if load_dotenv is not None:
        for p in env_paths:
            if p.exists():
                load_dotenv(p)
                break

    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "serper_api_key": os.getenv("SERPER_API_KEY", ""),
        "db_path": os.getenv("OMEGA_DB_PATH", "omega_memory.db"),
        "cache_ttl_hours": int(os.getenv("OMEGA_CACHE_TTL", "24")),
        "max_search_results": int(os.getenv("OMEGA_MAX_RESULTS", "15")),
        "max_workers": int(os.getenv("OMEGA_MAX_WORKERS", "5")),
        "session_timeout": int(os.getenv("OMEGA_SESSION_TIMEOUT", "3600")),
        "model": os.getenv("OMEGA_MODEL", "gpt-4o-mini"),
        "debug": os.getenv("OMEGA_DEBUG", "false").lower() == "true",
    }


def validate_config(config: dict) -> list[str]:
    """Validate configuration dictionary for required values.

    Args:
        config: Configuration dictionary from :func:`load_config`.

    Returns:
        List of human-readable error messages. An empty list means the
        configuration is valid.

    Example:
        >>> cfg = load_config()
        >>> errors = validate_config(cfg)
        >>> if errors:
        ...     for e in errors:
        ...         print(f"Config error: {e}")
    """
    errors: list[str] = []

    if not config.get("openai_api_key"):
        errors.append("OPENAI_API_KEY is missing. Set it in your .env file.")

    if not config.get("serper_api_key"):
        errors.append("SERPER_API_KEY is missing. Set it in your .env file.")

    db_path = config.get("db_path", "")
    if not db_path:
        errors.append("OMEGA_DB_PATH cannot be empty.")

    if config.get("max_workers", 1) < 1:
        errors.append("OMEGA_MAX_WORKERS must be >= 1.")

    if config.get("cache_ttl_hours", 1) < 1:
        errors.append("OMEGA_CACHE_TTL must be >= 1 hour.")

    return errors
