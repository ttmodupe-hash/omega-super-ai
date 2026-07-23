"""Omega AI v3.7.0 — Pedagogical Engine: Elite Tri-Agent Learning System
World-class educational framework modeled after top-tier professors, master trainers,
and cognitive scientists. Three specialized agents work in synchrony:

- Agent_Socrates: Scaffolded instruction, Socratic method, adaptive explanations
- Agent_Bjork: Cognitive Ledger, spaced repetition, retrieval cues, desirable difficulties
- Agent_Bloom: Bloom's Taxonomy enforcement, mastery gating, context purge

Features:
- Cognitive Ledger tracking per student
- Retrieval Intercept (spaced repetition flashbacks)
- Progression Lock (no new topics without mastery)
- Bloom's Taxonomy level progression (Remember→Create)
- Context Purge Mandate (archive mastered topics)
- Diagnostic quizzes before topic unlock
- Desirable difficulties tracking
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# BLOOM'S TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════════

class BloomLevel(str, Enum):
    REMEMBER = "remember"       # Recall facts
    UNDERSTAND = "understand"   # Explain concepts
    APPLY = "apply"             # Use in new situations
    ANALYZE = "analyze"         # Break down relationships
    EVALUATE = "evaluate"       # Justify decisions
    CREATE = "create"           # Produce original work


BLOOM_ORDER = [BloomLevel.REMEMBER, BloomLevel.UNDERSTAND, BloomLevel.APPLY,
               BloomLevel.ANALYZE, BloomLevel.EVALUATE, BloomLevel.CREATE]

BLOOM_VERBS: dict[str, list[str]] = {
    "remember": ["define", "list", "recall", "identify", "name", "state", "describe"],
    "understand": ["explain", "summarize", "paraphrase", "compare", "classify", "interpret"],
    "apply": ["demonstrate", "use", "solve", "implement", "calculate", "apply"],
    "analyze": ["break down", "analyze", "differentiate", "relate", "distinguish", "examine"],
    "evaluate": ["justify", "evaluate", "critique", "defend", "recommend", "assess"],
    "create": ["design", "create", "invent", "compose", "construct", "devise"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConceptMastery:
    """Tracks a student's mastery of a single concept through Bloom's levels."""
    concept: str
    domain: str
    bloom_level: str = BloomLevel.REMEMBER
    status: str = "active"       # active | passed | archived
    created_at: float = 0.0
    last_tested: float = 0.0
    test_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    ledger_summary: str = ""      # Compact 1-sentence mastery summary
    difficulties: list[str] = field(default_factory=list)  # Weak areas
    prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def current_level_idx(self) -> int:
        return BLOOM_ORDER.index(BloomLevel(self.bloom_level))

    @property
    def is_mastered(self) -> bool:
        return self.status == "passed" and self.bloom_level == BloomLevel.CREATE

    @property
    def needs_retrieval_test(self) -> bool:
        """True if enough time has passed for spaced repetition."""
        if self.status != "passed":
            return False
        elapsed = time.time() - self.last_tested
        # Spaced repetition intervals: 1 day, 3 days, 7 days, 14 days, 30 days
        intervals = [86400, 259200, 604800, 1209600, 2592000]
        idx = min(self.pass_count - 1, len(intervals) - 1)
        return elapsed >= intervals[idx]


@dataclass
class CognitiveLedger:
    """The student's compact learning state — printed every turn."""
    student_id: str
    domain: str = ""
    concepts: dict[str, ConceptMastery] = field(default_factory=dict)
    current_focus: str = ""
    ledger_entries: list[str] = field(default_factory=list)
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "domain": self.domain,
            "current_focus": self.current_focus,
            "concept_count": len(self.concepts),
            "mastered_count": sum(1 for c in self.concepts.values() if c.is_mastered),
            "updated_at": self.updated_at,
        }

    def format_output(self) -> str:
        """Format the ledger for display to the student."""
        lines = [
            "",
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "┃                  [COGNITIVE LEDGER]                          ┃",
            "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫",
        ]

        # Current Focus
        focus = self.current_focus or "Awaiting domain selection..."
        lines.append(f"┃ [Current Core Focus]: {focus[:52]:52} ┃")
        lines.append("┃                                                              ┃")

        # Desirable Difficulties (weak areas needing spaced repetition)
        difficulties = []
        for c in self.concepts.values():
            if c.status == "passed" and c.needs_retrieval_test:
                difficulties.append(f"{c.concept} (L{c.current_level_idx + 1})")
            elif c.difficulties:
                difficulties.extend([f"{c.concept}/{d}" for d in c.difficulties[:2]])
        if difficulties:
            lines.append(f"┃ [Desirable Difficulties]: {', '.join(difficulties[:4])[:46]:46} ┃")
        else:
            lines.append(f"┃ [Desirable Difficulties]: None — all caught up!             ┃")
        lines.append("┃                                                              ┃")

        # Mastered & Compacted
        mastered = [c for c in self.concepts.values() if c.status == "passed"]
        if mastered:
            for c in mastered[:3]:
                summary = c.ledger_summary or f"{c.concept}: {c.bloom_level}"
                lines.append(f"┃ [Mastered]: {summary[:56]:56} ┃")
            if len(mastered) > 3:
                lines.append(f"┃         ... and {len(mastered) - 3} more mastered concepts{'':23} ┃")
        else:
            lines.append(f"┃ [Mastered]: None yet — let's build!{'':24} ┃")

        lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        return "\n".join(lines)


