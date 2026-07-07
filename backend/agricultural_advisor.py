#!/usr/bin/env python3
"""Luqi AI v20 - Agricultural Advisor for Africa
=================================================
AI farming advisor optimized for African smallholder farmers.
Covers crops, livestock, pest control, weather, markets, and climate resilience.
All advice uses low-cost, locally available methods.

This module provides comprehensive agricultural guidance tailored to African
contexts — from the Sahel to the Horn, the Rift Valley to the Congo Basin,
and the coastal plains of West Africa to the Maghreb. Every recommendation
is designed for smallholders farming 1–5 acres (0.4–2 hectares) with limited
access to capital, inputs, and irrigation infrastructure.

Key Design Principles:
    1. Low-cost: Recommendations prioritize locally available, affordable inputs.
    2. Context-aware: Regional and seasonal variations are deeply integrated.
    3. Dual-method: Both organic/traditional African practices and modern
       scientific methods are presented where appropriate.
    4. Self-contained: Zero external API dependencies — works offline.
    5. Data-driven: SQLite backend for tracking farm records and learning.

Usage:
    from agricultural_advisor import (
        CropAdvisor, LivestockAdvisor, MarketAdvisor,
        ClimateAdvisor, IrrigationAdvisor, FarmPlanner,
        farming_advice, pest_diagnosis, market_advice, farm_plan
    )

    advisor = CropAdvisor()
    guide = advisor.get_planting_guide("maize", "west_africa", "rainy")

Author: Luqi AI Systems
License: MIT
Version: 20.0.0
"""

from __future__ import annotations

import copy
import datetime
import enum
import json
import logging
import math
import os
import random
import re
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)
logger: logging.Logger = logging.getLogger("luqi_agri_advisor")

# ---------------------------------------------------------------------------
# Disclaimers
# ---------------------------------------------------------------------------
WEATHER_DISCLAIMER: str = (
    "DISCLAIMER: Weather and seasonal guidance provided by this system are "
    "illustrative and based on historical climate patterns. Actual conditions "
    "vary by year and micro-climate. Always consult local meteorological "
    "services and agricultural extension officers before making planting decisions."
)

MEDICAL_DISCLAIMER: str = (
    "DISCLAIMER: Livestock disease information is for educational purposes only. "
    "Consult a qualified veterinary officer for diagnosis and treatment. "
    "Delayed professional care can result in animal loss."
)

FINANCIAL_DISCLAIMER: str = (
    "DISCLAIMER: Market prices, ROI estimates, and financial projections are "
    "indicative based on historical data. Actual returns depend on weather, "
    "market conditions, input quality, and management practices. This is not "
    "financial advice."
)

GENERAL_DISCLAIMER: str = (
    "DISCLAIMER: This AI advisor provides general agricultural guidance. "
    "Conditions vary significantly across regions, soil types, and seasons. "
    "Always validate recommendations with local agricultural extension officers, "
    "veterinary services, and agro-dealers. Luqi AI assumes no liability for "
    "crop loss, livestock mortality, or financial loss resulting from the use "
    "of this information."
)

# ---------------------------------------------------------------------------
# Module Version
# ---------------------------------------------------------------------------
__version__ = "20.0.0"
__author__ = "Luqi AI Systems"

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AfricanRegion(enum.Enum):
    """Major African farming regions with distinct agro-ecological zones."""

    WEST_AFRICA = "west_africa"
    EAST_AFRICA = "east_africa"
    SOUTHERN_AFRICA = "southern_africa"
    CENTRAL_AFRICA = "central_africa"
    NORTH_AFRICA = "north_africa"
    SAHEL = "sahel"
    HORN_OF_AFRICA = "horn_of_africa"


class Season(enum.Enum):
    """Farming seasons across African regions."""

    RAINY = "rainy"
    DRY = "dry"
    SHORT_RAINS = "short_rains"
    LONG_RAINS = "long_rains"
    HARMATTAN = "harmattan"
    WET = "wet"


class SoilType(enum.Enum):
    """Common soil types in African smallholder contexts."""

    SANDY = "sandy"
    CLAY = "clay"
    LOAMY = "loamy"
    SILT = "silt"
    LATERITE = "laterite"
    VOLCANIC = "volcanic"
    ALLUVIAL = "alluvial"
    BLACK_COTTON = "black_cotton"
    SANDY_LOAM = "sandy_loam"
    CLAY_LOAM = "clay_loam"


class BudgetLevel(enum.Enum):
    """Budget tiers for farming recommendations."""

    VERY_LOW = "very_low"  # Subsistence, < $50/acre
    LOW = "low"  # Smallholder, $50–150/acre
    MEDIUM = "medium"  # Emerging, $150–400/acre
    HIGH = "high"  # Commercial smallholder, $400+/acre


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlantingGuide:
    """Structured planting recommendation."""

    crop: str
    region: str
    season: str
    steps: List[str]
    spacing: str
    seed_rate: str
    depth: str
    days_to_germination: int
    days_to_maturity: int
    companion_crops: List[str]
    warnings: List[str]


@dataclass
class PestControl:
    """Pest/disease control recommendation."""

    pest_name: str
    symptoms: List[str]
    organic_treatment: List[str]
    chemical_treatment: List[str]
    prevention: List[str]
    severity: str  # low, medium, high, critical


