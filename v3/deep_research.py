"""Omega AI v3 — Deep Research Swarm
Multi-dimensional research with citation tracking.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from config import CONFIG
from utils import Spinner, colorize, Colors
from web_search import WebSearch
from local_llm import LLM
from citation_engine import format_citations


class DeepResearch:
    """Multi-agent deep research orchestrator."""

    def __init__(self) -> None:
        self.search = WebSearch()
        self.llm = LLM()

    def research(self, query: str, depth: str = "deep") -> dict[str, Any]:
        """Main research entry point."""
        with Spinner(f"Researching: {query[:40]}..."):
            sub_queries = self.generate_sub_queries(query, depth)
            all_sources: list[dict] = []
            details: list[str] = []

            # Wide search on main query
            main_results = self.search.search(query, num_results=5)
            all_sources.extend(main_results)

            # Deep dive on sub-queries
            if depth in ("deep", "comprehensive"):
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(self._search_sub, sq) for sq in sub_queries]
                    for future in futures:
                        srcs, detail = future.result()
                        all_sources.extend(srcs)
                        details.append(detail)

            # Cross-verify and synthesize
            sources = self._deduplicate(all_sources)
            summary = self.synthesize_findings(details, query, sources)
            cited_response = summary + format_citations(sources)

            return {
                "summary": summary,
                "cited_response": cited_response,
                "sources": sources,
                "sub_queries": sub_queries,
                "details": details,
            }

    def generate_sub_queries(self, main_query: str, depth: str = "deep") -> list[str]:
        """Break query into sub-queries for investigation."""
        q = main_query.lower()
        sub_queries = []

        historical = any(w in q for w in ["history", "evolution", "past", "origin", "timeline", "background", "stone age"])
        comparative = any(w in q for w in ["compare", "versus", "vs", "difference", "better"])
        how_to = any(w in q for w in ["how to", "guide", "steps", "tutorial", "setup"])
        current = any(w in q for w in ["current", "latest", "2026", "now", "today", "trend"])

        if depth == "quick":
            sub_queries = [main_query]
        elif depth == "deep":
            sub_queries = [main_query]
            if historical:
                sub_queries.append(f"history and evolution of {main_query}")
            if comparative:
                sub_queries.append(f"comparison and analysis of {main_query}")
            if how_to:
                sub_queries.append(f"step by step guide for {main_query}")
            if current or not historical:
                sub_queries.append(f"latest developments in {main_query} 2026")
            sub_queries.append(f"expert analysis and key facts about {main_query}")
        else:  # comprehensive
            sub_queries = [
                main_query,
                f"history and evolution of {main_query}",
                f"current state and latest developments of {main_query}",
                f"expert opinions and analysis on {main_query}",
                f"statistics and data about {main_query}",
                f"future trends and predictions for {main_query}",
                f"common misconceptions about {main_query}",
                f"practical applications of {main_query}",
            ]

        return sub_queries[:6] if depth == "comprehensive" else sub_queries[:4]

    def synthesize_findings(self, details: list[str], query: str, sources: list[dict]) -> str:
        """Combine findings into coherent response."""
        if self.llm.provider in ("ollama", "openai"):
            prompt = self._build_synthesis_prompt(query, details, sources)
            return self.llm.chat(prompt, system_prompt="You are a research analyst. Synthesize findings into a clear, well-structured response with sections. Be factual and cite sources.")

        parts = [f"## Research: {query}\n"]
        parts.append("Based on available sources, here are the key findings:\n")

        for i, src in enumerate(sources[:5], 1):
            parts.append(f"{i}. **{src.get('title', 'Source')}**: {src.get('snippet', 'No details')}")

        if not sources:
            parts.append("No external sources found. This is a general knowledge topic.")

        parts.append("\n*Note: Connect an LLM (Ollama/OpenAI) for deeper synthesis.*")
        return "\n".join(parts)

    def _build_synthesis_prompt(self, query: str, details: list[str], sources: list[dict]) -> str:
        """Build prompt for LLM synthesis."""
        source_text = "\n".join(f"- {s.get('title')}: {s.get('snippet')}" for s in sources[:8])
        detail_text = "\n\n".join(d for d in details if d)
        return f"""Synthesize the following research findings into a clear, comprehensive response.

Query: {query}

Source Data:
{source_text}

Sub-query Results:
{detail_text}

Provide a well-structured response with:
1. Key findings summary
2. Important details and context
3. Any conflicting information or caveats
Keep it factual and concise."""

    def _search_sub(self, sub_query: str) -> tuple[list[dict], str]:
        """Search a sub-query and return sources + detail."""
        results = self.search.search(sub_query, num_results=3)
        detail = f"## {sub_query}\n"
        for r in results:
            detail += f"- {r.get('title')}: {r.get('snippet')}\n"
        return results, detail

    def _deduplicate(self, sources: list[dict]) -> list[dict]:
        """Remove duplicate sources by link."""
        seen = set()
        unique = []
        for s in sources:
            link = s.get("link", "")
            if link and link in seen:
                continue
            seen.add(link)
            unique.append(s)
        return unique


def deep_research(query: str, depth: str = "deep") -> dict[str, Any]:
    """Convenience function for deep research."""
    dr = DeepResearch()
    return dr.research(query, depth)


if __name__ == "__main__":
    result = deep_research("Bitcoin mining profitability South Africa", depth="deep")
    print(result["cited_response"][:1500])
