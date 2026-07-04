#!/usr/bin/env python3
"""
Omega Super AI v10 — Multi-Agent Deep Research Swarm
======================================================
Performs deep multi-angle research by:
1. Planning research angles via LLM
2. Executing parallel searches for each angle
3. Fetching and extracting content
4. Cross-referencing findings
5. Synthesizing comprehensive answers
6. Identifying knowledge gaps and contradictions
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from omega.search_engines import unified_search
from omega.content_extractor import (
    analyze_content,
    extract_entities,
    extract_key_facts,
    summarize_content,
)


# ---------------------------------------------------------------------------
# ResearchSwarm
# ---------------------------------------------------------------------------


class ResearchSwarm:
    """
    Orchestrates deep multi-angle research using parallel search,
    content extraction, and LLM-powered synthesis.
    """

    def __init__(self, serper_api_key: str, openai_client: Any) -> None:
        """
        Initialize the ResearchSwarm.

        Parameters
        ----------
        serper_api_key: API key for Google Serper (Serper.dev).
        openai_client: An OpenAI-compatible client with ``chat.completions.create``.
        """
        self.serper_api_key = serper_api_key
        self.client = openai_client
        self._search_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _llm_chat(messages: list[dict[str, str]], client: Any, model: str = "gpt-4o", temperature: float = 0.3, max_tokens: int = 2_000) -> str:
        """Call the LLM and return the text content, or empty string on failure."""
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            return ""

    @staticmethod
    def _safe_json_parse(text: str) -> Any:
        """Try to extract and parse JSON from an LLM response."""
        # Try direct parse first
        try:
            return json.loads(text)
        except Exception:
            pass
        # Try extracting JSON block
        match = __import__("re").search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        # Try finding array or object directly
        match = __import__("re").search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_research(self, query: str) -> list[str]:
        """
        Use the LLM to break a query into 3-5 research angles / sub-questions.

        Parameters
        ----------
        query: The main research question.

        Returns
        -------
        List of sub-question strings.
        """
        system_prompt = (
            "You are an expert research planner. Given a research question, "
            "break it down into 3-5 distinct research angles or sub-questions "
            "that, when answered together, provide a comprehensive answer. "
            "Each angle should explore a different facet of the topic. "
            "Return ONLY a JSON array of strings."
        )
        user_prompt = f"Research question: {query}\n\nProvide 3-5 research angles as a JSON array."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = self._llm_chat(messages, self.client, max_tokens=1_000, temperature=0.4)

        parsed = self._safe_json_parse(response)
        if isinstance(parsed, list) and len(parsed) >= 2:
            return [str(a).strip() for a in parsed if str(a).strip()]

        # Fallback: generate generic angles
        return [
            f"What is {query}?",
            f"How does {query} work?",
            f"What are the latest developments in {query}?",
            f"What are the main challenges or controversies around {query}?",
            f"What do experts say about {query}?",
        ]

    def execute_research(self, query: str, depth: int = 3) -> dict[str, Any]:
        """
        Execute deep multi-angle research.

        Parameters
        ----------
        query: The main research question.
        depth: Number of top results per angle to fetch full content for.

        Returns
        -------
        dict with plan, angles, synthesis, sources, confidence_score,
        knowledge_gaps, and contradictions.
        """
        if not query or not query.strip():
            return {
                "query": query,
                "plan": [],
                "angles": [],
                "synthesis": "Empty query provided.",
                "sources": [],
                "confidence_score": 0,
                "knowledge_gaps": ["No query to research."],
                "contradictions": [],
            }

        # Step 1: Plan research angles
        angles = self.plan_research(query)

        # Step 2: Search each angle in parallel
        angle_results: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(len(angles), 5)) as pool:
            futures = {}
            for angle in angles:
                futures[pool.submit(unified_search, angle, self.serper_api_key, 10)] = angle

            for future in as_completed(futures):
                angle = futures[future]
                try:
                    angle_results[angle] = future.result(timeout=60)
                except Exception as exc:
                    angle_results[angle] = {
                        "query": angle,
                        "results": [],
                        "sources": [],
                        "summary": f"Error: {exc}",
                        "engines_used": [],
                        "from_cache": False,
                    }

        # Step 3: Fetch and extract content for top results per angle
        angles_data: list[dict[str, Any]] = []
        all_sources: list[dict[str, Any]] = []

        for angle in angles:
            search_data = angle_results.get(angle, {})
            results = search_data.get("results", [])[:depth]

            fetched_findings: list[str] = []
            for r in results:
                link = r.get("link", "")
                if link and link.startswith("http"):
                    try:
                        analysis = analyze_content(link, timeout=8)
                        r["full_content"] = analysis.get("content", "")
                        r["facts"] = analysis.get("facts", [])
                        r["summary"] = analysis.get("summary", "")
                        if analysis.get("content"):
                            fetched_findings.append(analysis["content"][:1000])
                    except Exception:
                        pass
                all_sources.append({
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                    "relevance": r.get("quality_score", 50),
                    "angle": angle,
                })

            # Extract key findings from snippets + fetched content
            combined_text = " ".join(
                [r.get("snippet", "") for r in results] + fetched_findings
            )
            key_findings = extract_key_facts(combined_text, max_facts=8)

            angles_data.append({
                "angle": angle,
                "results": results,
                "key_findings": key_findings,
            })

        # Step 4: Cross-reference findings between angles
        cross_refs = self._cross_reference(angles_data)

        # Step 5: Synthesize comprehensive answer
        synthesis = self._synthesize(query, angles, angles_data, cross_refs)

        # Step 6: Identify knowledge gaps and contradictions
        gaps = self._identify_gaps(query, angles_data)
        contradictions = self._find_contradictions(angles_data)

        # Calculate confidence score
        confidence = self._calculate_confidence(angles_data, len(all_sources), contradictions)

        result = {
            "query": query,
            "plan": angles,
            "angles": angles_data,
            "synthesis": synthesis,
            "sources": all_sources,
            "confidence_score": confidence,
            "knowledge_gaps": gaps,
            "contradictions": contradictions,
        }

        self._search_history.append({
            "query": query,
            "timestamp": time.time(),
            "angles_count": len(angles),
            "sources_count": len(all_sources),
        })

        return result

    def quick_search(self, query: str) -> dict[str, Any]:
        """
        Fast single-search for simple queries.

        Parameters
        ----------
        query: The search query.

        Returns
        -------
        dict with unified search results and a brief synthesis.
        """
        search_data = unified_search(query, self.serper_api_key, max_results=10)

        synthesis = ""
        if self.client:
            system_prompt = (
                "You are a research assistant. Provide a brief, accurate summary "
                "of the search results in 2-3 sentences. Be concise and factual."
            )
            user_prompt = f"Query: {query}\n\nSearch results:\n"
            for r in search_data.get("results", [])[:5]:
                user_prompt += f"- {r.get('title', '')}: {r.get('snippet', '')}\n"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            synthesis = self._llm_chat(messages, self.client, max_tokens=500, temperature=0.3)

        return {
            "query": query,
            "results": search_data.get("results", []),
            "sources": search_data.get("sources", []),
            "synthesis": synthesis or search_data.get("summary", ""),
            "engines_used": search_data.get("engines_used", []),
            "from_cache": search_data.get("from_cache", False),
        }

    def deep_dive(self, query: str, iterations: int = 3) -> dict[str, Any]:
        """
        Iterative deep research: search -> analyze -> identify gaps -> search again.

        Parameters
        ----------
        query: The research question.
        iterations: Number of research iterations (default 3).

        Returns
        -------
        dict with iterative research results, synthesis, and metadata.
        """
        all_angles_data: list[dict[str, Any]] = []
        all_sources: list[dict[str, Any]] = []
        all_gaps: list[str] = []
        iteration_results: list[dict[str, Any]] = []

        current_query = query
        for iteration in range(1, iterations + 1):
            # Execute research for current query/angles
            result = self.execute_research(current_query, depth=3)

            iteration_results.append({
                "iteration": iteration,
                "query": current_query,
                "angles_count": len(result.get("plan", [])),
                "sources_count": len(result.get("sources", [])),
                "confidence": result.get("confidence_score", 0),
            })

            all_angles_data.extend(result.get("angles", []))
            all_sources.extend(result.get("sources", []))
            gaps = result.get("knowledge_gaps", [])
            all_gaps.extend(gaps)

            # Use gaps to form next iteration's query
            if iteration < iterations and gaps and self.client:
                gap_text = "; ".join(gaps[:3])
                system_prompt = (
                    "You are a research strategist. Given the original question "
                    "and identified knowledge gaps, formulate a focused follow-up "
                    "research query to fill the most important gaps. "
                    "Return ONLY the new query string, nothing else."
                )
                user_prompt = (
                    f"Original question: {query}\n"
                    f"Knowledge gaps: {gap_text}\n"
                    f"Formulate a focused follow-up research query."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                new_query = self._llm_chat(messages, self.client, max_tokens=200, temperature=0.4)
                if new_query and new_query.strip() and new_query.strip().lower() != current_query.lower():
                    current_query = new_query.strip()
                else:
                    break  # No new angles, stop iterating
            else:
                break

        # Deduplicate sources
        seen_links: set[str] = set()
        unique_sources: list[dict[str, Any]] = []
        for s in all_sources:
            link = s.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                unique_sources.append(s)

        # Final synthesis across all iterations
        final_synthesis = self._synthesize_multi_iteration(query, all_angles_data, iteration_results)

        # Calculate final confidence
        final_confidence = self._calculate_confidence(all_angles_data, len(unique_sources), [])

        return {
            "query": query,
            "iterations": iteration_results,
            "angles": all_angles_data,
            "synthesis": final_synthesis,
            "sources": unique_sources,
            "confidence_score": min(final_confidence + (iterations - 1) * 5, 100),
            "knowledge_gaps": list(set(all_gaps))[:10],
            "contradictions": self._find_contradictions(all_angles_data),
        }

    # ------------------------------------------------------------------
    # Private synthesis / analysis helpers
    # ------------------------------------------------------------------

    def _cross_reference(self, angles_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find overlapping findings between research angles."""
        cross_refs: list[dict[str, Any]] = []
        for i, angle_a in enumerate(angles_data):
            for j, angle_b in enumerate(angles_data):
                if i >= j:
                    continue
                findings_a = set(a.lower() for a in angle_a.get("key_findings", []))
                findings_b = set(b.lower() for b in angle_b.get("key_findings", []))
                overlap = findings_a & findings_b
                if overlap:
                    cross_refs.append({
                        "angle_1": angle_a["angle"],
                        "angle_2": angle_b["angle"],
                        "overlapping_findings": list(overlap)[:5],
                    })
        return cross_refs

    def _synthesize(
        self,
        query: str,
        angles: list[str],
        angles_data: list[dict[str, Any]],
        cross_refs: list[dict[str, Any]],
    ) -> str:
        """Use the LLM to synthesize a comprehensive answer."""
        if not self.client:
            # Fallback: concatenate key findings
            parts = [f"Research on: {query}\n"]
            for ad in angles_data:
                parts.append(f"\n--- {ad['angle']} ---")
                for f in ad.get("key_findings", [])[:5]:
                    parts.append(f"  • {f}")
            return "\n".join(parts)

        # Build context for LLM
        context = f"Research question: {query}\n\nResearch angles explored:\n"
        for i, ad in enumerate(angles_data, 1):
            context += f"\n{i}. {ad['angle']}\n"
            context += "Key findings:\n"
            for finding in ad.get("key_findings", [])[:5]:
                context += f"  - {finding}\n"
            context += "Sources:\n"
            for r in ad.get("results", [])[:3]:
                context += f"  • {r.get('title', '')} ({r.get('link', '')})\n"

        if cross_refs:
            context += "\nCross-referenced findings between angles:\n"
            for cr in cross_refs[:5]:
                context += f"  - Between '{cr['angle_1']}' and '{cr['angle_2']}': "
                context += f"{', '.join(cr['overlapping_findings'][:3])}\n"

        system_prompt = (
            "You are an expert research synthesizer. Given research findings from "
            "multiple angles, provide a comprehensive, well-structured answer. "
            "Organize your response with clear sections. Cite specific findings. "
            "Be balanced, mention uncertainties, and highlight key insights. "
            "Write in a professional, authoritative tone."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]

        return self._llm_chat(messages, self.client, max_tokens=3_000, temperature=0.3)

    def _synthesize_multi_iteration(
        self,
        query: str,
        angles_data: list[dict[str, Any]],
        iteration_results: list[dict[str, Any]],
    ) -> str:
        """Synthesize results across multiple research iterations."""
        if not self.client:
            parts = [f"Deep research on: {query}"]
            for ir in iteration_results:
                parts.append(f"\nIteration {ir['iteration']}: {ir['query']}")
                parts.append(f"  Sources: {ir['sources_count']}, Confidence: {ir['confidence']}%")
            return "\n".join(parts)

        context = f"Deep research question: {query}\n\n"
        context += f"Research conducted over {len(iteration_results)} iterations:\n"
        for ir in iteration_results:
            context += f"\nIteration {ir['iteration']}: {ir['query']}\n"
            context += f"  - Sources found: {ir['sources_count']}\n"
            context += f"  - Confidence: {ir['confidence']}%\n"

        context += "\nKey findings across all iterations:\n"
        seen_findings: set[str] = set()
        for ad in angles_data:
            for finding in ad.get("key_findings", []):
                key = finding.lower()[:80]
                if key not in seen_findings:
                    seen_findings.add(key)
                    context += f"  • {finding}\n"

        system_prompt = (
            "You are an expert research synthesizer who has conducted multi-iteration "
            "deep research. Provide a comprehensive final report that integrates findings "
            "from all research iterations. Structure with: Executive Summary, Key Findings, "
            "Detailed Analysis, and Conclusions. Be thorough, balanced, and cite specific "
            "discoveries. Note any remaining uncertainties."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]

        return self._llm_chat(messages, self.client, max_tokens=4_000, temperature=0.3)

    def _identify_gaps(self, query: str, angles_data: list[dict[str, Any]]) -> list[str]:
        """Identify knowledge gaps using the LLM."""
        if not self.client:
            return ["LLM client not available for gap analysis."]

        findings_text = ""
        for ad in angles_data:
            findings_text += f"\nAngle: {ad['angle']}\n"
            for f in ad.get("key_findings", []):
                findings_text += f"  - {f}\n"

        system_prompt = (
            "You are a critical research analyst. Given research findings, identify "
            "the most important knowledge gaps — questions that remain unanswered or "
            "areas that need deeper investigation. Return ONLY a JSON array of strings."
        )
        user_prompt = f"Research question: {query}\n\nFindings:{findings_text}\n\nIdentify knowledge gaps as JSON array."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self._llm_chat(messages, self.client, max_tokens=1_000, temperature=0.3)
        parsed = self._safe_json_parse(response)
        if isinstance(parsed, list) and len(parsed) > 0:
            return [str(g).strip() for g in parsed if str(g).strip()]

        return ["No significant gaps identified by automated analysis."]

    def _find_contradictions(self, angles_data: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Find contradictions between different research angles."""
        contradictions: list[dict[str, str]] = []

        # Collect all findings with their angles
        all_findings: list[tuple[str, str]] = []
        for ad in angles_data:
            for f in ad.get("key_findings", []):
                all_findings.append((ad["angle"], f))

        # Look for contradiction patterns
        contradiction_patterns = [
            (r"\bincreased\b|\brose\b|\bgrew\b|\bwent up\b", r"\bdecreased\b|\bfell\b|\bdropped\b|\bwent down\b"),
            (r"\bsupports\b|\bconfirms\b|\bvalidates\b", r"\brefutes\b|\bdisproves\b|\bcontradicts\b"),
            (r"\bpositive\b|\bbeneficial\b|\badvantageous\b", r"\bnegative\b|\bharmful\b|\bdetrimental\b"),
            (r"\bsuccessful\b|\beffective\b|\bworks\b", r"\bunsuccessful\b|\bineffective\b|\bfailed\b"),
            (r"\bhigh\b|\blarge\b|\bsignificant\b", r"\blow\b|\bsmall\b|\binsignificant\b"),
        ]

        checked_pairs: set[tuple[int, int]] = set()
        for i, (angle_a, finding_a) in enumerate(all_findings):
            for j, (angle_b, finding_b) in enumerate(all_findings):
                if i >= j or (i, j) in checked_pairs:
                    continue
                checked_pairs.add((i, j))

                # Check for topic overlap (simple word overlap)
                words_a = set(__import__("re").findall(r"\b\w{5,}\b", finding_a.lower()))
                words_b = set(__import__("re").findall(r"\b\w{5,}\b", finding_b.lower()))
                if len(words_a & words_b) < 2:
                    continue

                for pos_pat, neg_pat in contradiction_patterns:
                    a_positive = bool(__import__("re").search(pos_pat, finding_a, __import__("re").IGNORECASE))
                    a_negative = bool(__import__("re").search(neg_pat, finding_a, __import__("re").IGNORECASE))
                    b_positive = bool(__import__("re").search(pos_pat, finding_b, __import__("re").IGNORECASE))
                    b_negative = bool(__import__("re").search(neg_pat, finding_b, __import__("re").IGNORECASE))

                    if (a_positive and b_negative) or (a_negative and b_positive):
                        contradictions.append({
                            "angle_a": angle_a,
                            "finding_a": finding_a[:200],
                            "angle_b": angle_b,
                            "finding_b": finding_b[:200],
                            "type": "directional_contradiction",
                        })
                        break

        return contradictions

    def _calculate_confidence(
        self,
        angles_data: list[dict[str, Any]],
        total_sources: int,
        contradictions: list[dict[str, str]],
    ) -> int:
        """Calculate a confidence score (0-100) based on research breadth and consistency."""
        score = 0

        # Points for number of angles with findings
        angles_with_findings = sum(
            1 for ad in angles_data if ad.get("key_findings")
        )
        score += min(angles_with_findings * 15, 45)

        # Points for source diversity
        if total_sources >= 10:
            score += 25
        elif total_sources >= 5:
            score += 15
        elif total_sources >= 3:
            score += 10
        else:
            score += 5

        # Points for total findings
        total_findings = sum(len(ad.get("key_findings", [])) for ad in angles_data)
        score += min(total_findings * 2, 20)

        # Penalty for contradictions
        score -= min(len(contradictions) * 10, 30)

        # Cross-reference bonus
        cross_ref_bonus = 0
        for i, ad_i in enumerate(angles_data):
            for j, ad_j in enumerate(angles_data):
                if i >= j:
                    continue
                fi = set(f.lower() for f in ad_i.get("key_findings", []))
                fj = set(f.lower() for f in ad_j.get("key_findings", []))
                if fi & fj:
                    cross_ref_bonus += 3
        score += min(cross_ref_bonus, 15)

        return max(0, min(score, 100))
