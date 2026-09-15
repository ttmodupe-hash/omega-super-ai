#!/usr/bin/env python3
"""Luqi AI v20 - Healthcare Assistant for Africa
================================================
Health information system providing guidance on common conditions,
first aid, maternal health, nutrition, and preventive care.

IMPORTANT: This does NOT provide medical diagnosis or replace qualified
healthcare professionals. Always consult a licensed medical practitioner.

DISCLAIMER: All information provided by this module is for educational
purposes only and does not constitute medical advice. In case of medical
emergency, contact emergency services immediately.

Target Users:
    - Community health workers in rural Africa
    - Individuals seeking health information
    - Caregivers and parents
    - Pregnant women and new mothers

Geographic Focus:
    - Sub-Saharan Africa
    - 15+ countries with localized content

Guideline Sources:
    - World Health Organization (WHO)
    - UNICEF Child Health Guidelines
    - African Union Health Initiatives
    - National health ministries

Author: Luqi AI v20
License: MIT
Python: 3.8+
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = "20.0.0"
__author__ = "Luqi AI"
__license__ = "MIT"
__all__ = [
    "FirstAidGuide",
    "MaternalHealthGuide",
    "ChildHealthGuide",
    "DiseaseInformation",
    "NutritionGuide",
    "MentalHealthSupport",
    "HealthFacilityLocator",
    "health_info",
    "first_aid",
    "check_symptoms",
    "maternal_health",
    "child_health",
    "nutrition_advice",
    "MedicalDisclaimer",
    "UrgencyLevel",
    "HealthRecordDB",
]

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logger = logging.getLogger("luqi_healthcare")
logger.setLevel(logging.DEBUG)

# Console handler
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_format = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_console_handler.setFormatter(_console_format)

# File handler (if writable directory exists)
_log_dir = Path.home() / ".luqi" / "logs"
try:
    _log_dir.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(_log_dir / "healthcare.log")
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(_console_format)
    logger.addHandler(_file_handler)
except OSError:
    pass  # Silent fail for restricted environments

logger.addHandler(_console_handler)


# ============================================================================
# DISCLAIMER UTILITIES
# ============================================================================

class MedicalDisclaimer:
    """Provides medical disclaimers for all health information outputs.

    Every public-facing method in this module should include a disclaimer
    in its output to ensure users understand the educational nature of
    the information provided.
    """

    STANDARD_DISCLAIMER: str = (
        "\n\n=== MEDICAL DISCLAIMER ===\n"
        "This information is for educational purposes only and does not "
        "constitute medical advice. Always consult a qualified healthcare "
        "professional for diagnosis, treatment, and personalized medical "
        "guidance. In case of emergency, contact your local emergency "
        "services immediately."
    )

    EMERGENCY_DISCLAIMER: str = (
        "\n\n=== EMERGENCY DISCLAIMER ===\n"
        "This is a medical EMERGENCY. Call your local emergency number "
        "IMMEDIATELY. This information is only a temporary guide while "
        "waiting for professional medical help. Do NOT delay seeking "
        "emergency care."
    )

    CHILDREN_DISCLAIMER: str = (
        "\n\n=== CHILD SAFETY DISCLAIMER ===\n"
        "Children require specialized medical care. This information is "
        "for educational purposes only. For any child health concern, "
        "consult a pediatric healthcare provider immediately."
    )

    PREGNANCY_DISCLAIMER: str = (
        "\n\n=== PREGNANCY DISCLAIMER ===\n"
        "Pregnancy and childbirth require professional medical supervision. "
        "Attend all antenatal care appointments and seek immediate medical "
        "attention for any danger signs. This information supplements but "
        "does not replace professional maternity care."
    )

    MENTAL_HEALTH_DISCLAIMER: str = (
        "\n\n=== MENTAL HEALTH DISCLAIMER ===\n"
        "If you or someone you know is in crisis or having thoughts of "
        "self-harm, seek immediate help from a mental health professional "
        "or emergency services. You are not alone. Help is available."
    )

    TRADITIONAL_MEDICINE_DISCLAIMER: str = (
        "\n\n=== TRADITIONAL MEDICINE WARNING ===\n"
        "Traditional remedies mentioned are for informational purposes only. "
        "Always inform your healthcare provider about any traditional "
        "medicines you are using, as some may interact with conventional "
        "medications or have side effects. Safety and efficacy may vary."
    )

    @classmethod
    def wrap(cls, content: str, disclaimer_type: str = "standard") -> str:
        """Wrap content with the specified disclaimer type.

        Args:
            content: The health information content to wrap.
            disclaimer_type: One of 'standard', 'emergency', 'children',
                'pregnancy', 'mental_health', 'traditional'.

        Returns:
            Content string with appropriate disclaimer appended.
        """
        disclaimers = {
            "standard": cls.STANDARD_DISCLAIMER,
            "emergency": cls.EMERGENCY_DISCLAIMER,
            "children": cls.CHILDREN_DISCLAIMER,
            "pregnancy": cls.PREGNANCY_DISCLAIMER,
            "mental_health": cls.MENTAL_HEALTH_DISCLAIMER,
            "traditional": cls.TRADITIONAL_MEDICINE_DISCLAIMER,
        }
        disclaimer = disclaimers.get(disclaimer_type, cls.STANDARD_DISCLAIMER)
        return content + disclaimer


# ============================================================================
# ENUMERATIONS
# ============================================================================

class UrgencyLevel(Enum):
    """Urgency levels for health conditions."""

    CRITICAL = "CRITICAL - Seek emergency care immediately"
    URGENT = "URGENT - Seek medical care within 24 hours"
    MODERATE = "MODERATE - Schedule medical appointment soon"
    LOW = "LOW - Monitor and consult if persists"
    INFORMATIONAL = "INFORMATIONAL - General health guidance"


class FacilityType(Enum):
    """Types of health facilities."""

    HOSPITAL = "Hospital"
    CLINIC = "Clinic"
    HEALTH_CENTER = "Health Center"
    PHARMACY = "Pharmacy"
    COMMUNITY_HEALTH_WORKER = "Community Health Worker"
    TRADITIONAL_HEALER = "Traditional Healer"
    MATERNITY_CLINIC = "Maternity Clinic"
    DIAGNOSTIC_CENTER = "Diagnostic Center"


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class HealthRecordDB:
    """SQLite database manager for health records and queries.

    Provides persistent storage for:
    - Health query history
    - Immunization records
    - Growth tracking for children
    - Pregnancy tracking
    - Medication reminders

    Thread-safe singleton for concurrent access.
    """

    _instance: Optional[HealthRecordDB] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> HealthRecordDB:
        """Singleton pattern for database access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize database connection and schema.

        Args:
            db_path: Path to SQLite database file. If None, uses
                default location in user's home directory.
        """
        if self._initialized:
            return

        if db_path is None:
            db_dir = Path.home() / ".luqi" / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "health_records.db")
        else:
            self.db_path = db_path

        self._local = threading.local()
        self._initialize_schema()
        self._initialized = True
        logger.info(f"HealthRecordDB initialized at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS health_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            category TEXT,
            age INTEGER,
            country TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS immunization_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_name TEXT NOT NULL,
            birth_date DATE NOT NULL,
            vaccine_name TEXT NOT NULL,
            scheduled_date DATE,
            administered_date DATE,
            administered_by TEXT,
            facility TEXT,
            notes TEXT,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_name TEXT NOT NULL,
            birth_date DATE NOT NULL,
            record_date DATE NOT NULL,
            age_months INTEGER,
            weight_kg REAL,
            height_cm REAL,
            muac_cm REAL,
            head_circumference_cm REAL,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pregnancy_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_name TEXT NOT NULL,
            lmp_date DATE,
            edd_date DATE,
            current_week INTEGER,
            weight_kg REAL,
            blood_pressure TEXT,
            notes TEXT,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS medication_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            medication_name TEXT NOT NULL,
            dosage TEXT,
            frequency TEXT,
            start_date DATE,
            end_date DATE,
            prescribed_by TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON health_queries(timestamp);
        CREATE INDEX IF NOT EXISTS idx_queries_category ON health_queries(category);
        CREATE INDEX IF NOT EXISTS idx_immunization_child ON immunization_records(child_name);
        CREATE INDEX IF NOT EXISTS idx_growth_child ON growth_records(child_name);
        CREATE INDEX IF NOT EXISTS idx_pregnancy_mother ON pregnancy_tracking(mother_name);
        """
        try:
            conn = self._get_connection()
            conn.executescript(schema)
            conn.commit()
            logger.debug("Database schema initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database schema initialization failed: {e}")
            raise

    def log_query(
        self,
        query_text: str,
        category: Optional[str] = None,
        age: Optional[int] = None,
        country: Optional[str] = None,
    ) -> bool:
        """Log a health query to the database.

        Args:
            query_text: The health query string.
            category: Category of the query (e.g., 'first_aid', 'maternal').
            age: Age of the person the query is about.
            country: Country context for the query.

        Returns:
            True if logged successfully, False otherwise.
        """
        try:
            conn = self._get_connection()
            conn.execute(
                """INSERT INTO health_queries (query_text, category, age, country)
                   VALUES (?, ?, ?, ?)""",
                (query_text, category, age, country),
            )
            conn.commit()
            logger.debug(f"Query logged: {category} - {query_text[:50]}...")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to log query: {e}")
            return False

    def add_immunization_record(
        self,
        child_name: str,
        birth_date: str,
        vaccine_name: str,
        scheduled_date: Optional[str] = None,
        administered_date: Optional[str] = None,
        administered_by: Optional[str] = None,
        facility: Optional[str] = None,
        notes: Optional[str] = None,
        country: Optional[str] = None,
    ) -> bool:
        """Add an immunization record.

        Args:
            child_name: Name of the child.
            birth_date: Birth date in YYYY-MM-DD format.
            vaccine_name: Name of the vaccine.
            scheduled_date: Scheduled date for the vaccine.
            administered_date: Date when vaccine was administered.
            administered_by: Name of healthcare worker.
            facility: Facility where vaccine was given.
            notes: Additional notes.
            country: Country context.

        Returns:
            True if added successfully, False otherwise.
        """
        try:
            conn = self._get_connection()
            conn.execute(
                """INSERT INTO immunization_records
                   (child_name, birth_date, vaccine_name, scheduled_date,
                    administered_date, administered_by, facility, notes, country)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (child_name, birth_date, vaccine_name, scheduled_date,
                 administered_date, administered_by, facility, notes, country),
            )
            conn.commit()
            logger.debug(f"Immunization record added for {child_name}: {vaccine_name}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to add immunization record: {e}")
            return False

    def add_growth_record(
        self,
        child_name: str,
        birth_date: str,
        record_date: str,
        age_months: int,
        weight_kg: Optional[float] = None,
        height_cm: Optional[float] = None,
        muac_cm: Optional[float] = None,
        head_circumference_cm: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Add a child growth monitoring record.

        Args:
            child_name: Name of the child.
            birth_date: Birth date in YYYY-MM-DD format.
            record_date: Date of measurement in YYYY-MM-DD format.
            age_months: Age in months at time of measurement.
            weight_kg: Weight in kilograms.
            height_cm: Height in centimeters.
            muac_cm: Mid-upper arm circumference in cm.
            head_circumference_cm: Head circumference in cm.
            notes: Additional notes.

        Returns:
            True if added successfully, False otherwise.
        """
        try:
            conn = self._get_connection()
            conn.execute(
                """INSERT INTO growth_records
                   (child_name, birth_date, record_date, age_months,
                    weight_kg, height_cm, muac_cm, head_circumference_cm, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (child_name, birth_date, record_date, age_months,
                 weight_kg, height_cm, muac_cm, head_circumference_cm, notes),
            )
            conn.commit()
            logger.debug(f"Growth record added for {child_name} at {age_months} months")
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to add growth record: {e}")
            return False

    def get_growth_history(self, child_name: str) -> List[Dict[str, Any]]:
        """Retrieve growth history for a child.

        Args:
            child_name: Name of the child.

        Returns:
            List of growth record dictionaries.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """SELECT * FROM growth_records WHERE child_name = ?
                   ORDER BY record_date DESC""",
                (child_name,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve growth history: {e}")
            return []

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.debug("Database connection closed")


# ============================================================================
# FIRST AID GUIDE
# ============================================================================

class FirstAidGuide:
    """Comprehensive first aid guide for common emergencies.

    Provides step-by-step first aid instructions for emergencies commonly
    encountered in African communities. All guidance follows WHO Emergency
    Care guidelines and basic life support protocols.

    Methods:
        get_first_aid: Get first aid steps for an emergency type.
        get_emergency_numbers: Get emergency contacts for a country.
        assess_urgency: Assess symptom urgency level.
        get_cpr_steps: Get CPR instructions.
    """

    # Emergency contact numbers for African countries
    # Format: country -> {service -> [numbers]}
    EMERGENCY_NUMBERS: Dict[str, Dict[str, List[str]]] = {
        "nigeria": {
            "ambulance": ["112", "199"],
            "police": ["112", "199"],
            "fire": ["112", "199"],
            "poison_control": ["0800-222-333"],
            "name": "Nigeria",
        },
        "south_africa": {
            "ambulance": ["10177", "112"],
            "police": ["10111", "112"],
            "fire": ["10177", "112"],
            "poison_control": ["0861-555-777"],
            "name": "South Africa",
        },
        "kenya": {
            "ambulance": ["999", "112"],
            "police": ["999", "112"],
            "fire": ["999", "112"],
            "name": "Kenya",
        },
        "ghana": {
            "ambulance": [ "193", "112", "999" ],
            "police": ["18555", "112", "999"],
            "fire": ["192", "112", "999"],
            "name": "Ghana",
        },
        "ethiopia": {
            "ambulance": ["907", "991"],
            "police": ["991", "112"],
            "fire": [["939"]],
            "name": "Ethiopia",
        },
        "uganda": {
            "ambulance": ["911", "112"],
            "police": ["999", "112"],
            "fire": ["999", "112"],
            "name": "Uganda",
        },
        "tanzania": {
            "ambulance": ["114", "112"],
            "police": ["999", "112"],
            "fire": ["115", "112"],
            "name": "Tanzania",
        },
        "rwanda": {
            "ambulance": ["912", "112"],
            "police": ["999", "112"],
            "fire": ["111", "112"],
            "name": "Rwanda",
        },
        "senegal": {
            "ambulance": ["15", "112"],
            "police": ["17", "112"],
            "fire": ["18", "112"],
            "name": "Senegal",
        },
        "ivory_coast": {
            "ambulance": ["185", "112"],
            "police": ["170", "112"],
            "fire": ["180", "112"],
            "name": "Ivory Coast (Cote d'Ivoire)",
        },
        "cameroon": {
            "ambulance": ["112"],
            "police": [["17"]],
            "fire": ["18", "112"],
            "name": "Cameroon",
        },
        "zambia": {
            "ambulance": ["991", "112"],
            "police": ["999", "112"],
            "fire": [["993"]],
            "name": "Zambia",
        },
        "zimbabwe": {
            "ambulance": [["994"]],
            "police": ["995", "112"],
            "fire": ["993", "112"],
            "name": "Zimbabwe",
        },
        "malawi": {
            "ambulance": ["998", "112"],
            "police": ["997", "112"],
            "fire": ["999", "112"],
            "name": "Malawi",
        },
        "mozambique": {
            "ambulance": ["117", "112"],
            "police": ["119", "112"],
            "fire": ["118", "112"],
            "name": "Mozambique",
        },
        "botswana": {
            "ambulance": [["997"], "112"],
            "police": ["999", "112"],
            "fire": ["998", "112"],
            "name": "Botswana",
        },
        "namibia": {
            "ambulance": ["211111", "112"],
            "police": ["10111", "112"],
            "fire": ["211111", "112"],
            "name": "Namibia",
        },
    }

    # First aid procedures by emergency type
    FIRST_AID_PROCEDURES: Dict[str, Dict[str, str]] = {
        "choking": {
            "title": "FIRST AID: CHOKING",
            "steps": """
1. ASSESS: Determine if the person can cough, speak, or breathe.
   - If coughing forcefully: Encourage them to keep coughing.
   - If unable to cough/speak/breathe: Act immediately.

2. FOR ADULTS AND CHILDREN OVER 1 YEAR:
   a) Stand behind the person and wrap your arms around their waist.
   b) Make a fist with one hand and place it just above the navel.
   c) Grasp your fist with the other hand.
   d) Give quick, upward abdominal thrusts (Heimlich maneuver).
   e) Repeat until the object is expelled or person becomes unconscious.

3. FOR INFANTS UNDER 1 YEAR:
   a) Sit and place the infant face-down on your forearm.
   b) Support the head and neck with your hand.
   c) Give 5 firm back blows between the shoulder blades.
   d) If still blocked, turn infant face-up and give 5 chest thrusts.
   e) Alternate back blows and chest thrusts until object is expelled.

4. IF PERSON BECOMES UNCONSCIOUS:
   a) Carefully lower them to the ground.
   b) Call emergency services immediately.
   c) Begin CPR if not breathing.

5. AFTER CARE:
   - Even if object is expelled, seek medical evaluation.
   - Check for any injury from the abdominal thrusts.
""",
        },
        "bleeding": {
            "title": "FIRST AID: SEVERE BLEEDING",
            "steps": """
1. PROTECT YOURSELF: Wear gloves if available, or use plastic bags.

2. APPLY DIRECT PRESSURE:
   a) Place a clean cloth, sterile dressing, or any clean fabric over the wound.
   b) Press firmly with both hands directly on the wound.
   c) Maintain pressure continuously for at least 10 minutes.
   d) Do NOT lift the dressing to check - this disrupts clotting.

3. IF BLEEDING DOES NOT STOP:
   a) Add more layers on top without removing the first layer.
   b) Apply a pressure bandage if available.
   c) Elevate the injured area above heart level if possible.

4. FOR LIMB INJURIES:
   a) Apply a tourniquet ONLY as last resort for life-threatening bleeding.
   b) Place tourniquet 5-10 cm above the wound, not over a joint.
   c) Tighten until bleeding stops. Note the time applied.
   d) Seek emergency care immediately - tourniquet must be removed by professionals.

5. SIGNS OF SHOCK (call emergency immediately):
   - Pale, cold, clammy skin
   - Rapid, weak pulse
   - Rapid breathing
   - Confusion or loss of consciousness
   - Dizziness or fainting

6. WHILE WAITING FOR HELP:
   - Keep the person lying down.
   - Cover with a blanket to maintain body temperature.
   - Do not give food or drink.
   - Reassure and keep calm.
""",
        },
        "burns": {
            "title": "FIRST AID: BURNS",
            "steps": """
1. ASSESS SEVERITY:
   - First degree (superficial): Red, painful, no blisters.
   - Second degree (partial thickness): Blisters, very painful.
   - Third degree (full thickness): White/charred, may be painless.
   - Electrical and chemical burns always need medical attention.

2. IMMEDIATE ACTION FOR THERMAL BURNS:
   a) Remove the person from the heat source.
   b) Cool the burn with cool (not cold) running water for 20 minutes.
   c) Remove jewelry and loose clothing near the burn (NOT stuck to skin).
   d) Do NOT apply ice, butter, oil, or traditional remedies.
   e) Do NOT break blisters.

3. COVER THE BURN:
   a) Cover with clean, non-stick cloth or sterile dressing.
   b) Do NOT use cotton wool or fluffy materials.
   c) Wrap loosely to avoid pressure on the burn.

4. FOR CHEMICAL BURNS:
   a) Brush off dry chemicals before washing.
   b) Flush with large amounts of running water for 20 minutes.
   c) Remove contaminated clothing while flushing.
   d) Seek emergency care immediately.

5. FOR ELECTRICAL BURNS:
   a) Do NOT touch the person if still in contact with electricity.
   b) Turn off power source first.
   c) Call emergency services - internal injuries may not be visible.
   d) Check breathing and pulse, begin CPR if needed.

6. BURN AREAS REQUIRING EMERGENCY CARE:
   - Face, hands, feet, genitals, or major joints
   - Burns larger than the person's palm
   - Third-degree burns
   - Burns in children or elderly
   - Burns with breathing difficulty
""",
        },
        "fractures": {
            "title": "FIRST AID: FRACTURES (BROKEN BONES)",
            "steps": """
1. RECOGNIZE SIGNS:
   - Deformity or unnatural angle
   - Swelling and bruising
   - Severe pain that worsens with movement
   - Inability to move or bear weight
   - Bone protruding through skin (open fracture)
   - Grating sound or feeling

2. CALL EMERGENCY IF:
   - Open fracture (bone visible)
   - Suspected skull, neck, or back fracture
   - Fracture with heavy bleeding
   - Person is unconscious or confused

3. IMMOBILIZE THE INJURED AREA:
   a) Do NOT try to straighten or realign the bone.
   b) Keep the injured area in the position found.
   c) Immobilize the joint above AND below the fracture.

4. CREATE A SPLINT:
   a) Use rigid materials: wooden sticks, rolled newspaper, cardboard.
   b) Pad the splint with cloth to prevent pressure sores.
   c) Secure splint with cloth strips, belts, or bandages.
   d) Do NOT tie directly over the fracture site.
   e) Check circulation below the splint (warmth, color, pulse).

5. FOR OPEN FRACTURES:
   a) Cover the wound with clean cloth or sterile dressing.
   b) Do NOT push bone back in.
   c) Do NOT attempt to clean the wound.
   d) Control bleeding with gentle pressure around the wound.

6. MANAGE PAIN AND SHOCK:
   - Keep person warm with a blanket.
   - Elevate legs slightly if no head/spinal injury.
   - Do not give food or drink (may need surgery).
   - Reassure and keep person calm.

7. TRANSPORT:
   - Use a stretcher or flat surface for spinal injuries.
   - Support the injured limb during transport.
   - Go to the nearest health facility immediately.
""",
        },
        "poisoning": {
            "title": "FIRST AID: POISONING",
            "steps": """
1. SCENE SAFETY: Ensure you are not also at risk of poisoning.

2. CALL EMERGENCY SERVICES IMMEDIATELY for:
   - Difficulty breathing
   - Drowsiness or unconsciousness
   - Seizures
   - Chemical burns around mouth
   - Suspected pesticide or chemical poisoning

3. GENERAL STEPS:
   a) Try to identify the poison - save container or sample.
   b) Check breathing and consciousness.
   c) If unconscious, place in recovery position.
   d) If not breathing, begin CPR.

4. IMPORTANT - DO NOT:
   - Do NOT give anything by mouth to an unconscious person.
   - Do NOT induce vomiting (especially for corrosive substances).
   - Do NOT give water or milk unless advised by poison control.
   - Do NOT try to neutralize the poison with other chemicals.

5. FOR INHALED POISONS:
   a) Move person to fresh air immediately.
   b) Open doors and windows.
   c) If unconscious, check breathing and begin CPR if needed.

6. FOR SKIN CONTACT:
   a) Remove contaminated clothing.
   b) Rinse skin with running water for 15-20 minutes.
   c) Wash gently with soap and water.

7. FOR EYE CONTACT:
   a) Hold eyelid open.
   b) Flush eye with clean water for 15-20 minutes.
   c) Roll eye around to wash all surfaces.
   d) Seek emergency care immediately.

8. COMMON POISONS IN AFRICA:
   - Pesticides (organophosphates): Extremely dangerous
   - Kerosene/paraffin: Do NOT induce vomiting
   - Medication overdose: Save pill bottles
   - Snake/spider venom: See snake bite protocol
   - Traditional medicine overdose: Bring sample to hospital
""",
        },
        "heatstroke": {
            "title": "FIRST AID: HEAT STROKE (HEAT EMERGENCY)",
            "steps": """
1. RECOGNIZE HEAT STROKE - MEDICAL EMERGENCY:
   - Body temperature above 40 C (104 F)
   - Hot, dry skin (or profuse sweating)
   - Confusion, agitation, or seizures
   - Loss of consciousness
   - Rapid, strong pulse
   - Nausea and vomiting
   - Headache
   - Note: Heat exhaustion is less severe but can progress to heat stroke.

2. CALL EMERGENCY SERVICES IMMEDIATELY.

3. COOL THE PERSON RAPIDLY:
   a) Move to shade or cool area immediately.
   b) Remove excess clothing.
   c) Apply cool water to skin - sponge or spray.
   d) Fan the person to increase evaporation.
   e) Place ice packs or cold cloths on neck, armpits, and groin.
   f) Immerse in cool water if available (bath, stream, basin).

4. IF CONSCIOUS:
   a) Give small sips of cool water or oral rehydration solution.
   b) Do NOT give alcohol, caffeine, or very cold drinks.
   c) Lie down and elevate legs slightly.

5. IF UNCONSCIOUS:
   a) Place in recovery position.
   b) Monitor breathing and pulse.
   c) Begin CPR if breathing stops.

6. PREVENTION IN HOT CLIMATES:
   - Stay hydrated - drink water regularly, even if not thirsty.
   - Rest in shade during hottest hours (11 AM - 3 PM).
   - Wear light-colored, loose-fitting clothing.
   - Avoid strenuous activity during peak heat.
   - Never leave children in closed vehicles.
   - Check on elderly neighbors during heat waves.
""",
        },
        "snake_bite": {
            "title": "FIRST AID: SNAKE BITE",
            "steps": """
1. CALL EMERGENCY SERVICES IMMEDIATELY.
   - Note: Some African snakes are highly venomous (mambas, cobras,
     puff adders, boomslangs). Treat ALL snake bites as serious.

2. KEEP CALM AND STILL:
   a) Panic increases heart rate and spreads venom faster.
   b) Keep the bitten person calm and reassured.
   c) Immobilize the person - do NOT let them walk.

3. POSITION:
   a) Keep the bitten limb at or below heart level.
   b) Do NOT elevate the limb.
   c) Keep the person lying down.

4. DO NOT:
   - Do NOT cut the wound or suck out venom.
   - Do NOT apply a tourniquet (unless specifically trained).
   - Do NOT apply ice or cold packs.
   - Do NOT give alcohol or caffeine.
   - Do NOT try to catch or kill the snake.
   - Do NOT wash the bite (venom residue helps identification).
   - Do NOT apply electric shock.
   - Do NOT use traditional remedies on the wound.

5. PRESSURE IMMOBILIZATION BANDAGE (Recommended):
   a) Apply firm pressure bandage over the bite site.
   b) Wrap bandage up the entire limb (like a sprain).
   c) Apply splint to immobilize the limb.
   d) Keep the bandage firm but not so tight it cuts circulation.
   e) Mark the location of the bite on the bandage.

6. MONITOR:
   - Watch for signs of envenomation: swelling, nausea, dizziness,
     difficulty breathing, bleeding, drooping eyelids.
   - Note the time of the bite.
   - Try to remember snake color, size, and shape for identification.

7. ANTIVENOM:
   - Only trained medical professionals should administer antivenom.
   - Transport to hospital with snake bite/antivenom capability.
""",
        },
        "drowning": {
            "title": "FIRST AID: DROWNING",
            "steps": """
1. ENSURE SCENE SAFETY:
   a) Do NOT enter the water if it puts you at risk.
   b) Throw a rope, pole, or flotation device to the person if possible.
   c) Call for help and emergency services.

2. REMOVE FROM WATER:
   a) Once safe to do so, get the person out of the water.
   b) If spinal injury suspected, keep head and neck supported.

3. CHECK FOR BREATHING:
   a) Open airway by tilting head back and lifting chin.
   b) Look, listen, and feel for breathing for 10 seconds.
   c) If breathing normally: Place in recovery position.
   d) If NOT breathing: Begin CPR immediately.

4. BEGIN CPR:
   a) Give 30 chest compressions (5-6 cm depth for adults).
   b) Give 2 rescue breaths (tilt head back, pinch nose).
   c) Continue 30:2 ratio until help arrives or person recovers.
   d) For children: Use one hand for compressions.
   e) For infants: Use two fingers for compressions.

5. IMPORTANT NOTES:
   - Vomiting is common - turn head to side to clear airway.
   - Do NOT stop CPR to drain water.
   - Continue CPR until medical help takes over.
   - Even if person recovers, they MUST go to hospital.
   - Secondary drowning can occur hours later.

6. AFTER RESUSCITATION:
   - Keep person warm (remove wet clothing, cover with dry blanket).
   - Monitor breathing continuously.
   - Watch for signs of secondary drowning:
     * Difficulty breathing hours later
     * Persistent cough
     * Unusual fatigue
     * Behavioral changes
""",
        },
        "cpr": {
            "title": "FIRST AID: CPR (CARDIOPULMONARY RESUSCITATION)",
            "steps": """
1. CHECK RESPONSIVENESS:
   a) Tap the person's shoulder and shout "Are you OK?"
   b) If no response, call for emergency help immediately.
   c) If others are present, send someone to call emergency services.

2. CHECK BREATHING:
   a) Open airway: tilt head back, lift chin.
   b) Look, listen, and feel for normal breathing for 10 seconds.
   c) Occasional gasps are NOT normal breathing - begin CPR.

3. FOR ADULTS (8 years and older):
   a) Place heel of one hand on center of chest (lower half of breastbone).
   b) Place heel of other hand on top, interlock fingers.
   c) Keep arms straight, shoulders directly over hands.
   d) Compress at least 5 cm deep (but not more than 6 cm).
   e) Compress at rate of 100-120 per minute.
   f) Allow chest to fully recoil between compressions.
   g) Give 30 compressions, then 2 rescue breaths.
   h) Continue 30:2 ratio.

4. RESCUE BREATHS:
   a) Open airway (head tilt, chin lift).
   b) Pinch the nose shut.
   c) Take a normal breath and seal your mouth over theirs.
   d) Give 2 breaths, each lasting about 1 second.
   e) Watch for chest rise.
   f) If chest doesn't rise, re-tilt head and try again.

5. FOR CHILDREN (1-8 years):
   a) Use one hand for compressions.
   b) Compress about 5 cm deep (one-third of chest depth).
   c) Same 30:2 ratio if alone.
   d) If two rescuers: use 15:2 ratio.

6. FOR INFANTS (under 1 year):
   a) Use two fingers in center of chest.
   b) Compress about 4 cm deep (one-third of chest depth).
   c) Same 30:2 ratio if alone.
   d) For rescue breaths: cover both nose and mouth with your mouth.

7. CONTINUE CPR:
   - Do NOT stop until:
     a) Emergency services take over.
     b) Person shows signs of life.
     c) You are physically unable to continue.
     d) An AED is available and tells you to stop.

8. IF AED AVAILABLE:
   a) Turn on AED and follow voice prompts.
   b) Attach pads as shown on diagrams.
   c) Ensure no one touches person during analysis/shock.
   d) Resume CPR immediately after shock.
""",
        },
    }

    # Red flag symptoms requiring immediate care
    RED_FLAG_SYMPTOMS: Dict[str, UrgencyLevel] = {
        "cannot breathe": UrgencyLevel.CRITICAL,
        "difficulty breathing": UrgencyLevel.CRITICAL,
        "chest pain": UrgencyLevel.CRITICAL,
        "severe bleeding": UrgencyLevel.CRITICAL,
        "unconscious": UrgencyLevel.CRITICAL,
        "not responding": UrgencyLevel.CRITICAL,
        "seizure": UrgencyLevel.CRITICAL,
        "severe headache": UrgencyLevel.URGENT,
        "stiff neck": UrgencyLevel.URGENT,
        "high fever": UrgencyLevel.URGENT,
        "severe abdominal pain": UrgencyLevel.URGENT,
        "unable to urinate": UrgencyLevel.URGENT,
        "blood in stool": UrgencyLevel.URGENT,
        "blood in urine": UrgencyLevel.URGENT,
        "blood in vomit": UrgencyLevel.URGENT,
        "severe dehydration": UrgencyLevel.URGENT,
        "swollen face": UrgencyLevel.URGENT,
        "rash with fever": UrgencyLevel.URGENT,
        "severe burns": UrgencyLevel.CRITICAL,
        "snake bite": UrgencyLevel.CRITICAL,
        "broken bone": UrgencyLevel.URGENT,
        "eye injury": UrgencyLevel.URGENT,
        "severe allergic reaction": UrgencyLevel.CRITICAL,
        "difficulty swallowing": UrgencyLevel.URGENT,
        "confusion": UrgencyLevel.URGENT,
        "fainting": UrgencyLevel.URGENT,
        "rapid heartbeat": UrgencyLevel.URGENT,
        "blue lips": UrgencyLevel.CRITICAL,
        "blue fingers": UrgencyLevel.CRITICAL,
        "severe vomiting": UrgencyLevel.URGENT,
        "severe diarrhea": UrgencyLevel.URGENT,
        "convulsions": UrgencyLevel.CRITICAL,
        "persistent crying": UrgencyLevel.URGENT,
        "bulging fontanelle": UrgencyLevel.CRITICAL,
        "stiff neck": UrgencyLevel.CRITICAL,
    }

    def __init__(self) -> None:
        """Initialize the FirstAidGuide."""
        self.db = HealthRecordDB()
        logger.debug("FirstAidGuide initialized")

    def get_first_aid(self, emergency_type: str) -> str:
        """Get first aid steps for a specific emergency type.

        Args:
            emergency_type: Type of emergency. Options include:
                'choking', 'bleeding', 'burns', 'fractures',
                'poisoning', 'heatstroke', 'snake_bite', 'drowning', 'cpr'.

        Returns:
            Formatted first aid instructions with medical disclaimer.

        Raises:
            ValueError: If emergency_type is not recognized.
        """
        emergency_type = emergency_type.lower().strip().replace(" ", "_")
        
        # Normalize common variations
        aliases = {
            "burn": "burns",
            "heat stroke": "heatstroke",
            "heat_stroke": "heatstroke",
            "snakebite": "snake_bite",
            "snake bite": "snake_bite",
            "broken bone": "fractures",
            "broken_bone": "fractures",
            "break": "fractures",
        }
        emergency_type = aliases.get(emergency_type, emergency_type)

        if emergency_type not in self.FIRST_AID_PROCEDURES:
            available = ", ".join(self.FIRST_AID_PROCEDURES.keys())
            result = (
                f"Unknown emergency type: '{emergency_type}'.\n\n"
                f"Available emergency types: {available}\n\n"
                f"For any emergency, call your local emergency number immediately."
            )
            return MedicalDisclaimer.wrap(result, "emergency")

        procedure = self.FIRST_AID_PROCEDURES[emergency_type]
        result = f"{procedure['title']}\n{'=' * len(procedure['title'])}\n{procedure['steps']}"
        
        self.db.log_query(f"first_aid: {emergency_type}", "first_aid")
        return MedicalDisclaimer.wrap(result, "emergency")

    def get_emergency_numbers(self, country: str) -> str:
        """Get emergency contact numbers for an African country.

        Args:
            country: Country name (e.g., 'nigeria', 'south_africa', 'kenya').

        Returns:
            Formatted emergency numbers with disclaimer.
        """
        country = country.lower().strip().replace(" ", "_")
        
        # Normalize common variations
        aliases = {
            "sa": "south_africa",
            "rsa": "south_africa",
            "cote_divoire": "ivory_coast",
            "cote_d_ivoire": "ivory_coast",
        }
        country = aliases.get(country, country)

        if country not in self.EMERGENCY_NUMBERS:
            countries_list = ", ".join(
                info["name"] for info in self.EMERGENCY_NUMBERS.values()
            )
            result = (
                f"Emergency numbers not available for '{country}'.\n\n"
                f"Available countries: {countries_list}\n\n"
                f"General Emergency: Try 112 (works in many African countries)\n"
                f"For any emergency, contact your local hospital or police station."
            )
            return MedicalDisclaimer.wrap(result, "emergency")

        info = self.EMERGENCY_NUMBERS[country]
        lines = [f"Emergency Numbers - {info['name']}", "=" * 40]
        
        for service, numbers in info.items():
            if service == "name":
                continue
            service_name = service.replace("_", " ").title()
            num_str = ", ".join(str(n) for n in numbers)
            lines.append(f"{service_name}: {num_str}")
        
        lines.append("\nNOTE: 112 is the universal emergency number in many countries.")
        lines.append("If numbers don't work, go directly to the nearest hospital.")
        
        self.db.log_query(f"emergency_numbers: {country}", "first_aid")
        return MedicalDisclaimer.wrap("\n".join(lines), "emergency")

    def assess_urgency(self, symptoms: Union[str, List[str]]) -> str:
        """Assess the urgency level of symptoms.

        Args:
            symptoms: A symptom string or list of symptom strings.

        Returns:
            Urgency assessment with recommended action and disclaimer.
        """
        if isinstance(symptoms, str):
            symptoms = [symptoms]

        symptoms_lower = [s.lower().strip() for s in symptoms]
        matched_flags: List[Tuple[str, UrgencyLevel]] = []

        for symptom in symptoms_lower:
            for flag, level in self.RED_FLAG_SYMPTOMS.items():
                if flag in symptom or symptom in flag:
                    matched_flags.append((flag, level))

        if not matched_flags:
            result = (
                "Symptom Urgency Assessment\n"
                "========================\n\n"
                f"Symptoms: {', '.join(symptoms)}\n\n"
                "No critical red flags detected based on the symptoms provided.\n\n"
                "Urgency Level: MODERATE to LOW\n\n"
                "Recommendation:\n"
                "- Monitor symptoms closely\n"
                "- If symptoms worsen or new symptoms appear, seek medical care\n"
                "- Schedule a routine medical appointment if symptoms persist\n"
                "- For infants, elderly, or pregnant women, seek care sooner\n"
            )
            self.db.log_query(f"assess_urgency: {symptoms}", "first_aid")
            return MedicalDisclaimer.wrap(result, "standard")

        # Determine highest urgency
        urgency_order = {
            UrgencyLevel.CRITICAL: 4,
            UrgencyLevel.URGENT: 3,
            UrgencyLevel.MODERATE: 2,
            UrgencyLevel.LOW: 1,
        }
        highest = max(matched_flags, key=lambda x: urgency_order.get(x[1], 0))

        critical_flags = [f[0] for f in matched_flags if f[1] == UrgencyLevel.CRITICAL]
        urgent_flags = [f[0] for f in matched_flags if f[1] == UrgencyLevel.URGENT]

        lines = [
            "Symptom Urgency Assessment",
            "========================",
            "",
            f"Symptoms reported: {', '.join(symptoms)}",
            "",
            f"Overall Urgency: {highest[1].value}",
            "",
        ]

        if critical_flags:
            lines.append("CRITICAL RED FLAGS DETECTED:")
            for flag in critical_flags:
                lines.append(f"  - {flag}")
            lines.append("")

        if urgent_flags:
            lines.append("URGENT SIGNS DETECTED:")
            for flag in urgent_flags:
                lines.append(f"  - {flag}")
            lines.append("")

        if highest[1] == UrgencyLevel.CRITICAL:
            lines.append("ACTION REQUIRED:")
            lines.append("- Seek emergency medical care IMMEDIATELY")
            lines.append("- Call your local emergency number")
            lines.append("- Do NOT wait or try to manage at home")
            lines.append("- If possible, have someone accompany you")
        elif highest[1] == UrgencyLevel.URGENT:
            lines.append("ACTION REQUIRED:")
            lines.append("- Seek medical care within 24 hours")
            lines.append("- Contact a healthcare provider today")
            lines.append("- Monitor for any worsening")
        else:
            lines.append("ACTION REQUIRED:")
            lines.append("- Schedule a medical appointment soon")
            lines.append("- Monitor symptoms")

        self.db.log_query(f"assess_urgency: {symptoms}", "first_aid")
        return MedicalDisclaimer.wrap("\n".join(lines), "emergency")



# ============================================================================
# MATERNAL HEALTH GUIDE
# ============================================================================

class MaternalHealthGuide:
    """Comprehensive maternal health guide for pregnancy and postpartum care.

    Provides evidence-based guidance following WHO guidelines for antenatal care,
    childbirth preparation, postnatal care, and newborn care. Tailored for
    African contexts with locally relevant recommendations.

    Methods:
        get_prenatal_care: Week-by-week pregnancy guidance.
        get_danger_signs_pregnancy: Emergency warning signs during pregnancy.
        get_childbirth_prep: Signs of labor and delivery preparation.
        get_postnatal_care: Postpartum recovery guidance.
        get_newborn_care: Essential newborn care instructions.
    """

    # Week-by-week prenatal care guidance
    PRENATAL_CARE: Dict[int, Dict[str, str]] = {
        1: {
            "title": "Weeks 1-4: Early Pregnancy",
            "body": """
- Confirm pregnancy with a home test or clinic visit.
- Start taking folic acid (400 mcg daily) if not already.
- Stop smoking, alcohol, and any non-prescribed drugs.
- Schedule your first prenatal appointment.
- Begin eating a balanced, nutritious diet.
- Stay hydrated - drink at least 8 glasses of clean water daily.
- Get adequate rest and sleep (8 hours per night).
- Avoid raw or undercooked meat, fish, and eggs.
- Limit caffeine intake.
- Start a pregnancy journal to track symptoms and appointments.
""",
        },
        5: {
            "title": "Weeks 5-8: First Trimester",
            "body": """
- Morning sickness may begin - eat small, frequent meals.
- Continue folic acid supplementation daily.
- First ultrasound may be done to confirm pregnancy.
- Begin iron supplements if prescribed by your healthcare provider.
- Eat foods rich in iron: leafy greens, beans, red meat (if available).
- Avoid strenuous physical activity.
- Attend first antenatal care (ANC) visit.
- Get tested for HIV, syphilis, hepatitis B, and blood group.
- Check blood pressure and urine protein.
- Take malaria prophylaxis if recommended in your area (IPTp).
""",
        },
        9: {
            "title": "Weeks 9-12: End of First Trimester",
            "body": """
- Nausea may start to improve for some women.
- Continue regular ANC visits (at least 4 visits during pregnancy).
- Eat protein-rich foods: beans, eggs, fish, chicken, nuts.
- Continue iron and folic acid supplements.
- Stay active with light walking (if no complications).
- Avoid heavy lifting and prolonged standing.
- Get screened for gestational diabetes if at risk.
- Discuss family planning for after delivery.
- Ensure adequate calcium intake: dairy, leafy greens, small fish with bones.
- Rest when tired - your body is working hard.
""",
        },
        13: {
            "title": "Weeks 13-16: Second Trimester Begins",
            "body": """
- Most women feel better during the second trimester.
- You may begin to show a baby bump.
- Continue balanced nutrition - increase calories by about 340/day.
- Eat iron-rich foods: dark leafy greens (moringa, spinach), liver, beans.
- Continue daily iron and folic acid supplements.
- Stay physically active with moderate exercise like walking.
- Drink plenty of clean, safe water throughout the day.
- Attend ANC visit for weight, blood pressure, and urine checks.
- Ask about tetanus toxoid vaccination if not already given.
- Sleep on your side (left side preferred) to improve circulation.
""",
        },
        17: {
            "title": "Weeks 17-20: Mid-Pregnancy",
            "body": """
- You may feel the baby move (quickening) around week 18-20.
- Second ultrasound may be offered to check baby development.
- Continue eating nutrient-dense foods.
- Increase protein intake: eggs, beans, fish, meat, groundnuts.
- Take deworming medication if prescribed by your provider.
- Continue iron and folic acid supplements daily.
- Monitor weight gain (average 0.5-1 kg per week).
- Practice good posture to reduce back pain.
- Wear comfortable, supportive clothing and footwear.
- Continue ANC visits every 4 weeks.
""",
        },
        21: {
            "title": "Weeks 21-24: Viability Milestone",
            "body": """
- Baby's movements become more regular - monitor daily.
- Continue balanced diet with extra protein and calcium.
- Eat calcium-rich foods: milk, yogurt, okra, leafy greens.
- Get tested for anemia (Hb check) at ANC visit.
- If anemic, increase iron-rich foods and supplements.
- Sleep on your left side to improve blood flow to the baby.
- Use pillows for support while sleeping.
- Stay hydrated - aim for 10 glasses of water daily.
- Watch for swelling in hands, feet, or face (report to provider).
- Continue regular ANC monitoring.
""",
        },
        25: {
            "title": "Weeks 25-28: Third Trimester Approaches",
            "body": """
- You may experience heartburn - eat smaller, more frequent meals.
- Continue iron supplements (especially important in third trimester).
- Monitor baby's movements daily - should feel regular movements.
- Get screened for gestational diabetes if not already done.
- Continue calcium-rich foods for baby's bone development.
- Rest frequently - take naps during the day.
- Avoid lying flat on your back.
- Prepare for childbirth: identify facility and transport plan.
- Pack a bag with essentials for hospital/clinic.
- Save money for delivery expenses.
""",
        },
        29: {
            "title": "Weeks 29-32: Third Trimester",
            "body": """
- Baby grows rapidly - continue nutrient-rich diet.
- Increase food intake by about 450 calories daily.
- Continue iron and folic acid until delivery.
- Take second dose of IPTp for malaria prevention (if applicable).
- Sleep may become difficult - use pillows for comfort.
- Practice breathing exercises and relaxation techniques.
- Continue regular movement and light exercise.
- Prepare for breastfeeding: learn proper latch technique.
- Attend ANC visits every 2 weeks now.
- Discuss birth plan with healthcare provider.
""",
        },
        33: {
            "title": "Weeks 33-36: Preparing for Birth",
            "body": """
- Pack your delivery bag: clean clothes, pads, baby clothes, soap.
- Arrange transport to the health facility.
- Continue eating well - baby is gaining weight rapidly.
- Stay hydrated and rest as much as possible.
- Monitor for signs of pre-eclampsia: severe headache, vision changes,
  upper abdominal pain, sudden swelling.
- Take third dose of IPTp (if applicable).
- Ensure birth companion is identified and informed.
- Know the danger signs that require immediate care.
- Keep emergency numbers easily accessible.
- Attend ANC visits weekly or as advised.
""",
        },
        37: {
            "title": "Weeks 37-40: Full Term",
            "body": """
- Baby is considered full term - can be born safely anytime.
- Be ready to go to the facility at any moment.
- Continue monitoring baby's movements.
- Rest as much as possible - conserve energy for labor.
- Eat light, easily digestible meals.
- Practice breathing and relaxation exercises daily.
- Keep your delivery bag ready and accessible.
- Ensure transport plan is confirmed.
- Stay near your chosen health facility if possible.
- Know the signs of labor (see get_childbirth_prep).
""",
        },
    }

    # Danger signs during pregnancy
    DANGER_SIGNS: Dict[str, Dict[str, str]] = {
        "vaginal_bleeding": {
            "sign": "Vaginal bleeding at any time during pregnancy",
            "action": "Go to hospital IMMEDIATELY. Any bleeding during pregnancy is abnormal.",
            "urgency": "CRITICAL",
        },
        "severe_headache": {
            "sign": "Severe headache that does not go away with rest",
            "action": "Go to hospital immediately. May indicate pre-eclampsia.",
            "urgency": "CRITICAL",
        },
        "blurred_vision": {
            "sign": "Blurred vision, spots before eyes, or sudden vision changes",
            "action": "Go to hospital immediately. Sign of pre-eclampsia.",
            "urgency": "CRITICAL",
        },
        "severe_abdominal_pain": {
            "sign": "Severe pain in the upper abdomen or stomach",
            "action": "Go to hospital immediately. Could indicate liver problems or other complications.",
            "urgency": "CRITICAL",
        },
        "swelling": {
            "sign": "Swelling of face, hands, or feet (sudden or severe)",
            "action": "Go to hospital immediately. May indicate pre-eclampsia.",
            "urgency": "CRITICAL",
        },
        "fever": {
            "sign": "High fever (above 38 C / 100.4 F)",
            "action": "Seek medical care urgently. Could indicate infection or malaria.",
            "urgency": "URGENT",
        },
        "decreased_fetal_movement": {
            "sign": "Baby moving much less than usual or not moving",
            "action": "Go to hospital immediately. Baby may be in distress.",
            "urgency": "CRITICAL",
        },
        "water_breaking": {
            "sign": "Water breaks before 37 weeks (premature rupture)",
            "action": "Go to hospital immediately. Risk of infection and premature delivery.",
            "urgency": "CRITICAL",
        },
        "severe_vomiting": {
            "sign": "Severe vomiting, unable to keep any food or fluids down",
            "action": "Seek medical care urgently. Risk of severe dehydration.",
            "urgency": "URGENT",
        },
        "convulsions": {
            "sign": "Fits, convulsions, or seizures",
            "action": "EMERGENCY. Go to hospital immediately. Sign of eclampsia.",
            "urgency": "CRITICAL",
        },
        "reduced_urine": {
            "sign": "Passing very little or no urine",
            "action": "Seek medical care urgently. May indicate kidney problems or dehydration.",
            "urgency": "URGENT",
        },
        "breathing_difficulty": {
            "sign": "Difficulty breathing or shortness of breath",
            "action": "Seek medical care urgently. Could indicate anemia or other complications.",
            "urgency": "URGENT",
        },
        "severe_itching": {
            "sign": "Severe itching, especially of palms and soles",
            "action": "Seek medical care. May indicate liver condition (cholestasis).",
            "urgency": "MODERATE",
        },
    }

    # Childbirth preparation information
    CHILDBIRTH_PREP: Dict[str, str] = {
        "signs_of_labor": """
SIGNS THAT LABOR IS STARTING:

1. Regular Contractions:
   - Contractions become regular, stronger, and closer together.
   - True labor contractions don't go away with rest or change of position.
   - Time contractions: note start time and duration.
   - Go to facility when contractions are 5 minutes apart.

2. Water Breaking:
   - A gush or trickle of fluid from the vagina.
   - Note the color: should be clear or slightly pink.
   - If green/brown or foul-smelling, go to facility immediately.
   - If water breaks but labor hasn't started, still go to facility.

3. Bloody Show:
   - Mucus plug dislodges - may be tinged with blood.
   - Normal sign that cervix is dilating.
   - If heavy bleeding, go to facility immediately.

4. Back Pain:
   - Persistent lower back pain that comes and goes rhythmically.
   - May be a sign of labor, especially in some women.
""",
        "preparation": """
PREPARING FOR DELIVERY:

1. Choose Your Birth Facility:
   - Visit the health center or hospital before delivery.
   - Know the route and travel time.
   - Ensure facility has skilled birth attendants.

2. Arrange Transport:
   - Have a reliable transport plan (neighbor with vehicle, motorcycle,
     ambulance number saved).
   - Save emergency transport money in a safe place.

3. Pack Your Delivery Bag:
   - Clean clothes for mother and baby.
   - Sanitary pads (cloth or disposable).
   - Baby blankets and warm clothes.
   - Soap and clean water container.
   - Any ANC cards or documents.
   - Snacks and drinks for labor.
   - Plastic sheet or clean mat.

4. Identify a Birth Companion:
   - Choose someone who can accompany you.
   - They should know your health history.
   - They can help advocate for you at the facility.

5. Save for Delivery Costs:
   - Set aside money for facility fees, transport, and medications.
   - Community health insurance schemes may be available.

6. Know the Danger Signs:
   - Review danger signs requiring immediate transfer.
   - Have emergency numbers readily available.
""",
    }

    # Postnatal care by week
    POSTNATAL_CARE: Dict[int, Dict[str, str]] = {
        1: {
            "title": "First Week Postpartum",
            "body": """
MOTHER'S RECOVERY:
- Rest as much as possible. Sleep when the baby sleeps.
- Eat nutritious foods to aid recovery and milk production.
- Drink plenty of fluids, especially water and warm drinks.
- Take prescribed iron supplements for at least 6 months.
- Keep the perineal area clean - wash with clean water daily.
- Watch for signs of infection: fever, foul-smelling discharge, severe pain.
- Mild cramping (afterpains) is normal as uterus shrinks.
- Some vaginal bleeding (lochia) is normal - should gradually decrease.

BREASTFEEDING:
- Breastfeed within the first hour after birth if possible.
- Feed on demand - at least 8-12 times per day.
- Ensure proper latch: baby should have most of the areola in mouth.
- Offer both breasts at each feeding.
- Drink plenty of fluids to support milk production.
- Seek help if you have breast pain, cracking, or difficulty.

WARNING SIGNS - Go to facility immediately if:
- Heavy bleeding (soaking a pad in an hour)
- Fever above 38 C
- Severe abdominal pain
- Foul-smelling vaginal discharge
- Severe headaches or vision changes
- Painful, red, or swollen breasts with fever
- Difficulty breathing
- Severe depression or thoughts of self-harm
""",
        },
        2: {
            "title": "Week 2 Postpartum",
            "body": """
- Continue breastfeeding on demand.
- Gradually increase light activity as tolerated.
- Continue eating iron-rich foods and taking supplements.
- Vaginal bleeding should be decreasing (turning pink/brown).
- Continue perineal hygiene.
- Check healing of any tears or episiotomy.
- Begin gentle walking when feeling up to it.
- Avoid heavy lifting and strenuous activity.
- Rest remains very important.
- Schedule postnatal check-up if not already done.
""",
        },
        6: {
            "title": "Weeks 3-6 Postpartum",
            "body": """
- By week 6, most bleeding should have stopped.
- Continue exclusive breastfeeding for 6 months.
- Attend postnatal check-up around 6 weeks.
- Discuss family planning options with your provider.
- Gradually resume normal activities.
- Continue iron supplements.
- Monitor mood - some sadness is normal (baby blues).
- If persistent sadness, anxiety, or hopelessness, seek help.
- Begin gentle exercises like walking.
- Eat a balanced diet for energy and recovery.
""",
        },
        12: {
            "title": "3 Months Postpartum",
            "body": """
- Continue breastfeeding (exclusive for 6 months, then with complementary foods).
- Should be feeling more energetic by now.
- Continue family planning as discussed with provider.
- Monitor baby's growth and development.
- Ensure baby receives all scheduled immunizations.
- Take care of your mental health - seek support if needed.
- Maintain a balanced diet.
- Continue regular physical activity.
""",
        },
    }

    # Newborn care essentials
    NEWBORN_CARE: Dict[str, str] = {
        "immediate": """
IMMEDIATE NEWBORN CARE (First Hour):

1. Keep Warm:
   - Dry the baby immediately with a clean, warm cloth.
   - Place baby on mother's chest (skin-to-skin contact).
   - Cover both with a clean, warm blanket.
   - Delay bathing for at least 24 hours.

2. Clearing Airway:
   - Wipe baby's mouth and nose with clean cloth if needed.
   - Baby should start breathing and crying within a few seconds.
   - If not breathing, stimulate by rubbing back firmly.

3. Cord Care:
   - Tie cord with clean string or clamp about 2-3 cm from belly.
   - Cut with clean, sharp blade or scissors (sterilized with boiling water).
   - Do NOT apply anything to the cord stump (no ash, cow dung, herbs).
   - Keep cord clean and dry.
   - Fold diaper below cord stump.
   - Watch for signs of infection: redness, swelling, foul smell, pus.

4. Initiate Breastfeeding:
   - Put baby to breast within first hour.
   - Colostrum (first milk) is rich in antibodies - very important.
   - Feed on demand day and night.

5. Identification:
   - Weigh the baby.
   - Note birth time and date.
""",
        "feeding": """
BREASTFEEDING GUIDANCE:

1. Exclusive Breastfeeding:
   - Only breast milk for the first 6 months - no water, formula, or other foods.
   - Feed 8-12 times per day, including at night.
   - Feed on demand - whenever baby shows hunger cues.

2. Hunger Cues:
   - Rooting (turning head, opening mouth).
   - Sucking on hands or fingers.
   - Becoming more alert and active.
   - Crying is a late hunger cue.

3. Proper Latching:
   - Baby's mouth should cover most of the areola.
   - Lips should be flanged outward.
   - Chin should touch the breast.
   - You should hear swallowing sounds.
   - Should not be painful after initial latch.

4. Signs Baby is Getting Enough Milk:
   - 6+ wet diapers per day after day 5.
   - Regular bowel movements.
   - Steady weight gain.
   - Baby seems satisfied after feeding.
   - Breasts feel softer after feeding.

5. Common Breastfeeding Problems:
   - Sore nipples: Check latch, express milk and rub on nipples.
   - Engorgement: Feed frequently, express milk, warm compress.
   - Blocked duct: Massage toward nipple, continue nursing.
   - Mastitis (breast infection): Red, hot, painful area with fever - seek care.
""",
        "hygiene": """
NEWBORN HYGIENE:

1. Bathing:
   - Delay first bath for at least 24 hours (WHO recommendation).
   - After 24 hours, sponge bath daily with warm water.
   - Use mild soap only on hands, bottom, and skin folds.
   - Keep bath short (5 minutes) to prevent getting cold.
   - Dry thoroughly and dress warmly immediately.

2. Cord Care:
   - Keep cord stump clean and dry.
   - Fold diaper below cord.
   - Watch for infection: redness, swelling, pus, foul smell.
   - Cord falls off naturally in 1-2 weeks.

3. Diaper/Nappy Care:
   - Change frequently to prevent diaper rash.
   - Clean with water and mild soap.
   - Allow skin to air dry when possible.
   - Apply petroleum jelly or zinc oxide cream if rash develops.

4. Clothing:
   - Dress baby in one more layer than you would wear.
   - Keep head covered in cool weather.
   - Use soft, clean fabrics.
   - Avoid overheating - baby should not be sweaty.
""",
        "warning_signs": """
NEWBORN DANGER SIGNS - SEEK CARE IMMEDIATELY:

1. FEEDING PROBLEMS:
   - Unable to feed or refusing to feed.
   - Vomiting everything.
   - Not breastfeeding at all.

2. BREATHING PROBLEMS:
   - Fast breathing (more than 60 breaths per minute).
   - Severe chest indrawing (chest pulls in with each breath).
   - Grunting sounds.
   - Blue lips or tongue.

3. TEMPERATURE:
   - Fever (above 37.5 C / 99.5 F).
   - Low body temperature (below 35.5 C / 95.9 F).
   - Cold to touch with lethargy.

4. ACTIVITY:
   - Lethargy or reduced movement.
   - Unconscious or not responding.
   - Convulsions or fits.
   - Irritable, high-pitched crying.

5. SKIN:
   - Yellow skin or eyes (jaundice) spreading to limbs.
   - Severe skin infection, boils, or abscesses.
   - Pustules or blisters.

6. UMBILICAL CORD:
   - Redness spreading from cord stump.
   - Foul-smelling discharge from cord.
   - Pus at base of cord.

7. WEIGHT:
   - Not gaining weight.
   - Losing weight after the first week.

8. OTHER:
   - Blood in stool.
   - Bulging fontanelle (soft spot on head).
   - Severe diarrhea.
""",
    }

    def __init__(self) -> None:
        """Initialize the MaternalHealthGuide."""
        self.db = HealthRecordDB()
        logger.debug("MaternalHealthGuide initialized")

    def get_prenatal_care(self, week: int) -> str:
        """Get week-by-week pregnancy guidance.

        Args:
            week: Current week of pregnancy (1-40).

        Returns:
            Prenatal care guidance for the specified week with disclaimer.
        """
        if not isinstance(week, int) or week < 1 or week > 42:
            result = (
                "Please provide a valid pregnancy week (1-42).\n"
                "Pregnancy typically lasts 37-42 weeks.\n"
                "Enter your current week number to get personalized guidance."
            )
            return MedicalDisclaimer.wrap(result, "pregnancy")

        # Find the closest guidance block
        available_weeks = sorted(self.PRENATAL_CARE.keys())
        selected_week = max(w for w in available_weeks if w <= week)

        info = self.PRENATAL_CARE[selected_week]
        header = f"Prenatal Care Guidance - {info['title']}"
        result = f"{header}\n{'=' * len(header)}\nYou are in week {week} of pregnancy.\n{info['body']}"
        
        # Add week-specific reminders
        if week >= 37:
            result += "\nYou are at full term. Be prepared to go to the facility at any time!\n"

        self.db.log_query(f"prenatal_care: week {week}", "maternal")
        return MedicalDisclaimer.wrap(result, "pregnancy")

    def get_danger_signs_pregnancy(self) -> str:
        """Get danger signs during pregnancy requiring emergency care.

        Returns:
            List of danger signs with actions and disclaimer.
        """
        lines = [
            "PREGNANCY DANGER SIGNS",
            "=====================",
            "",
            "Seek IMMEDIATE medical care if you experience ANY of these signs:",
            "",
        ]

        for key, info in self.DANGER_SIGNS.items():
            lines.append(f"{info['sign']}")
            lines.append(f"  Urgency: {info['urgency']}")
            lines.append(f"  Action: {info['action']}")
            lines.append("")

        lines.extend([
            "Remember: It is always better to seek care and be told everything",
            "is fine than to wait too long. Your life and your baby's life",
            "depend on quick action when danger signs appear.",
            "",
            "Attend ALL scheduled antenatal care visits.",
            "Know your emergency transport plan.",
            "Keep emergency numbers saved on your phone.",
        ])

        self.db.log_query("danger_signs_pregnancy", "maternal")
        return MedicalDisclaimer.wrap("\n".join(lines), "pregnancy")

    def get_childbirth_prep(self) -> str:
        """Get signs of labor and delivery preparation guidance.

        Returns:
            Childbirth preparation information with disclaimer.
        """
        lines = [
            "CHILDBIRTH PREPARATION GUIDE",
            "===========================",
            "",
        ]

        for key, content in self.CHILDBIRTH_PREP.items():
            lines.append(content)
            lines.append("")

        lines.extend([
            "DANGER SIGNS DURING LABOR - Go to facility immediately:",
            "- Heavy vaginal bleeding",
            "- Severe, continuous abdominal pain",
            "- Baby stops moving",
            "- Green or brown amniotic fluid",
            "- Fever during labor",
            "- Severe headache or visual disturbances",
            "- Prolonged labor (more than 12 hours for first baby)",
            "",
            "DELIVERY AT A HEALTH FACILITY is the safest option.",
            "Skilled birth attendants can manage complications",
            "that may arise during delivery.",
        ])

        self.db.log_query("childbirth_prep", "maternal")
        return MedicalDisclaimer.wrap("\n".join(lines), "pregnancy")

    def get_postnatal_care(self, week: int) -> str:
        """Get postpartum recovery guidance.

        Args:
            week: Number of weeks since delivery.

        Returns:
            Postnatal care guidance with disclaimer.
        """
        if week < 1 or week > 52:
            result = (
                "Please provide a valid postpartum week (1-52).\n"
                "The postpartum period covers the first year after delivery."
            )
            return MedicalDisclaimer.wrap(result, "pregnancy")

        available_weeks = sorted(self.POSTNATAL_CARE.keys())
        selected_week = max(w for w in available_weeks if w <= week)

        info = self.POSTNATAL_CARE[selected_week]
        header = f"Postnatal Care - {info['title']}"
        result = f"{header}\n{'=' * len(header)}\nYou are {week} week(s) postpartum.\n{info['body']}"

        # Add general advice
        result += """

GENERAL POSTNATAL ADVICE:
- Accept help from family and friends.
- Rest whenever the baby sleeps.
- Eat a balanced diet to support recovery and breastfeeding.
- Continue taking iron supplements.
- Stay hydrated.
- Watch your mental health - seek help if feeling overwhelmed.
- Attend all postnatal check-ups.
- Begin family planning discussions before resuming sexual activity.
"""

        self.db.log_query(f"postnatal_care: week {week}", "maternal")
        return MedicalDisclaimer.wrap(result, "pregnancy")

    def get_newborn_care(self) -> str:
        """Get comprehensive newborn care instructions.

        Returns:
            Newborn care guidance with disclaimer.
        """
        lines = [
            "NEWBORN CARE GUIDE",
            "==================",
            "",
            "Your newborn baby needs special care in the first weeks of life.",
            "",
        ]

        for key, content in self.NEWBORN_CARE.items():
            lines.append(content)
            lines.append("")

        lines.extend([
            "IMMUNIZATION REMINDER:",
            "- BCG vaccine (against TB): At birth or first contact",
            "- Polio vaccine: Starting at birth, then at 6, 10, 14 weeks",
            "- DPT/HepB/Hib vaccine: At 6, 10, 14 weeks",
            "- Measles vaccine: At 9 months",
            "",
            "Keep your baby's immunization card safe and bring it to every visit.",
            "",
            "EXCLUSIVE BREASTFEEDING for the first 6 months is the best",
            "nutrition for your baby. It provides all the nutrients needed",
            "and protects against infections and diseases.",
        ])

        self.db.log_query("newborn_care", "maternal")
        return MedicalDisclaimer.wrap("\n".join(lines), "pregnancy")



# ============================================================================
# CHILD HEALTH GUIDE
# ============================================================================

class ChildHealthGuide:
    """Comprehensive child health guide for African contexts.

    Provides immunization schedules, malnutrition assessment, common childhood
    illness guidance, oral rehydration instructions, and feeding guidelines.
    Follows WHO and UNICEF child health protocols.

    Methods:
        get_immunization_schedule: EPI schedule for African countries.
        assess_malnutrition: WHO criteria for malnutrition assessment.
        get_common_childhood_illnesses: Guidance for malaria, diarrhea, etc.
        get_oral_rehydration_guide: Homemade ORS recipe.
        get_child_nutrition: Feeding guidelines by age.
    """

    # Expanded Program on Immunization (EPI) schedules
    IMMUNIZATION_SCHEDULES: Dict[str, Dict[str, Any]] = {
        "nigeria": {
            "name": "Nigeria",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0", "HepB-BD"]},
                {"age": "6 weeks", "vaccines": ["OPV1", "Penta1 (DPT+HepB+Hib)", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["OPV2", "Penta2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["OPV3", "Penta3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "Yellow Fever", "MenA"]},
                {"age": "12 months", "vaccines": ["Measles2"]},
                {"age": "15 months", "vaccines": ["PCV Booster"]},
            ],
            "notes": "Nigeria follows the National Primary Health Care Development Agency (NPHCDA) schedule.",
        },
        "south_africa": {
            "name": "South Africa",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["RV1", "DTaP-IPV-Hib-HepB1", "PCV1"]},
                {"age": "10 weeks", "vaccines": ["DTaP-IPV-Hib-HepB2", "PCV2"]},
                {"age": "14 weeks", "vaccines": ["RV2", "DTaP-IPV-Hib-HepB3", "PCV3"]},
                {"age": "6 months", "vaccines": ["Measles1"]},
                {"age": "9 months", "vaccines": ["PCV Booster"]},
                {"age": "12 months", "vaccines": ["Measles2"]},
                {"age": "18 months", "vaccines": ["DTaP-IPV-Hib-HepB Booster"]},
            ],
            "notes": "South Africa follows the Expanded Programme on Immunisation (EPI-SA).",
        },
        "kenya": {
            "name": "Kenya",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0", "HepB-BD"]},
                {"age": "6 weeks", "vaccines": ["OPV1", "Penta1 (DPT+HepB+Hib)", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["OPV2", "Penta2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["OPV3", "Penta3", "PCV3", "IPV"]},
                {"age": "6 months", "vaccines": ["Vitamin A", "Deworming"]},
                {"age": "9 months", "vaccines": ["Measles-Rubella1", "Yellow Fever"]},
                {"age": "10 months", "vaccines": ["MenA"]},
                {"age": "18 months", "vaccines": ["Measles-Rubella2"]},
            ],
            "notes": "Kenya follows the Division of Vaccines and Immunization (DVI) schedule.",
        },
        "ghana": {
            "name": "Ghana",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0", "HepB-BD"]},
                {"age": "6 weeks", "vaccines": ["OPV1", "Penta1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["OPV2", "Penta2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["OPV3", "Penta3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles-Rubella1", "Yellow Fever", "MenA"]},
                {"age": "18 months", "vaccines": ["Measles-Rubella2", "OPV Booster"]},
            ],
            "notes": "Ghana follows the Ghana Health Service (GHS) EPI schedule.",
        },
        "ethiopia": {
            "name": "Ethiopia",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0", "HepB-BD"]},
                {"age": "6 weeks", "vaccines": ["Penta1 (DPT+HepB+Hib)", "OPV1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["Penta2", "OPV2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["Penta3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "Yellow Fever", "MenA"]},
                {"age": "15 months", "vaccines": ["Measles2", "PCV Booster"]},
            ],
            "notes": "Ethiopia follows the Federal Ministry of Health (FMOH) schedule.",
        },
        "uganda": {
            "name": "Uganda",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["DPT-HepB-Hib1", "OPV1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["DPT-HepB-Hib2", "OPV2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["DPT-HepB-Hib3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "Yellow Fever", "MR1"]},
                {"age": "18 months", "vaccines": ["Measles2", "MR2", "DPT Booster"]},
            ],
            "notes": "Uganda follows the Uganda National Expanded Programme on Immunization (UNEPI).",
        },
        "tanzania": {
            "name": "Tanzania",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "4 weeks", "vaccines": ["OPV1"]},
                {"age": "8 weeks", "vaccines": ["DPT-HepB-Hib1", "OPV2", "PCV1"]},
                {"age": "12 weeks", "vaccines": ["DPT-HepB-Hib2", "OPV3", "PCV2"]},
                {"age": "16 weeks", "vaccines": ["DPT-HepB-Hib3", "OPV4", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "MR1", "Yellow Fever"]},
                {"age": "18 months", "vaccines": ["Measles2", "MR2"]},
            ],
            "notes": "Tanzania follows the Immunization and Vaccine Development (IVD) programme.",
        },
        "rwanda": {
            "name": "Rwanda",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["Penta1", "PCV1", "Rota1", "OPV1"]},
                {"age": "10 weeks", "vaccines": ["Penta2", "PCV2", "Rota2", "OPV2"]},
                {"age": "14 weeks", "vaccines": ["Penta3", "PCV3", "IPV", "OPV3"]},
                {"age": "9 months", "vaccines": ["MR1", "Yellow Fever"]},
                {"age": "15 months", "vaccines": ["MR2"]},
                {"age": "18 months", "vaccines": ["Penta Booster"]},
            ],
            "notes": "Rwanda follows the Rwanda Biomedical Centre (RBC) immunization schedule.",
        },
        "malawi": {
            "name": "Malawi",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["Penta1", "PCV1", "Rota1", "OPV1"]},
                {"age": "10 weeks", "vaccines": ["Penta2", "PCV2", "Rota2", "OPV2"]},
                {"age": "14 weeks", "vaccines": ["Penta3", "PCV3", "IPV", "OPV3"]},
                {"age": "9 months", "vaccines": ["Measles1", "MR1"]},
                {"age": "15 months", "vaccines": ["Measles2", "MR2"]},
            ],
            "notes": "Malawi follows the EPI programme under the Ministry of Health.",
        },
        "zambia": {
            "name": "Zambia",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["DPT-HepB-Hib1", "OPV1", "PCV1"]},
                {"age": "10 weeks", "vaccines": ["DPT-HepB-Hib2", "OPV2", "PCV2"]},
                {"age": "14 weeks", "vaccines": ["DPT-HepB-Hib3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "MR1", "Yellow Fever"]},
                {"age": "18 months", "vaccines": ["Measles2", "MR2", "DPT Booster"]},
            ],
            "notes": "Zambia follows the Ministry of Health EPI schedule.",
        },
        "zimbabwe": {
            "name": "Zimbabwe",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["DPT-HepB-Hib1", "OPV1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["DPT-HepB-Hib2", "OPV2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["DPT-HepB-Hib3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "MR1"]},
                {"age": "18 months", "vaccines": ["Measles2", "MR2"]},
            ],
            "notes": "Zimbabwe follows the Ministry of Health and Child Care EPI schedule.",
        },
        "cameroon": {
            "name": "Cameroon",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0", "HepB-BD"]},
                {"age": "6 weeks", "vaccines": ["Penta1", "OPV1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["Penta2", "OPV2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["Penta3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "Yellow Fever", "MR1"]},
                {"age": "15-18 months", "vaccines": ["Measles2", "MR2"]},
            ],
            "notes": "Cameroon follows the Ministry of Public Health EPI schedule.",
        },
        "mozambique": {
            "name": "Mozambique",
            "schedule": [
                {"age": "Birth", "vaccines": ["BCG", "OPV0"]},
                {"age": "6 weeks", "vaccines": ["Penta1", "OPV1", "PCV1", "Rota1"]},
                {"age": "10 weeks", "vaccines": ["Penta2", "OPV2", "PCV2", "Rota2"]},
                {"age": "14 weeks", "vaccines": ["Penta3", "OPV3", "PCV3", "IPV"]},
                {"age": "9 months", "vaccines": ["Measles1", "MR1"]},
                {"age": "18 months", "vaccines": ["Measles2", "MR2"]},
            ],
            "notes": "Mozambique follows the Ministry of Health PAV (Plano Ampliado de Vacinacao) schedule.",
        },
    }

    # WHO malnutrition assessment criteria
    MALNUTRITION_Z_SCORES: Dict[str, Dict[str, float]] = {
        "severe_wasting": {"weight_for_height": -3.0, "muac_cm": 11.5},
        "moderate_wasting": {"weight_for_height": -2.0, "muac_cm": 12.5},
        "severe_stunting": {"height_for_age": -3.0},
        "moderate_stunting": {"height_for_age": -2.0},
        "underweight_severe": {"weight_for_age": -3.0},
        "underweight_moderate": {"weight_for_age": -2.0},
    }

    # Common childhood illness guidance
    CHILDHOOD_ILLNESSES: Dict[str, Dict[str, str]] = {
        "malaria": {
            "title": "MALARIA IN CHILDREN",
            "symptoms": [
                "Fever (may be high or intermittent)",
                "Chills and sweating",
                "Headache",
                "Fatigue and weakness",
                "Loss of appetite",
                "Vomiting and diarrhea",
                "Pale palms (sign of anemia)",
                "In severe cases: convulsions, unconsciousness, difficulty breathing",
            ],
            "home_care": """
HOME CARE (while seeking medical attention):
- Keep child cool with tepid sponging.
- Give plenty of fluids (ORS, water, breast milk).
- Give food if child can eat.
- For fever: tepid sponging with room temperature water.
- Keep child resting in a cool, shaded area.
- Use insecticide-treated mosquito net.
- Note: Do NOT give aspirin to children.
""",
            "when_to_seek": """
SEEK CARE IMMEDIATELY if:
- Fever lasts more than 24 hours in children under 2.
- Fever lasts more than 48 hours in older children.
- Child has convulsions or fits.
- Child is unconscious or very drowsy.
- Difficulty breathing.
- Cannot eat or drink.
- Repeated vomiting.
- Very pale or yellow eyes/skin.
- Child is unusually irritable or lethargic.
""",
            "prevention": [
                "Sleep under insecticide-treated mosquito nets (ITNs) every night.",
                "Remove standing water where mosquitoes breed.",
                "Keep doors and windows screened or closed at dusk.",
                "Wear long sleeves and trousers in the evening.",
                "Use indoor residual spraying (IRS) if available.",
                "Take malaria prophylaxis if traveling to high-risk areas.",
                "Pregnant women should take IPTp (intermittent preventive treatment).",
                "Seek prompt treatment for any fever.",
            ],
        },
        "diarrhea": {
            "title": "DIARRHEA IN CHILDREN",
            "symptoms": [
                "Loose or watery stools (3 or more per day)",
                "Stomach pain or cramps",
                "Vomiting",
                "Fever (sometimes)",
                "Loss of appetite",
                "Signs of dehydration: dry mouth, no tears, sunken eyes,",
                "  sunken fontanelle (in infants), fewer wet diapers",
            ],
            "home_care": """
HOME CARE - MOST IMPORTANT: PREVENT DEHYDRATION:

1. Give Oral Rehydration Solution (ORS):
   - Give small sips frequently after each loose stool.
   - Under 2 years: 50-100 ml after each stool.
   - 2-10 years: 100-200 ml after each stool.
   - Over 10 years: as much as wanted.

2. Continue Feeding:
   - Breastfeed more frequently and longer.
   - Give regular foods: rice, porridge, potatoes, bananas.
   - Give small amounts more often.

3. Zinc Supplementation:
   - Give zinc tablets for 10-14 days.
   - Under 6 months: 10 mg daily.
   - 6 months to 5 years: 20 mg daily.

4. Hygiene:
   - Wash hands with soap after toilet and before eating.
   - Use clean, safe drinking water.
   - Dispose of stools safely.
""",
            "when_to_seek": """
SEEK CARE IMMEDIATELY if:
- Signs of dehydration (sunken eyes, very dry mouth, no tears, lethargy).
- Blood in stool (dysentery).
- Diarrhea lasts more than 3 days.
- Child is under 6 months old.
- Repeated vomiting.
- High fever.
- Child is very weak or difficult to wake.
""",
            "prevention": [
                "Wash hands with soap before eating and after using toilet.",
                "Use safe drinking water (boil, filter, or treat).",
                "Store water in clean, covered containers.",
                "Breastfeed exclusively for first 6 months.",
                "Feed freshly prepared food.",
                "Wash fruits and vegetables with clean water.",
                "Dispose of feces safely (use latrines).",
                "Vaccinate against rotavirus (where available).",
            ],
        },
        "pneumonia": {
            "title": "PNEUMONIA IN CHILDREN",
            "symptoms": [
                "Fast breathing (tachypnea):",
                "  - Under 2 months: 60+ breaths per minute",
                "  - 2-12 months: 50+ breaths per minute",
                "  - 1-5 years: 40+ breaths per minute",
                "Chest indrawing (lower chest pulls in when breathing)",
                "Cough",
                "Fever",
                "Difficulty breathing",
                "Grunting sounds with breathing",
                "Nasal flaring",
                "Lethargy or irritability",
                "Refusing to eat or drink",
                "Bluish lips or fingernails (severe)",
            ],
            "home_care": """
HOME CARE:
- Keep child warm but not overheated.
- Give plenty of fluids (breast milk, water, ORS).
- Clear nasal secretions with saline drops.
- Raise head slightly during sleep.
- Keep room well-ventilated.
- Keep child away from smoke (cooking smoke, tobacco).
- Give food in small, frequent amounts.
""",
            "when_to_seek": """
SEEK CARE IMMEDIATELY if:
- Fast breathing (count breaths for a full minute).
- Chest indrawing visible.
- Difficulty breathing or grunting.
- Child cannot drink or breastfeed.
- Child is lethargic or unconscious.
- Bluish lips or fingernails.
- Fever lasts more than 3 days.
- Child is under 2 months old with any breathing difficulty.
""",
            "prevention": [
                "Vaccinate: PCV (pneumococcal), Hib, measles, pertussis.",
                "Breastfeed exclusively for first 6 months.",
                "Ensure good nutrition with varied diet.",
                "Keep child away from indoor cooking smoke.",
                "Ensure good ventilation in living spaces.",
                "Practice hand hygiene.",
                "Avoid overcrowded living conditions.",
            ],
        },
        "measles": {
            "title": "MEASLES IN CHILDREN",
            "symptoms": [
                "High fever",
                "Cough",
                "Runny nose (coryza)",
                "Red, watery eyes (conjunctivitis)",
                "Koplik spots (tiny white spots inside cheeks)",
                "Red, blotchy rash starting on face/hairline",
                "Rash spreads downward to body and limbs",
                "Rash may become raised and join together",
            ],
            "home_care": """
HOME CARE:
- Keep child comfortable and well-hydrated.
- Give plenty of fluids (water, ORS, breast milk).
- Give soft, easy-to-eat foods.
- Keep room dim if eyes are sensitive to light.
- Keep child away from other children (highly contagious).
- Give vitamin A supplement if available (from health facility).
- Do NOT give aspirin to children.
- Tepid sponging for high fever.
""",
            "when_to_seek": """
SEEK CARE IMMEDIATELY if:
- Child is under 1 year old.
- Severe diarrhea or vomiting.
- Signs of dehydration.
- Difficulty breathing or chest infection signs.
- Ear pain or discharge (ear infection).
- Child is very drowsy or confused.
- Convulsions.
- Child not improving after 3 days.
""",
            "prevention": [
                "VACCINATE: Measles vaccine at 9 months and second dose.",
                "Keep unvaccinated children away from infected individuals.",
                "Ensure good nutrition (vitamin A deficiency increases risk).",
                "Promote breastfeeding for immune protection.",
                "Vitamin A supplementation (where recommended).",
                "Good hygiene practices.",
            ],
        },
    }

    # Feeding guidelines by age
    FEEDING_GUIDELINES: Dict[str, Dict[str, str]] = {
        "0-6_months": {
            "title": "Feeding: 0-6 Months",
            "guidelines": """
EXCLUSIVE BREASTFEEDING:
- Breast milk ONLY for the first 6 months.
- No water, formula, cow's milk, or solid foods.
- Feed on demand: 8-12 times per day.
- Feed day and night.
- First milk (colostrum) is very important - full of antibodies.
- Ensure proper latch for effective feeding.
- If mother is HIV-positive, consult provider about feeding options.

IF BREASTFEEDING IS NOT POSSIBLE:
- Use infant formula prepared with clean, safe water.
- Use cup feeding (preferred over bottles).
- Prepare formula exactly as directed.
- Use within 1 hour of preparation.
""",
        },
        "6-9_months": {
            "title": "Feeding: 6-9 Months",
            "guidelines": """
START COMPLEMENTARY FOODS:
- Continue breastfeeding.
- Start soft, mashed foods 2-3 times per day.
- Introduce one new food at a time.
- Good first foods:
  * Mashed ripe banana
  * Mashed avocado
  * Thin porridge (uji) made with millet, sorghum, or maize
  * Mashed sweet potato
  * Mashed beans or lentils
  * Soft cooked egg yolk
  * Mashed fish (remove all bones)

- Add a little oil or fat to foods for energy.
- Foods should be nutrient-dense and easy to swallow.
- Wash hands and utensils before preparing food.
- Prepare fresh food for each meal.
""",
        },
        "9-12_months": {
            "title": "Feeding: 9-12 Months",
            "guidelines": """
INCREASE FOOD VARIETY:
- Continue breastfeeding.
- Increase to 3-4 meals per day plus snacks.
- Offer finger foods for self-feeding practice.
- Include from 4 food groups daily:
  1. Cereals/grains: ugali, rice, porridge, bread
  2. Proteins: beans, eggs, fish, chicken, meat
  3. Fruits and vegetables: mango, banana, pumpkin, greens
  4. Dairy: milk, yogurt (if available)

- Add oil, groundnut paste, or avocado for energy.
- Offer mashed and finely chopped foods.
- Encourage child to feed themselves.
- Continue to prepare fresh, clean food.
""",
        },
        "12-24_months": {
            "title": "Feeding: 12-24 Months",
            "guidelines": """
FAMILY FOODS:
- Continue breastfeeding.
- 3 main meals plus 2-3 nutritious snacks per day.
- Offer family foods (adapted: soft, cut into small pieces).
- Include a variety of foods from all food groups.
- Ensure adequate protein for growth.
- Offer iron-rich foods: meat, beans, leafy greens.
- Offer vitamin C-rich foods with iron-rich foods.
- Limit sugary foods and drinks.
- Avoid salty and processed foods.
- Let child eat with family to learn eating habits.
- Supervise eating to prevent choking.
- Continue hand washing before meals.
""",
        },
        "2-5_years": {
            "title": "Feeding: 2-5 Years",
            "guidelines": """
BALANCED DIET:
- Breastfeed as long as desired (up to 2 years and beyond).
- 3 balanced meals plus 2 healthy snacks daily.
- Include foods from all food groups:
  * Energy foods: grains, roots, fats
  * Body-building: beans, eggs, fish, meat, milk
  * Protective foods: fruits, vegetables
- Encourage a variety of colors on the plate.
- Limit sweets, sugary drinks, and processed snacks.
- Promote drinking water.
- Encourage hand washing before eating.
- Teach healthy eating habits by example.
- Regular deworming every 6 months.
- Vitamin A supplementation every 6 months (if recommended).
""",
        },
    }

    def __init__(self) -> None:
        """Initialize the ChildHealthGuide."""
        self.db = HealthRecordDB()
        logger.debug("ChildHealthGuide initialized")

    def get_immunization_schedule(self, country: str) -> str:
        """Get EPI immunization schedule for a specific African country.

        Args:
            country: Country name (e.g., 'nigeria', 'kenya', 'south_africa').

        Returns:
            Formatted immunization schedule with disclaimer.
        """
        country = country.lower().strip().replace(" ", "_")
        aliases = {
            "sa": "south_africa",
            "rsa": "south_africa",
            "cote_divoire": "ivory_coast",
        }
        country = aliases.get(country, country)

        if country not in self.IMMUNIZATION_SCHEDULES:
            available = ", ".join(
                info["name"] for info in self.IMMUNIZATION_SCHEDULES.values()
            )
            result = (
                f"Immunization schedule not available for '{country}'.\n\n"
                f"Available countries: {available}\n\n"
                f"General WHO EPI Schedule:\n"
                f"- Birth: BCG, OPV0, HepB-BD\n"
                f"- 6, 10, 14 weeks: Penta, OPV, PCV, Rota\n"
                f"- 9 months: Measles, Yellow Fever\n"
                f"- 15-18 months: Measles booster\n\n"
                f"Visit your nearest health facility for the complete schedule."
            )
            return MedicalDisclaimer.wrap(result, "children")

        schedule = self.IMMUNIZATION_SCHEDULES[country]
        lines = [
            f"Immunization Schedule - {schedule['name']}",
            "=" * 50,
            "",
            schedule["notes"],
            "",
            "| Age          | Vaccines                                      |",
            "|------------- |---------------------------------------------- |",
        ]

        for entry in schedule["schedule"]:
            age = entry["age"]
            vaccines = ", ".join(entry["vaccines"])
            lines.append(f"| {age:<12} | {vaccines:<45} |")

        lines.extend([
            "",
            "IMPORTANT NOTES:",
            "- Vaccines protect children from serious, life-threatening diseases.",
            "- Keep your child's immunization card safe and bring it to every visit.",
            "- If a vaccine dose is missed, go to the facility as soon as possible.",
            "- It is safe to give multiple vaccines at the same visit.",
            "- Mild fever or soreness after vaccination is normal.",
            "- Vaccines are typically FREE at government health facilities.",
        ])

        self.db.log_query(f"immunization_schedule: {country}", "child_health")
        return MedicalDisclaimer.wrap("\n".join(lines), "children")

    def assess_malnutrition(
        self,
        age_months: int,
        weight_kg: Optional[float] = None,
        height_cm: Optional[float] = None,
        muac_cm: Optional[float] = None,
    ) -> str:
        """Assess child malnutrition using WHO criteria.

        Uses MUAC (Mid-Upper Arm Circumference) as the primary screening
        tool, which is the standard in community-based programs across Africa.

        Args:
            age_months: Child's age in months.
            weight_kg: Weight in kilograms (optional).
            height_cm: Height in centimeters (optional).
            muac_cm: Mid-upper arm circumference in cm (primary indicator).

        Returns:
            Malnutrition assessment with disclaimer.
        """
        lines = [
            "CHILD MALNUTRITION ASSESSMENT",
            "============================",
            "",
            f"Age: {age_months} months",
        ]

        if weight_kg:
            lines.append(f"Weight: {weight_kg} kg")
        if height_cm:
            lines.append(f"Height: {height_cm} cm")
        if muac_cm:
            lines.append(f"MUAC: {muac_cm} cm")

        lines.append("")

        # MUAC-based assessment (primary, for children 6-59 months)
        if muac_cm is not None and 6 <= age_months <= 59:
            if muac_cm < 11.5:
                lines.append("RESULT: SEVERE ACUTE MALNUTRITION (SAM)")
                lines.append("=" * 45)
                lines.append("MUAC is below 11.5 cm - this is a CRITICAL finding.")
                lines.append("")
                lines.append("ACTIONS REQUIRED:")
                lines.append("1. Go to the nearest health facility IMMEDIATELY.")
                lines.append("2. Child needs Ready-to-Use Therapeutic Food (RUTF).")
                lines.append("3. May need admission for therapeutic feeding.")
                lines.append("4. Check for complications: fever, infection, dehydration.")
                lines.append("")
                lines.append("WARNING SIGNS REQUIRING URGENT REFERRAL:")
                lines.append("- Very weak or lethargic")
                lines.append("- Unable to eat or drink")
                lines.append("- Vomiting everything")
                lines.append("- Fever")
                lines.append("- Severe diarrhea")
                lines.append("- Edema (swelling of feet/hands/face)")
            elif muac_cm < 12.5:
                lines.append("RESULT: MODERATE ACUTE MALNUTRITION (MAM)")
                lines.append("=" * 45)
                lines.append("MUAC is between 11.5 and 12.5 cm.")
                lines.append("")
                lines.append("ACTIONS REQUIRED:")
                lines.append("1. Visit health facility within the week.")
                lines.append("2. Child may need Ready-to-Use Supplementary Food (RUSF).")
                lines.append("3. Counsel on improving child's diet.")
                lines.append("4. Treat any underlying illness (malaria, worms, diarrhea).")
                lines.append("5. Return for follow-up in 2 weeks.")
            else:
                lines.append("RESULT: MUAC in NORMAL range")
                lines.append("MUAC is 12.5 cm or above - no acute malnutrition detected by MUAC.")

        lines.append("")
        lines.append("GENERAL NUTRITION RECOMMENDATIONS:")
        lines.append("- Continue breastfeeding if under 2 years.")
        lines.append("- Ensure child eats from at least 4 food groups daily.")
        lines.append("- Give nutrient-dense foods: eggs, beans, groundnut paste, avocado.")
        lines.append("- Add oil or fat to meals for energy.")
        lines.append("- Give vitamin A supplements every 6 months (from health facility).")
        lines.append("- Regular deworming every 6 months.")
        lines.append("- Treat illnesses promptly (malaria, diarrhea, worms).")
        lines.append("- Ensure clean water and good hygiene.")

        if weight_kg and height_cm:
            lines.append("")
            lines.append("NOTE: Weight-for-height assessment requires WHO reference tables.")
            lines.append("Visit a health facility for accurate assessment using growth charts.")

        self.db.log_query(
            f"malnutrition_assessment: age={age_months}, muac={muac_cm}",
            "child_health",
        )
        return MedicalDisclaimer.wrap("\n".join(lines), "children")

    def get_common_childhood_illnesses(self, illness: str) -> str:
        """Get guidance for common childhood illnesses.

        Args:
            illness: Illness name ('malaria', 'diarrhea', 'pneumonia', 'measles').

        Returns:
            Illness information with disclaimer.
        """
        illness = illness.lower().strip()
        aliases = {
            "fever": "malaria",
            "loose_stools": "diarrhea",
            "loose stools": "diarrhea",
            "cough": "pneumonia",
            "rash": "measles",
        }
        illness = aliases.get(illness, illness)

        if illness not in self.CHILDHOOD_ILLNESSES:
            available = ", ".join(self.CHILDHOOD_ILLNESSES.keys())
            result = (
                f"Illness information not available for '{illness}'.\n\n"
                f"Available illnesses: {available}\n\n"
                f"For ANY child illness, consult a healthcare provider.\n"
                f"Children can deteriorate rapidly - seek care early."
            )
            return MedicalDisclaimer.wrap(result, "children")

        info = self.CHILDHOOD_ILLNESSES[illness]
        lines = [
            info["title"],
            "=" * len(info["title"]),
            "",
            "SYMPTOMS:",
        ]
        for symptom in info["symptoms"]:
            lines.append(f"  - {symptom}")

        lines.extend([
            "",
            info["home_care"],
            "",
            info["when_to_seek"],
            "",
            "PREVENTION:",
        ])
        for prev in info["prevention"]:
            lines.append(f"  - {prev}")

        self.db.log_query(f"childhood_illness: {illness}", "child_health")
        return MedicalDisclaimer.wrap("\n".join(lines), "children")

    def get_oral_rehydration_guide(self) -> str:
        """Get oral rehydration solution (ORS) recipe and usage instructions.

        Returns:
            ORS preparation guide with disclaimer.
        """
        guide = """
ORAL REHYDRATION SOLUTION (ORS) GUIDE
=====================================

ORS saves lives! It is the most important treatment for diarrhea.

HOMEMADE ORS RECIPE (if packets are not available):
---------------------------------------------------
Ingredients:
- 6 level teaspoons of sugar
- 1/2 level teaspoon of salt
- 1 liter (4 cups) of clean drinking water

Instructions:
1. Wash your hands thoroughly.
2. Measure exactly - too much salt or sugar can be harmful.
3. Mix sugar and salt in the clean water.
4. Stir until completely dissolved.
5. Taste the solution - it should not be saltier than tears.
6. Give to the child in small, frequent sips.

PREMADE ORS PACKETS:
--------------------
If you have ORS packets from the health facility:
1. Read the instructions on the packet.
2. Add the powder to the correct amount of clean water (usually 1 liter).
3. Stir well until dissolved.

HOW TO GIVE ORS:
----------------
- Under 2 years: Give 50-100 ml after each loose stool.
- 2-10 years: Give 100-200 ml after each loose stool.
- Over 10 years: Give as much as the person wants.
- Use a clean cup or spoon.
- Give small amounts frequently (every 1-2 minutes).
- If vomiting, wait 10 minutes and try again with smaller sips.
- Continue giving ORS until diarrhea stops.

IMPORTANT RULES:
----------------
- Do NOT use too much salt or sugar - measure carefully.
- Do NOT stop giving food while giving ORS.
- Do NOT give plain water alone - it does not replace salts.
- Do NOT give fizzy drinks or sweetened juices - too much sugar.
- Continue breastfeeding throughout diarrhea.
- Give zinc supplements alongside ORS (from health facility).

WHEN TO SEEK CARE:
------------------
- Child cannot drink or keep fluids down.
- Signs of severe dehydration (very sunken eyes, very dry mouth,
  no tears, cold hands/feet, lethargy).
- Blood in stool.
- Diarrhea lasting more than 3 days.
- Child is under 6 months old.
"""
        return MedicalDisclaimer.wrap(guide, "children")

    def get_child_nutrition(self, age: str) -> str:
        """Get feeding guidelines for a specific age group.

        Args:
            age: Age category ('0-6_months', '6-9_months', '9-12_months',
                 '12-24_months', '2-5_years').

        Returns:
            Feeding guidelines with disclaimer.
        """
        age = age.lower().strip().replace(" ", "_")

        # Normalize age input
        age_aliases = {
            "0-6": "0-6_months",
            "0_6": "0-6_months",
            "infant": "0-6_months",
            "baby": "0-6_months",
            "newborn": "0-6_months",
            "6-9": "6-9_months",
            "6_9": "6-9_months",
            "9-12": "9-12_months",
            "9_12": "9-12_months",
            "12-24": "12-24_months",
            "12_24": "12-24_months",
            "1-2_years": "12-24_months",
            "2-5": "2-5_years",
            "2_5": "2-5_years",
            "toddler": "12-24_months",
            "preschool": "2-5_years",
        }
        age = age_aliases.get(age, age)

        if age not in self.FEEDING_GUIDELINES:
            available = ", ".join(
                g["title"] for g in self.FEEDING_GUIDELINES.values()
            )
            result = (
                f"Feeding guidelines not found for '{age}'.\n\n"
                f"Available age groups:\n{available}\n\n"
                f"Every child is different. Consult a health worker for "
                f"personalized feeding advice."
            )
            return MedicalDisclaimer.wrap(result, "children")

        guide = self.FEEDING_GUIDELINES[age]
        result = f"{guide['title']}\n{'=' * len(guide['title'])}\n{guide['guidelines']}"

        self.db.log_query(f"child_nutrition: {age}", "child_health")
        return MedicalDisclaimer.wrap(result, "children")



# ============================================================================
# DISEASE INFORMATION
# ============================================================================

class DiseaseInformation:
    """Comprehensive disease information for common African conditions.

    Provides information on symptoms, prevention, and when to seek care
    for diseases prevalent in Africa. Follows WHO and CDC guidelines.

    Attributes:
        COMMON_AFRICAN_DISEASES: Dictionary with comprehensive disease data.

    Methods:
        get_disease_info: General information about a disease.
        get_prevention: Prevention methods for a disease.
        get_when_to_seek_care: Red flag symptoms requiring medical attention.
    """

    COMMON_AFRICAN_DISEASES: Dict[str, Dict[str, Any]] = {
        "malaria": {
            "name": "Malaria",
            "description": """
Malaria is a life-threatening disease caused by parasites transmitted to
people through the bites of infected female Anopheles mosquitoes. It is
preventable and curable. Africa carries a disproportionately high share
of the global malaria burden.
""",
            "symptoms": [
                "Fever (may be intermittent or constant)",
                "Chills and sweating",
                "Headache and body aches",
                "Fatigue and weakness",
                "Nausea and vomiting",
                "Diarrhea (especially in children)",
                "Anemia (pale skin, tiredness)",
                "Jaundice (yellow skin/eyes)",
            ],
            "severe_symptoms": [
                "Confusion or altered consciousness (cerebral malaria)",
                "Difficulty breathing",
                "Multiple convulsions",
                "Prostration (unable to sit/stand without assistance)",
                "Abnormal bleeding",
                "Jaundice with dark urine",
                "Very pale (severe anemia)",
                "Shock (cold clammy skin, weak rapid pulse)",
            ],
            "prevention": [
                "Sleep under insecticide-treated mosquito nets (ITNs) every night.",
                "Remove standing water where mosquitoes breed (old tires, pots, puddles).",
                "Indoor residual spraying (IRS) of insecticides.",
                "Wear long-sleeved clothing and trousers in the evening.",
                "Use mosquito repellents on exposed skin.",
                "Keep windows and doors screened or use wire mesh.",
                "Clear vegetation around homes.",
                "Take malaria prophylaxis when traveling to endemic areas.",
                "Intermittent preventive treatment in pregnancy (IPTp).",
                "Seasonal malaria chemoprevention (SMC) for children in Sahel region.",
                "Prompt diagnosis and treatment of all suspected cases.",
            ],
            "when_to_seek": [
                "Any fever in a child under 5 years - seek care within 24 hours.",
                "Fever lasting more than 48 hours in adults.",
                "Any severe symptoms listed above.",
                "Pregnant woman with fever.",
                "Fever after recent travel to a malaria-endemic area.",
                "Signs of anemia (extreme tiredness, pale skin).",
                "Jaundice (yellow eyes or skin).",
                "Unable to eat or drink.",
            ],
            "treatment_note": "Malaria is treated with antimalarial medications such as artemisinin-based combination therapies (ACTs). Treatment must be prescribed by a healthcare provider after confirmed diagnosis (rapid diagnostic test or microscopy). Do NOT self-medicate with leftover antimalarials.",
            "affected_regions": "Sub-Saharan Africa bears approximately 95% of global malaria cases and 96% of malaria deaths. High transmission areas include West Africa, Central Africa, and parts of East and Southern Africa.",
        },
        "typhoid": {
            "name": "Typhoid Fever",
            "description": """
Typhoid fever is a bacterial infection caused by Salmonella typhi. It
spreads through contaminated food and water. Typhoid is common in areas
with poor sanitation and limited access to clean water. Without treatment,
it can be life-threatening.
""",
            "symptoms": [
                "Prolonged high fever (gradual onset, lasting weeks)",
                "Headache and body aches",
                "Stomach pain and constipation (or diarrhea)",
                "Loss of appetite",
                "Weakness and fatigue",
                "Rose-colored spots on chest/abdomen",
                "Enlarged liver or spleen",
                "Cough",
            ],
            "severe_symptoms": [
                "Severe abdominal pain",
                "Bloody diarrhea",
                "Confusion or altered mental state",
                "Intestinal perforation (severe abdominal pain, rigid abdomen)",
                "Persistent vomiting",
                "Shock",
            ],
            "prevention": [
                "Drink only safe water (boiled, filtered, or treated).",
                "Wash hands with soap before eating and after using toilet.",
                "Eat thoroughly cooked food served hot.",
                "Avoid raw fruits and vegetables unless washed with safe water.",
                "Avoid street food of uncertain hygiene.",
                "Use latrines or toilets. Dispose of feces safely.",
                "Typhoid vaccination is available for travelers and high-risk groups.",
                "Proper sewage disposal and water treatment.",
            ],
            "when_to_seek": [
                "Fever lasting more than 3 days, especially with stomach symptoms.",
                "Severe abdominal pain.",
                "Blood in stool.",
                "Confusion or altered consciousness.",
                "Signs of dehydration.",
                "Persistent vomiting.",
                "Not improving after starting antibiotics.",
            ],
            "treatment_note": "Typhoid is treated with antibiotics prescribed by a healthcare provider. Proper diagnosis through blood or stool culture is important. Completing the full antibiotic course is essential even if you feel better.",
            "affected_regions": "Common across Africa, especially in urban areas with overcrowding and poor water/sanitation infrastructure. Higher incidence in West and Central Africa.",
        },
        "cholera": {
            "name": "Cholera",
            "description": """
Cholera is an acute diarrheal infection caused by ingestion of food or
water contaminated with the bacterium Vibrio cholerae. It can cause
severe dehydration and death within hours if untreated. Cholera outbreaks
occur frequently in Africa, especially during rainy seasons and in
conflict/displacement settings.
""",
            "symptoms": [
                "Profuse watery diarrhea ('rice water' stools)",
                "Vomiting",
                "Rapid dehydration",
                "Leg cramps",
                "Restlessness and irritability",
                "Thirst",
                "Dry mouth and skin",
                "Reduced urine output",
            ],
            "severe_symptoms": [
                "Severe dehydration (sunken eyes, wrinkled skin)",
                "Very rapid weak pulse",
                "Low blood pressure",
                "Altered consciousness",
                "Shock and collapse",
                "Death can occur within hours",
            ],
            "prevention": [
                "Drink only safe water (boiled, chlorinated, or bottled).",
                "Wash hands frequently with soap and safe water.",
                "Cook food thoroughly and eat while hot.",
                "Wash fruits and vegetables with treated water.",
                "Use latrines. Do not defecate in open areas.",
                "Proper disposal of feces, especially of children.",
                "Cholera vaccination is available for outbreak settings.",
                "Report suspected cases to health authorities promptly.",
                "Avoid contact with cholera patient feces/vomit.",
            ],
            "when_to_seek": [
                "ANY suspected cholera case requires IMMEDIATE medical care.",
                "Profuse watery diarrhea.",
                "Signs of dehydration (dry mouth, sunken eyes, no urine).",
                "Vomiting with diarrhea.",
                "Anyone in an area with an active cholera outbreak with diarrhea.",
            ],
            "treatment_note": "Cholera treatment is primarily ORS (oral rehydration solution) to replace lost fluids. Severe cases need IV fluids. Antibiotics may be given for severe cases. Zinc supplements help recovery. Early treatment saves lives.",
            "affected_regions": "Outbreaks occur across Africa, particularly in the Horn of Africa, Great Lakes region, West Africa, and Southern Africa. Risk increases during floods, conflicts, and displacement.",
        },
        "hiv_aids": {
            "name": "HIV/AIDS",
            "description": """
HIV (Human Immunodeficiency Virus) attacks the immune system. Without
treatment, it can lead to AIDS (Acquired Immunodeficiency Syndrome).
With proper antiretroviral therapy (ART), people with HIV can live
long, healthy lives. Africa has the highest burden of HIV globally,
but treatment access has greatly improved.
""",
            "symptoms": [
                "Acute infection (2-4 weeks after exposure):",
                "  - Flu-like illness (fever, sore throat, rash)",
                "  - Swollen lymph nodes",
                "  - Muscle and joint aches",
                "  - Headache",
                "Chronic phase may have no symptoms for years.",
                "As immune system weakens:",
                "  - Persistent fever",
                "  - Night sweats",
                "  - Chronic diarrhea",
                "  - Weight loss",
                "  - Persistent cough",
                "  - Skin rashes and sores",
                "  - Recurrent infections",
                "  - Oral thrush (white patches in mouth)",
            ],
            "severe_symptoms": [
                "Opportunistic infections (TB, pneumonia, meningitis)",
                "Severe weight loss and wasting",
                "Neurological problems (confusion, memory loss)",
                "Kaposi's sarcoma (skin cancer lesions)",
                "Severe fungal infections",
            ],
            "prevention": [
                "Use condoms correctly during every sexual encounter.",
                "Get tested regularly (know your status and your partner's).",
                "Take PrEP (Pre-Exposure Prophylaxis) if at high risk.",
                "Pregnant women: take ART to prevent mother-to-child transmission (PMTCT).",
                "Use sterile needles and syringes (never share).",
                "Ensure safe blood transfusions (screened blood).",
                "Male circumcision reduces female-to-male transmission risk.",
                "Promptly treat sexually transmitted infections (STIs).",
                "Support people living with HIV - reduce stigma.",
                "People with HIV: take ART daily as prescribed to achieve viral suppression.",
            ],
            "when_to_seek": [
                "If you suspect exposure to HIV - get tested immediately.",
                "Persistent symptoms suggesting immune suppression.",
                "Any opportunistic infection symptoms.",
                "If on ART: any severe side effects or treatment failure signs.",
                "Pregnant and HIV-positive: immediate care for PMTCT.",
                "Regular follow-up if HIV-positive (every 3-6 months).",
            ],
            "treatment_note": "HIV is managed with antiretroviral therapy (ART). Daily medication suppresses the virus, prevents transmission, and allows normal life expectancy. ART is FREE in most African countries. Adherence (taking medication every day) is crucial. U=U: Undetectable = Untransmittable.",
            "affected_regions": "Eastern and Southern Africa have the highest prevalence. South Africa, Mozambique, Tanzania, Kenya, Uganda, Zimbabwe, Malawi, Zambia, and Nigeria have the largest numbers of people living with HIV.",
        },
        "tuberculosis": {
            "name": "Tuberculosis (TB)",
            "description": """
Tuberculosis is a bacterial infection caused by Mycobacterium tuberculosis.
It most commonly affects the lungs (pulmonary TB) but can affect other
parts of the body. TB is a leading cause of death in Africa, particularly
among people living with HIV. It is curable with proper treatment.
""",
            "symptoms": [
                "Persistent cough lasting more than 2-3 weeks",
                "Coughing up blood or sputum",
                "Chest pain",
                "Fever and night sweats",
                "Unexplained weight loss",
                "Fatigue and weakness",
                "Loss of appetite",
                "Shortness of breath",
            ],
            "severe_symptoms": [
                "Massive hemoptysis (coughing up large amounts of blood)",
                "Severe shortness of breath",
                "Meningitis symptoms (severe headache, stiff neck, confusion)",
                "Spinal involvement (back pain, paralysis)",
                "Miliary TB (widespread infection)",
            ],
            "prevention": [
                "Complete full course of TB treatment if diagnosed.",
                "BCG vaccination at birth (protects against severe childhood TB).",
                "Good ventilation in homes and workplaces.",
                "Cover mouth when coughing.",
                "People with TB should wear masks in crowded places.",
                "Isoniazid preventive therapy (IPT) for high-risk individuals.",
                "Early diagnosis and treatment of all TB cases.",
                "Screen household contacts of TB patients.",
                "Address HIV-TB co-infection through integrated services.",
            ],
            "when_to_seek": [
                "Cough lasting more than 2 weeks.",
                "Coughing up blood.",
                "Unexplained weight loss with persistent cough.",
                "Night sweats with fever.",
                "Close contact with someone diagnosed with TB.",
                "If on TB treatment: severe side effects (jaundice, severe rash).",
            ],
            "treatment_note": "TB is treated with a 6-month course of antibiotics (isoniazid, rifampicin, ethambutol, pyrazinamide). Drug-resistant TB requires longer treatment with different medications. Treatment is FREE in most countries. Completing the FULL course is essential to prevent drug resistance. Directly Observed Therapy (DOT) programs help ensure adherence.",
            "affected_regions": "High burden countries include South Africa, Nigeria, Mozambique, Tanzania, Kenya, Ethiopia, Uganda, Zambia, Zimbabwe, and Malawi. TB-HIV co-infection is common in Southern and Eastern Africa.",
        },
        "hepatitis": {
            "name": "Hepatitis (A, B, C, E)",
            "description": """
Hepatitis is inflammation of the liver caused by viral infections.
Hepatitis B is particularly prevalent in Africa, where it is often
transmitted from mother to child at birth or in early childhood.
Hepatitis C is also significant. Vaccination is available for Hepatitis B.
""",
            "symptoms": [
                "Many people have no symptoms (especially chronic carriers).",
                "Acute symptoms may include:",
                "  - Fatigue and weakness",
                "  - Nausea and vomiting",
                "  - Abdominal pain (upper right)",
                "  - Loss of appetite",
                "  - Low-grade fever",
                "  - Dark urine",
                "  - Clay-colored stool",
                "  - Joint pain",
                "  - Jaundice (yellow skin and eyes)",
            ],
            "severe_symptoms": [
                "Acute liver failure",
                "Confusion or altered consciousness",
                "Severe vomiting",
                "Bleeding problems",
                "Severe abdominal swelling (ascites)",
                "Hepatocellular carcinoma (liver cancer - in chronic cases)",
            ],
            "prevention": [
                "Hepatitis B vaccination (part of routine childhood immunization).",
                "Ensure safe blood transfusions (screened blood).",
                "Use sterile needles and syringes.",
                "Practice safe sex (use condoms).",
                "Do not share personal items that may have blood (razors, toothbrushes).",
                "Ensure safe tattooing and piercing practices.",
                "Hepatitis B: PMTCT - give HBV vaccine to newborns within 24 hours.",
                "Hand washing, especially after toilet use (Hepatitis A & E).",
                "Safe water and food handling (Hepatitis A & E).",
                "Hepatitis B immunoglobulin for exposed individuals.",
            ],
            "when_to_seek": [
                "Jaundice (yellow skin or eyes).",
                "Persistent nausea and vomiting.",
                "Severe abdominal pain.",
                "Dark urine and pale stools.",
                "Unexplained fatigue lasting weeks.",
                "If pregnant: get tested for Hepatitis B for PMTCT.",
                "If on treatment: regular monitoring of liver function.",
            ],
            "treatment_note": "Acute hepatitis may resolve on its own. Chronic Hepatitis B may require antiviral treatment (tenofovir, entecavir). Hepatitis C is curable with direct-acting antivirals (DAAs). Regular monitoring of liver function is important. Avoid alcohol and hepatotoxic medications.",
            "affected_regions": "Hepatitis B is highly endemic in Sub-Saharan Africa with prevalence rates of 5-15% in many countries. Highest rates in West and Central Africa. Hepatitis C is significant in Egypt and parts of Central Africa.",
        },
        "diabetes": {
            "name": "Diabetes Mellitus",
            "description": """
Diabetes is a chronic condition where blood sugar levels are too high
due to the body not producing enough insulin or not using it effectively.
Type 2 diabetes is increasing rapidly in Africa due to lifestyle changes.
Diabetes can lead to serious complications if not managed properly.
""",
            "symptoms": [
                "Increased thirst and frequent urination",
                "Unexplained weight loss (especially Type 1)",
                "Increased hunger",
                "Fatigue and weakness",
                "Blurred vision",
                "Slow-healing sores or frequent infections",
                "Numbness or tingling in hands/feet",
                "Dry skin",
                "Dark patches on skin (acanthosis nigricans - Type 2)",
            ],
            "severe_symptoms": [
                "Diabetic ketoacidosis (DKA): nausea, vomiting, abdominal pain,",
                "  fruity breath, rapid breathing, confusion",
                "Hyperosmolar hyperglycemic state: extreme thirst, confusion, seizures",
                "Severe hypoglycemia: sweating, trembling, confusion, loss of consciousness",
                "Diabetic foot ulcers and infections",
                "Severe dehydration",
            ],
            "prevention": [
                "Maintain a healthy weight through balanced diet and exercise.",
                "Eat a diet rich in vegetables, whole grains, and lean proteins.",
                "Limit sugar, sugary drinks, and refined carbohydrates.",
                "Exercise regularly (at least 150 minutes per week).",
                "Avoid tobacco use.",
                "Limit alcohol consumption.",
                "Regular health check-ups, especially if family history.",
                "Manage blood pressure and cholesterol.",
                "For gestational diabetes: follow provider guidance to prevent Type 2.",
            ],
            "when_to_seek": [
                "Symptoms of high blood sugar (excessive thirst, frequent urination).",
                "Symptoms of DKA or severe hypoglycemia (EMERGENCY).",
                "Any wound, especially on feet, that is not healing.",
                "Signs of infection (fever with diabetes).",
                "Vision changes.",
                "Regular follow-ups if diagnosed (every 3-6 months).",
                "If on medication: any severe side effects.",
            ],
            "treatment_note": "Type 1 diabetes requires daily insulin injections. Type 2 diabetes is managed with lifestyle changes, oral medications (metformin, sulfonylureas), and sometimes insulin. Regular blood glucose monitoring is essential. Comprehensive management includes blood pressure and cholesterol control. Foot care is critical to prevent complications.",
            "affected_regions": "Increasing across all African regions. Higher rates in urban areas and among older adults. South Africa, Egypt, Morocco, Algeria, and Nigeria have the highest numbers. Type 2 diabetes is becoming more common in younger populations.",
        },
        "hypertension": {
            "name": "Hypertension (High Blood Pressure)",
            "description": """
Hypertension is when blood pressure in the arteries is persistently
elevated. It is often called the 'silent killer' because it frequently
has no symptoms but causes serious damage to the heart, brain, kidneys,
and eyes. Hypertension is increasingly common in Africa.
""",
            "symptoms": [
                "Most people have NO symptoms (hence 'silent killer').",
                "Some may experience:",
                "  - Headaches (especially morning headaches)",
                "  - Dizziness",
                "  - Shortness of breath",
                "  - Nosebleeds",
                "  - Flushing",
                "  - Chest pain (in severe cases)",
                "  - Vision problems (in severe cases)",
            ],
            "severe_symptoms": [
                "Hypertensive emergency: blood pressure 180/120 or higher with:",
                "  - Chest pain",
                "  - Severe headache",
                "  - Confusion or altered consciousness",
                "  - Severe anxiety",
                "  - Shortness of breath",
                "  - Seizures",
                "  - Vision changes",
                "  - Signs of stroke (sudden weakness, speech difficulty)",
            ],
            "prevention": [
                "Reduce salt intake (less than 5g/1 teaspoon per day).",
                "Maintain a healthy weight.",
                "Exercise regularly (at least 30 minutes most days).",
                "Eat a diet rich in fruits, vegetables, and whole grains.",
                "Limit alcohol consumption.",
                "Avoid tobacco use.",
                "Manage stress through relaxation techniques.",
                "Regular blood pressure checks (at least annually).",
                "Take prescribed medications exactly as directed.",
                "Reduce processed and packaged foods (high in sodium).",
                "Use herbs and spices instead of salt for flavoring.",
            ],
            "when_to_seek": [
                "Hypertensive emergency symptoms listed above - call emergency.",
                "Blood pressure consistently above 140/90 at home.",
                "Persistent headaches with elevated BP.",
                "If on medication: side effects (dizziness, cough, swelling).",
                "Regular follow-up every 1-3 months if diagnosed.",
                "Annual screening if over 40 or with risk factors.",
                "If pregnant: report any high blood pressure readings immediately.",
            ],
            "treatment_note": "Lifestyle modifications are the foundation. Medications may include: thiazide diuretics, ACE inhibitors, ARBs, calcium channel blockers, or beta-blockers. Multiple medications may be needed. Treatment is lifelong. Regular monitoring and medication adherence are essential. Never stop medication without consulting your provider.",
            "affected_regions": "High prevalence across Africa, especially in urban areas. Countries with higher rates include South Africa, Ghana, Nigeria, Kenya, Senegal, and Morocco. Often underdiagnosed and poorly controlled due to limited screening.",
        },
        "sickle_cell": {
            "name": "Sickle Cell Disease",
            "description": """
Sickle cell disease is an inherited blood disorder where red blood cells
become rigid and shaped like sickles. These cells can block blood flow,
causing pain, organ damage, and other complications. It is one of the
most common genetic disorders in Africa, affecting millions of people.
""",
            "symptoms": [
                "Chronic anemia (fatigue, pale skin, shortness of breath)",
                "Pain crises (sudden severe pain in bones, chest, abdomen, joints)",
                "Swelling of hands and feet (in children)",
                "Frequent infections",
                "Jaundice (yellowing of skin and eyes)",
                "Delayed growth and puberty",
                "Vision problems",
                "Enlarged spleen (in children)",
            ],
            "severe_symptoms": [
                "Acute chest syndrome (chest pain, fever, cough, difficulty breathing)",
                "Stroke (sudden weakness, speech difficulty, confusion)",
                "Severe anemia crisis (extreme fatigue, rapid heartbeat)",
                "Priapism (prolonged painful erection)",
                "Splenic sequestration (sudden enlarged spleen, severe anemia)",
                "Severe infections (sepsis, meningitis, pneumonia)",
                "Multi-organ failure",
            ],
            "prevention": [
                "Genetic counseling for prospective parents (know your genotype).",
                "Newborn screening programs where available.",
                "Daily penicillin prophylaxis for children (prevents infections).",
                "Regular vaccinations (pneumococcal, meningococcal, Hib).",
                "Folic acid supplementation daily.",
                "Stay well-hydrated - drink plenty of water.",
                "Avoid extreme temperatures and high altitude.",
                "Prompt treatment of infections.",
                "Avoid strenuous exercise without medical guidance.",
                "Malaria prevention (sleep under ITNs, prophylaxis if recommended).",
                "Regular medical follow-up every 3-6 months.",
            ],
            "when_to_seek": [
                "Any signs of acute chest syndrome (EMERGENCY).",
                "Stroke symptoms (EMERGENCY).",
                "Severe pain crisis not responding to usual pain medication.",
                "Fever 38.5 C (101.3 F) or higher (risk of serious infection).",
                "Signs of severe anemia (extreme tiredness, rapid heartbeat).",
                "Severe headache or confusion.",
                "Priapism lasting more than 4 hours.",
                "Signs of dehydration.",
                "Any illness in children with sickle cell - seek care promptly.",
            ],
            "treatment_note": "Treatment includes: pain management during crises, blood transfusions for severe anemia, hydroxyurea medication (reduces crises), antibiotics for infection prevention, folic acid supplements, and management of complications. Bone marrow transplant is a potential cure but is complex and expensive. Comprehensive care in specialized centers is ideal.",
            "affected_regions": "Very high prevalence in Sub-Saharan Africa. Countries with highest rates include Nigeria, Democratic Republic of Congo, Tanzania, Uganda, Ghana, Kenya, and Cameroon. Sickle cell trait (AS genotype) is protective against malaria, which explains its high prevalence in malaria-endemic regions.",
        },
    }

    def __init__(self) -> None:
        """Initialize the DiseaseInformation guide."""
        self.db = HealthRecordDB()
        logger.debug("DiseaseInformation initialized")

    def get_disease_info(self, disease: str) -> str:
        """Get comprehensive information about a disease.

        Args:
            disease: Disease name. Options: 'malaria', 'typhoid', 'cholera',
                'hiv_aids', 'tuberculosis', 'hepatitis', 'diabetes',
                'hypertension', 'sickle_cell'.

        Returns:
            Disease information with disclaimer.
        """
        disease = disease.lower().strip().replace(" ", "_")
        aliases = {
            "tb": "tuberculosis",
            "hiv": "hiv_aids",
            "aids": "hiv_aids",
            "high_blood_pressure": "hypertension",
            "high blood pressure": "hypertension",
            "bp": "hypertension",
            "sugar": "diabetes",
            "hep": "hepatitis",
        }
        disease = aliases.get(disease, disease)

        if disease not in self.COMMON_AFRICAN_DISEASES:
            available = ", ".join(self.COMMON_AFRICAN_DISEASES.keys())
            result = (
                f"Disease information not available for '{disease}'.\n\n"
                f"Available diseases: {available}\n\n"
                f"For any health concern, consult a healthcare provider."
            )
            return MedicalDisclaimer.wrap(result, "standard")

        info = self.COMMON_AFRICAN_DISEASES[disease]
        lines = [
            f"{info['name']}",
            "=" * 60,
            info['description'],
            "",
            "SYMPTOMS:",
        ]
        for symptom in info["symptoms"]:
            lines.append(f"  - {symptom}")

        if info.get("severe_symptoms"):
            lines.extend(["", "SEVERE SYMPTOMS - Seek emergency care:"])
            for symptom in info["severe_symptoms"]:
                lines.append(f"  - {symptom}")

        lines.extend(["", f"TREATMENT NOTE: {info['treatment_note']}", ""])

        if info.get("affected_regions"):
            lines.extend(["AFFECTED REGIONS:", f"  {info['affected_regions']}", ""])

        self.db.log_query(f"disease_info: {disease}", "disease_info")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")

    def get_prevention(self, disease: str) -> str:
        """Get prevention methods for a specific disease.

        Args:
            disease: Disease name (same as get_disease_info).

        Returns:
            Prevention information with disclaimer.
        """
        disease = disease.lower().strip().replace(" ", "_")
        aliases = {
            "tb": "tuberculosis",
            "hiv": "hiv_aids",
            "aids": "hiv_aids",
            "high_blood_pressure": "hypertension",
            "bp": "hypertension",
            "sugar": "diabetes",
            "hep": "hepatitis",
        }
        disease = aliases.get(disease, disease)

        if disease not in self.COMMON_AFRICAN_DISEASES:
            result = (
                f"Prevention information not available for '{disease}'.\n\n"
                f"General prevention measures:\n"
                f"- Wash hands regularly with soap\n"
                f"- Drink safe water\n"
                f"- Eat a balanced diet\n"
                f"- Exercise regularly\n"
                f"- Get vaccinated as recommended\n"
                f"- Practice safe sex\n"
                f"- Avoid tobacco and limit alcohol\n"
                f"- Get regular health check-ups"
            )
            return MedicalDisclaimer.wrap(result, "standard")

        info = self.COMMON_AFRICAN_DISEASES[disease]
        lines = [
            f"PREVENTION: {info['name']}",
            "=" * 60,
            "",
            "Prevention measures:",
        ]
        for i, measure in enumerate(info["prevention"], 1):
            lines.append(f"{i}. {measure}")

        lines.extend(["", "Remember: Prevention is always better than cure.",
                      "Consistent prevention habits protect you and your community."])

        self.db.log_query(f"prevention: {disease}", "disease_info")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")

    def get_when_to_seek_care(self, disease: str, symptoms: Optional[str] = None) -> str:
        """Get guidance on when to seek medical care for a disease.

        Args:
            disease: Disease name.
            symptoms: Optional specific symptoms the person is experiencing.

        Returns:
            When to seek care guidance with disclaimer.
        """
        disease = disease.lower().strip().replace(" ", "_")
        aliases = {
            "tb": "tuberculosis",
            "hiv": "hiv_aids",
            "aids": "hiv_aids",
            "high_blood_pressure": "hypertension",
            "bp": "hypertension",
            "sugar": "diabetes",
            "hep": "hepatitis",
        }
        disease = aliases.get(disease, disease)

        lines = [
            "WHEN TO SEEK MEDICAL CARE",
            "========================",
            "",
        ]

        if disease in self.COMMON_AFRICAN_DISEASES:
            info = self.COMMON_AFRICAN_DISEASES[disease]
            lines.extend([f"Disease: {info['name']}", ""])
            lines.append("Seek medical care when:")
            for item in info["when_to_seek"]:
                lines.append(f"  - {item}")

            if info.get("severe_symptoms"):
                lines.extend(["", "EMERGENCY signs requiring IMMEDIATE care:"])
                for symptom in info["severe_symptoms"]:
                    lines.append(f"  * {symptom}")
        else:
            lines.append(f"Specific guidance not available for '{disease}'.")
            lines.append("General guidance:")
            lines.append("  - If symptoms worsen or don't improve after 3 days")
            lines.append("  - If you develop new symptoms")
            lines.append("  - If you have difficulty breathing")
            lines.append("  - If you have severe pain")
            lines.append("  - If you are confused or drowsy")

        if symptoms:
            lines.extend([
                "",
                f"Your reported symptoms: {symptoms}",
                "If these symptoms are severe, worsening, or concerning,",
                "seek medical care promptly.",
            ])

        lines.extend(["", "When in doubt, seek care. It is better to be evaluated",
                      "and told you are fine than to delay needed treatment."])

        self.db.log_query(f"when_to_seek: {disease}", "disease_info")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")



# ============================================================================
# NUTRITION GUIDE
# ============================================================================

class NutritionGuide:
    """Comprehensive nutrition guide using locally available African foods.

    Provides balanced diet recommendations, condition-specific food guidance,
    water and sanitation information, and common medication information.

    Methods:
        get_balanced_diet: Balanced diet using local foods.
        get_food_for_condition: Foods for specific health conditions.
        get_water_sanitation_guide: Clean water and hygiene practices.
        get_medication_info: Common medication information.
    """

    # Local African foods organized by food group
    AFRICAN_FOODS: Dict[str, List[str]] = {
        "grains_starch": [
            "Maize (corn, ugali, pap, sadza)",
            "Millet (finger millet, pearl millet)",
            "Sorghum",
            "Rice",
            "Wheat (bread, chapati)",
            "Cassava",
            "Sweet potatoes",
            "Irish potatoes",
            "Yam",
            "Plantain",
            "Cocoyam (taro)",
        ],
        "proteins": [
            "Beans (cowpeas, pigeon peas, black-eyed peas)",
            "Groundnuts (peanuts)",
            "Soybeans",
            "Lentils",
            "Chickpeas",
            "Eggs",
            "Fish (tilapia, sardines, mackerel, dried fish)",
            "Chicken",
            "Goat meat",
            "Beef",
            "Termites (white ants)",
            "Caterpillars",
            "Dried beans (njahi, ndengu)",
        ],
        "vegetables": [
            "Kale (sukuma wiki)",
            "Spinach",
            "Amaranth leaves (terere, mchicha)",
            "Pumpkin leaves",
            "Cassava leaves",
            "Cowpea leaves",
            "Cabbage",
            "Tomatoes",
            "Onions",
            "Carrots",
            "Okra",
            "Eggplant",
            "Moringa leaves",
            "Bitter leaf",
        ],
        "fruits": [
            "Mango",
            "Banana",
            "Papaya (pawpaw)",
            "Orange",
            "Guava",
            "Pineapple",
            "Avocado",
            "Watermelon",
            "Passion fruit",
            "Baobab fruit",
            "Tamarind",
            "Jackfruit",
        ],
        "dairy": [
            "Milk (fresh, powdered, fermented)",
            "Yogurt",
            "Cheese (where available)",
            "Traditional fermented milk (mala, lala, nono)",
        ],
        "fats_oils": [
            "Palm oil",
            "Groundnut oil",
            "Sunflower oil",
            "Coconut oil",
            "Sesame oil",
            "Shea butter",
            "Avocado",
            "Groundnut paste (peanut butter)",
        ],
    }

    # Condition-specific food recommendations
    CONDITION_FOODS: Dict[str, Dict[str, str]] = {
        "anemia": {
            "title": "Foods for Anemia (Low Blood)",
            "recommendations": """
IRON-RICH FOODS (eat daily):
- Dark leafy greens: kale, spinach, amaranth, moringa
- Liver (from cow, goat, or chicken) - very high in iron
- Beans and lentils: cowpeas, pigeon peas, kidney beans
- Red meat: beef, goat meat
- Dried fish and small fish eaten with bones
- Eggs
- Groundnuts and groundnut paste
- Fortified cereals and porridge

VITAMIN C foods (eat WITH iron-rich foods to boost absorption):
- Oranges, mangoes, guavas, tomatoes
- Pawpaw, pineapple
- Bell peppers

AVOID with iron-rich meals:
- Tea and coffee (reduce iron absorption)
- Too much calcium at the same meal

TIPS:
- Cook in iron pots when possible (adds iron to food)
- Soak beans and lentils before cooking
- Eat a variety of iron sources daily
- Combine plant and animal iron sources
- If iron supplements are prescribed, take with orange juice or other vitamin C source
""",
        },
        "diabetes": {
            "title": "Foods for Diabetes Management",
            "recommendations": """
FOODS TO EAT MORE:
- Non-starchy vegetables: kale, spinach, cabbage, okra, eggplant
- Whole grains: millet, sorghum, brown rice (in moderation)
- Legumes: beans, lentils, cowpeas, chickpeas (excellent for blood sugar)
- Fish: tilapia, sardines, mackerel
- Lean proteins: chicken (without skin), eggs
- Avocado (healthy fats)
- Nuts: groundnuts, cashews (unsalted, in moderation)

FOODS TO LIMIT:
- White bread, chapati made with white flour
- Sugary foods: sweets, cakes, sweetened drinks
- White rice and refined grains
- Large portions of starchy foods (ugali, cassava, potatoes)
- Sweetened tea and fruit juices
- Alcohol

TIPS:
- Eat smaller portions more frequently (3 meals + 2 snacks)
- Fill half your plate with vegetables
- Choose whole grains over refined grains
- Eat proteins with carbohydrates to slow sugar absorption
- Avoid skipping meals
- Cook with minimal oil
- Steam, boil, or grill instead of frying
- Monitor blood sugar regularly if you have a glucometer
- Maintain a healthy weight through diet and exercise
""",
        },
        "pregnancy": {
            "title": "Foods for Pregnancy",
            "recommendations": """
ESSENTIAL NUTRIENTS FOR PREGNANCY:

1. IRON (for blood and to prevent anemia):
   - Dark leafy greens (kale, spinach, moringa)
   - Liver (once per week)
   - Beans, lentils, cowpeas
   - Red meat
   - Dried fish with bones
   - Take iron supplements as prescribed

2. FOLIC ACID (prevents birth defects):
   - Dark leafy greens
   - Beans and lentils
   - Eggs
   - Fortified grains
   - Take folic acid supplements (400 mcg daily)

3. CALCIUM (for baby's bones):
   - Milk and dairy products
   - Small fish with bones
   - Green leafy vegetables
   - Groundnut paste

4. PROTEIN (for baby's growth):
   - Eggs
   - Fish, chicken, lean meat
   - Beans and lentils
   - Groundnuts
   - Soybeans

5. VITAMIN A (for vision and immunity):
   - Orange vegetables: carrots, pumpkin, sweet potato
   - Dark green vegetables
   - Liver
   - Eggs
   - Mangoes and papayas

6. VITAMIN C (boosts iron absorption):
   - Citrus fruits, mangoes, guavas
   - Tomatoes, peppers

FOODS TO AVOID:
- Raw or undercooked meat, fish, or eggs
- Unpasteurized milk and dairy
- Alcohol completely
- Excessive caffeine
- Certain traditional herbs (consult provider)

TIPS:
- Eat small, frequent meals to manage nausea
- Stay well hydrated (10+ glasses of water daily)
- Take prenatal vitamins as prescribed
- Eat a variety of foods from all food groups
""",
        },
        "hypertension": {
            "title": "Foods for High Blood Pressure",
            "recommendations": """
FOODS TO EAT MORE:
- Fruits: bananas, oranges, watermelon, pawpaw
  (rich in potassium which helps lower BP)
- Vegetables: spinach, kale, tomatoes, beetroot
- Whole grains: oats, brown rice, millet, sorghum
- Legumes: beans, lentils, cowpeas
- Fish: tilapia, sardines (rich in omega-3)
- Nuts: groundnuts, cashews (unsalted)
- Garlic and onions (may help lower BP)
- Hibiscus tea (zobo/roselle - may help lower BP)

FOODS TO AVOID/LIMIT:
- Salt: use less than 1 teaspoon (5g) per day TOTAL
  - Do not add salt at the table
  - Limit salty foods: salted fish, cured meats
  - Avoid stock cubes with high sodium (use herbs instead)
- Processed and packaged foods (usually high in salt)
- Pickled and fermented foods with lots of salt
- Alcohol
- Excessive caffeine

TIPS:
- Flavor food with herbs and spices instead of salt
  (garlic, ginger, onions, lemon, chili, curry powder)
- Read labels on packaged foods for sodium content
- Rinse canned foods to reduce salt
- Gradually reduce salt - your taste buds will adjust
- Maintain a healthy weight
- Exercise regularly
- Take prescribed blood pressure medication
""",
        },
        "wound_healing": {
            "title": "Foods for Wound Healing",
            "recommendations": """
NUTRIENTS FOR WOUND HEALING:

1. PROTEIN (essential for tissue repair):
   - Eggs
   - Fish, chicken, meat
   - Beans and lentils
   - Milk and dairy
   - Groundnuts

2. VITAMIN C (collagen formation):
   - Citrus fruits (oranges, lemons)
   - Guavas, mangoes, tomatoes
   - Pawpaw, pineapple

3. VITAMIN A (immune function):
   - Orange vegetables (carrots, pumpkin)
   - Dark green vegetables
   - Liver, eggs

4. ZINC (cell growth and repair):
   - Meat, fish, poultry
   - Beans, lentils, peas
   - Groundnuts, pumpkin seeds
   - Whole grains

5. IRON (for blood supply to wound):
   - Dark leafy greens
   - Red meat, liver
   - Beans
   - Dried fruit

HYDRATION:
- Drink plenty of clean water
- Stay well hydrated for optimal healing

TIPS:
- Eat a balanced diet with a variety of foods
- Do not skip meals
- Avoid smoking (delays wound healing)
- Keep wound clean and covered as instructed
""",
        },
        "diarrhea_recovery": {
            "title": "Foods for Diarrhea Recovery",
            "recommendations": """
WHAT TO EAT DURING AND AFTER DIARRHEA:

1. CONTINUE FEEDING (never stop eating):
   - Breastfeed infants more frequently
   - Give regular foods in small amounts

2. BRAT-TYPE FOODS (easy to digest):
   - Bananas
   - Rice (white rice is easier to digest)
   - Applesauce or stewed apples
   - Toast or plain bread

3. OTHER GOOD CHOICES:
   - Porridge (uji) made with millet or maize
   - Boiled potatoes
   - Plain boiled rice
   - Soft cooked carrots and pumpkin
   - Yogurt with live cultures (restores gut bacteria)
   - Soups and broths

4. WHAT TO AVOID:
   - Greasy, fried foods
   - Spicy foods
   - Very sugary foods and drinks
   - Cow's milk (may worsen diarrhea)
   - Coffee and tea
   - Alcohol

TIPS:
- Give ORS to prevent dehydration (most important!)
- Eat small amounts frequently
- Gradually return to normal diet as symptoms improve
- Give zinc supplements for 10-14 days
- Wash hands before preparing food
""",
        },
    }

    # Medication information
    MEDICATION_INFO: Dict[str, Dict[str, str]] = {
        "paracetamol": {
            "name": "Paracetamol (Acetaminophen)",
            "use": "Pain relief and fever reduction. First-line treatment for mild to moderate pain and fever.",
            "dosage": "Adults: 500mg-1g every 4-6 hours (max 4g/day). Children: 10-15mg/kg every 4-6 hours. Always follow package instructions or healthcare provider advice.",
            "warnings": "Do not exceed recommended dose (can cause liver damage). Be careful with combination products - check all medications for paracetamol content. Avoid alcohol. Use with caution in liver disease.",
            "side_effects": "Rare at normal doses. Overdose can cause severe liver damage.",
        },
        "ibuprofen": {
            "name": "Ibuprofen",
            "use": "Pain relief, fever reduction, and anti-inflammatory. Used for headaches, muscle pain, menstrual cramps, arthritis.",
            "dosage": "Adults: 200-400mg every 4-6 hours (max 1200mg/day OTC). Take with food. Children: use pediatric formulations and follow weight-based dosing.",
            "warnings": "Avoid in pregnancy (especially third trimester). Avoid if you have stomach ulcers, kidney disease, or are on blood thinners. Take with food to reduce stomach irritation. Do not use in children under 6 months.",
            "side_effects": "Stomach upset, heartburn, nausea. Long-term use can cause stomach ulcers and kidney problems.",
        },
        "amoxicillin": {
            "name": "Amoxicillin",
            "use": "Antibiotic used to treat bacterial infections (ear infections, throat infections, pneumonia, urinary tract infections).",
            "dosage": "Adults: 500mg three times daily. Children: dose based on weight. Duration typically 5-10 days. Complete FULL course even if feeling better.",
            "warnings": "Do NOT use for viral infections (colds, flu). Complete the full course. Avoid if allergic to penicillin. May reduce effectiveness of birth control pills.",
            "side_effects": "Diarrhea, nausea, rash. Allergic reactions (hives, difficulty breathing) require immediate medical attention.",
        },
        "artemether_lumefantrine": {
            "name": "Artemether-Lumefantrine (Coartem)",
            "use": "First-line antimalarial treatment. Treats uncomplicated malaria caused by Plasmodium falciparum.",
            "dosage": "Weight-based dosing. Typically 1-4 tablets depending on weight, twice daily for 3 days. Take with food or fatty drink to improve absorption.",
            "warnings": "Must be prescribed after confirmed malaria diagnosis (RDT or microscopy). Do not use for prevention. Not for severe malaria. Caution in heart conditions. Inform provider of all other medications.",
            "side_effects": "Headache, dizziness, loss of appetite, nausea, weakness, muscle/joint pain.",
        },
        "ors": {
            "name": "Oral Rehydration Salts (ORS)",
            "use": "Prevents and treats dehydration from diarrhea, vomiting, or excessive sweating. Saves lives in diarrheal diseases.",
            "dosage": "Dissolve one sachet in 1 liter of clean water. Give small frequent sips. Under 2 years: 50-100ml after each stool. 2-10 years: 100-200ml after each stool. Older: as much as needed.",
            "warnings": "Mix with EXACT amount of water. Discard after 24 hours. Prepare fresh solution daily. Homemade ORS: 6 level tsp sugar + 1/2 level tsp salt in 1 liter clean water.",
            "side_effects": "None when used correctly. Too concentrated can worsen diarrhea.",
        },
        "iron_supplements": {
            "name": "Iron Supplements (Ferrous Sulfate/Fumarate)",
            "use": "Treatment and prevention of iron-deficiency anemia. Essential for pregnant women, children, and those with anemia.",
            "dosage": "Adults: 65mg elemental iron daily (or as prescribed). Take on an empty stomach if tolerated. Children: dose based on weight as prescribed.",
            "warnings": "Take with vitamin C (orange juice) to improve absorption. Do not take with tea, coffee, or calcium. May cause dark stools (normal). Keep ALL iron supplements away from children - overdose can be fatal.",
            "side_effects": "Constipation, nausea, stomach upset, dark stools. Taking with food reduces side effects but also absorption.",
        },
        "metformin": {
            "name": "Metformin",
            "use": "First-line medication for Type 2 diabetes. Lowers blood sugar by reducing glucose production and improving insulin sensitivity.",
            "dosage": "Start 500mg once or twice daily with meals. Gradually increase as prescribed. Maximum 2000mg/day. Take with meals to reduce stomach upset.",
            "warnings": "Take with food. Regular blood sugar monitoring needed. Kidney function should be checked before starting. Do not use in severe kidney disease. Temporary discontinuation needed before contrast dye procedures.",
            "side_effects": "Stomach upset, diarrhea, nausea, metallic taste. Usually improves over time. Rare: lactic acidosis (seek care for unusual fatigue, muscle pain, breathing difficulty).",
        },
    }

    def __init__(self) -> None:
        """Initialize the NutritionGuide."""
        self.db = HealthRecordDB()
        logger.debug("NutritionGuide initialized")

    def get_balanced_diet(self, age: Optional[int] = None, condition: Optional[str] = None) -> str:
        """Get balanced diet recommendations using locally available foods.

        Args:
            age: Age in years (optional, for age-specific recommendations).
            condition: Health condition for tailored advice (optional).

        Returns:
            Balanced diet guidance with disclaimer.
        """
        lines = [
            "BALANCED DIET GUIDE - Using Locally Available Foods",
            "====================================================",
            "",
            "A balanced diet provides the nutrients your body needs to stay",
            "healthy, fight diseases, and maintain energy. Aim to eat foods",
            "from ALL food groups every day.",
            "",
            "THE 5 FOOD GROUPS:",
            "",
        ]

        for group, foods in self.AFRICAN_FOODS.items():
            group_name = group.replace("_", " ").title()
            lines.append(f"{group_name}:")
            for food in foods:
                lines.append(f"  - {food}")
            lines.append("")

        lines.extend([
            "DAILY EATING GUIDE:",
            "-------------------",
            "1. GRAINS/STARCH: Base of every meal. Provides energy.",
            "   - Examples: Ugali, rice, porridge, cassava, sweet potatoes",
            "   - Tip: Choose whole grains (millet, sorghum, brown rice) when possible",
            "",
            "2. PROTEINS: Build and repair the body. Essential for growth.",
            "   - Examples: Beans, eggs, fish, chicken, groundnuts",
            "   - Aim for at least 2 servings per day",
            "",
            "3. VEGETABLES: Provide vitamins, minerals, and fiber.",
            "   - Examples: Sukuma wiki, spinach, pumpkin leaves, cabbage",
            "   - Eat with EVERY meal. Aim for variety of colors.",
            "",
            "4. FRUITS: Provide vitamins, especially vitamin C.",
            "   - Examples: Mango, banana, pawpaw, orange, guava",
            "   - Eat 2-3 servings daily. Whole fruit is better than juice.",
            "",
            "5. FATS/OILS: Provide energy and help absorb vitamins.",
            "   - Examples: Palm oil, groundnut oil, avocado, groundnut paste",
            "   - Use in moderation. Choose healthy fats.",
            "",
        ])

        if age is not None:
            if age < 1:
                lines.append("AGE-SPECIFIC: Infant - Exclusive breastfeeding for first 6 months.")
            elif age < 3:
                lines.append("AGE-SPECIFIC: Toddler - 3 small meals + 2 snacks. Include all food groups.")
            elif age < 6:
                lines.append("AGE-SPECIFIC: Preschooler - 3 meals + 2 snacks. Variety is key.")
            elif age < 13:
                lines.append("AGE-SPECIFIC: School-age - Balanced meals for growth and learning.")
            elif age < 20:
                lines.append("AGE-SPECIFIC: Adolescent - Increased protein and iron needs.")
            elif age < 50:
                lines.append("AGE-SPECIFIC: Adult - Maintain balanced diet. Watch portion sizes.")
            else:
                lines.append("AGE-SPECIFIC: Older Adult - Ensure adequate protein. Eat nutrient-dense foods.")

        if condition:
            lines.extend(["", f"CONDITION-SPECIFIC: See also get_food_for_condition('{condition}')"])

        lines.extend(["", "TIPS FOR HEALTHY EATING:",
                      "- Eat a variety of foods every day",
                      "- Eat plenty of vegetables and fruits",
                      "- Eat less salt (less than 1 teaspoon per day)",
                      "- Use iodized salt",
                      "- Limit sugar and sugary drinks",
                      "- Drink plenty of clean water (8-10 glasses daily)",
                      "- Eat breakfast every day",
                      "- Do not skip meals",
                      "- Practice food hygiene: wash hands, cook thoroughly, store safely"])

        self.db.log_query(f"balanced_diet: age={age}", "nutrition")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")

    def get_food_for_condition(self, condition: str) -> str:
        """Get food recommendations for a specific health condition.

        Args:
            condition: Health condition. Options: 'anemia', 'diabetes',
                'pregnancy', 'hypertension', 'wound_healing', 'diarrhea_recovery'.

        Returns:
            Condition-specific food guidance with disclaimer.
        """
        condition = condition.lower().strip().replace(" ", "_")
        aliases = {
            "low_blood": "anemia",
            "low blood": "anemia",
            "sugar": "diabetes",
            "pregnant": "pregnancy",
            "bp": "hypertension",
            "high_bp": "hypertension",
            "high blood pressure": "hypertension",
            "wound": "wound_healing",
            "injury": "wound_healing",
            "diarrhoea": "diarrhea_recovery",
            "diarrhea": "diarrhea_recovery",
        }
        condition = aliases.get(condition, condition)

        if condition not in self.CONDITION_FOODS:
            available = ", ".join(self.CONDITION_FOODS.keys())
            result = (
                f"Food recommendations not available for '{condition}'.\n\n"
                f"Available conditions: {available}\n\n"
                f"General healthy eating advice:\n"
                f"- Eat a variety of foods from all food groups\n"
                f"- Eat plenty of fruits and vegetables\n"
                f"- Choose whole grains\n"
                f"- Include lean proteins\n"
                f"- Limit salt, sugar, and processed foods\n"
                f"- Stay hydrated"
            )
            return MedicalDisclaimer.wrap(result, "standard")

        info = self.CONDITION_FOODS[condition]
        result = f"{info['title']}\n{'=' * len(info['title'])}\n{info['recommendations']}"

        self.db.log_query(f"food_for_condition: {condition}", "nutrition")
        return MedicalDisclaimer.wrap(result, "standard")

    def get_water_sanitation_guide(self) -> str:
        """Get clean water and sanitation guidance.

        Returns:
            Water and sanitation guide with disclaimer.
        """
        guide = """
WATER AND SANITATION GUIDE
==========================

Clean water and good sanitation are the foundation of health.
They prevent diarrhea, cholera, typhoid, hepatitis, and many other diseases.

SAFE DRINKING WATER:
--------------------

1. WATER TREATMENT METHODS:

   a) BOILING (most reliable):
      - Bring water to a rolling boil for at least 1 minute
      - Let cool and store in clean, covered container
      - Boiled water tastes flat - pour between containers to add air

   b) CHLORINATION (water purification tablets/drops):
      - Follow instructions on the product exactly
      - Wait the recommended time before drinking
      - Water may taste slightly of chlorine (safe to drink)

   c) FILTRATION:
      - Use a certified water filter (ceramic, sand, or membrane)
      - Clean and maintain filter regularly
      - Some filters remove bacteria but not viruses - combine with
        chlorination if water may contain viruses

   d) SOLAR DISINFECTION (SODIS):
      - Fill clear plastic bottles with water
      - Leave in direct sunlight for at least 6 hours
      - Works best on sunny days
      - Best for clear water (not cloudy)

2. WATER STORAGE:
   - Store in clean, covered containers
   - Use containers with narrow openings or taps
   - Do not dip hands or cups into storage containers
   - Pour water out or use a clean tap
   - Clean storage containers regularly with soap

3. WATER SOURCES (from safest to least safe):
   - Piped water (treated)
   - Borehole with hand pump
   - Protected spring or well
   - Rainwater (if properly collected)
   - Unprotected spring or well
   - River, stream, or pond (least safe - must be treated)

SANITATION AND HYGIENE:
-----------------------

1. HAND WASHING (most important hygiene practice!):
   - Wash hands with soap and clean water:
     * Before eating or preparing food
     * After using the toilet or latrine
     * After cleaning a child
     * After touching animals
     * After handling waste
   - Scrub for at least 20 seconds
   - Dry with clean towel or air dry
   - If no soap, use ash and water (better than nothing)

2. TOILET USE:
   - Use a latrine or toilet (not open defecation)
   - Keep latrine clean and covered
   - Wash hands after every toilet use
   - Keep toilet area away from water sources

3. SAFE FOOD HANDLING:
   - Wash hands before preparing food
   - Wash fruits and vegetables with clean water
   - Cook food thoroughly (especially meat, fish, eggs)
   - Keep cooked food covered
   - Eat food while hot
   - Store leftovers properly and reheat thoroughly
   - Separate raw and cooked foods
   - Use clean utensils and surfaces

4. WASTE DISPOSAL:
   - Dispose of feces safely (use latrines)
   - Keep living areas clean
   - Dispose of garbage in designated areas
   - Keep animals away from living and cooking areas

5. MENSTRUAL HYGIENE:
   - Use clean sanitary pads, cloths, or menstrual cups
   - Change regularly (every 4-6 hours)
   - Wash reusable cloths with soap and dry in sunlight
   - Wash hands before and after changing
   - Dispose of used materials safely

COMMON WATER-RELATED DISEASES PREVENTED:
----------------------------------------
- Diarrhea and dysentery
- Cholera
- Typhoid
- Hepatitis A and E
- Guinea worm disease
- Bilharzia (schistosomiasis)
- Trachoma (eye infection)
"""
        return MedicalDisclaimer.wrap(guide, "standard")

    def get_medication_info(self, medication: str) -> str:
        """Get information about common medications.

        Args:
            medication: Medication name. Options include: 'paracetamol',
                'ibuprofen', 'amoxicillin', 'artemether_lumefantrine',
                'ors', 'iron_supplements', 'metformin'.

        Returns:
            Medication information with disclaimer.
        """
        medication = medication.lower().strip().replace(" ", "_")
        aliases = {
            "acetaminophen": "paracetamol",
            "panadol": "paracetamol",
            "brufen": "ibuprofen",
            "advil": "ibuprofen",
            "coartem": "artemether_lumefantrine",
            "artemether": "artemether_lumefantrine",
            "al": "artemether_lumefantrine",
            "oral_rehydration": "ors",
            "oral_rehydration_salts": "ors",
            "ferrous_sulfate": "iron_supplements",
            "ferrous_fumarate": "iron_supplements",
            "folic_acid": "iron_supplements",
        }
        medication = aliases.get(medication, medication)

        if medication not in self.MEDICATION_INFO:
            available = ", ".join(self.MEDICATION_INFO.keys())
            result = (
                f"Medication information not available for '{medication}'.\n\n"
                f"Available medications: {available}\n\n"
                f"IMPORTANT: Always consult a healthcare provider or pharmacist\n"
                f"before taking any medication. Never self-diagnose or self-treat\n"
                f"without professional guidance."
            )
            return MedicalDisclaimer.wrap(result, "standard")

        info = self.MEDICATION_INFO[medication]
        lines = [
            f"MEDICATION INFORMATION: {info['name']}",
            "=" * 60,
            "",
            f"USE: {info['use']}",
            "",
            f"DOSAGE: {info['dosage']}",
            "",
            f"WARNINGS:\n{info['warnings']}",
            "",
            f"SIDE EFFECTS:\n{info['side_effects']}",
            "",
            "IMPORTANT REMINDERS:",
            "- Always follow the instructions of your healthcare provider.",
            "- Read the medication label carefully.",
            "- Ask your pharmacist if you have any questions.",
            "- Store medications out of reach of children.",
            "- Check expiry dates before use.",
            "- Do not share prescription medications with others.",
            "- Inform your provider of ALL medications you are taking.",
            "- If you experience severe side effects, seek medical care immediately.",
        ]

        self.db.log_query(f"medication_info: {medication}", "nutrition")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")



# ============================================================================
# MENTAL HEALTH SUPPORT
# ============================================================================

class MentalHealthSupport:
    """Mental health support resources and coping strategies.

    Provides culturally appropriate mental health information for African
    contexts, including coping strategies, crisis helplines, and stigma
    reduction information. Mental health is an integral part of overall health.

    Methods:
        get_coping_strategies: Strategies for managing stress, grief, etc.
        get_crisis_resources: Mental health helplines by country.
        get_stigma_reduction_info: Information on reducing mental health stigma.
    """

    # Coping strategies by stressor type
    COPING_STRATEGIES: Dict[str, Dict[str, str]] = {
        "stress": {
            "title": "Coping with STRESS",
            "content": """
Stress is a normal response to life's challenges, but chronic stress
affects your physical and mental health. Learning to manage stress is
essential for wellbeing.

RECOGNIZE SIGNS OF STRESS:
- Feeling overwhelmed or unable to cope
- Irritability, anger, or mood swings
- Difficulty sleeping or sleeping too much
- Headaches, muscle tension, or stomach problems
- Difficulty concentrating
- Withdrawing from others
- Increased use of alcohol or tobacco

COPING STRATEGIES:

1. BREATHE DEEPLY:
   - Breathe in slowly through your nose for 4 counts
   - Hold for 4 counts
   - Breathe out through your mouth for 6 counts
   - Repeat 5-10 times. Do this whenever you feel stressed.

2. TALK TO SOMEONE:
   - Share your feelings with a trusted friend or family member
   - Talking helps process emotions and find solutions
   - You don't have to face everything alone

3. STAY ACTIVE:
   - Physical activity reduces stress hormones
   - Walk, dance, do farm work, or any movement you enjoy
   - Even 15 minutes of walking helps

4. TAKE BREAKS:
   - Step away from stressful situations when possible
   - Rest when you can - overworking increases stress
   - Do activities you enjoy: listening to music, gardening, socializing

5. MAINTAIN ROUTINES:
   - Regular sleep schedule (7-9 hours for adults)
   - Regular meals with nutritious food
   - Regular prayer or meditation

6. CONNECT WITH OTHERS:
   - Spend time with supportive people
   - Participate in community activities
   - Join a support group if available

7. PRACTICAL STEPS:
   - Break problems into smaller, manageable parts
   - Focus on what you can control
   - Set realistic goals
   - Ask for help when needed
   - Limit alcohol and avoid drugs

8. SPIRITUAL/RELIGIOUS PRACTICES:
   - Prayer and meditation can provide comfort
   - Attend religious services if meaningful to you
   - Spiritual community provides support
""",
        },
        "grief": {
            "title": "Coping with GRIEF and LOSS",
            "content": """
Grief is a natural response to losing someone or something important.
There is no 'right' way to grieve, and everyone experiences it differently.

COMMON GRIEF REACTIONS:
- Shock, disbelief, numbness
- Intense sadness and crying
- Anger or guilt
- Difficulty sleeping or eating
- Physical symptoms (fatigue, pain)
- Difficulty concentrating
- Withdrawing from others
- Questioning beliefs or purpose

COPING WITH GRIEF:

1. ALLOW YOURSELF TO GRIEVE:
   - Grief is not weakness - it is love
   - There is no timeline for grieving
   - Accept your feelings without judgment
   - Cry when you need to - it helps release emotions

2. TALK ABOUT YOUR LOSS:
   - Share memories and feelings with trusted people
   - Talk about the person who died - keeping their memory alive helps
   - Consider joining a bereavement support group
   - Writing in a journal can help process emotions

3. TAKE CARE OF YOUR PHYSICAL HEALTH:
   - Try to eat regular meals, even if you don't feel like it
   - Rest when you can - grief is exhausting
   - Gentle physical activity can help
   - Avoid alcohol as a way to cope

4. RELY ON YOUR SUPPORT SYSTEM:
   - Accept help from family and friends
   - Let people know what you need
   - Be with people who understand and comfort you
   - Community and family support is healing

5. HONOR YOUR LOVED ONE:
   - Find meaningful ways to remember them
   - Continue traditions they valued
   - Create a memorial or tribute
   - Live in a way that honors their memory

6. BE PATIENT WITH YOURSELF:
   - Healing takes time - there is no rush
   - Anniversaries and holidays may be especially difficult
   - It's okay to feel joy alongside grief
   - Seek professional help if grief feels overwhelming

WHEN TO SEEK PROFESSIONAL HELP:
- Inability to function in daily life after several months
- Thoughts of self-harm or suicide
- Extreme depression or hopelessness
- Using alcohol or drugs to cope
- Severe anxiety or panic attacks
- Isolating completely from everyone
- Inability to care for yourself or dependents
""",
        },
        "anxiety": {
            "title": "Coping with ANXIETY",
            "content": """
Anxiety is excessive worry or fear that interferes with daily life.
While some anxiety is normal, persistent anxiety that affects functioning
may need attention.

SIGNS OF ANXIETY:
- Excessive worry that is hard to control
- Restlessness or feeling on edge
- Fatigue and difficulty sleeping
- Difficulty concentrating
- Irritability
- Muscle tension
- Rapid heartbeat or shortness of breath
- Avoiding situations that cause anxiety

COPING STRATEGIES:

1. GROUNDING TECHNIQUE (5-4-3-2-1 method):
   - Name 5 things you can SEE
   - Name 4 things you can TOUCH
   - Name 3 things you can HEAR
   - Name 2 things you can SMELL
   - Name 1 thing you can TASTE
   - This brings you back to the present moment

2. CONTROLLED BREATHING:
   - Breathe in for 4 counts
   - Hold for 4 counts
   - Breathe out for 6 counts
   - Repeat until you feel calmer

3. CHALLENGE WORRYING THOUGHTS:
   - Ask: Is this thought realistic?
   - Ask: What is the worst that could happen? Could I handle it?
   - Ask: What would I tell a friend with this worry?
   - Replace catastrophic thoughts with balanced ones

4. LIMIT STIMULANTS:
   - Reduce caffeine (tea, coffee, energy drinks)
   - Avoid alcohol and drugs
   - Limit news and social media if they trigger anxiety

5. REGULAR EXERCISE:
   - Walking, dancing, or any physical activity reduces anxiety
   - Aim for at least 30 minutes most days
   - Exercise releases natural mood-boosting chemicals

6. ROUTINE AND STRUCTURE:
   - Regular sleep schedule
   - Regular meals
   - Structured daily activities
   - Predictability reduces anxiety

7. RELAXATION TECHNIQUES:
   - Progressive muscle relaxation (tense and relax each muscle group)
   - Prayer and meditation
   - Listening to calming music
   - Spending time in nature

8. SOCIAL CONNECTION:
   - Talk to trusted people about your feelings
   - Social support is protective against anxiety
   - Isolation worsens anxiety

WHEN TO SEEK PROFESSIONAL HELP:
- Anxiety interferes with work, school, or relationships
- Panic attacks (intense fear with physical symptoms)
- Avoiding important activities due to anxiety
- Anxiety persists for more than 2 weeks
- Physical symptoms without medical cause
""",
        },
        "depression": {
            "title": "Coping with DEPRESSION",
            "content": """
Depression is more than sadness. It is a medical condition that affects
mood, thinking, and daily functioning. It is NOT a sign of weakness,
and it is treatable. You are not alone.

SIGNS OF DEPRESSION:
- Persistent sad, empty, or hopeless mood
- Loss of interest in activities once enjoyed
- Changes in appetite or weight
- Difficulty sleeping or sleeping too much
- Fatigue and low energy
- Feelings of worthlessness or guilt
- Difficulty concentrating or making decisions
- Restlessness or slowed movements
- Thoughts of death or suicide

SELF-CARE STRATEGIES:

1. REACH OUT FOR SUPPORT:
   - Talk to someone you trust - a friend, family member, or elder
   - You do not have to carry this burden alone
   - Sharing your struggles is a sign of strength
   - Consider speaking to a counselor or healthcare provider

2. MAINTAIN CONNECTIONS:
   - Depression makes you want to isolate - resist this
   - Even brief contact with others helps
   - Sit with family, attend community events
   - Accept invitations even when you don't feel like it

3. STRUCTURE YOUR DAY:
   - Get up at the same time each day
   - Get dressed, even if you don't go anywhere
   - Do small tasks - accomplishment builds momentum
   - Set very small, achievable goals

4. PHYSICAL ACTIVITY:
   - Exercise is as effective as medication for mild depression
   - Start with a 10-minute walk
   - Gradually increase activity
   - Any movement counts

5. SUNLIGHT EXPOSURE:
   - Spend time outdoors in natural light
   - Open curtains and blinds at home
   - Sunlight helps regulate mood chemicals

6. EAT NUTRITIOUSLY:
   - Depression affects appetite - make effort to eat regularly
   - Include fruits, vegetables, and proteins
   - Limit alcohol (worsens depression)

7. CHALLENGE NEGATIVE THINKING:
   - Depression lies - not all negative thoughts are true
   - Ask: Would I say this to a friend?
   - Look for evidence against negative thoughts
   - Focus on small positives

8. SPIRITUAL AND CULTURAL PRACTICES:
   - Prayer and faith community can provide comfort
   - Traditional healing practices (alongside medical care)
   - Cultural rituals and community support

IMPORTANT - SEEK PROFESSIONAL HELP IF:
- Symptoms last more than 2 weeks
- You have thoughts of self-harm or suicide
- You cannot care for yourself or your family
- Symptoms are getting worse
- You have no support system

TREATMENT OPTIONS:
- Counseling/talking therapy (very effective)
- Antidepressant medication (if prescribed by a doctor)
- Combination of therapy and medication
- Community support groups
- Spiritual counseling

CRISIS: If you are thinking about hurting yourself,
seek help immediately from emergency services, a healthcare provider,
or a trusted person. Your life matters.
""",
        },
    }

    # Crisis resources by African country
    CRISIS_RESOURCES: Dict[str, Dict[str, Any]] = {
        "nigeria": {
            "name": "Nigeria",
            "helplines": [
                {"name": "Lagos State Emergency Mental Health Helpline", "number": "0800-333-3333"},
                {"name": "Mentally Aware Nigeria Initiative (MANI)", "number": "0809-111-6264"},
                {"name": "She Writes Woman Mental Health", "number": "0808-444-4444"},
            ],
            "services": "Mental health services available at tertiary hospitals and some general hospitals.",
        },
        "south_africa": {
            "name": "South Africa",
            "helplines": [
                {"name": "Suicide Crisis Helpline", "number": "0800-567-567"},
                {"name": "Lifeline South Africa", "number": "0861-322-322"},
                {"name": "SADAG (South African Depression and Anxiety Group)", "number": "0800-456-789"},
                {"name": "Cipla Mental Health Helpline", "number": "0800-456-789"},
            ],
            "services": "Mental health services available through public clinics, hospitals, and private practitioners.",
        },
        "kenya": {
            "name": "Kenya",
            "helplines": [
                {"name": "Befrienders Kenya", "number": "0722-178-177"},
                {"name": "Mental Health Helpline", "number": "1199"},
                {"name": "Niskize (Counseling line)", "number": "0900-620-800"},
            ],
            "services": "Mental health services available at county hospitals and some health centers.",
        },
        "ghana": {
            "name": "Ghana",
            "helplines": [
                {"name": "Mental Health Authority Helpline", "number": "055-331-4604"},
                {"name": "Samaritans Ghana", "number": "057-769-0904"},
            ],
            "services": "Psychiatric hospitals in Accra, Pantang, and Ankaful. Mental health units in regional hospitals.",
        },
        "uganda": {
            "name": "Uganda",
            "helplines": [
                {"name": "Mental Health Uganda", "number": "0800-111-333"},
                {"name": "Samaritans Uganda", "number": "0800-211-771"},
            ],
            "services": "Butabika National Referral Hospital and regional mental health units.",
        },
        "tanzania": {
            "name": "Tanzania",
            "helplines": [
                {"name": "Mental Health Helpline", "number": "0800-750-000"},
            ],
            "services": "Muhimbili National Hospital has psychiatric services. Mental health services at regional hospitals.",
        },
        "ethiopia": {
            "name": "Ethiopia",
            "helplines": [
                {"name": "Amanuel Mental Specialized Hospital", "number": "0112-760-111"},
            ],
            "services": "Amanuel Hospital in Addis Ababa is the main mental health facility. Regional psychiatric centers available.",
        },
        "rwanda": {
            "name": "Rwanda",
            "helplines": [
                {"name": "Mental Health Support Line", "number": "109"},
            ],
            "services": "Mental health services integrated into primary care. Specialized services at CHUK and district hospitals.",
        },
        "zambia": {
            "name": "Zambia",
            "helplines": [
                {"name": "Mental Health Helpline", "number": "909"},
                {"name": "Chainama Hills Hospital", "number": "0211-251-211"},
            ],
            "services": "Chainama Hills Hospital in Lusaka. Mental health units at UTH and some provincial hospitals.",
        },
    }

    def __init__(self) -> None:
        """Initialize the MentalHealthSupport guide."""
        self.db = HealthRecordDB()
        logger.debug("MentalHealthSupport initialized")

    def get_coping_strategies(self, stressor: str) -> str:
        """Get coping strategies for a specific stressor.

        Args:
            stressor: Type of stressor. Options: 'stress', 'grief',
                'anxiety', 'depression'.

        Returns:
            Coping strategies with disclaimer.
        """
        stressor = stressor.lower().strip().replace(" ", "_")
        aliases = {
            "worried": "anxiety",
            "worry": "anxiety",
            "worries": "anxiety",
            "sad": "depression",
            "sadness": "depression",
            "loss": "grief",
            "bereavement": "grief",
            "tension": "stress",
            "pressure": "stress",
        }
        stressor = aliases.get(stressor, stressor)

        if stressor not in self.COPING_STRATEGIES:
            available = ", ".join(self.COPING_STRATEGIES.keys())
            result = (
                f"Coping strategies not available for '{stressor}'.\n\n"
                f"Available topics: {available}\n\n"
                f"GENERAL MENTAL HEALTH TIPS:\n"
                f"- Talk to someone you trust about how you're feeling\n"
                f"- Take time for activities you enjoy\n"
                f"- Get regular physical activity\n"
                f"- Maintain a regular sleep schedule\n"
                f"- Eat nutritious meals\n"
                f"- Limit alcohol and avoid drugs\n"
                f"- Seek professional help if feelings persist or worsen"
            )
            return MedicalDisclaimer.wrap(result, "mental_health")

        info = self.COPING_STRATEGIES[stressor]
        result = f"{info['title']}\n{'=' * len(info['title'])}\n{info['content']}"

        self.db.log_query(f"coping_strategies: {stressor}", "mental_health")
        return MedicalDisclaimer.wrap(result, "mental_health")

    def get_crisis_resources(self, country: str) -> str:
        """Get mental health crisis resources for an African country.

        Args:
            country: Country name (e.g., 'nigeria', 'south_africa', 'kenya').

        Returns:
            Crisis resources with disclaimer.
        """
        country = country.lower().strip().replace(" ", "_")
        aliases = {
            "sa": "south_africa",
            "rsa": "south_africa",
        }
        country = aliases.get(country, country)

        lines = [
            "MENTAL HEALTH CRISIS RESOURCES",
            "==============================",
            "",
            "If you or someone you know is in crisis, help is available.",
            "You are NOT alone. Reaching out is a sign of strength.",
            "",
        ]

        if country in self.CRISIS_RESOURCES:
            info = self.CRISIS_RESOURCES[country]
            lines.extend([f"Resources for {info['name']}:", ""])
            for helpline in info["helplines"]:
                lines.append(f"  {helpline['name']}: {helpline['number']}")
            lines.extend(["", info["services"], ""])
        else:
            available = ", ".join(
                info["name"] for info in self.CRISIS_RESOURCES.values()
            )
            lines.extend([
                f"Specific resources not available for '{country}'.",
                f"Available countries: {available}",
                "",
            ])

        lines.extend([
            "GENERAL CRISIS SUPPORT:",
            "- Go to the nearest hospital emergency department",
            "- Contact your local health center",
            "- Speak to a trusted community leader, elder, or religious leader",
            "- Talk to a trusted family member or friend",
            "- Call your local emergency number (try 112)",
            "",
            "WHAT TO DO IN A MENTAL HEALTH CRISIS:",
            "1. Stay calm and do not leave the person alone",
            "2. Remove any means of self-harm if possible",
            "3. Listen without judgment",
            "4. Encourage them to seek professional help",
            "5. Accompany them to a health facility if needed",
            "6. Call emergency services if immediate danger",
            "",
            "REMEMBER: Mental health conditions are treatable.",
            "Seeking help is a sign of strength, not weakness.",
        ])

        self.db.log_query(f"crisis_resources: {country}", "mental_health")
        return MedicalDisclaimer.wrap("\n".join(lines), "mental_health")

    def get_stigma_reduction_info(self, condition: Optional[str] = None) -> str:
        """Get information on reducing mental health stigma.

        Args:
            condition: Specific mental health condition (optional).

        Returns:
            Stigma reduction information with disclaimer.
        """
        info = """
REDUCING MENTAL HEALTH STIGMA
=============================

Mental health stigma prevents people from seeking the help they need.
In many African communities, cultural beliefs and lack of understanding
contribute to stigma. Changing this starts with education and compassion.

UNDERSTANDING MENTAL HEALTH:
----------------------------

1. MENTAL HEALTH CONDITIONS ARE MEDICAL CONDITIONS:
   - Depression, anxiety, schizophrenia, and bipolar disorder are REAL
     medical conditions, just like diabetes or hypertension.
   - They are caused by a combination of biological, psychological,
     and social factors.
   - They are NOT caused by witchcraft, curses, or personal failure.
   - They are NOT signs of weakness or lack of faith.

2. MENTAL HEALTH CONDITIONS ARE COMMON:
   - 1 in 4 people worldwide will experience a mental health condition
     in their lifetime.
   - In Africa, millions of people live with mental health conditions.
   - You likely know several people who have experienced depression or anxiety.

3. MENTAL HEALTH CONDITIONS ARE TREATABLE:
   - Most people recover or manage well with proper treatment.
   - Treatment includes medication, counseling, and community support.
   - Early treatment leads to better outcomes.

HOW TO REDUCE STIGMA:
---------------------

1. EDUCATE YOURSELF AND OTHERS:
   - Learn the facts about mental health.
   - Share accurate information with your community.
   - Challenge myths and misconceptions when you hear them.

2. USE RESPECTFUL LANGUAGE:
   - Avoid words like 'crazy,' 'mad,' or 'insane' to describe people.
   - Say 'person with schizophrenia' not 'schizophrenic.'
   - Speak about mental health with the same respect as physical health.

3. SHOW COMPASSION:
   - Treat people with mental health conditions with dignity.
   - Listen without judgment.
   - Offer support and encouragement.
   - Include them in community activities.

4. SHARE STORIES:
   - When safe to do so, sharing experiences helps others feel less alone.
   - Recovery stories inspire hope.
   - Community leaders speaking about mental health reduces stigma.

5. SUPPORT COMMUNITY RESOURCES:
   - Advocate for mental health services in your community.
   - Support integration of mental health into primary healthcare.
   - Encourage training of community health workers in mental health.

6. IN RELIGIOUS/CULTURAL CONTEXTS:
   - Faith and mental health treatment can work together.
   - Prayer and spiritual support are valuable alongside medical care.
   - Religious leaders can play a positive role in reducing stigma.
   - Mental health conditions are not punishments from God.

COMMON MYTHS vs. FACTS:
-----------------------

MYTH: "Mental illness is caused by witchcraft or evil spirits."
FACT: Mental illness has biological causes and can be treated medically.

MYTH: "People with mental illness are violent and dangerous."
FACT: Most people with mental illness are not violent. They are more
      likely to be victims of violence than perpetrators.

MYTH: "Talking about suicide gives people the idea."
FACT: Talking about suicide openly can help someone seek help and
      can reduce their risk.

MYTH: "Mental health problems are a sign of weakness."
FACT: Mental health conditions can affect anyone regardless of strength,
      character, or faith.

MYTH: "You can just snap out of depression."
FACT: Depression is a medical condition that requires treatment,
      just like diabetes or malaria.

MYTH: "Children don't experience mental health problems."
FACT: Children can and do experience mental health conditions.
      Early support is crucial.
"""
        return MedicalDisclaimer.wrap(info, "mental_health")



# ============================================================================
# HEALTH FACILITY LOCATOR
# ============================================================================

class HealthFacilityLocator:
    """Health facility information and visit preparation guide.

    Provides information about different types of health facilities
    available in African communities and guidance on what to expect
    and how to prepare for visits.

    Methods:
        get_facility_types: Types of health facilities.
        get_what_to_expect: Preparing for a facility visit.
    """

    FACILITY_TYPES: Dict[str, Dict[str, str]] = {
        "hospital": {
            "name": "Hospital",
            "description": """
A hospital provides comprehensive medical care including emergency services,
surgery, specialized consultations, laboratory tests, and inpatient care.
Hospitals are staffed by doctors, nurses, and specialists.

WHEN TO GO:
- Medical emergencies
- Severe illness or injury
- Surgery needs
- Complicated pregnancy or delivery
- Specialized care (cardiology, neurology, etc.)
- Diagnostic tests (X-ray, ultrasound, CT scan)
- Conditions not manageable at lower-level facilities

WHAT TO EXPECT:
- Registration/triage area where your condition is assessed
- Possible waiting time depending on urgency
- Consultation with a doctor or clinical officer
- Possible diagnostic tests
- Treatment prescription or admission
- Payment required (fees vary; some services may be free at public hospitals)

TYPES OF HOSPITALS:
- National/Teaching Hospitals: Highest level of care, specialists
- Provincial/Regional Hospitals: Moderate to complex cases
- District Hospitals: General medical and surgical care
- Mission/Private Hospitals: Varying levels of care
""",
        },
        "clinic": {
            "name": "Health Clinic / Dispensary",
            "description": """
A clinic or dispensary provides basic outpatient medical care. Staffed by
clinical officers, nurses, or community health workers. This is often the
first point of contact for non-emergency health concerns.

WHEN TO GO:
- Common illnesses (cough, cold, mild fever)
- Minor injuries
- Chronic disease management (diabetes, hypertension follow-up)
- Immunizations
- Antenatal care (routine pregnancy check-ups)
- Family planning services
- Basic laboratory tests
- Health education and counseling

WHAT TO EXPECT:
- Registration with basic information
- Triage (vital signs: temperature, blood pressure, weight)
- Consultation with a clinical officer or nurse
- Prescription for medication
- Possible referral to hospital if condition is serious
- Shorter wait times than hospitals for routine care
- Lower cost than hospitals
""",
        },
        "health_center": {
            "name": "Health Center",
            "description": """
A health center is a mid-level facility between a clinic and a hospital.
It provides a broader range of services than a clinic, including maternity
care, some laboratory services, and management of more complex conditions.

WHEN TO GO:
- Routine antenatal and postnatal care
- Normal delivery (if equipped)
- Child health services (immunization, growth monitoring)
- Family planning
- Treatment of common illnesses
- Management of chronic conditions
- Laboratory tests (malaria RDT, HIV test, blood sugar, urinalysis)
- Health education

WHAT TO EXPECT:
- Registration
- Triage assessment
- Consultation with qualified health worker
- Possible laboratory tests
- Treatment or referral
- Community health worker involvement
""",
        },
        "pharmacy": {
            "name": "Pharmacy / Chemist",
            "description": """
A pharmacy or chemist dispenses medications prescribed by healthcare
providers. Some also provide basic health advice and over-the-counter
medications. Pharmacists are trained medication experts.

WHEN TO GO:
- Fill a prescription
- Purchase over-the-counter medications (paracetamol, ORS, etc.)
- Get advice about medications
- Check blood pressure (many pharmacies offer this)
- Purchase health supplies (bandages, thermometers, mosquito nets)
- Dispose of expired medications

WHAT TO EXPECT:
- Present your prescription
- Pharmacist may ask about allergies and other medications
- Receive medication with instructions
- Payment at point of service
- Pharmacist can explain how to take medications properly

IMPORTANT:
- Only purchase from licensed pharmacies
- Check expiry dates on all medications
- Ask about proper storage
- Do not use expired medications
- Pharmacists can identify drug interactions
""",
        },
        "community_health_worker": {
            "name": "Community Health Worker (CHW)",
            "description": """
Community Health Workers are trusted community members trained to provide
basic health services at the community level. They are often the first
point of contact, especially in rural areas.

SERVICES PROVIDED:
- Health education and promotion
- Distribution of insecticide-treated nets
- Screening for common conditions (malnutrition, danger signs)
- Referral to health facilities
- Follow-up of patients with chronic conditions
- Immunization reminders
- Maternal and child health home visits
- Distribution of condoms and family planning information
- Basic first aid

WHEN TO APPROACH:
- General health questions
- Need for health education
- Screening for child health
- Pregnancy registration and follow-up
- Need referral to a facility
- Questions about family planning
- Need for a community health activity

IMPORTANT:
- CHWs provide valuable services but cannot diagnose or prescribe
- They refer to facilities when conditions require professional care
- They play a vital role in connecting communities to health systems
""",
        },
        "traditional_healer": {
            "name": "Traditional Healer",
            "description": """
Traditional healers are respected community members who use indigenous
knowledge, herbs, and spiritual practices to address health concerns.
They remain an important part of healthcare in many African communities.

IMPORTANT SAFETY CONSIDERATIONS:
--------------------------------

1. INFORM YOUR HEALTHCARE PROVIDER:
   - Always tell your doctor or nurse about any traditional medicines
     you are using.
   - Some herbs can interact with conventional medications.
   - Your provider needs complete information to care for you safely.

2. TRADITIONAL MEDICINE AND CONVENTIONAL CARE CAN COEXIST:
   - Many people successfully use both systems.
   - Use traditional medicine for conditions it is known to help with.
   - Use conventional medicine for serious or life-threatening conditions.
   - Do not delay seeking conventional care for serious conditions.

3. BE AWARE OF RISKS:
   - Some traditional remedies may have side effects.
   - Quality and dosage of herbal preparations can vary.
   - Some remedies may be contaminated.
   - Certain herbs are toxic to the liver or kidneys.

4. SIGNS THAT YOU NEED CONVENTIONAL MEDICAL CARE:
   - Severe or worsening symptoms
   - Difficulty breathing
   - High fever
   - Severe pain
   - Signs of dehydration
   - Bleeding that won't stop
   - Pregnancy complications
   - Any condition not improving with traditional treatment

5. RESPECT BOTH SYSTEMS:
   - Traditional medicine has valuable knowledge accumulated over centuries.
   - Conventional medicine has scientific evidence for many treatments.
   - The best outcomes often come from respectful integration of both.
   - Choose qualified, respected practitioners in both systems.

COMMON SAFE TRADITIONAL PRACTICES:
- Steam inhalation for congestion
- Ginger tea for nausea
- Chamomile for mild anxiety
- Aloe vera for minor skin conditions
- Warm salt water gargle for sore throat
""",
        },
        "maternity_clinic": {
            "name": "Maternity Clinic / Antenatal Clinic",
            "description": """
Maternity clinics specialize in pregnancy care, childbirth, and postpartum
services. They provide antenatal care (ANC), delivery services, and
newborn care.

WHEN TO GO:
- Pregnancy confirmation
- Regular antenatal check-ups
- Delivery
- Postnatal check-ups
- Newborn care and immunization
- Family planning after delivery
- Breastfeeding support

WHAT TO EXPECT:
- Weight and blood pressure check
- Urine test for protein and sugar
- Blood tests (anemia, HIV, blood group)
- Abdominal examination
- Fetal heart rate monitoring
- Counseling on nutrition, danger signs, and birth preparation
- Immunizations (tetanus toxoid)
- Malaria prevention (IPTp)

VISIT SCHEDULE:
- First visit: As soon as pregnancy is suspected
- Then: Monthly until 28 weeks
- Then: Every 2 weeks until 36 weeks
- Then: Weekly until delivery
- Postnatal: Within 48 hours, then at 1-2 weeks, 6 weeks
""",
        },
        "diagnostic_center": {
            "name": "Diagnostic Center / Laboratory",
            "description": """
Diagnostic centers and laboratories perform medical tests to help diagnose
conditions. They may be standalone facilities or part of a hospital.

SERVICES:
- Blood tests (complete blood count, blood sugar, cholesterol)
- Malaria rapid diagnostic tests (RDT)
- HIV testing and counseling
- Urinalysis
- Stool examination
- Pregnancy tests
- Blood typing
- TB tests
- Hepatitis screening
- X-rays and imaging (at some centers)
- Ultrasound scans

WHAT TO EXPECT:
- Sample collection (blood, urine, stool)
- Some tests give results immediately (RDT, pregnancy test)
- Other tests may take hours to days
- Results usually given to you or sent to your healthcare provider
- Payment may be required at point of service

IMPORTANT:
- Fasting may be required for some blood tests (blood sugar, cholesterol)
- Bring identification
- Some tests require a referral from a healthcare provider
- Results should be discussed with a qualified healthcare provider
""",
        },
    }

    def __init__(self) -> None:
        """Initialize the HealthFacilityLocator."""
        self.db = HealthRecordDB()
        logger.debug("HealthFacilityLocator initialized")

    def get_facility_types(self) -> str:
        """Get information about types of health facilities.

        Returns:
            Facility types with descriptions and disclaimer.
        """
        lines = [
            "TYPES OF HEALTH FACILITIES",
            "==========================",
            "",
            "In most African communities, you can find these types of",
            "health facilities. Understanding what each offers helps you",
            "choose the right place for your health needs.",
            "",
        ]

        for key, info in self.FACILITY_TYPES.items():
            lines.append(f"{info['name']}")
            lines.append("-" * len(info['name']))
            lines.append(info["description"])
            lines.append("")

        lines.extend([
            "CHOOSING THE RIGHT FACILITY:",
            "-----------------------------",
            "1. For EMERGENCIES: Go to the nearest hospital immediately.",
            "2. For routine care: Start at a clinic or health center.",
            "3. For pregnancy: Register at a maternity clinic or hospital.",
            "4. For medications: Visit a licensed pharmacy.",
            "5. For tests: Go to a diagnostic center or hospital laboratory.",
            "6. For health advice: Community health workers can help guide you.",
            "",
            "Referral System:",
            "- Community Health Worker -> Clinic/Health Center -> Hospital",
            "- Lower-level facilities refer complex cases to higher-level ones.",
            "- Use this system to get the right care at the right level.",
        ])

        self.db.log_query("facility_types", "facility_info")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")

    def get_what_to_expect(self, facility_type: str) -> str:
        """Get guidance on what to expect and how to prepare for a visit.

        Args:
            facility_type: Type of facility ('hospital', 'clinic',
                'health_center', 'pharmacy', 'maternity_clinic',
                'diagnostic_center', 'traditional_healer').

        Returns:
            Visit preparation guide with disclaimer.
        """
        facility_type = facility_type.lower().strip().replace(" ", "_")
        aliases = {
            "chemist": "pharmacy",
            "dispensary": "clinic",
            "lab": "diagnostic_center",
            "laboratory": "diagnostic_center",
            "anc": "maternity_clinic",
            "maternity": "maternity_clinic",
            "chw": "community_health_worker",
            "herbalist": "traditional_healer",
        }
        facility_type = aliases.get(facility_type, facility_type)

        if facility_type not in self.FACILITY_TYPES:
            available = ", ".join(
                f"'{k}'" for k in self.FACILITY_TYPES.keys()
            )
            result = (
                f"Facility type '{facility_type}' not recognized.\n\n"
                f"Available types: {available}\n\n"
                f"GENERAL VISIT PREPARATION:\n"
                f"- Bring any identification documents\n"
                f"- Bring any previous medical records\n"
                f"- List all medications you are taking\n"
                f"- Note your symptoms and when they started\n"
                f"- Bring money for fees\n"
                f"- If possible, bring a companion\n"
                f"- Wear comfortable clothing"
            )
            return MedicalDisclaimer.wrap(result, "standard")

        info = self.FACILITY_TYPES[facility_type]
        lines = [
            f"VISITING A {info['name'].upper()}",
            "=" * 50,
            info["description"],
            "",
            "HOW TO PREPARE FOR YOUR VISIT:",
            "------------------------------",
        ]

        lines.extend([
            "1. BRING DOCUMENTS:",
            "   - Identification card",
            "   - Health insurance card (if available)",
            "   - Previous medical records or clinic cards",
            "   - Immunization card (for children)",
            "   - Antenatal card (for pregnant women)",
            "",
            "2. BRING INFORMATION:",
            "   - List of current medications (names and doses)",
            "   - List of allergies",
            "   - Note your symptoms and when they started",
            "   - Note any treatments you've already tried",
            "   - Family medical history (if relevant)",
            "",
            "3. BRING SUPPLIES:",
            "   - Money for consultation and medications",
            "   - Water and small snack (in case of long wait)",
            "   - Notebook and pen to write down instructions",
            "   - A companion (family member or friend)",
            "",
            "4. DURING THE VISIT:",
            "   - Arrive early",
            "   - Register at reception",
            "   - Be honest about your symptoms and concerns",
            "   - Ask questions if you don't understand",
            "   - Take notes on the diagnosis and treatment plan",
            "   - Ask about follow-up visits",
            "   - Know when to return if not improving",
            "",
            "5. AFTER THE VISIT:",
            "   - Follow treatment instructions exactly",
            "   - Take medications as prescribed (full course for antibiotics)",
            "   - Attend follow-up appointments",
            "   - Return to facility if symptoms worsen",
            "   - Keep your clinic card for future visits",
        ])

        self.db.log_query(f"what_to_expect: {facility_type}", "facility_info")
        return MedicalDisclaimer.wrap("\n".join(lines), "standard")



# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

# Singleton instances for module-level functions
_first_aid_guide: Optional[FirstAidGuide] = None
_maternal_guide: Optional[MaternalHealthGuide] = None
_child_guide: Optional[ChildHealthGuide] = None
_disease_info: Optional[DiseaseInformation] = None
_nutrition_guide: Optional[NutritionGuide] = None
_mental_health: Optional[MentalHealthSupport] = None
_facility_locator: Optional[HealthFacilityLocator] = None
_db: Optional[HealthRecordDB] = None


def _get_first_aid() -> FirstAidGuide:
    """Get or create FirstAidGuide singleton."""
    global _first_aid_guide
    if _first_aid_guide is None:
        _first_aid_guide = FirstAidGuide()
    return _first_aid_guide


def _get_maternal() -> MaternalHealthGuide:
    """Get or create MaternalHealthGuide singleton."""
    global _maternal_guide
    if _maternal_guide is None:
        _maternal_guide = MaternalHealthGuide()
    return _maternal_guide


def _get_child() -> ChildHealthGuide:
    """Get or create ChildHealthGuide singleton."""
    global _child_guide
    if _child_guide is None:
        _child_guide = ChildHealthGuide()
    return _child_guide


def _get_disease() -> DiseaseInformation:
    """Get or create DiseaseInformation singleton."""
    global _disease_info
    if _disease_info is None:
        _disease_info = DiseaseInformation()
    return _disease_info


def _get_nutrition() -> NutritionGuide:
    """Get or create NutritionGuide singleton."""
    global _nutrition_guide
    if _nutrition_guide is None:
        _nutrition_guide = NutritionGuide()
    return _nutrition_guide


def _get_mental() -> MentalHealthSupport:
    """Get or create MentalHealthSupport singleton."""
    global _mental_health
    if _mental_health is None:
        _mental_health = MentalHealthSupport()
    return _mental_health


def _get_facility() -> HealthFacilityLocator:
    """Get or create HealthFacilityLocator singleton."""
    global _facility_locator
    if _facility_locator is None:
        _facility_locator = HealthFacilityLocator()
    return _facility_locator


def _get_db() -> HealthRecordDB:
    """Get or create HealthRecordDB singleton."""
    global _db
    if _db is None:
        _db = HealthRecordDB()
    return _db


def health_info(query: str, age: Optional[int] = None, country: Optional[str] = None) -> str:
    """Get general health information based on a query.

    This is the main entry point for general health questions.
    It attempts to route the query to the appropriate guide based on
    keywords detected in the query.

    Args:
        query: The health question or topic.
        age: Age of the person (optional, for age-specific guidance).
        country: Country name (optional, for localized information).

    Returns:
        Health information response with medical disclaimer.

    Examples:
        >>> health_info("What are malaria symptoms?")
        >>> health_info("How do I treat a burn?")
        >>> health_info("Pregnancy week 20 guidance", age=25, country="kenya")
    """
    query_lower = query.lower().strip()
    _get_db().log_query(query, "general", age, country)

    # Route to appropriate guide based on keywords
    first_aid_keywords = [
        "first aid", "emergency", "choking", "bleeding", "burn", "fracture",
        "broken", "poison", "heat stroke", "heatstroke", "snake", "drown",
        "cpr", "unconscious", "wound", "cut", "injury",
    ]
    maternal_keywords = [
        "pregnancy", "pregnant", "prenatal", "antenatal", "birth", "delivery",
        "labor", "labour", "postnatal", "postpartum", "newborn", "baby care",
        "breastfeeding", "morning sickness", "gestation",
    ]
    child_keywords = [
        "child", "children", "baby", "infant", "toddler", "immunization",
        "vaccine", "vaccination", "malnutrition", "muac", "childhood illness",
        "diarrhea", "pneumonia", "measles", "ors", "feeding",
    ]
    disease_keywords = [
        "malaria", "typhoid", "cholera", "hiv", "aids", "tuberculosis", "tb",
        "hepatitis", "diabetes", "hypertension", "high blood pressure",
        "sickle cell", "fever", "cough", "disease",
    ]
    nutrition_keywords = [
        "nutrition", "diet", "food", "eat", "eating", "malnutrition",
        "anemia", "iron", "vitamin", "protein", "water", "sanitation",
        "hygiene", "medication", "medicine", "drug", "ors",
    ]
    mental_keywords = [
        "mental health", "depression", "anxiety", "stress", "grief", "sad",
        "suicide", "stigma", "counseling", "therapy", "coping",
    ]
    facility_keywords = [
        "hospital", "clinic", "facility", "pharmacy", "chemist",
        "doctor", "nurse", "health center", "where to go",
    ]

    if any(kw in query_lower for kw in first_aid_keywords):
        guide = _get_first_aid()
        # Extract emergency type from query
        for etype in guide.FIRST_AID_PROCEDURES:
            if etype in query_lower:
                return guide.get_first_aid(etype)
        return guide.assess_urgency(query)

    if any(kw in query_lower for kw in maternal_keywords):
        guide = _get_maternal()
        if "danger" in query_lower:
            return guide.get_danger_signs_pregnancy()
        if "childbirth" in query_lower or "labor" in query_lower or "birth" in query_lower:
            return guide.get_childbirth_prep()
        if "newborn" in query_lower:
            return guide.get_newborn_care()
        if "postnatal" in query_lower or "postpartum" in query_lower:
            return guide.get_postnatal_care(week=1)
        return guide.get_prenatal_care(week=query_lower.count("week") + 1 if "week" in query_lower else 1)

    if any(kw in query_lower for kw in child_keywords):
        guide = _get_child()
        if "immunization" in query_lower or "vaccine" in query_lower or "vaccination" in query_lower:
            return guide.get_immunization_schedule(country or "nigeria")
        if "malnutrition" in query_lower or "muac" in query_lower:
            return guide.assess_malnutrition(age_months=age or 12, muac_cm=12.0)
        if "ors" in query_lower or "rehydration" in query_lower or "diarrhea" in query_lower:
            return guide.get_oral_rehydration_guide()
        if "feed" in query_lower or "nutrition" in query_lower or "eat" in query_lower:
            return guide.get_child_nutrition(age="0-6_months" if age and age < 1 else "2-5_years")
        for illness in guide.CHILDHOOD_ILLNESSES:
            if illness in query_lower:
                return guide.get_common_childhood_illnesses(illness)
        return guide.get_child_nutrition(age="0-6_months")

    if any(kw in query_lower for kw in disease_keywords):
        guide = _get_disease()
        for disease in guide.COMMON_AFRICAN_DISEASES:
            if disease.replace("_", " ") in query_lower or disease in query_lower:
                if "prevent" in query_lower:
                    return guide.get_prevention(disease)
                if "when" in query_lower or "seek" in query_lower:
                    return guide.get_when_to_seek_care(disease)
                return guide.get_disease_info(disease)
        return guide.get_disease_info("malaria")

    if any(kw in query_lower for kw in nutrition_keywords):
        guide = _get_nutrition()
        if "water" in query_lower or "sanitation" in query_lower or "hygiene" in query_lower:
            return guide.get_water_sanitation_guide()
        if "medication" in query_lower or "medicine" in query_lower or "drug" in query_lower:
            return guide.get_medication_info("paracetamol")
        if "condition" in query_lower:
            return guide.get_food_for_condition("anemia")
        return guide.get_balanced_diet(age=age)

    if any(kw in query_lower for kw in mental_keywords):
        guide = _get_mental()
        if "stigma" in query_lower:
            return guide.get_stigma_reduction_info()
        if "crisis" in query_lower or "helpline" in query_lower or "suicide" in query_lower:
            return guide.get_crisis_resources(country or "nigeria")
        for stressor in guide.COPING_STRATEGIES:
            if stressor in query_lower:
                return guide.get_coping_strategies(stressor)
        return guide.get_coping_strategies("stress")

    if any(kw in query_lower for kw in facility_keywords):
        guide = _get_facility()
        if "expect" in query_lower or "prepare" in query_lower:
            return guide.get_what_to_expect("hospital")
        return guide.get_facility_types()

    # Default response
    result = (
        f"Health Information Query: {query}\n\n"
        f"I understand you're asking about health information.\n\n"
        f"Here are some topics I can help with:\n"
        f"- First aid and emergencies\n"
        f"- Maternal health (pregnancy, childbirth, newborn care)\n"
        f"- Child health (immunizations, common illnesses, nutrition)\n"
        f"- Disease information (malaria, HIV, diabetes, etc.)\n"
        f"- Nutrition and healthy eating\n"
        f"- Mental health support\n"
        f"- Health facility information\n\n"
        f"Please try asking a more specific question, or contact your\n"
        f"local healthcare provider for personalized guidance."
    )
    return MedicalDisclaimer.wrap(result, "standard")


def first_aid(emergency_type: str) -> str:
    """Get first aid guidance for an emergency.

    Args:
        emergency_type: Type of emergency. Options include:
            'choking', 'bleeding', 'burns', 'fractures',
            'poisoning', 'heatstroke', 'snake_bite', 'drowning', 'cpr'.

    Returns:
        First aid instructions with emergency disclaimer.

    Examples:
        >>> first_aid("burns")
        >>> first_aid("snake_bite")
        >>> first_aid("cpr")
    """
    return _get_first_aid().get_first_aid(emergency_type)


def check_symptoms(
    symptoms: Union[str, List[str]],
    age: Optional[int] = None,
    country: Optional[str] = None,
) -> str:
    """Check symptoms and get health information (NOT diagnosis).

    IMPORTANT: This function provides health information only.
    It does NOT diagnose medical conditions. Always consult a
    healthcare professional for proper diagnosis and treatment.

    Args:
        symptoms: Symptom description (string or list of strings).
        age: Age of the person in years (optional).
        country: Country for context (optional).

    Returns:
        Symptom assessment with health information and disclaimers.

    Examples:
        >>> check_symptoms("fever and headache")
        >>> check_symptoms(["fever", "cough", "fatigue"], age=5)
        >>> check_symptoms("chest pain", age=45, country="nigeria")
    """
    _get_db().log_query(f"symptoms: {symptoms}", "symptom_check", age, country)

    if isinstance(symptoms, str):
        symptoms_list = [symptoms]
    else:
        symptoms_list = symptoms

    symptoms_lower = " ".join(s.lower() for s in symptoms_list)

    lines = [
        "SYMPTOM INFORMATION (NOT A DIAGNOSIS)",
        "=====================================",
        "",
        "IMPORTANT: This is health information only. It is NOT a medical",
        "diagnosis. Only a qualified healthcare professional can diagnose",
        "medical conditions after proper examination and testing.",
        "",
        f"Reported symptoms: {', '.join(symptoms_list)}",
    ]

    if age is not None:
        lines.append(f"Age: {age} years")
    if country:
        lines.append(f"Country: {country.title()}")

    lines.append("")

    # Urgency assessment
    fa_guide = _get_first_aid()
    urgency = fa_guide.assess_urgency(symptoms_list)
    # Extract just the urgency part
    lines.append(urgency.split("=== MEDICAL DISCLAIMER ===")[0].strip())
    lines.append("")

    # Try to match to disease information
    disease_guide = _get_disease()
    matched_diseases = []
    for disease_key, disease_data in disease_guide.COMMON_AFRICAN_DISEASES.items():
        disease_symptoms = " ".join(disease_data.get("symptoms", [])).lower()
        for symptom in symptoms_list:
            if symptom.lower() in disease_symptoms:
                matched_diseases.append(disease_key)
                break

    if matched_diseases:
        lines.append("RELEVANT DISEASE INFORMATION:")
        lines.append("The following conditions can cause similar symptoms.")
        lines.append("This does NOT mean you have any of these conditions.")
        lines.append("")
        for disease in matched_diseases[:3]:  # Limit to top 3
            info = disease_guide.COMMON_AFRICAN_DISEASES[disease]
            lines.append(f"- {info['name']}: {info['description'].strip()[:200]}...")
        lines.append("")

    lines.extend([
        "NEXT STEPS:",
        "-----------",
        "1. Monitor your symptoms closely.",
        "2. If symptoms are severe or worsening, seek medical care immediately.",
        "3. For mild symptoms, rest, hydrate, and monitor for 24-48 hours.",
        "4. If symptoms persist beyond 3 days, consult a healthcare provider.",
        "5. Keep a symptom diary (what, when, severity, triggers).",
        "",
        "Remember: When in doubt, seek professional medical advice.",
        "Self-diagnosis can be dangerous. Your health is worth the visit.",
    ])

    return MedicalDisclaimer.wrap("\n".join(lines), "standard")


def maternal_health(topic: str, week: Optional[int] = None) -> str:
    """Get maternal health information.

    Args:
        topic: Topic of interest. Options include:
            'prenatal', 'danger_signs', 'childbirth', 'postnatal', 'newborn'.
        week: Week number for pregnancy or postpartum guidance (optional).

    Returns:
        Maternal health information with pregnancy disclaimer.

    Examples:
        >>> maternal_health("prenatal", week=20)
        >>> maternal_health("danger_signs")
        >>> maternal_health("childbirth")
        >>> maternal_health("postnatal", week=2)
        >>> maternal_health("newborn")
    """
    guide = _get_maternal()
    topic = topic.lower().strip().replace(" ", "_")

    if topic in ["prenatal", "pregnancy", "antenatal"]:
        return guide.get_prenatal_care(week or 1)
    elif topic in ["danger_signs", "danger", "warning"]:
        return guide.get_danger_signs_pregnancy()
    elif topic in ["childbirth", "birth", "labor", "delivery"]:
        return guide.get_childbirth_prep()
    elif topic in ["postnatal", "postpartum", "after_birth"]:
        return guide.get_postnatal_care(week or 1)
    elif topic in ["newborn", "baby", "infant"]:
        return guide.get_newborn_care()
    else:
        result = (
            f"Maternal health topic '{topic}' not recognized.\n\n"
            f"Available topics:\n"
            f"- 'prenatal' (with week number)\n"
            f"- 'danger_signs'\n"
            f"- 'childbirth'\n"
            f"- 'postnatal' (with week number)\n"
            f"- 'newborn'\n\n"
            f"For any pregnancy or maternal health concern,\n"
            f"consult a qualified maternity care provider."
        )
        return MedicalDisclaimer.wrap(result, "pregnancy")


def child_health(topic: str, age: Optional[int] = None) -> str:
    """Get child health guidance.

    Args:
        topic: Topic of interest. Options include:
            'immunization', 'malnutrition', 'illness', 'ors', 'nutrition'.
        age: Age in months (optional, for age-specific guidance).

    Returns:
        Child health information with child safety disclaimer.

    Examples:
        >>> child_health("immunization")
        >>> child_health("malnutrition", age=18)
        >>> child_health("illness")
        >>> child_health("nutrition", age=8)
    """
    guide = _get_child()
    topic = topic.lower().strip().replace(" ", "_")

    if topic in ["immunization", "vaccine", "vaccination", "immunisation"]:
        return guide.get_immunization_schedule("nigeria")
    elif topic in ["malnutrition", "muac", "nutrition_screening"]:
        return guide.assess_malnutrition(age_months=age or 12, muac_cm=12.5)
    elif topic in ["illness", "disease", "sick", "sickness"]:
        return guide.get_common_childhood_illnesses("malaria")
    elif topic in ["ors", "rehydration", "diarrhea", "diarrhoea"]:
        return guide.get_oral_rehydration_guide()
    elif topic in ["nutrition", "feeding", "food", "eat"]:
        age_map = {
            None: "0-6_months",
        }
        if age is not None:
            if age <= 6:
                age_key = "0-6_months"
            elif age <= 9:
                age_key = "6-9_months"
            elif age <= 12:
                age_key = "9-12_months"
            elif age <= 24:
                age_key = "12-24_months"
            else:
                age_key = "2-5_years"
        else:
            age_key = "0-6_months"
        return guide.get_child_nutrition(age=age_key)
    else:
        result = (
            f"Child health topic '{topic}' not recognized.\n\n"
            f"Available topics:\n"
            f"- 'immunization'\n"
            f"- 'malnutrition' (with age in months)\n"
            f"- 'illness'\n"
            f"- 'ors' (oral rehydration)\n"
            f"- 'nutrition' (with age in months)\n\n"
            f"For any child health concern, consult a pediatric healthcare provider.\n"
            f"Children should be assessed promptly as they can deteriorate quickly."
        )
        return MedicalDisclaimer.wrap(result, "children")


def nutrition_advice(age: int, condition: Optional[str] = None) -> str:
    """Get nutrition guidance for a specific age and optional condition.

    Args:
        age: Age in years.
        condition: Health condition for tailored nutrition advice (optional).
            Options: 'anemia', 'diabetes', 'pregnancy', 'hypertension',
            'wound_healing', 'diarrhea_recovery'.

    Returns:
        Nutrition guidance with disclaimer.

    Examples:
        >>> nutrition_advice(30)
        >>> nutrition_advice(25, condition="anemia")
        >>> nutrition_advice(45, condition="diabetes")
    """
    guide = _get_nutrition()

    if condition:
        return guide.get_food_for_condition(condition)

    return guide.get_balanced_diet(age=age)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point for interactive use of the healthcare assistant.

    Demonstrates key functionality of the Luqi Healthcare Assistant.
    Can be run directly for a quick health information demo.
    """
    print("=" * 70)
    print("LUQI AI v20 - Healthcare Assistant for Africa")
    print("=" * 70)
    print()
    print("This assistant provides health INFORMATION only.")
    print("It does NOT provide medical diagnosis or replace qualified")
    print("healthcare professionals.")
    print()
    print(MedicalDisclaimer.STANDARD_DISCLAIMER)
    print()
    print("=" * 70)
    print()

    # Demo: First Aid
    print("DEMO 1: First Aid - Burns")
    print("-" * 40)
    print(first_aid("burns")[:800])
    print("...")
    print()

    # Demo: Emergency Numbers
    print("DEMO 2: Emergency Numbers - Nigeria")
    print("-" * 40)
    print(_get_first_aid().get_emergency_numbers("nigeria"))
    print()

    # Demo: Disease Information
    print("DEMO 3: Disease Information - Malaria")
    print("-" * 40)
    print(_get_disease().get_disease_info("malaria")[:800])
    print("...")
    print()

    # Demo: Maternal Health
    print("DEMO 4: Maternal Health - Pregnancy Week 20")
    print("-" * 40)
    print(_get_maternal().get_prenatal_care(20)[:800])
    print("...")
    print()

    # Demo: Child Health
    print("DEMO 5: Child Health - Immunization Schedule (Kenya)")
    print("-" * 40)
    print(_get_child().get_immunization_schedule("kenya"))
    print()

    # Demo: Nutrition
    print("DEMO 6: Nutrition - Foods for Anemia")
    print("-" * 40)
    print(_get_nutrition().get_food_for_condition("anemia")[:800])
    print("...")
    print()

    # Demo: Mental Health
    print("DEMO 7: Mental Health - Coping with Stress")
    print("-" * 40)
    print(_get_mental().get_coping_strategies("stress")[:800])
    print("...")
    print()

    # Demo: Facility Information
    print("DEMO 8: Health Facility Types")
    print("-" * 40)
    print(_get_facility().get_facility_types()[:800])
    print("...")
    print()

    print("=" * 70)
    print("Demo complete. Import this module to use all features.")
    print("Example: from healthcare_assistant import health_info, first_aid")
    print("=" * 70)


if __name__ == "__main__":
    main()
