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

import openai
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

# Tax module (imported with graceful fallback)
try:
    from omega.tax_module import InternationalTax
    _tax_module = InternationalTax()
except Exception:
    _tax_module = None

# Opportunities module (imported with graceful fallback)
try:
    from omega.opportunities import OpportunitySeeker
    _opp_seeker = OpportunitySeeker()
except Exception:
    _opp_seeker = None

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
        self._conversation_history: list[dict[str, str]] = []  # last 5 exchanges

    def elapsed_seconds(self) -> float:
        """Return seconds since session start."""
        start = datetime.fromisoformat(self.start_time)
        return (datetime.now(timezone.utc) - start).total_seconds()


# Singleton populated in main()
_state: SessionState | None = None


# ---------------------------------------------------------------------------
# OpenAI integration
# ---------------------------------------------------------------------------

def get_openai_client():
    """Return an OpenAI client using the API key from config."""
    api_key = _state.config.get("openai_api_key") if _state else ""
    if api_key:
        return openai.OpenAI(api_key=api_key)
    return None


def _ai_chat(system_prompt: str, user_message: str, model: str = None) -> str:
    """Send a message to OpenAI and return the response text.

    Automatically includes the last 5 conversation exchanges for context.
    """
    client = get_openai_client()
    if not client:
        return (
            "OpenAI API key not configured. Add OPENAI_API_KEY to your .env file.\n\n"
            "Once configured, I'll be able to provide intelligent, context-aware responses!"
        )
    try:
        model = model or (_state.config.get("model") if _state else None) or "gpt-4o-mini"
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Include conversation history for context (last 5 exchanges)
        if _state and _state._conversation_history:
            messages.extend(_state._conversation_history[-10:])  # 5 Q/A pairs = 10 messages

        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        content = resp.choices[0].message.content or "No response from AI."

        # Store exchange in conversation history
        if _state is not None:
            _state._conversation_history.append({"role": "user", "content": user_message})
            _state._conversation_history.append({"role": "assistant", "content": content})
            # Keep only last 5 exchanges (10 messages)
            if len(_state._conversation_history) > 10:
                _state._conversation_history = _state._conversation_history[-10:]

        return content
    except Exception as e:
        return f"AI Error: {e}"


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

    # Tax triggers
    if any(w in q for w in (
        "tax", "vat", "gst", "income tax", "filing", "deduction",
        "bracket", "withholding", "capital gains", "tax return",
        "tax rate", "tax liability", "tax credit", "tax treaty",
        "double taxation", "expat tax", "digital nomad visa",
        "tax authority", "tax compliance", "tax residency",
        "tax obligation", "tax year", "tax free", "offshore tax",
        "social security contributions", "tax calculator",
    )):
        return "tax"

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

    # Opportunities triggers
    if any(w in q for w in (
        "job", "jobs", "career", "hiring", "vacancy", "vacancies",
        "employment", "work opportunity", "position", "opening",
        "tender", "tenders", "rfp", "bid", "bids", "contract",
        "business opportunity", "partnership", "distributorship",
        "franchise", "investment opportunity", "grant", "grants",
        "funding", "scholarship", "scholarships", "bursary", "bursaries",
        "fellowship", "fellowships", "freelance", "gig work",
        "side hustle", "networking event", "conference", "trade show",
        "startup funding", "seed funding", "angel investor",
        "venture capital", "crowdfunding",
    )):
        return "opportunities"

    return "general"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def handle_default(query: str) -> str:
    """Default handler for non-command free-form queries."""
    intent = detect_intent(query)
    print_info(f"Detected intent: [bold]{intent}[/bold]")
    loading_animation("Processing your request …", duration=1.2)

    system = (
        "You are Omega Super AI, a helpful, knowledgeable assistant. "
        "Provide clear, well-structured answers. When appropriate, cite sources "
        "and include disclaimers for financial/medical advice."
    )
    return _ai_chat(system, query)


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
        cached_text = f"Cached research results for: {args}\n\n{format_sources(sources)}"
        # Enhance cached results with AI
        ai_summary = _ai_chat(
            "You are a research assistant. Provide comprehensive, well-sourced information. "
            "Structure your response with clear headings, bullet points, and source citations.",
            f"Synthesize and expand on the following cached research about '{args}':\n\n{cached_text}",
        )
        return f"{cached_text}\n\n---\n\n**AI Synthesis:**\n\n{ai_summary}"

    system = (
        "You are a research assistant. Provide comprehensive, well-sourced information. "
        "Structure your response with clear headings, bullet points, and source citations."
    )
    return _ai_chat(system, args)


