"""Omega AI v3 — Citation Engine
Source verification and citation formatting.
"""
from __future__ import annotations

import urllib.request
from datetime import datetime, timezone
from typing import Any

from utils import colorize, Colors, truncate_text


CITATION_TEMPLATE = "[Source: {source} — {title}, as of {date}]"


def verify_source(url: str, timeout: int = 10) -> dict[str, Any]:
    """Check if a URL is accessible. Returns status dict."""
    result: dict[str, Any] = {"url": url, "accessible": False, "status": 0, "error": None}
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["accessible"] = True
            result["status"] = resp.status
    except Exception as e:
        result["error"] = str(e)
    return result


def format_citation(source: str, title: str = "", date: str = "") -> str:
    """Format a single citation."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not title:
        title = source
    return CITATION_TEMPLATE.format(source=source, title=title, date=date)


def format_citations(sources: list[dict[str, str]]) -> str:
    """Format multiple sources into a citation block."""
    if not sources:
        return ""
    lines = ["\n\n" + colorize("─" * 50, Colors.DIM), colorize("📚 Sources:", Colors.BOLD)]
    for i, src in enumerate(sources, 1):
        title = src.get("title", src.get("source", "Unknown"))
        link = src.get("link", src.get("url", ""))
        source_name = src.get("source", src.get("domain", "Web"))
        date = src.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        lines.append(f"  {i}. {colorize(title, Colors.CYAN)}")
        if link:
            lines.append(f"     {colorize(link, Colors.DIM)}")
        lines.append(f"     {colorize(format_citation(source_name, title, date), Colors.DIM)}")
    lines.append(colorize("─" * 50, Colors.DIM))
    return "\n".join(lines)


def add_citation(response: str, sources: list[dict[str, str]]) -> str:
    """Append citation block to a response."""
    return response + format_citations(sources)


if __name__ == "__main__":
    sources = [
        {"title": "Bitcoin Mining Guide 2026", "link": "https://example.com/btc", "source": "Example Mining", "date": "2026-07-01"},
        {"title": "Crypto Tax Regulations", "link": "https://example.com/tax", "source": "Tax Authority", "date": "2026-06-15"},
    ]
    response = "Bitcoin mining profitability depends on several factors."
    print(add_citation(response, sources))
