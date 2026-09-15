"""Autonomous Research Agent for monitoring the AI landscape.

Scrapes multiple research sources to discover new papers, models, techniques,
and competitor movements in the AI space.
"""

from __future__ import annotations

import json
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urljoin

import requests

logger = logging.getLogger(__name__)

# Default research sources
RESEARCH_SOURCES = [
    "arxiv",
    "huggingface",
    "openai_blog",
    "github_trending",
    "papers_with_code",
]

# Capability categories for classification
CAPABILITY_CATEGORIES = [
    "code_generation",
    "multilingual_support",
    "african_languages",
    "reasoning_depth",
    "image_generation",
    "image_analysis",
    "agentic_workflows",
    "memory_persistence",
    "voice_support",
    "education_features",
    "data_analysis",
    "web_search",
    "document_generation",
    "privacy_protection",
    "offline_capability",
    "cost_efficiency",
    "speed_latency",
    "conversation_quality",
    "virtual_labs",
    "file_processing",
]

# Scraping configuration
SCRAPING_CONFIG = {
    "user_agent": "Luqi-AI-Prometheus-ResearchBot/1.0 (research@luqi.ai)",
    "polite_delay_seconds": 2,
    "max_retries": 3,
    "retry_backoff_factor": 2,
    "timeout_seconds": 30,
    "max_papers_per_category": 50,
    "max_results_per_source": 30,
}


