#!/usr/bin/env python3
"""Luqi AI v20 - Teacher Assistant for Africa
==============================================
AI teaching assistant to support educators in under-resourced settings.
Generates lesson plans, worksheets, assessments, and teaching materials.
Aligned to African national curricula and designed for limited-resource classrooms.

DISCLAIMER:
-----------
This software is provided as-is to assist educators. All generated lesson plans,
assessments, and teaching materials should be reviewed by qualified teachers
before classroom use. The grading schemes are indicative and may need to be
adjusted to meet local examination board requirements. The developers are not
responsible for any outcomes resulting from the use of this software.

SUPPORTED CURRICULA:
- West Africa: WAEC, NECO (Nigeria, Ghana, Sierra Leone, The Gambia, Liberia)
- East Africa: KCSE (Kenya), NECTA (Tanzania)
- Southern Africa: ZIMSEC (Zimbabwe), ECZ (Zambia)

AUTHOR: Luqi AI Team
VERSION: 20.0.0
LICENSE: MIT
"""

from __future__ import annotations

import copy
import datetime
import enum
import json
import logging
import os
import pathlib
import random
import sqlite3
import textwrap
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# ──────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────

LOG_FORMAT = "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("luqi_teacher_assistant")


# ──────────────────────────────────────────────────────────────────────────
# CONSTANTS AND ENUMS
# ──────────────────────────────────────────────────────────────────────────

class GradeLevel(enum.Enum):
    """Standard grade levels across African education systems."""
    PRIMARY_1 = "primary_1"
    PRIMARY_2 = "primary_2"
    PRIMARY_3 = "primary_3"
    PRIMARY_4 = "primary_4"
    PRIMARY_5 = "primary_5"
    PRIMARY_6 = "primary_6"
    JSS_1 = "jss_1"
    JSS_2 = "jss_2"
    JSS_3 = "jss_3"
    SSS_1 = "sss_1"
    SSS_2 = "sss_2"
    SSS_3 = "sss_3"


class AssessmentType(enum.Enum):
    """Types of assessments used in continuous assessment frameworks."""
    CONTINUOUS_ASSESSMENT = "continuous_assessment"
    EXAM = "exam"
    PRACTICAL = "practical"
    ORAL = "oral"
    PROJECT = "project"
    HOMEWORK = "homework"
    CLASS_TEST = "class_test"


