"""Capability Gap Analyzer for identifying weaknesses and opportunities.

Analyzes Luqi AI's current capabilities against competitors to identify
gaps and prioritize improvements.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Capability categories
CAPABILITY_CATEGORIES = [
    "conversation_quality", "reasoning_depth", "code_generation",
    "multilingual_support", "web_search", "file_processing",
    "image_generation", "image_analysis", "voice_support",
    "memory_persistence", "agentic_workflows", "education_features",
    "offline_capability", "privacy_protection", "cost_efficiency",
    "speed_latency", "african_languages", "virtual_labs",
    "document_generation", "data_analysis",
]

CAPABILITY_LABELS = {
    "conversation_quality": "Conversation Quality",
    "reasoning_depth": "Reasoning Depth",
    "code_generation": "Code Generation",
    "multilingual_support": "Multilingual Support",
    "web_search": "Web Search",
    "file_processing": "File Processing",
    "image_generation": "Image Generation",
    "image_analysis": "Image Analysis",
    "voice_support": "Voice Support (TTS/STT)",
    "memory_persistence": "Memory Persistence",
    "agentic_workflows": "Agentic Workflows",
    "education_features": "Education Features",
    "offline_capability": "Offline Capability",
    "privacy_protection": "Privacy Protection",
    "cost_efficiency": "Cost Efficiency",
    "speed_latency": "Speed / Latency",
    "african_languages": "African Languages",
    "virtual_labs": "Virtual Labs",
    "document_generation": "Document Generation",
    "data_analysis": "Data Analysis",
}

SCORE_MIN = 1
SCORE_MAX = 10
SCORE_DEFAULT = 5

# Weight factors for priority calculation
WEIGHT_GAP_SIZE = 0.35
WEIGHT_STRATEGIC_IMPORTANCE = 0.25
WEIGHT_USER_IMPACT = 0.25
WEIGHT_EASE_OF_IMPLEMENTATION = 0.15

# Competitor data
COMPETITORS = [
    {"name": "ChatGPT (OpenAI)", "url": "https://chat.openai.com"},
    {"name": "Claude (Anthropic)", "url": "https://claude.ai"},
    {"name": "Gemini (Google)", "url": "https://gemini.google.com"},
    {"name": "Llama (Meta)", "url": "https://llama.meta.com"},
    {"name": "DeepSeek", "url": "https://deepseek.com"},
]


@dataclass
class CapabilityScore:
    """Score for a single capability category."""
    category: str
    label: str
    score: int
    evidence: str = ""
    last_updated: str = ""
    trend: str = "stable"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Gap:
    """Identified capability gap."""
    category: str
    current_score: int
    competitor_best: int
    gap_size: int
    priority: float = 0.0
    recommendation: str = ""
    estimated_effort: int = 4
    estimated_impact: int = 5
    ease_of_implementation: int = 5
    strategic_importance: int = 5
    user_impact: int = 5
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompetitorProfile:
    """Profile of a competitor's capabilities."""
    name: str
    url: str
    scores: dict[str, int] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "scores": self.scores,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "last_updated": self.last_updated,
        }


