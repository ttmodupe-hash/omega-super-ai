"""
Luqi AI - Automotive Diagnostic Module
========================================
A comprehensive automotive diagnostic AI that helps vehicle owners troubleshoot
mechanical issues safely and cost-effectively. Follows a strict diagnostic
protocol to prevent blind parts-buying.

Author: Luqi AI Engineering Team
Version: 1.0.0
License: Proprietary

This module provides:
- Symptom analysis across 5 categories (sounds, feel, smells, visual, timing)
- Differential diagnosis with probability-ranked causes
- Zero-cost inspection procedures (check-before-buy)
- Safety filtering for critical vehicle systems
- OBD-II diagnostic trouble code database
- Vehicle systems reference with maintenance intervals
- Repair cost estimation with DIY difficulty ratings

Usage:
    from automotive import diagnose, parse_symptoms, lookup_obd2
    result = diagnose(["grinding when braking"], {"year": 2015, "make": "Toyota"})
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass, field
from enum import Enum
import json


# =============================================================================
# CONSTANTS AND ENUMS
# =============================================================================

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CostTier(str, Enum):
    LOW = "low"       # Under $100
    MEDIUM = "medium"  # $100 - $500
    HIGH = "high"      # $500 - $1500
    VERY_HIGH = "very_high"  # Over $1500


class UrgencyLevel(str, Enum):
    IMMEDIATE = "immediate"  # Stop driving now
    SOON = "soon"            # Within a few days
    ROUTINE = "routine"      # Next maintenance window
    INFO = "info"            # For awareness


# =============================================================================
# SECTION 1: SYMPTOM ANALYSIS ENGINE
# =============================================================================
# Comprehensive symptom database organized by perceptual category.
# Each symptom maps to probable causes with diagnostic metadata.

SYMPTOM_DATABASE: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # CATEGORY: SOUNDS
    # -------------------------------------------------------------------------
    "sounds": {
        "chirping": {
            "causes": [
                {"name": "Worn serpentine belt", "probability": 0.85, "cost": "low", "severity": "medium", "inspection": "Visual belt check for cracks/glazing"},
                {"name": "Faulty belt tensioner", "probability": 0.60, "cost": "medium", "severity": "medium", "inspection": "Check tensioner pulley for wobble/play"},
                {"name": "Alternator bearing wear", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Remove belt and spin alternator pulley by hand"},
                {"name": "Idler pulley bearing failure", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Remove belt and spin each pulley by hand, listen for noise"},
                {"name": "A/C compressor clutch wear", "probability": 0.20, "cost": "high", "severity": "low", "inspection": "Engage/disengage A/C while listening for noise change"},
            ],
            "safety_note": "Belt failure can cause overheating and loss of power steering. Inspect immediately if chirping is loud or constant.",
        },
        "grinding": {
            "causes": [
                {"name": "Worn brake pads (metal-on-metal)", "probability": 0.90, "cost": "low", "severity": "high", "inspection": "Remove wheel and visually inspect pad thickness"},
                {"name": "Wheel bearing failure", "probability": 0.70, "cost": "medium", "severity": "high", "inspection": "Jack up car, wiggle wheel at 12 and 6 o'clock positions"},
                {"name": "Transmission gear wear", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Check transmission fluid level and color"},
                {"name": "Differential gear wear", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Check differential fluid level and condition"},
                {"name": "Starter motor gear not retracting", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Check if grinding occurs only during or right after starting"},
            ],
            "safety_note": "CRITICAL SAFETY WARNING: Grinding brakes or wheel bearings can cause sudden component failure. Inspect immediately before driving further.",
        },
        "thumping": {
            "causes": [
                {"name": "Flat-spotted tire", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Visual tire inspection for uneven wear or flat spots"},
                {"name": "Worn shock absorber", "probability": 0.65, "cost": "medium", "severity": "medium", "inspection": "Bounce each corner of car -- should settle in 1-2 cycles"},
                {"name": "Driveshaft/CV joint worn", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Check CV boots for tears, inspect for grease leaks"},
                {"name": "Separated tire tread (tire failure)", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Inspect tire tread for bulges, separations, or exposed cords"},
                {"name": "Engine mount broken", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Open hood, have assistant shift between D and R, watch engine movement"},
                {"name": "Exhaust pipe hitting underbody", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Inspect exhaust hangers and mounts from under vehicle"},
            ],
            "safety_note": "Thumping from tires at speed can indicate impending tire failure. Reduce speed and inspect immediately.",
        },
        "squealing": {
            "causes": [
                {"name": "Brake pad wear indicator", "probability": 0.88, "cost": "low", "severity": "medium", "inspection": "Check brake pad thickness through caliper inspection hole"},
                {"name": "Worn serpentine belt", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Visual belt check for cracks, glazing, or contamination"},
                {"name": "Loose belt tension", "probability": 0.55, "cost": "low", "severity": "low", "inspection": "Press on belt mid-span -- should deflect approximately 1 inch"},
                {"name": "Worn accessory bearings (alternator, power steering)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Remove belt, spin each pulley by hand, listen for roughness"},
                {"name": "Brake dust buildup", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Clean brakes with brake cleaner spray and test drive"},
                {"name": "Glazed brake pads or rotors", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Inspect rotor surface for mirror-like glaze or scoring"},
            ],
            "safety_note": "Squealing brake pads indicate they are nearing end of life. Schedule replacement within 500 miles.",
        },
    },
}
