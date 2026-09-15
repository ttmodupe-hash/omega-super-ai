"""Omega AI v3 — Opportunity Engine
Detects business, investment, and market opportunities.
"""
from __future__ import annotations

from typing import Any

from web_search import WebSearch
from local_llm import LLM
from utils import Spinner, colorize, Colors


class OpportunityEngine:
    """Engine for discovering and analyzing opportunities."""

    AFRICAN_SECTORS = [
        "AgriTech & Food Processing", "FinTech & Mobile Payments", "Renewable Energy",
        "E-commerce & Logistics", "HealthTech & Telemedicine", "EdTech & E-learning",
        "Clean Water & Sanitation", "Affordable Housing", "Waste Management & Recycling",
        "Digital Infrastructure", "Tourism & Hospitality", "Mining Technology",
        "Manufacturing & Industry 4.0", "Transportation & Mobility", "Creative Industries",
    ]

    def __init__(self) -> None:
        self.search = WebSearch()
        self.llm = LLM()

    def seek_opportunities(self, domain: str = "", location: str = "") -> list[dict[str, Any]]:
        """Search for business/investment opportunities."""
        query = f"business opportunities {domain}" if domain else "business opportunities 2026"
        if location:
            query += f" {location}"

        with Spinner("Scanning for opportunities"):
            results = self.search.search(query, num_results=8)

        opportunities = []
        for r in results:
            opp = {
                "title": r.get("title", ""),
                "description": r.get("snippet", ""),
                "source": r.get("source", ""),
                "link": r.get("link", ""),
                "market_size": "Research required",
                "entry_barriers": "Medium",
                "risk_level": "Medium",
            }
            opportunities.append(opp)

        return opportunities

    def analyze_trend(self, topic: str) -> dict[str, Any]:
        """Research emerging trends in a sector."""
        with Spinner(f"Analyzing trend: {topic}"):
            news = self.search.news_search(topic, num_results=5)
            web = self.search.search(topic, num_results=3)

        sources = news + web
        trend_summary = f"Trend analysis for '{topic}':\n\n"
        for s in sources[:5]:
            trend_summary += f"- {s.get('title')}: {s.get('snippet')}\n"

        if self.llm.provider in ("ollama", "openai"):
            trend_summary = self.llm.chat(
                f"Analyze the trend '{topic}' based on these sources:\n{trend_summary}\n\nProvide: trend direction, growth rate, key drivers, risks.",
                system_prompt="You are a market analyst.",
            )

        return {
            "topic": topic,
            "summary": trend_summary,
            "sources": sources,
            "direction": "Upward" if any(w in trend_summary.lower() for w in ["growth", "rising", "boom"]) else "Mixed",
        }

    def market_gaps(self, industry: str) -> list[dict[str, Any]]:
        """Identify underserved market segments."""
        query = f"underserved market segments {industry} gaps"
        results = self.search.search(query, num_results=5)

        gaps = []
        for r in results:
            gaps.append({
                "segment": r.get("title", ""),
                "opportunity": r.get("snippet", ""),
                "source": r.get("source", ""),
                "link": r.get("link", ""),
            })
        return gaps

    def african_opportunities(self, country: str = "") -> list[dict[str, Any]]:
        """Specific focus on African markets."""
        location = country if country else "Africa"
        query = f"investment opportunities {location} 2026"

        with Spinner(f"Scanning {location}"):
            results = self.search.search(query, num_results=8)

        opportunities = []
        for r in results:
            opportunities.append({
                "title": r.get("title", ""),
                "description": r.get("snippet", ""),
                "source": r.get("source", ""),
                "link": r.get("link", ""),
                "location": location,
                "sectors": self._detect_sectors(r.get("snippet", "")),
            })

        opportunities.append({
            "title": f"Key Sectors in {location}",
            "description": "Top growth sectors: " + ", ".join(self.AFRICAN_SECTORS[:8]),
            "source": "Luqi-AI Analysis",
            "link": "",
            "location": location,
            "sectors": self.AFRICAN_SECTORS[:8],
        })

        return opportunities

    def suggest_partnerships(self, sector: str) -> list[dict[str, Any]]:
        """Suggest partnership/collaboration ideas."""
        query = f"partnership opportunities {sector} collaboration 2026"
        results = self.search.search(query, num_results=5)

        return [{
            "idea": r.get("title", ""),
            "description": r.get("snippet", ""),
            "source": r.get("source", ""),
            "link": r.get("link", ""),
        } for r in results]

    def _detect_sectors(self, text: str) -> list[str]:
        """Detect which sectors are mentioned in text."""
        text_lower = text.lower()
        found = []
        for sector in self.AFRICAN_SECTORS:
            if any(word in text_lower for word in sector.lower().split(" & ")):
                found.append(sector)
        return found if found else ["General"]


if __name__ == "__main__":
    engine = OpportunityEngine()
    ops = engine.african_opportunities("South Africa")
    for op in ops[:3]:
        print(f"- {op['title']} ({op.get('location', '')})")
