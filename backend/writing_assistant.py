#!/usr/bin/env python3
"""
Writing Assistant (Grammar & Wording Corrections) — Luqi AI
============================================================

A comprehensive writing assistant that corrects grammar, improves word choice,
adjusts tone, enhances clarity, and helps users write better in any context —
from emails to essays to creative writing.

Modules
-------
GrammarEngine      – Detects and corrects grammar errors with explanations
improve_wording    – Improves word choice and phrasing by style
analyze_readability – Analyses text readability via standard formulas
adjust_tone        – Adjusts writing tone to a target profile
check_originality  – Identifies clichés and overused phrases
check_style_guide  – Checks compliance with APA / MLA / Chicago / Oxford
get_text_stats     – Comprehensive text statistics

Example
-------
>>> from writing_assistant import GrammarEngine, improve_wording, analyze_readability
>>> engine = GrammarEngine()
>>> engine.check_grammar("She are going to the store.")
>>> result = improve_wording("The movie was really good.", style="academic")
"""

from __future__ import annotations

import math
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS & DATA
# =============================================================================

# ---------------------------------------------------------------------------
# Grammar rules
# ---------------------------------------------------------------------------
GRAMMAR_RULES: Dict[str, Any] = {
    "subject_verb_agreement": {
        "pattern": (
            r"\b(she|he|it)\s+(are|were|have)\b|"
            r"\b(they|we|you)\s+(is|was|has)\b|"
            r"\b(I)\s+(is|are|was|were|has)\b"
        ),
        "severity": "high",
        "examples": [
            {
                "incorrect": "She are going",
                "correct": "She is going",
                "explanation": "Singular subject 'she' requires singular verb 'is'.",
            },
            {
                "incorrect": "They was here",
                "correct": "They were here",
                "explanation": "Plural subject 'they' requires plural verb 'were'.",
            },
            {
                "incorrect": "He have a car",
                "correct": "He has a car",
                "explanation": "Singular subject 'he' requires singular verb 'has'.",
            },
            {
                "incorrect": "We was happy",
                "correct": "We were happy",
                "explanation": "Plural subject 'we' requires plural verb 'were'.",
            },
            {
                "incorrect": "I is ready",
                "correct": "I am ready",
                "explanation": "First-person singular 'I' requires 'am' (present) or 'was' (past).",
            },
        ],
    },
    "double_negative": {
        "pattern": (
            r"\b(don't|doesn't|didn't|can't|won't|couldn't|wouldn't|shouldn't|"
            r"haven't|hasn't|isn't|aren't|wasn't|weren't)\s+"
            r"(no|none|nothing|nobody|nowhere|neither|nor|hardly|scarcely|barely)\b"
        ),
        "severity": "high",
        "examples": [
            {
                "incorrect": "I don't have nothing",
                "correct": "I don't have anything",
                "explanation": (
                    "Double negative creates a positive meaning. "
                    "Use 'anything' instead of 'nothing' after a negative verb."
                ),
            },
            {
                "incorrect": "She can't hardly wait",
                "correct": "She can hardly wait",
                "explanation": (
                    "'Can't hardly' is a double negative. "
                    "Remove the negative contraction for the intended meaning."
                ),
            },
            {
                "incorrect": "We didn't see nobody",
                "correct": "We didn't see anybody",
                "explanation": (
                    "Use 'anybody' rather than 'nobody' after a negative auxiliary verb."
                ),
            },
        ],
    },
}