@dataclass
class FertilizerGuide:
    """Fertilizer recommendation."""

    crop: str
    soil_type: str
    npk_ratio: str
    organic_options: List[str]
    inorganic_options: List[str]
    application_timing: List[str]
    estimated_cost_per_acre: float
    micronutrients: List[str]


@dataclass
class HarvestGuide:
    """Harvest and post-harvest guidance."""

    crop: str
    maturity_indicators: List[str]
    harvest_method: str
    tools_needed: List[str]
    post_harvest_handling: List[str]
    storage_methods: List[str]
    expected_yield_per_acre: str


@dataclass
class FarmRecord:
    """Single farm activity record for SQLite tracking."""

    record_id: Optional[int]
    farm_name: str
    activity_type: str  # planting, harvest, expense, income, pest_control, etc.
    crop_or_animal: str
    date: str
    details: str
    quantity: Optional[float]
    unit: Optional[str]
    cost: Optional[float]
    revenue: Optional[float]
    notes: str
    created_at: Optional[str] = None


@dataclass
class ROIEstimate:
    """Return on investment estimate for a crop enterprise."""

    crop: str
    land_size_acres: float
    input_costs: float
    expected_yield_kg: float
    expected_price_per_kg: float
    expected_revenue: float
    net_profit: float
    roi_percentage: float
    break_even_yield_kg: float
    risk_factors: List[str]


# ---------------------------------------------------------------------------
# Constants — Regional Data
# ---------------------------------------------------------------------------

REGIONAL_CLIMATE: Dict[str, Dict[str, Any]] = {
    "west_africa": {
        "countries": ["Nigeria", "Ghana", "Côte d'Ivoire", "Senegal", "Mali", "Burkina Faso", "Niger", "Benin", "Togo", "Guinea", "Sierra Leone", "Liberia"],
        "rainy_months": ["April", "May", "June", "July", "August", "September", "October"],
        "dry_months": ["November", "December", "January", "February", "March"],
        "annual_rainfall_mm": (800, 1600),
        "temperature_range_c": (24, 35),
        "dominant_soil": ["laterite", "sandy_loam", "alluvial"],
        "challenges": ["erratic_rainfall", "pest_pressure", "soil_degradation", "market_access"],
    },
    "east_africa": {
        "countries": ["Kenya", "Tanzania", "Uganda", "Rwanda", "Burundi", "Ethiopia"],
        "rainy_months": ["March", "April", "May", "October", "November", "December"],
        "dry_months": ["June", "July", "August", "September", "January", "February"],
        "annual_rainfall_mm": (600, 1400),
        "temperature_range_c": (18, 30),
        "dominant_soil": ["volcanic", "sandy_loam", "clay_loam"],
        "challenges": ["drought", "pests", "land_fragmentation", "climate_change"],
    },
    "southern_africa": {
        "countries": ["Zambia", "Zimbabwe", "Malawi", "Mozambique", "Botswana", "South Africa"],
        "rainy_months": ["November", "December", "January", "February", "March", "April"],
        "dry_months": ["May", "June", "July", "August", "September", "October"],
        "annual_rainfall_mm": (500, 1200),
        "temperature_range_c": (15, 32),
        "dominant_soil": ["sandy", "loamy", "clay"],
        "challenges": ["drought", "flood", "input_costs", "market_volatility"],
    },
    "central_africa": {
        "countries": ["Cameroon", "Central African Republic", "DRC", "Congo", "Gabon"],
        "rainy_months": ["March", "April", "May", "June", "July", "August", "September", "October"],
        "dry_months": ["November", "December", "January", "February"],
        "annual_rainfall_mm": (1200, 2200),
        "temperature_range_c": (22, 30),
        "dominant_soil": ["laterite", "alluvial", "clay"],
        "challenges": ["excess_moisture", "disease_pressure", "infrastructure", "access_to_inputs"],
    },
    "north_africa": {
        "countries": ["Morocco", "Algeria", "Tunisia", "Egypt", "Libya", "Sudan"],
        "rainy_months": ["October", "November", "December", "January", "February", "March"],
        "dry_months": ["April", "May", "June", "July", "August", "September"],
        "annual_rainfall_mm": (50, 400),
        "temperature_range_c": (20, 45),
        "dominant_soil": ["sandy", "alluvial", "clay"],
        "challenges": ["water_scarcity", "salinity", "heat_stress", "desertification"],
    },
    "sahel": {
        "countries": ["Mauritania", "Mali", "Niger", "Chad", "Sudan", "Burkina Faso", "Senegal"],
        "rainy_months": ["June", "July", "August", "September"],
        "dry_months": ["October", "November", "December", "January", "February", "March", "April", "May"],
        "annual_rainfall_mm": (200, 600),
        "temperature_range_c": (25, 45),
        "dominant_soil": ["sandy", "laterite"],
        "challenges": ["severe_drought", "desertification", "food_insecurity", "conflict"],
    },
    "horn_of_africa": {
        "countries": ["Somalia", "Ethiopia", "Eritrea", "Djibouti", "Kenya"],
        "rainy_months": ["March", "April", "May", "October", "November"],
        "dry_months": ["June", "July", "August", "September", "December", "January", "February"],
        "annual_rainfall_mm": (200, 800),
        "temperature_range_c": (20, 40),
        "dominant_soil": ["volcanic", "sandy", "clay"],
        "challenges": ["recurring_drought", "conflict", "pastoral_livelihoods", "climate_variability"],
    },
}

# Placeholder - this is just the first portion of the file for testing
# Full file has 6819 lines and 334KB