def handle_think(args: str) -> str:
    """Handle ``/think`` — step-by-step reasoning mode."""
    if not args.strip():
        return "Usage: /think <question or problem>"

    print_section("Chain-of-Thought Mode")
    loading_animation("Thinking step-by-step …", duration=1.5)

    system = (
        "You are a critical thinking analyst. Break down the problem step by step, "
        "identify assumptions, evaluate evidence, consider alternatives, and provide "
        "a reasoned conclusion."
    )
    return _ai_chat(system, args)


def handle_mentor(args: str) -> str:
    """Handle ``/mentor`` — personalised mentoring session."""
    if not args.strip():
        return "Usage: /mentor <topic or goal>"

    print_section("Mentoring Mode")
    loading_animation(f"Preparing mentorship for: {args} …", duration=1.2)

    # Save learning context
    save_memory(f"mentor_topic_{args[:30]}", args, category="mentoring")

    system = (
        "You are a supportive mentor and coach. Create structured learning paths, "
        "set milestones, provide encouragement, and give actionable advice for "
        "personal and professional growth."
    )
    return _ai_chat(system, args)


def handle_expert(args: str) -> str:
    """Handle ``/expert`` — expert-level consultation."""
    if not args.strip():
        return "Usage: /expert <domain or question>"

    print_section("Expert Consultation")
    loading_animation("Consulting domain experts …", duration=1.2)

    system = (
        "You are a senior professional consultant with deep expertise across multiple "
        "domains. Provide expert-level analysis, best practices, and practical "
        "recommendations. Always note when professional in-person consultation is needed."
    )
    return _ai_chat(system, args)


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

    system = (
        "You are a financial literacy educator. Provide educational information about "
        "personal finance, investing, and money management. Always include a disclaimer "
        "that this is educational information only and not professional financial advice. "
        "Be cautious about risk."
    )
    return _ai_chat(system, args)