@dataclass
class ResearchFinding:
    """A single research finding from any source.

    Attributes:
        title: Title of the finding.
        source: Source name (e.g., 'arxiv', 'huggingface').
        url: Direct URL to the resource.
        summary: Brief summary or abstract.
        relevance_score: Estimated relevance to Luqi AI (0.0 - 1.0).
        category: Related capability category.
        date: Publication or discovery date.
        authors: List of authors (if applicable).
        tags: Additional tags for classification.
    """

    title: str
    source: str
    url: str
    summary: str = ""
    relevance_score: float = 0.5
    category: str = ""
    date: str = ""
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary representation."""
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "category": self.category,
            "date": self.date,
            "authors": self.authors,
            "tags": self.tags,
        }


class ResearchAgent:
    """Autonomous agent for researching the AI landscape.

    Scrapes multiple sources including arXiv, HuggingFace, OpenAI blog,
    GitHub trending, and Papers with Code to discover new developments.

    Attributes:
        config: Scraping configuration dictionary.
        session: Shared requests session with configured headers.
        findings: Accumulated research findings.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the ResearchAgent.

        Args:
            config: Optional scraping configuration overrides.
        """
        self.config = config or SCRAPING_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.get("user_agent", SCRAPING_CONFIG["user_agent"]),
            "Accept": "application/json, text/html, application/xml",
        })
        self.findings: list[ResearchFinding] = []
        logger.info("ResearchAgent initialized with %d sources", len(RESEARCH_SOURCES))

    def _polite_delay(self) -> None:
        """Apply polite delay between requests."""
        delay = self.config.get("polite_delay_seconds", SCRAPING_CONFIG["polite_delay_seconds"])
        time.sleep(delay)

    def _fetch_with_retry(self, url: str, **kwargs: Any) -> requests.Response | None:
        """Fetch URL with retry logic and polite delays."""
        max_retries = self.config.get("max_retries", SCRAPING_CONFIG["max_retries"])
        backoff = self.config.get("retry_backoff_factor", SCRAPING_CONFIG["retry_backoff_factor"])
        timeout = self.config.get("timeout_seconds", SCRAPING_CONFIG["timeout_seconds"])

        for attempt in range(max_retries):
            try:
                self._polite_delay()
                response = self.session.get(url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning("Request to %s failed (attempt %d/%d): %s", url, attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    time.sleep(backoff ** attempt)
                else:
                    logger.error("All retries failed for %s", url)
        return None

    def _estimate_relevance(self, title: str, summary: str) -> float:
        """Estimate relevance of a finding to Luqi AI.

        Uses keyword matching against capability categories and
        Luqi-specific interests.

        Args:
            title: Title of the finding.
            summary: Summary or abstract text.

        Returns:
            Relevance score between 0.0 and 1.0.
        """
        text = f"{title} {summary}".lower()

        # Keywords that indicate high relevance
        high_relevance_keywords = [
            "multilingual", "african language", "low-resource",
            "code generation", "agent", "tool use", "reasoning",
            "rag", "retrieval", "fine-tuning", "efficient",
            "distillation", "quantization", "on-device",
            "privacy-preserving", "federated",
        ]

        # Keywords that indicate medium relevance
        medium_relevance_keywords = [
            "llm", "language model", "transformer",
            "attention", "embedding", "prompt",
            "instruction tuning", "rlhf", "alignment",
            "evaluation", "benchmark",
        ]

        score = 0.0
        for kw in high_relevance_keywords:
            if kw in text:
                score += 0.15

        for kw in medium_relevance_keywords:
            if kw in text:
                score += 0.08

        # Cap relevance to category matches
        for category in CAPABILITY_CATEGORIES:
            if category.replace("_", " ") in text:
                score += 0.1

        return min(score, 1.0)

    def _categorize(self, title: str, summary: str) -> str:
        """Categorize a finding into a capability category."""
        text = f"{title} {summary}".lower()

        category_keywords: dict[str, list[str]] = {
            "code_generation": ["code", "programming", "coding", "developer"],
            "multilingual_support": ["multilingual", "translation", "language"],
            "african_languages": ["african", "swahili", "yoruba", "igbo", "hausa", "zulu", "low-resource"],
            "reasoning_depth": ["reasoning", "logic", "inference", "chain-of-thought", "cot"],
            "image_generation": ["image generation", "diffusion", "gan", "synthesis"],
            "image_analysis": ["vision", "image understanding", "multimodal", "vlm"],
            "agentic_workflows": ["agent", "tool use", "function calling", "autonomous"],
            "memory_persistence": ["memory", "retrieval", "rag", "context"],
            "voice_support": ["speech", "voice", "audio", "tts", "asr"],
            "education_features": ["education", "tutor", "learning", "teaching"],
            "data_analysis": ["data", "analysis", "visualization", "statistics"],
            "web_search": ["search", "retrieval", "web"],
            "document_generation": ["document", "pdf", "report", "generation"],
            "privacy_protection": ["privacy", "secure", "federated", "differential"],
            "offline_capability": ["on-device", "edge", "mobile", "offline"],
            "cost_efficiency": ["efficient", "distillation", "quantization", "pruning"],
            "speed_latency": ["latency", "fast", "speed", "throughput"],
            "conversation_quality": ["dialogue", "conversation", "chat"],
            "virtual_labs": ["simulation", "lab", "experiment", "sandbox"],
            "file_processing": ["file", "document parsing", "pdf extraction"],
        }

        best_category = ""
        best_score = 0.0

        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def scrape_arxiv(self, category: str = "cs.AI", days: int = 7) -> list[ResearchFinding]:
        """Scrape recent AI papers from arXiv.

        Uses the arXiv API to fetch recent papers in a given category.

        Args:
            category: arXiv category code (e.g., 'cs.AI', 'cs.CL', 'cs.LG').
            days: Number of days back to search.

        Returns:
            List of ResearchFinding objects for papers found.
        """
        logger.info("Scraping arXiv category %s for last %d days", category, days)
        findings: list[ResearchFinding] = []

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # arXiv API query
        query_params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": self.config.get("max_papers_per_category", SCRAPING_CONFIG["max_papers_per_category"]),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        url = f"http://export.arxiv.org/api/query?{urlencode(query_params)}"
        response = self._fetch_with_retry(url)

        if not response:
            logger.error("Failed to fetch arXiv papers for category %s", category)
            return findings

        try:
            # Parse Atom feed
            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                summary_elem = entry.find("atom:summary", ns)
                url_elem = entry.find("atom:id", ns)
                date_elem = entry.find("atom:published", ns)
                authors_elems = entry.findall("atom:author/atom:name", ns)

                if title_elem is None or url_elem is None:
                    continue

                title = title_elem.text.strip() if title_elem.text else ""
                summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
                paper_url = url_elem.text.strip() if url_elem.text else ""
                date = date_elem.text[:10] if date_elem is not None and date_elem.text else ""
                authors = [a.text for a in authors_elems if a.text]

                # Filter by date
                if date < start_date.strftime("%Y-%m-%d"):
                    continue

                relevance = self._estimate_relevance(title, summary)
                category_found = self._categorize(title, summary)

                finding = ResearchFinding(
                    title=title,
                    source="arxiv",
                    url=paper_url,
                    summary=summary[:500] + "..." if len(summary) > 500 else summary,
                    relevance_score=relevance,
                    category=category_found,
                    date=date,
                    authors=authors,
                    tags=[category, "research"],
                )
                findings.append(finding)

            logger.info("Found %d papers from arXiv %s", len(findings), category)

        except ET.ParseError as e:
            logger.error("Failed to parse arXiv XML: %s", e)

        return findings

    def scrape_huggingface(self, limit: int = 30) -> list[ResearchFinding]:
        """Scrape trending models and papers from HuggingFace.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of ResearchFinding objects.
        """
        logger.info("Scraping HuggingFace trending models")
        findings: list[ResearchFinding] = []

        # HuggingFace API endpoint for trending models
        url = "https://huggingface.co/api/trending"
        response = self._fetch_with_retry(url)

        if not response:
            return findings

        try:
            data = response.json()
            for item in data[:limit]:
                title = item.get("modelId", "Unknown Model")
                summary = item.get("description", "")
                model_url = f"https://huggingface.co/{title}"
                tags = item.get("tags", [])

                relevance = self._estimate_relevance(title, summary)
                category = self._categorize(title, summary)

                finding = ResearchFinding(
                    title=title,
                    source="huggingface",
                    url=model_url,
                    summary=summary[:500] if summary else "",
                    relevance_score=relevance,
                    category=category,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    tags=tags,
                )
                findings.append(finding)

            logger.info("Found %d models from HuggingFace", len(findings))

        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse HuggingFace response: %s", e)

        return findings

    def scrape_github_trending(self, language: str = "python", since: str = "weekly") -> list[ResearchFinding]:
        """Scrape trending repositories from GitHub.

        Args:
            language: Programming language filter.
            since: Time period ('daily', 'weekly', 'monthly').

        Returns:
            List of ResearchFinding objects.
        """
        logger.info("Scraping GitHub trending for language=%s, since=%s", language, since)
        findings: list[ResearchFinding] = []

        # GitHub trending is scraped from the HTML page
        url = f"https://github.com/trending/{language}?since={since}"
        response = self._fetch_with_retry(url, headers={"Accept": "text/html"})

        if not response:
            return findings

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("article", class_="Box-row")

            for article in articles[:self.config.get("max_results_per_source", SCRAPING_CONFIG["max_results_per_source"])]:
                h2 = article.find("h2")
                if not h2:
                    continue

                repo_link = h2.find("a")
                if not repo_link:
                    continue

                repo_name = repo_link.get_text(strip=True).replace(" ", "").replace("\n", "")
                repo_url = urljoin("https://github.com", repo_link.get("href", ""))

                description_elem = article.find("p", class_="col-9")
                description = description_elem.get_text(strip=True) if description_elem else ""

                relevance = self._estimate_relevance(repo_name, description)
                category = self._categorize(repo_name, description)

                finding = ResearchFinding(
                    title=repo_name,
                    source="github_trending",
                    url=repo_url,
                    summary=description[:300] if description else "",
                    relevance_score=relevance,
                    category=category,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    tags=[language, "repository"],
                )
                findings.append(finding)

            logger.info("Found %d repositories from GitHub trending", len(findings))

        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping GitHub trending scraping")
        except Exception as e:
            logger.error("Error scraping GitHub trending: %s", e)

        return findings

    def run_full_scrape(self, days: int = 7) -> list[ResearchFinding]:
        """Run a full research scrape across all configured sources.

        Args:
            days: Number of days back to search for time-bounded sources.

        Returns:
            Combined list of all ResearchFinding objects.
        """
        logger.info("Starting full research scrape (last %d days)", days)
        all_findings: list[ResearchFinding] = []

        # arXiv - multiple categories
        for category in ["cs.AI", "cs.CL", "cs.LG", "cs.CV"]:
            findings = self.scrape_arxiv(category=category, days=days)
            all_findings.extend(findings)

        # HuggingFace
        findings = self.scrape_huggingface()
        all_findings.extend(findings)

        # GitHub Trending
        findings = self.scrape_github_trending()
        all_findings.extend(findings)

        # Sort by relevance
        all_findings.sort(key=lambda x: x.relevance_score, reverse=True)

        self.findings = all_findings
        logger.info("Full scrape complete: %d total findings", len(all_findings))

        return all_findings

    def get_top_findings(self, n: int = 10, min_relevance: float = 0.3) -> list[ResearchFinding]:
        """Get top N findings above a relevance threshold.

        Args:
            n: Maximum number of findings to return.
            min_relevance: Minimum relevance score to include.

        Returns:
            Filtered and sorted list of findings.
        """
        filtered = [f for f in self.findings if f.relevance_score >= min_relevance]
        return filtered[:n]

    def to_dict(self) -> list[dict[str, Any]]:
        """Convert all findings to list of dictionaries.

        Returns:
            List of finding dictionaries.
        """
        return [f.to_dict() for f in self.findings]
