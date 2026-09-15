"""
Companion Module — Omega Super AI v10

Mentoring & Companion Mode providing personalized AI mentorship,
goal coaching, quiz generation, simplified explanations, study guides,
and progress tracking across ANY topic domain.

Classes:
    Companion: Personalized AI mentor with adaptive learning paths.

Typical usage:
    companion = Companion(openai_client=client, db=database)
    plan = companion.mentor(topic="Quantum Physics", user_level="beginner")
    steps = companion.coach(goal="Learn Spanish", timeframe="90 days")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class Companion:
    """Personalized AI mentor providing adaptive learning experiences.

    The Companion class generates structured lesson plans, coaching roadmaps,
    quiz questions, simplified explanations, study guides, and progress reports.
    All content is personalized based on the user's declared experience level.

    Attributes:
        openai_client: An initialized OpenAI-compatible API client.
        db: Optional database connection for progress tracking.
    """

    LEVEL_PROMPTS: dict[str, str] = {
        "beginner": (
            "You are a patient, encouraging mentor for a complete beginner. "
            "Use simple analogies, avoid jargon, and build foundational confidence. "
            "Start with the absolute basics and progress gradually."
        ),
        "intermediate": (
            "You are a knowledgeable mentor for someone with foundational knowledge. "
            "Build on what they know, introduce more complex concepts, and challenge "
            "them with practical applications."
        ),
        "advanced": (
            "You are an expert mentor for someone very knowledgeable in this area. "
            "Focus on cutting-edge developments, nuanced debates, and highly "
            "specialized skills. Be concise and intellectually rigorous."
        ),
        "expert": (
            "You are a peer-level expert mentor. Discuss the latest research, "
            "advanced techniques, and domain-specific innovations at a professional level."
        ),
    }

    LEVEL_DEFAULTS: dict[str, dict[str, int]] = {
        "beginner": {"lessons": 8, "quiz_questions": 5, "duration_hours": 20},
        "intermediate": {"lessons": 6, "quiz_questions": 5, "duration_hours": 15},
        "advanced": {"lessons": 4, "quiz_questions": 7, "duration_hours": 10},
        "expert": {"lessons": 3, "quiz_questions": 10, "duration_hours": 6},
    }

    def __init__(self, openai_client: Any, db: Any = None) -> None:
        """Initialize the Companion with an AI client and optional database.

        Args:
            openai_client: An initialized OpenAI-compatible API client with a
                ``chat.completions.create`` method.
            db: Optional database connection for progress persistence and retrieval.
        """
        self.openai_client = openai_client
        self.db = db
        logger.info("Companion initialized (db=%s)", "connected" if db else "none")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _system_prompt(self, user_level: str) -> str:
        """Return the mentoring personality prompt for *user_level*.

        Falls back to the ``beginner`` prompt if the level is not recognized.
        """
        return self.LEVEL_PROMPTS.get(user_level, self.LEVEL_PROMPTS["beginner"])

    def _chat(self, system: str, user: str, temperature: float = 0.7) -> str:
        """Call the OpenAI-compatible chat endpoint safely.

        Args:
            system: System-level instructions for the model.
            user: The user message / prompt.
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            The model's text response, or an error message string on failure.
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
        """Parse JSON from model output, stripping markdown fences if needed.

        Returns the parsed object, or a dict with an ``error`` key on failure.
        """
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

    def _normalize_level(self, level: str) -> str:
        """Normalize a free-form level string to a known key."""
        mapping = {
            "beginner": "beginner",
            "intermediate": "intermediate",
            "advanced": "advanced",
            "expert": "expert",
            "novice": "beginner",
            "new": "beginner",
            "basic": "beginner",
            "amateur": "beginner",
            "mid": "intermediate",
            "medium": "intermediate",
            "moderate": "intermediate",
            "pro": "advanced",
            "professional": "advanced",
            "master": "expert",
            "phd": "expert",
        }
        return mapping.get(level.lower().strip(), "beginner")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def mentor(self, topic: str, user_level: str = "beginner") -> dict[str, Any]:
        """Generate a personalized learning path for *topic*.

        Uses the AI model to build a structured lesson plan tailored to the
        user's experience level. The plan includes lessons, key takeaways,
        exercises, milestones, prerequisites, and estimated duration.

        Args:
            topic: The subject the user wants to learn.
            user_level: Experience level — ``beginner``, ``intermediate``,
                ``advanced``, or ``expert``. Defaults to ``beginner``.

        Returns:
            A dictionary describing the complete learning path.
        """
        level = self._normalize_level(user_level)
        defaults = self.LEVEL_DEFAULTS.get(level, self.LEVEL_DEFAULTS["beginner"])
        num_lessons = defaults["lessons"]
        duration = defaults["duration_hours"]

        system = self._system_prompt(level)
        user_prompt = (
            f"Create a structured {num_lessons}-lesson learning path for: {topic}\n"
            f"User level: {level}\n"
            f"Estimated duration: {duration} hours total\n\n"
            "Respond ONLY with a JSON object in this exact structure:\n"
            "{\n"
            '  "topic": "string",\n'
            '  "user_level": "string",\n'
            '  "lessons": [\n'
            "    {\n"
            '      "number": 1,\n'
            '      "title": "string",\n'
            '      "content": "string (detailed lesson content)",\n'
            '      "key_takeaways": ["string"],\n'
            '      "exercises": ["string"]\n'
            "    }\n"
            "  ],\n"
            '  "estimated_duration": "string",\n'
            '  "prerequisites": ["string"],\n'
            '  "resources": ["string"],\n'
            '  "milestones": [\n'
            '    {"description": "string", "checkpoint": "string"}\n'
            "  ]\n"
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.7)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            data["user_level"] = level
            return data

        # Graceful fallback — return a minimal valid structure.
        return {
            "topic": topic,
            "user_level": level,
            "lessons": [
                {
                    "number": i + 1,
                    "title": f"Lesson {i + 1}: Introduction to {topic}",
                    "content": f"Explore core concepts of {topic} at {level} level.",
                    "key_takeaways": [f"Understand fundamentals of {topic}"],
                    "exercises": [f"Practice a basic {topic} exercise"],
                }
                for i in range(num_lessons)
            ],
            "estimated_duration": f"{duration} hours",
            "prerequisites": ["Curiosity and willingness to learn"],
            "resources": [
                f"Online courses on {topic}",
                f"Books about {topic}",
                f"Practice projects for {topic}",
            ],
            "milestones": [
                {
                    "description": f"Complete first {topic} lesson",
                    "checkpoint": "Able to explain basic concepts",
                },
                {
                    "description": f"Finish half of {topic} course",
                    "checkpoint": "Complete mid-point project",
                },
                {
                    "description": f"Master {topic} fundamentals",
                    "checkpoint": "Pass final assessment",
                },
            ],
        }

    def coach(
        self,
        goal: str,
        timeframe: str = "30 days",
        current_status: str = "",
    ) -> dict[str, Any]:
        """Create a goal-setting and accountability coaching plan.

        Breaks a high-level goal into weekly and daily actionable steps
        with built-in accountability checkpoints.

        Args:
            goal: The goal the user wants to achieve.
            timeframe: Target duration (e.g. ``"30 days"``, ``"12 weeks"``).
            current_status: Optional description of where the user is now.

        Returns:
            A dictionary with the action plan, weekly targets, and accountability
            check schedule.
        """
        system = (
            "You are an expert goal-setting and accountability coach. "
            "You break ambitious goals into concrete, actionable steps with "
            "specific weekly targets and accountability mechanisms."
        )
        user_prompt = (
            f"Goal: {goal}\n"
            f"Timeframe: {timeframe}\n"
            f"Current status: {current_status or 'Starting from scratch'}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "goal": "string",\n'
            '  "timeframe": "string",\n'
            '  "action_plan": "string (overview)",\n'
            '  "weekly_targets": [\n'
            '    {"week": 1, "target": "string", "actions": ["string"], "success_metric": "string"}\n'
            "  ],\n"
            '  "accountability_checks": [\n'
            '    {"when": "string", "check": "string", "remedy": "string"}\n'
            "  ],\n"
            '  "motivation_tips": ["string"],\n'
            '  "obstacles": [\n'
            '    {"obstacle": "string", "solution": "string"}\n'
            "  ]\n"
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.8)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            return data

        return {
            "goal": goal,
            "timeframe": timeframe,
            "action_plan": f"Break {goal} into daily actions over {timeframe}.",
            "weekly_targets": [
                {
                    "week": 1,
                    "target": f"Start {goal}",
                    "actions": ["Research the topic", "Set up environment"],
                    "success_metric": "Completed initial research",
                }
            ],
            "accountability_checks": [
                {
                    "when": "End of week 1",
                    "check": f"Did you start {goal}?",
                    "remedy": "Revisit motivation and adjust plan",
                }
            ],
            "motivation_tips": ["Track daily progress", "Celebrate small wins"],
            "obstacles": [
                {"obstacle": "Procrastination", "solution": "Use Pomodoro technique"}
            ],
        }

    def quiz(self, topic: str, num_questions: int = 5) -> list[dict[str, Any]]:
        """Generate quiz questions to test knowledge on *topic*.

        Args:
            topic: The subject to create questions about.
            num_questions: Number of questions (default 5, max 20).

        Returns:
            A list of question dictionaries, each with options, the correct
            answer, and an explanation.
        """
        num_questions = max(1, min(num_questions, 20))
        system = (
            "You are an expert educator who creates engaging, challenging quiz questions. "
            "Each question has exactly 4 options with one clearly correct answer. "
            "Make questions thought-provoking and educational."
        )
        user_prompt = (
            f"Create {num_questions} quiz questions about: {topic}\n\n"
            "Respond ONLY with a JSON array in this structure:\n"
            "[\n"
            "  {\n"
            '    "question": "string",\n'
            '    "options": ["A. option1", "B. option2", "C. option3", "D. option4"],\n'
            '    "correct_answer": "string (the full text of correct option)",\n'
            '    "explanation": "string"\n'
            "  }\n"
            "]\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.8)
        data = self._safe_json(raw)

        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "error" not in data and "questions" in data:
            return list(data["questions"])

        # Fallback questions
        return [
            {
                "question": f"What is the most fundamental concept in {topic}?",
                "options": [
                    "A. Core principles",
                    "B. Advanced techniques",
                    "C. Historical background",
                    "D. Modern applications",
                ],
                "correct_answer": "A. Core principles",
                "explanation": "Core principles form the foundation upon which all other knowledge is built.",
            }
            for _ in range(num_questions)
        ]

    def explain_like_im_five(self, concept: str) -> str:
        """Explain any concept in simple terms a five-year-old would understand.

        Args:
            concept: The concept to explain.

        Returns:
            A plain-language explanation with analogies.
        """
        system = (
            "You are a wonderful teacher who explains complex ideas to young children. "
            "Use simple words, fun analogies, and everyday examples. "
            "Keep explanations warm, encouraging, and easy to understand."
        )
        user_prompt = f"Explain '{concept}' like I'm five years old."
        return self._chat(system, user_prompt, temperature=0.9)

    def study_guide(
        self, topic: str, exam_date: str | None = None
    ) -> dict[str, Any]:
        """Generate a comprehensive study guide for *topic*.

        Args:
            topic: The subject to study.
            exam_date: Optional target date (``"YYYY-MM-DD"``) to build a
                day-by-day review schedule.

        Returns:
            A dictionary with sections, practice questions, and an optional
            review schedule.
        """
        system = (
            "You are an expert academic coach who creates effective study guides. "
            "Organize material logically, highlight key concepts, and create "
            "structured review plans that maximize retention."
        )
        exam_info = f"\nExam date: {exam_date}" if exam_date else ""
        user_prompt = (
            f"Create a comprehensive study guide for: {topic}{exam_info}\n\n"
            "Respond ONLY with JSON in this structure:\n"
            "{\n"
            '  "topic": "string",\n'
            '  "sections": [\n'
            "    {\n"
            '      "title": "string",\n'
            '      "content": "string (detailed study material)",\n'
            '      "priority": "HIGH|MEDIUM|LOW"\n'
            "    }\n"
            "  ],\n"
            '  "practice_questions": [\n'
            "    {\n"
            '      "question": "string",\n'
            '      "answer": "string",\n'
            '      "difficulty": "easy|medium|hard"\n'
            "    }\n"
            "  ],\n"
            '  "review_schedule": [\n'
            '    {"day": "Day X", "topics": ["string"], "activity": "string"}\n'
            "  ]\n"
            "}\n"
        )

        raw = self._chat(system, user_prompt, temperature=0.7)
        data = self._safe_json(raw)

        if isinstance(data, dict) and "error" not in data:
            # Build review schedule if exam_date provided
            if exam_date and "review_schedule" not in data:
                data["review_schedule"] = self._build_review_schedule(topic, exam_date)
            return data

        return {
            "topic": topic,
            "sections": [
                {
                    "title": f"Core Concepts of {topic}",
                    "content": f"Study the fundamental principles of {topic}.",
                    "priority": "HIGH",
                }
            ],
            "practice_questions": [
                {
                    "question": f"What is the definition of {topic}?",
                    "answer": f"The study and practice of {topic}.",
                    "difficulty": "medium",
                }
            ],
            "review_schedule": (
                self._build_review_schedule(topic, exam_date) if exam_date else []
            ),
        }

    def _build_review_schedule(self, topic: str, exam_date: str) -> list[dict[str, Any]]:
        """Generate a spaced-repetition review schedule leading up to *exam_date*.

        Args:
            topic: Subject name.
            exam_date: ISO-formatted date string.

        Returns:
            A list of daily review tasks.
        """
        try:
            target = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            logger.warning("Invalid exam_date: %s", exam_date)
            return []

        today = datetime.now().date()
        days_remaining = (target - today).days
        if days_remaining <= 0:
            return [{"day": "Today (Exam Day)", "topics": [topic], "activity": "Final review"}]

        schedule: list[dict[str, Any]] = []
        phase1_end = max(1, days_remaining // 3)
        phase2_end = max(phase1_end + 1, 2 * days_remaining // 3)

        for day in range(1, days_remaining + 1):
            if day <= phase1_end:
                activity = "Learn new material"
            elif day <= phase2_end:
                activity = "Review and practice"
            else:
                activity = "Intensive review"

            schedule.append(
                {
                    "day": f"Day {day}",
                    "topics": [f"{topic} — {activity}"],
                    "activity": activity,
                }
            )

        return schedule

    def progress_check(self, topic: str, db: Any | None = None) -> dict[str, Any]:
        """Check the user's learning progress for *topic* from the database.

        Args:
            topic: The subject to look up progress for.
            db: Optional database connection (overrides instance ``db``).

        Returns:
            A progress summary with recommendations.
        """
        db_conn = db or self.db
        if db_conn is None:
            return {
                "topic": topic,
                "status": "no_database",
                "message": "No database connection available for progress tracking.",
                "completed_lessons": 0,
                "total_lessons": 0,
                "completion_percentage": 0,
                "last_activity": None,
                "recommendations": ["Connect a database to track progress."],
            }

        try:
            rows = db_conn.execute(
                "SELECT lesson_number, completed, completed_at, quiz_score "
                "FROM learning_progress WHERE topic = ? ORDER BY lesson_number",
                (topic,),
            ).fetchall()
        except Exception as exc:
            logger.error("Database query error: %s", exc)
            return {
                "topic": topic,
                "status": "error",
                "message": f"Database error: {exc}",
                "completed_lessons": 0,
                "total_lessons": 0,
                "completion_percentage": 0,
                "last_activity": None,
                "recommendations": ["Check database schema and connectivity."],
            }

        if not rows:
            return {
                "topic": topic,
                "status": "not_started",
                "message": f"No progress found for '{topic}'. Start learning!",
                "completed_lessons": 0,
                "total_lessons": 0,
                "completion_percentage": 0,
                "last_activity": None,
                "recommendations": [
                    f"Start with lesson 1 of {topic}",
                    f"Take the {topic} quiz to assess your level",
                ],
            }

        total = len(rows)
        completed = sum(1 for r in rows if r[1])
        pct = round((completed / total) * 100, 1) if total else 0
        last_activity = max(
            (r[2] for r in rows if r[2]), default=None
        )
        avg_score = round(
            sum(r[3] for r in rows if r[3] is not None) /
            max(1, sum(1 for r in rows if r[3] is not None)),
            1,
        )

        recommendations: list[str] = []
        if pct < 25:
            recommendations.append(f"Just getting started! Complete lesson 1 of {topic}")
        elif pct < 50:
            recommendations.append("Keep going! You're building momentum.")
        elif pct < 75:
            recommendations.append("Great progress! Review any weak areas.")
        elif pct < 100:
            recommendations.append("Almost there! Finish the remaining lessons.")
        else:
            recommendations.append("Congratulations! Consider the next level or a related topic.")

        if avg_score < 70:
            recommendations.append("Quiz scores suggest more review is needed.")

        return {
            "topic": topic,
            "status": "in_progress" if pct < 100 else "completed",
            "completed_lessons": completed,
            "total_lessons": total,
            "completion_percentage": pct,
            "average_quiz_score": avg_score,
            "last_activity": str(last_activity) if last_activity else None,
            "recommendations": recommendations,
        }