@dataclass
class DiagnosticQuestion:
    """A Bloom's-aligned diagnostic question."""
    concept: str
    bloom_level: str
    question: str
    expected_answer_keywords: list[str]
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT_SOCRATES: The Master Educator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentSocrates:
    """Scaffolded instruction, Socratic method, adaptive explanations.

    - Never gives answers away; guides the student to derive them
    - Adapts dynamically based on cognitive load and vocabulary
    - Uses analogies, scaffolding, and guided discovery
    """

    def __init__(self) -> None:
        self.teaching_cache: dict[str, str] = {}

    def guide(self, concept: str, student_response: str = "", context: dict | None = None) -> str:
        """Generate a Socratic guiding response — never a direct answer."""
        ctx = context or {}
        level = ctx.get("bloom_level", "remember")
        difficulty = ctx.get("difficulty", "medium")
        hints_used = ctx.get("hints_used", 0)

        # If student is stuck, provide a hint, not the answer
        if student_response and ("don't know" in student_response.lower() or
                                  "confused" in student_response.lower() or
                                  "?" == student_response.strip()):
            hints = self._generate_hints(concept, level)
            if hints_used < len(hints):
                return (f"That's okay — let's explore together.\n\n"
                        f"💡 Hint {hints_used + 1}: {hints[hints_used]}\n\n"
                        f"What do you think this tells us about {concept}?")
            return (f"No worries. Let's approach {concept} from a different angle.\n\n"
                    f"Think about: What would happen if {concept} did NOT work this way?\n"
                    f"Take your time and share whatever comes to mind.")

        # Normal Socratic guidance
        prompts = self._socratic_prompts(concept, level)
        return random.choice(prompts)

    def explain_adaptive(self, concept: str, student_level: str = "intermediate") -> str:
        """Generate an adaptive explanation that doesn't give the answer directly."""
        analogies = self._get_analogies(concept)
        if analogies:
            analogy = random.choice(analogies)
            return (f"To understand {concept}, let's think about something familiar:\n\n"
                    f"🔄 Analogy: {analogy}\n\n"
                    f"How do you think this relates to what we're exploring?")
        return (f"Let's break down {concept} step by step.\n"
                f"What do you already know about this topic? Even small details help.")

    def celebrate_progress(self, concept: str, level: str) -> str:
        """Celebrate when a student advances a Bloom level."""
        messages = [
            f"🎯 Excellent! You've demonstrated **{level.upper()}** of *{concept}*!",
            f"⭐ Strong work — your grasp of *{concept}* is deepening at the **{level.upper()}** level!",
            f"🏆 Outstanding! You're operating at **{level.upper()}** for *{concept}*!",
        ]
        return random.choice(messages)

    def _generate_hints(self, concept: str, level: str) -> list[str]:
        """Generate progressively revealing hints."""
        return [
            f"Think about the key components that make {concept} work.",
            f"Consider what would change if one part of {concept} were removed.",
            f"Reflect on how {concept} connects to something you already know well.",
        ]

    def _socratic_prompts(self, concept: str, level: str) -> list[str]:
        """Generate Socratic questions based on Bloom level."""
        prompts = {
            "remember": [
                f"What are the key facts or definitions associated with {concept}?",
                f"Can you list the main components of {concept}?",
                f"How would you describe {concept} to someone who has never heard of it?",
            ],
            "understand": [
                f"In your own words, how does {concept} work?",
                f"What is the relationship between {concept} and its inputs/outputs?",
                f"Can you explain {concept} using a real-world example?",
            ],
            "apply": [
                f"How would you apply {concept} to solve [a practical problem]?",
                f"Given [a scenario], how would you use {concept} here?",
                f"Walk me through implementing {concept} step by step.",
            ],
            "analyze": [
                f"What are the assumptions underlying {concept}?",
                f"How does {concept} differ from [similar concept]?",
                f"Break down {concept} — what are its cause-and-effect relationships?",
            ],
            "evaluate": [
                f"What are the strengths and limitations of {concept}?",
                f"Under what conditions does {concept} work best? When does it fail?",
                f"How would you defend {concept} against common criticisms?",
            ],
            "create": [
                f"How would you extend or improve {concept}?",
                f"Design a new application that uses {concept} in an innovative way.",
                f"If you were to teach {concept} to a beginner, how would you structure it?",
            ],
        }
        return prompts.get(level, prompts["remember"])

    def _get_analogies(self, concept: str) -> list[str]:
        """Get analogies for a concept."""
        # Core analogies for common CS/math/science concepts
        analogies_db = {
            "recursion": [
                "Russian nesting dolls — each doll contains a smaller version of itself, until you reach the smallest one.",
                "Two mirrors facing each other — each reflection contains a smaller reflection, going on infinitely (theoretically).",
            ],
            "algorithm": [
                "A recipe in a cookbook — precise step-by-step instructions that anyone can follow to get the same result.",
                "Assembly instructions for IKEA furniture — steps must be followed in order for the final product to work.",
            ],
            "database": [
                "A well-organized library — books (data) are catalogued (indexed) so the librarian can find any book quickly.",
                "A filing cabinet with labeled drawers — each drawer is a table, each folder a row.",
            ],
            "neural network": [
                "The human brain's neuron structure — interconnected cells that strengthen connections based on repeated patterns.",
                "A factory assembly line where workers pass partially completed products to the next station.",
            ],
            "api": [
                "A restaurant menu — you (the client) order from the menu (API), and the kitchen (server) prepares it.",
                "A translator at a UN meeting — bridges two parties who speak different languages.",
            ],
        }
        return analogies_db.get(concept.lower(), [])


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT_BJORK: The Cognitive Historian
# ═══════════════════════════════════════════════════════════════════════════════

