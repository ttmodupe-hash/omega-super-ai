"""
Luqi AI v24.5.0 — Animation Engine
====================================
Generates animated practical learning content for African learners.

Features:
  - Scene-by-scene animation script generation
  - Interactive HTML/CSS/JS animation generation
  - Step-by-step visual lab walkthroughs
  - Topic-specific animation templates (networking, security, coding)
  - Browser-based (works on mobile, no video files needed)
  - Voiceover narration scripts
  - Auto-generated from training content

Part of Luqi AI v24.5.0 by Limitless Telecoms — Empowering Africa

Author: Animation Engine Team
License: Proprietary - Limitless Telecoms
Python: 3.11+
"""

from __future__ import annotations

import html
import json
import logging
import re
import secrets
import textwrap
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------


class SceneType(str, Enum):
    """Types of animation scenes for structured learning flow."""

    INTRO = "intro"
    DEMONSTRATION = "demonstration"
    PRACTICE = "practice"
    EXPLANATION = "explanation"
    SUMMARY = "summary"
    QUIZ = "quiz"


class TransitionType(str, Enum):
    """Visual transition styles between scenes."""

    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    NONE = "none"


class ComplexityLevel(str, Enum):
    """Audience complexity levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class AnimationScene:
    """A single scene within an animation script.

    Attributes:
        scene_number: Position in the sequence (1-based).
        scene_type: Category of scene (intro, demo, practice, etc.).
        title: Short display title for the scene.
        description: Detailed visual description for the animator.
        duration_seconds: How long this scene runs.
        visual_elements: List of dicts describing elements to render.
        narration_text: Voiceover script for the scene.
        on_screen_text: Text overlays to display.
        transition_type: How the next scene should appear.
    """

    scene_number: int
    scene_type: SceneType
    title: str
    description: str
    duration_seconds: int
    visual_elements: List[Dict[str, Any]] = field(default_factory=list)
    narration_text: str = ""
    on_screen_text: str = ""
    transition_type: TransitionType = TransitionType.FADE

    def to_dict(self) -> dict:
        """Serialize to dict for JSON export."""
        return {
            "scene_number": self.scene_number,
            "scene_type": self.scene_type.value,
            "title": self.title,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "visual_elements": self.visual_elements,
            "narration_text": self.narration_text,
            "on_screen_text": self.on_screen_text,
            "transition_type": self.transition_type.value,
        }


@dataclass
class AnimationScript:
    """Complete animation script with metadata and scenes.

    Attributes:
        topic: Subject of the animation.
        total_duration_seconds: Sum of all scene durations.
        target_audience: Who this is for.
        scenes: Ordered list of AnimationScene objects.
        learning_objectives: What the learner will achieve.
        prerequisites: What they should know first.
        assessment_questions: Quiz questions to verify learning.
    """

    topic: str
    total_duration_seconds: int = 0
    target_audience: str = "beginner"
    scenes: List[AnimationScene] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    assessment_questions: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize full script to dict."""
        return {
            "topic": self.topic,
            "total_duration_seconds": self.total_duration_seconds,
            "target_audience": self.target_audience,
            "scenes": [s.to_dict() for s in self.scenes],
            "learning_objectives": self.learning_objectives,
            "prerequisites": self.prerequisites,
            "assessment_questions": self.assessment_questions,
        }


# ---------------------------------------------------------------------------
# Template Database
# ---------------------------------------------------------------------------

