#!/usr/bin/env python3
"""
Omega Super AI v10 — Critical Thinking & Reasoning Engine
===========================================================
Provides chain-of-thought critical analysis, claim verification,
logical fallacy detection, and devil's advocate argumentation.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Constants — logical fallacy regex patterns
# ---------------------------------------------------------------------------

FALLACY_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "ad_hominem",
        "name": "Ad Hominem",
        "patterns": [
            r"\b(?:idiot|stupid|dumb|moron|fool|ignorant|lazy|corrupt|liar|cheat|fraud)\b.*\b(?:argument|opinion|view|position|claim)\b",
            r"\b(?:he|she|they)\s+(?:is|are|was|were)\s+(?:just|only|simply)?\s*(?:an?\s+)?\w*\s*(?:idiot|stupid|fool|moron)\b",
            r"\battacking\s+(?:the\s+)?(?:person|character|messenger)\b",
        ],
        "description": "Attacking the person making the argument rather than the argument itself.",
    },
    {
        "type": "straw_man",
        "name": "Straw Man",
        "patterns": [
            r"\b(?:misrepresents?|distorts?|exaggerates?|oversimplif(?:y|ies))\b.*\b(?:argument|position|view)\b",
            r"\b(?:so\s+you(?:'re|\s+are)\s+saying|what\s+(?:you|they)\s+reall?y\s+mean|that's\s+like\s+saying)\b",
        ],
        "description": "Misrepresenting someone's argument to make it easier to attack.",
    },
    {
        "type": "false_dichotomy",
        "name": "False Dichotomy (Either/Or Fallacy)",
        "patterns": [
            r"\b(?:either\s+you\s+(?:are|do|believe)|either\s+we\s+(?:do|go|act)|either\s+or\s+(?:nothing|no\s+one|nobody))\b",
            r"\b(?:there\s+(?:is|are)\s+only\s+(?:two|2)\s+(?:options|choices|possibilities|sides))\b",
            r"\b(?:you\s+(?:are\s+either|either)\s+with\s+(?:us|me)\s+or\s+against\s+(?:us|me))\b",
        ],
        "description": "Presenting only two options when more exist.",
    },
    {
        "type": "appeal_to_authority",
        "name": "Appeal to Authority",
        "patterns": [
            r"\b(?:expert|professor|doctor|scientist|study|research)\s+says\b.*\b(?:therefore|so|thus|hence|proves)\b",
            r"\b(?:according\s+to)\s+(?:the\s+)?(?:experts|scientists|authorities|professionals)\b",
            r"\b(?:believe\s+(?:it|this)\s+because)\s+.*\b(?:expert|authority|PhD|doctor|professor)\b",
        ],
        "description": "Claiming something is true because an authority figure says so, without evidence.",
    },
    {
        "type": "slippery_slope",
        "name": "Slippery Slope",
        "patterns": [
            r"\b(?:if\s+we\s+(?:allow|permit|accept))\b.*\b(?:then|next|eventually|lead\s+to|will\s+result)\b.*\b(?:all|every|total|complete)\b",
            r"\b(?:slippery\s+slope|domino\s+effect|chain\s+reaction|snowball\s+effect)\b",
            r"\b(?:before\s+you\s+know\s+it|it\s+will\s+lead\s+to|one\s+thing\s+leads\s+to)\b",
        ],
        "description": "Arguing that a small step will inevitably lead to a chain of extreme consequences.",
    },
    {
        "type": "hasty_generalization",
        "name": "Hasty Generalization",
        "patterns": [
            r"\b(?:all|every|always|never|none)\s+.*\b(?:because|since|from\s+my)\b.*\b(?:experience|saw|heard|read)\b",
            r"\b(?:everyone\s+knows|nobody\s+(?:really\s+)?(?:believes|thinks|cares))\b",
            r"\b(?:based\s+on\s+(?:this|that|one|a\s+single)\s+(?:example|case|instance|time))\b.*\b(?:all|every|always)\b",
        ],
        "description": "Drawing a broad conclusion from a small or unrepresentative sample.",
    },
    {
        "type": "circular_reasoning",
        "name": "Circular Reasoning (Begging the Question)",
        "patterns": [
            r"\b(?:is\s+true\s+because|because\s+.*\bis\s+true)\b",
            r"\b(?:the\s+reason\s+is\s+that|that's\s+because)\b.*\b(?:same\s+thing|exactly\s+what)\b",
        ],
        "description": "The conclusion is assumed in the premise; the argument goes in a circle.",
    },
    {
        "type": "bandwagon",
        "name": "Bandwagon Appeal",
        "patterns": [
            r"\b(?:everyone|everybody|most\s+people|the\s+majority)\s+(?:knows|believes|thinks|agrees|does)\b.*\b(?:so\+should|therefore)\b",
            r"\b(?:join\s+the\s+crowd|everyone\s+is\s+doing\s+it|go\s+with\s+the\s+majority)\b",
            r"\b(?:popular\s+(?:opinion|belief|view))\b.*\b(?:therefore|so|thus|proves)\b",
        ],
        "description": "Arguing that something is true or good because many people believe or do it.",
    },
    {
        "type": "red_herring",
        "name": "Red Herring",
        "patterns": [
            r"\b(?:that's\s+not\s+the\s+point|misses\s+the\s+point|irrelevant\s+to)\b",
            r"\b(?:changing\s+the\s+subject|let's\s+talk\s+about\s+instead)\b",
        ],
        "description": "Introducing an irrelevant topic to divert attention from the original issue.",
    },
    {
        "type": "tu_quoque",
        "name": "Tu Quoque (You Too)",
        "patterns": [
            r"\b(?:but\s+you\s+(?:do|did|have|are|were)|look\s+who's\s+talking|pot\s+calling\s+the\s+kettle)\b",
            r"\b(?:you\s+(?:do|did)\s+it\s+too|what\s+about\s+(?:you|your))\b",
        ],
        "description": "Dismissing an argument because the person making it is also guilty of the behavior.",
    },
    {
        "type": "anecdotal_evidence",
        "name": "Anecdotal Evidence",
        "patterns": [
            r"\b(?:I\s+know\s+(?:a\s+person|someone|a\s+guy)|my\s+(?:friend|cousin|uncle|neighbor))\b.*\b(?:and\s+(?:he|she|they))\b",
            r"\b(?:in\s+my\s+(?:experience|life|case|opinion))\b.*\b(?:therefore|so|thus|proves|shows)\b",
        ],
        "description": "Using personal experience or a single story as proof instead of systematic evidence.",
    },
    {
        "type": "appeal_to_emotion",
        "name": "Appeal to Emotion",
        "patterns": [
            r"\b(?:think\s+of\s+the\s+(?:children|victims|families)|heartless|cruel|devastating|heartbreaking)\b",
            r"\b(?:outrageous|disgusting|shocking|appalling|scandalous)\b.*\b(?:we\s+must|we\s+need|we\s+should)\b",
            r"\b(?:how\s+dare\s+you|shame\s+on|you\s+should\s+be\s+ashamed)\b",
        ],
        "description": "Manipulating emotions to win an argument rather than using facts and logic.",
    },
]


# ---------------------------------------------------------------------------
# CriticalThinker class
# ---------------------------------------------------------------------------


class CriticalThinker:
    """
    Chain-of-thought critical analysis engine.

    Provides structured reasoning, claim verification, fallacy detection,
    and devil's advocate counter-argument generation.
    """

    def __init__(self, openai_client: Any) -> None:
        """
        Initialize the CriticalThinker.

        Parameters
        ----------
        openai_client: An OpenAI-compatible client with ``chat.completions.create``.
        """
        self.client = openai_client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _llm_chat(
        messages: list[dict[str, str]],
        client: Any,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2_000,
    ) -> str:
        """Call the LLM and return text content, or empty string on failure."""
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
        try:
            return __import__("json").loads(text)
        except Exception:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return __import__("json").loads(match.group(1))
            except Exception:
                pass
        match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if match:
            try:
                return __import__("json").loads(match.group(1))
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, query: str, research_findings: dict[str, Any]) -> dict[str, Any]:
        """
        Perform chain-of-thought critical analysis of research findings.

        Steps:
        1. Break down the problem
        2. Identify assumptions and premises
        3. Evaluate evidence quality and source reliability
        4. Check for cognitive biases and logical fallacies
        5. Consider alternative perspectives
        6. Assess overall confidence
        7. Provide structured reasoning

        Parameters
        ----------
        query: The original research question.
        research_findings: Dict with ``synthesis``, ``sources``, ``confidence_score``, etc.

        Returns
        -------
        dict with reasoning_chain, assumptions, evidence_quality, identified_biases,
        alternative_perspectives, confidence_score, recommendations, uncertainties.
        """
        if not self.client:
            return self._analyze_without_llm(query, research_findings)

        synthesis = research_findings.get("synthesis", "")
        sources = research_findings.get("sources", [])
        confidence = research_findings.get("confidence_score", 50)

        # Build source summary
        source_summary = "\n".join(
            f"- {s.get('title', 'Untitled')} ({s.get('link', '')}, relevance: {s.get('relevance', 'N/A')})"
            for s in sources[:10]
        )

        system_prompt = (
            "You are an expert critical thinker and analytical philosopher. "
            "Perform a rigorous critical analysis of the provided research findings. "
            "Structure your response as a JSON object with these keys:\n"
            "  reasoning_chain: array of reasoning steps\n"
            "  assumptions: array of identified assumptions\n"
            "  evidence_quality: object with score (0-100) and assessment text\n"
            "  identified_biases: array of detected biases\n"
            "  alternative_perspectives: array of counter-perspectives\n"
            "  confidence_score: number 0-100\n"
            "  recommendations: array of actionable recommendations\n"
            "  uncertainties: array of remaining uncertainties\n"
            "Be thorough, honest, and intellectually rigorous."
        )

        user_prompt = (
            f"Research question: {query}\n\n"
            f"Research synthesis:\n{synthesis[:3_000]}\n\n"
            f"Sources ({len(sources)} total):\n{source_summary}\n\n"
            f"Initial confidence: {confidence}%\n\n"
            f"Provide critical analysis as JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self._llm_chat(messages, self.client, max_tokens=4_000, temperature=0.2)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, dict) and "reasoning_chain" in parsed:
            return {
                "reasoning_chain": parsed.get("reasoning_chain", []),
                "assumptions": parsed.get("assumptions", []),
                "evidence_quality": parsed.get("evidence_quality", {"score": 50, "assessment": "Unknown"}),
                "identified_biases": parsed.get("identified_biases", []),
                "alternative_perspectives": parsed.get("alternative_perspectives", []),
                "confidence_score": parsed.get("confidence_score", confidence),
                "recommendations": parsed.get("recommendations", []),
                "uncertainties": parsed.get("uncertainties", []),
            }

        # Fallback to non-LLM analysis
        return self._analyze_without_llm(query, research_findings)

    def verify_claims(
        self,
        claims: list[str],
        search_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Cross-verify each claim against search results.

        Parameters
        ----------
        claims: List of claim strings to verify.
        search_results: List of search result dicts with ``snippet``, ``title``, ``link``.

        Returns
        -----
        List of dicts with claim, verified, confidence, supporting, contradicting.
        """
        verified_results: list[dict[str, Any]] = []

        for claim in claims:
            claim_lower = claim.lower()
            claim_words = set(re.findall(r"\b\w{4,}\b", claim_lower))

            supporting: list[dict[str, str]] = []
            contradicting: list[dict[str, str]] = []

            for result in search_results:
                snippet = result.get("snippet", "").lower()
                title = result.get("title", "").lower()
                combined = f"{title} {snippet}"
                result_words = set(re.findall(r"\b\w{4,}\b", combined))

                if not claim_words or not result_words:
                    continue

                # Word overlap score
                overlap = len(claim_words & result_words)
                total = len(claim_words | result_words)
                similarity = overlap / total if total > 0 else 0.0

                if similarity >= 0.3:
                    source_info = {
                        "title": result.get("title", ""),
                        "link": result.get("link", ""),
                        "similarity": round(similarity, 3),
                    }

                    # Check for contradiction signals
                    negation_patterns = [
                        r"\b(not|no|never|none|nothing|false|incorrect|wrong|disprove|refute|deny|reject)\b",
                        r"\b(contrary|opposite|however|but|although|despite|rather)\b",
                    ]
                    has_negation = any(
                        re.search(pat, snippet[snippet.find(word):snippet.find(word) + 200] if (word := list(claim_words & result_words)[0] if (claim_words & result_words) else "") in snippet else "")
                        for pat in negation_patterns
                    ) if (claim_words & result_words) else False

                    if has_negation and similarity >= 0.4:
                        contradicting.append(source_info)
                    else:
                        supporting.append(source_info)

            # Determine verification status
            if supporting and not contradicting:
                verified = True
                confidence = min(50 + len(supporting) * 15 + max(s["similarity"] for s in supporting) * 30, 95)
            elif supporting and contradicting:
                verified = False
                confidence = 30 + len(supporting) * 10
            elif not supporting and not contradicting:
                verified = False
                confidence = 10
            else:
                verified = False
                confidence = max(5, 20 - len(contradicting) * 5)

            verified_results.append({
                "claim": claim,
                "verified": verified,
                "confidence": round(confidence, 1),
                "supporting": supporting[:5],
                "contradicting": contradicting[:5],
            })

        return verified_results

    def detect_fallacies(self, text: str) -> list[dict[str, Any]]:
        """
        Detect logical fallacies in text using pattern matching.

        Parameters
        ----------
        text: Input text to analyze.

        Returns
        -------
        List of dicts with fallacy_type, excerpt, and explanation.
        """
        if not text or len(text) < 20:
            return []

        detected: list[dict[str, Any]] = []
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sentence in sentences:
            sentence_stripped = sentence.strip()
            if len(sentence_stripped) < 15:
                continue

            for fallacy in FALLACY_DEFINITIONS:
                for pattern in fallacy["patterns"]:
                    try:
                        if re.search(pattern, sentence_stripped, re.IGNORECASE):
                            excerpt = sentence_stripped[:250]
                            detected.append({
                                "fallacy_type": fallacy["type"],
                                "fallacy_name": fallacy["name"],
                                "excerpt": excerpt,
                                "explanation": fallacy["description"],
                            })
                            break  # Only one match per fallacy type per sentence
                    except re.error:
                        continue

        # Deduplicate by (type, excerpt) combination
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for d in detected:
            key = f"{d['fallacy_type']}:{d['excerpt'][:60]}"
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique

    def devil_advocate(self, position: str) -> str:
        """
        Generate counter-arguments to a given position.

        Parameters
        ----------
        position: The position to argue against.

        Returns
        -----
        String with counter-arguments.
        """
        if not self.client:
            return self._devil_advocate_without_llm(position)

        system_prompt = (
            "You are a skilled devil's advocate. Your role is to challenge the given "
            "position by providing the strongest possible counter-arguments. "
            "Be intellectually rigorous, fair, and constructive. Present 3-5 specific "
            "counter-arguments, each with supporting reasoning. Acknowledge when the "
            "original position has merit, but focus on its weaknesses, blind spots, "
            "and alternative interpretations. Write in a clear, persuasive style."
        )

        user_prompt = (
            f"Position to challenge: '{position}'\n\n"
            f"Provide strong counter-arguments as devil's advocate."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self._llm_chat(messages, self.client, max_tokens=2_000, temperature=0.4)

    # ------------------------------------------------------------------
    # Fallback analysis (no LLM)
    # ------------------------------------------------------------------

    def _analyze_without_llm(
        self, query: str, research_findings: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform basic critical analysis without LLM assistance."""
        sources = research_findings.get("sources", [])
        synthesis = research_findings.get("synthesis", "")
        confidence = research_findings.get("confidence_score", 50)

        # Extract assumptions from synthesis
        assumptions: list[str] = []
        assumption_patterns = [
            r"(?:assumes?|assuming|presum(?:es?|ing)|it\s+is\s+(?:assumed|presumed))\s+(?:that\s+)?([^.]+)",
            r"(?:based\s+on\s+the\s+assumption)\s+(?:that\s+)?([^.]+)",
        ]
        for pattern in assumption_patterns:
            for match in re.finditer(pattern, synthesis, re.IGNORECASE):
                assumptions.append(match.group(1).strip())

        if not assumptions:
            assumptions = [
                "The research assumes the sources are credible and up-to-date.",
                "The analysis assumes the search queries captured the full scope of the topic.",
            ]

        # Evaluate evidence quality
        source_count = len(sources)
        domain_scores: list[int] = []
        for s in sources:
            link = s.get("link", "")
            if ".gov" in link or ".edu" in link:
                domain_scores.append(90)
            elif "wikipedia.org" in link:
                domain_scores.append(60)
            elif "news" in link or "reuters" in link or "bloomberg" in link:
                domain_scores.append(75)
            elif "arxiv" in link or "github" in link:
                domain_scores.append(80)
            else:
                domain_scores.append(50)

        avg_domain_score = sum(domain_scores) / len(domain_scores) if domain_scores else 50
        evidence_score = min(
            int(avg_domain_score * 0.5 + min(source_count * 5, 50)),
            100,
        )

        # Detect biases in synthesis
        bias_patterns: dict[str, str] = {
            "confirmation_bias": r"\b(clearly|obviously|undoubtedly|certainly|definitely)\b",
            "selection_bias": r"\b(most\s+(?:studies|research|experts)|many\s+sources)\b",
            "framing_bias": r"\b(crisis|epidemic|breakthrough|revolutionary|game-changing)\b",
        }
        identified_biases: list[str] = []
        for bias_name, pattern in bias_patterns.items():
            if re.search(pattern, synthesis, re.IGNORECASE):
                identified_biases.append(bias_name.replace("_", " ").title())

        # Alternative perspectives
        alternative_perspectives = [
            f"Consider the opposite: What if the conventional wisdom about '{query}' is wrong?",
            "Evaluate methodological limitations in the underlying research.",
            "Consider temporal factors — has the landscape changed since the data was collected?",
            "Examine whether cultural or regional factors affect the generalizability of findings.",
        ]

        # Calculate adjusted confidence
        adjusted_confidence = max(0, min(confidence - len(identified_biases) * 5, 100))

        # Recommendations
        recommendations = [
            "Seek primary sources to verify key claims.",
            "Look for peer-reviewed studies on this topic.",
            "Consider running additional searches with different keywords.",
            "Evaluate the recency and relevance of cited sources.",
        ]
        if source_count < 5:
            recommendations.insert(0, "Increase source diversity — more sources needed for robust conclusions.")

        # Uncertainties
        uncertainties = [
            "Scope of search coverage — not all sources may have been indexed.",
            "Source credibility assessment is automated and may miss nuanced reliability factors.",
            "Temporal validity — information may become outdated.",
        ]

        return {
            "reasoning_chain": [
                f"1. Analyzed research question: '{query}'",
                f"2. Examined {source_count} sources for credibility and relevance",
                f"3. Identified {len(assumptions)} underlying assumptions",
                f"4. Evaluated evidence quality (score: {evidence_score}/100)",
                f"5. Detected {len(identified_biases)} potential bias indicators",
                f"6. Generated {len(alternative_perspectives)} alternative perspectives",
                f"7. Final confidence assessment: {adjusted_confidence}%",
            ],
            "assumptions": assumptions,
            "evidence_quality": {
                "score": evidence_score,
                "assessment": f"Based on {source_count} sources with average domain authority of {avg_domain_score:.0f}/100.",
            },
            "identified_biases": identified_biases,
            "alternative_perspectives": alternative_perspectives,
            "confidence_score": adjusted_confidence,
            "recommendations": recommendations,
            "uncertainties": uncertainties,
        }

    def _devil_advocate_without_llm(self, position: str) -> str:
        """Generate generic counter-arguments without LLM."""
        return (
            f"Counter-arguments to: '{position}'\n\n"
            f"1. **Unintended Consequences**: Implementing '{position}' may lead to "
            f"negative outcomes that were not initially anticipated. Changes often have "
            f"ripple effects across interconnected systems.\n\n"
            f"2. **Alternative Explanations**: The evidence supporting '{position}' may "
            f"have other valid interpretations. Correlation does not imply causation, and "
            f"multiple hypotheses may fit the observed data.\n\n"
            f"3. **Overgeneralization Risk**: '{position}' might be based on specific "
            f"contexts that do not generalize broadly. What works in one domain, culture, "
            f"or time period may not transfer elsewhere.\n\n"
            f"4. **Resource and Feasibility Concerns**: Even if '{position}' is "
            f"theoretically sound, practical implementation may require resources, "
            f"coordination, or infrastructure that is not currently available.\n\n"
            f"5. **Missing Stakeholder Perspectives**: '{position}' may not account for "
            f"the needs and concerns of all affected parties. Diverse viewpoints should "
            f"be incorporated for a balanced assessment.\n\n"
            f"Conclusion: While '{position}' has merit, these counter-arguments highlight "
            f"the importance of thorough critical examination before acceptance."
        )
