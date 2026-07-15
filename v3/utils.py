"""Omega AI v3 — Shared Utilities
Terminal colors, formatting helpers, and common utilities.
"""
from __future__ import annotations

import itertools
import json
import sys
import threading
import time
from typing import Any


# ── ANSI Colors ──────────────────────────────────────────────────────
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{Colors.RESET}"


def print_header(text: str, width: int = 60) -> None:
    """Print a formatted section header."""
    print()
    print(colorize("=" * width, Colors.CYAN))
    print(colorize(f"  {text}", Colors.BOLD + Colors.CYAN))
    print(colorize("=" * width, Colors.CYAN))


def print_success(text: str) -> None:
    print(colorize(f"  ✓ {text}", Colors.GREEN))


def print_error(text: str) -> None:
    print(colorize(f"  ✗ {text}", Colors.RED), file=sys.stderr)


def print_warning(text: str) -> None:
    print(colorize(f"  ⚠ {text}", Colors.YELLOW))


def print_info(text: str) -> None:
    print(colorize(f"  ℹ {text}", Colors.BLUE))


# ── Spinner ──────────────────────────────────────────────────────────
class Spinner:
    """Terminal spinner for long-running operations."""

    _frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Processing") -> None:
        self.message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        for frame in itertools.cycle(self._frames):
            if self._stop_event.is_set():
                break
            print(f"\r  {colorize(frame, Colors.CYAN)} {self.message}...", end="", flush=True)
            time.sleep(0.08)
        print("\r" + " " * (len(self.message) + 10) + "\r", end="")

    def stop(self, success: bool = True) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        status = colorize("✓ Done", Colors.GREEN) if success else colorize("✗ Failed", Colors.RED)
        print(f"  {status}")

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop(success=args[0] is None)


# ── Text Utilities ───────────────────────────────────────────────────
def truncate_text(text: str, max_len: int = 500) -> str:
    """Smart text truncation with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def sanitize_input(text: str) -> str:
    """Basic input sanitization."""
    return text.strip().replace("\r", "").replace("\x00", "")


def current_timestamp() -> str:
    """ISO format timestamp."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def safe_json_loads(text: str) -> dict[str, Any]:
    """Safe JSON parsing with fallback to empty dict."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{seconds / 60:.1f}m"


# ── Box Drawing ──────────────────────────────────────────────────────
def draw_box(content: str, title: str = "", width: int = 56) -> str:
    """Draw a Unicode box around content."""
    lines = content.split("\n")
    result = [f"┌{'─' * (width - 2)}┐"]
    if title:
        pad = (width - 2 - len(title)) // 2
        result.append(f"│{' ' * pad}{colorize(title, Colors.BOLD)}{' ' * (width - 2 - pad - len(title))}│")
        result.append(f"├{'─' * (width - 2)}┤")
    for line in lines:
        result.append(f"│ {truncate_text(line, width - 4):<{width - 4}} │")
    result.append(f"└{'─' * (width - 2)}┘")
    return "\n".join(result)


if __name__ == "__main__":
    print_header("Utility Demo")
    print_success("Everything loaded")
    print_info("Testing spinner...")
    with Spinner("Working"):
        time.sleep(1.5)
    print(draw_box("This is a test message\nLine two\nLine three", title="Demo Box"))
