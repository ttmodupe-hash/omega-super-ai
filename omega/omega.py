#!/usr/bin/env python3
"""Omega Super AI v10 — Main CLI entry point.

This module implements the primary REPL (Read-Eval-Print Loop) for the
Omega Super AI system.  It handles command parsing, intent detection,
session management, and dispatches work to the appropriate subsystems.

Commands
--------
/research <query>     Deep research with web search + synthesis
/think <query>        Step-by-step reasoning mode
/mentor <topic>       Personalised mentoring session
/expert <domain>      Expert-level professional consultation
/finance <query>      Financial analysis & market data
/scam <text>          Scam / fraud detection analysis
/learn <topic>        Learning & skill-building mode
/history              Show conversation history
/memory               Show long-term memory store
/clear                Clear the terminal screen
/help                 Show command reference
/quit                 Exit the application

Examples
--------
Run interactively::

    $ python -m omega.omega

Or directly::

    $ python omega/omega.py
"""

from __future__ import annotations

import argparse
import atexit
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Dependency imports with graceful fallbacks
# ---------------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    print("Error: 'rich' is required.  Install it with: pip install rich")
    raise SystemExit(1)

# Omega internal modules
from omega.config import load_config, validate_config
from omega.database import (
    close_db,
    get_cache,
    get_history,
    get_learning,
    get_memory,
    get_scam_reports,
    init_db,
    save_cache,
    save_conversation,
    save_learning,
    save_memory,
    save_scam_report,
)
from omega.utils import (
    box_text,
    colorize,
    confirm,
    format_sources,
    get_console,
    loading_animation,
    print_error,
    print_header,
    print_info,
    print_section,
    print_success,
    print_warning,
    truncate_text,
)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