def handle_tax(args: str) -> str:
    """Handle ``/tax`` — international tax knowledge base queries.

    Subcommands:
      authority <country>     — Tax authority contact info
      profile <country>       — Full tax system profile
      calculate <country> <income> [status] [deductions]
                              — Progressive tax estimate
      nomad <country>         — Digital nomad tax guide
      treaty <a> <b>          — Double taxation agreement info
      expat <home> <host>     — Expat tax guide
      compliance <country>    — Filing requirements
      compare <c1> <c2> ...   — Compare tax systems
      lowtax                  — List low-tax jurisdictions
    """
    if not _tax_module:
        return (
            "Tax module is not available. Ensure tax_module.py is in "
            "the omega package and has no import errors."
        )

    parts = args.strip().split()
    if not parts:
        return (
            "[bold cyan]International Tax Module[/bold cyan]\n\n"
            "Usage: /tax <subcommand> [args]\n\n"
            "[bold]Subcommands:[/bold]\n"
            "  authority <country>          Tax authority contact info\n"
            "  profile <country>            Full tax system profile\n"
            "  calculate <country> <income> [single|married] [deductions]\n"
            "                               Estimate income tax\n"
            "  nomad <country>              Digital nomad tax guide\n"
            "  treaty <country_a> <country_b>\n"
            "                               Check DTA between countries\n"
            "  expat <home> <host>          Expat tax guide\n"
            "  compliance <country>         Filing requirements\n"
            "  compare <c1> <c2> ...        Compare tax systems\n"
            "  lowtax                       List low-tax jurisdictions\n\n"
            "[bold]Examples:[/bold]\n"
            "  /tax authority United States\n"
            "  /tax profile Singapore\n"
            "  /tax calculate Germany 75000 married\n"
            "  /tax nomad Portugal\n"
            "  /tax treaty United States United Kingdom\n"
            "  /tax expat United States Germany\n"
            "  /tax compliance India\n"
            "  /tax compare UAE Singapore Switzerland\n"
            f"\n{_tax_module._disclaimer}"
        )

    sub = parts[0].lower()

    # ---- authority ----
    if sub == "authority":
        if len(parts) < 2:
            return "Usage: /tax authority <country>"
        country = " ".join(parts[1:])
        result = _tax_module.get_tax_authority(country)
        if "error" in result:
            return f"Error: {result['error']}"
        lines = [
            f"[bold cyan]Tax Authority: {result['country']}[/bold cyan]",
            f"  Authority:   {result['authority_name']}",
            f"  Website:     {result['website']}",
            f"  E-filing:    {result['e_filing_url'] or 'N/A'}",
            f"  Phone:       {result['contact_phone'] or 'N/A'}",
            f"  Email:       {result['contact_email'] or 'N/A'}",
            f"  Updated:     {result['last_updated']}",
        ]
        return "\n".join(lines)

    # ---- profile ----
    if sub == "profile":
        if len(parts) < 2:
            return "Usage: /tax profile <country>"
        country = " ".join(parts[1:])
        result = _tax_module.get_tax_profile(country)
        if "error" in result:
            return f"Error: {result['error']}"
        lines = [
            f"[bold cyan]Tax Profile: {result['country']}[/bold cyan]",
            f"  Tax Year:        {result.get('tax_year_calendar', 'N/A')}",
            "",
            "[bold]Personal Income Tax[/bold]",
        ]
        pit = result.get("personal_income_tax", {})
        lines.append(f"  Has PIT:         {pit.get('has_it', 'N/A')}")
        if pit.get("has_it"):
            lines.append(f"  Top Rate:        {pit.get('top_rate', 'N/A')}")
            lines.append(f"  Brackets:        {pit.get('brackets_summary', 'N/A')}")
            lines.append(f"  Std Deduction:   {pit.get('standard_deduction', 'N/A')}")
            lines.append(f"  Filing Deadline: {pit.get('filing_deadline', 'N/A')}")
        lines.append("")
        ct = result.get("corporate_tax", {})
        lines.append(f"[bold]Corporate Tax[/bold]")
        lines.append(f"  Rate:            {ct.get('rate', 'N/A')}")
        lines.append(f"  Filing Deadline: {ct.get('filing_deadline', 'N/A')}")
        lines.append("")
        vat = result.get("vat_gst", {})
        lines.append(f"[bold]VAT/GST[/bold]")
        lines.append(f"  Has VAT/GST:     {vat.get('has_it', 'N/A')}")
        if vat.get("has_it"):
            lines.append(f"  Name:            {vat.get('rate_name', 'N/A')}")
            lines.append(f"  Standard Rate:   {vat.get('standard_rate', 'N/A')}")
            lines.append(f"  Reduced Rate:    {vat.get('reduced_rate', 'N/A')}")
        lines.append("")
        wht = result.get("withholding_tax", {})
        lines.append(f"[bold]Withholding Tax[/bold]")
        lines.append(f"  Dividends:       {wht.get('dividends', 'N/A')}")
        lines.append(f"  Interest:        {wht.get('interest', 'N/A')}")
        lines.append(f"  Royalties:       {wht.get('royalties', 'N/A')}")
        lines.append("")
        dta_list = result.get("double_taxation_treaties", [])
        lines.append(f"[bold]DTA Network[/bold]")
        lines.append(f"  Treaties with {len(dta_list)} countries")
        if dta_list:
            lines.append(f"  Examples: {', '.join(dta_list[:10])}")
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- calculate ----
    if sub == "calculate":
        if len(parts) < 3:
            return "Usage: /tax calculate <country> <income> [filing_status] [deductions]"
        country = " ".join(parts[1:-1])
        income_str = parts[-1]
        status = "single"
        deductions = 0.0
        # Parse: calculate <country> <income> [status] [deductions]
        try:
            income = float(parts[2])
            country = parts[1] if len(parts) == 3 else " ".join(parts[1:2])
            if len(parts) >= 4:
                # parts[3] could be status or deductions
                if parts[3].lower() in ("single", "married", "married_separate", "head_of_household", "joint", "separate"):
                    status = parts[3].lower()
                    if len(parts) >= 5:
                        deductions = float(parts[4])
                else:
                    deductions = float(parts[3])
            # Re-parse more robustly
            # pattern: calculate COUNTRY INCOME [STATUS] [DEDUCTIONS]
            # Try income at position 2
            income = float(parts[2])
            country = parts[1]
            status = "single"
            deductions = 0.0
            if len(parts) >= 4:
                p3 = parts[3].lower()
                if p3 in ("single", "married", "married_separate", "head_of_household", "joint", "separate", "mfs", "hoh"):
                    status = parts[3]
                    if len(parts) >= 5:
                        try:
                            deductions = float(parts[4])
                        except ValueError:
                            pass
                else:
                    try:
                        deductions = float(parts[3])
                    except ValueError:
                        pass
        except (ValueError, IndexError):
            return "Usage: /tax calculate <country> <income> [filing_status] [deductions]\nExample: /tax calculate United States 85000 single 5000"

        result = _tax_module.estimate_income_tax(country, income, status, deductions)
        if "error" in result:
            return f"Error: {result['error']}"
        lines = [
            f"[bold cyan]Tax Estimate: {result['country']}[/bold cyan]",
            f"  Tax Year:        {result['tax_year']}",
            f"  Gross Income:    {result['gross_income']:,.2f} {result['currency']}",
            f"  Std Deduction:   {result['standard_deduction']:,.2f} {result['currency']}",
            f"  Add\'l Deductions: {result['additional_deductions']:,.2f} {result['currency']}",
            f"  Taxable Income:  {result['taxable_income']:,.2f} {result['currency']}",
            f"  Total Tax:       {result['total_tax']:,.2f} {result['currency']}",
            f"  Effective Rate:  {result['effective_rate_percent']}%",
            f"  Filing Status:   {result['filing_status']}",
            "",
            "[bold]Tax by Bracket:[/bold]",
        ]
        for b in result.get("tax_by_bracket", []):
            hi = str(b['bracket_high'])
            lines.append(
                f"  {b['bracket_low']:>12,.0f} – {hi:>12} @ {b['rate']*100:>5.1f}% = "
                f"{b['tax']:>12,.2f}"
            )
        lines.append("")
        lines.append(f"[dim]{result['notes']}[/dim]")
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- nomad ----
    if sub == "nomad":
        if len(parts) < 2:
            return "Usage: /tax nomad <country>"
        country = " ".join(parts[1:])
        result = _tax_module.get_digital_nomad_tax_guide(country)
        if "error" in result:
            return f"Error: {result['error']}"
        lines = [
            f"[bold cyan]Digital Nomad Guide: {result['country']}[/bold cyan]",
            f"  Visa Available:    {result.get('digital_nomad_visa_available', 'N/A')}",
            f"  Visa Details:      {result.get('visa_details', 'N/A')}",
            f"  Residency Days:    {result.get('tax_residency_days_threshold', 'N/A')}",
            "",
            "[bold]Tax Obligations:[/bold]",
            f"  {result.get('tax_obligations_for_nomads', 'N/A')}",
            "",
            "[bold]Recommended Structure:[/bold]",
            f"  {result.get('recommended_structure', 'N/A')}",
            "",
            "[bold red]Warnings:[/bold red]",
            f"  {result.get('warnings', 'N/A')}",
            "",
            f"[dim]{_tax_module._disclaimer}[/dim]",
        ]
        return "\n".join(lines)

    # ---- treaty ----
    if sub == "treaty":
        if len(parts) < 3:
            return "Usage: /tax treaty <country_a> <country_b>"
        ca, cb = parts[1], parts[2]
        result = _tax_module.get_dta_info(ca, cb)
        if not result.get("has_treaty"):
            lines = [
                f"[bold cyan]DTA: {result['country_a']} ↔ {result['country_b']}[/bold cyan]",
                "  [red]No DTA information found in database.[/red]",
                f"  {result.get('notes', '')}",
            ]
        else:
            lines = [
                f"[bold cyan]DTA: {result['country_a']} ↔ {result['country_b']}[/bold cyan]",
                f"  Has Treaty:     {result['has_treaty']}",
                f"  Dividends WHT:  {result.get('dividends_rate', 'N/A')}",
                f"  Interest WHT:   {result.get('interest_rate', 'N/A')}",
                f"  Royalties WHT:  {result.get('royalties_rate', 'N/A')}",
                f"  Method:         {result.get('method', 'N/A')}",
                f"  Tie-Breaker:    {result.get('tie_breaker_rule', 'N/A')}",
            ]
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- expat ----
    if sub == "expat":
        if len(parts) < 3:
            return "Usage: /tax expat <home_country> <host_country>"
        home, host = parts[1], parts[2]
        result = _tax_module.get_expat_tax_guide(home, host)
        lines = [
            f"[bold cyan]Expat Tax Guide: {result['home_country']} → {result['host_country']}[/bold cyan]",
            "",
            "[bold]Home Country Rules:[/bold]",
        ]
        if "tax_residency_rules" in result:
            lines.append(f"  {result['tax_residency_rules']}")
        if "home_country_filing_obligations" in result:
            lines.append("")
            lines.append("[bold]Home Filing Obligations:[/bold]")
            lines.append(f"  {result['home_country_filing_obligations']}")
        if "recommended_actions" in result:
            lines.append("")
            lines.append("[bold]Recommended Actions:[/bold]")
            for action in result["recommended_actions"]:
                lines.append(f"  • {action}")
        if "warnings" in result:
            lines.append("")
            lines.append(f"[bold red]Warnings:[/bold red]\n  {result['warnings']}")
        if "general_recommendations" in result:
            lines.append("")
            lines.append("[bold]General Recommendations:[/bold]")
            for rec in result["general_recommendations"]:
                lines.append(f"  • {rec}")
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- compliance ----
    if sub == "compliance":
        if len(parts) < 2:
            return "Usage: /tax compliance <country> [individual|corporate]"
        country = parts[1]
        entity = parts[2] if len(parts) > 2 else "individual"
        result = _tax_module.check_compliance_requirements(country, entity)
        if "error" in result:
            return f"Error: {result['error']}"
        lines = [
            f"[bold cyan]Compliance: {result['country']} ({result['entity_type']})[/bold cyan]",
            "",
            "[bold]Required Filings:[/bold]",
        ]
        for filing in result.get("required_filings", []):
            lines.append(f"  • {filing['form']}: {filing['description']}")
            lines.append(f"    Deadline: {filing['deadline']} | Electronic: {filing['electronic']}")
        lines.append("")
        lines.append(f"[bold]Record Keeping:[/bold]\n  {result.get('record_keeping', 'N/A')}")
        penalties = result.get("penalties", {})
        if penalties:
            lines.append("")
            lines.append("[bold red]Penalties:[/bold red]")
            for k, v in penalties.items():
                lines.append(f"  • {k}: {v}")
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- compare ----
    if sub == "compare":
        if len(parts) < 3:
            return "Usage: /tax compare <country1> <country2> [country3] ..."
        countries = parts[1:]
        result = _tax_module.get_comparison(countries)
        lines = [f"[bold cyan]Tax Comparison ({result['count']} countries)[/bold cyan]", ""]
        for entry in result.get("comparison", []):
            if "note" in entry:
                lines.append(f"  [yellow]{entry['country']}: {entry['note']}[/yellow]")
            else:
                lines.append(
                    f"  [bold]{entry['country']}[/bold]: "
                    f"PIT top={entry['top_income_tax_rate']}, "
                    f"CIT={entry['corporate_tax_rate']}, "
                    f"VAT={entry['vat_gst_rate']}, "
                    f"CGT={'Yes' if entry['has_cgt'] else 'No'}({entry['cgt_rate']})"
                )
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- lowtax ----
    if sub == "lowtax":
        result = _tax_module.get_low_tax_jurisdictions()
        lines = [
            "[bold cyan]Low / Zero Tax Jurisdictions[/bold cyan]",
            "",
            "[bold]Zero Personal Income Tax:[/bold]",
        ]
        for j in result.get("zero_personal_income_tax", []):
            lines.append(f"  • {j}")
        lines.append("")
        lines.append("[bold]Zero Corporate Tax:[/bold]")
        for j in result.get("zero_corporate_tax", []):
            lines.append(f"  • {j}")
        lines.append("")
        lines.append("[bold]Territorial Tax Systems:[/bold]")
        for j in result.get("territorial_tax_systems", []):
            lines.append(f"  • {j}")
        lines.append("")
        for note in result.get("notes", []):
            lines.append(f"[dim]  {note}[/dim]")
        lines.append("")
        lines.append(f"[dim]{_tax_module._disclaimer}[/dim]")
        return "\n".join(lines)

    # ---- AI fallback for unknown subcommands ----
    print_info(f"Tax subcommand '{sub}' not recognised — consulting AI …")
    system = (
        "You are a tax information assistant. Provide general educational information "
        "about tax systems. Always emphasize that this is not professional tax advice "
        "and users should consult a certified tax professional for their jurisdiction."
    )
    return _ai_chat(system, f"Tax question about '{sub}' with args: {args}")