class GapAnalyzer:
    """Analyzes capability gaps between Luqi AI and competitors.

    Provides comprehensive gap analysis including:
    - Current capability assessment
    - Competitor analysis
    - Gap identification
    - Priority ranking
    - Actionable recommendations

    Attributes:
        capability_scores: Current Luqi AI capability scores.
        competitor_profiles: Competitor capability profiles.
        gaps: Identified gaps.
        recommendations: Generated recommendations.
    """

    def __init__(self, competitors: list[str] | None = None) -> None:
        """Initialize the GapAnalyzer.

        Args:
            competitors: Optional list of competitor identifiers.
        """
        self.competitors = competitors or [c["name"] for c in COMPETITORS]
        self.capability_scores: dict[str, CapabilityScore] = {}
        self.competitor_profiles: dict[str, CompetitorProfile] = {}
        self.gaps: list[Gap] = []
        self.recommendations: list[dict[str, Any]] = []
        logger.info("GapAnalyzer initialized with competitors: %s", self.competitors)

    def assess_current_capabilities(self) -> dict[str, CapabilityScore]:
        """Score Luqi AI across all capability categories.

        In a production environment, this would use real benchmarks,
        user feedback, and automated testing. For initialization,
        it uses expert-assessed baseline scores.

        Returns:
            Dictionary mapping category to CapabilityScore.
        """
        logger.info("Assessing current capabilities")

        from datetime import datetime

        # Baseline assessment for Luqi AI
        baseline_scores: dict[str, dict[str, Any]] = {
            "conversation_quality": {
                "score": 7,
                "evidence": "Strong conversational abilities with contextual understanding",
                "trend": "improving",
            },
            "reasoning_depth": {
                "score": 6,
                "evidence": "Good reasoning but struggles with complex multi-step problems",
                "trend": "improving",
            },
            "code_generation": {
                "score": 7,
                "evidence": "Generates functional code in multiple languages",
                "trend": "stable",
            },
            "multilingual_support": {
                "score": 6,
                "evidence": "Supports major languages but limited in regional variants",
                "trend": "improving",
            },
            "web_search": {
                "score": 5,
                "evidence": "Basic web search integration available",
                "trend": "improving",
            },
            "file_processing": {
                "score": 6,
                "evidence": "Can process various file formats",
                "trend": "stable",
            },
            "image_generation": {
                "score": 4,
                "evidence": "Limited image generation capabilities",
                "trend": "improving",
            },
            "image_analysis": {
                "score": 6,
                "evidence": "Can analyze and describe images",
                "trend": "improving",
            },
            "voice_support": {
                "score": 3,
                "evidence": "No native voice input/output support",
                "trend": "stable",
            },
            "memory_persistence": {
                "score": 5,
                "evidence": "Session-based memory, limited long-term persistence",
                "trend": "improving",
            },
            "agentic_workflows": {
                "score": 5,
                "evidence": "Basic tool calling, limited autonomous agent capabilities",
                "trend": "improving",
            },
            "education_features": {
                "score": 6,
                "evidence": "Good educational explanations and tutoring",
                "trend": "stable",
            },
            "offline_capability": {
                "score": 2,
                "evidence": "Cloud-dependent, no offline mode",
                "trend": "stable",
            },
            "privacy_protection": {
                "score": 6,
                "evidence": "Standard privacy practices, no advanced privacy features",
                "trend": "stable",
            },
            "cost_efficiency": {
                "score": 7,
                "evidence": "Competitive pricing structure",
                "trend": "stable",
            },
            "speed_latency": {
                "score": 7,
                "evidence": "Good response times for most queries",
                "trend": "improving",
            },
            "african_languages": {
                "score": 4,
                "evidence": "Limited support for African languages - key differentiator opportunity",
                "trend": "improving",
            },
            "virtual_labs": {
                "score": 3,
                "evidence": "No virtual lab or simulation environment",
                "trend": "stable",
            },
            "document_generation": {
                "score": 5,
                "evidence": "Basic document creation, limited formatting",
                "trend": "improving",
            },
            "data_analysis": {
                "score": 6,
                "evidence": "Can analyze data and create visualizations",
                "trend": "improving",
            },
        }

        for category in CAPABILITY_CATEGORIES:
            baseline = baseline_scores.get(category, {})
            self.capability_scores[category] = CapabilityScore(
                category=category,
                label=CAPABILITY_LABELS.get(category, category),
                score=baseline.get("score", SCORE_DEFAULT),
                evidence=baseline.get("evidence", "Not yet assessed"),
                last_updated=datetime.now().isoformat(),
                trend=baseline.get("trend", "stable"),
            )

        logger.info(
            "Capability assessment complete: %d categories assessed",
            len(self.capability_scores),
        )
        return self.capability_scores

    def analyze_competitors(self) -> dict[str, CompetitorProfile]:
        """Scrape and analyze competitor features and capabilities.

        In production, this would use web scraping, API calls, and
        benchmark results. For now, uses expert-assessed competitive
        intelligence data.

        Returns:
            Dictionary mapping competitor name to CompetitorProfile.
        """
        logger.info("Analyzing competitors")

        from datetime import datetime

        # Competitive intelligence data
        competitor_data: dict[str, dict[str, Any]] = {
            "ChatGPT (OpenAI)": {
                "scores": {
                    "conversation_quality": 9,
                    "reasoning_depth": 8,
                    "code_generation": 9,
                    "multilingual_support": 7,
                    "web_search": 7,
                    "file_processing": 7,
                    "image_generation": 8,
                    "image_analysis": 8,
                    "voice_support": 6,
                    "memory_persistence": 6,
                    "agentic_workflows": 7,
                    "education_features": 7,
                    "offline_capability": 2,
                    "privacy_protection": 6,
                    "cost_efficiency": 6,
                    "speed_latency": 8,
                    "african_languages": 3,
                    "virtual_labs": 2,
                    "document_generation": 6,
                    "data_analysis": 7,
                },
                "strengths": ["Code generation", "Conversation quality", "Image generation", "Reasoning"],
                "weaknesses": ["African languages", "Offline capability", "Cost for heavy use"],
            },
            "Claude (Anthropic)": {
                "scores": {
                    "conversation_quality": 9,
                    "reasoning_depth": 9,
                    "code_generation": 8,
                    "multilingual_support": 7,
                    "web_search": 6,
                    "file_processing": 8,
                    "image_generation": 5,
                    "image_analysis": 8,
                    "voice_support": 4,
                    "memory_persistence": 5,
                    "agentic_workflows": 7,
                    "education_features": 8,
                    "offline_capability": 2,
                    "privacy_protection": 7,
                    "cost_efficiency": 6,
                    "speed_latency": 7,
                    "african_languages": 3,
                    "virtual_labs": 2,
                    "document_generation": 7,
                    "data_analysis": 7,
                },
                "strengths": ["Reasoning depth", "Safety", "Long context", "Education features"],
                "weaknesses": ["Voice support", "Image generation", "African languages"],
            },
            "Gemini (Google)": {
                "scores": {
                    "conversation_quality": 8,
                    "reasoning_depth": 8,
                    "code_generation": 8,
                    "multilingual_support": 9,
                    "web_search": 9,
                    "file_processing": 8,
                    "image_generation": 7,
                    "image_analysis": 9,
                    "voice_support": 7,
                    "memory_persistence": 6,
                    "agentic_workflows": 7,
                    "education_features": 7,
                    "offline_capability": 4,
                    "privacy_protection": 6,
                    "cost_efficiency": 7,
                    "speed_latency": 8,
                    "african_languages": 5,
                    "virtual_labs": 3,
                    "document_generation": 7,
                    "data_analysis": 8,
                },
                "strengths": ["Multilingual support", "Web search", "Image analysis", "African languages"],
                "weaknesses": ["Virtual labs", "Offline capability", "Privacy concerns"],
            },
            "Llama (Meta)": {
                "scores": {
                    "conversation_quality": 7,
                    "reasoning_depth": 7,
                    "code_generation": 7,
                    "multilingual_support": 6,
                    "web_search": 3,
                    "file_processing": 6,
                    "image_generation": 2,
                    "image_analysis": 5,
                    "voice_support": 3,
                    "memory_persistence": 4,
                    "agentic_workflows": 5,
                    "education_features": 6,
                    "offline_capability": 9,
                    "privacy_protection": 7,
                    "cost_efficiency": 9,
                    "speed_latency": 7,
                    "african_languages": 3,
                    "virtual_labs": 2,
                    "document_generation": 5,
                    "data_analysis": 6,
                },
                "strengths": ["Offline capability", "Cost efficiency", "Open source", "Privacy"],
                "weaknesses": ["Web search", "Image generation", "Voice support", "African languages"],
            },
            "DeepSeek": {
                "scores": {
                    "conversation_quality": 8,
                    "reasoning_depth": 9,
                    "code_generation": 9,
                    "multilingual_support": 6,
                    "web_search": 6,
                    "file_processing": 6,
                    "image_generation": 2,
                    "image_analysis": 5,
                    "voice_support": 3,
                    "memory_persistence": 5,
                    "agentic_workflows": 6,
                    "education_features": 6,
                    "offline_capability": 3,
                    "privacy_protection": 5,
                    "cost_efficiency": 9,
                    "speed_latency": 7,
                    "african_languages": 2,
                    "virtual_labs": 2,
                    "document_generation": 5,
                    "data_analysis": 7,
                },
                "strengths": ["Code generation", "Reasoning", "Cost efficiency"],
                "weaknesses": ["Image generation", "African languages", "Voice support", "Virtual labs"],
            },
        }

        for comp_name, data in competitor_data.items():
            if comp_name not in self.competitors:
                continue
            comp_info = next((c for c in COMPETITORS if c["name"] == comp_name), {"name": comp_name, "url": ""})
            self.competitor_profiles[comp_name] = CompetitorProfile(
                name=comp_name,
                url=comp_info.get("url", ""),
                scores=data.get("scores", {}),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                last_updated=datetime.now().isoformat(),
            )

        logger.info("Competitor analysis complete: %d profiles", len(self.competitor_profiles))
        return self.competitor_profiles

    def identify_gaps(self) -> list[Gap]:
        """Identify capability gaps between Luqi AI and competitors.

        Compares Luqi AI's scores against the best competitor in each
        category to identify significant gaps.

        Returns:
            List of Gap objects sorted by priority.
        """
        logger.info("Identifying capability gaps")

        if not self.capability_scores:
            self.assess_current_capabilities()
        if not self.competitor_profiles:
            self.analyze_competitors()

        self.gaps = []

        for category in CAPABILITY_CATEGORIES:
            current = self.capability_scores.get(category)
            if not current:
                continue

            # Find best competitor score in this category
            best_score = current.score
            best_competitor = "Luqi AI"
            for comp_name, profile in self.competitor_profiles.items():
                comp_score = profile.scores.get(category, 0)
                if comp_score > best_score:
                    best_score = comp_score
                    best_competitor = comp_name

            gap_size = best_score - current.score

            # Only flag significant gaps (>= 2 points)
            if gap_size < 2:
                continue

            # Calculate priority score
            strategic = self._get_strategic_importance(category)
            user_impact = self._get_user_impact(category)
            ease = self._get_ease_of_implementation(category)

            priority = (
                gap_size * WEIGHT_GAP_SIZE +
                strategic * WEIGHT_STRATEGIC_IMPORTANCE +
                user_impact * WEIGHT_USER_IMPACT +
                ease * WEIGHT_EASE_OF_IMPLEMENTATION
            )

            gap = Gap(
                category=category,
                current_score=current.score,
                competitor_best=best_score,
                gap_size=gap_size,
                priority=priority,
                recommendation=self._generate_recommendation(category, gap_size, best_competitor),
                estimated_effort=self._estimate_effort(category),
                estimated_impact=user_impact,
                ease_of_implementation=ease,
                strategic_importance=strategic,
                user_impact=user_impact,
                sources=[best_competitor],
            )
            self.gaps.append(gap)

        # Sort by priority (descending)
        self.gaps.sort(key=lambda g: g.priority, reverse=True)

        logger.info("Gap identification complete: %d gaps found", len(self.gaps))
        return self.gaps

    def _get_strategic_importance(self, category: str) -> int:
        """Get strategic importance score for a category (1-10)."""
        strategic_map: dict[str, int] = {
            "african_languages": 10,
            "virtual_labs": 9,
            "voice_support": 8,
            "offline_capability": 7,
            "privacy_protection": 7,
            "multilingual_support": 8,
            "agentic_workflows": 7,
            "education_features": 8,
            "reasoning_depth": 7,
            "code_generation": 6,
            "conversation_quality": 6,
            "image_generation": 5,
            "image_analysis": 6,
            "memory_persistence": 6,
            "web_search": 5,
            "file_processing": 5,
            "cost_efficiency": 6,
            "speed_latency": 6,
            "document_generation": 4,
            "data_analysis": 5,
        }
        return strategic_map.get(category, 5)

    def _get_user_impact(self, category: str) -> int:
        """Get expected user impact score for a category (1-10)."""
        impact_map: dict[str, int] = {
            "conversation_quality": 9,
            "african_languages": 10,
            "voice_support": 9,
            "offline_capability": 8,
            "virtual_labs": 9,
            "education_features": 9,
            "multilingual_support": 8,
            "reasoning_depth": 7,
            "code_generation": 7,
            "image_generation": 6,
            "image_analysis": 7,
            "agentic_workflows": 6,
            "memory_persistence": 7,
            "web_search": 6,
            "file_processing": 6,
            "privacy_protection": 7,
            "cost_efficiency": 7,
            "speed_latency": 7,
            "document_generation": 5,
            "data_analysis": 6,
        }
        return impact_map.get(category, 5)

    def _get_ease_of_implementation(self, category: str) -> int:
        """Get ease of implementation score for a category (1-10, higher = easier)."""
        ease_map: dict[str, int] = {
            "voice_support": 7,
            "document_generation": 8,
            "web_search": 7,
            "file_processing": 7,
            "image_analysis": 6,
            "education_features": 6,
            "african_languages": 5,
            "multilingual_support": 5,
            "virtual_labs": 3,
            "offline_capability": 4,
            "privacy_protection": 6,
            "agentic_workflows": 5,
            "memory_persistence": 5,
            "reasoning_depth": 4,
            "code_generation": 5,
            "conversation_quality": 4,
            "image_generation": 4,
            "cost_efficiency": 5,
            "speed_latency": 4,
            "data_analysis": 6,
        }
        return ease_map.get(category, 5)

    def _generate_recommendation(self, category: str, gap_size: int, best_competitor: str) -> str:
        """Generate an actionable recommendation for a gap."""
        recommendations: dict[str, str] = {
            "african_languages": (
                f"Priority: Build comprehensive African language support. "
                f"Gap of {gap_size} points behind {best_competitor}. "
                f"Add 50+ African languages with native greetings, cultural context, "
                f"and voice support. This is a key differentiator."
            ),
            "voice_support": (
                f"Add TTS/STT support for 85+ languages using OpenAI Whisper and TTS APIs. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "virtual_labs": (
                f"Build virtual science lab with 20+ simulations for African schools. "
                f"Gap of {gap_size} points - major opportunity with no direct competition."
            ),
            "offline_capability": (
                f"Implement model quantization and edge deployment for offline use. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "reasoning_depth": (
                f"Improve multi-step reasoning with chain-of-thought prompting. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "image_generation": (
                f"Integrate image generation capabilities (DALL-E, Stable Diffusion). "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "agentic_workflows": (
                f"Enhance autonomous agent capabilities with better tool use and planning. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "memory_persistence": (
                f"Implement long-term memory with vector database storage. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
            "multilingual_support": (
                f"Expand language coverage beyond major languages to regional variants. "
                f"Gap of {gap_size} points behind {best_competitor}."
            ),
        }
        return recommendations.get(
            category,
            f"Improve {CAPABILITY_LABELS.get(category, category)}. "
            f"Gap of {gap_size} points behind {best_competitor}."
        )

    def _estimate_effort(self, category: str) -> int:
        """Estimate implementation effort in person-weeks."""
        effort_map: dict[str, int] = {
            "voice_support": 4,
            "document_generation": 3,
            "web_search": 3,
            "file_processing": 3,
            "image_analysis": 6,
            "education_features": 4,
            "african_languages": 8,
            "multilingual_support": 6,
            "virtual_labs": 12,
            "offline_capability": 10,
            "privacy_protection": 4,
            "agentic_workflows": 6,
            "memory_persistence": 5,
            "reasoning_depth": 8,
            "code_generation": 5,
            "conversation_quality": 6,
            "image_generation": 8,
            "cost_efficiency": 4,
            "speed_latency": 5,
            "data_analysis": 4,
        }
        return effort_map.get(category, 4)

    def analyze(self, findings: list[Any] | None = None) -> list[dict[str, Any]]:
        """Run full gap analysis pipeline.

        Args:
            findings: Optional research findings to incorporate.

        Returns:
            List of gap dictionaries sorted by priority.
        """
        self.assess_current_capabilities()
        self.analyze_competitors()
        gaps = self.identify_gaps()
        return [g.to_dict() for g in gaps]

    def get_top_gaps(self, n: int = 5) -> list[dict[str, Any]]:
        """Get top N gaps by priority.

        Args:
            n: Number of gaps to return.

        Returns:
            List of top gap dictionaries.
        """
        sorted_gaps = sorted(self.gaps, key=lambda g: g.priority, reverse=True)
        return [g.to_dict() for g in sorted_gaps[:n]]