APP_NAME = "Omega Super AI"
APP_VERSION = "10.0.0"
APP_BUILD = "2025.07"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class SessionState:
    """Holds mutable runtime state for a single CLI session."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.session_id: str = str(uuid.uuid4())[:8]
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self.turn_count: int = 0
        self.running: bool = True
        self.console: Console = get_console()

    def elapsed_seconds(self) -> float:
        """Return seconds since session start."""
        start = datetime.fromisoformat(self.start_time)
        return (datetime.now(timezone.utc) - start).total_seconds()


# Singleton populated in main()
_state: SessionState | None = None


# ---------------------------------------------------------------------------
# Startup & shutdown
# ---------------------------------------------------------------------------


def _shutdown_handler(signum: int, frame: Any) -> None:
    """Handle SIGINT / SIGTERM gracefully."""
    global _state
    if _state is not None:
        _state.running = False
    print("\n")
    print_info("Shutdown signal received — cleaning up …")
    close_db()
    raise SystemExit(0)


def _register_signal_handlers() -> None:
    """Register OS signal handlers for clean shutdown."""
    signal.signal(signal.SIGINT, _shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown_handler)


def show_banner(config: dict[str, Any]) -> None:
    """Display the Omega Super AI startup banner with system status."""
    console = get_console()

    # ASCII-art logo (rendered with rich for colour)
    logo_lines = [
        "  ██████╗ ███╗   ███╗███████╗ ██████╗  █████╗     ███████╗██╗   ██╗██████╗ ███████╗██████╗     █████╗ ██╗",
        " ██╔═══██╗████╗ ████║██╔════╝██╔═══██╗██╔══██╗    ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗   ██╔══██╗██║",
        " ██║   ██║██╔████╔██║█████╗  ██║   ██║███████║    ███████╗██║   ██║██████╔╝█████╗  ██████╔╝   ███████║██║",
        " ██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║    ╚════██║██║   ██║██╔══██╗██╔══╝  ██╔══██╗   ██╔══██║██║",
        " ╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║    ███████║╚██████╔╝██║  ██║███████╗██║  ██║██╗██║  ██║██║",
        "  ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝",
        "",
    ]
    for line in logo_lines:
        console.print(Text(line, style="bold cyan"))

    print_header(f"{APP_NAME}  [v{APP_VERSION}  build {APP_BUILD}]")

    # System status table
    status_items = [
        ("Session ID", _state.session_id if _state else "—"),
        ("Model", config.get("model", "—")),
        ("Debug", "enabled" if config.get("debug") else "disabled"),
        ("Cache TTL", f"{config.get('cache_ttl_hours', 24)} h"),
        ("Max results", str(config.get("max_search_results", 15))),
        ("Workers", str(config.get("max_workers", 5))),
        ("Database", config.get("db_path", "—")),
    ]

    max_key = max(len(k) for k, _ in status_items)
    for key, value in status_items:
        console.print(
            f"  {colorize(key.ljust(max_key + 2), 'dim')} {colorize(value, 'green' if value != '—' else 'dim')}"
        )

    console.print()
    print_info("Type /help for available commands or ask me anything.")
    console.print()


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------


def detect_intent(query: str) -> str:
    """Classify a free-form query into an intent label.

    The classifier uses a keyword-based heuristic that looks for
    domain-specific trigger words.  Returns one of:

    ``research``, ``think``, ``mentor``, ``expert``, ``finance``,
    ``scam``, ``learn``, ``general``.

    Args:
        query: Raw user input (without the leading ``/command``).

    Returns:
        Intent label string.
    """
    q = query.lower()

    # Finance triggers
    if any(w in q for w in (
        "stock", "price", "market", "crypto", "bitcoin", "ethereum",
        "invest", "portfolio", "dividend", "earnings", "revenue",
        "financial", "economy", "inflation", "rate", "trading",
    )):
        return "finance"

    # Scam / fraud triggers
    if any(w in q for w in (
        "scam", "fraud", "phishing", "spam", "suspicious",
        "hack", "steal", "fake", "identity theft", "ponzi",
        "pyramid", "malware", "virus",
    )):
        return "scam"

    # Mentor triggers — checked before general learning so career/mentor
    # questions are not captured by "how to" learning patterns.
    if any(w in q for w in (
        "mentor", "guide", "advice", "career", "coach",
        "personal development", "self improvement",
    )):
        return "mentor"

    # Expert triggers
    if any(w in q for w in (
        "expert", "professional", "consult", "specialist",
        "advanced analysis", "deep dive", "industry",
    )):
        return "expert"

    # Learning triggers
    if any(w in q for w in (
        "learn", "tutorial", "course", "lesson", "study",
        "how to", "explain", "teach me", "beginner",
        "advanced", "skill",
    )):
        return "learn"

    # Think / reasoning triggers
    if any(w in q for w in (
        "think", "reason", "step by step", "logic", "solve",
        "brain teaser", "puzzle", "riddle", "analysis",
    )):
        return "think"

    # Research triggers
    if any(w in q for w in (
        "research", "search", "find", "lookup", "information",
        "data", "report", "survey", "study",
    )):
        return "research"

    return "general"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def handle_default(query: str) -> str:
    """Default handler for non-command free-form queries."""
    intent = detect_intent(query)
    print_info(f"Detected intent: [bold]{intent}[/bold]")
    loading_animation("Processing your request …", duration=1.2)

    response = (
        f"Hi! I'm Omega Super AI v10. You asked about: \"{query}\"\n\n"
        f"(Intent detected: {intent})\n\n"
        "This is a default response.  The full AI integration will be "
        "connected in a subsequent module.  Try these commands:\n"
        "  /research <topic>   — Deep research mode\n"
        "  /think <question>   — Step-by-step reasoning\n"
        "  /finance <query>    — Financial analysis\n"
        "  /scam <text>        — Scam detection\n"
        "  /learn <topic>      — Learning mode\n"
        "  /mentor <topic>     — Personal mentoring\n"
        "  /help               — Full command list"
    )
    return response


def handle_research(args: str) -> str:
    """Handle ``/research`` — deep research with web search."""
    if not args.strip():
        return "Usage: /research <topic or question>"

    print_section("Research Mode")
    loading_animation(f"Researching: {args} …", duration=1.5)

    # Check cache first
    cached = get_cache(args, ttl_hours=_state.config["cache_ttl_hours"]) if _state else None
    if cached:
        print_success("Found cached results.")
        sources = [{"title": c.get("title", "Cached"), "url": c.get("url", "")} for c in cached[:5]]
        return f"Cached research results for: {args}\n\n{format_sources(sources)}"

    # Stub response (full web search integration coming later)
    results = [
        {"title": f"Research: {args}", "url": "https://example.com/research", "source": "web"},
        {"title": "Related article", "url": "https://example.com/article", "source": "web"},
    ]
    save_cache(args, results)
    return f"Research results for: {args}\n\n{format_sources(results)}\n\n(Full AI-powered research synthesis coming in next module.)"


def handle_think(args: str) -> str:
    """Handle ``/think`` — step-by-step reasoning mode."""
    if not args.strip():
        return "Usage: /think <question or problem>"

    print_section("Chain-of-Thought Mode")
    loading_animation("Thinking step-by-step …", duration=1.5)

    steps = [
        f"1. **Understanding the problem**: \"{args}\"",
        "2. **Breaking it down**: Identifying key components and constraints …",
        "3. **Exploring approaches**: Evaluating multiple solution strategies …",
        "4. **Synthesising answer**: Formulating the best response …",
    ]
    return "\n".join(steps) + "\n\n(Full reasoning engine will be connected in a subsequent module.)"


def handle_mentor(args: str) -> str:
    """Handle ``/mentor`` — personalised mentoring session."""
    if not args.strip():
        return "Usage: /mentor <topic or goal>"

    print_section("Mentoring Mode")
    loading_animation(f"Preparing mentorship for: {args} …", duration=1.2)

    # Save learning context
    save_memory(f"mentor_topic_{args[:30]}", args, category="mentoring")

    return (
        f"Welcome to your mentoring session on **{args}**!\n\n"
        "I'll guide you through a structured learning path:\n"
        "1. Assess your current level\n"
        "2. Set clear milestones\n"
        "3. Provide resources and exercises\n"
        "4. Track your progress\n\n"
        "(Full mentoring engine will be connected in a subsequent module.)"
    )


def handle_expert(args: str) -> str:
    """Handle ``/expert`` — expert-level consultation."""
    if not args.strip():
        return "Usage: /expert <domain or question>"

    print_section("Expert Consultation")
    loading_animation("Consulting domain experts …", duration=1.2)

    domains = ["Technology", "Science", "Business", "Medicine", "Law", "Engineering"]
    return (
        f"Expert consultation activated for: **{args}**\n\n"
        f"Available domains: {', '.join(domains)}\n\n"
        "I'll provide professional-grade analysis and recommendations.\n\n"
        "(Full expert system will be connected in a subsequent module.)"
    )


def handle_finance(args: str) -> str:
    """Handle ``/finance`` — financial analysis."""
    if not args.strip():
        return (
            "Usage: /finance <query>\n"
            "Examples:\n"
            "  /finance AAPL stock price\n"
            "  /finance Bitcoin analysis\n"
            "  /finance portfolio allocation"
        )

    print_section("Financial Analysis")
    loading_animation(f"Analysing: {args} …", duration=1.5)

    return (
        f"Financial analysis for: **{args}**\n\n"
        "Capabilities:\n"
        "• Real-time stock quotes\n"
        "• Technical & fundamental analysis\n"
        "• Portfolio optimisation\n"
        "• Market trend identification\n"
        "• Risk assessment\n\n"
        "(Full financial data integration will be connected in a subsequent module.)"
    )


def handle_scam(args: str) -> str:
    """Handle ``/scam`` — scam / fraud detection analysis."""
    if not args.strip():
        return "Usage: /scam <text to analyse>"

    print_section("Scam Detection")
    loading_animation("Analysing for scam indicators …", duration=1.5)

    # Common indicators
    red_flags = [
        "Urgency or time pressure",
        "Requests for personal information",
        "Too-good-to-be-true offers",
        "Unsolicited contact",
        "Requests for money transfers",
        "Suspicious URLs or email addresses",
    ]

    detected = [flag for flag in red_flags if any(word in args.lower() for word in flag.lower().split())]

    report_id = save_scam_report(
        scam_type="user_submitted",
        description=args,
        indicators=detected or red_flags[:3],
    )

    result = (
        f"Scam analysis report #{report_id} for: **{truncate_text(args, 80)}**\n\n"
        f"**Risk level**: {'⚠️ HIGH' if detected else '✓ Low — no obvious red flags'}\n\n"
        "**Common red flags to watch for:**\n"
    )
    for flag in red_flags:
        marker = "⚠️" if flag in detected else "  "
        result += f"  {marker} {flag}\n"

    result += "\n(Full AI-powered scam detection will be connected in a subsequent module.)"
    return result


def handle_learn(args: str) -> str:
    """Handle ``/learn`` — learning & skill-building mode."""
    if not args.strip():
        return "Usage: /learn <topic>"

    print_section("Learning Mode")
    loading_animation(f"Preparing learning path for: {args} …", duration=1.2)

    # Check existing progress
    progress = get_learning(topic=args)
    if progress and isinstance(progress, dict):
        lessons = progress.get("completed_lessons", [])
        level = progress.get("level", "beginner")
        print_info(f"Resuming at {level} level. {len(lessons)} lessons completed.")
    else:
        lessons = []
        level = "beginner"

    # Save/update progress
    save_learning(topic=args, level=level, completed_lessons=lessons)

    return (
        f"Learning path for: **{args}**\n\n"
        f"Current level: {level}\n"
        f"Lessons completed: {len(lessons)}\n\n"
        "Learning modules:\n"
        "1. Foundational concepts\n"
        "2. Practical exercises\n"
        "3. Advanced techniques\n"
        "4. Real-world projects\n"
        "5. Assessment & certification\n\n"
        "(Full adaptive learning engine will be connected in a subsequent module.)"
    )


def handle_history(args: str) -> str:
    """Handle ``/history`` — show conversation history."""
    print_section("Conversation History")
    limit = 20
    try:
        if args.strip().isdigit():
            limit = int(args.strip())
    except ValueError:
        pass

    history = get_history(session_id=_state.session_id if _state else None, limit=limit)

    if not history:
        return "No conversation history yet."

    lines: list[str] = []
    for entry in history:
        ts = entry["timestamp"][:19] if entry["timestamp"] else "—"
        intent_tag = f" [{entry['intent']}]" if entry["intent"] else ""
        q = truncate_text(entry["user_query"], 60)
        r = truncate_text(entry["response"], 80)
        lines.append(f"  [{ts}]{intent_tag}\n    Q: {q}\n    A: {r}")

    return "\n\n".join(lines)


def handle_memory_cmd(args: str) -> str:
    """Handle ``/memory`` — show or manage memory store."""
    print_section("Memory Store")

    if args.strip().startswith("set "):
        # /memory set key=value
        try:
            kv = args.strip()[4:]
            key, value = kv.split("=", 1)
            save_memory(key.strip(), value.strip())
            print_success(f"Memory saved: {key.strip()}")
            return ""
        except ValueError:
            return "Usage: /memory set key=value"

    if args.strip().startswith("get "):
        key = args.strip()[4:].strip()
        entry = get_memory(key=key)
        if entry is None:
            return f"No memory found for key: {key}"
        return f"  {entry['key']}: {entry['value']}"

    # Show all
    entries = get_memory()
    if not entries:
        return "Memory store is empty.\nUsage:\n  /memory set key=value\n  /memory get <key>"

    lines: list[str] = []
    for entry in entries[:20]:
        ts = entry["timestamp"][:19] if entry["timestamp"] else "—"
        cat = entry["category"]
        lines.append(f"  [{ts}] ({cat}) {entry['key']}: {truncate_text(entry['value'], 60)}")
    return "\n".join(lines)


def handle_clear(args: str) -> str:
    """Handle ``/clear`` — clear the terminal screen."""
    console = get_console()
    console.clear()
    print_header(f"{APP_NAME} v{APP_VERSION}")
    return ""


def handle_help(args: str) -> str:
    """Handle ``/help`` — display command reference."""
    help_text = """
