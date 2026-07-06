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