ANIMATION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "network_packet_flow": {
        "title": "Network Packet Flow: TCP Handshake & Data Transfer",
        "description": "Visualizes the 3-way TCP handshake and subsequent data packet flow between client and server.",
        "tags": ["networking", "tcp", "packets"],
        "complexity": "beginner",
        "default_scenes": [
            {
                "type": SceneType.INTRO,
                "title": "Introduction to TCP Communication",
                "description": "Two devices appear on screen - a Client (laptop) and Server (rack). A label 'TCP/IP' appears between them.",
                "duration": 15,
                "visual_elements": [
                    {"type": "device", "label": "Client", "x": 10, "y": 50},
                    {"type": "device", "label": "Server", "x": 80, "y": 50},
                    {"type": "label", "text": "TCP/IP Communication", "x": 35, "y": 10},
                ],
                "narration": "Welcome! In this lesson, we'll see how two computers establish a reliable connection using the TCP protocol. Meet the Client and the Server.",
                "on_screen_text": "TCP Communication",
            },
            {
                "type": SceneType.EXPLANATION,
                "title": "The 3-Way Handshake",
                "description": "Three labeled arrows animate sequentially: SYN from Client to Server, SYN-ACK back, then ACK from Client. Each step highlights and pauses.",
                "duration": 45,
                "visual_elements": [
                    {"type": "packet", "label": "SYN", "from": "Client", "to": "Server", "seq": 1},
                    {"type": "packet", "label": "SYN-ACK", "from": "Server", "to": "Client", "seq": 2},
                    {"type": "packet", "label": "ACK", "from": "Client", "to": "Server", "seq": 3},
                ],
                "narration": "First, the Client sends a SYN packet to request a connection. The Server replies with SYN-ACK, acknowledging and requesting its own connection. Finally, the Client sends ACK to confirm. The connection is now established!",
                "on_screen_text": "Step 1: SYN → SYN-ACK → ACK",
            },
            {
                "type": SceneType.DEMONSTRATION,
                "title": "Data Transfer",
                "description": "Multiple data packets animate from Client to Server with sequence numbers. ACK packets flow back. A progress bar fills.",
                "duration": 40,
                "visual_elements": [
                    {"type": "packet", "label": "DATA[1]", "from": "Client", "to": "Server"},
                    {"type": "packet", "label": "DATA[2]", "from": "Client", "to": "Server"},
                    {"type": "packet", "label": "DATA[3]", "from": "Client", "to": "Server"},
                    {"type": "packet", "label": "ACK", "from": "Server", "to": "Client"},
                ],
                "narration": "Now data flows! The Client sends packets with sequence numbers. The Server acknowledges each one. If a packet is lost, it will be retransmitted - that's the reliability of TCP.",
                "on_screen_text": "Data Transfer with Acknowledgments",
            },
            {
                "type": SceneType.SUMMARY,
                "title": "Connection Teardown",
                "description": "FIN and FIN-ACK packets animate to gracefully close the connection. A 'Connection Closed' label appears.",
                "duration": 20,
                "visual_elements": [
                    {"type": "packet", "label": "FIN", "from": "Client", "to": "Server"},
                    {"type": "packet", "label": "FIN-ACK", "from": "Server", "to": "Client"},
                ],
                "narration": "To close, the Client sends a FIN packet. The Server acknowledges with FIN-ACK. The connection is now gracefully closed. This is how every secure web session works!",
                "on_screen_text": "Graceful Connection Close",
            },
        ],
    },
    "sql_injection_defense": {
        "title": "SQL Injection Attack & Defense",
        "description": "Demonstrates how SQL injection attacks work and how parameterized queries prevent them.",
        "tags": ["security", "sql", "injection", "web"],
        "complexity": "intermediate",
        "default_scenes": [
            {
                "type": SceneType.INTRO,
                "title": "What is SQL Injection?",
                "description": "A login form appears on screen. Text cursor blinks in username field. A warning icon pulses nearby.",
                "duration": 15,
                "visual_elements": [
                    {"type": "form", "label": "Login Form", "fields": ["Username", "Password"]},
                    {"type": "warning_icon", "x": 75, "y": 20},
                ],
                "narration": "SQL Injection is one of the most common web attacks. An attacker inserts malicious SQL code into input fields to manipulate the database.",
                "on_screen_text": "SQL Injection Explained",
            },
            {
                "type": SceneType.DEMONSTRATION,
                "title": "The Attack",
                "description": "Text 'admin' OR '1'='1' appears in username field. The query string highlights malicious parts in red. A database icon shows 'Access Granted'.",
                "duration": 40,
                "visual_elements": [
                    {"type": "input_field", "label": "Username", "value": "' OR '1'='1", "highlight_malicious": True},
                    {"type": "query_display", "sql": "SELECT * FROM users WHERE name='' OR '1'='1' --' AND pass=''", "highlight_injection": True},
                    {"type": "database", "state": "compromised"},
                ],
                "narration": "Watch this! The attacker enters a quote to close the string, then adds OR one equals one - which is always true. The database returns ALL user records. The attacker is now logged in as admin!",
                "on_screen_text": "Attack: ' OR '1'='1 --",
            },
            {
                "type": SceneType.DEMONSTRATION,
                "title": "The Defense",
                "description": "Same input but now parameterized query blocks it. A shield icon appears. Database shows 'Access Denied'.",
                "duration": 40,
                "visual_elements": [
                    {"type": "shield", "x": 50, "y": 30},
                    {"type": "query_display", "sql": "SELECT * FROM users WHERE name=? AND pass=?", "highlight_safe": True},
                    {"type": "database", "state": "protected"},
                ],
                "narration": "Now the defense! With parameterized queries, user input is treated as data, never as code. The entire malicious string is passed as a parameter. The database compares it literally - no tricks work!",
                "on_screen_text": "Defense: Parameterized Queries",
            },
            {
                "type": SceneType.PRACTICE,
                "title": "Identify the Vulnerability",
                "description": "Two code snippets side by side. Learner clicks which one is vulnerable. Checkmark or X appears.",
                "duration": 30,
                "visual_elements": [
                    {"type": "code_snippet", "label": "Code A", "vulnerable": True},
                    {"type": "code_snippet", "label": "Code B", "vulnerable": False},
                    {"type": "quiz_prompt", "question": "Which code is vulnerable to SQL injection?"},
                ],
                "narration": "Now you try! Look at these two code snippets. Can you spot which one is vulnerable to SQL injection? Click on the vulnerable code.",
                "on_screen_text": "Practice: Spot the Vulnerability",
            },
            {
                "type": SceneType.SUMMARY,
                "title": "Key Takeaways",
                "description": "Bullet points appear one by one with icons: shield, lock, checkmark.",
                "duration": 20,
                "visual_elements": [
                    {"type": "bullet_point", "text": "Never trust user input"},
                    {"type": "bullet_point", "text": "Always use parameterized queries"},
                    {"type": "bullet_point", "text": "Validate and sanitize all inputs"},
                    {"type": "bullet_point", "text": "Use ORM frameworks when possible"},
                ],
                "narration": "Remember these rules: never trust user input, always use parameterized queries, validate and sanitize everything, and consider using ORM frameworks. Stay secure!",
                "on_screen_text": "Security Best Practices",
            },
        ],
    },
}