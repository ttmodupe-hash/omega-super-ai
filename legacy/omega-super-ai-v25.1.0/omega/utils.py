"""Terminal utilities for Omega Super AI.

Provides rich formatting helpers built on the ``rich`` library: headers,
status messages, spinners, text truncation, source formatting, boxed
output, and interactive prompts.
"""

import time
from typing import Any

from rich import box
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

# ---------------------------------------------------------------------------
# Global console instance
# ---------------------------------------------------------------------------

_console: Console | None = None


def get_console() -> Console:
    """Return the shared :class:`rich.console.Console` instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


# ---------------------------------------------------------------------------
# Colours / styles
# ---------------------------------------------------------------------------

_COLOR_MAP: dict[str, str] = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


# ---------------------------------------------------------------------------
# Headers & sections
# ---------------------------------------------------------------------------


def print_header(title: str) -> None:
    """Print a big bold coloured header with ``═══`` borders.

    Args:
        title: Text to display inside the header.

    Example::

        >>> print_header("Omega Super AI v10")
        ╔══════════════════════════════╗
        ║   Omega Super AI v10       ║
        ╚══════════════════════════════╝
    """
    console = get_console()
    text = Text(title, style="bold cyan", justify="center")
    panel = Panel(
        Align.center(text),
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 4),
    )
    console.print(panel)


def print_section(title: str) -> None:
    """Print a section divider with ``───`` borders.

    Args:
        title: Section title to display.

    Example::

        >>> print_section("Research Results")
        ──── Research Results ────
    """
    console = get_console()
    text = Text(f" {title} ", style="bold yellow")
    console.print()
    console.print(Text("─" * 4, style="dim yellow") + text + Text("─" * 40, style="dim yellow"))
    console.print()


# ---------------------------------------------------------------------------
# ANSI colour wrapper
# ---------------------------------------------------------------------------


def colorize(text: str, color: str) -> str:
    """Wrap *text* in ANSI colour codes.

    Args:
        text: The string to colour.
        color: One of ``red``, ``green``, ``yellow``, ``blue``,
            ``magenta``, ``cyan``, ``white``, ``bold``, ``dim``.

    Returns:
        ANSI-coloured string (resets automatically at end).
    """
    code = _COLOR_MAP.get(color.lower(), "")
    reset = _COLOR_MAP["reset"]
    return f"{code}{text}{reset}"


# ---------------------------------------------------------------------------
# Loading spinner
# ---------------------------------------------------------------------------


def loading_animation(message: str, duration: float = 2.0) -> None:
    """Display a spinner animation for *duration* seconds.

    Args:
        message: Text shown next to the spinner.
        duration: How many seconds to keep the spinner alive.

    Note:
        This blocks the thread.  For non-blocking usage, use
        ``rich.live.Live`` directly in an async context.
    """
    console = get_console()
    spinner = Spinner("dots", text=Text(message, style="italic cyan"))

    with Live(spinner, console=console, refresh_per_second=12, transient=True):
        time.sleep(duration)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def truncate_text(text: str, max_chars: int = 500) -> str:
    """Truncate *text* intelligently, preserving word boundaries.

    Args:
        text: Input string.
        max_chars: Maximum length before truncation.

    Returns:
        Truncated string with an ellipsis appended when cut.
    """
    if len(text) <= max_chars:
        return text
    # Try to break at the last space before the limit
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.7:
        truncated = truncated[:last_space]
    return truncated.rstrip() + " …"


def format_sources(sources: list[dict[str, Any]]) -> str:
    """Format a list of source dicts for terminal display.

    Each source dict should have at least a ``title`` and ``url`` key.
    Additional keys (``source``, ``date``) are rendered when present.

    Args:
        sources: List of source metadata dictionaries.

    Returns:
        Multi-line formatted string ready for printing.
    """
    if not sources:
        return colorize("  (no sources)", "dim")

    lines: list[str] = []
    for idx, src in enumerate(sources, start=1):
        title = src.get("title", "Untitled")
        url = src.get("url", "")
        source_name = src.get("source", "")
        date = src.get("date", "")

        meta_parts = [p for p in (source_name, date) if p]
        meta = f"  [{', '.join(meta_parts)}]" if meta_parts else ""

        lines.append(f"  {idx}. {colorize(title, 'cyan')}{colorize(meta, 'dim')}")
        if url:
            lines.append(f"     {colorize(url, 'blue')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Boxed output
# ---------------------------------------------------------------------------


def box_text(text: str, title: str | None = None) -> None:
    """Draw a rounded border around *text* and print it.

    Args:
        text: Body content.
        title: Optional panel title displayed at the top.
    """
    console = get_console()
    panel = Panel(
        text,
        title=Text(title, style="bold magenta") if title else None,
        title_align="left",
        box=box.ROUNDED,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Status messages
# ---------------------------------------------------------------------------


def print_success(msg: str) -> None:
    """Print a green check-marked success message."""
    get_console().print(f"[bold green]✓[/bold green] {msg}")


def print_error(msg: str) -> None:
    """Print a red error message."""
    get_console().print(f"[bold red]✗[/bold red] {msg}")


def print_warning(msg: str) -> None:
    """Print a yellow warning message."""
    get_console().print(f"[bold yellow]⚠[/bold yellow] {msg}")


def print_info(msg: str) -> None:
    """Print a cyan informational message."""
    get_console().print(f"[bold cyan]ℹ[/bold cyan] {msg}")


# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------


def confirm(prompt: str) -> bool:
    """Ask the user a yes/no question.

    Args:
        prompt: Question text (``" (y/n)"`` is appended automatically).

    Returns:
        ``True`` if the user answered ``y`` or ``yes`` (case-insensitive),
        ``False`` otherwise.
    """
    console = get_console()
    full_prompt = f"{prompt} [bold](y/n)[/bold]: "
    answer = console.input(full_prompt).strip().lower()
    return answer in ("y", "yes")
