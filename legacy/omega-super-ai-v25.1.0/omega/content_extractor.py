#!/usr/bin/env python3
"""
Omega Super AI v10 — Web Content Extraction Module
===================================================
Provides utilities for fetching web pages, extracting clean text,
key facts, summaries, named entities, and statistics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HTTP_TIMEOUT: int = 10
MAX_CONTENT_LENGTH: int = 8_000
CACHE_TTL_SECONDS: int = 86_400  # 24 hours
CACHE_DIR: str = os.path.join(os.path.expanduser("~"), ".omega_cache", "extractor")

_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Regex for named-entity extraction (lightweight, no heavy NLP deps)
_RE_PERSON = re.compile(
    r"\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
)
_RE_ORG = re.compile(
    r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\s+(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|"
    r"Company|Co\.?|Group|Organization|Foundation|Institute|University|College|"
    r"School|Academy|Association|Society|Union|Bank|Partners|Holdings|Technologies|"
    r"Systems|Solutions|Network|Media|Digital|Labs|Research))\b",
    re.IGNORECASE,
)
_RE_DATE = re.compile(
    r"\b(?:"
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{4}|"
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},?\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}/\d{1,2}/\d{2,4}|"
    r"\d{1,2}-\d{1,2}-\d{2,4}|"
    r"Q[1-4]\s+\d{4}|"
    r"(?:Spring|Summer|Fall|Autumn|Winter)\s+\d{4}"
    r")\b"
)
_RE_NUMBER = re.compile(
    r"(?:\$\s*)?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:"
    r"million|billion|trillion|thousand|hundred|percent|%|kg|km|miles|GB|TB|"
    r"USD|EUR|GBP)?",
    re.IGNORECASE,
)
_RE_PERCENTAGE = re.compile(r"\b\d+(?:\.\d+)?%\b|\b\d+(?:\.\d+)?\s+percent\b", re.IGNORECASE)
_RE_DOLLAR = re.compile(r"\$\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:million|billion|trillion|thousand|hundred)?", re.IGNORECASE)

# Sentence tokenizer (lightweight)
_RE_SENTENCE = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _ensure_cache_dir() -> None:
    """Create cache directory if needed."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(url: str) -> str:
    """MD5 cache key for a URL."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def _read_cache(key: str) -> str | None:
    """Read cached page content if not expired."""
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cached_at = datetime.fromisoformat(data.get("cached_at", "1970-01-01T00:00:00"))
        if datetime.now(timezone.utc) - cached_at > timedelta(seconds=CACHE_TTL_SECONDS):
            os.remove(path)
            return None
        return data.get("content")
    except Exception:
        return None


def _write_cache(key: str, content: str) -> None:
    """Persist page content to cache."""
    _ensure_cache_dir()
    path = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "content": content,
                },
                fh,
                ensure_ascii=False,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def fetch_page(url: str, timeout: int = HTTP_TIMEOUT) -> str:
    """
    Fetch a URL, strip HTML/scripts/styles, and return clean text.

    Parameters
    ----------
    url: The URL to fetch.
    timeout: HTTP request timeout in seconds.

    Returns
    -------
    Clean text content (max 8000 characters).
    """
    if not url or not url.startswith(("http://", "https://")):
        return ""

    # Check cache
    key = _cache_key(url)
    cached = _read_cache(key)
    if cached is not None:
        return cached[:MAX_CONTENT_LENGTH]

    try:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.RequestException:
        return ""
    except Exception:
        return ""

    # Strip script and style tags
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<noscript[^>]*>[\s\S]*?</noscript>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<iframe[^>]*>[\s\S]*?</iframe>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>[\s\S]*?</nav>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>[\s\S]*?</footer>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<header[^>]*>[\s\S]*?</header>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<aside[^>]*>[\s\S]*?</aside>", " ", html, flags=re.IGNORECASE)

    # Extract text from paragraph-like tags first (they usually have the best content)
    paragraphs = re.findall(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.IGNORECASE)
    article_text = re.findall(r"<article[^>]*>([\s\S]*?)</article>", html, flags=re.IGNORECASE)
    main_text = re.findall(r"<main[^>]*>([\s\S]*?)</main>", html, flags=re.IGNORECASE)
    section_text = re.findall(r"<section[^>]*>([\s\S]*?)</section>", html, flags=re.IGNORECASE)
    div_text = re.findall(r"<div[^>]*>([\s\S]*?)</div>", html, flags=re.IGNORECASE)

    # Prioritize article/main content
    content_parts: list[str] = []
    if article_text:
        content_parts.extend(article_text)
    if main_text:
        content_parts.extend(main_text)
    if section_text:
        content_parts.extend(section_text)
    if paragraphs:
        content_parts.extend(paragraphs)
    if not content_parts:
        content_parts = div_text if div_text else [html]

    # Strip remaining HTML tags
    text = "\n\n".join(content_parts)
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&rsquo;", "'")
    text = text.replace("&lsquo;", "'")
    text = text.replace("&rdquo;", '"')
    text = text.replace("&ldquo;", '"')
    text = text.replace("&mdash;", "—")
    text = text.replace("&ndash;", "–")
    text = text.replace("&hellip;", "...")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Cache and return
    _write_cache(key, text)
    return text[:MAX_CONTENT_LENGTH]


def extract_key_facts(text: str, max_facts: int = 10) -> list[str]:
    """
    Extract bullet-point key facts from text using regex patterns.

    Parameters
    ----------
    text: Input text to analyze.
    max_facts: Maximum number of facts to return.

    Returns
    -------
    List of fact strings.
    """
    if not text or len(text) < 20:
        return []

    facts: list[str] = []

    # Pattern 1: sentences with strong factual indicators
    fact_indicators = [
        r"is a\s+(.*?(?:company|organization|institution|platform|framework|system|"
        r"technology|language|model|algorithm|tool|service|product|initiative|program))",
        r"was founded\s+(.*?\d{4})",
        r"was established\s+(.*?\d{4})",
        r"was developed\s+(.*?\d{4})",
        r"was created\s+(.*?\d{4})",
        r"was launched\s+(.*?\d{4})",
        r"announced\s+(.*?\d{4})",
        r"reported\s+(.*?\d+(?:\.\d+)?%?)",
        r"has\s+(?:over|more than|approximately|about|around)\s+(.*?\d+)",
        r"(?:generates|produces|creates|makes)\s+(.*?\d+)",
        r"(?:raised|secured|received|obtained)\s+\$(.*?") 
        + "d+)",
        r"(?:valued at|worth|market cap of)\s+\$(.*?") 
        + "d+)",
        r"(?:headquartered|based)\s+(?:in|at)\s+(.*?)(?:\.|,|;|\s+(?:and|with|it|which|where))",
        r"(?:CEO|CTO|CFO|founder|co-founder|president|director)\s+(?:is|was)\s+(.*?)(?:\.|,|;)",
        r"(?:serves|operates|functions)\s+(?:as|in)\s+(.*?)(?:\.|,|;)",
        r"(?:employs|has)\s+(.*?") 
        + "d+)\s+(?:employees|people|staff|workers)",
        r"(?:revenue|sales|income)\s+(?:of|was|is)\s+\$(.*?") 
        + "d+)",
        r"(?:grew|increased|rose|gained)\s+(?:by\s+)?(\d+(?:\.\d+)?%)",
        r"(?:decreased|fell|dropped|declined)\s+(?:by\s+)?(\d+(?:\.\d+)?%)",
        r"partnership\s+(?:with|between)\s+(.*?)(?:\.|,|;)",
        r"collaboration\s+(?:with|between)\s+(.*?)(?:\.|,|;)",
        r"acquired\s+(.*?)(?:\.|,|;|\s+for)",
        r"merger\s+(?:with|of|between)\s+(.*?)(?:\.|,|;)",
    ]

    for pattern in fact_indicators:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            fact = match.group(0).strip()
            # Clean up and truncate
            fact = re.sub(r"\s+", " ", fact)
            if len(fact) > 15 and len(fact) < 300:
                facts.append(fact)
        if len(facts) >= max_facts * 2:
            break

    # Pattern 2: sentences with numbers and statistics
    stat_sentences = re.findall(
        r"[A-Z][^.]*?\d+[^.]*?(?:million|billion|trillion|percent|%)" r"[^.]*?\.",
        text,
    )
    for sent in stat_sentences[:max_facts]:
        clean = sent.strip()
        if len(clean) > 20 and clean not in facts:
            facts.append(clean)

    # Pattern 3: definition-style sentences
    definition_sentences = re.findall(
        r"[A-Z][^.]*?(?:is defined as|refers to|means|is a type of|is the process of)" r"[^.]*?\.",
        text,
        re.IGNORECASE,
    )
    for sent in definition_sentences[:max_facts]:
        clean = sent.strip()
        if len(clean) > 20 and clean not in facts:
            facts.append(clean)

    # Deduplicate and truncate
    seen: set[str] = set()
    unique_facts: list[str] = []
    for f in facts:
        key = re.sub(r"\s+", " ", f.lower().strip()[:60])
        if key not in seen:
            seen.add(key)
            unique_facts.append(f)
        if len(unique_facts) >= max_facts:
            break

    return unique_facts


def summarize_content(text: str, max_sentences: int = 5) -> str:
    """
    Generate an extractive summary by scoring sentences.

    Parameters
    ----------
    text: Input text to summarize.
    max_sentences: Maximum number of sentences in the summary.

    Returns
    -------
    Summary string.
    """
    if not text:
        return ""

    if len(text) <= 200:
        return text.strip()

    # Split into sentences
    sentences = _RE_SENTENCE.split(text)
    if len(sentences) <= max_sentences:
        return text.strip()

    # Score each sentence
    word_freq: dict[str, int] = {}
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1

    # Normalize frequencies
    max_freq = max(word_freq.values()) if word_freq else 1
    for w in word_freq:
        word_freq[w] = word_freq[w] / max_freq

    sentence_scores: list[tuple[float, str]] = []
    for sent in sentences:
        sent_words = re.findall(r"\b[a-zA-Z]{3,}\b", sent.lower())
        if not sent_words:
            continue
        score = sum(word_freq.get(w, 0) for w in sent_words) / len(sent_words)

        # Boost sentences with numerical data
        if re.search(r"\d", sent):
            score *= 1.3
        # Boost sentences with named entities (capitalized words)
        if re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", sent):
            score *= 1.2
        # Boost first sentence of paragraphs
        if sent.strip() and sent == sentences[0]:
            score *= 1.1
        # Penalize very short sentences
        if len(sent_words) < 5:
            score *= 0.5

        sentence_scores.append((score, sent.strip()))

    # Sort by score and pick top sentences, preserving original order
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    top_sentences = sentence_scores[:max_sentences]
    top_sentences.sort(key=lambda x: sentences.index(x[1]) if x[1] in sentences else float("inf"))

    summary = " ".join(s for _, s in top_sentences)
    return summary


def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Extract named entities (people, organizations, dates) from text.

    Parameters
    ----------
    text: Input text to analyze.

    Returns
    -------
    dict with keys ``people``, ``organizations``, ``dates``.
    """
    if not text:
        return {"people": [], "organizations": [], "dates": []}

    people = list(set(_RE_PERSON.findall(text)))
    organizations = list(set(_RE_ORG.findall(text)))
    dates = list(set(_RE_DATE.findall(text)))

    # Filter out false positives for people
    stop_words = {
        "The", "This", "That", "These", "Those", "There", "Their", "They",
        "What", "When", "Where", "Which", "Who", "Why", "How", "But", "And",
        "For", "Nor", "Or", "So", "Yet", "With", "From", "Into", "Onto",
        "About", "Above", "Across", "After", "Against", "Along", "Among",
        "Around", "Before", "Behind", "Below", "Beneath", "Beside", "Between",
        "Beyond", "During", "Except", "Inside", "Outside", "Until", "Upon",
        "Within", "Without", "January", "February", "March", "April", "May",
        "June", "July", "August", "September", "October", "November", "December",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        "Inc", "Ltd", "Corp", "LLC", "Google", "Apple", "Microsoft", "Amazon",
    }
    people = [p for p in people if not all(w in stop_words for w in p.split())]
    people = [p for p in people if len(p.split()) >= 2]

    # Clean and deduplicate
    people = sorted(set(p.strip() for p in people if len(p.strip()) > 3))[:20]
    organizations = sorted(set(o.strip() for o in organizations if len(o.strip()) > 3))[:20]
    dates = sorted(set(d.strip() for d in dates if len(d.strip()) > 3))[:20]

    return {"people": people, "organizations": organizations, "dates": dates}