class DifficultyLevel(enum.Enum):
    """Question difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


# ──────────────────────────────────────────────────────────────────────────
# SHARED DATA: SUBJECTS
# ──────────────────────────────────────────────────────────────────────────

SUBJECTS: Dict[str, Dict[str, Any]] = {
    "mathematics": {
        "name": "Mathematics",
        "categories": ["numeracy", "algebra", "geometry", "statistics"],
        "primary_topics": ["addition", "subtraction", "multiplication", "division",
                           "fractions", "decimals", "geometry", "measurement"],
        "secondary_topics": ["algebra", "trigonometry", "calculus", "statistics",
                             "probability", "coordinate_geometry", "matrices"],
        "icon": "📐",
    },
    "english": {
        "name": "English Language",
        "categories": ["reading", "writing", "grammar", "literature"],
        "primary_topics": ["phonics", "reading_comprehension", "creative_writing",
                           "grammar", "vocabulary", "spelling"],
        "secondary_topics": ["essay_writing", "summary", "comprehension",
                             "oral_english", "literature"],
        "icon": "📖",
    },
    "science": {
        "name": "Basic Science & Technology",
        "categories": ["biology", "chemistry", "physics", "environmental"],
        "primary_topics": ["plants", "animals", "human_body", "weather",
                           "matter", "energy", "environment"],
        "secondary_topics": ["biology", "chemistry", "physics"],
        "icon": "🔬",
    },
    "social_studies": {
        "name": "Social Studies",
        "categories": ["history", "geography", "civics", "culture"],
        "primary_topics": ["family", "community", "culture", "government",
                           "maps", "resources"],
        "secondary_topics": ["governance", "economics", "geography", "history"],
        "icon": "🌍",
    },
    "ict": {
        "name": "Information & Communication Technology",
        "categories": ["computer_basics", "programming", "digital_literacy"],
        "primary_topics": ["parts_of_computer", "typing", "internet_safety",
                           "word_processing"],
        "secondary_topics": ["programming", "databases", "networking",
                             "web_design"],
        "icon": "💻",
    },
    "agriculture": {
        "name": "Agricultural Science",
        "categories": ["crop", "animal", "soil", "farm_management"],
        "primary_topics": ["crop_cultivation", "animal_husbandry", "soil",
                           "tools", "pest_control"],
        "secondary_topics": ["agronomy", "animal_science", "agric_economics",
                             "extension"],
        "icon": "🌾",
    },
    "civic_education": {
        "name": "Civic Education",
        "categories": ["citizenship", "governance", "rights", "responsibilities"],
        "primary_topics": ["rights", "responsibilities", "government",
                           "leadership", "national_values"],
        "secondary_topics": ["democracy", "human_rights", "constitution",
                             "citizenship"],
        "icon": "🏛️",
    },
    "religious_studies": {
        "name": "Religious & Moral Education",
        "categories": ["christianity", "islam", "traditional", "morality"],
        "primary_topics": ["moral_lessons", "religious_stories", "values",
                           "prayers"],
        "secondary_topics": ["scripture", "ethics", "comparative_religion"],
        "icon": "🙏",
    },
    "physical_education": {
        "name": "Physical & Health Education",
        "categories": ["sports", "health", "fitness", "hygiene"],
        "primary_topics": ["running", "jumping", "ball_games", "hygiene",
                           "nutrition"],
        "secondary_topics": ["athletics", "team_sports", "first_aid",
                             "health_education"],
        "icon": "⚽",
    },
    "arts": {
        "name": "Cultural & Creative Arts",
        "categories": ["drawing", "music", "drama", "craft"],
        "primary_topics": ["drawing", "singing", "dancing", "crafts",
                           "traditional_art"],
        "secondary_topics": ["fine_arts", "music", "drama", "design"],
        "icon": "🎨",
    },
    "local_language": {
        "name": "Local Language",
        "categories": ["reading", "writing", "speaking", "culture"],
        "primary_topics": ["alphabet", "greetings", "folktales",
                           "proverbs", "counting"],
        "secondary_topics": ["literature", "grammar", "poetry", "essay"],
        "icon": "🗣️",
    },
    "home_economics": {
        "name": "Home Economics",
        "categories": ["cooking", "sewing", "childcare", "budgeting"],
        "primary_topics": ["cooking", "cleaning", "sewing", "nutrition"],
        "secondary_topics": ["food_nutrition", "clothing", "home_management",
                             "family_living"],
        "icon": "🏠",
    },
    "business_studies": {
        "name": "Business Studies",
        "categories": ["commerce", "accounting", "entrepreneurship"],
        "primary_topics": ["trade", "money", "savings", "types_of_business"],
        "secondary_topics": ["commerce", "bookkeeping", "office_practice",
                             "entrepreneurship"],
        "icon": "📊",
    },
    "biology": {
        "name": "Biology",
        "categories": ["cell", "genetics", "ecology", "physiology"],
        "primary_topics": ["living_things", "plants", "animals",
                           "human_body"],
        "secondary_topics": ["cell_biology", "genetics", "ecology",
                             "reproduction", "evolution"],
        "icon": "🧬",
    },
    "chemistry": {
        "name": "Chemistry",
        "categories": ["organic", "inorganic", "physical", "analytical"],
        "primary_topics": ["matter", "mixtures", "acids_bases", "water"],
        "secondary_topics": ["organic_chemistry", "stoichiometry", "electrochemistry",
                             "periodic_table"],
        "icon": "⚗️",
    },
    "physics": {
        "name": "Physics",
        "categories": ["mechanics", "electricity", "optics", "thermodynamics"],
        "primary_topics": ["force", "motion", "energy", "light", "sound"],
        "secondary_topics": ["mechanics", "waves", "electricity", "modern_physics"],
        "icon": "⚡",
    },
    "geography": {
        "name": "Geography",
        "categories": ["physical", "human", "regional", "cartography"],
        "primary_topics": ["landforms", "weather", "maps", "climate"],
        "secondary_topics": ["geomorphology", "climatology", "population",
                             "economic_geography"],
        "icon": "🗺️",
    },
    "history": {
        "name": "History",
        "categories": ["ancient", "medieval", "colonial", "contemporary"],
        "primary_topics": ["community_history", "great_leaders",
                           "independence", "empires"],
        "secondary_topics": ["african_history", "world_history",
                             "colonialism", "cold_war"],
        "icon": "📜",
    },
    "economics": {
        "name": "Economics",
        "categories": ["micro", "macro", "development", "international"],
        "primary_topics": ["trade", "money", "savings", "market"],
        "secondary_topics": ["microeconomics", "macroeconomics",
                             "development_economics", "international_trade"],
        "icon": "💰",
    },
    "literature": {
        "name": "Literature in English",
        "categories": ["prose", "poetry", "drama", "literary_devices"],
        "primary_topics": ["storytelling", "folktales", "poems",
                           "character", "setting"],
        "secondary_topics": ["shakespeare", "african_literature",
                             "literary_criticism", "drama"],
        "icon": "📚",
    },
}

GRADES: Dict[str, Dict[str, Any]] = {
    "primary_1": {"level": "Primary", "year": 1, "ages": "5-7", "system": "Universal"},
    "primary_2": {"level": "Primary", "year": 2, "ages": "6-8", "system": "Universal"},
    "primary_3": {"level": "Primary", "year": 3, "ages": "7-9", "system": "Universal"},
    "primary_4": {"level": "Primary", "year": 4, "ages": "8-10", "system": "Universal"},
    "primary_5": {"level": "Primary", "year": 5, "ages": "9-11", "system": "Universal"},
    "primary_6": {"level": "Primary", "year": 6, "ages": "10-12", "system": "Universal"},
    "jss_1": {"level": "Junior Secondary", "year": 7, "ages": "11-13", "system": "WAEC/NECO"},
    "jss_2": {"level": "Junior Secondary", "year": 8, "ages": "12-14", "system": "WAEC/NECO"},
    "jss_3": {"level": "Junior Secondary", "year": 9, "ages": "13-15", "system": "WAEC/NECO"},
    "sss_1": {"level": "Senior Secondary", "year": 10, "ages": "14-16", "system": "WAEC/NECO"},
    "sss_2": {"level": "Senior Secondary", "year": 11, "ages": "15-17", "system": "WAEC/NECO"},
    "sss_3": {"level": "Senior Secondary", "year": 12, "ages": "16-18", "system": "WAEC/NECO"},
}

LANGUAGES: Dict[str, Dict[str, Any]] = {
    "swahili": {
        "name": "Kiswahili",
        "greeting": "Habari",
        "thank_you": "Asante",
        "regions": ["Kenya", "Tanzania", "Uganda", "DRC"],
        "family": "Bantu",
    },
    "yoruba": {
        "name": "Yoruba",
        "greeting": "Bawo ni",
        "thank_you": "E seun",
        "regions": ["Nigeria", "Benin", "Togo"],
        "family": "Niger-Congo",
    },
    "igbo": {
        "name": "Igbo",
        "greeting": "Nnoo",
        "thank_you": "Daalu",
        "regions": ["Nigeria"],
        "family": "Niger-Congo",
    },
    "hausa": {
        "name": "Hausa",
        "greeting": "Sannu",
        "thank_you": "Na gode",
        "regions": ["Nigeria", "Niger", "Ghana"],
        "family": "Afro-Asiatic",
    },
    "zulu": {
        "name": "isiZulu",
        "greeting": "Sawubona",
        "thank_you": "Ngiyabonga",
        "regions": ["South Africa", "Zimbabwe", "Lesotho"],
        "family": "Bantu",
    },
    "xhosa": {
        "name": "isiXhosa",
        "greeting": "Molo",
        "thank_you": "Enkosi",
        "regions": ["South Africa", "Zimbabwe"],
        "family": "Bantu",
    },
    "amharic": {
        "name": "Amharic",
        "greeting": "Selam",
        "thank_you": "Ameseginalehu",
        "regions": ["Ethiopia"],
        "family": "Semitic",
    },
    "luganda": {
        "name": "Luganda",
        "greeting": "Oli otya",
        "thank_you": "Webale",
        "regions": ["Uganda"],
        "family": "Bantu",
    },
    "wolof": {
        "name": "Wolof",
        "greeting": "Salaam aleekum",
        "thank_you": "Jerejef",
        "regions": ["Senegal", "Gambia", "Mauritania"],
        "family": "Niger-Congo",
    },
    "shona": {
        "name": "Shona",
        "greeting": "Mhoroi",
        "thank_you": "Ndinotenda",
        "regions": ["Zimbabwe", "Mozambique", "Botswana"],
        "family": "Bantu",
    },
}

TEACHING_METHODS: Dict[str, Dict[str, Any]] = {
    "group_work": {
        "name": "Group Work / Cooperative Learning",
        "description": "Students work in small groups to complete tasks together.",
        "steps": [
            "Divide class into groups of 4-6 students (mixed ability).",
            "Assign each group a clear task or problem to solve.",
            "Give each student a role (leader, recorder, timekeeper, presenter).",
            "Circulate to monitor and provide support.",
            "Have groups present their findings to the class.",
        ],
        "benefits": ["Builds teamwork", "Peer learning", "Manages large classes"],
        "class_size": "Best for 40-80 students",
    },
    "peer_teaching": {
        "name": "Peer Teaching",
        "description": "Students teach each other in pairs or small groups.",
        "steps": [
            "Pair stronger students with those who need support.",
            "Give the teaching student a clear concept to explain.",
            "Provide a simple guide or questions to structure the session.",
            "Rotate pairs regularly so all students get to teach.",
            "Review key points as a whole class.",
        ],
        "benefits": ["Reinforces understanding", "Builds confidence", "Reduces teacher workload"],
        "class_size": "Best for 40-80 students",
    },
    "role_play": {
        "name": "Role Play",
        "description": "Students act out real-life scenarios to understand concepts.",
        "steps": [
            "Choose a scenario relevant to the topic (e.g., market trading for economics).",
            "Assign roles to volunteers or groups.",
            "Give brief preparation time (2-3 minutes).",
            "Let students perform the role play.",
            "Discuss what was learned and connect to the lesson.",
        ],
        "benefits": ["Makes learning memorable", "Builds empathy", "Active engagement"],
        "class_size": "Best for 40-60 students",
    },
    "demonstration": {
        "name": "Demonstration",
        "description": "Teacher shows how to do something, then students practice.",
        "steps": [
            "Gather all materials needed for the demonstration.",
            "Position yourself so all students can see clearly.",
            "Explain each step as you perform it.",
            "Ask guiding questions during the demo.",
            "Have students volunteer to repeat the demonstration.",
        ],
        "benefits": ["Visual learning", "Clear procedure", "Works with limited resources"],
        "class_size": "Best for any class size",
    },
    "discussion": {
        "name": "Class Discussion",
        "description": "Facilitated conversation about a topic.",
        "steps": [
            "Pose an open-ended question to the class.",
            "Wait 5-10 seconds for students to think (think time).",
            "Call on students from different parts of the room.",
            "Encourage students to respond to each other's ideas.",
            "Summarize key points on the chalkboard.",
        ],
        "benefits": ["Develops critical thinking", "Oral skills", "Inclusive"],
        "class_size": "Best for 30-50 students",
    },
    "project_based": {
        "name": "Project-Based Learning",
        "description": "Students work on an extended project over days or weeks.",
        "steps": [
            "Define a real-world problem or question.",
            "Plan the project timeline and milestones.",
            "Provide resources and guidance.",
            "Monitor progress regularly.",
            "Have students present their final project.",
        ],
        "benefits": ["Deep learning", "Real-world application", "Cross-curricular"],
        "class_size": "Best for any class size (groups)",
    },
    "inquiry_based": {
        "name": "Inquiry-Based Learning",
        "description": "Students discover concepts through questions and investigation.",
        "steps": [
            "Present a puzzling phenomenon or question.",
            "Let students formulate their own hypotheses.",
            "Guide students to design simple investigations.",
            "Have students collect and analyze data.",
            "Draw conclusions together as a class.",
        ],
        "benefits": ["Develops scientific thinking", "Curiosity-driven", "Student-centered"],
        "class_size": "Best for 30-60 students",
    },
    "storytelling": {
        "name": "Storytelling",
        "description": "Use narratives to teach concepts and values.",
        "steps": [
            "Choose or create a story relevant to the lesson.",
            "Use expressive voice and gestures while telling the story.",
            "Pause at key moments to ask predictive questions.",
            "Have students retell the story in their own words.",
            "Connect the story's moral to the lesson objective.",
        ],
        "benefits": ["Culturally relevant", "Engaging", "Improves memory"],
        "class_size": "Best for any class size",
    },
    "games_based": {
        "name": "Games-Based Learning",
        "description": "Educational games to reinforce learning.",
        "steps": [
            "Choose or design a simple game for the topic.",
            "Explain the rules clearly and demonstrate.",
            "Divide students into teams if needed.",
            "Play the game with active teacher facilitation.",
            "Debrief: discuss what was learned during the game.",
        ],
        "benefits": ["Highly engaging", "Reduces anxiety", "Repeated practice"],
        "class_size": "Best for 20-60 students",
    },
}


# ──────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER
# ──────────────────────────────────────────────────────────────────────────

class DatabaseManager:
    """Manages SQLite database for lesson plans, student records, and tracking.

    This class handles all database operations including creating tables,
    inserting records, and querying data. It uses a singleton pattern to
    ensure only one database connection pool exists.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None) -> None:
        if self._initialized:
            return
        self.db_path = db_path or os.path.join(
            os.path.expanduser("~"), ".luqi", "teacher_assistant.db"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._initialized = True
        logger.info("DatabaseManager initialized at %s", self.db_path)

    def _init_db(self) -> None:
        """Create all required tables if they do not exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS lesson_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            grade TEXT NOT NULL,
            duration INTEGER NOT NULL,
            language TEXT DEFAULT 'english',
            objectives TEXT,
            materials TEXT,
            activities TEXT,
            assessment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            grade TEXT NOT NULL,
            num_questions INTEGER DEFAULT 10,
            difficulty TEXT DEFAULT 'medium',
            questions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            school TEXT,
            country TEXT DEFAULT 'nigeria',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            student_uuid TEXT,
            subject TEXT NOT NULL,
            assessment_type TEXT NOT NULL,
            score REAL,
            max_score REAL DEFAULT 100,
            term TEXT,
            year INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_uuid) REFERENCES students(uuid)
        );

        CREATE TABLE IF NOT EXISTS teaching_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            grade TEXT NOT NULL,
            topic TEXT NOT NULL,
            duration INTEGER,
            attendance INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_lesson_subject ON lesson_plans(subject);
        CREATE INDEX IF NOT EXISTS idx_lesson_grade ON lesson_plans(grade);
        CREATE INDEX IF NOT EXISTS idx_assessment_student ON assessments(student_uuid);
        CREATE INDEX IF NOT EXISTS idx_assessment_subject ON assessments(subject);
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(schema)
            conn.commit()
            logger.debug("Database schema initialized successfully")
        except sqlite3.Error as e:
            logger.error("Database initialization error: %s", e)
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        """Execute a SQL query and return results."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            conn.commit()
            return results
        except sqlite3.Error as e:
            logger.error("SQL error: %s | Query: %s | Params: %s", e, query, params)
            raise
        finally:
            conn.close()

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a record and return the row ID."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(query, tuple(data.values()))
            conn.commit()
            return cursor.lastrowid or 0
        except sqlite3.Error as e:
            logger.error("Insert error: %s", e)
            raise
        finally:
            conn.close()


# ──────────────────────────────────────────────────────────────────────────
# LESSON PLAN GENERATOR
# ──────────────────────────────────────────────────────────────────────────

class LessonPlanGenerator:
    """Generates comprehensive lesson plans aligned to African curricula.

    This class creates structured lesson plans including objectives, materials,
    teaching activities, and assessments. It is designed for educators in
    under-resourced settings managing large classes of 40-80 students.

    Attributes:
        db: DatabaseManager instance for persisting lesson plans.
    """

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.db = db or DatabaseManager()
        logger.info("LessonPlanGenerator initialized")

    def generate_lesson(
        self,
        subject: str,
        topic: str,
        grade: str,
        duration: int = 40,
        language: str = "english",
    ) -> Dict[str, Any]:
        """Generate a complete lesson plan for a single subject and topic.

        Args:
            subject: Subject key from SUBJECTS dict.
            topic: Specific topic to cover.
            grade: Grade level key from GRADES dict.
            duration: Lesson duration in minutes (default 40).
            language: Language of instruction (default 'english').

        Returns:
            A dictionary containing the complete lesson plan with keys:
            uuid, subject, topic, grade, duration, language, objectives,
            materials, activities, assessment, teacher_notes, differentiation.
        """
        if subject not in SUBJECTS:
            raise ValueError(f"Unknown subject '{subject}'. Valid: {list(SUBJECTS.keys())}")
        if grade not in GRADES:
            raise ValueError(f"Unknown grade '{grade}'. Valid: {list(GRADES.keys())}")

        subject_info = SUBJECTS[subject]
        grade_info = GRADES[grade]
        lesson_uuid = str(uuid.uuid4())

        objectives = self._generate_objectives(subject, topic, grade)
        materials = self._generate_materials(subject, topic, grade)
        activities = self._generate_activities(subject, topic, grade, duration)
        assessment = self._generate_assessment(subject, topic, grade)
        teacher_notes = self._generate_teacher_notes(subject, topic, grade)
        differentiation = self._generate_differentiation(subject, topic, grade)

        lesson_plan: Dict[str, Any] = {
            "uuid": lesson_uuid,
            "subject": subject_info["name"],
            "subject_key": subject,
            "topic": topic,
            "grade": grade,
            "grade_info": grade_info,
            "duration": duration,
            "language": language,
            "objectives": objectives,
            "materials": materials,
            "activities": activities,
            "assessment": assessment,
            "teacher_notes": teacher_notes,
            "differentiation": differentiation,
            "created_at": datetime.datetime.now().isoformat(),
        }

        try:
            self.db.insert("lesson_plans", {
                "uuid": lesson_uuid,
                "subject": subject,
                "topic": topic,
                "grade": grade,
                "duration": duration,
                "language": language,
                "objectives": json.dumps(objectives),
                "materials": json.dumps(materials),
                "activities": json.dumps(activities),
                "assessment": json.dumps(assessment),
            })
            logger.info("Lesson plan saved: %s (%s, %s, %s)", lesson_uuid, subject, topic, grade)
        except Exception as e:
            logger.warning("Failed to save lesson plan to database: %s", e)

        return lesson_plan

    def _generate_objectives(self, subject: str, topic: str, grade: str) -> List[str]:
        """Generate learning objectives based on Bloom's taxonomy."""
        if "primary" in grade:
            return [
                f"Students will identify basic concepts related to {topic}.",
                f"Students will describe {topic} in their own words.",
                f"Students will complete simple exercises on {topic}.",
            ]
        elif "jss" in grade:
            return [
                f"Students will explain the meaning and importance of {topic}.",
                f"Students will describe the processes involved in {topic}.",
                f"Students will solve problems related to {topic}.",
            ]
        else:
            return [
                f"Students will analyze the principles underlying {topic}.",
                f"Students will evaluate different approaches to {topic}.",
                f"Students will apply advanced concepts of {topic} to real-world scenarios.",
            ]

    def _generate_materials(self, subject: str, topic: str, grade: str) -> List[str]:
        """Generate a list of materials needed, prioritising low-resource options."""
        universal_materials = [
            "Chalkboard and chalk",
            "Duster or cloth",
        ]

        subject_materials: Dict[str, List[str]] = {
            "mathematics": [
                "Counting sticks or stones (local counters)",
                "Ruler (can be made from cardboard)",
                "Paper and pencil for each student",
                "Number chart drawn on chalkboard",
            ],
            "english": [
                "Reading passage written on chalkboard",
                "Flashcards made from cardboard",
                "Students' notebooks and pencils",
            ],
            "science": [
                "Local materials for demonstration (bottles, leaves, water)",
                "Safety equipment (water, first aid)",
            ],
            "social_studies": [
                "Map drawn on chalkboard",
                "Pictures cut from magazines or drawn",
                "Chart showing timeline or family tree",
            ],
            "ict": [
                "Chalkboard-drawn keyboard layout",
                "Paper keyboard templates",
                "Mobile phones (if available) for demonstration",
            ],
            "agriculture": [
                "Soil samples from school compound",
                "Seeds (local varieties)",
                "Farming tools (hoe, cutlass) or pictures",
                "Watering can made from plastic bottle",
            ],
            "civic_education": [
                "Chart of government structure drawn on board",
                "Pictures of national symbols drawn",
                "Copies of simplified constitution excerpts",
            ],
            "arts": [
                "Coloured pencils or crayons",
                "Paper or cardboard",
                "Local craft materials (raffia, beads, clay)",
            ],
            "physical_education": [
                "Open space or field",
                "Makeshift balls (rolled socks, tied rags)",
                "Cones or stones to mark boundaries",
            ],
        }

        return universal_materials + subject_materials.get(subject, ["Relevant textbooks if available"])

    def _generate_activities(self, subject: str, topic: str, grade: str, duration: int) -> List[Dict[str, Any]]:
        """Generate timed teaching activities for the lesson."""
        intro_time = max(5, duration // 8)
        main_time = max(20, duration * 5 // 8)
        review_time = max(5, duration // 8)
        wrap_time = max(5, duration // 8)

        activities = [
            {
                "phase": "Introduction",
                "duration": intro_time,
                "description": f"Greet the class. Review previous lesson. Introduce the topic of {topic} by asking students what they already know. Write their responses on the chalkboard.",
                "teacher_action": "Write key questions on the board. Elicit prior knowledge.",
                "student_action": "Respond to questions. Share what they know.",
            },
            {
                "phase": "Main Activity",
                "duration": main_time,
                "description": f"Present the main content on {topic}. Use the chalkboard to write key points, draw diagrams, and work through examples. Use questioning techniques to check understanding throughout.",
                "teacher_action": "Explain concepts clearly. Use board work. Ask check questions every 3-5 minutes.",
                "student_action": "Listen, copy notes, answer questions, solve problems on the board.",
            },
            {
                "phase": "Practice & Application",
                "duration": main_time // 2,
                "description": "Students work in pairs or small groups to practice what they have learned. Circulate to provide individual support, especially to struggling students.",
                "teacher_action": "Monitor group work. Provide feedback. Identify common errors.",
                "student_action": "Work on exercises. Discuss with peers. Ask questions.",
            },
            {
                "phase": "Review",
                "duration": review_time,
                "description": f"Review the key points of {topic}. Ask students to summarize what they have learned. Correct any misconceptions.",
                "teacher_action": "Facilitate summary. Write key takeaways on board.",
                "student_action": "Participate in summary. Ask clarifying questions.",
            },
            {
                "phase": "Wrap-up",
                "duration": wrap_time,
                "description": "Set homework or follow-up task. Preview next lesson. Dismiss class orderly.",
                "teacher_action": "Give clear homework instructions. Check understanding of task.",
                "student_action": "Write down homework. Pack up quietly.",
            },
        ]
        return activities

    def _generate_assessment(self, subject: str, topic: str, grade: str) -> Dict[str, Any]:
        """Generate assessment strategies for the lesson."""
        return {
            "formative": [
                "Oral questioning during the lesson",
                "Chalkboard exercises (select students to solve)",
                "Thumbs up/down check for understanding",
            ],
            "summative": [
                f"Written exercise on {topic} (to be completed in next lesson or as homework)",
                "Peer assessment of practice work",
            ],
            "continuous_assessment_record": [
                "Record participation level for 3-5 selected students",
                "Note any students who need extra support",
                "Score practice exercise out of 10",
            ],
        }

    def _generate_teacher_notes(self, subject: str, topic: str, grade: str) -> List[str]:
        """Generate helpful notes for the teacher."""
        return [
            "ARRANGEMENT: For large classes (40+), arrange desks so all students can see the chalkboard. Consider having some students sit on the floor at the front if seating is insufficient.",
            "VOICE PROJECTION: Speak clearly and face the class. Use a louder voice for larger classrooms. Consider appointing a student to repeat key points to the back rows.",
            "BOARD MANAGEMENT: Divide the chalkboard into sections. Write the lesson topic and objectives at the top and leave them visible throughout.",
            "TIME MANAGEMENT: Use a simple timer (watch or sand timer) to keep activities on schedule. If running behind, shorten the practice phase rather than skipping the review.",
            "STUDENT ENGAGEMENT: Call on students by name from all parts of the room. Use 'think-pair-share' for large classes - students think individually, discuss with a partner, then share with the class.",
            f"COMMON MISCONCEPTIONS: Be aware that students often confuse aspects of {topic}. Plan to address these explicitly.",
        ]

    def _generate_differentiation(self, subject: str, topic: str, grade: str) -> Dict[str, Any]:
        """Generate differentiation strategies for mixed-ability classes."""
        return {
            "for_struggling_learners": [
                "Provide simpler, more concrete examples",
                "Pair with a stronger student for peer support",
                "Reduce the number of exercises required",
                "Use visual aids and manipulatives",
            ],
            "for_average_learners": [
                "Provide standard exercises from the textbook or board",
                "Encourage them to explain their reasoning aloud",
                "Set achievable but challenging targets",
            ],
            "for_advanced_learners": [
                "Provide extension questions or enrichment tasks",
                "Ask them to teach a concept to a peer",
                "Give open-ended problems to solve",
                "Assign them as group leaders during activities",
            ],
        }

    def generate_daily_schedule(
        self,
        subjects: List[str],
        grade: str,
        start_time: str = "08:00",
        lesson_duration: int = 40,
        break_duration: int = 20,
    ) -> Dict[str, Any]:
        """Generate a daily timetable/schedule for a class.

        Args:
            subjects: List of subject keys for the day.
            grade: Grade level.
            start_time: School start time in HH:MM format.
            lesson_duration: Minutes per lesson (default 40).
            break_duration: Minutes for break (default 20).

        Returns:
            Daily schedule with timed periods.
        """
        if grade not in GRADES:
            raise ValueError(f"Unknown grade '{grade}'")

        for s in subjects:
            if s not in SUBJECTS:
                raise ValueError(f"Unknown subject '{s}'")

        schedule: Dict[str, Any] = {
            "grade": grade,
            "date": datetime.date.today().isoformat(),
            "periods": [],
        }

        current = datetime.datetime.strptime(start_time, "%H:%M")
        assembly_end = current + datetime.timedelta(minutes=30)

        schedule["periods"].append({
            "name": "Morning Assembly",
            "start": current.strftime("%H:%M"),
            "end": assembly_end.strftime("%H:%M"),
            "duration": 30,
            "type": "assembly",
        })

        current = assembly_end
        break_inserted = False

        for i, subject in enumerate(subjects):
            if not break_inserted and i >= 2:
                break_start = current
                break_end = current + datetime.timedelta(minutes=break_duration)
                schedule["periods"].append({
                    "name": "Short Break",
                    "start": break_start.strftime("%H:%M"),
                    "end": break_end.strftime("%H:%M"),
                    "duration": break_duration,
                    "type": "break",
                })
                current = break_end
                break_inserted = True

            end_time = current + datetime.timedelta(minutes=lesson_duration)
            subject_info = SUBJECTS[subject]
            schedule["periods"].append({
                "name": subject_info["name"],
                "subject_key": subject,
                "start": current.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
                "duration": lesson_duration,
                "type": "lesson",
                "icon": subject_info["icon"],
            })
            current = end_time

        lunch_end = current + datetime.timedelta(minutes=60)
        schedule["periods"].append({
            "name": "Lunch Break",
            "start": current.strftime("%H:%M"),
            "end": lunch_end.strftime("%H:%M"),
            "duration": 60,
            "type": "break",
        })

        schedule["total_hours"] = (
            datetime.datetime.strptime(schedule["periods"][-1]["end"], "%H:%M")
            - datetime.datetime.strptime(schedule["periods"][0]["start"], "%H:%M")
        ).total_seconds() / 3600

        logger.info("Daily schedule generated for %s with %d periods", grade, len(subjects))
        return schedule

    def generate_weekly_plan(
        self,
        subjects: List[str],
        grade: str,
    ) -> Dict[str, Any]:
        """Generate a weekly teaching plan overview.

        Args:
            subjects: List of subject keys to cover.
            grade: Grade level.

        Returns:
            Weekly plan with daily allocations and cross-curricular themes.
        """