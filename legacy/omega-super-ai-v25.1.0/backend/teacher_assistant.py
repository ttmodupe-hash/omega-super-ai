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
        if grade not in GRADES:
            raise ValueError(f"Unknown grade '{grade}'")

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekly_plan: Dict[str, Any] = {
            "grade": grade,
            "week_start": datetime.date.today().isoformat(),
            "days": {},
            "cross_curricular_theme": self._get_cross_curricular_theme(grade),
            "assessment_schedule": self._get_weekly_assessment_schedule(grade),
        }

        day_subjects: Dict[str, List[str]] = {}
        for i, day in enumerate(days):
            start_idx = (i * 2) % len(subjects)
            day_subjects[day] = []
            for j in range(4):
                idx = (start_idx + j) % len(subjects)
                day_subjects[day].append(subjects[idx])

        for day in days:
            weekly_plan["days"][day] = {
                "subjects": [
                    {"subject_key": s, "name": SUBJECTS[s]["name"], "icon": SUBJECTS[s]["icon"]}
                    for s in day_subjects[day]
                ],
                "focus_skill": self._get_daily_focus(day),
                "homework": "Review today's lessons and complete assigned exercises.",
            }

        logger.info("Weekly plan generated for %s", grade)
        return weekly_plan

    def _get_cross_curricular_theme(self, grade: str) -> str:
        """Select a cross-curricular theme appropriate for the grade."""
        themes = [
            "Environmental Conservation and Climate Action",
            "Community Health and Hygiene",
            "Entrepreneurship and Financial Literacy",
            "Digital Citizenship and Online Safety",
            "African Heritage and Cultural Identity",
            "Agricultural Innovation and Food Security",
            "Peace Building and Conflict Resolution",
        ]
        return random.choice(themes)

    def _get_weekly_assessment_schedule(self, grade: str) -> Dict[str, str]:
        """Generate an assessment schedule for the week."""
        return {
            "Monday": "Diagnostic assessment (oral questioning)",
            "Tuesday": "Formative assessment (class exercise)",
            "Wednesday": "Peer assessment activity",
            "Thursday": "Class test (15-minute quiz)",
            "Friday": "Weekly review and reflection",
        }

    def _get_daily_focus(self, day: str) -> str:
        """Get a skill focus for each day of the week."""
        focuses = {
            "Monday": "Critical Thinking and Problem Solving",
            "Tuesday": "Communication and Collaboration",
            "Wednesday": "Creativity and Innovation",
            "Thursday": "Analysis and Evaluation",
            "Friday": "Reflection and Synthesis",
        }
        return focuses.get(day, "General Learning")



# ──────────────────────────────────────────────────────────────────────────
# WORKSHEET GENERATOR
# ──────────────────────────────────────────────────────────────────────────

