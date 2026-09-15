"""Omega AI v3 — Terminal Utilities
ANSI colors, text formatting, spinners, and CLI helpers.
"""
from __future__ import annotations

import itertools
import re
import shutil
import sys
import threading
import time
from typing import Any


class Colors:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Colors.RESET}"


def print_success(msg: str) -> None:
    print(colorize(f"✓ {msg}", Colors.GREEN))


def print_error(msg: str) -> None:
    print(colorize(f"✗ {msg}", Colors.RED), file=sys.stderr)


def print_warning(msg: str) -> None:
    print(colorize(f"⚠ {msg}", Colors.YELLOW))


def print_info(msg: str) -> None:
    print(colorize(f"ℹ {msg}", Colors.CYAN))


def print_header(msg: str) -> None:
    term_width = shutil.get_terminal_size().columns
    line = "═" * min(len(msg) + 4, term_width)
    print(colorize(line, Colors.CYAN))
    print(colorize(f"  {msg}", Colors.BOLD + Colors.CYAN))
    print(colorize(line, Colors.CYAN))


def draw_box(title: str, lines: list[str], width: int = 60) -> str:
    """Draw an ASCII box with a title."""
    inner = width - 2
    result = [f"┌{'─' * inner}┐"]
    if title:
        t = f" {title} ".center(inner, "─")
        result.append(f"├{t}┤")
    for line in lines:
        result.append(f"│ {line:<{inner - 1}}│")
    result.append(f"└{'─' * inner}┘")
    return "\n".join(result)


def truncate_text(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rsplit(" ", 1)[0] + "..."


def sanitize_input(text: str) -> str:
    """Sanitize user input: strip dangerous characters."""
    if not text:
        return ""
    text = text.strip()
    # Remove control chars except newline and tab
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or (ord(ch) >= 32 and ord(ch) < 127))
    return text


class Spinner:
    """Threaded CLI spinner for long-running operations."""

    def __init__(self, message: str = "Loading") -> None:
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message: str = "") -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        if final_message:
            print(f"\r✓ {final_message}", flush=True)
        else:
            print(f"\r{' ' * (len(self.message) + 10)}", end="\r", flush=True)

    def _spin(self) -> None:
        for char in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if self._stop_event.is_set():
                break
            print(f"\r{Colors.CYAN}{char}{Colors.RESET} {self.message}...", end="", flush=True)
            time.sleep(0.08)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()