def handle_opportunities(args: str) -> str:
    """Handle ``/opps`` / ``/opportunities`` — opportunity discovery.

    Subcommands:
      jobs <query> [loc] [cat]       — Search job openings
      business [industry] [loc]      — Tenders, RFPs, partnerships
      invest <category> [loc]        — Investment opportunities
      freelance <query> [skills]     — Freelance / gig work
      grants [type] [loc]            — Grants and funding
      scholarships [level] [field]   — Scholarships & bursaries
      network <topic> [loc]          — Events, conferences, meetups
      match                          — Match profile to opportunities
      saved                          — View saved opportunities
    """
    if not _opp_seeker:
        return (
            "Opportunities module is not available. Ensure opportunities.py "
            "is in the omega package and has no import errors."
        )

    parts = args.strip().split()
    if not parts:
        return (
            "[bold cyan]Opportunities Discovery[/bold cyan]\n\n"
            "Usage: /opps <subcommand> [args]\n\n"
            "[bold]Subcommands:[/bold]\n"
            "  jobs <query> [location] [category]\n"
            "      Search job openings across 50+ job boards\n"
            "  business [industry] [location] [type]\n"
            "      Tenders, RFPs, partnerships, franchises\n"
            "  invest <category> [location] [budget]\n"
            "      Real estate, startup, franchise, stock opportunities\n"
            "  freelance <query> [skills] [rate]\n"
            "      Gig work across Upwork, Fiverr, Freelancer, etc.\n"
            "  grants [type] [purpose] [location]\n"
            "      Government, NGO, international grants & funding\n"
            "  scholarships [level] [field] [country]\n"
            "      Scholarships, bursaries, fellowships\n"
            "  network <topic> [location] [date_range]\n"
            "      Conferences, trade shows, meetups, webinars\n"
            "  match\n"
            "      Match your profile to available opportunities\n"
            "  saved\n"
            "      View previously saved opportunities\n\n"
            "[bold]Examples:[/bold]\n"
            "  /opps jobs software engineer Johannesburg\n"
            "  /opps business construction Gauteng tender\n"
            "  /opps invest real estate Cape Town\n"
            "  /opps freelance web design\n"
            "  /opps grants small_business South Africa\n"
            "  /opps scholarships masters computer_science\n"
            "  /opps network technology Africa\n"
            "  /opps match\n"
            "\n[dim]Opportunity data is for informational purposes only.\n"
            "Always verify details directly with the listing source.[/dim]"
        )

    sub = parts[0].lower()

    # ---- jobs ----
    if sub == "jobs":
        query = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        category = parts[3] if len(parts) > 3 else ""
        experience = parts[4] if len(parts) > 4 else ""
        if not query:
            return "Usage: /opps jobs <query> [location] [category] [experience]\n"
        results = _opp_seeker.search_jobs(query, location, category, experience)
        if not results:
            return f"No job results found for '{query}'. Try broadening your search."
        listing = _opp_seeker.format_opportunity_list(results, f"Job Opportunities: {query}")
        ai_tip = _ai_chat(
            "You are a career coach. Provide brief, actionable advice for job seekers.",
            f"Give 3 short tips for someone searching for '{query}' jobs in '{location or 'any location'}'.",
        )
        return f"{listing}\n\n---\n\n**Career Tips:**\n\n{ai_tip}"

    # ---- business ----
    if sub == "business":
        industry = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        opp_type = parts[3] if len(parts) > 3 else ""
        results = _opp_seeker.search_business_opportunities(industry, location, opp_type)
        if not results:
            return "No business opportunities found. Try adjusting your filters."
        listing = _opp_seeker.format_opportunity_list(results, "Business Opportunities")
        ai_tip = _ai_chat(
            "You are a business development advisor. Give short, practical advice.",
            f"Give 2-3 brief tips for pursuing business opportunities in '{industry or 'general industry'}' in '{location or 'this region'}'.",
        )
        return f"{listing}\n\n---\n\n**Business Advice:**\n\n{ai_tip}"

    # ---- invest ----
    if sub == "invest":
        category = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        budget = parts[3] if len(parts) > 3 else ""
        if not category:
            return (
                "Usage: /opps invest <category> [location] [budget_range]\n"
                "Categories: real_estate, startup, franchise, stocks, "
                "agriculture, crypto, renewable_energy, private_equity\n"
                "Example: /opps invest real_estate Cape Town under_1m"
            )
        results = _opp_seeker.search_investment_opportunities(category, location, budget)
        if not results:
            return f"No investment opportunities found for '{category}'."
        listing = _opp_seeker.format_opportunity_list(results, f"Investment Opportunities: {category}")
        ai_tip = _ai_chat(
            "You are an investment education assistant. Provide educational information only, "
            "not investment advice. Always include a disclaimer.",
            f"Give 2-3 brief educational tips about '{category}' investing. Include a disclaimer that this is not financial advice.",
        )
        return f"{listing}\n\n---\n\n**Investment Education:**\n\n{ai_tip}"

    # ---- freelance ----
    if sub == "freelance":
        query = parts[1] if len(parts) > 1 else ""
        skills = parts[2] if len(parts) > 2 else ""
        rate = parts[3] if len(parts) > 3 else ""
        if not query:
            return "Usage: /opps freelance <query> [skills] [hourly_rate]\nExample: /opps freelance web_design"
        results = _opp_seeker.search_freelance(query, skills, rate)
        if not results:
            return f"No freelance opportunities found for '{query}'."
        listing = _opp_seeker.format_opportunity_list(results, f"Freelance Opportunities: {query}")
        ai_tip = _ai_chat(
            "You are a freelancing coach. Give short, actionable advice.",
            f"Give 2-3 brief tips for a freelancer offering '{query}' services.",
        )
        return f"{listing}\n\n---\n\n**Freelancing Tips:**\n\n{ai_tip}"

    # ---- grants ----
    if sub == "grants":
        entity_type = parts[1] if len(parts) > 1 else ""
        purpose = parts[2] if len(parts) > 2 else ""
        location = parts[3] if len(parts) > 3 else ""
        results = _opp_seeker.search_grants(entity_type, purpose, location)
        if not results:
            return "No grants found. Try adjusting your search criteria."
        listing = _opp_seeker.format_opportunity_list(results, "Grants & Funding")
        ai_tip = _ai_chat(
            "You are a grant writing advisor. Give short, practical advice.",
            f"Give 2-3 brief tips for writing a winning grant proposal for '{purpose or 'general purpose'}' grants in '{location or 'any location'}'.",
        )
        return f"{listing}\n\n---\n\n**Grant Writing Tips:**\n\n{ai_tip}"

    # ---- scholarships ----
    if sub == "scholarships":
        level = parts[1] if len(parts) > 1 else ""
        field = parts[2] if len(parts) > 2 else ""
        country = parts[3] if len(parts) > 3 else ""
        results = _opp_seeker.search_scholarships(level, field, country)
        if not results:
            return "No scholarships found. Try broadening your search."
        listing = _opp_seeker.format_opportunity_list(results, "Scholarships & Bursaries")
        ai_tip = _ai_chat(
            "You are an education advisor. Give short, practical advice.",
            f"Give 2-3 brief tips for winning scholarships at '{level or 'any'}' level in '{field or 'any field'}' for '{country or 'any country'}'.",
        )
        return f"{listing}\n\n---\n\n**Scholarship Tips:**\n\n{ai_tip}"

    # ---- network ----
    if sub == "network":
        topic = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        date_range = parts[3] if len(parts) > 3 else ""
        if not topic:
            return "Usage: /opps network <topic> [location] [date_range]\nExample: /opps network technology Johannesburg"
        results = _opp_seeker.search_networking_events(topic, location, date_range)
        if not results:
            return f"No networking events found for '{topic}'."
        listing = _opp_seeker.format_opportunity_list(results, f"Networking Events: {topic}")
        ai_tip = _ai_chat(
            "You are a networking coach. Give short, actionable advice.",
            f"Give 2-3 brief tips for effective networking at '{topic}' events in '{location or 'any location'}'.",
        )
        return f"{listing}\n\n---\n\n**Networking Tips:**\n\n{ai_tip}"

    # ---- match ----
    if sub == "match":
        print_section("Opportunity Matching")
        print_info("Building your profile and scanning for matches...")
        # Build profile from memory / defaults
        profile = {
            "skills": [],
            "interests": [],
            "location": "",
            "experience_level": "",
            "goals": "",
        }
        # Try to load from memory
        try:
            mem = get_memory(key="user_profile")
            if mem:
                import json as _json
                profile.update(_json.loads(mem["value"]))
        except Exception:
            pass
        results = _opp_seeker.match_opportunities(profile)
        if not results:
            return "No matching opportunities found. Try setting your profile with /memory set user_profile={...}"
        listing = _opp_seeker.format_opportunity_list(results, "Matched Opportunities")
        ai_tip = _ai_chat(
            "You are a career strategist. Give short, personalised advice.",
            f"Based on a profile with skills {profile['skills'] or ['not set']}, interests {profile['interests'] or ['not set']}, "
            f"location '{profile['location'] or 'not set'}', and goals '{profile['goals'] or 'not set'}', "
            f"give 2-3 brief recommendations for improving their profile to find better opportunities.",
        )
        return f"{listing}\n\n---\n\n**Profile Recommendations:**\n\n{ai_tip}"

    # ---- saved ----
    if sub == "saved":
        results = _opp_seeker.get_saved_opportunities()
        if not results:
            return "No saved opportunities. Use /opps to browse and save interesting listings."
        return _opp_seeker.format_opportunity_list(results, "Saved Opportunities")

    # ---- AI fallback for unknown subcommands ----
    print_info(f"Opps subcommand '{sub}' not recognised — consulting AI …")
    return _ai_chat(
        "You are an opportunity discovery assistant. Help users find jobs, grants, "
        "tenders, scholarships, investments, networking events, and business opportunities. "
        "Be concise and action-oriented.",
        f"The user asked about '{sub}' with args: {args}. Provide helpful guidance about finding opportunities related to this topic.",
    )