def extract_statistics(text: str) -> dict[str, list[str]]:
    """
    Extract numbers, percentages, and dollar amounts from text.

    Parameters
    ----------
    text: Input text to analyze.

    Returns
    -------
    dict with keys ``numbers``, ``percentages``, ``dollar_amounts``.
    """
    if not text:
        return {"numbers": [], "percentages": [], "dollar_amounts": []}

    numbers = list(set(_RE_NUMBER.findall(text)))
    percentages = list(set(_RE_PERCENTAGE.findall(text)))
    dollar_amounts = list(set(_RE_DOLLAR.findall(text)))

    # Clean and sort by length (longer = more specific)
    numbers = sorted(set(n.strip() for n in numbers if len(n.strip()) > 0), key=len, reverse=True)[:30]
    percentages = sorted(set(p.strip() for p in percentages if len(p.strip()) > 0), key=len, reverse=True)[:20]
    dollar_amounts = sorted(set(d.strip() for d in dollar_amounts if len(d.strip()) > 0), key=len, reverse=True)[:20]

    return {
        "numbers": numbers,
        "percentages": percentages,
        "dollar_amounts": dollar_amounts,
    }


def analyze_content(url: str, timeout: int = HTTP_TIMEOUT) -> dict[str, Any]:
    """
    Full content analysis pipeline: fetch, extract facts, summarize,
    entities, and statistics.

    Parameters
    ----------
    url: URL to analyze.
    timeout: HTTP timeout.

    Returns
    -------
    dict with ``url``, ``content``, ``facts``, ``summary``, ``entities``, ``statistics``.
    """
    content = fetch_page(url, timeout=timeout)
    if not content:
        return {
            "url": url,
            "content": "",
            "facts": [],
            "summary": "",
            "entities": {"people": [], "organizations": [], "dates": []},
            "statistics": {"numbers": [], "percentages": [], "dollar_amounts": []},
        }

    return {
        "url": url,
        "content": content,
        "facts": extract_key_facts(content),
        "summary": summarize_content(content),
        "entities": extract_entities(content),
        "statistics": extract_statistics(content),
    }