class AgentBjork:
    """Manages long-term retrieval cues, spaced repetition, desirable difficulties.

    Named after Robert Bjork (desirable difficulties, spacing effects).
    - Maintains the Cognitive Ledger per student
    - Tracks desirable difficulties (weak areas needing work)
    - Handles Retrieval Intercept (spaced repetition flashbacks)
    - Compacts mastered topics into single-sentence summaries
    """

    def __init__(self, persist_path: str = ".omega_sessions/cognitive_ledgers.json") -> None:
        self._persist_path = persist_path
        self._ledgers: dict[str, CognitiveLedger] = {}
        self._load()

    def _load(self) -> None:
        path = Path(self._persist_path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for sid, ledger_data in data.items():
                    concepts = {}
                    for cid, cd in ledger_data.get("concepts", {}).items():
                        concepts[cid] = ConceptMastery(**cd)
                    self._ledgers[sid] = CognitiveLedger(
                        student_id=sid,
                        domain=ledger_data.get("domain", ""),
                        concepts=concepts,
                        current_focus=ledger_data.get("current_focus", ""),
                        ledger_entries=ledger_data.get("ledger_entries", []),
                        updated_at=ledger_data.get("updated_at", 0),
                    )
            except Exception:
                pass

    def _save(self) -> None:
        try:
            Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for sid, ledger in self._ledgers.items():
                data[sid] = {
                    "student_id": sid,
                    "domain": ledger.domain,
                    "concepts": {cid: c.to_dict() for cid, c in ledger.concepts.items()},
                    "current_focus": ledger.current_focus,
                    "ledger_entries": ledger.ledger_entries,
                    "updated_at": time.time(),
                }
            Path(self._persist_path).write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def get_or_create_ledger(self, student_id: str) -> CognitiveLedger:
        if student_id not in self._ledgers:
            self._ledgers[student_id] = CognitiveLedger(student_id=student_id)
        return self._ledgers[student_id]

    def set_domain(self, student_id: str, domain: str) -> None:
        ledger = self.get_or_create_ledger(student_id)
        ledger.domain = domain
        ledger.updated_at = time.time()
        self._save()

    def set_focus(self, student_id: str, concept: str) -> None:
        ledger = self.get_or_create_ledger(student_id)
        ledger.current_focus = concept
        ledger.updated_at = time.time()
        self._save()

    def add_concept(self, student_id: str, concept: str, domain: str = "",
                    prerequisites: list[str] | None = None) -> ConceptMastery:
        ledger = self.get_or_create_ledger(student_id)
        if concept not in ledger.concepts:
            ledger.concepts[concept] = ConceptMastery(
                concept=concept,
                domain=domain or ledger.domain,
                created_at=time.time(),
                last_tested=time.time(),
                prerequisites=prerequisites or [],
            )
            self._save()
        return ledger.concepts[concept]

    def record_test_result(self, student_id: str, concept: str, passed: bool,
                           difficulty_notes: list[str] | None = None) -> ConceptMastery:
        ledger = self.get_or_create_ledger(student_id)
        if concept not in ledger.concepts:
            return self.add_concept(student_id, concept)

        cm = ledger.concepts[concept]
        cm.test_count += 1
        cm.last_tested = time.time()

        if passed:
            cm.pass_count += 1
            cm.fail_count = max(0, cm.fail_count - 1)
            # Advance Bloom level if enough passes at current level
            if cm.pass_count >= 2:  # Need 2 passes to advance
                self._advance_bloom(cm)
        else:
            cm.fail_count += 1
            if difficulty_notes:
                cm.difficulties.extend(difficulty_notes)
                cm.difficulties = cm.difficulties[-5:]  # Keep last 5

        ledger.updated_at = time.time()
        self._save()
        return cm

    def _advance_bloom(self, cm: ConceptMastery) -> None:
        """Advance concept to next Bloom level."""
        try:
            current_idx = BLOOM_ORDER.index(BloomLevel(cm.bloom_level))
            if current_idx < len(BLOOM_ORDER) - 1:
                cm.bloom_level = BLOOM_ORDER[current_idx + 1].value
                cm.pass_count = 0  # Reset pass count for new level
                cm.difficulties = []
        except ValueError:
            pass

    def compact_concept(self, student_id: str, concept: str, summary: str) -> None:
        """Create a compact mastery summary for an archived concept."""
        ledger = self.get_or_create_ledger(student_id)
        if concept in ledger.concepts:
            ledger.concepts[concept].ledger_summary = summary
            ledger.concepts[concept].status = "passed"
            ledger.ledger_entries.append(summary)
            ledger.ledger_entries = ledger.ledger_entries[-20:]  # Keep last 20
            ledger.updated_at = time.time()
            self._save()

    def get_retrieval_candidates(self, student_id: str, max_count: int = 3) -> list[ConceptMastery]:
        """Get concepts that need spaced repetition testing."""
        ledger = self.get_or_create_ledger(student_id)
        candidates = [c for c in ledger.concepts.values() if c.needs_retrieval_test]
        return sorted(candidates, key=lambda c: c.last_tested)[:max_count]

    def get_pending_concepts(self, student_id: str) -> list[ConceptMastery]:
        """Get concepts not yet mastered."""
        ledger = self.get_or_create_ledger(student_id)
        return [c for c in ledger.concepts.values() if c.status == "active"]

    def print_ledger(self, student_id: str) -> str:
        """Print the Cognitive Ledger for a student."""
        ledger = self.get_or_create_ledger(student_id)
        return ledger.format_output()

    def stats(self, student_id: str) -> dict[str, Any]:
        ledger = self.get_or_create_ledger(student_id)
        concepts = list(ledger.concepts.values())
        return {
            "student_id": student_id,
            "domain": ledger.domain,
            "total_concepts": len(concepts),
            "mastered": sum(1 for c in concepts if c.is_mastered),
            "in_progress": sum(1 for c in concepts if c.status == "active"),
            "avg_bloom_level": sum(c.current_level_idx for c in concepts) / len(concepts) if concepts else 0,
            "retrieval_due": len(self.get_retrieval_candidates(student_id)),
            "current_focus": ledger.current_focus,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT_BLOOM: The Mastery Gatekeeper & Purge Engine
# ═══════════════════════════════════════════════════════════════════════════════

class AgentBloom:
    """Enforces Bloom's Taxonomy, blocks progression until mastery verified.

    Named after Benjamin Bloom (Bloom's Taxonomy of Learning).
    - Issues diagnostic questions before topic unlock
    - Evaluates student responses against expected answers
    - Triggers Context Purge Mandate when mastery achieved
    - Never allows progression without [STATUS: PASS]
    """

    def __init__(self) -> None:
        self._question_bank: dict[str, list[DiagnosticQuestion]] = self._build_question_bank()

    def generate_diagnostic(self, concept: str, level: str | None = None) -> DiagnosticQuestion | None:
        """Generate a Bloom-aligned diagnostic question for a concept."""
        questions = self._question_bank.get(concept.lower(), [])
        if not questions:
            # Generate a generic question
            return self._generate_generic_question(concept, level or "remember")
        if level:
            filtered = [q for q in questions if q.bloom_level == level]
            if filtered:
                return random.choice(filtered)
        return random.choice(questions)

    def evaluate_response(self, question: DiagnosticQuestion, student_response: str) -> dict[str, Any]:
        """Evaluate a student's response to a diagnostic question."""
        response_lower = student_response.lower()
        matched_keywords = [kw for kw in question.expected_answer_keywords
                            if kw.lower() in response_lower]
        match_ratio = len(matched_keywords) / len(question.expected_answer_keywords) if question.expected_answer_keywords else 0.5

        # Need at least 60% keyword match to pass
        passed = match_ratio >= 0.6 and len(student_response) > 15

        if passed:
            return {
                "passed": True,
                "match_ratio": round(match_ratio, 2),
                "matched_keywords": matched_keywords,
                "status": "[STATUS: PASS]",
                "feedback": f"✅ Strong answer! You demonstrated understanding of {question.concept}.",
                "next_level": self._next_bloom_level(question.bloom_level),
            }
        else:
            hints = question.hints[:2] if question.hints else [
                f"Think about the key principles of {question.concept}.",
                f"Consider a concrete example involving {question.concept}.",
            ]
            return {
                "passed": False,
                "match_ratio": round(match_ratio, 2),
                "matched_keywords": matched_keywords,
                "status": "[STATUS: NEEDS_WORK]",
                "feedback": f"💡 Not quite there yet. Here are some hints:\n" + "\n".join(f"  • {h}" for h in hints),
                "hints": hints,
            }

    def generate_purge_mandate(self, concept: str) -> str:
        """Generate the Context Purge Mandate message."""
        return (
            f"\n✨ **[WORLD-CLASS MASTERY RECORDED]**: You have demonstrated deep conceptual "
            f"mastery of **{concept}**.\n\n"
            f"To maintain a clean, ultra-high-fidelity active memory environment and prevent "
            f"chat lag/hallucinations, this raw conversation thread must be recycled.\n\n"
            f"👉 **Reply 'COMPACT'** to archive this into your permanent [Cognitive Ledger] "
            f"and wipe the raw text from my active history.\n"
        )

    def can_progress(self, concept_mastery: ConceptMastery) -> bool:
        """Check if student can progress past this concept."""
        return concept_mastery.status == "passed" and concept_mastery.pass_count >= 2

    def generate_quiz(self, concept: str, bloom_level: str) -> str:
        """Generate a quiz question for a concept at a specific Bloom level."""
        verbs = BLOOM_VERBS.get(bloom_level, ["explain"])
        verb = random.choice(verbs)
        templates = {
            "remember": [
                f"**{verb.upper()}** {concept}: What are its core definitions and key facts?",
                f"List the 3 most important things to remember about {concept}.",
            ],
            "understand": [
                f"**{verb.upper()}** {concept}: How would you explain it to a 12-year-old?",
                f"In your own words, describe how {concept} works and why it matters.",
            ],
            "apply": [
                f"**{verb.upper()}** {concept}: Describe a real-world scenario where you'd use it.",
                f"Walk me through applying {concept} to solve a practical problem.",
            ],
            "analyze": [
                f"**{verb.upper()}** {concept}: Break it into components. How do they interact?",
                f"Compare {concept} with an alternative approach. What are the trade-offs?",
            ],
            "evaluate": [
                f"**{verb.upper()}** {concept}: What are its strengths and key limitations?",
                f"Defend when {concept} is the best choice versus when to avoid it.",
            ],
            "create": [
                f"**{verb.upper()}** using {concept}: Propose an original extension or improvement.",
                f"How would you combine {concept} with another concept to build something new?",
            ],
        }
        return random.choice(templates.get(bloom_level, templates["remember"]))

    @staticmethod
    def _next_bloom_level(current: str) -> str:
        try:
            idx = BLOOM_ORDER.index(BloomLevel(current))
            if idx < len(BLOOM_ORDER) - 1:
                return BLOOM_ORDER[idx + 1].value
            return current
        except ValueError:
            return "understand"

    def _generate_generic_question(self, concept: str, level: str) -> DiagnosticQuestion:
        verbs = BLOOM_VERBS.get(level, ["explain"])
        verb = random.choice(verbs)
        return DiagnosticQuestion(
            concept=concept,
            bloom_level=level,
            question=f"{verb.upper()} the concept of '{concept}' and its significance.",
            expected_answer_keywords=[concept.lower(), "because", "therefore"],
            hints=[f"Think about what makes {concept} unique.",
                   f"Consider why someone would use {concept} over alternatives."],
        )

    def _build_question_bank(self) -> dict[str, list[DiagnosticQuestion]]:
        """Build a bank of diagnostic questions for common concepts."""
        return {
            "recursion": [
                DiagnosticQuestion("recursion", "remember",
                    "Define recursion and identify its two essential components.",
                    ["base case", "recursive case", "self-referential", "calls itself"]),
                DiagnosticQuestion("recursion", "understand",
                    "Explain why a base case is absolutely necessary in every recursive function.",
                    ["infinite loop", "stack overflow", "termination", "stop"]),
                DiagnosticQuestion("recursion", "apply",
                    "Write pseudocode for a recursive factorial function and trace factorial(4).",
                    ["factorial(n-1)", "return 1", "base", "24"]),
            ],
            "algorithm": [
                DiagnosticQuestion("algorithm", "remember",
                    "What are the three properties every algorithm must have?",
                    ["finite", "well-defined", "effective", "input", "output"]),
                DiagnosticQuestion("algorithm", "analyze",
                    "Compare O(n log n) and O(n²). When does each become impractical?",
                    ["quadratic", "merge sort", "bubble sort", "million", "scaling"]),
            ],
            "neural network": [
                DiagnosticQuestion("neural network", "remember",
                    "Name the three layers of a basic neural network and their roles.",
                    ["input", "hidden", "output", "weights", "activation"]),
                DiagnosticQuestion("neural network", "evaluate",
                    "Evaluate when a neural network is appropriate versus a decision tree.",
                    ["black box", "interpretability", "large dataset", "pattern"]),
            ],
            "database": [
                DiagnosticQuestion("database", "remember",
                    "What is the difference between SQL and NoSQL databases?",
                    ["relational", "schema", "flexible", "structured", "document"]),
                DiagnosticQuestion("database", "apply",
                    "Design a database schema for a library system. What tables and relationships?",
                    ["books", "authors", "borrowers", "primary key", "foreign key"]),
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED PEDAGOGICAL ENGINE — Coordinator
# ═══════════════════════════════════════════════════════════════════════════════

class PedagogicalEngine:
    """Unified interface coordinating Socrates, Bjork, and Bloom."""

    def __init__(self) -> None:
        self.socrates = AgentSocrates()
        self.bjork = AgentBjork()
        self.bloom = AgentBloom()

    # ── Student lifecycle ──

    def initialize_student(self, student_id: str, domain: str) -> str:
        """Initialize a new student with a domain of expertise."""
        self.bjork.set_domain(student_id, domain)
        ledger = self.bjork.get_or_create_ledger(student_id)

        welcome = (
            f"Welcome to your personalized mastery journey in **{domain}**! 🎓\n\n"
            f"I operate as three synchronized learning agents:\n"
            f"  🧠 **Socrates** — guides you through scaffolded discovery\n"
            f"  📊 **Bjork** — tracks your cognitive state and retrieval cues\n"
            f"  🛡️ **Bloom** — enforces mastery gates at each level\n\n"
            f"Here's your starting Cognitive Ledger:{self.bjork.print_ledger(student_id)}\n\n"
            f"Let's begin! What specific concept within **{domain}** would you like to explore?\n"
            f"(Or I can suggest a learning path for you.)"
        )
        return welcome

    def start_concept(self, student_id: str, concept: str) -> str:
        """Begin learning a new concept — triggers Retrieval Intercept first."""
        self.bjork.add_concept(student_id, concept)
        self.bjork.set_focus(student_id, concept)

        # Retrieval Intercept: test previous knowledge before new material
        retrieval = self._retrieval_intercept(student_id)

        if retrieval:
            return (
                f"🔔 **Retrieval Intercept**: Before we explore *{concept}*,\n"
                f"let's strengthen your existing knowledge:\n\n{retrieval}\n\n"
                f"Reply with your answer, and then we'll begin *{concept}*."
            )

        # No retrieval needed — start Socratic guidance
        guidance = self.socrates.guide(concept)
        ledger = self.bjork.print_ledger(student_id)

        return f"Let's explore **{concept}**!\n\n{guidance}{ledger}"

    def handle_response(self, student_id: str, concept: str, response: str) -> str:
        """Process a student's response — Socratic guidance or Bloom evaluation."""
        cm = self.bjork.get_or_create_ledger(student_id).concepts.get(concept)
        if not cm:
            return self.start_concept(student_id, concept)

        # Check if we're waiting for a diagnostic response
        if cm.status == "active" and cm.test_count > 0 and cm.fail_count < 3:
            # Evaluate the response
            question = self.bloom.generate_diagnostic(concept, cm.bloom_level)
            if question:
                result = self.bloom.evaluate_response(question, response)
                self.bjork.record_test_result(student_id, concept, result["passed"])

                if result["passed"]:
                    # Check if we should advance or trigger purge
                    updated_cm = self.bjork.get_or_create_ledger(student_id).concepts[concept]
                    if self.bloom.can_progress(updated_cm):
                        return self._trigger_mastery(student_id, concept, updated_cm)
                    else:
                        celebration = self.socrates.celebrate_progress(concept, updated_cm.bloom_level)
                        next_q = self.bloom.generate_quiz(concept, updated_cm.bloom_level)
                        return f"{celebration}\n\nNow let's go deeper:\n{next_q}{self.bjork.print_ledger(student_id)}"
                else:
                    return f"{result['feedback']}\n\nTry again when ready!{self.bjork.print_ledger(student_id)}"

        # Normal Socratic flow
        guidance = self.socrates.guide(concept, response,
                                        context={"bloom_level": cm.bloom_level,
                                                 "hints_used": cm.fail_count})
        return f"{guidance}{self.bjork.print_ledger(student_id)}"

    def request_diagnostic(self, student_id: str, concept: str) -> str:
        """Request a Bloom-level diagnostic quiz for a concept."""
        cm = self.bjork.get_or_create_ledger(student_id).concepts.get(concept)
        if not cm:
            cm = self.bjork.add_concept(student_id, concept)

        level = cm.bloom_level
        question = self.bloom.generate_diagnostic(concept, level)
        if not question:
            question = self.bloom.generate_quiz(concept, level)
            return f"📝 **Mastery Check** ({level.upper()} level):\n\n{question}{self.bjork.print_ledger(student_id)}"

        return (
            f"📝 **Mastery Check** — {concept} ({level.upper()} level):\n\n"
            f"**Question**: {question.question}\n\n"
            f"Take your time and explain your reasoning thoroughly."
            f"{self.bjork.print_ledger(student_id)}"
        )

    def compact_conversation(self, student_id: str, concept: str, summary: str) -> str:
        """Archive a mastered concept into the Cognitive Ledger (COMPACT)."""
        self.bjork.compact_concept(student_id, concept, summary)
        ledger = self.bjork.print_ledger(student_id)
        return (
            f"📦 **Concept Archived**: *{concept}* has been compacted into your Cognitive Ledger.\n"
            f"Summary: *{summary}*\n\n"
            f"You can now build upon this foundation! What would you like to explore next?"
            f"{ledger}"
        )

    def get_ledger(self, student_id: str) -> str:
        """Display the current Cognitive Ledger."""
        return self.bjork.print_ledger(student_id)

    def stats(self, student_id: str) -> dict[str, Any]:
        """Get learning statistics for a student."""
        return self.bjork.stats(student_id)

    def _retrieval_intercept(self, student_id: str) -> str | None:
        """Check if spaced repetition is due for any mastered concepts."""
        candidates = self.bjork.get_retrieval_candidates(student_id, max_count=1)
        if candidates:
            c = candidates[0]
            question = self.bloom.generate_quiz(c.concept, c.bloom_level)
            return f"**Quick recall check** for *{c.concept}*:\n{question}"
        return None

    def _trigger_mastery(self, student_id: str, concept: str, cm: ConceptMastery) -> str:
        """Trigger mastery celebration and context purge mandate."""
        celebration = self.socrates.celebrate_progress(concept, cm.bloom_level)
        purge = self.bloom.generate_purge_mandate(concept)
        ledger = self.bjork.print_ledger(student_id)

        return (
            f"{celebration}\n\n"
            f"🎯 **Milestone Achieved**: You've reached **{cm.bloom_level.upper()}** "
            f"mastery of *{concept}*!\n\n"
            f"{purge}"
            f"{ledger}"
        )

    def get_response(self, action: str = "status", student_id: str = "default",
                     concept: str = "", response: str = "", summary: str = "",
                     domain: str = "", **kwargs) -> dict[str, Any]:
        """Unified API response handler."""
        if action == "initialize":
            text = self.initialize_student(student_id, domain or "General Learning")
            return {"module": "pedagogical", "action": "initialize", "response": text}
        elif action == "start_concept":
            text = self.start_concept(student_id, concept)
            return {"module": "pedagogical", "action": "start_concept", "concept": concept, "response": text}
        elif action == "handle_response":
            text = self.handle_response(student_id, concept, response)
            return {"module": "pedagogical", "action": "handle_response", "concept": concept, "response": text}
        elif action == "diagnostic":
            text = self.request_diagnostic(student_id, concept)
            return {"module": "pedagogical", "action": "diagnostic", "concept": concept, "response": text}
        elif action == "compact":
            text = self.compact_conversation(student_id, concept, summary)
            return {"module": "pedagogical", "action": "compact", "concept": concept, "response": text}
        elif action == "ledger":
            return {"module": "pedagogical", "action": "ledger", "ledger": self.get_ledger(student_id)}
        elif action == "stats":
            return {"module": "pedagogical", "action": "stats", **self.stats(student_id)}
        else:
            return {"module": "pedagogical", "action": "status", "student_id": student_id,
                    "available_concepts": list(self.bjork.get_or_create_ledger(student_id).concepts.keys())}


# ── Global instance ──
_ped_engine: PedagogicalEngine | None = None

def get_pedagogical_engine() -> PedagogicalEngine:
    global _ped_engine
    if _ped_engine is None:
        _ped_engine = PedagogicalEngine()
    return _ped_engine


if __name__ == "__main__":
    engine = PedagogicalEngine()
    sid = "test_student"

    # Demo initialization
    print(engine.initialize_student(sid, "Computer Science"))
    print()

    # Demo concept start
    print(engine.start_concept(sid, "recursion"))
    print()

    # Demo diagnostic
    print(engine.request_diagnostic(sid, "recursion"))