def handle_scam(args: str) -> str:
    """Handle ``/scam`` — scam / fraud detection analysis."""
    if not args.strip():
        return "Usage: /scam <text to analyse>"

    print_section("Scam Detection")
    loading_animation("Analysing for scam indicators …", duration=1.5)

    # Store the report and get AI analysis
    report_id = save_scam_report(
        scam_type="user_submitted",
        description=args,
        indicators=["AI analysis pending"],
    )

    system = (
        "You are a fraud prevention expert. Analyze the provided text for scam indicators, "
        "explain the red flags found, and provide safety advice. Be thorough but practical. "
        "Structure your response with: 1) Overall risk assessment, 2) Specific red flags identified, "
        "3) Safety recommendations, 4) What to do if already a victim."
    )
    ai_analysis = _ai_chat(system, f"Analyze this text for scam/fraud indicators:\n\n{args}")

    result = (
        f"Scam analysis report #{report_id} for: **{truncate_text(args, 80)}**\n\n"
        f"{ai_analysis}"
    )
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

    system = (
        "You are an adaptive learning tutor. Create structured lesson plans with clear "
        "explanations, examples, exercises, and assessments. Adjust complexity to the "
        "learner's needs. Include: 1) Overview of the topic, 2) Learning objectives, "
        "3) Core concepts with examples, 4) Practical exercises, 5) Assessment questions, "
        "6) Next steps and further resources."
    )
    user_msg = f"Create a structured learning path for: {args}\n\nCurrent level: {level}\nLessons completed: {len(lessons)}"
    return _ai_chat(system, user_msg)


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
  /tax <subcmd>       International tax knowledge base & calculators
  /opps <subcmd>      Discover jobs, grants, tenders, investments, scholarships
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
    "tax": handle_tax,
    "opps": handle_opportunities,
    "opportunities": handle_opportunities,
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
