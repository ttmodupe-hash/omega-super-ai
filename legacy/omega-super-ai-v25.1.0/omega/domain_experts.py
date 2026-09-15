"""
Domain Experts Module — Omega Super AI v10

Professional domain knowledge covering ALL major professional fields.
Provides expert consultation, troubleshooting, best practices, and
safety warnings for safety-critical domains.

Each domain response includes a ``when_to_call_professional`` field to
guide users toward qualified human experts when appropriate.

Classes:
    DomainExperts: Multi-domain expert system with 13 professional fields.

Example:
    experts = DomainExperts(openai_client=client)
    result = experts.consult("plumbing", "How do I fix a leaky faucet?")
    guide = experts.get_domain_guide("medical", "first aid for burns")
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DomainExperts:
    """Multi-domain professional knowledge system.

    Covers 13 major professional fields with subfield detection,
    domain-specific best practices, safety warnings, and guidance
    on when to consult a licensed professional.

    Attributes:
        DOMAINS (dict): Mapping of domain names to metadata.
        openai_client: OpenAI-compatible API client.
    """

    DOMAINS: dict[str, dict[str, Any]] = {
        "engineering": {
            "subfields": ["civil", "mechanical", "electrical", "software", "chemical"],
            "description": "Design, build, and maintain structures, machines, and systems",
        },
        "architecture": {
            "subfields": ["residential", "commercial", "landscape", "urban"],
            "description": "Design buildings and spaces for human use",
        },
        "plumbing": {
            "subfields": ["residential", "commercial", "industrial", "emergency"],
            "description": "Install and repair pipe systems, fixtures, and water systems",
        },
        "medical": {
            "subfields": ["general", "emergency", "preventive", "mental_health"],
            "description": "Health, wellness, and medical guidance (NOT a substitute for professional care)",
        },
        "legal": {
            "subfields": ["contracts", "property", "labor", "criminal"],
            "description": "Legal information and guidance (NOT legal advice)",
        },
        "education": {
            "subfields": ["teaching", "curriculum", "assessment", "special_ed"],
            "description": "Educational methods, strategies, and best practices",
        },
        "it_support": {
            "subfields": ["networking", "hardware", "software", "cybersecurity"],
            "description": "Technical support, troubleshooting, and IT guidance",
        },
        "agriculture": {
            "subfields": ["crop", "livestock", "sustainable", "machinery"],
            "description": "Farming, cultivation, and agricultural best practices",
        },
        "automotive": {
            "subfields": ["repair", "maintenance", "diagnostics", "electric"],
            "description": "Vehicle care, repair, and maintenance guidance",
        },
        "culinary": {
            "subfields": ["cooking", "baking", "food_safety", "nutrition"],
            "description": "Cooking techniques, recipes, and food safety",
        },
        "finance": {
            "subfields": ["personal", "corporate", "investment", "accounting"],
            "description": "Financial concepts, planning, and analysis",
        },
        "construction": {
            "subfields": ["residential", "commercial", "renovation", "safety"],
            "description": "Building, renovation, and construction safety",
        },
        "beauty": {
            "subfields": ["hair", "skincare", "nails", "makeup"],
            "description": "Beauty techniques, products, and best practices",
        },
    }

    # Domain-specific safety-critical flags
    SAFETY_CRITICAL: set[str] = {"medical", "legal", "construction", "plumbing", "automotive", "electrical"}

    # Professional-call triggers by domain
    PRO_TRIGGERS: dict[str, list[str]] = {
        "medical": [
            "chest pain", "difficulty breathing", "severe bleeding",
            "loss of consciousness", "poisoning", "suicide", "emergency",
            "prescription", "diagnosis", "broken bone", "allergic reaction",
            "stroke", "heart attack", "overdose", "seizure",
        ],
        "legal": [
            "lawsuit", "court", "arrested", "charged", "subpoena",
            "divorce", "custody", "will", "estate", "patent",
            "trademark", "incorporation", "criminal", "felony",
        ],
        "plumbing": [
            "gas leak", "sewage", "main line", "water heater explosion",
            "flooding", "structural damage",
        ],
        "construction": [
            "structural", "foundation", "load-bearing", "permit",
            "electrical panel", "gas line", "roof collapse",
        ],
        "automotive": [
            "airbag", "brake failure", "steering failure", "recall",
            "transmission", "engine rebuild",
        ],
        "engineering": [
            "structural failure", "safety-critical", "bridge", "dam",
        ],
    }

    def __init__(self, openai_client: Any) -> None:
        """Initialize DomainExperts with an AI client.

        Args:
            openai_client: An initialized OpenAI-compatible API client.
        """
        self.openai_client = openai_client
        logger.info("DomainExperts initialized with %d domains", len(self.DOMAINS))

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _chat(self, system: str, user: str, temperature: float = 0.6) -> str:
        """Call the OpenAI-compatible chat endpoint safely.

        Args:
            system: System-level instructions.
            user: User message.
            temperature: Sampling temperature.

        Returns:
            Model response text or an error string.
        """
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("OpenAI API error: %s", exc)
            return f"[Error contacting AI service: {exc}]"

    def _safe_json(self, text: str) -> Any:
        """Parse JSON from model output, stripping markdown fences."""
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                logger.error("JSON parse error: %s", exc)
                return {"error": "Failed to parse JSON", "raw": text}

    def _detect_subfield(self, domain: str, question: str) -> str:
        """Heuristically detect the most relevant subfield.

        Args:
            domain: The domain key.
            question: The user's question text.

        Returns:
            The best-matching subfield name or ``"general"``.
        """
        question_lower = question.lower()
        subfields = self.DOMAINS.get(domain, {}).get("subfields", [])
        for sf in subfields:
            if sf.replace("_", " ") in question_lower or sf in question_lower:
                return sf
        return "general"

    def _should_call_professional(self, domain: str, question: str) -> tuple[bool, list[str]]:
        """Check whether the question triggers professional-consultation advice.

        Args:
            domain: The domain key.
            question: The user's question.

        Returns:
            ``(should_call, reasons)`` tuple.
        """
        triggers = self.PRO_TRIGGERS.get(domain, [])
        matched = [t for t in triggers if t.lower() in question.lower()]
        return bool(matched), matched

    def _domain_system_prompt(self, domain: str, detail_level: str) -> str:
        """Build a domain-specific system prompt."""
        meta = self.DOMAINS.get(domain, {})
        subfields = ", ".join(meta.get("subfields", []))
        description = meta.get("description", "")

        safety_note = ""
        if domain == "medical":
            safety_note = (
                "\n\nCRITICAL: You are NOT a medical professional. "
                "Always remind the user to consult a licensed healthcare provider "
                "for diagnosis, treatment, or emergency care. "
                "Never provide specific medical diagnoses or prescribe treatments."
            )
        elif domain == "legal":
            safety_note = (
                "\n\nCRITICAL: You are NOT a lawyer. This is general legal information only, "
                "not legal advice. Always recommend consulting a licensed attorney "
                "for specific legal matters."
            )
        elif domain in ("construction", "plumbing"):
            safety_note = (
                "\n\nSAFETY: Always emphasize proper safety equipment and permits. "
                "Recommend professional help for hazardous work."
            )

        return (
            f"You are an expert {domain} consultant with deep knowledge across "
            f"subfields: {subfields}.\n"
            f"Domain description: {description}\n"
            f"Provide {detail_level} responses with best practices, common mistakes, "
            f"safety warnings, and relevant code standards or regulations."
            f"{safety_note}"
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def consult(
        self,
        domain: str,
        question: str,
        detail_level: str = "comprehensive",
    ) -> dict[str, Any]:
        """Expert consultation for the specified domain.

        Uses a domain-specific system prompt to generate authoritative
        guidance including best practices, safety warnings, and
        professional-consultation triggers.

        Args:
            domain: One of the keys in :attr:`DOMAINS`.
            question: The user's question.
            detail_level: ``"brief"``, ``"comprehensive"``, or ``"detailed"``.

        Returns:
            A dictionary with the answer, best practices, safety warnings,
            and guidance on when to call a professional.
        """
        domain = domain.lower().strip()
        if domain not in self.DOMAINS:
            return {
                "domain": domain,
                "error": f"Unknown domain '{domain}'. Available: {list(self.DOMAINS.keys())}",
            }

        subfield = self._detect_subfield(domain, question)
        should_call, trigger_reasons = self._should_call_professional(domain, question)

        system = self._domain_system_prompt(domain, detail_level)
        user_prompt = (
            f"Domain: {domain}\n"
            f"Detected subfield: {subfield}\n"
            f"Question: {question}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "domain": "string",\n'
            '  "subfield_detected": "string",\n'
            '  "question": "string",\n'
            '  "answer": "string (comprehensive answer)",\n'
            '  "best_practices": ["string"],\n'
            '  "common_mistakes": ["string"],\n'
            '  "safety_warnings": ["string"],\n'
            '  "code_standards": ["string"],\n'
            '  "resources": ["string"],\n'
            '  "when_to_call_professional": "string"\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.6)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            data["domain"] = domain
            data["subfield_detected"] = subfield
            data["question"] = question
            if should_call:
                data["when_to_call_professional"] = (
                    f"This question involves topics that require a licensed "
                    f"professional: {', '.join(trigger_reasons)}. "
                    f"Please consult a qualified {domain} professional."
                )
            return data

        # Fallback
        return {
            "domain": domain,
            "subfield_detected": subfield,
            "question": question,
            "answer": f"Here is general guidance for {domain}: {question}",
            "best_practices": ["Follow industry standards", "Use proper safety equipment"],
            "common_mistakes": ["Skipping safety protocols", "Using wrong materials"],
            "safety_warnings": ["Always follow safety guidelines"],
            "code_standards": ["Refer to relevant industry codes"],
            "resources": [f"Professional {domain} associations", "Industry publications"],
            "when_to_call_professional": (
                f"Consult a licensed {domain} professional for complex, dangerous, "
                f"or regulated work."
            ),
        }

    def list_domains(self) -> list[dict[str, Any]]:
        """Return all available domains with descriptions.

        Returns:
            A list of domain metadata dictionaries.
        """
        return [
            {
                "name": name,
                "subfields": info["subfields"],
                "description": info["description"],
                "safety_critical": name in self.SAFETY_CRITICAL,
            }
            for name, info in self.DOMAINS.items()
        ]

    def get_domain_guide(self, domain: str, topic: str) -> dict[str, Any]:
        """Get a detailed guide on a specific topic within a domain.

        Args:
            domain: Domain key (e.g. ``"plumbing"``).
            topic: Specific topic within the domain.

        Returns:
            A structured guide with sections and references.
        """
        domain = domain.lower().strip()
        if domain not in self.DOMAINS:
            return {
                "domain": domain,
                "topic": topic,
                "error": f"Unknown domain. Available: {list(self.DOMAINS.keys())}",
            }

        system = self._domain_system_prompt(domain, "detailed")
        user_prompt = (
            f"Create a detailed guide on '{topic}' within {domain}.\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "domain": "string",\n'
            '  "topic": "string",\n'
            '  "overview": "string",\n'
            '  "sections": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "content": "string (detailed)",\n'
            '      "key_points": ["string"]\n'
            "    }\n"
            "  ],\n"
            '  "tools_needed": ["string"],\n'
            '  "materials": ["string"],\n'
            '  "estimated_time": "string",\n'
            '  "difficulty": "Beginner|Intermediate|Advanced",\n'
            '  "safety_precautions": ["string"],\n'
            '  "cost_estimate": "string",\n'
            '  "when_to_hire_professional": "string",\n'
            '  "regulations": ["string"],\n'
            '  "resources": ["string"]\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.6)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return data

        return {
            "domain": domain,
            "topic": topic,
            "overview": f"Guide to {topic} in {domain}",
            "sections": [
                {
                    "title": "Introduction",
                    "content": f"Overview of {topic} in {domain}",
                    "key_points": ["Understand the basics"],
                }
            ],
            "tools_needed": ["Basic tools"],
            "materials": ["Standard materials"],
            "estimated_time": "Varies",
            "difficulty": "Intermediate",
            "safety_precautions": ["Follow safety guidelines"],
            "cost_estimate": "Varies by scope",
            "when_to_hire_professional": (
                f"Hire a professional for complex or regulated {domain} work."
            ),
            "regulations": ["Check local regulations"],
            "resources": [f"{domain} professional associations"],
        }

    def troubleshoot(self, domain: str, problem: str) -> dict[str, Any]:
        """Step-by-step troubleshooting for domain-specific problems.

        Args:
            domain: Domain key.
            problem: Description of the problem.

        Returns:
            A structured troubleshooting guide with diagnostic steps,
            likely causes, solutions, and prevention tips.
        """
        domain = domain.lower().strip()
        if domain not in self.DOMAINS:
            return {
                "domain": domain,
                "problem": problem,
                "error": f"Unknown domain. Available: {list(self.DOMAINS.keys())}",
            }

        system = (
            f"You are a {domain} troubleshooting expert. "
            "Provide systematic diagnostic steps, root-cause analysis, "
            "and practical solutions. Prioritize safety at every step."
        )
        user_prompt = (
            f"Domain: {domain}\n"
            f"Problem: {problem}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "problem": "string",\n'
            '  "domain": "string",\n'
            '  "urgency": "LOW|MEDIUM|HIGH|CRITICAL",\n'
            '  "diagnostic_steps": [\n'
            '    {"step": 1, "action": "string", "what_to_look_for": "string"}\n'
            "  ],\n"
            '  "likely_causes": [\n'
            '    {"cause": "string", "probability": "High|Medium|Low", "how_to_verify": "string"}\n'
            "  ],\n"
            '  "solutions": [\n'
            '    {"solution": "string", "difficulty": "Easy|Medium|Hard", "cost": "string", "time": "string"}\n'
            "  ],\n"
            '  "prevention": ["string"],\n'
            '  "safety_warnings": ["string"],\n'
            '  "when_to_call_expert": "string"\n'
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.6)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return data

        return {
            "problem": problem,
            "domain": domain,
            "urgency": "MEDIUM",
            "diagnostic_steps": [
                {
                    "step": 1,
                    "action": f"Inspect the {problem} carefully",
                    "what_to_look_for": "Visible signs of damage or malfunction",
                }
            ],
            "likely_causes": [
                {
                    "cause": "General wear and tear",
                    "probability": "Medium",
                    "how_to_verify": "Visual inspection",
                }
            ],
            "solutions": [
                {
                    "solution": "Basic maintenance or repair",
                    "difficulty": "Medium",
                    "cost": "Moderate",
                    "time": "1-2 hours",
                }
            ],
            "prevention": ["Regular maintenance", "Early problem detection"],
            "safety_warnings": ["Ensure power is off before inspection"],
            "when_to_call_expert": (
                f"If the problem persists after basic troubleshooting or involves safety risks, "
                f"contact a licensed {domain} professional."
            ),
        }