[bold cyan]Omega Super AI v10 — Command Reference[/bold cyan]

[bold]General[/bold]
  <anything>          Ask a natural-language question (intent auto-detected)
  /help               Show this help message
  /quit               Exit the application
  /clear              Clear the terminal screen

[bold]Intelligence Modes[/bold]
  /research <query>   Deep research with web search + AI synthesis
  /think <question>   Step-by-step chain-of-thought reasoning
  /mentor <topic>     Personalised mentoring & guidance
  /expert <domain>    Expert-level professional consultation

[bold]Domain Tools[/bold]
  /finance <query>    Financial analysis, stock data & market insights
  /scam <text>        Analyse text for scam / fraud indicators
  /learn <topic>      Adaptive learning & skill-building path

[bold]Session & Memory[/bold]
  /history [n]        Show last n conversation turns (default 20)
  /memory             List stored memories
  /memory set k=v     Save a key-value pair to memory
  /memory get <key>   Retrieve a specific memory value

[bold]Tips[/bold]
  • Start a query with / for command mode, or just type naturally.
  • Use arrow keys (↑ / ↓) to navigate command history.
  • Press Ctrl+C at any time to exit gracefully.
"""
    console = get_console()
    console.print(help_text)
    return ""


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------

_COMMAND_MAP: dict[str, Any] = {
    "research": handle_research,
    "think": handle_think,
    "mentor": handle_mentor,
    "expert": handle_expert,
    "finance": handle_finance,
    "scam": handle_scam,
    "learn": handle_learn,
    "history": handle_history,
    "memory": handle_memory_cmd,
    "clear": handle_clear,
    "help": handle_help,
    "quit": None,  # handled specially in loop
}


def dispatch_command(raw_input: str) -> str:
    """Parse *raw_input* and route to the correct handler.

    Args:
        raw_input: The user's raw terminal input.

    Returns:
        Response string from the handler.  May be empty for
        display-only commands (e.g. ``/clear``).
    """
    text = raw_input.strip()

    if not text:
        return ""

    # Check for command prefix
    if text.startswith("/"):
        # Split on first space or use the whole word
        parts = text[1:].split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = _COMMAND_MAP.get(cmd)
        if handler is None:
            if cmd in ("quit", "exit", "q"):
                return "__QUIT__"
            return f"Unknown command: /{cmd}.  Type /help for available commands."
        return handler(args)

    # Default: free-form query with intent detection
    return handle_default(text)


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point — runs the Omega Super AI REPL loop."""
    global _state

    # Argument parsing (for optional flags)
    parser = argparse.ArgumentParser(
        prog="omega",
        description="Omega Super AI v10 — Intelligent CLI Assistant",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to custom .env file"
    )
    cli_args = parser.parse_args()

    if cli_args.version:
        print(f"{APP_NAME} v{APP_VERSION}")
        raise SystemExit(0)

    # Load configuration
    config = load_config()
    errors = validate_config(config)
    if errors:
        for err in errors:
            print_error(err)
        print_info("Create a .env file based on .env.example and try again.")
        raise SystemExit(1)

    # Initialize database
    init_db(db_path=config["db_path"])

    # Register cleanup hooks
    atexit.register(close_db)
    _register_signal_handlers()

    # Create session state
    _state = SessionState(config)

    # Show startup banner
    show_banner(config)

    # REPL loop
    console = get_console()
    while _state.running:
        try:
            # Prompt
            prompt_text = colorize(f"Ω [{_state.turn_count:03d}] » ", "cyan")
            user_input = console.input(prompt_text).strip()

            if not user_input:
                continue

            # Special quit shortcuts
            if user_input.lower() in ("/quit", "/exit", "/q", "quit", "exit"):
                break

            # Dispatch
            _state.turn_count += 1
            response = dispatch_command(user_input)

            # Handle quit signal
            if response == "__QUIT__":
                break

            # Display response
            if response:
                # Render markdown-style responses if they contain formatting
                if any(c in response for c in "*#`[]"):
                    console.print(Markdown(response))
                else:
                    console.print(response)
                console.print()

                # Persist conversation (skip for display-only commands)
                save_conversation(
                    session_id=_state.session_id,
                    user_query=user_input,
                    response=response,
                    intent=detect_intent(user_input) if not user_input.startswith("/") else user_input.split()[0][1:],
                )

        except KeyboardInterrupt:
            print()
            if confirm("Really quit"):
                break
            continue
        except EOFError:
            break
        except Exception as exc:
            print_error(f"Unexpected error: {exc}")
            if config.get("debug"):
                import traceback

                console.print(traceback.format_exc())
            continue

    # Graceful shutdown
    print()
    print_info("Saving session data …")
    close_db()
    print_success(f"Session {_state.session_id} ended. Goodbye!")
    console.print()


if __name__ == "__main__":
    main()
