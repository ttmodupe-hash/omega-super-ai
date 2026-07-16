"""Omega AI v3 — Structured Logging
Replaces ad-hoc print statements with configurable logging.
Console output is preserved via a custom handler with ANSI colors.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from utils import Colors, colorize


class ColoredFormatter(logging.Formatter):
    """ANSI-colored log formatter for terminal output."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        record.levelname = colorize(record.levelname, color)
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
    console: bool = True,
) -> logging.Logger:
    """Configure structured logging for Luqi-AI."""
    logger = logging.getLogger("luqi")
    logger.setLevel(level)
    logger.handlers = []

    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        fmt = ColoredFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        plain_fmt = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(plain_fmt)
        logger.addHandler(file_handler)

    return logger


_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def debug(msg: str, *args: Any, **kwargs: Any) -> None:
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args: Any, **kwargs: Any) -> None:
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args: Any, **kwargs: Any) -> None:
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args: Any, **kwargs: Any) -> None:
    get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args: Any, **kwargs: Any) -> None:
    get_logger().critical(msg, *args, **kwargs)