class WorksheetGenerator:
    """Generates worksheets, quizzes, homework, and revision exams.

    Creates printable assessment materials appropriate for large classes
    and low-resource settings. Supports multiple question types and
    difficulty levels.
    """

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.db = db or DatabaseManager()
        logger.info("WorksheetGenerator initialized")

    def generate_worksheet(
        self,
        subject: str,
        topic: str,
        grade: str,
        num_questions: int = 10,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """Generate a printable worksheet with questions and answer key.

        Args:
            subject: Subject key.
            topic: Topic to assess.
            grade: Grade level.
            num_questions: Number of questions (default 10).
            difficulty: Difficulty level (easy, medium, hard).

        Returns:
            Worksheet with questions, instructions, marking scheme, and metadata.
        """
        if subject not in SUBJECTS:
            raise ValueError(f"Unknown subject '{subject}'")
        if grade not in GRADES:
            raise ValueError(f"Unknown grade '{grade}'")

        ws_uuid = str(uuid.uuid4())
        questions = self._build_questions(subject, topic, grade, num_questions, difficulty)
        answer_key = self._build_answer_key(questions)
        instructions = self._get_worksheet_instructions(subject, grade)

        worksheet: Dict[str, Any] = {
            "uuid": ws_uuid,
            "title": f"{SUBJECTS[subject]['name']} - {topic.title()}",
            "subject": subject,
            "topic": topic,
            "grade": grade,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "instructions": instructions,
            "questions": questions,
            "answer_key": answer_key,
            "total_marks": sum(q.get("marks", 1) for q in questions),
            "time_allowed": num_questions * 3,
            "created_at": datetime.datetime.now().isoformat(),
        }

        try:
            self.db.insert("worksheets", {
                "uuid": ws_uuid,
                "subject": subject,
                "topic": topic,
                "grade": grade,
                "num_questions": num_questions,
                "difficulty": difficulty,
                "questions": json.dumps(questions),
            })
        except Exception as e:
            logger.warning("Failed to save worksheet: %s", e)

        logger.info("Worksheet generated: %s (%s, %s, %d questions)", ws_uuid, subject, topic, num_questions)
        return worksheet

    def _build_questions(
        self,
        subject: str,
        topic: str,
        grade: str,
        num_questions: int,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """Build a list of questions for the worksheet."""
        questions: List[Dict[str, Any]] = []
        for i in range(num_questions):
            q = self._generate_single_question(subject, topic, grade, i + 1, difficulty)
            questions.append(q)
        return questions

    def _generate_single_question(
        self,
        subject: str,
        topic: str,
        grade: str,
        q_num: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        """Generate a single question based on subject and difficulty."""
        templates = self._get_question_templates(subject, difficulty)
        template = random.choice(templates)

        question_text = template["question"].format(topic=topic, grade=grade, num=q_num)
        return {
            "number": q_num,
            "type": template["type"],
            "question": question_text,
            "marks": template.get("marks", 2),
            "answer": template["answer"].format(topic=topic),
            "difficulty": difficulty,
        }

    def _get_question_templates(self, subject: str, difficulty: str) -> List[Dict[str, Any]]:
        """Get question templates for a subject and difficulty."""
        common_templates = [
            {
                "type": "short_answer",
                "question": "Explain what you understand by '{topic}'.",
                "answer": "A clear definition of {topic} with examples.",
                "marks": 2,
            },
            {
                "type": "fill_blank",
                "question": "___________ is defined as {topic}.",
                "answer": "The correct term related to {topic}.",
                "marks": 1,
            },
            {
                "type": "true_false",
                "question": "State whether the following statement about {topic} is TRUE or FALSE: [Statement].",
                "answer": "TRUE / FALSE with explanation.",
                "marks": 1,
            },
        ]

        subject_templates: Dict[str, List[Dict[str, Any]]] = {
            "mathematics": [
                {
                    "type": "calculation",
                    "question": "Solve the following problem: [Problem related to {topic}]",
                    "answer": "Correct numerical answer with working shown.",
                    "marks": 3,
                },
                {
                    "type": "word_problem",
                    "question": "A farmer has [number] items. If she [operation related to {topic}], how many does she have left?",
                    "answer": "Correct answer with step-by-step working.",
                    "marks": 4,
                },
            ],
            "english": [
                {
                    "type": "comprehension",
                    "question": "Read the following passage about {topic} and answer the questions below.",
                    "answer": "Answers derived from the passage.",
                    "marks": 5,
                },
                {
                    "type": "grammar",
                    "question": "Identify the [part of speech] in the following sentence about {topic}.",
                    "answer": "Correct identification with explanation.",
                    "marks": 2,
                },
            ],
            "science": [
                {
                    "type": "explanation",
                    "question": "Describe the process of {topic}. Include the key stages.",
                    "answer": "A step-by-step description of the process.",
                    "marks": 4,
                },
                {
                    "type": "diagram",
                    "question": "Draw and label a diagram showing {topic}.",
                    "answer": "Correctly labelled diagram with all key parts identified.",
                    "marks": 5,
                },
            ],
            "social_studies": [
                {
                    "type": "essay",
                    "question": "Discuss the importance of {topic} in your community. Give three reasons.",
                    "answer": "A well-structured response with at least three valid points.",
                    "marks": 6,
                },
            ],
        }

        return common_templates + subject_templates.get(subject, [])

    def _build_answer_key(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build the answer key / marking scheme for a worksheet."""
        return [
            {
                "question_number": q["number"],
                "correct_answer": q["answer"],
                "marks": q["marks"],
                "marking_guidance": f"Award {q['marks']} mark(s) for correct answer. Partial credit for partially correct responses.",
            }
            for q in questions
        ]

    def _get_worksheet_instructions(self, subject: str, grade: str) -> str:
        """Get standard worksheet instructions."""
        return (
            f"INSTRUCTIONS:\n"
            f"1. Write your name, class, and date at the top of your paper.\n"
            f"2. Read each question carefully before answering.\n"
            f"3. Answer ALL questions.\n"
            f"4. Show all your working for calculation questions.\n"
            f"5. Write your answers clearly and neatly.\n"
            f"6. Check your work before submitting."
        )

    def generate_quiz(
        self,
        subject: str,
        topic: str,
        grade: str,
        num_questions: int = 5,
    ) -> Dict[str, Any]:
        """Generate a quick quiz for rapid assessment.

        Args:
            subject: Subject key.
            topic: Topic to assess.
            grade: Grade level.
            num_questions: Number of questions (default 5).

        Returns:
            Quiz with multiple choice and short answer questions.
        """
        quiz_uuid = str(uuid.uuid4())
        mcq_count = num_questions // 2
        saq_count = num_questions - mcq_count

        questions: List[Dict[str, Any]] = []
        for i in range(mcq_count):
            questions.append({
                "number": i + 1,
                "type": "multiple_choice",
                "question": f"Question {i+1} about {topic}: [Stem statement]?",
                "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                "correct": random.choice(["A", "B", "C", "D"]),
                "marks": 1,
            })

        for i in range(saq_count):
            questions.append({
                "number": mcq_count + i + 1,
                "type": "short_answer",
                "question": f"Briefly explain: [Question about {topic}]?",
                "marks": 2,
            })

        quiz: Dict[str, Any] = {
            "uuid": quiz_uuid,
            "title": f"Quick Quiz: {topic.title()}",
            "subject": subject,
            "topic": topic,
            "grade": grade,
            "type": "quiz",
            "time_limit": num_questions * 2,
            "questions": questions,
            "total_marks": sum(q["marks"] for q in questions),
            "instructions": "Answer ALL questions. Choose the best answer for multiple choice questions.",
            "created_at": datetime.datetime.now().isoformat(),
        }

        logger.info("Quiz generated: %s (%s, %d questions)", quiz_uuid, topic, num_questions)
        return quiz

    def generate_homework(
        self,
        subject: str,
        topic: str,
        grade: str,
    ) -> Dict[str, Any]:
        """Generate a homework assignment.

        Args:
            subject: Subject key.
            topic: Topic covered in class.
            grade: Grade level.

        Returns:
            Homework assignment with tasks and submission instructions.
        """
        hw_uuid = str(uuid.uuid4())

        tasks = [
            f"Review today's lesson on {topic}. Write a summary in your notebook.",
            f"Complete exercises 1-5 on {topic} from your textbook (or board notes).",
            f"Find three examples of {topic} in your home or community. Write them down.",
            f"Draw a diagram or picture illustrating {topic}.",
            f"Prepare two questions about {topic} to ask in the next class.",
        ]

        if "primary" in grade:
            tasks = tasks[:3]
        elif "sss" in grade:
            tasks.append(f"Research {topic} online or in a library book. Write a one-page report.")

        homework: Dict[str, Any] = {
            "uuid": hw_uuid,
            "title": f"Homework: {topic.title()}",
            "subject": subject,
            "topic": topic,
            "grade": grade,
            "date_assigned": datetime.date.today().isoformat(),
            "date_due": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
            "tasks": tasks,
            "materials_needed": ["Notebook", "Pen/pencil", "Textbook if available"],
            "submission_format": "Written in exercise book",
            "teacher_instructions": (
                "Collect homework at the start of the next lesson. "
                "Quickly scan for completion. Select 3-5 books to mark in detail. "
                "Address common errors on the chalkboard."
            ),
        }

        logger.info("Homework generated: %s (%s, %s)", hw_uuid, subject, topic)
        return homework

    def generate_revision_exam(
        self,
        subjects: List[str],
        grade: str,
        num_questions_per_subject: int = 5,
    ) -> Dict[str, Any]:
        """Generate an end-of-term revision exam covering multiple subjects.

        Args:
            subjects: List of subject keys to include.
            grade: Grade level.
            num_questions_per_subject: Questions per subject (default 5).

        Returns:
            Full revision exam with sections, questions, and marking scheme.
        """
        exam_uuid = str(uuid.uuid4())
        sections: List[Dict[str, Any]] = []
        total_marks = 0

        for subject in subjects:
            if subject not in SUBJECTS:
                continue
            subject_info = SUBJECTS[subject]
            topic_list = subject_info.get("primary_topics" if "primary" in grade else "secondary_topics", ["general"])
            topic = random.choice(topic_list)
            questions = self._build_questions(subject, topic, grade, num_questions_per_subject, "mixed")
            section_marks = sum(q["marks"] for q in questions)
            total_marks += section_marks

            sections.append({
                "subject": subject,
                "subject_name": subject_info["name"],
                "topic": topic,
                "questions": questions,
                "section_marks": section_marks,
            })

        exam: Dict[str, Any] = {
            "uuid": exam_uuid,
            "title": f"End of Term Revision Examination - {GRADES.get(grade, {}).get('level', '')} {GRADES.get(grade, {}).get('year', '')}",
            "grade": grade,
            "type": "revision_exam",
            "duration_hours": max(1, len(subjects)),
            "sections": sections,
            "total_marks": total_marks,
            "instructions": (
                "1. Write your name, class, and date on the answer booklet.\n"
                "2. Answer ALL questions in ALL sections.\n"
                "3. Read each question carefully before answering.\n"
                "4. Show all working for mathematics and science questions.\n"
                "5. Manage your time wisely.\n"
                "6. Check your answers before submitting."
            ),
            "created_at": datetime.datetime.now().isoformat(),
        }

        logger.info("Revision exam generated: %s (%d subjects, %d marks)", exam_uuid, len(sections), total_marks)
        return exam


# ──────────────────────────────────────────────────────────────────────────
# TEACHING METHODS
# ──────────────────────────────────────────────────────────────────────────

class TeachingMethods:
    """Provides teaching methodology guidance for African classrooms.

    Offers detailed explanations of various teaching methods, low-resource
    activities, local teaching aid instructions, and classroom management
    strategies specifically for large classes with limited materials.
    """

    def __init__(self) -> None:
        logger.info("TeachingMethods initialized")

    def get_method(self, method_name: str) -> Dict[str, Any]:
        """Retrieve detailed information about a specific teaching method.

        Args:
            method_name: Key of the teaching method. Valid options:
                group_work, peer_teaching, role_play, demonstration,
                discussion, project_based, inquiry_based, storytelling,
                games_based.

        Returns:
            Dictionary with name, description, steps, benefits, and class
            size recommendations.

        Raises:
            ValueError: If method_name is not recognized.
        """
        if method_name not in TEACHING_METHODS:
            valid = ", ".join(TEACHING_METHODS.keys())
            raise ValueError(f"Unknown method '{method_name}'. Valid: {valid}")

        method = copy.deepcopy(TEACHING_METHODS[method_name])
        method["subject_adaptations"] = self._get_subject_adaptations(method_name)
        method["assessment_integration"] = self._get_assessment_integration(method_name)
        return method

    def _get_subject_adaptations(self, method_name: str) -> Dict[str, List[str]]:
        """Get subject-specific adaptations for a teaching method."""
        adaptations: Dict[str, List[str]] = {
            "mathematics": [
                "Use group work for problem-solving stations",
                "Peer teaching for calculation practice",
                "Games-based for multiplication tables",
            ],
            "english": [
                "Role play for dialogue practice",
                "Storytelling for comprehension",
                "Discussion for essay planning",
            ],
            "science": [
                "Demonstration for experiments",
                "Inquiry-based for investigations",
                "Project-based for term projects",
            ],
            "agriculture": [
                "Demonstration using school farm",
                "Project-based for crop cultivation projects",
                "Group work for farm maintenance teams",
            ],
        }
        return adaptations

    def _get_assessment_integration(self, method_name: str) -> List[str]:
        """Get assessment strategies integrated with a teaching method."""
        return [
            "Observe student participation during the activity",
            "Use a simple checklist to record engagement levels",
            "Have students complete a brief reflection after the activity",
            "Collect and review any written outputs produced",
        ]

    def get_low_resource_activity(self, subject: str) -> Dict[str, Any]:
        """Get a teaching activity that requires minimal or no materials.

        Args:
            subject: Subject key.

        Returns:
            Activity plan with title, materials (none or local), procedure,
            and assessment approach.
        """
        activities: Dict[str, List[Dict[str, Any]]] = {
            "mathematics": [
                {
                    "title": "Body Number Line",
                    "materials": ["None - students use their bodies"],
                    "procedure": [
                        "Have students stand in a line to form a human number line.",
                        "Call out numbers and have students position themselves.",
                        "Use for ordering, comparing, and basic operations.",
                    ],
                    "assessment": "Observe accuracy of positioning. Ask students to explain their reasoning.",
                },
                {
                    "title": "Stone Counting",
                    "materials": ["Small stones or seeds collected from the ground"],
                    "procedure": [
                        "Give each student 10-20 small stones.",
                        "Use stones as counters for addition, subtraction, and grouping.",
                        "Students can keep stones in their pockets for practice at home.",
                    ],
                    "assessment": "Check accuracy of calculations using stones.",
                },
            ],
            "english": [
                {
                    "title": "Circle Story",
                    "materials": ["None"],
                    "procedure": [
                        "Students sit in a circle.",
                        "Teacher starts a story with one sentence.",
                        "Each student adds one sentence to continue the story.",
                        "Record the story on the chalkboard as it develops.",
                    ],
                    "assessment": "Evaluate sentence structure, vocabulary use, and creativity.",
                },
                {
                    "title": "Chalkboard Charades",
                    "materials": ["Chalkboard and chalk"],
                    "procedure": [
                        "Write vocabulary words on the board.",
                        "One student acts out a word without speaking.",
                        "Others guess the word and use it in a sentence.",
                    ],
                    "assessment": "Record correct usage of vocabulary in sentences.",
                },
            ],
            "science": [
                {
                    "title": "Observation Walk",
                    "materials": ["Notebook and pencil"],
                    "procedure": [
                        "Take students on a walk around the school compound.",
                        "Ask them to observe plants, insects, and weather conditions.",
                        "Return to class and record observations on the chalkboard.",
                        "Discuss findings and draw conclusions.",
                    ],
                    "assessment": "Review observation notes for detail and accuracy.",
                },
                {
                    "title": "Water Cycle Demonstration",
                    "materials": ["Plastic bottle", "Water", "Sunlight"],
                    "procedure": [
                        "Fill a clear plastic bottle one-third with water.",
                        "Seal and place in direct sunlight.",
                        "Observe condensation forming on the inside over time.",
                        "Explain evaporation, condensation, and precipitation.",
                    ],
                    "assessment": "Students draw and label the water cycle diagram.",
                },
            ],
            "social_studies": [
                {
                    "title": "Community Mapping",
                    "materials": ["Large paper or ground space", "Sticks or chalk"],
                    "procedure": [
                        "Students work in groups to draw a map of their community.",
                        "Mark important places: school, market, mosque/church, homes.",
                        "Present maps to the class and explain key features.",
                    ],
                    "assessment": "Evaluate map accuracy and presentation quality.",
                },
            ],
            "agriculture": [
                {
                    "title": "Soil Texture Test",
                    "materials": ["Soil samples", "Water", "Jar or bottle"],
                    "procedure": [
                        "Collect soil samples from different locations.",
                        "Mix with water in a jar and shake.",
                        "Let settle and observe layers (sand, silt, clay).",
                        "Discuss soil types and their suitability for crops.",
                    ],
                    "assessment": "Students identify soil types and recommend crops.",
                },
            ],
            "arts": [
                {
                    "title": "Nature Collage",
                    "materials": ["Leaves, flowers, seeds collected outside", "Paper", "Glue (flour paste)"],
                    "procedure": [
                        "Students collect natural materials during a nature walk.",
                        "Arrange materials on paper to create a picture or pattern.",
                        "Use flour-and-water paste as glue if commercial glue unavailable.",
                        "Display completed artworks on classroom walls.",
                    ],
                    "assessment": "Evaluate creativity, use of materials, and neatness.",
                },
            ],
            "physical_education": [
                {
                    "title": "Circle Relay",
                    "materials": ["Open space"],
                    "procedure": [
                        "Divide class into teams of 8-10 students.",
                        "Teams form circles. On 'go', first student runs around circle.",
                        "Tags next student who continues. Continue until all have run.",
                        "First team to finish wins.",
                    ],
                    "assessment": "Observe teamwork, fairness, and participation.",
                },
            ],
        }

        subject_activities = activities.get(subject, [
            {
                "title": "Think-Pair-Share",
                "materials": ["None"],
                "procedure": [
                    "Pose a question to the class.",
                    "Students think individually for 30 seconds.",
                    "Pair with a neighbour to discuss.",
                    "Share answers with the whole class.",
                ],
                "assessment": "Listen to shared answers for understanding.",
            }
        ])

        result = random.choice(subject_activities)
        result["subject"] = subject
        result["class_size_note"] = "Designed for classes of 40-80 students"
        return result

    def get_teaching_aids(self, subject: str) -> Dict[str, Any]:
        """Get instructions for making visual aids from local materials.

        Args:
            subject: Subject key.

        Returns:
            Instructions for creating low-cost teaching aids.
        """
        aids: Dict[str, List[Dict[str, Any]]] = {
            "mathematics": [
                {
                    "name": "Number Chart",
                    "materials": ["Cardboard box", "Marker or charcoal", "Ruler (optional)"],
                    "steps": [
                        "Cut a large rectangle from a cardboard box.",
                        "Draw a grid of 10 columns and 10 rows.",
                        "Fill in numbers 1-100 in the grid.",
                        "Hang on wall with string or tape.",
                    ],
                    "uses": "Number recognition, counting, skip counting, multiplication tables",
                },
                {
                    "name": "Fraction Wheel",
                    "materials": ["Cardboard", "String or paper fastener"],
                    "steps": [
                        "Cut two circles from cardboard, one slightly larger.",
                        "Divide the larger circle into equal parts (halves, thirds, quarters).",
                        "Cut out one section to create a window.",
                        "Attach the smaller circle behind with string through the centre.",
                    ],
                    "uses": "Visualising fractions, equivalent fractions, angle measurement",
                },
            ],
            "science": [
                {
                    "name": "Human Body Chart",
                    "materials": ["Large paper or cardboard", "Markers or coloured pencils"],
                    "steps": [
                        "Draw the outline of a human body on large paper.",
                        "Draw and label major organs (heart, lungs, brain, stomach).",
                        "Use different colours for different systems.",
                        "Laminate with clear tape or plastic wrap for durability.",
                    ],
                    "uses": "Teaching anatomy, organ functions, body systems",
                },
                {
                    "name": "Solar System Model",
                    "materials": ["Different sized stones or clay balls", "String", "Sticks"],
                    "steps": [
                        "Collect stones of different sizes to represent planets.",
                        "Paint or mark each 'planet' with its name.",
                        "Arrange in order from the 'sun' (largest stone) on the ground.",
                        "Use string to show orbital paths.",
                    ],
                    "uses": "Teaching planet names, sizes, distances, and order",
                },
            ],
            "geography": [
                {
                    "name": "Contour Map from Soil",
                    "materials": ["Sand or soil", "Plywood or flat cardboard", "Sticks"],
                    "steps": [
                        "Build a small hill or mountain shape with damp sand on the board.",
                        "Place sticks at equal height intervals into the sand.",
                        "Connect sticks at the same height with string to show contour lines.",
                        "Spray gently with water to fix the shape.",
                    ],
                    "uses": "Teaching contour lines, elevation, landforms",
                },
            ],
            "english": [
                {
                    "name": "Word Wall",
                    "materials": ["Paper strips", "Tape or thumbtacks", "Marker"],
                    "steps": [
                        "Write vocabulary words on paper strips (one word per strip).",
                        "Organise by category (nouns, verbs, theme).",
                        "Stick to a designated wall or board space.",
                        "Update weekly with new vocabulary.",
                    ],
                    "uses": "Vocabulary building, spelling reference, word categorisation",
                },
            ],
        }

        return {
            "subject": subject,
            "aids": aids.get(subject, [
                {
                    "name": "Flashcards",
                    "materials": ["Cardboard", "Marker"],
                    "steps": [
                        "Cut cardboard into equal-sized rectangles.",
                        "Write key terms or questions on one side.",
                        "Write definitions or answers on the reverse.",
                    ],
                    "uses": "Quick review, pair work, memory games",
                }
            ]),
            "general_tips": [
                "Use chalkboard effectively - divide into sections.",
                "Use coloured chalk or charcoal for emphasis.",
                "Hang student work on walls as visual aids.",
                "Use real objects from the environment as teaching aids.",
            ],
        }

    def get_classroom_management_tips(self) -> Dict[str, Any]:
        """Get strategies for managing large classes effectively.

        Returns:
            Comprehensive classroom management guidance.
        """
        return {
            "overview": (
                "Managing large classes (40-80 students) requires preparation, "
                "clear routines, and engaging strategies. These tips are designed "
                "for under-resourced African classrooms with limited space and materials."
            ),
            "seating_arrangements": [
                {
                    "name": "Grid Layout",
                    "description": "Desks in straight rows facing the chalkboard.",
                    "best_for": "Lectures, board work, individual tests",
                    "tips": "Leave aisles for movement. Rotate front-row students weekly.",
                },
                {
                    "name": "Cluster Groups",
                    "description": "Desks grouped in sets of 4-6 facing each other.",
                    "best_for": "Group work, discussions, peer learning",
                    "tips": "Assign roles within each group. Rearrange before and after group activities.",
                },
                {
                    "name": "U-Shape",
                    "description": "Desks arranged in a U or semi-circle.",
                    "best_for": "Discussions, demonstrations, storytelling",
                    "tips": "Works best for classes under 50. Use when space permits.",
                },
            ],
            "routines_and_procedures": [
                "Greet students at the door to set a positive tone.",
                "Start every lesson with a clear routine (e.g., prayer, attendance, review).",
                "Have a standard signal for attention (clap pattern, raised hand, phrase).",
                "Assign classroom duties to students (board cleaning, attendance, distributing books).",
                "Establish clear entry and exit procedures to avoid chaos.",
                "Set time limits for activities and use a visible timer.",
            ],
            "engagement_strategies": [
                {
                    "strategy": "Cold Calling",
                    "description": "Call on random students rather than only those who raise hands.",
                    "tip": "Use popsicle sticks with names, or a numbered system.",
                },
                {
                    "strategy": "Think-Pair-Share",
                    "description": "Individual thinking, then pair discussion, then class sharing.",
                    "tip": "Ensures all students participate, not just confident ones.",
                },
                {
                    "strategy": "Choral Response",
                    "description": "Whole class responds together to questions.",
                    "tip": "Great for vocabulary, times tables, and key facts.",
                },
                {
                    "strategy": "Student Reporters",
                    "description": "Assign students to report group findings to the class.",
                    "tip": "Rotate reporters so all students get practice presenting.",
                },
            ],
            "discipline_techniques": [
                "Use positive reinforcement: praise good behaviour publicly.",
                "Use proximity: stand near off-task students.",
                "Use non-verbal cues: eye contact, hand signals, a look.",
                "Apply consistent consequences fairly to all students.",
                "Avoid shouting - use a calm but firm voice.",
                "Build relationships: learn all students' names quickly.",
                "Involve parents/guardians for persistent issues.",
            ],
            "time_management": [
                "Plan every minute of the lesson in advance.",
                "Have extra activities ready for fast finishers.",
                "Use transitions efficiently (e.g., while students are writing, prepare the next activity).",
                "Set clear time limits for each activity and announce them.",
                "End lessons 2-3 minutes early to summarise and dismiss orderly.",
            ],
            "assessment_in_large_classes": [
                "Use peer marking for objective questions.",
                "Mark a rotation of books each week (not all every day).",
                "Use self-assessment checklists.",
                "Conduct oral assessments during group work.",
                "Use exit tickets: one quick question at the end of each lesson.",
            ],
        }



# ──────────────────────────────────────────────────────────────────────────
# ASSESSMENT TRACKER
# ──────────────────────────────────────────────────────────────────────────

class AssessmentTracker:
    """Manages student assessment records, grading schemes, and progress tracking.

    Implements continuous assessment (CA) frameworks used across African
    education systems. Supports WAEC, NECO, KCSE, and WASSCE grading schemes.
    """

    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.db = db or DatabaseManager()
        logger.info("AssessmentTracker initialized")

    def create_assessment_template(
        self,
        subject: str,
        assessment_type: str,
    ) -> Dict[str, Any]:
        """Create an assessment template for a specific subject and type.

        Args:
            subject: Subject key.
            assessment_type: Type of assessment - continuous_assessment, exam,
                practical, or project.

        Returns:
            Assessment template with structure, marking criteria, and instructions.
        """
        if subject not in SUBJECTS:
            raise ValueError(f"Unknown subject '{subject}'")

        templates: Dict[str, Dict[str, Any]] = {
            "continuous_assessment": {
                "name": "Continuous Assessment",
                "weight": 40,
                "components": [
                    {"name": "Class Tests", "weight": 15, "frequency": "Bi-weekly"},
                    {"name": "Assignments", "weight": 10, "frequency": "Weekly"},
                    {"name": "Participation", "weight": 5, "frequency": "Daily"},
                    {"name": "Projects", "weight": 10, "frequency": "Per term"},
                ],
                "instructions": "Record scores for each component throughout the term. Calculate weighted average.",
            },
            "exam": {
                "name": "Terminal Examination",
                "weight": 60,
                "components": [
                    {"name": "Section A - Objective", "marks": 20, "type": "Multiple choice / Short answer"},
                    {"name": "Section B - Theory", "marks": 50, "type": "Essay / Long answer"},
                    {"name": "Section C - Problem Solving", "marks": 30, "type": "Application questions"},
                ],
                "instructions": "Examination to be conducted under standard conditions. Duration: 2-3 hours.",
            },
            "practical": {
                "name": "Practical Assessment",
                "weight": 30,
                "components": [
                    {"name": "Procedure", "marks": 25, "criteria": "Correct method and sequence"},
                    {"name": "Observation", "marks": 25, "criteria": "Accurate recording of results"},
                    {"name": "Skills", "marks": 25, "criteria": "Proper handling of materials"},
                    {"name": "Conclusion", "marks": 25, "criteria": "Correct interpretation of results"},
                ],
                "instructions": "Assess each student individually or in pairs. Use provided rubric.",
            },
            "project": {
                "name": "Project Assessment",
                "weight": 20,
                "components": [
                    {"name": "Planning", "marks": 20, "criteria": "Clear objectives and timeline"},
                    {"name": "Execution", "marks": 40, "criteria": "Quality of work and effort"},
                    {"name": "Presentation", "marks": 30, "criteria": "Clarity and organisation"},
                    {"name": "Reflection", "marks": 10, "criteria": "Self-assessment and learning"},
                ],
                "instructions": "Projects span 2-4 weeks. Students present to the class.",
            },
        }

        template = templates.get(assessment_type, templates["continuous_assessment"])
        template["subject"] = subject
        template["subject_name"] = SUBJECTS[subject]["name"]
        template["total_marks"] = 100
        template["grading"] = "See grading scheme for your country"
        template["created_at"] = datetime.datetime.now().isoformat()

        logger.info("Assessment template created: %s for %s", assessment_type, subject)
        return template

    def get_grading_scheme(self, country: str) -> Dict[str, Any]:
        """Get the official grading scheme for a given country/exam board.

        Args:
            country: Country or exam board code. Supported:
                'waec', 'neco', 'kcse', 'wassce', 'nigeria', 'kenya',
                'ghana', 'uganda', 'tanzania', 'zimbabwe'.

        Returns:
            Grading scheme with grade boundaries and descriptions.

        NOTE: Grading schemes are indicative and may vary by year.
        Always verify with the latest official examination board guidelines.
        """
        schemes: Dict[str, Dict[str, Any]] = {
            "waec": {
                "name": "WAEC (West African Examinations Council)",
                "countries": ["Nigeria", "Ghana", "Sierra Leone", "The Gambia", "Liberia"],
                "grades": [
                    {"grade": "A1", "min": 75, "max": 100, "description": "Excellent", "points": 1},
                    {"grade": "B2", "min": 70, "max": 74, "description": "Very Good", "points": 2},
                    {"grade": "B3", "min": 65, "max": 69, "description": "Good", "points": 3},
                    {"grade": "C4", "min": 60, "max": 64, "description": "Credit", "points": 4},
                    {"grade": "C5", "min": 55, "max": 59, "description": "Credit", "points": 5},
                    {"grade": "C6", "min": 50, "max": 54, "description": "Credit", "points": 6},
                    {"grade": "D7", "min": 45, "max": 49, "description": "Pass", "points": 7},
                    {"grade": "E8", "min": 40, "max": 44, "description": "Pass", "points": 8},
                    {"grade": "F9", "min": 0, "max": 39, "description": "Fail", "points": 9},
                ],
                "pass_grades": ["A1", "B2", "B3", "C4", "C5", "C6"],
                "disclaimer": "WAEC grading may vary. Verify with official WAEC publications.",
            },
            "neco": {
                "name": "NECO (National Examinations Council) - Nigeria",
                "countries": ["Nigeria"],
                "grades": [
                    {"grade": "A1", "min": 75, "max": 100, "description": "Excellent", "points": 1},
                    {"grade": "B2", "min": 70, "max": 74, "description": "Very Good", "points": 2},
                    {"grade": "B3", "min": 65, "max": 69, "description": "Good", "points": 3},
                    {"grade": "C4", "min": 60, "max": 64, "description": "Credit", "points": 4},
                    {"grade": "C5", "min": 55, "max": 59, "description": "Credit", "points": 5},
                    {"grade": "C6", "min": 50, "max": 54, "description": "Credit", "points": 6},
                    {"grade": "D7", "min": 45, "max": 49, "description": "Pass", "points": 7},
                    {"grade": "E8", "min": 40, "max": 44, "description": "Pass", "points": 8},
                    {"grade": "F9", "min": 0, "max": 39, "description": "Fail", "points": 9},
                ],
                "pass_grades": ["A1", "B2", "B3", "C4", "C5", "C6"],
                "disclaimer": "NECO grading is subject to change. Consult NECO official website.",
            },
            "kcse": {
                "name": "KCSE (Kenya Certificate of Secondary Education)",
                "countries": ["Kenya"],
                "grades": [
                    {"grade": "A", "min": 80, "max": 100, "description": "Excellent", "points": 12},
                    {"grade": "A-", "min": 75, "max": 79, "description": "Very Good", "points": 11},
                    {"grade": "B+", "min": 70, "max": 74, "description": "Good", "points": 10},
                    {"grade": "B", "min": 65, "max": 69, "description": "Good", "points": 9},
                    {"grade": "B-", "min": 60, "max": 64, "description": "Average", "points": 8},
                    {"grade": "C+", "min": 55, "max": 59, "description": "Average", "points": 7},
                    {"grade": "C", "min": 50, "max": 54, "description": "Average", "points": 6},
                    {"grade": "C-", "min": 45, "max": 49, "description": "Pass", "points": 5},
                    {"grade": "D+", "min": 40, "max": 44, "description": "Pass", "points": 4},
                    {"grade": "D", "min": 35, "max": 39, "description": "Pass", "points": 3},
                    {"grade": "D-", "min": 30, "max": 34, "description": "Pass", "points": 2},
                    {"grade": "E", "min": 0, "max": 29, "description": "Fail", "points": 1},
                ],
                "pass_grades": ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"],
                "disclaimer": "KCSE grading reviewed periodically. Check KNEC for latest updates.",
            },
            "wassce": {
                "name": "WASSCE (West African Senior School Certificate Examination)",
                "countries": ["West Africa"],
                "grades": [
                    {"grade": "A1", "min": 75, "max": 100, "description": "Excellent", "points": 1},
                    {"grade": "B2", "min": 70, "max": 74, "description": "Very Good", "points": 2},
                    {"grade": "B3", "min": 65, "max": 69, "description": "Good", "points": 3},
                    {"grade": "C4", "min": 60, "max": 64, "description": "Credit", "points": 4},
                    {"grade": "C5", "min": 55, "max": 59, "description": "Credit", "points": 5},
                    {"grade": "C6", "min": 50, "max": 54, "description": "Credit", "points": 6},
                    {"grade": "D7", "min": 45, "max": 49, "description": "Pass", "points": 7},
                    {"grade": "E8", "min": 40, "max": 44, "description": "Pass", "points": 8},
                    {"grade": "F9", "min": 0, "max": 39, "description": "Fail", "points": 9},
                ],
                "pass_grades": ["A1", "B2", "B3", "C4", "C5", "C6"],
                "disclaimer": "WASSCE grading subject to revision. Consult WAEC official sources.",
            },
            "uganda": {
                "name": "UCE/UACE (Uganda National Examinations Board)",
                "countries": ["Uganda"],
                "grades": [
                    {"grade": "D1", "min": 80, "max": 100, "description": "Distinction", "points": 1},
                    {"grade": "D2", "min": 75, "max": 79, "description": "Distinction", "points": 2},
                    {"grade": "C3", "min": 70, "max": 74, "description": "Credit", "points": 3},
                    {"grade": "C4", "min": 65, "max": 69, "description": "Credit", "points": 4},
                    {"grade": "C5", "min": 60, "max": 64, "description": "Credit", "points": 5},
                    {"grade": "C6", "min": 50, "max": 59, "description": "Credit", "points": 6},
                    {"grade": "P7", "min": 45, "max": 49, "description": "Pass", "points": 7},
                    {"grade": "P8", "min": 35, "max": 44, "description": "Pass", "points": 8},
                    {"grade": "F9", "min": 0, "max": 34, "description": "Fail", "points": 9},
                ],
                "pass_grades": ["D1", "D2", "C3", "C4", "C5", "C6", "P7", "P8"],
                "disclaimer": "UNEB grading reviewed periodically. Verify with official UNEB publications.",
            },
            "tanzania": {
                "name": "NECTA (National Examinations Council of Tanzania)",
                "countries": ["Tanzania"],
                "grades": [
                    {"grade": "A", "min": 75, "max": 100, "description": "Excellent", "points": 1},
                    {"grade": "B", "min": 65, "max": 74, "description": "Good", "points": 2},
                    {"grade": "C", "min": 45, "max": 64, "description": "Satisfactory", "points": 3},
                    {"grade": "D", "min": 30, "max": 44, "description": "Pass", "points": 4},
                    {"grade": "F", "min": 0, "max": 29, "description": "Fail", "points": 5},
                ],
                "pass_grades": ["A", "B", "C", "D"],
                "disclaimer": "NECTA grading subject to change. Check NECTA official website.",
            },
        }

        aliases = {
            "nigeria": "neco",
            "kenya": "kcse",
            "ghana": "waec",
            "sierra_leone": "waec",
            "gambia": "waec",
            "liberia": "waec",
            "uganda": "uganda",
            "tanzania": "tanzania",
            "zimbabwe": "waec",
        }

        key = aliases.get(country.lower(), country.lower())
        scheme = schemes.get(key)

        if scheme is None:
            logger.warning("Grading scheme not found for '%s', returning WAEC as default", country)
            scheme = schemes["waec"]
            scheme["note"] = f"Scheme for '{country}' not specifically found. Showing WAEC as reference."

        return scheme

    def track_student_progress(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track and analyse student progress over time.

        Args:
            student_data: Dictionary with keys:
                - student_name: str
                - student_id: str (optional)
                - grade: str
                - assessments: List of dicts with subject, type, score, max_score, term, year

        Returns:
            Progress report with trends, strengths, weaknesses, and recommendations.

        DISCLAIMER: This tool provides analytical support only. Final decisions
        about student progression should be made by qualified educators.
        """
        assessments = student_data.get("assessments", [])
        if not assessments:
            return {"error": "No assessment data provided"}

        student_uuid = student_data.get("student_id") or str(uuid.uuid4())
        try:
            existing = self.db.execute(
                "SELECT uuid FROM students WHERE uuid = ?", (student_uuid,)
            )
            if not existing:
                self.db.insert("students", {
                    "uuid": student_uuid,
                    "name": student_data.get("student_name", "Unknown"),
                    "grade": student_data.get("grade", ""),
                })
        except Exception as e:
            logger.warning("Database error tracking student: %s", e)

        subject_scores: Dict[str, List[float]] = {}
        for a in assessments:
            subject = a["subject"]
            pct = (a["score"] / a.get("max_score", 100)) * 100 if a.get("max_score", 100) > 0 else 0
            if subject not in subject_scores:
                subject_scores[subject] = []
            subject_scores[subject].append(pct)

        subject_averages = {
            subject: round(sum(scores) / len(scores), 1)
            for subject, scores in subject_scores.items()
        }

        sorted_subjects = sorted(subject_averages.items(), key=lambda x: x[1], reverse=True)

        overall_average = round(
            sum(subject_averages.values()) / len(subject_averages), 1
        ) if subject_averages else 0

        strengths = [subj for subj, avg in sorted_subjects if avg >= 70]
        needs_support = [subj for subj, avg in sorted_subjects if 50 <= avg < 70]
        at_risk = [subj for subj, avg in sorted_subjects if avg < 50]

        term_data: Dict[str, Dict[str, List[float]]] = {}
        for a in assessments:
            term_key = f"{a.get('year', '2024')}-{a.get('term', '1')}"
            if term_key not in term_data:
                term_data[term_key] = {}
            subj = a["subject"]
            pct = (a["score"] / a.get("max_score", 100)) * 100
            if subj not in term_data[term_key]:
                term_data[term_key][subj] = []
            term_data[term_key][subj].append(pct)

        trend = "stable"
        if len(term_data) >= 2:
            term_keys = sorted(term_data.keys())
            first_avg = sum(
                sum(v) / len(v) for v in term_data[term_keys[0]].values()
            ) / max(len(term_data[term_keys[0]]), 1)
            last_avg = sum(
                sum(v) / len(v) for v in term_data[term_keys[-1]].values()
            ) / max(len(term_data[term_keys[-1]]), 1)
            if last_avg > first_avg + 5:
                trend = "improving"
            elif last_avg < first_avg - 5:
                trend = "declining"

        report: Dict[str, Any] = {
            "student_name": student_data.get("student_name", "Unknown"),
            "student_id": student_uuid,
            "grade": student_data.get("grade", ""),
            "report_date": datetime.date.today().isoformat(),
            "overall_average": overall_average,
            "trend": trend,
            "subject_breakdown": subject_averages,
            "strengths": strengths,
            "needs_support": needs_support,
            "at_risk": at_risk,
            "recommendations": self._generate_recommendations(strengths, needs_support, at_risk),
            "teacher_actions": [
                "Meet with student to discuss progress and set goals",
                "Contact parents/guardians with specific feedback",
                "Provide differentiated materials for areas needing support",
                "Set up peer tutoring for at-risk subjects",
                "Schedule follow-up assessment in 2-4 weeks",
            ],
        }

        logger.info("Progress report generated for student %s", student_uuid)
        return report

    def _generate_recommendations(
        self,
        strengths: List[str],
        needs_support: List[str],
        at_risk: List[str],
    ) -> List[str]:
        """Generate personalised recommendations based on performance."""
        recommendations = []

        if strengths:
            recommendations.append(
                f"Encourage the student to maintain strong performance in: {', '.join(strengths)}."
            )
            recommendations.append(
                f"Consider peer tutoring: this student could support classmates in {strengths[0]}."
            )

        if needs_support:
            recommendations.append(
                f"Provide additional practice and review in: {', '.join(needs_support)}."
            )
            recommendations.append(
                f"Use visual aids and hands-on activities for {needs_support[0]} concepts."
            )

        if at_risk:
            recommendations.append(
                f"URGENT: Arrange one-on-one or small group support for: {', '.join(at_risk)}."
            )
            recommendations.append(
                f"Consider referral to remedial classes for {', '.join(at_risk)}."
            )
            recommendations.append(
                "Meet with parents/guardians to discuss support strategies at home."
            )

        if not at_risk and not needs_support:
            recommendations.append(
                "Student is performing well across all subjects. Provide enrichment activities."
            )

        return recommendations

    def calculate_final_grade(
        self,
        ca_scores: List[float],
        exam_score: float,
        ca_weight: float = 40.0,
        exam_weight: float = 60.0,
    ) -> Dict[str, Any]:
        """Calculate final grade from continuous assessment and exam scores.

        Args:
            ca_scores: List of continuous assessment scores (out of 100 each).
            exam_score: Examination score (out of 100).
            ca_weight: Weight percentage for CA (default 40).
            exam_weight: Weight percentage for exam (default 60).

        Returns:
            Final grade calculation with breakdown.

        NOTE: This is a general calculation tool. Specific schools and exam
        boards may use different weighting systems. Adjust weights accordingly.
        """
        if not ca_scores:
            ca_average = 0
        else:
            ca_average = sum(ca_scores) / len(ca_scores)

        ca_contribution = ca_average * (ca_weight / 100)
        exam_contribution = exam_score * (exam_weight / 100)
        final_score = ca_contribution + exam_contribution

        grade = "F"
        description = "Fail"
        if final_score >= 75:
            grade, description = "A1", "Excellent"
        elif final_score >= 70:
            grade, description = "B2", "Very Good"
        elif final_score >= 65:
            grade, description = "B3", "Good"
        elif final_score >= 60:
            grade, description = "C4", "Credit"
        elif final_score >= 55:
            grade, description = "C5", "Credit"
        elif final_score >= 50:
            grade, description = "C6", "Credit"
        elif final_score >= 45:
            grade, description = "D7", "Pass"
        elif final_score >= 40:
            grade, description = "E8", "Pass"

        return {
            "ca_average": round(ca_average, 1),
            "ca_weight": ca_weight,
            "ca_contribution": round(ca_contribution, 1),
            "exam_score": exam_score,
            "exam_weight": exam_weight,
            "exam_contribution": round(exam_contribution, 1),
            "final_score": round(final_score, 1),
            "grade": grade,
            "description": description,
            "passed": final_score >= 50,
        }



# ──────────────────────────────────────────────────────────────────────────
# STEM EXPERIMENTS
# ──────────────────────────────────────────────────────────────────────────

class STEMExperiments:
    """Provides hands-on STEM experiments using household/local materials.

    All experiments are designed to be safe, low-cost, and use materials
    readily available in African communities. Suitable for classes of 40-80
    students with group-based setup.
    """

    def __init__(self) -> None:
        logger.info("STEMExperiments initialized")

    def get_experiment(self, subject: str, topic: str) -> Dict[str, Any]:
        """Get a science experiment for a subject and topic.

        Args:
            subject: Subject key (biology, chemistry, physics, science).
            topic: Topic the experiment should demonstrate.

        Returns:
            Complete experiment protocol with materials, procedure, safety
            notes, and expected results.

        SAFETY DISCLAIMER: All experiments should be supervised by a
        qualified teacher. Follow local safety guidelines.
        """
        experiments: Dict[str, List[Dict[str, Any]]] = {
            "biology": [
                {
                    "title": "Observing Osmosis in an Egg",
                    "topic": "osmosis",
                    "materials": ["Raw egg", "White vinegar", "Clear container", "Water", "Corn syrup"],
                    "procedure": [
                        "Place a raw egg in a container and cover with white vinegar.",
                        "Leave for 24-48 hours until the shell dissolves.",
                        "Remove the egg and gently rinse. Observe the rubbery membrane.",
                        "Place the egg in water for several hours and observe swelling.",
                        "Then place it in corn syrup and observe shrinking.",
                    ],
                    "expected_result": "Egg swells in water (water enters) and shrinks in syrup (water leaves), demonstrating osmosis.",
                    "safety": ["Wash hands after handling raw egg.", "Do not consume the egg after the experiment."],
                    "group_size": "2-3 students per group",
                    "class_size_note": "For 40+ students, prepare 15-20 eggs. Groups share observations.",
                },
                {
                    "title": "Extracting DNA from Banana",
                    "topic": "dna",
                    "materials": ["Ripe banana", "Warm water", "Dish soap", "Salt", "Rubbing alcohol", "Plastic bag", "Clear cup", "Sieve"],
                    "procedure": [
                        "Mash half a banana in a plastic bag with 100ml warm water.",
                        "Add one teaspoon of dish soap and a pinch of salt.",
                        "Mix gently and let sit for 5 minutes.",
                        "Strain the mixture through a sieve into a clear cup.",
                        "Slowly pour cold rubbing alcohol down the side of the cup.",
                        "White stringy substance at the boundary is DNA.",
                    ],
                    "expected_result": "White, stringy DNA precipitates at the alcohol-water boundary layer.",
                    "safety": ["Do not drink the alcohol.", "Wash hands thoroughly after the experiment."],
                    "group_size": "3-4 students per group",
                    "class_size_note": "One banana serves 2 groups. For 40 students, need 10 bananas.",
                },
                {
                    "title": "Photosynthesis Demonstration",
                    "topic": "photosynthesis",
                    "materials": ["Two potted plants", "Black paper", "Clear plastic bag", "String", "Sunny window"],
                    "procedure": [
                        "Cover one leaf of a plant with black paper on both sides.",
                        "Leave both plants in sunlight for 24-48 hours.",
                        "Place a clear bag over a leaf on the uncovered plant and seal.",
                        "After several hours, observe condensation in the bag (transpiration).",
                        "Remove the covered leaf and test for starch using iodine if available.",
                    ],
                    "expected_result": "Uncovered leaf tests positive for starch; covered leaf does not, showing light is needed for photosynthesis.",
                    "safety": ["Iodine can stain. Handle with care.", "Use gloves if available."],
                    "group_size": "Whole class demonstration or 4-5 groups",
                    "class_size_note": "Best as teacher demonstration for 40+ students.",
                },
                {
                    "title": "Germination Rate Experiment",
                    "topic": "germination",
                    "materials": ["Bean or maize seeds", "Cotton wool", "Plastic containers", "Water", "Ruler"],
                    "procedure": [
                        "Place cotton wool in several cups and moisten with water.",
                        "Place 5 seeds in each cup, spaced apart.",
                        "Put cups in different conditions: sunlight, shade, dark cupboard.",
                        "Water equally each day.",
                        "Record which seeds germinate first and measure growth daily.",
                    ],
                    "expected_result": "Seeds in light and warmth germinate fastest. Seeds in dark may germinate but grow poorly.",
                    "safety": ["Mold may grow on wet cotton. Replace if moldy."],
                    "group_size": "2-3 students per group",
                    "class_size_note": "Each group manages 3 cups. Easy to scale for any class size.",
                },
            ],
            "chemistry": [
                {
                    "title": "Making a Simple Acid-Base Indicator",
                    "topic": "acids_and_bases",
                    "materials": ["Red cabbage leaves", "Water", "Pot or pan", "Heat source", "Small containers", "Test substances (lemon juice, soap water, baking soda, vinegar)"],
                    "procedure": [
                        "Chop red cabbage and boil in water for 10 minutes.",
                        "Strain the liquid - this is your indicator (purple).",
                        "Pour small amounts into separate containers.",
                        "Add different test substances to each container.",
                        "Observe and record colour changes.",
                    ],
                    "expected_result": "Acids turn indicator red/pink. Bases turn it green/yellow. Neutral stays purple.",
                    "safety": ["Adult supervision required for boiling.", "Do not taste any substances."],
                    "group_size": "Teacher demonstration or 4 students per group",
                    "class_size_note": "Teacher demonstration works best for 40+ students.",
                },
                {
                    "title": "Volcano Eruption Model",
                    "topic": "chemical_reactions",
                    "materials": ["Baking soda", "Vinegar", "Dish soap", "Red food colouring", "Empty plastic bottle", "Sand or soil", "Tray"],
                    "procedure": [
                        "Place the bottle on the tray and build a 'volcano' mound around it using sand/soil.",
                        "Add 2 tablespoons of baking soda into the bottle.",
                        "Add a few drops of dish soap and red colouring.",
                        "Pour vinegar into the bottle quickly.",
                        "Stand back and observe the eruption.",
                    ],
                    "expected_result": "Foamy red 'lava' erupts from the bottle due to the acid-base reaction producing CO2 gas.",
                    "safety": ["Stand back when adding vinegar.", "Do not get the mixture in eyes."],
                    "group_size": "Teacher demonstration",
                    "class_size_note": "Ideal teacher demo for any class size.",
                },
                {
                    "title": "Testing for Starch in Foods",
                    "topic": "food_tests",
                    "materials": ["Iodine solution", "Small food samples (rice, beans, cassava, banana, sugar, oil)", "White plate", "Dropper"],
                    "procedure": [
                        "Place a small piece of each food on a white plate.",
                        "Add 1-2 drops of iodine solution to each sample.",
                        "Observe and record colour changes.",
                        "Compare results across different food types.",
                    ],
                    "expected_result": "Starch-containing foods turn blue-black. Foods without starch show yellow-brown iodine colour.",
                    "safety": ["Iodine stains skin and clothes. Handle carefully.", "Do not consume iodine or tested food."],
                    "group_size": "3-4 students per group",
                    "class_size_note": "Small samples needed. One bottle of iodine serves many groups.",
                },
            ],
            "physics": [
                {
                    "title": "Simple Pendulum",
                    "topic": "simple_harmonic_motion",
                    "materials": ["String or thread", "Small weight (stone, nut, or washer)", "Stopwatch or watch", "Ruler", "Stand or hook"],
                    "procedure": [
                        "Tie the weight to one end of the string.",
                        "Hang the pendulum from a fixed point.",
                        "Measure the length of the string.",
                        "Displace the weight slightly and release.",
                        "Time 10 complete swings (oscillations).",
                        "Repeat with different string lengths.",
                        "Record and compare the periods.",
                    ],
                    "expected_result": "Period increases with string length. Period is independent of mass.",
                    "safety": ["Ensure the weight is securely tied.", "Keep clear of swinging weight."],
                    "group_size": "2-3 students per group",
                    "class_size_note": "Easy to set up multiple stations. Very low cost.",
                },
                {
                    "title": "Electrostatic Attraction",
                    "topic": "static_electricity",
                    "materials": ["Balloon or plastic comb", "Small pieces of paper", "Wool cloth or hair", "Water tap (optional)"],
                    "procedure": [
                        "Inflate the balloon and tie it.",
                        "Rub the balloon vigorously against wool cloth or hair for 30 seconds.",
                        "Hold the balloon near small paper pieces and observe attraction.",
                        "Hold the balloon near a thin stream of water from a tap.",
                        "Try with a plastic comb rubbed on hair as well.",
                    ],
                    "expected_result": "Charged balloon/comb attracts paper and bends water stream, demonstrating static electricity.",
                    "safety": ["No significant hazards. Ensure balloon does not pop near faces."],
                    "group_size": "Pairs",
                    "class_size_note": "Each pair needs one balloon. Very scalable.",
                },
                {
                    "title": "Refraction in Water",
                    "topic": "refraction",
                    "materials": ["Clear glass or container", "Water", "Pencil or straw", "Coin", "Paper with arrow drawn"],
                    "procedure": [
                        "Half-fill a glass with water.",
                        "Place a pencil in the water at an angle. Observe from the side.",
                        "Place a coin at the bottom of an empty container. Step back until you cannot see it.",
                        "Have a friend slowly pour water in while you watch.",
                        "Observe the coin becoming visible as water is added.",
                    ],
                    "expected_result": "Pencil appears bent at the water surface. Coin becomes visible due to light bending (refraction).",
                    "safety": ["Handle glass carefully.", "Mop up any spills immediately."],
                    "group_size": "Pairs",
                    "class_size_note": "Each pair needs one glass of water. Very scalable.",
                },
            ],
        }

        subject_experiments = experiments.get(subject, experiments.get("biology", []))
        for exp in subject_experiments:
            if topic.lower() in exp.get("topic", "").lower() or topic.lower() in exp.get("title", "").lower():
                return exp

        if subject_experiments:
            return subject_experiments[0]

        return {
            "title": f"Observation Experiment: {topic}",
            "topic": topic,
            "materials": ["Notebook", "Pencil", "Objects from the environment related to the topic"],
            "procedure": [
                "Identify objects or phenomena related to the topic in the local environment.",
                "Record detailed observations in your notebook.",
                "Draw diagrams of what you observe.",
                "Formulate questions based on your observations.",
            ],
            "expected_result": "Students develop observation skills and ask scientific questions.",
            "safety": ["Ensure safe environment for exploration."],
            "group_size": "3-4 students",
            "class_size_note": "Works for any class size.",
        }

    def get_math_activity(self, topic: str, grade: str) -> Dict[str, Any]:
        """Get a hands-on mathematics activity.

        Args:
            topic: Math topic (e.g., fractions, geometry, algebra).
            grade: Grade level.

        Returns:
            Activity description with materials and instructions.
        """
        activities: Dict[str, List[Dict[str, Any]]] = {
            "fractions": [
                {
                    "title": "Paper Folding Fractions",
                    "materials": ["Paper (scrap or old newspapers)", "Pencil", "Ruler"],
                    "instructions": [
                        "Give each student a rectangular piece of paper.",
                        "Fold in half to demonstrate 1/2. Unfold and shade one half.",
                        "Fold in half again to demonstrate 1/4.",
                        "Continue folding to show 1/8.",
                        "Compare fractions by overlaying different folds.",
                    ],
                    "learning_outcome": "Visual understanding of equivalent fractions and fraction comparison.",
                },
                {
                    "title": "Sharing Mangoes - Division Fractions",
                    "materials": ["Stones or seeds as counters", "Paper circles drawn on board"],
                    "instructions": [
                        "Present scenario: 4 mangoes shared among 3 children.",
                        "Use stones to represent mangoes.",
                        "Demonstrate division: each child gets 1 whole mango, then 1/3 of the last.",
                        "Generalise to other sharing problems.",
                    ],
                    "learning_outcome": "Understanding fractions as division and sharing.",
                },
            ],
            "geometry": [
                {
                    "title": "Shape Hunt Around the School",
                    "materials": ["Notebook", "Pencil"],
                    "instructions": [
                        "Students walk around the school compound in groups.",
                        "Identify and list real-world examples of geometric shapes.",
                        "Draw at least 5 different shapes found.",
                        "Classify shapes by properties (number of sides, angles).",
                    ],
                    "learning_outcome": "Recognition of geometric shapes in real-world contexts.",
                },
                {
                    "title": "Constructing Angles with String",
                    "materials": ["String or rope", "Two sticks", "Chalk or stick for marking ground"],
                    "instructions": [
                        "Tie a string between two sticks stuck in the ground.",
                        "Use a third stick and string to create different angles.",
                        "Mark acute, right, obtuse, and straight angles.",
                        "Measure approximate angles using a paper protractor.",
                    ],
                    "learning_outcome": "Understanding angle types and construction.",
                },
            ],
            "algebra": [
                {
                    "title": "Balance Scale Algebra",
                    "materials": ["Two identical containers", "Stones or seeds", "A stick for balance"],
                    "instructions": [
                        "Set up a simple balance using a stick on a fulcrum.",
                        "Put an unknown number of stones in a closed container on one side.",
                        "Add known numbers of stones to balance.",
                        "Relate to algebraic equations: x + 3 = 7.",
                        "Solve by removing equal amounts from both sides.",
                    ],
                    "learning_outcome": "Concrete understanding of solving linear equations.",
                },
            ],
            "measurement": [
                {
                    "title": "Measuring the School Compound",
                    "materials": ["Measuring tape or marked rope", "Notebook", "Pencil"],
                    "instructions": [
                        "Students work in groups to measure different parts of the school.",
                        "Measure the classroom length and width.",
                        "Measure the distance between two trees.",
                        "Convert between metres and centimetres.",
                        "Calculate area of rectangular spaces.",
                    ],
                    "learning_outcome": "Practical measurement skills and unit conversion.",
                },
            ],
            "statistics": [
                {
                    "title": "Class Census Data Collection",
                    "materials": ["Notebook", "Pencil", "Chalkboard for class tally"],
                    "instructions": [
                        "Choose a topic: favourite food, transport to school, family size.",
                        "Each student contributes their data.",
                        "Create a tally chart on the chalkboard.",
                        "Convert tally to frequency table.",
                        "Draw a bar chart or pictogram on the board.",
                        "Calculate mean, median, and mode.",
                    ],
                    "learning_outcome": "Data collection, representation, and basic statistical measures.",
                },
            ],
        }

        topic_activities = activities.get(topic.lower(), [{
            "title": f"Exploring {topic.title()}",
            "materials": ["Notebook", "Pencil", "Local counting materials"],
            "instructions": [
                f"Introduce the concept of {topic} using real-world examples.",
                "Have students work through guided examples on the chalkboard.",
                "Provide practice problems of increasing difficulty.",
                "Have students create their own problems for peers to solve.",
            ],
            "learning_outcome": f"Understanding and application of {topic}.",
        }])

        result = random.choice(topic_activities)
        result["topic"] = topic
        result["grade"] = grade
        result["class_size_note"] = "Designed for large classes (40-80 students)"
        return result

    def get_ict_activity(self, skill_level: str) -> Dict[str, Any]:
        """Get an ICT lesson that works with or without computers.

        Args:
            skill_level: 'beginner', 'intermediate', or 'advanced'.

        Returns:
            ICT activity with both tech and no-tech alternatives.
        """
        activities: Dict[str, List[Dict[str, Any]]] = {
            "beginner": [
                {
                    "title": "Parts of a Computer",
                    "with_computer": [
                        "Show students a real computer or laptop.",
                        "Point out and name each part: monitor, keyboard, mouse, CPU.",
                        "Let each student touch and identify parts.",
                        "Students draw and label a computer diagram.",
                    ],
                    "without_computer": [
                        "Draw a computer diagram on the chalkboard.",
                        "Use the paper keyboard template for students to practice finger placement.",
                        "Have students create a 3D model using cardboard boxes.",
                        "Label each part and describe its function.",
                    ],
                    "assessment": "Students label a blank computer diagram correctly.",
                },
                {
                    "title": "Typing Practice",
                    "with_computer": [
                        "Open a word processor.",
                        "Students type their name and a simple sentence.",
                        "Practice correct finger placement on the keyboard.",
                        "Save the document to a folder.",
                    ],
                    "without_computer": [
                        "Use paper keyboard templates.",
                        "Practice finger placement and key locations.",
                        "Teacher calls out letters; students 'type' on paper keyboard.",
                        "Timed drills: how many letters can you 'type' in 1 minute?",
                    ],
                    "assessment": "Students demonstrate correct finger placement and can locate common keys.",
                },
            ],
            "intermediate": [
                {
                    "title": "Creating a Document with Formatting",
                    "with_computer": [
                        "Open a word processor.",
                        "Type a paragraph about a local topic.",
                        "Apply formatting: bold, italic, underline, different fonts.",
                        "Insert a simple table.",
                        "Save and print the document.",
                    ],
                    "without_computer": [
                        "Draw a formatted document layout on the chalkboard.",
                        "Students recreate the layout on paper using different colours.",
                        "Practice drawing tables with rulers.",
                        "Discuss when to use bold, italics, and underlining.",
                    ],
                    "assessment": "Students produce a neatly formatted handwritten document.",
                },
            ],
            "advanced": [
                {
                    "title": "Introduction to Programming with Python",
                    "with_computer": [
                        "Install Python (or use online interpreter).",
                        "Write a simple 'Hello, World!' program.",
                        "Create variables and print statements.",
                        "Write a program that asks for user input and responds.",
                        "Introduce loops: print numbers 1 to 10.",
                    ],
                    "without_computer": [
                        "Introduce programming concepts using 'unplugged' activities.",
                        "Activity: Students write step-by-step instructions for making tea.",
                        "Discuss algorithms, sequences, and debugging.",
                        "Use flowcharts drawn on the board to represent programs.",
                        "Have students trace through a simple program on paper.",
                    ],
                    "assessment": "Students write a simple algorithm in pseudocode.",
                },
            ],
        }

        level_activities = activities.get(skill_level, activities["beginner"])
        result = random.choice(level_activities)
        result["skill_level"] = skill_level
        result["note"] = "Each activity includes both 'with computer' and 'without computer' options."
        return result

    def get_practical_project(self, subject: str, grade: str) -> Dict[str, Any]:
        """Get a term-length practical project for a subject.

        Args:
            subject: Subject key.
            grade: Grade level.

        Returns:
            Project brief with timeline, deliverables, and assessment criteria.
        """
        projects: Dict[str, List[Dict[str, Any]]] = {
            "agriculture": [
                {
                    "title": "School Garden Project",
                    "duration": "One term (10-12 weeks)",
                    "description": "Students plan, plant, maintain, and harvest a crop in the school garden.",
                    "stages": [
                        {"week": "1-2", "task": "Site selection, soil testing, crop selection"},
                        {"week": "3-4", "task": "Land preparation, planting"},
                        {"week": "5-8", "task": "Daily maintenance (watering, weeding, pest control)"},
                        {"week": "9-10", "task": "Harvesting and yield measurement"},
                        {"week": "11-12", "task": "Report writing and presentation"},
                    ],
                    "deliverables": ["Garden plot", "Daily maintenance log", "Final report", "Presentation"],
                    "assessment_criteria": {
                        "planning": "Clear plan with appropriate crop selection (20%)",
                        "execution": "Quality of garden maintenance (40%)",
                        "record_keeping": "Complete and accurate log book (20%)",
                        "presentation": "Clear oral and written presentation (20%)",
                    },
                },
            ],
            "biology": [
                {
                    "title": "Ecosystem Study of the School Compound",
                    "duration": "One term (10-12 weeks)",
                    "description": "Students identify and study the ecosystem within the school environment.",
                    "stages": [
                        {"week": "1-2", "task": "Identify study area and list observed organisms"},
                        {"week": "3-5", "task": "Weekly observations and data collection"},
                        {"week": "6-8", "task": "Draw food chains and food webs"},
                        {"week": "9-10", "task": "Analyse human impact on the ecosystem"},
                        {"week": "11-12", "task": "Compile report and recommendations"},
                    ],
                    "deliverables": ["Species inventory", "Food web diagram", "Field notes", "Final report"],
                    "assessment_criteria": {
                        "observation": "Thoroughness of observations (30%)",
                        "classification": "Correct identification and classification (25%)",
                        "analysis": "Quality of food web and analysis (25%)",
                        "presentation": "Report organisation and clarity (20%)",
                    },
                },
            ],
            "chemistry": [
                {
                    "title": "Water Quality Testing in the Local Area",
                    "duration": "One term (10-12 weeks)",
                    "description": "Students collect and test water samples from different local sources.",
                    "stages": [
                        {"week": "1-2", "task": "Identify water sources and plan sampling"},
                        {"week": "3-4", "task": "Collect samples and observe physical properties"},
                        {"week": "5-7", "task": "Perform simple chemical tests (pH, hardness, etc.)"},
                        {"week": "8-9", "task": "Compare results across sources"},
                        {"week": "10-12", "task": "Write report with recommendations"},
                    ],
                    "deliverables": ["Sample collection log", "Test results table", "Comparison chart", "Report"],
                    "assessment_criteria": {
                        "methodology": "Appropriate sampling and testing methods (30%)",
                        "accuracy": "Careful and accurate test results (30%)",
                        "analysis": "Meaningful comparison and conclusions (25%)",
                        "recommendations": "Practical and relevant recommendations (15%)",
                    },
                },
            ],
            "physics": [
                {
                    "title": "Building a Solar Oven",
                    "duration": "One term (10-12 weeks)",
                    "description": "Students design and build a solar oven using local materials.",
                    "stages": [
                        {"week": "1-2", "task": "Research solar energy and oven designs"},
                        {"week": "3-4", "task": "Design the solar oven on paper"},
                        {"week": "5-7", "task": "Build the solar oven using cardboard, foil, and plastic"},
                        {"week": "8-9", "task": "Test by heating water and recording temperatures"},
                        {"week": "10-12", "task": "Optimise design and present results"},
                    ],
                    "deliverables": ["Design sketch", "Working solar oven", "Temperature data log", "Presentation"],
                    "assessment_criteria": {
                        "design": "Clear and practical design (25%)",
                        "construction": "Quality and durability of build (25%)",
                        "testing": "Systematic testing and data collection (25%)",
                        "presentation": "Clear explanation of principles and results (25%)",
                    },
                },
            ],
            "mathematics": [
                {
                    "title": "School Budget Mathematics",
                    "duration": "One term (10-12 weeks)",
                    "description": "Students create a mock budget for a school or family.",
                    "stages": [
                        {"week": "1-2", "task": "Identify income and expense categories"},
                        {"week": "3-5", "task": "Collect and record actual or estimated data"},
                        {"week": "6-7", "task": "Calculate percentages and ratios"},
                        {"week": "8-9", "task": "Create charts and graphs of the budget"},
                        {"week": "10-12", "task": "Present findings and savings recommendations"},
                    ],
                    "deliverables": ["Budget spreadsheet or table", "Charts/graphs", "Analysis report", "Presentation"],
                    "assessment_criteria": {
                        "data_collection": "Complete and realistic data (25%)",
                        "calculations": "Accurate mathematical working (30%)",
                        "presentation": "Clear charts and visual presentation (25%)",
                        "recommendations": "Practical savings suggestions (20%)",
                    },
                },
            ],
        }

        subject_projects = projects.get(subject, [{
            "title": f"Research Project on {subject.title()}",
            "duration": "One term (10-12 weeks)",
            "description": f"Students research a topic in {subject} and present findings.",
            "stages": [
                {"week": "1-2", "task": "Topic selection and research planning"},
                {"week": "3-7", "task": "Research and data collection"},
                {"week": "8-10", "task": "Analysis and report writing"},
                {"week": "11-12", "task": "Presentation to class"},
            ],
            "deliverables": ["Research notes", "Written report", "Oral presentation"],
            "assessment_criteria": {
                "research": "Thoroughness of research (30%)",
                "analysis": "Quality of analysis (30%)",
                "presentation": "Clarity of written and oral presentation (40%)",
            },
        }])

        result = random.choice(subject_projects)
        result["subject"] = subject
        result["grade"] = grade
        result["group_size"] = "3-5 students per group"
        result["class_size_note"] = "Groups work well for 40-80 students (8-16 groups)"
        return result



# ──────────────────────────────────────────────────────────────────────────
# MULTILINGUAL SUPPORT
# ──────────────────────────────────────────────────────────────────────────

class MultilingualSupport:
    """Provides multilingual support for teaching in African languages.

    Includes subject vocabulary, bilingual lesson templates, and
    culturally relevant translations for major African languages.
    """

    def __init__(self) -> None:
        logger.info("MultilingualSupport initialized")

    def get_subject_vocabulary(self, subject: str, language: str) -> Dict[str, Any]:
        """Get key subject vocabulary translated into a local language.

        Args:
            subject: Subject key.
            language: Language key from LANGUAGES dict.

        Returns:
            Vocabulary list with English term, local translation, and
            pronunciation guide where available.
        """
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported language '{language}'. Valid: {list(LANGUAGES.keys())}")

        vocabularies: Dict[str, Dict[str, Dict[str, List[Dict[str, str]]]]] = {
            "swahili": {
                "mathematics": [
                    {"english": "Addition", "translation": "Kujumlisha", "pronunciation": "koo-joom-LEE-sha"},
                    {"english": "Subtraction", "translation": "Kutoa", "pronunciation": "koo-TOH-ah"},
                    {"english": "Multiplication", "translation": "Kuzidisha", "pronunciation": "koo-zee-DEE-sha"},
                    {"english": "Division", "translation": "Kugawanya", "pronunciation": "koo-gah-WAHN-yah"},
                    {"english": "Fraction", "translation": "Sehemu", "pronunciation": "seh-HEH-moo"},
                    {"english": "Number", "translation": "Nambari", "pronunciation": "nahm-BAH-ree"},
                    {"english": "Equation", "translation": "Mlinganyo", "pronunciation": "mleen-GAHN-yoh"},
                    {"english": "Geometry", "translation": "Jiometri", "pronunciation": "jee-oh-MEH-tree"},
                ],
                "science": [
                    {"english": "Experiment", "translation": "Jaribio", "pronunciation": "jah-REE-bee-oh"},
                    {"english": "Plant", "translation": "Mmea", "pronunciation": "mMEH-ah"},
                    {"english": "Water", "translation": "Maji", "pronunciation": "MAH-jee"},
                    {"english": "Animal", "translation": "Mnyama", "pronunciation": "mnyah-MAH"},
                    {"english": "Soil", "translation": "Udongo", "pronunciation": "oo-DOHN-goh"},
                    {"english": "Energy", "translation": "Nishati", "pronunciation": "nee-SHAH-tee"},
                    {"english": "Force", "translation": "Nguvu", "pronunciation": "nGOO-voo"},
                    {"english": "Light", "translation": "Nuru", "pronunciation": "NOO-roo"},
                ],
                "english": [
                    {"english": "Reading", "translation": "Kusoma", "pronunciation": "koo-SOH-mah"},
                    {"english": "Writing", "translation": "Kuandika", "pronunciation": "kwahn-DEE-kah"},
                    {"english": "Sentence", "translation": "Sentensi", "pronunciation": "sen-TEN-see"},
                    {"english": "Word", "translation": "Neno", "pronunciation": "NEH-noh"},
                    {"english": "Story", "translation": "Hadithi", "pronunciation": "hah-DEE-thee"},
                    {"english": "Question", "translation": "Swali", "pronunciation": "SWAH-lee"},
                    {"english": "Answer", "translation": "Jibu", "pronunciation": "JEE-boo"},
                    {"english": "Book", "translation": "Kitabu", "pronunciation": "kee-TAH-boo"},
                ],
            },
            "yoruba": {
                "mathematics": [
                    {"english": "Addition", "translation": "Ìsọdipúpò", "pronunciation": "ee-soh-dee-POO-poh"},
                    {"english": "Subtraction", "translation": "Ìyókò", "pronunciation": "ee-yoh-KOH"},
                    {"english": "Number", "translation": "Nọ́mbà", "pronunciation": "NOHM-bah"},
                    {"english": "Fraction", "translation": "Àáyè", "pronunciation": "ah-AH-yeh"},
                    {"english": "Multiply", "translation": "Ìsọdipúpò púpò", "pronunciation": "ee-soh-dee-POO-poh POO-poh"},
                    {"english": "Divide", "translation": "Pínlò", "pronunciation": "peen-LOH"},
                    {"english": "Geometry", "translation": "Ìmọ̀ ọnà", "pronunciation": "ee-moh oh-NAH"},
                    {"english": "Circle", "translation": "Ìróyìn", "pronunciation": "ee-roh-yeen"},
                ],
                "science": [
                    {"english": "Plant", "translation": "Ògì", "pronunciation": "oh-gee"},
                    {"english": "Water", "translation": "Omi", "pronunciation": "OH-mee"},
                    {"english": "Fire", "translation": "Iná", "pronunciation": "ee-NAH"},
                    {"english": "Earth", "translation": "Ilẹ̀", "pronunciation": "ee-LEH"},
                    {"english": "Air", "translation": "Fẹ́fẹ́", "pronunciation": "feh-FEH"},
                    {"english": "Animal", "translation": "Ẹranko", "pronunciation": "eh-RAHN-koh"},
                    {"english": "Sun", "translation": "Òòrùn", "pronunciation": "oh-oh-ROON"},
                    {"english": "Moon", "translation": "Òṣùpá", "pronunciation": "oh-shoo-PAH"},
                ],
            },
            "igbo": {
                "mathematics": [
                    {"english": "Addition", "translation": "Mgbakwunye", "pronunciation": "mm-gbah-KWOON-yeh"},
                    {"english": "Subtraction", "translation": "Nwepu", "pronunciation": "nWEH-poo"},
                    {"english": "Number", "translation": "Nọ́mbà", "pronunciation": "NOHM-bah"},
                    {"english": "Count", "translation": "Gụọ", "pronunciation": "goo-woh"},
                    {"english": "Multiply", "translation": "Ịgba-ụzọ", "pronunciation": "ee-gbah-oo-zoh"},
                    {"english": "Fraction", "translation": "Akụkẹrẹ", "pronunciation": "ah-koo-KEH-reh"},
                ],
                "science": [
                    {"english": "Plant", "translation": "Osisi", "pronunciation": "oh-SEE-see"},
                    {"english": "Water", "translation": "Mmiri", "pronunciation": "mm-MEE-ree"},
                    {"english": "Sun", "translation": "Anyanwu", "pronunciation": "ahn-YAHN-woo"},
                    {"english": "Moon", "translation": "Ọnwa", "pronunciation": "OHN-wah"},
                    {"english": "Star", "translation": "Kpakpando", "pronunciation": "kpah-kpahn-doh"},
                ],
            },
            "hausa": {
                "mathematics": [
                    {"english": "Addition", "translation": "Kara", "pronunciation": "KAH-rah"},
                    {"english": "Subtraction", "translation": "Rage", "pronunciation": "RAH-geh"},
                    {"english": "Number", "translation": "Lamba", "pronunciation": "LAHM-bah"},
                    {"english": "Multiply", "translation": "Zarba", "pronunciation": "ZAHR-bah"},
                    {"english": "Divide", "translation": "Raba", "pronunciation": "RAH-bah"},
                    {"english": "Fraction", "translation": "Kashi", "pronunciation": "KAH-shee"},
                ],
                "science": [
                    {"english": "Water", "translation": "Ruwa", "pronunciation": "ROO-wah"},
                    {"english": "Fire", "translation": "Wuta", "pronunciation": "WOO-tah"},
                    {"english": "Earth", "translation": "Kasa", "pronunciation": "KAH-sah"},
                    {"english": "Plant", "translation": "Shuka", "pronunciation": "SHOO-kah"},
                    {"english": "Animal", "translation": "Dabba", "pronunciation": "DAH-bah"},
                ],
            },
            "zulu": {
                "mathematics": [
                    {"english": "Addition", "translation": "Ukwengeza", "pronunciation": "ook-wen-GEH-zah"},
                    {"english": "Subtraction", "translation": "Ukuhluthisa", "pronunciation": "oo-koo-loo-TEE-sah"},
                    {"english": "Number", "translation": "Inombolo", "pronunciation": "ee-nohm-BOH-loh"},
                    {"english": "Multiply", "translation": "Phindaphinda", "pronunciation": "peen-dah-PEEN-dah"},
                    {"english": "Fraction", "translation": "Ingxenye", "pronunciation": "een-GEH-nyeh"},
                ],
                "science": [
                    {"english": "Water", "translation": "Amanzi", "pronunciation": "ah-MAHN-zee"},
                    {"english": "Sun", "translation": "Ilanga", "pronunciation": "ee-LAHN-gah"},
                    {"english": "Plant", "translation": "Isitshalo", "pronunciation": "ee-seet-SHAH-loh"},
                    {"english": "Animal", "translation": "Isilwane", "pronunciation": "ee-seel-WAH-neh"},
                ],
            },
            "xhosa": {
                "mathematics": [
                    {"english": "Addition", "translation": "Ukudibanisa", "pronunciation": "oo-koo-dee-bah-NEE-sah"},
                    {"english": "Number", "translation": "Inani", "pronunciation": "ee-NAH-nee"},
                    {"english": "Count", "translation": "Bala", "pronunciation": "BAH-lah"},
                    {"english": "Fraction", "translation": "Isiqhekeza", "pronunciation": "ee-see-keh-KEH-zah"},
                ],
                "science": [
                    {"english": "Water", "translation": "Amanzi", "pronunciation": "ah-MAHN-zee"},
                    {"english": "Sun", "translation": "Ilanga", "pronunciation": "ee-LAHN-gah"},
                    {"english": "Plant", "translation": "Isityalo", "pronunciation": "ee-see-TYAH-loh"},
                ],
            },
            "amharic": {
                "mathematics": [
                    {"english": "Addition", "translation": "መደመር (medamer)", "pronunciation": "meh-dah-MEHR"},
                    {"english": "Number", "translation": "ቁጥር (kutir)", "pronunciation": "koo-TEER"},
                    {"english": "Count", "translation": "መቁጠር (mekutere)", "pronunciation": "meh-koo-teh-REHR"},
                ],
                "science": [
                    {"english": "Water", "translation": "ውሃ (waha)", "pronunciation": "wah-HAH"},
                    {"english": "Sun", "translation": "ፀሐይ (tsehay)", "pronunciation": "tseh-HIGH"},
                    {"english": "Plant", "translation": "ገነት (genet)", "pronunciation": "geh-NEHT"},
                ],
            },
            "luganda": {
                "mathematics": [
                    {"english": "Addition", "translation": "Okugattika", "pronunciation": "oh-koo-gah-tee-kah"},
                    {"english": "Number", "translation": "Ennamba", "pronunciation": "ehn-NAHM-bah"},
                    {"english": "Count", "translation": "Okubala", "pronunciation": "oh-koo-BAH-lah"},
                ],
                "science": [
                    {"english": "Water", "translation": "Amazzi", "pronunciation": "ah-MAH-zee"},
                    {"english": "Sun", "translation": "Enjuba", "pronunciation": "ehn-JOO-bah"},
                    {"english": "Plant", "translation": "Ekimera", "pronunciation": "eh-kee-MEH-rah"},
                ],
            },
            "wolof": {
                "mathematics": [
                    {"english": "Addition", "translation": "Bokk", "pronunciation": "bohk"},
                    {"english": "Number", "translation": "Nomb", "pronunciation": "nohmb"},
                    {"english": "Count", "translation": "Bay", "pronunciation": "buy"},
                ],
                "science": [
                    {"english": "Water", "translation": "Ndox", "pronunciation": "ndoh"},
                    {"english": "Sun", "translation": "Jant", "pronunciation": "jahnt"},
                    {"english": "Plant", "translation": "Gax", "pronunciation": "gah"},
                ],
            },
            "shona": {
                "mathematics": [
                    {"english": "Addition", "translation": "Kuwedzera", "pronunciation": "koo-weh-DEH-rah"},
                    {"english": "Number", "translation": "Nhamba", "pronunciation": "NAHM-bah"},
                    {"english": "Count", "translation": "Kuverenga", "pronunciation": "koo-veh-REHN-gah"},
                ],
                "science": [
                    {"english": "Water", "translation": "Mvura", "pronunciation": "mm-VOO-rah"},
                    {"english": "Sun", "translation": "Zuva", "pronunciation": "ZOO-vah"},
                    {"english": "Plant", "translation": "Chikamu", "pronunciation": "chee-KAH-moo"},
                ],
            },
        }

        language_data = LANGUAGES[language]
        subject_vocab = vocabularies.get(language, {}).get(subject, [
            {"english": "Subject", "translation": f"[{language} word for subject]", "pronunciation": "N/A"},
            {"english": "Learn", "translation": f"[{language} word for learn]", "pronunciation": "N/A"},
            {"english": "Teach", "translation": f"[{language} word for teach]", "pronunciation": "N/A"},
        ])

        return {
            "language": language,
            "language_name": language_data["name"],
            "subject": subject,
            "subject_name": SUBJECTS.get(subject, {}).get("name", subject),
            "vocabulary": subject_vocab,
            "general_phrases": [
                {"english": "Good morning", "translation": language_data["greeting"]},
                {"english": "Thank you", "translation": language_data["thank_you"]},
                {"english": "Please repeat", "translation": "[Teacher gesture + local phrase]"},
                {"english": "I understand", "translation": "[Local acknowledgment phrase]"},
            ],
            "note": f"Vocabulary for {language_data['name']} in {subject}. Pronunciation is approximate.",
        }

    def get_bilingual_lesson(
        self,
        subject: str,
        topic: str,
        primary_lang: str = "english",
        secondary_lang: str = "swahili",
    ) -> Dict[str, Any]:
        """Generate a bilingual lesson plan template.

        Args:
            subject: Subject key.
            topic: Topic to cover.
            primary_lang: Primary language of instruction.
            secondary_lang: Secondary language for reinforcement.

        Returns:
            Bilingual lesson plan with translations for key terms and
            instructions in both languages.
        """
        if primary_lang not in LANGUAGES and primary_lang != "english":
            raise ValueError(f"Unsupported primary language: {primary_lang}")
        if secondary_lang not in LANGUAGES:
            raise ValueError(f"Unsupported secondary language: {secondary_lang}")

        primary_name = "English" if primary_lang == "english" else LANGUAGES[primary_lang]["name"]
        secondary_name = LANGUAGES[secondary_lang]["name"]

        vocabulary = self.get_subject_vocabulary(subject, secondary_lang)
        key_terms = vocabulary.get("vocabulary", [])[:5]

        bilingual_lesson: Dict[str, Any] = {
            "subject": SUBJECTS.get(subject, {}).get("name", subject),
            "topic": topic,
            "primary_language": primary_name,
            "secondary_language": secondary_name,
            "lesson_structure": {
                "introduction": {
                    "primary": f"Welcome the class. Introduce today's topic: {topic}.",
                    "secondary": f"Use {secondary_name} greeting. Introduce key terms.",
                    "bilingual_approach": f"Begin in {primary_name}. Introduce {secondary_name} terms for key vocabulary. Write both on the board.",
                },
                "key_terms": [
                    {
                        "english": term["english"],
                        "translation": term["translation"],
                        "pronunciation": term.get("pronunciation", ""),
                    }
                    for term in key_terms
                ],
                "main_activity": {
                    "primary": f"Explain the concept of {topic} in {primary_name}.",
                    "secondary": f"Reinforce using {secondary_name} explanations and examples.",
                    "bilingual_approach": f"Teach primarily in {primary_name}. Pause to translate difficult concepts into {secondary_name}. Use visual aids that work in both languages.",
                },
                "practice": {
                    "primary": "Students complete exercises in their preferred language.",
                    "secondary": f"Encourage stronger students to explain to peers in {secondary_name}.",
                },
                "assessment": {
                    "primary": f"Assess understanding in {primary_name}.",
                    "secondary": f"Accept responses in {secondary_name} where the concept is correctly demonstrated.",
                },
            },
            "teaching_tips": [
                f"Write all key terms on the board in both {primary_name} and {secondary_name}.",
                f"Use visuals and gestures to bridge language gaps.",
                f"Allow students to respond in either language during oral questions.",
                f"Create a bilingual word wall in the classroom.",
                f"Pair students with different language strengths together.",
                "Use songs, rhymes, or proverbs in the secondary language to reinforce concepts.",
            ],
            "created_at": datetime.datetime.now().isoformat(),
        }

        logger.info("Bilingual lesson created: %s in %s + %s", topic, primary_name, secondary_name)
        return bilingual_lesson



# ──────────────────────────────────────────────────────────────────────────
# SPECIAL NEEDS SUPPORT
# ──────────────────────────────────────────────────────────────────────────

class SpecialNeeds:
    """Provides inclusion strategies and differentiated activities.

    Offers practical guidance for adapting teaching to support students
    with various disabilities and learning differences in low-resource
    African classrooms.

    DISCLAIMER: This information is for educational guidance only. Teachers
    should consult qualified special education professionals for individual
    student assessments and intervention plans.
    """

    def __init__(self) -> None:
        logger.info("SpecialNeeds initialized")

    def get_inclusion_strategies(self, condition: str) -> Dict[str, Any]:
        """Get teaching strategies for a specific disability or condition.

        Args:
            condition: Type of disability. Options:
                visual_impairment, hearing_impairment, physical_disability,
                learning_disability, autism, adhd, intellectual_disability,
                speech_impairment, albinism, epilepsy.

        Returns:
            Detailed inclusion strategies for classroom management,
            teaching methods, assessment adaptations, and peer support.

        DISCLAIMER: These strategies are general guidance. Individual students
        may have unique needs. Consult a special education specialist for
        personalised support plans.
        """
        strategies: Dict[str, Dict[str, Any]] = {
            "visual_impairment": {
                "name": "Visual Impairment / Blindness",
                "description": "Strategies for students with limited or no vision.",
                "seating_position": "Front of class, near the board. Ensure good lighting.",
                "teaching_strategies": [
                    "Use verbal descriptions for everything written on the board.",
                    "Allow the student to touch and handle objects during demonstrations.",
                    "Use tactile materials: raised line drawings, textured materials.",
                    "Provide audio recordings of textbooks and notes.",
                    "Pair with a sighted peer who can describe visual content.",
                    "Use large print (18pt+) for all printed materials.",
                    "Write clearly with thick lines on the chalkboard.",
                    "Use high-contrast colours on the board (white chalk on dark board).",
                ],
                "assessment_adaptations": [
                    "Provide exams in Braille or large print format.",
                    "Allow oral responses instead of written answers.",
                    "Allow extra time for reading and writing tasks.",
                    "Use a reader or scribe if available.",
                ],
                "peer_support": [
                    "Assign a consistent peer buddy to describe visual content.",
                    "Encourage group activities where the student can contribute non-visually.",
                ],
                "low_resource_tips": [
                    "Create tactile labels using glue or thread on cardboard.",
                    "Use sandpaper cut into shapes for tactile learning.",
                    "Have students trace letters in sand or clay.",
                    "Use stones or seeds for counting (tactile mathematics).",
                ],
            },
            "hearing_impairment": {
                "name": "Hearing Impairment / Deafness",
                "description": "Strategies for students with limited or no hearing.",
                "seating_position": "Front of class, facing the teacher. Ensure clear sight lines.",
                "teaching_strategies": [
                    "Face the student when speaking. Do not turn your back while explaining.",
                    "Speak clearly and at a moderate pace.",
                    "Use visual aids extensively: diagrams, charts, written notes.",
                    "Write all instructions on the board.",
                    "Use gestures and facial expressions to reinforce meaning.",
                    "Teach key vocabulary in sign language if possible.",
                    "Use group work where peers can repeat or clarify instructions.",
                    "Flash lights to get attention instead of clapping or calling out.",
                ],
                "assessment_adaptations": [
                    "Provide written instructions for all assessments.",
                    "Allow written responses in place of oral assessments.",
                    "Provide extra time to read and understand questions.",
                    "Use visual diagrams in test questions where possible.",
                ],
                "peer_support": [
                    "Seat next to a helpful peer who can repeat instructions.",
                    "Encourage classmates to face the student when speaking.",
                ],
                "low_resource_tips": [
                    "Learn basic sign language for classroom communication.",
                    "Use picture cards for common classroom instructions.",
                    "Write everything on the board - do not rely only on verbal instructions.",
                    "Use hand signals for common requests (bathroom, water, help).",
                ],
            },
            "physical_disability": {
                "name": "Physical Disability",
                "description": "Strategies for students with mobility or motor impairments.",
                "seating_position": "Accessible position near the door and with adequate space.",
                "teaching_strategies": [
                    "Ensure the student can reach the board and materials.",
                    "Modify writing tasks: allow oral responses, shorter written assignments.",
                    "Provide support for physical activities (PE, experiments).",
                    "Assign a peer to assist with movement around the classroom.",
                    "Adapt seating if needed (cushion, modified desk height).",
                    "Plan movement breaks for the whole class to include the student.",
                ],
                "assessment_adaptations": [
                    "Allow extra time for written exams.",
                    "Provide a scribe if the student has difficulty writing.",
                    "Allow oral examinations as an alternative.",
                    "Ensure examination venue is accessible.",
                ],
                "peer_support": [
                    "Assign a buddy to help with physical tasks.",
                    "Include the student in all group activities.",
                ],
                "low_resource_tips": [
                    "Create a comfortable seating arrangement using available cushions.",
                    "Adapt writing tools: wrap pencils with cloth for better grip.",
                    "Use slanted writing surfaces (propped-up board) if helpful.",
                ],
            },
            "learning_disability": {
                "name": "Learning Disability (Dyslexia, Dyscalculia)",
                "description": "Strategies for students with specific learning difficulties.",
                "seating_position": "Near the front, away from distractions.",
                "teaching_strategies": [
                    "Break instructions into small, clear steps.",
                    "Use multi-sensory approaches: see, hear, touch, and move.",
                    "For dyslexia: use coloured overlays, teach phonics explicitly.",
                    "For dyscalculia: use concrete manipulatives (stones, counters).",
                    "Repeat and reinforce concepts frequently.",
                    "Provide extra time for reading and writing tasks.",
                    "Use visual organisers and mind maps.",
                    "Celebrate small achievements to build confidence.",
                ],
                "assessment_adaptations": [
                    "Provide extra time for all assessments.",
                    "Read questions aloud if the student requests.",
                    "Allow oral responses instead of written where appropriate.",
                    "Break long assessments into shorter sections.",
                    "Provide a quiet space for examinations if possible.",
                ],
                "peer_support": [
                    "Pair with a patient, supportive peer for reading activities.",
                    "Use peer tutoring in areas of strength.",
                ],
                "low_resource_tips": [
                    "Use sand trays for practising letter formation.",
                    "Use different coloured chalk for different parts of words or equations.",
                    "Create phonics cards from cardboard.",
                    "Use songs and rhymes to reinforce spelling and multiplication tables.",
                ],
            },
            "autism": {
                "name": "Autism Spectrum Disorder",
                "description": "Strategies for students on the autism spectrum.",
                "seating_position": "Consistent seat, away from noisy areas and bright lights.",
                "teaching_strategies": [
                    "Maintain consistent routines and warn about any changes.",
                    "Use visual schedules showing the day's activities.",
                    "Give clear, literal instructions (avoid idioms and sarcasm).",
                    "Allow breaks when the student becomes overwhelmed.",
                    "Use the student's special interests to engage them in learning.",
                    "Minimise sensory overload: reduce noise, provide quiet spaces.",
                    "Use social stories to teach social skills.",
                    "Be patient with transitions between activities.",
                ],
                "assessment_adaptations": [
                    "Provide a quiet, separate space for exams.",
                    "Allow extra time and breaks during assessments.",
                    "Use clear, unambiguous language in questions.",
                    "Offer choice in how to demonstrate knowledge (oral, written, project).",
                ],
                "peer_support": [
                    "Educate classmates about autism in a positive, inclusive way.",
                    "Assign a calm, understanding peer buddy.",
                ],
                "low_resource_tips": [
                    "Create a visual daily schedule using pictures on cardboard.",
                    "Designate a calm corner in the classroom with a mat or cushion.",
                    "Use consistent hand signals for transitions.",
                    "Create social stories using simple drawings.",
                ],
            },
            "adhd": {
                "name": "Attention Deficit Hyperactivity Disorder",
                "description": "Strategies for students with attention and hyperactivity challenges.",
                "seating_position": "Near the front, away from windows and doors to minimise distractions.",
                "teaching_strategies": [
                    "Break lessons into short segments (10-15 minutes each).",
                    "Use physical movement and hands-on activities frequently.",
                    "Give clear, concise instructions one step at a time.",
                    "Use visual aids and colourful materials to maintain attention.",
                    "Provide fidget tools (eraser, small stone) to channel energy.",
                    "Give frequent positive feedback and encouragement.",
                    "Alternate seated work with active tasks.",
                    "Set clear expectations and consistent consequences.",
                ],
                "assessment_adaptations": [
                    "Break assessments into shorter sections with breaks.",
                    "Allow extra time.",
                    "Provide a quiet, distraction-free space if possible.",
                    "Allow oral responses for students who struggle with written expression.",
                ],
                "peer_support": [
                    "Seat next to a calm, focused peer.",
                    "Include in group work with clear roles.",
                ],
                "low_resource_tips": [
                    "Use movement breaks: stretching, clapping patterns, standing activities.",
                    "Create a simple reward chart using paper and stickers (or stamps).",
                    "Use songs and chants to engage attention.",
                    "Allow the student to stand at their desk if it helps them focus.",
                ],
            },
            "intellectual_disability": {
                "name": "Intellectual Disability",
                "description": "Strategies for students with cognitive impairments.",
                "seating_position": "Near the front, close to the teacher for frequent support.",
                "teaching_strategies": [
                    "Use simple, concrete language. Avoid abstract concepts.",
                    "Break all tasks into very small, manageable steps.",
                    "Use lots of repetition and practice.",
                    "Focus on practical, life-relevant skills.",
                    "Use visual supports: pictures, gestures, demonstrations.",
                    "Provide immediate and specific feedback.",
                    "Set realistic, achievable goals.",
                    "Use role-play and hands-on learning extensively.",
                ],
                "assessment_adaptations": [
                    "Use practical assessments rather than written tests.",
                    "Assess based on individual goals and progress.",
                    "Allow extra time.",
                    "Use oral questioning and observation.",
                ],
                "peer_support": [
                    "Assign a patient, kind peer buddy.",
                    "Include in all class activities with appropriate support.",
                ],
                "low_resource_tips": [
                    "Use real objects for teaching (real money for math, real items for sorting).",
                    "Create picture-based instruction cards.",
                    "Use songs and repetition for memorisation.",
                    "Focus on functional skills: counting money, telling time, reading signs.",
                ],
            },
            "albinism": {
                "name": "Albinism",
                "description": "Strategies for students with albinism (visual sensitivity and skin protection needs).",
                "seating_position": "Away from direct sunlight and bright windows. Shade the desk area.",
                "teaching_strategies": [
                    "Ensure the student is not seated in direct sunlight.",
                    "Use large print materials.",
                    "Write clearly and boldly on the board.",
                    "Allow the student to move closer to the board when needed.",
                    "Provide rest breaks for the eyes.",
                    "Use high-contrast materials (dark print on light background).",
                    "Encourage the student to wear hats indoors if helpful.",
                    "Be aware that the student may have difficulty with outdoor activities in bright sun.",
                ],
                "assessment_adaptations": [
                    "Provide large print exam papers.",
                    "Allow extra time for reading.",
                    "Ensure adequate lighting without glare.",
                    "Allow the student to sit where lighting is optimal.",
                ],
                "peer_support": [
                    "Educate classmates about albinism to prevent stigma and bullying.",
                    "Encourage inclusive attitudes.",
                ],
                "low_resource_tips": [
                    "Create shaded areas in the classroom using cardboard or cloth.",
                    "Use thick chalk for better visibility on the board.",
                    "Enlarge worksheets by copying onto larger paper if possible.",
                    "Seat near a window with a blind or shade that can be drawn.",
                ],
            },
            "epilepsy": {
                "name": "Epilepsy / Seizure Disorder",
                "description": "Strategies for students with epilepsy.",
                "seating_position": "Anywhere, but ensure clear access for first aid if needed.",
                "teaching_strategies": [
                    "Ensure all staff know the student's seizure action plan.",
                    "Avoid flashing lights or rapidly changing visual stimuli.",
                    "Allow rest periods if the student is tired (fatigue can trigger seizures).",
                    "Be aware of any seizure triggers and minimise them.",
                    "Ensure the student stays hydrated, especially in hot weather.",
                    "Do not draw attention to the condition unnecessarily.",
                ],
                "assessment_adaptations": [
                    "Allow extra time if seizures affect concentration.",
                    "Provide a safe, quiet space for recovery if a seizure occurs during an exam.",
                    "Be flexible with deadlines if needed.",
                ],
                "peer_support": [
                    "Teach classmates basic seizure first aid (clear space, do not restrain, place on side).",
                    "Encourage a supportive, non-stigmatising environment.",
                ],
                "low_resource_tips": [
                    "Keep a simple first aid guide visible in the classroom.",
                    "Identify a quiet recovery area in the classroom.",
                    "Ensure the classroom layout allows easy movement.",
                ],
                "seizure_first_aid": [
                    "Stay calm. Note the time the seizure starts.",
                    "Clear the area around the student of dangerous objects.",
                    "Do NOT put anything in the student's mouth.",
                    "Do NOT restrain the student.",
                    "Place something soft under their head.",
                    "Turn the student onto their side after the seizure stops.",
                    "Stay with the student until fully recovered.",
                    "Call for medical help if the seizure lasts more than 5 minutes.",
                ],
            },
        }

        strategy = strategies.get(condition)
        if strategy is None:
            valid = ", ".join(strategies.keys())
            raise ValueError(f"Unknown condition '{condition}'. Valid: {valid}")

        strategy["disclaimer"] = (
            "These strategies are general guidance for inclusive teaching. "
            "Individual students may have unique needs. Consult a qualified "
            "special education professional for personalised assessments and plans."
        )
        return strategy

    def get_differentiated_activity(
        self,
        topic: str,
        ability_levels: List[str],
    ) -> Dict[str, Any]:
        """Generate a multi-level activity for mixed-ability classes.

        Args:
            topic: The topic being taught.
            ability_levels: List of levels to differentiate for.
                Options: beginner, intermediate, advanced.

        Returns:
            Activity plan with tiered tasks for each ability level.
        """
        activities: Dict[str, Dict[str, Any]] = {}

        for level in ability_levels:
            if level == "beginner":
                activities["beginner"] = {
                    "level": "Beginner (Support Needed)",
                    "task": f"Match key terms about {topic} with their definitions.",
                    "activities": [
                        f"Draw and label a simple diagram of {topic}.",
                        f"Complete a fill-in-the-blanks exercise on {topic}.",
                        f"Sort pictures or words related to {topic} into categories.",
                    ],
                    "support": [
                        "Provide vocabulary list with definitions.",
                        "Work with a peer buddy.",
                        "Use visual aids and manipulatives.",
                    ],
                    "assessment": "Can the student correctly match terms and complete the fill-in exercise?",
                }
            elif level == "intermediate":
                activities["intermediate"] = {
                    "level": "Intermediate (On Track)",
                    "task": f"Explain the concept of {topic} and apply it to examples.",
                    "activities": [
                        f"Write a paragraph explaining {topic} in your own words.",
                        f"Solve problems related to {topic} using standard methods.",
                        f"Create a concept map showing the main ideas of {topic}.",
                    ],
                    "support": [
                        "Provide structured worksheets with guided questions.",
                        "Encourage independent work with teacher check-ins.",
                    ],
                    "assessment": "Can the student explain the concept clearly and solve standard problems?",
                }
            elif level == "advanced":
                activities["advanced"] = {
                    "level": "Advanced (Extension)",
                    "task": f"Analyse, evaluate, and create new applications of {topic}.",
                    "activities": [
                        f"Design an experiment or project to investigate an aspect of {topic}.",
                        f"Compare and contrast different approaches to {topic}.",
                        f"Teach the concept of {topic} to a peer who is struggling.",
                        f"Create a presentation or poster about {topic} for the class.",
                    ],
                    "support": [
                        "Provide open-ended, challenging problems.",
                        "Encourage independent research using available resources.",
                        "Assign leadership roles in group activities.",
                    ],
                    "assessment": "Can the student demonstrate deep understanding and creative application?",
                }

        return {
            "topic": topic,
            "differentiated_activities": activities,
            "implementation_tips": [
                "Assign students to ability groups flexibly - students may be advanced in one topic and beginner in another.",
                "Use the same core concept for all levels to maintain class unity.",
                "Rotate group membership regularly to avoid labelling.",
                "For large classes (40+): assign group leaders from advanced students to help manage.",
                "All students should come together for a whole-class summary at the end.",
            ],
            "classroom_management": {
                "grouping": "Mixed-ability groups of 4-6 work best for peer support.",
                "materials": "Prepare 3 versions of worksheets (colour-coded or labelled A, B, C).",
                "time": "Begin with whole-class instruction, then split into level groups.",
                "large_class_tip": "For 60+ students, have advanced students serve as assistant teachers for beginner groups.",
            },
        }


# ──────────────────────────────────────────────────────────────────────────
# READING MATERIAL
# ──────────────────────────────────────────────────────────────────────────

class ReadingMaterial:
    """Generates reading passages, comprehension questions, and moral stories.

    Provides culturally relevant reading materials for African students,
    with comprehension questions aligned to grade level.
    """

    def __init__(self) -> None:
        logger.info("ReadingMaterial initialized")

    def get_reading_passage(self, grade: str, topic: str) -> Dict[str, Any]:
        """Get a reading comprehension passage appropriate for the grade level.

        Args:
            grade: Grade level.
            topic: Topic or theme of the passage.

        Returns:
            Reading passage with title, text, word count, and difficulty info.
        """
        passages: Dict[str, List[Dict[str, Any]]] = {
            "primary_1": [
                {
                    "title": "The Goat and the Garden",
                    "topic": "animals",
                    "text": (
                        "Kofi has a goat. The goat is white. It has two horns. "
                        "The goat likes to eat grass. Kofi feeds the goat every day. "
                        "One day, the goat went into the garden. It ate Mama's vegetables! "
                        "Mama was not happy. Kofi said sorry. He built a fence around the garden. "
                        "Now the goat stays in its pen. The vegetables are safe."
                    ),
                    "word_count": 69,
                },
                {
                    "title": "My School Day",
                    "topic": "school",
                    "text": (
                        "I wake up early. I wash my face. I eat my breakfast. "
                        "Then I walk to school. My school is near my house. "
                        "I see my friends at school. We learn many things. "
                        "My teacher is kind. She helps us read and write. "
                        "I like going to school."
                    ),
                    "word_count": 52,
                },
            ],
            "primary_3": [
                {
                    "title": "The Rainy Season",
                    "topic": "weather",
                    "text": (
                        "The rainy season has come to our village. Dark clouds gather in the sky. "
                        "The wind blows strongly. Then the rain falls. It rains for many hours. "
                        "The rivers fill with water. The farmers are happy because their crops will grow. "
                        "The children play in the rain. They splash in the puddles. "
                        "But we must be careful. Too much rain can cause floods. "
                        "We must keep our drains clean so water can flow away. "
                        "After the rain, the sun comes out. Everything looks green and beautiful. "
                        "The rainy season is important for our country."
                    ),
                    "word_count": 112,
                },
                {
                    "title": "A Day at the Market",
                    "topic": "community",
                    "text": (
                        "On Saturday, Mama and I go to the market. The market is a busy place. "
                        "Many people sell different things. Some sell tomatoes and onions. "
                        "Some sell rice and beans. Others sell cloth and shoes. "
                        "Mama buys fresh fish from the fisherwoman. She buys yams from the farmer. "
                        "I help carry the bags. The market is noisy but exciting. "
                        "I like to hear the traders calling out their prices. "
                        "Mama teaches me to count the change. Going to the market is fun!"
                    ),
                    "word_count": 104,
                },
            ],
            "primary_6": [
                {
                    "title": "The Importance of Clean Water",
                    "topic": "health",
                    "text": (
                        "Water is essential for life. Every person needs clean water to drink, cook, and wash. "
                        "In many African villages, people walk long distances to fetch water from rivers or wells. "
                        "Sometimes this water is not clean. Dirty water can cause diseases like cholera and typhoid. "
                        "To keep water clean, we should boil it before drinking. We should also keep our water containers covered. "
                        "Villages that have boreholes are very fortunate. Borehole water is usually safer than river water. "
                        "It is important for every community to have access to clean drinking water. "
                        "Governments and NGOs work together to build wells and boreholes in rural areas. "
                        "Children who drink clean water are healthier and can concentrate better in school. "
                        "We must all take responsibility for keeping our water sources clean."
                    ),
                    "word_count": 152,
                },
                {
                    "title": "Asha the Young Entrepreneur",
                    "topic": "business",
                    "text": (
                        "Asha is twelve years old. She lives in a small town in Kenya. "
                        "During the school holidays, Asha started a small business. She makes beaded jewellery "
                        "and sells it at the local market. Asha learned to make beads from her grandmother. "
                        "She uses colourful beads and strong thread. Each necklace takes about two hours to make. "
                        "Asha sells her necklaces for 200 shillings each. She uses some of the money to buy more materials. "
                        "She saves the rest in a box at home. Asha dreams of opening a shop one day. "
                        "Her teacher says Asha is learning important skills. She is learning how to manage money, "
                        "how to talk to customers, and how to be responsible. Asha hopes to study business at university. "
                        "She wants to create jobs for other young people in her community."
                    ),
                    "word_count": 158,
                },
            ],
            "jss_1": [
                {
                    "title": "Understanding Malaria",
                    "topic": "health",
                    "text": (
                        "Malaria is one of the most common diseases in Africa. It is caused by a parasite called "
                        "Plasmodium, which is transmitted to humans through the bite of an infected female Anopheles mosquito. "
                        "When a mosquito bites an infected person, it picks up the parasite. When it bites another person, "
                        "it transmits the parasite into their bloodstream. The symptoms of malaria include fever, headache, "
                        "chills, and vomiting. If not treated promptly, malaria can be fatal, especially in young children "
                        "and pregnant women. The best way to prevent malaria is to avoid mosquito bites. People should sleep "
                        "under insecticide-treated mosquito nets. Stagnant water around homes should be drained because it "
                        "provides breeding places for mosquitoes. Houses should have screens on windows and doors. "
                        "If someone shows symptoms of malaria, they should visit a health centre immediately for testing "
                        "and treatment. Artemisinin-based Combination Therapy (ACT) is the most effective treatment. "
                        "Malaria is a preventable and treatable disease. With proper prevention measures, its impact "
                        "on African communities can be greatly reduced."
                    ),
                    "word_count": 198,
                },
                {
                    "title": "The Role of Agriculture in Economic Development",
                    "topic": "agriculture",
                    "text": (
                        "Agriculture is the backbone of many African economies. Over 60 percent of the population "
                        "in sub-Saharan Africa depends on farming for their livelihood. Agriculture provides food "
                        "for families, employment for communities, and raw materials for industries. Crops such as "
                        "maize, rice, cassava, and yams are staples in many African countries. Cash crops like cocoa, "
                        "coffee, cotton, and tea are important exports that bring foreign currency into the country. "
                        "Despite its importance, agriculture in Africa faces many challenges. These include unreliable "
                        "rainfall, poor soil quality, limited access to modern farming tools, and climate change. "
                        "Many farmers still use traditional methods that produce low yields. To improve agricultural "
                        "productivity, governments and organisations are promoting irrigation, providing improved seeds, "
                        "and training farmers in modern techniques. When agriculture thrives, the entire economy benefits. "
                        "Schools can play a role by teaching agricultural science and maintaining school farms that "
                        "demonstrate best practices to the community."
                    ),
                    "word_count": 178,
                },
            ],
            "jss_3": [
                {
                    "title": "Renewable Energy for Rural Africa",
                    "topic": "science",
                    "text": (
                        "Access to electricity remains a significant challenge in many parts of rural Africa. "
                        "According to the World Bank, over 600 million people in sub-Saharan Africa lack access to electricity. "
                        "This affects education, healthcare, and economic development. Children cannot study after dark. "
                        "Hospitals cannot store vaccines properly. Small businesses cannot operate efficiently. "
                        "Renewable energy offers a promising solution. Solar power is particularly suitable for Africa "
                        "because the continent receives abundant sunshine throughout the year. Solar panels can be installed "
                        "on individual homes, in schools, and in health centres. Wind energy is also viable in coastal "
                        "and highland regions. Micro-hydroelectric systems can provide power for communities near rivers. "
                        "Biogas, produced from animal waste and agricultural residue, can be used for cooking and lighting. "
                        "The cost of solar technology has decreased significantly in recent years, making it more accessible. "
                        "Several African countries have launched ambitious renewable energy programmes. Kenya, for example, "
                        "has invested heavily in geothermal and wind energy. Rwanda has distributed solar systems to "
                        "off-grid communities. With continued investment and innovation, renewable energy can transform "
                        "rural Africa and improve the lives of millions of people."
                    ),
                    "word_count": 218,
                },
            ],
            "sss_1": [
                {
                    "title": "The Impact of Climate Change on African Agriculture",
                    "topic": "environment",
                    "text": (
                        "Climate change poses one of the greatest threats to food security in Africa. Rising temperatures, "
                        "changing rainfall patterns, and increased frequency of extreme weather events are already affecting "
                        "agricultural production across the continent. Studies suggest that by 2050, crop yields in sub-Saharan "
                        "Africa could decline by 10 to 20 percent due to climate change if adaptation measures are not taken. "
                        "Maize, wheat, and sorghum - three of Africa's most important crops - are particularly vulnerable to "
                        "heat stress. Changes in rainfall patterns are disrupting traditional farming calendars. In some regions, "
                        "the rainy season is starting later and ending earlier, giving farmers less time to plant and harvest. "
                        "Droughts are becoming more frequent and severe, especially in the Sahel region and parts of East Africa. "
                        "Coastal areas face different challenges: rising sea levels and saltwater intrusion are affecting "
                        "rice production in river deltas. However, African farmers are not passive victims. Many communities "
                        "are adopting climate-smart agriculture practices. These include drought-resistant crop varieties, "
                        "agroforestry, conservation agriculture, and improved water management. International agreements such "
                        "as the Paris Agreement recognise the need to support developing countries in adapting to climate change. "
                        "African nations are calling for increased climate finance to build resilient food systems. "
                        "Education also plays a crucial role: teaching young people about sustainable farming practices "
                        "ensures that the next generation of farmers will be better prepared to face these challenges."
                    ),
                    "word_count": 268,
                },
            ],
        }

        grade_passages = passages.get(grade, passages.get("primary_4", passages["primary_3"]))
        for passage in grade_passages:
            if topic.lower() in passage.get("topic", "").lower():
                return passage

        if grade_passages:
            return grade_passages[0]

        return {
            "title": f"Reading Passage: {topic.title()}",
            "topic": topic,
            "text": f"This is a reading passage about {topic}. " * 20,
            "word_count": 100,
        }

    def get_comprehension_questions(self, passage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehension questions for a reading passage.

        Args:
            passage: Passage dictionary from get_reading_passage.

        Returns:
            List of comprehension questions at literal, inferential, and
            evaluative levels.
        """
        text = passage.get("text", "")
        topic = passage.get("topic", "")
        title = passage.get("title", "")

        questions = [
            {
                "level": "Literal",
                "type": "recall",
                "question": f"What is the title of the passage?",
                "answer": title,
                "marks": 1,
            },
            {
                "level": "Literal",
                "type": "detail",
                "question": f"Who or what is the passage about?",
                "answer": f"The passage is about {topic}.",
                "marks": 2,
            },
            {
                "level": "Literal",
                "type": "detail",
                "question": f"Name two facts mentioned in the passage.",
                "answer": "[Any two facts from the passage]",
                "marks": 2,
            },
            {
                "level": "Inferential",
                "type": "inference",
                "question": f"Why do you think the author wrote this passage?",
                "answer": "[Reasonable inference about author's purpose]",
                "marks": 2,
            },
            {
                "level": "Inferential",
                "type": "relationship",
                "question": f"How does the information in this passage relate to your own life or community?",
                "answer": "[Personal connection to the text]",
                "marks": 3,
            },
            {
                "level": "Evaluative",
                "type": "opinion",
                "question": f"Do you agree with the main idea of this passage? Give reasons for your answer.",
                "answer": "[Opinion with supporting reasons]",
                "marks": 3,
            },
            {
                "level": "Evaluative",
                "type": "synthesis",
                "question": f"What would happen if the situation described in the passage changed? Explain.",
                "answer": "[Thoughtful prediction with explanation]",
                "marks": 3,
            },
            {
                "level": "Vocabulary",
                "type": "word_meaning",
                "question": f"Explain the meaning of an important word from the passage in your own words.",
                "answer": "[Appropriate definition]",
                "marks": 2,
            },
        ]

        return questions

    def get_story(self, grade: str, theme: str) -> Dict[str, Any]:
        """Get a moral story appropriate for the grade and theme.

        Args:
            grade: Grade level.
            theme: Moral theme (e.g., honesty, hard_work, kindness, respect,
                cooperation, courage, wisdom, humility).

        Returns:
            Story with title, text, moral, and discussion questions.
        """
        stories: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "primary": {
                "honesty": [
                    {
                        "title": "The Honest Farmer",
                        "text": (
                            "There was once a farmer named Musa who grew the best tomatoes in the village. "
                            "One market day, a wealthy merchant bought a basket of tomatoes from Musa. "
                            "He accidentally gave Musa too much money. Musa noticed the mistake immediately. "
                            "Even though he was poor and needed the money, he ran after the merchant. "
                            "'Sir, you gave me too much money,' Musa said, handing back the extra coins. "
                            "The merchant was so surprised and pleased. 'You are an honest man,' he said. "
                            "From that day, the merchant bought all his vegetables from Musa. "
                            "He also told all his friends about the honest farmer. "
                            "Musa's business grew, and he became the most successful farmer in the village. "
                            "His honesty had brought him more wealth than the extra coins ever could."
                        ),
                        "moral": "Honesty is always rewarded, even if not immediately.",
                    },
                ],
                "hard_work": [
                    {
                        "title": "The Two Brothers",
                        "text": (
                            "Two brothers, Tunde and Emeka, lived on a farm. Tunde was lazy. He slept late "
                            "and did not like to work. Emeka woke up early every day. He worked hard in the fields. "
                            "At harvest time, Emeka's crops were full and healthy. Tunde's crops were small and weak. "
                            "Emeka had enough food to eat and sell. Tunde did not have enough. "
                            "Tunde learned an important lesson: hard work brings good results. "
                            "The next season, Tunde started waking up early too. He worked hard alongside his brother. "
                            "Together, they had the best harvest the farm had ever seen."
                        ),
                        "moral": "Hard work leads to success. Laziness leads to hunger.",
                    },
                ],
                "kindness": [
                    {
                        "title": "The Kind Girl and the Bird",
                        "text": (
                            "Amina was a kind girl who loved animals. One day, she found a small bird "
                            "with a hurt wing. She gently picked it up and took it home. "
                            "Her mother helped her make a nest from a basket. Amina fed the bird and gave it water. "
                            "Every day, she checked on the bird. Slowly, the bird's wing healed. "
                            "After two weeks, the bird could fly again. Amina took it outside and opened her hands. "
                            "The bird flew up into the sky. But every morning, the bird came back to sing for Amina. "
                            "The whole village heard the beautiful song. Everyone said Amina's kindness had brought "
                            "music to the village."
                        ),
                        "moral": "Kindness to others brings joy to ourselves.",
                    },
                ],
                "cooperation": [
                    {
                        "title": "The Bundle of Sticks",
                        "text": (
                            "An old man had four sons who always argued. One day, the old man called them together. "
                            "He gave each son a single stick and asked them to break it. Each son broke the stick easily. "
                            "Then the old man tied four sticks together into a bundle. He asked each son to break the bundle. "
                            "None of them could break the bundle of sticks. "
                            "'My sons,' the old man said, 'when you are divided, you are weak like a single stick. "
                            "But when you work together, you are strong like the bundle of sticks.' "
                            "The sons understood. From that day, they stopped arguing and worked together. "
                            "Their family became strong and prosperous."
                        ),
                        "moral": "Unity is strength. Working together makes us stronger.",
                    },
                ],
                "wisdom": [
                    {
                        "title": "The Wise Elder",
                        "text": (
                            "In a village, two neighbours were fighting over a piece of land. They went to the village "
                            "elder to settle their dispute. The elder listened carefully to both sides. "
                            "Then he asked them to sit down together. He gave them each a cup of sweet palm wine. "
                            "As they drank together, they started talking. They discovered they were actually distant cousins! "
                            "The elder said, 'Family should not fight over land. Share it, and both your families will benefit.' "
                            "The neighbours agreed. They divided the land fairly and remained friends for life. "
                            "The village praised the elder for his wisdom."
                        ),
                        "moral": "Wisdom and patience can solve problems that anger cannot.",
                    },
                ],
            },
            "secondary": {
                "courage": [
                    {
                        "title": "The Young Defender",
                        "text": (
                            "In a small village near the forest, a young girl named Nia showed great courage. "
                            "One afternoon, while the adults were working in the fields, a fire started in the dry grass "
                            "near the village. The younger children were frightened. Nia, though only fourteen, took charge. "
                            "She organised the children into teams. Some fetched water from the well. Others used wet sacks "
                            "to beat the flames. Nia herself led the team creating a firebreak by clearing dry grass. "
                            "By the time the adults returned, the children had controlled the fire. "
                            "The village chief praised Nia's bravery and leadership. He said, 'Courage is not the absence "
                            "of fear, but acting despite it.' Nia became a symbol of courage for young people in the region."
                        ),
                        "moral": "True courage is taking action despite fear.",
                    },
                ],
                "humility": [
                    {
                        "title": "The Proud Student",
                        "text": (
                            "Kofi was the brightest student in his school. He always came first in examinations. "
                            "Because of this, he became proud. He looked down on his classmates and refused to help them. "
                            "One day, the school announced a science competition. Kofi was confident he would win alone. "
                            "However, the competition required a team of four students. Kofi had to choose teammates. "
                            "Because of his pride, no one wanted to join his team. "
                            "Meanwhile, a group of average students formed a team. They worked together, shared ideas, "
                            "and helped each other. On the day of the competition, their teamwork led them to victory. "
                            "Kofi learned that intelligence alone is not enough. Humility and cooperation are equally important."
                        ),
                        "moral": "Pride leads to isolation. Humility and teamwork lead to success.",
                    },
                ],
            },
        }

        grade_category = "primary" if "primary" in grade else "secondary"
        theme_stories = stories.get(grade_category, {}).get(theme, [{
            "title": f"A Story About {theme.title()}",
            "text": f"Once upon a time, there was a lesson about {theme}. " * 10,
            "moral": f"The moral of the story is: {theme} is important.",
        }])

        story = random.choice(theme_stories)
        story["theme"] = theme
        story["discussion_questions"] = [
            f"What did the main character do that showed {theme}?",
            f"Have you ever faced a situation where you had to show {theme}?",
            f"How would the story have ended differently if the character had not shown {theme}?",
            f"What does this story teach us about {theme} in our daily lives?",
        ]
        story["activities"] = [
            f"Draw a picture of the most important scene in the story.",
            f"Write an alternative ending to the story.",
            f"Act out the story with your classmates.",
            f"Write a diary entry from the main character's point of view.",
        ]

        return story



# ──────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ──────────────────────────────────────────────────────────────────────────

class ReportGenerator:
    """Generates formatted reports and printable documents.

    Converts lesson plans, worksheets, and assessment data into
    human-readable formatted text suitable for printing or display.
    """

    @staticmethod
    def format_lesson_plan(lesson: Dict[str, Any]) -> str:
        """Format a lesson plan as a printable document.

        Args:
            lesson: Lesson plan dictionary from LessonPlanGenerator.

        Returns:
            Formatted string suitable for printing.
        """
        lines = [
            "=" * 70,
            "LESSON PLAN",
            "=" * 70,
            f"Subject:    {lesson.get('subject', 'N/A')}",
            f"Topic:      {lesson.get('topic', 'N/A')}",
            f"Grade:      {lesson.get('grade', 'N/A')}",
            f"Duration:   {lesson.get('duration', 'N/A')} minutes",
            f"Language:   {lesson.get('language', 'english')}",
            f"Date:       {lesson.get('created_at', 'N/A')}",
            "-" * 70,
            "LEARNING OBJECTIVES",
            "-" * 70,
        ]

        for obj in lesson.get("objectives", []):
            lines.append(f"  - {obj}")

        lines.extend([
            "-" * 70,
            "MATERIALS NEEDED",
            "-" * 70,
        ])

        for mat in lesson.get("materials", []):
            lines.append(f"  - {mat}")

        lines.extend([
            "-" * 70,
            "TEACHING ACTIVITIES",
            "-" * 70,
        ])

        for activity in lesson.get("activities", []):
            lines.append(f"\n  [{activity.get('phase', 'Activity')}]")
            lines.append(f"  Duration: {activity.get('duration', 'N/A')} minutes")
            lines.append(f"  Description: {activity.get('description', 'N/A')}")
            lines.append(f"  Teacher: {activity.get('teacher_action', 'N/A')}")
            lines.append(f"  Students: {activity.get('student_action', 'N/A')}")

        lines.extend([
            "-" * 70,
            "ASSESSMENT",
            "-" * 70,
        ])

        assessment = lesson.get("assessment", {})
        for key, items in assessment.items():
            if isinstance(items, list):
                lines.append(f"  {key.replace('_', ' ').title()}:")
                for item in items:
                    lines.append(f"    - {item}")

        lines.extend([
            "-" * 70,
            "TEACHER NOTES",
            "-" * 70,
        ])

        for note in lesson.get("teacher_notes", []):
            lines.append(f"  - {note}")

        lines.extend([
            "-" * 70,
            "DIFFERENTIATION",
            "-" * 70,
        ])

        differentiation = lesson.get("differentiation", {})
        for key, items in differentiation.items():
            if isinstance(items, list):
                lines.append(f"  {key.replace('_', ' ').title()}:")
                for item in items:
                    lines.append(f"    - {item}")

        lines.extend([
            "=" * 70,
            "End of Lesson Plan",
            "=" * 70,
        ])

        return "\n".join(lines)

    @staticmethod
    def format_worksheet(worksheet: Dict[str, Any]) -> str:
        """Format a worksheet as a printable document.

        Args:
            worksheet: Worksheet dictionary from WorksheetGenerator.

        Returns:
            Formatted string suitable for printing.
        """
        lines = [
            "=" * 70,
            f"WORKSHEET: {worksheet.get('title', 'Untitled')}",
            "=" * 70,
            f"Grade: {worksheet.get('grade', 'N/A')}  |  "
            f"Difficulty: {worksheet.get('difficulty', 'N/A')}  |  "
            f"Total Marks: {worksheet.get('total_marks', 'N/A')}",
            "",
            worksheet.get('instructions', 'Answer all questions.'),
            "",
            "-" * 70,
            "QUESTIONS",
            "-" * 70,
        ]

        for q in worksheet.get("questions", []):
            lines.append(f"\n{q.get('number', '?')}. [{q.get('type', '').upper()}] "
                        f"({q.get('marks', 1)} marks)")
            lines.append(f"   {q.get('question', 'N/A')}")
            if q.get("type") == "multiple_choice" and "options" in q:
                for opt in q["options"]:
                    lines.append(f"      {opt}")

        lines.extend([
            "",
            "-" * 70,
            "ANSWER KEY (For Teacher Use Only)",
            "-" * 70,
        ])

        for ans in worksheet.get("answer_key", []):
            lines.append(f"  Q{ans.get('question_number', '?')}: {ans.get('correct_answer', 'N/A')} "
                        f"({ans.get('marks', 1)} marks)")
            lines.append(f"    Guidance: {ans.get('marking_guidance', 'N/A')}")

        lines.extend([
            "=" * 70,
        ])

        return "\n".join(lines)

    @staticmethod
    def format_daily_schedule(schedule: Dict[str, Any]) -> str:
        """Format a daily schedule as a readable timetable.

        Args:
            schedule: Schedule dictionary from LessonPlanGenerator.

        Returns:
            Formatted timetable string.
        """
        lines = [
            "=" * 70,
            "DAILY TIMETABLE",
            "=" * 70,
            f"Grade: {schedule.get('grade', 'N/A')}",
            f"Date:  {schedule.get('date', 'N/A')}",
            "-" * 70,
            f"{'Time':<15} {'Activity':<40} {'Type':<10}",
            "-" * 70,
        ]

        for period in schedule.get("periods", []):
            time_str = f"{period.get('start', '')} - {period.get('end', '')}"
            name = period.get("name", "N/A")
            ptype = period.get("type", "N/A")
            icon = period.get("icon", "")
            lines.append(f"{time_str:<15} {icon} {name:<38} {ptype:<10}")

        lines.extend([
            "-" * 70,
            f"Total school hours: {schedule.get('total_hours', 'N/A'):.1f}",
            "=" * 70,
        ])

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

_lesson_generator: Optional[LessonPlanGenerator] = None
_worksheet_generator: Optional[WorksheetGenerator] = None
_teaching_methods: Optional[TeachingMethods] = None
_stem_experiments: Optional[STEMExperiments] = None
_assessment_tracker: Optional[AssessmentTracker] = None
_multilingual: Optional[MultilingualSupport] = None
_special_needs: Optional[SpecialNeeds] = None
_reading_material: Optional[ReadingMaterial] = None
_db_manager: Optional[DatabaseManager] = None


def _get_db() -> DatabaseManager:
    """Get or create the singleton DatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def _get_lesson_generator() -> LessonPlanGenerator:
    """Get or create the singleton LessonPlanGenerator instance."""
    global _lesson_generator
    if _lesson_generator is None:
        _lesson_generator = LessonPlanGenerator(_get_db())
    return _lesson_generator


def _get_worksheet_generator() -> WorksheetGenerator:
    """Get or create the singleton WorksheetGenerator instance."""
    global _worksheet_generator
    if _worksheet_generator is None:
        _worksheet_generator = WorksheetGenerator(_get_db())
    return _worksheet_generator


def _get_teaching_methods() -> TeachingMethods:
    """Get or create the singleton TeachingMethods instance."""
    global _teaching_methods
    if _teaching_methods is None:
        _teaching_methods = TeachingMethods()
    return _teaching_methods


def _get_stem_experiments() -> STEMExperiments:
    """Get or create the singleton STEMExperiments instance."""
    global _stem_experiments
    if _stem_experiments is None:
        _stem_experiments = STEMExperiments()
    return _stem_experiments


def _get_assessment_tracker() -> AssessmentTracker:
    """Get or create the singleton AssessmentTracker instance."""
    global _assessment_tracker
    if _assessment_tracker is None:
        _assessment_tracker = AssessmentTracker(_get_db())
    return _assessment_tracker


def _get_multilingual() -> MultilingualSupport:
    """Get or create the singleton MultilingualSupport instance."""
    global _multilingual
    if _multilingual is None:
        _multilingual = MultilingualSupport()
    return _multilingual


def _get_special_needs() -> SpecialNeeds:
    """Get or create the singleton SpecialNeeds instance."""
    global _special_needs
    if _special_needs is None:
        _special_needs = SpecialNeeds()
    return _special_needs


def _get_reading_material() -> ReadingMaterial:
    """Get or create the singleton ReadingMaterial instance."""
    global _reading_material
    if _reading_material is None:
        _reading_material = ReadingMaterial()
    return _reading_material


def create_lesson(
    subject: str,
    topic: str,
    grade: str,
    duration: int = 40,
) -> Dict[str, Any]:
    """Quick function to create a lesson plan.

    This is a convenience wrapper around LessonPlanGenerator.generate_lesson()
    for quick lesson creation without instantiating the class.

    Args:
        subject: Subject key (e.g., 'mathematics', 'english').
        topic: Topic to cover (e.g., 'fractions', 'photosynthesis').
        grade: Grade level (e.g., 'primary_4', 'jss_2').
        duration: Lesson duration in minutes (default 40).

    Returns:
        Complete lesson plan dictionary.

    Example:
        >>> plan = create_lesson("mathematics", "fractions", "primary_4")
        >>> print(plan["subject"])
        Mathematics
    """
    generator = _get_lesson_generator()
    return generator.generate_lesson(
        subject=subject,
        topic=topic,
        grade=grade,
        duration=duration,
    )


def create_worksheet(
    subject: str,
    topic: str,
    grade: str,
    num_questions: int = 10,
    difficulty: str = "medium",
) -> Dict[str, Any]:
    """Quick function to create a worksheet.

    This is a convenience wrapper around WorksheetGenerator.generate_worksheet().

    Args:
        subject: Subject key.
        topic: Topic to assess.
        grade: Grade level.
        num_questions: Number of questions (default 10).
        difficulty: Difficulty level - easy, medium, or hard.

    Returns:
        Worksheet dictionary with questions and answer key.

    Example:
        >>> ws = create_worksheet("science", "plants", "primary_3", num_questions=5)
        >>> print(ws["total_marks"])
    """
    generator = _get_worksheet_generator()
    return generator.generate_worksheet(
        subject=subject,
        topic=topic,
        grade=grade,
        num_questions=num_questions,
        difficulty=difficulty,
    )


def teaching_tip(challenge: str) -> Dict[str, Any]:
    """Get practical advice for a specific teaching challenge.

    Provides targeted strategies for common challenges faced by teachers
    in under-resourced African schools.

    Args:
        challenge: Description of the teaching challenge. Common options:
            - large_class: Managing 50+ students
            - no_textbooks: Teaching without textbooks
            - mixed_ability: Different skill levels in one class
            - limited_time: Short class periods
            - discipline: Behaviour management
            - no_electricity: Teaching without power
            - assessment: Assessing large numbers of students
            - parent_engagement: Involving parents
            - absenteeism: Handling frequent absences
            - overcrowded_classroom: Very limited space

    Returns:
        Advice dictionary with strategies, tips, and resources.
    """
    tips: Dict[str, Dict[str, Any]] = {
        "large_class": {
            "challenge": "Managing a class of 50-80 students",
            "strategies": [
                "Use group work to make large classes manageable. Divide into groups of 6-8.",
                "Train group leaders to help distribute materials and collect work.",
                "Use choral responses for whole-class participation.",
                "Use peer teaching - stronger students help weaker ones.",
                "Mark books in rotation (e.g., mark 15 books per day, not all 80).",
                "Use self-assessment and peer-assessment where possible.",
                "Create a seating chart and learn names quickly using name tags.",
            ],
            "activities_for_large_classes": [
                "Think-Pair-Share: All students think, discuss with partner, then share.",
                "Choral Drills: Whole class recites times tables, vocabulary, or formulas.",
                "Board Races: Teams send representatives to solve problems on the board.",
                "Group Projects: Divide topics among groups who then teach the class.",
            ],
        },
        "no_textbooks": {
            "challenge": "Teaching with no or insufficient textbooks",
            "strategies": [
                "Write everything on the chalkboard - treat it as the textbook.",
                "Have students copy board notes carefully into their exercise books.",
                "Create simplified notes on paper and photocopy if possible.",
                "Use oral teaching and storytelling extensively.",
                "Use the environment as a teaching resource (nature, community).",
                "Share one textbook among 3-4 students during reading activities.",
                "Encourage students to create their own reference materials.",
            ],
            "low_cost_alternatives": [
                "Chalkboard as the primary text - plan board work carefully.",
                "Student-made notebooks - compile notes over the term.",
                "Community resources - invite local experts as guest speakers.",
                "Peer notes - stronger students help compile class notes.",
            ],
        },
        "mixed_ability": {
            "challenge": "Teaching students with very different skill levels in one class",
            "strategies": [
                "Differentiate instruction: same topic, different difficulty levels.",
                "Use tiered worksheets - basic, standard, and advanced versions.",
                "Pair stronger students with weaker students for peer support.",
                "Group students by ability for specific activities, then mix for others.",
                "Provide extension activities for fast finishers.",
                "Focus on individual progress rather than comparison between students.",
                "Use continuous assessment to track each student's growth.",
            ],
            "differentiation_techniques": [
                "Vary the complexity of questions asked to different students.",
                "Provide scaffolding (sentence starters, word banks) for struggling students.",
                "Offer open-ended tasks that allow different levels of response.",
                "Use mixed-ability grouping for cooperative learning.",
            ],
        },
        "discipline": {
            "challenge": "Managing student behaviour and maintaining order",
            "strategies": [
                "Establish clear rules from day one and apply them consistently.",
                "Use positive reinforcement - praise good behaviour publicly.",
                "Use non-verbal cues (eye contact, proximity) before verbal warnings.",
                "Have a clear escalation system: reminder, warning, consequence.",
                "Never use corporal punishment - it is harmful and often illegal.",
                "Build relationships - students behave better for teachers they respect.",
                "Keep students engaged - bored students misbehave.",
                "Address the root cause: is the student hungry, tired, or facing problems at home?",
            ],
            "positive_reinforcement": [
                "Smile and greet students by name every day.",
                "Publicly praise students who are working well.",
                "Use a class reward system (stars, points, privileges).",
                "Send positive notes home to parents.",
                "Give students responsibilities and trust them.",
            ],
        },
        "no_electricity": {
            "challenge": "Teaching without electricity or technology",
            "strategies": [
                "Maximise use of the chalkboard - plan detailed board work.",
                "Use natural light - position the board to avoid glare.",
                "Use hand-drawn visual aids, charts, and flashcards.",
                "Use songs, rhymes, and oral traditions that require no technology.",
                "Use physical demonstrations and hands-on activities.",
                "Organise outdoor lessons when weather permits.",
                "Use a battery-powered torch for early morning or evening classes if needed.",
            ],
            "tech_free_teaching_tools": [
                "Chalkboard and chalk (primary teaching tool)",
                "Hand-drawn charts and diagrams on paper or cardboard",
                "Physical objects from the environment as teaching aids",
                "Songs, rhymes, and oral storytelling",
                "Student-made flashcards and learning materials",
                "Games and physical activities for active learning",
            ],
        },
        "assessment": {
            "challenge": "Assessing learning in large classes with limited time",
            "strategies": [
                "Use quick formative assessments: thumbs up/down, mini whiteboards.",
                "Mark books in rotation - not every book every day.",
                "Use peer assessment for objective questions.",
                "Use self-assessment checklists.",
                "Conduct oral assessments during group work.",
                "Give whole-class feedback on common errors rather than individual marking.",
                "Use exit tickets: one question at the end of each lesson.",
                "Simplify record-keeping: use class mark sheets, not individual cards.",
            ],
            "time_saving_assessment": [
                "True/False and Multiple Choice (quick to mark)",
                "Peer marking (students swap and mark each other's work)",
                "Traffic light system (green=understand, yellow=some confusion, red=need help)",
                "One-minute papers (students write one thing they learned)",
            ],
        },
        "overcrowded_classroom": {
            "challenge": "Very limited classroom space with too many students",
            "strategies": [
                "Use every available space - some students can sit on mats on the floor.",
                "Create outdoor learning areas under trees for appropriate lessons.",
                "Stagger seating arrangements - some face front, some face sides.",
                "Rotate groups so not all students are in the room at once (if policy allows).",
                "Use the walls - hang learning materials at student eye level.",
                "Keep aisles clear for teacher movement.",
                "Request additional furniture from the community or local government.",
            ],
            "space_maximisation": [
                "Use vertical space: hang materials on walls and from ceiling.",
                "Outdoor classes for nature, agriculture, and PE lessons.",
                "Community hall or church for whole-school assemblies.",
                "Shared desk rotation: some students work on the floor with clipboards.",
            ],
        },
        "absenteeism": {
            "challenge": "Students missing school frequently",
            "strategies": [
                "Track attendance daily and identify patterns.",
                "Speak with students and families to understand the root cause.",
                "Common causes: illness, family responsibilities, farming season, lack of fees/uniform.",
                "Provide catch-up materials for absent students.",
                "Work with community leaders to emphasise the value of education.",
                "Create a welcoming classroom so students want to attend.",
                "For farming season: adjust homework to be lighter during harvest time.",
            ],
            "community_solutions": [
                "Parent-teacher association meetings to discuss attendance.",
                "Community education about the importance of regular schooling.",
                "School feeding programmes to incentivise attendance.",
                "Flexible schedules during planting and harvest seasons.",
            ],
        },
        "parent_engagement": {
            "challenge": "Getting parents involved in their children's education",
            "strategies": [
                "Hold parent meetings at convenient times (evenings or weekends).",
                "Send simple, positive notes home regularly.",
                "Invite parents to school events and celebrations.",
                "Explain how parents can help at home (reading together, checking homework).",
                "Use community meetings and religious gatherings to share school information.",
                "Respect parents' time constraints - many work long hours.",
                "Address language barriers by using local language interpreters.",
            ],
            "home_support_ideas": [
                "Ask parents to listen to their children read for 10 minutes daily.",
                "Encourage parents to ask children what they learned at school.",
                "Suggest practical math activities at home (counting, measuring).",
                "Provide take-home activities that require no special materials.",
            ],
        },
    }

    result = tips.get(challenge)

    if result is None:
        for key, value in tips.items():
            if challenge.lower() in key or key in challenge.lower():
                result = value
                break

    if result is None:
        result = {
            "challenge": challenge,
            "note": "Challenge not specifically catalogued. Here are all available teaching tip categories.",
            "available_challenges": list(tips.keys()),
            "general_advice": [
                "Stay positive and patient. Teaching is a challenging but rewarding profession.",
                "Seek support from fellow teachers. Share ideas and resources.",
                "Focus on what you CAN do with the resources you have.",
                "Celebrate small victories with your students.",
                "Continuously learn and improve your teaching practice.",
            ],
        }

    result["requested_challenge"] = challenge
    return result


def stem_experiment(subject: str, topic: str) -> Dict[str, Any]:
    """Quick function to get a hands-on STEM experiment.

    This is a convenience wrapper around STEMExperiments.get_experiment().

    Args:
        subject: Subject key (biology, chemistry, physics, science).
        topic: Topic for the experiment.

    Returns:
        Experiment protocol with materials, procedure, and safety notes.

    SAFETY DISCLAIMER: All experiments should be supervised by a qualified
    teacher. Follow appropriate safety precautions.

    Example:
        >>> exp = stem_experiment("physics", "static_electricity")
        >>> print(exp["materials"])
    """
    experiments = _get_stem_experiments()
    return experiments.get_experiment(subject, topic)


def assessment_tracker(subject: str, students: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Quick function to track student assessment data.

    This is a convenience wrapper around AssessmentTracker that processes
    a batch of student records and generates summary analytics.

    Args:
        subject: Subject key.
        students: List of student dicts, each with:
            name (str), scores (List[float]), max_score (float, optional).

    Returns:
        Summary report with class statistics and individual analysis.

    DISCLAIMER: This tool provides analytical support only. Final decisions
    about student progression should be made by qualified educators.

    Example:
        >>> students = [
        ...     {"name": "Ada", "scores": [15, 18, 20]},
        ...     {"name": "Ben", "scores": [10, 12, 14]},
        ... ]
        >>> report = assessment_tracker("mathematics", students)
        >>> print(report["class_average"])
    """
    tracker = _get_assessment_tracker()

    if not students:
        return {"error": "No student data provided"}

    individual_results = []
    all_averages = []

    for student in students:
        name = student.get("name", "Unknown")
        scores = student.get("scores", [])
        max_score = student.get("max_score", 100)

        if not scores:
            continue

        average = sum(scores) / len(scores)
        percentage = (average / max_score) * 100 if max_score > 0 else 0
        all_averages.append(percentage)

        grade = "F9"
        if percentage >= 75:
            grade = "A1"
        elif percentage >= 70:
            grade = "B2"
        elif percentage >= 65:
            grade = "B3"
        elif percentage >= 60:
            grade = "C4"
        elif percentage >= 55:
            grade = "C5"
        elif percentage >= 50:
            grade = "C6"
        elif percentage >= 45:
            grade = "D7"
        elif percentage >= 40:
            grade = "E8"

        individual_results.append({
            "name": name,
            "scores": scores,
            "average": round(average, 1),
            "percentage": round(percentage, 1),
            "grade": grade,
            "passed": percentage >= 50,
        })

    if all_averages:
        class_avg = round(sum(all_averages) / len(all_averages), 1)
        highest = round(max(all_averages), 1)
        lowest = round(min(all_averages), 1)
        passed_count = sum(1 for r in individual_results if r["passed"])
    else:
        class_avg = highest = lowest = 0
        passed_count = 0

    report: Dict[str, Any] = {
        "subject": SUBJECTS.get(subject, {}).get("name", subject),
        "subject_key": subject,
        "total_students": len(students),
        "class_average_percentage": class_avg,
        "highest_score": highest,
        "lowest_score": lowest,
        "pass_rate": round((passed_count / len(students)) * 100, 1) if students else 0,
        "students_passed": passed_count,
        "students_failed": len(students) - passed_count,
        "individual_results": individual_results,
        "generated_at": datetime.datetime.now().isoformat(),
        "teacher_recommendations": [
            "Review difficult topics where many students scored poorly.",
            "Provide remedial support for students who failed.",
            "Use peer tutoring to help struggling students.",
            "Plan a revision lesson before the next assessment.",
            "Contact parents of students who are consistently underperforming.",
        ],
    }

    logger.info("Assessment tracker report generated for %s: %d students, %.1f%% class average",
                subject, len(students), class_avg)
    return report



# ──────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT (for testing and CLI usage)
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point for testing the teacher assistant module.

    Run with: python teacher_assistant.py

    This demonstrates the key features of the module with sample data.
    """
    print("=" * 70)
    print("  Luqi AI v20 - Teacher Assistant for Africa")
    print("  Demonstration Mode")
    print("=" * 70)
    print()

    # 1. Generate a lesson plan
    print("[1] GENERATING LESSON PLAN...")
    print("-" * 70)
    lesson = create_lesson("mathematics", "fractions", "primary_4", duration=40)
    print(f"  Subject: {lesson['subject']}")
    print(f"  Topic: {lesson['topic']}")
    print(f"  Grade: {lesson['grade']}")
    print(f"  Duration: {lesson['duration']} minutes")
    print(f"  Objectives: {len(lesson['objectives'])}")
    for obj in lesson['objectives']:
        print(f"    - {obj}")
    print(f"  Materials: {len(lesson['materials'])}")
    print(f"  Activities: {len(lesson['activities'])} phases")
    print()

    # 2. Generate a worksheet
    print("[2] GENERATING WORKSHEET...")
    print("-" * 70)
    ws = create_worksheet("science", "plants", "primary_3", num_questions=5)
    print(f"  Title: {ws['title']}")
    print(f"  Questions: {ws['num_questions']}")
    print(f"  Total Marks: {ws['total_marks']}")
    print(f"  Difficulty: {ws['difficulty']}")
    for q in ws['questions']:
        print(f"    Q{q['number']}. {q['question'][:60]}...")
    print()

    # 3. Get a STEM experiment
    print("[3] GETTING STEM EXPERIMENT...")
    print("-" * 70)
    exp = stem_experiment("chemistry", "acids_and_bases")
    print(f"  Title: {exp['title']}")
    print(f"  Materials: {len(exp['materials'])}")
    for mat in exp['materials']:
        print(f"    - {mat}")
    print(f"  Expected Result: {exp['expected_result'][:80]}...")
    print()

    # 4. Get teaching tip
    print("[4] GETTING TEACHING TIP...")
    print("-" * 70)
    tip = teaching_tip("large_class")
    print(f"  Challenge: {tip['challenge']}")
    print(f"  Strategies: {len(tip['strategies'])}")
    for s in tip['strategies'][:3]:
        print(f"    - {s[:70]}...")
    print()

    # 5. Track assessment
    print("[5] TRACKING ASSESSMENTS...")
    print("-" * 70)
    students = [
        {"name": "Ada Okafor", "scores": [18, 20, 15, 19]},
        {"name": "Ben Kimani", "scores": [12, 14, 10, 13]},
        {"name": "Chido Moyo", "scores": [8, 10, 7, 9]},
        {"name": "Diallo Ndiaye", "scores": [20, 19, 18, 20]},
        {"name": "Esi Asante", "scores": [15, 16, 14, 17]},
    ]
    report = assessment_tracker("mathematics", students)
    print(f"  Subject: {report['subject']}")
    print(f"  Students: {report['total_students']}")
    print(f"  Class Average: {report['class_average_percentage']}%")
    print(f"  Pass Rate: {report['pass_rate']}%")
    print(f"  Top Performer: {report['individual_results'][0]['name']} "
          f"({report['individual_results'][0]['percentage']}%)")
    print()

    # 6. Daily schedule
    print("[6] GENERATING DAILY SCHEDULE...")
    print("-" * 70)
    gen = LessonPlanGenerator()
    schedule = gen.generate_daily_schedule(
        subjects=["mathematics", "english", "science", "social_studies", "agriculture"],
        grade="primary_5",
    )
    print(ReportGenerator.format_daily_schedule(schedule))
    print()

    # 7. Multilingual support
    print("[7] MULTILINGUAL SUPPORT...")
    print("-" * 70)
    ml = _get_multilingual()
    vocab = ml.get_subject_vocabulary("mathematics", "swahili")
    print(f"  Language: {vocab['language_name']}")
    print(f"  Subject: {vocab['subject_name']}")
    for term in vocab['vocabulary'][:3]:
        print(f"    {term['english']} = {term['translation']} ({term['pronunciation']})")
    print()

    # 8. Special needs
    print("[8] INCLUSION STRATEGIES...")
    print("-" * 70)
    sn = _get_special_needs()
    strategies = sn.get_inclusion_strategies("visual_impairment")
    print(f"  Condition: {strategies['name']}")
    print(f"  Strategies: {len(strategies['teaching_strategies'])}")
    for s in strategies['teaching_strategies'][:3]:
        print(f"    - {s[:70]}...")
    print()

    # 9. Reading material
    print("[9] READING MATERIAL...")
    print("-" * 70)
    rm = _get_reading_material()
    passage = rm.get_reading_passage("primary_3", "weather")
    print(f"  Title: {passage['title']}")
    print(f"  Word Count: {passage['word_count']}")
    questions = rm.get_comprehension_questions(passage)
    print(f"  Comprehension Questions: {len(questions)}")
    for q in questions[:3]:
        print(f"    [{q['level']}] {q['question'][:60]}...")
    print()

    # 10. Bilingual lesson
    print("[10] BILINGUAL LESSON PLAN...")
    print("-" * 70)
    bl = ml.get_bilingual_lesson("science", "plants", "english", "swahili")
    print(f"  Subject: {bl['subject']}")
    print(f"  Topic: {bl['topic']}")
    print(f"  Languages: {bl['primary_language']} + {bl['secondary_language']}")
    print(f"  Key Terms: {len(bl['lesson_structure']['key_terms'])}")
    print()

    print("=" * 70)
    print("  Demonstration Complete!")
    print("  All systems operational.")
    print("  Luqi AI v20 - Ready to support African educators.")
    print("=" * 70)


if __name__ == "__main__":
    main()
