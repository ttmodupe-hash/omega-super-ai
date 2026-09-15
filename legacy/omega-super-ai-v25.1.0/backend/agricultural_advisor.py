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

# ---------------------------------------------------------------------------
# Constants — Comprehensive Crop Database
# ---------------------------------------------------------------------------

CROPS: Dict[str, Dict[str, Any]] = {
    "maize": {
        "name": "Maize",
        "family": "Poaceae",
        "optimal_temp_c": (18, 32),
        "rainfall_mm": (500, 1000),
        "soil_preference": ["loamy", "sandy_loam", "clay_loam"],
        "ph_range": (5.5, 7.5),
        "days_to_maturity": (90, 150),
        "regions": ["west_africa", "east_africa", "southern_africa", "central_africa"],
        "seasons": ["rainy", "long_rains"],
        "seed_rate_kg_per_ha": 20,
        "spacing_cm": (75, 25),
        "fertilizer_npk": "60:30:30",
        "common_pests": ["stem_borer", "armyworm", "aphids", "maize_weevil"],
        "common_diseases": ["maize_streak_virus", "rust", "blight", "smut"],
        "companion_crops": ["beans", "pumpkin", "cowpea"],
        "yield_tons_per_ha": (1.5, 6.0),
        "storage_moisture_percent": 13.5,
        "drought_tolerance": "moderate",
        "description": "Staple cereal across Africa. Drought-tolerant varieties like SC627, DKC80-53, and WE2115 recommended for dry areas.",
    },
    "cassava": {
        "name": "Cassava",
        "family": "Euphorbiaceae",
        "optimal_temp_c": (25, 35),
        "rainfall_mm": (600, 1500),
        "soil_preference": ["sandy_loam", "loamy", "laterite"],
        "ph_range": (5.0, 7.5),
        "days_to_maturity": (240, 365),
        "regions": ["west_africa", "central_africa", "east_africa", "southern_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Stem cuttings
        "spacing_cm": (100, 100),
        "fertilizer_npk": "40:20:40",
        "common_pests": ["cassava_mealybug", "green_mite", "whitefly", "cassava_brown_streak"],
        "common_diseases": ["mosaic_disease", "brown_streak_disease", "bacterial_blight"],
        "companion_crops": ["maize", "groundnut", "cowpea"],
        "yield_tons_per_ha": (8.0, 25.0),
        "storage_moisture_percent": 0,  # Processed
        "drought_tolerance": "high",
        "description": "Root crop that thrives in poor soils. Drought-tolerant and provides food security. Process into garri, fufu, or flour.",
    },
    "rice": {
        "name": "Rice",
        "family": "Poaceae",
        "optimal_temp_c": (20, 35),
        "rainfall_mm": (1000, 2000),
        "soil_preference": ["clay", "clay_loam", "alluvial"],
        "ph_range": (5.0, 7.0),
        "days_to_maturity": (90, 150),
        "regions": ["west_africa", "east_africa", "central_africa", "southern_africa"],
        "seasons": ["rainy", "wet", "long_rains"],
        "seed_rate_kg_per_ha": 80,
        "spacing_cm": (20, 20),
        "fertilizer_npk": "80:40:40",
        "common_pests": ["rice_stem_borer", "rice_gall_midge", "African_rice_gall_midge", "quelea_birds"],
        "common_diseases": ["rice_blast", "brown_spot", "sheath_rot", "bacterial_leaf_blight"],
        "companion_crops": ["fish", "azolla"],
        "yield_tons_per_ha": (2.0, 8.0),
        "storage_moisture_percent": 14.0,
        "drought_tolerance": "low",
        "description": "Important staple grown in upland, lowland, and irrigated systems. NERICA varieties suitable for upland areas.",
    },
    "sorghum": {
        "name": "Sorghum",
        "family": "Poaceae",
        "optimal_temp_c": (25, 35),
        "rainfall_mm": (400, 800),
        "soil_preference": ["sandy", "loamy", "clay"],
        "ph_range": (5.0, 8.5),
        "days_to_maturity": (75, 120),
        "regions": ["sahel", "west_africa", "east_africa", "horn_of_africa", "southern_africa"],
        "seasons": ["rainy", "short_rains"],
        "seed_rate_kg_per_ha": 12,
        "spacing_cm": (75, 15),
        "fertilizer_npk": "40:20:20",
        "common_pests": ["stem_borer", "shoot_fly", "sorghum_midge", "aphids"],
        "common_diseases": ["grain_mold", "anthracnose", "leaf_blight", "smut"],
        "companion_crops": ["cowpea", "groundnut", "pigeon_pea"],
        "yield_tons_per_ha": (0.8, 4.0),
        "storage_moisture_percent": 13.0,
        "drought_tolerance": "very_high",
        "description": "Drought-hardy cereal ideal for arid and semi-arid regions. Used for food, fodder, and brewing.",
    },
    "millet": {
        "name": "Pearl Millet",
        "family": "Poaceae",
        "optimal_temp_c": (28, 35),
        "rainfall_mm": (250, 700),
        "soil_preference": ["sandy", "loamy", "laterite"],
        "ph_range": (5.5, 8.0),
        "days_to_maturity": (60, 90),
        "regions": ["sahel", "west_africa", "horn_of_africa", "southern_africa"],
        "seasons": ["rainy", "short_rains"],
        "seed_rate_kg_per_ha": 10,
        "spacing_cm": (75, 20),
        "fertilizer_npk": "30:15:15",
        "common_pests": ["millet_stem_borer", "millet_head_miner", "aphids", "grasshoppers"],
        "common_diseases": ["downy_mildew", "rust", "smut", "ergot"],
        "companion_crops": ["cowpea", "groundnut"],
        "yield_tons_per_ha": (0.5, 2.5),
        "storage_moisture_percent": 12.0,
        "drought_tolerance": "very_high",
        "description": "Most drought-tolerant cereal. Grows where maize and sorghum fail. Essential food security crop in the Sahel.",
    },
    "yam": {
        "name": "Yam",
        "family": "Dioscoreaceae",
        "optimal_temp_c": (25, 30),
        "rainfall_mm": (1000, 1500),
        "soil_preference": ["sandy_loam", "loamy", "clay_loam"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (240, 300),
        "regions": ["west_africa", "central_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Setts / tubers
        "spacing_cm": (100, 100),
        "fertilizer_npk": "80:40:80",
        "common_pests": ["yam_beetle", "mealybug", "nematodes", "scale_insects"],
        "common_diseases": ["anthracnose", "yam_mosaic_virus", "tuber_rot", "brown_spot"],
        "companion_crops": ["maize", "cocoyam"],
        "yield_tons_per_ha": (8.0, 20.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "Important tuber crop in West and Central Africa. Planted with whole tubers or setts. Store in yam barns.",
    },
    "plantain": {
        "name": "Plantain",
        "family": "Musaceae",
        "optimal_temp_c": (26, 30),
        "rainfall_mm": (1200, 2500),
        "soil_preference": ["loamy", "clay_loam", "alluvial", "volcanic"],
        "ph_range": (5.0, 7.0),
        "days_to_maturity": (300, 450),
        "regions": ["west_africa", "central_africa", "east_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Suckers
        "spacing_cm": (3, 3),  # metres
        "fertilizer_npk": "200:100:200",
        "common_pests": ["banana_weevil", "nematodes", "aphids", "thrips"],
        "common_diseases": ["black_sigatoka", "fusarium_wilt", "bunchy_top", "moko_disease"],
        "companion_crops": ["cocoa", "coffee", "yam"],
        "yield_tons_per_ha": (10.0, 40.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "Staple food crop in humid tropics. Propagated by suckers. Requires rich, well-drained soils.",
    },
    "cocoa": {
        "name": "Cocoa",
        "family": "Malvaceae",
        "optimal_temp_c": (21, 32),
        "rainfall_mm": (1000, 2500),
        "soil_preference": ["loamy", "clay_loam", "volcanic"],
        "ph_range": (5.0, 7.5),
        "days_to_maturity": (1095, 1460),  # 3–4 years to first harvest
        "regions": ["west_africa", "central_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Seedlings
        "spacing_cm": (3, 3),  # metres
        "fertilizer_npk": "150:60:150",
        "common_pests": ["capsid_bug", "cocoa_mirid", "mealybug", "cocoa_pod_borer"],
        "common_diseases": ["black_pod", "swollen_shoot", "vascular_streak_dieback", "witches_broom"],
        "companion_crops": ["plantain", "coconut", "shade_trees"],
        "yield_tons_per_ha": (0.3, 2.0),
        "storage_moisture_percent": 7.0,
        "drought_tolerance": "low",
        "description": "Major cash crop for West and Central Africa. Requires shade when young. Long-term investment crop.",
    },
    "coffee": {
        "name": "Coffee",
        "family": "Rubiaceae",
        "optimal_temp_c": (15, 28),
        "rainfall_mm": (900, 1800),
        "soil_preference": ["loamy", "volcanic", "clay_loam"],
        "ph_range": (5.0, 6.5),
        "days_to_maturity": (730, 1095),  # 2–3 years
        "regions": ["east_africa", "central_africa", "west_africa"],
        "seasons": ["rainy", "short_rains"],
        "seed_rate_kg_per_ha": 0,  # Seedlings
        "spacing_cm": (2.5, 2.5),  # metres
        "fertilizer_npk": "100:50:100",
        "common_pests": ["coffee_berry_borer", "leaf_miner", "antestia_bug", "scale_insects"],
        "common_diseases": ["coffee_leaf_rust", "coffee_wilt", "berry_disease", "damping_off"],
        "companion_crops": ["banana", "shade_trees", "beans"],
        "yield_tons_per_ha": (0.5, 3.0),
        "storage_moisture_percent": 12.0,
        "drought_tolerance": "moderate",
        "description": "High-value cash crop especially in East African highlands. Arabica at altitude, Robusta at lower elevations.",
    },
    "tea": {
        "name": "Tea",
        "family": "Theaceae",
        "optimal_temp_c": (18, 30),
        "rainfall_mm": (1200, 2500),
        "soil_preference": ["loamy", "volcanic", "clay_loam"],
        "ph_range": (4.5, 6.0),
        "days_to_maturity": (730, 1095),
        "regions": ["east_africa", "southern_africa"],
        "seasons": ["rainy", "long_rains"],
        "seed_rate_kg_per_ha": 0,  # Cuttings
        "spacing_cm": (1.5, 0.75),
        "fertilizer_npk": "200:50:100",
        "common_pests": ["red_spider_mite", "aphids", "thrips", "scale_insects"],
        "common_diseases": ["blister_blight", "black_rot", "red_root_rot", "anthracnose"],
        "companion_crops": ["shade_trees"],
        "yield_tons_per_ha": (1.5, 4.0),
        "storage_moisture_percent": 3.0,
        "drought_tolerance": "low",
        "description": "Highland crop grown extensively in Kenya, Tanzania, Malawi. Requires regular rainfall and well-drained acidic soils.",
    },
    "beans": {
        "name": "Common Beans",
        "family": "Fabaceae",
        "optimal_temp_c": (18, 28),
        "rainfall_mm": (350, 600),
        "soil_preference": ["loamy", "sandy_loam", "clay_loam"],
        "ph_range": (5.5, 7.5),
        "days_to_maturity": (60, 100),
        "regions": ["east_africa", "southern_africa", "central_africa", "west_africa"],
        "seasons": ["rainy", "short_rains", "long_rains"],
        "seed_rate_kg_per_ha": 60,
        "spacing_cm": (50, 10),
        "fertilizer_npk": "20:40:20",
        "common_pests": ["bean_stem_maggot", "aphids", "whitefly", "bruchid"],
        "common_diseases": ["bean_rust", "angular_leaf_spot", "anthracnose", "root_rot"],
        "companion_crops": ["maize", "sorghum", "potato"],
        "yield_tons_per_ha": (0.5, 3.0),
        "storage_moisture_percent": 14.0,
        "drought_tolerance": "moderate",
        "description": "Protein-rich legume that fixes nitrogen. Essential food security and income crop. Intercrop with maize.",
    },
    "groundnut": {
        "name": "Groundnut (Peanut)",
        "family": "Fabaceae",
        "optimal_temp_c": (25, 32),
        "rainfall_mm": (500, 1000),
        "soil_preference": ["sandy_loam", "loamy", "sandy"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (90, 140),
        "regions": ["west_africa", "east_africa", "southern_africa", "sahel"],
        "seasons": ["rainy", "short_rains"],
        "seed_rate_kg_per_ha": 80,
        "spacing_cm": (60, 15),
        "fertilizer_npk": "20:40:40",
        "common_pests": ["aphids", "thrips", "termites", "pod_borer"],
        "common_diseases": ["rosette_disease", "early_leaf_spot", "late_leaf_spot", "rust"],
        "companion_crops": ["maize", "millet", "sorghum"],
        "yield_tons_per_ha": (0.8, 3.5),
        "storage_moisture_percent": 8.0,
        "drought_tolerance": "moderate",
        "description": "Important oil and protein crop. Fix nitrogen and improve soil. Process into oil, paste, or snacks.",
    },
    "sesame": {
        "name": "Sesame",
        "family": "Pedaliaceae",
        "optimal_temp_c": (25, 35),
        "rainfall_mm": (400, 700),
        "soil_preference": ["sandy_loam", "loamy", "sandy"],
        "ph_range": (5.5, 8.0),
        "days_to_maturity": (80, 120),
        "regions": ["west_africa", "east_africa", "sahel", "central_africa"],
        "seasons": ["rainy", "short_rains"],
        "seed_rate_kg_per_ha": 5,
        "spacing_cm": (60, 15),
        "fertilizer_npk": "40:40:40",
        "common_pests": ["aphids", "whitefly", "gall_fly", "leaf_webber"],
        "common_diseases": ["phyllody", "leaf_curl", "stem_rot", "bacterial_blight"],
        "companion_crops": ["sorghum", "millet"],
        "yield_tons_per_ha": (0.3, 1.5),
        "storage_moisture_percent": 6.0,
        "drought_tolerance": "high",
        "description": "Drought-tolerant oilseed with high market value. Low input requirements make it ideal for smallholders.",
    },
    "cotton": {
        "name": "Cotton",
        "family": "Malvaceae",
        "optimal_temp_c": (25, 35),
        "rainfall_mm": (600, 1200),
        "soil_preference": ["loamy", "clay_loam", "black_cotton"],
        "ph_range": (5.5, 8.0),
        "days_to_maturity": (150, 180),
        "regions": ["west_africa", "east_africa", "southern_africa", "sahel"],
        "seasons": ["rainy", "long_rains"],
        "seed_rate_kg_per_ha": 20,
        "spacing_cm": (90, 30),
        "fertilizer_npk": "60:30:30",
        "common_pests": ["bollworm", "aphids", "whitefly", "jassid"],
        "common_diseases": ["bacterial_blight", "fusarium_wilt", "verticillium_wilt", "leaf_curl"],
        "companion_crops": ["cowpea", "groundnut"],
        "yield_tons_per_ha": (0.8, 3.0),
        "storage_moisture_percent": 10.0,
        "drought_tolerance": "moderate",
        "description": "Major cash crop for fiber. Requires good management. BT cotton varieties reduce pesticide needs.",
    },
    "tomato": {
        "name": "Tomato",
        "family": "Solanaceae",
        "optimal_temp_c": (20, 30),
        "rainfall_mm": (600, 1200),
        "soil_preference": ["loamy", "sandy_loam", "clay_loam"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (75, 120),
        "regions": ["west_africa", "east_africa", "southern_africa", "central_africa", "north_africa"],
        "seasons": ["rainy", "dry", "short_rains"],
        "seed_rate_kg_per_ha": 0.5,
        "spacing_cm": (75, 50),
        "fertilizer_npk": "80:60:80",
        "common_pests": ["whitefly", "aphids", "fruit_borer", "leaf_miner"],
        "common_diseases": ["early_blight", "late_blight", "bacterial_wilt", "tomato_yellow_leaf_curl"],
        "companion_crops": ["onion", "carrot", "basil"],
        "yield_tons_per_ha": (8.0, 40.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "High-value vegetable for fresh market and processing. Requires consistent moisture and staking.",
    },
    "pepper": {
        "name": "Pepper (Chili/Bell)",
        "family": "Solanaceae",
        "optimal_temp_c": (20, 30),
        "rainfall_mm": (600, 1200),
        "soil_preference": ["loamy", "sandy_loam", "clay_loam"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (90, 150),
        "regions": ["west_africa", "east_africa", "southern_africa", "central_africa"],
        "seasons": ["rainy", "short_rains", "long_rains"],
        "seed_rate_kg_per_ha": 0.3,
        "spacing_cm": (60, 45),
        "fertilizer_npk": "80:60:60",
        "common_pests": ["aphids", "whitefly", "thrips", "fruit_borer"],
        "common_diseases": ["anthracnose", "bacterial_wilt", "phytophthora_blight", "leaf_spot"],
        "companion_crops": ["onion", "tomato", "basil"],
        "yield_tons_per_ha": (3.0, 15.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "High-value spice and vegetable. Fresh and dried markets. Good export potential.",
    },
    "onion": {
        "name": "Onion",
        "family": "Amaryllidaceae",
        "optimal_temp_c": (15, 25),
        "rainfall_mm": (350, 600),
        "soil_preference": ["sandy_loam", "loamy", "sandy"],
        "ph_range": (6.0, 7.5),
        "days_to_maturity": (90, 150),
        "regions": ["west_africa", "east_africa", "southern_africa", "north_africa", "sahel"],
        "seasons": ["dry", "short_rains"],
        "seed_rate_kg_per_ha": 4,
        "spacing_cm": (30, 10),
        "fertilizer_npk": "80:60:60",
        "common_pests": ["thrips", "onion_fly", "aphids", "nematodes"],
        "common_diseases": ["downy_mildew", "purple_blotch", "botrytis", "bacterial_soft_rot"],
        "companion_crops": ["tomato", "pepper", "carrot"],
        "yield_tons_per_ha": (10.0, 30.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "moderate",
        "description": "High-demand bulb crop. Long storage potential. Red varieties command premium prices.",
    },
    "cabbage": {
        "name": "Cabbage",
        "family": "Brassicaceae",
        "optimal_temp_c": (15, 25),
        "rainfall_mm": (400, 700),
        "soil_preference": ["loamy", "clay_loam", "sandy_loam"],
        "ph_range": (6.0, 7.0),
        "days_to_maturity": (80, 120),
        "regions": ["west_africa", "east_africa", "southern_africa", "central_africa", "north_africa"],
        "seasons": ["rainy", "dry", "short_rains"],
        "seed_rate_kg_per_ha": 0.5,
        "spacing_cm": (60, 45),
        "fertilizer_npk": "120:80:100",
        "common_pests": ["diamondback_moth", "cabbage_worm", "aphids", "cutworm"],
        "common_diseases": ["black_rot", "clubroot", "downy_mildew", "alternaria"],
        "companion_crops": ["onion", "celery", "beetroot"],
        "yield_tons_per_ha": (15.0, 50.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "Popular leafy vegetable with year-round demand. Requires high nutrient inputs.",
    },
    "mango": {
        "name": "Mango",
        "family": "Anacardiaceae",
        "optimal_temp_c": (24, 30),
        "rainfall_mm": (750, 2500),
        "soil_preference": ["loamy", "alluvial", "sandy_loam"],
        "ph_range": (5.5, 7.5),
        "days_to_maturity": (1095, 1825),  # 3–5 years to fruiting
        "regions": ["west_africa", "east_africa", "central_africa", "southern_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Grafting
        "spacing_cm": (10, 10),  # metres
        "fertilizer_npk": "200:100:200",
        "common_pests": ["fruit_fly", "mango_seed_weevil", "mango_scale", "mealybug"],
        "common_diseases": ["anthracnose", "powdery_mildew", "bacterial_canker", "black_spot"],
        "companion_crops": ["beans", "groundnut", "vegetables"],
        "yield_tons_per_ha": (5.0, 25.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "high",
        "description": "High-value fruit with excellent export potential. Process into dried mango, juice, or jam.",
    },
    "banana": {
        "name": "Banana",
        "family": "Musaceae",
        "optimal_temp_c": (26, 30),
        "rainfall_mm": (1200, 2500),
        "soil_preference": ["loamy", "clay_loam", "alluvial", "volcanic"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (270, 365),
        "regions": ["west_africa", "east_africa", "central_africa", "southern_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Suckers
        "spacing_cm": (3, 3),
        "fertilizer_npk": "200:100:200",
        "common_pests": ["banana_weevil", "nematodes", "aphids", "thrips"],
        "common_diseases": ["black_sigatoka", "fusarium_wilt", "bunchy_top", "moko"],
        "companion_crops": ["beans", "groundnut", "cocoa"],
        "yield_tons_per_ha": (15.0, 50.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "low",
        "description": "Year-round fruit crop. Cavendish for export, local varieties for fresh consumption.",
    },
    "pineapple": {
        "name": "Pineapple",
        "family": "Bromeliaceae",
        "optimal_temp_c": (23, 32),
        "rainfall_mm": (600, 1500),
        "soil_preference": ["sandy_loam", "loamy", "laterite"],
        "ph_range": (4.5, 6.5),
        "days_to_maturity": (365, 548),  # 12–18 months
        "regions": ["west_africa", "east_africa", "central_africa", "southern_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Suckers / slips
        "spacing_cm": (30, 60),
        "fertilizer_npk": "100:50:100",
        "common_pests": ["mealybug", "scale_insects", "thrips", "nematodes"],
        "common_diseases": ["heart_rot", "root_rot", "mealybug_wilt", "fruitlet_core_rot"],
        "companion_crops": ["cassava", "groundnut", "cowpea"],
        "yield_tons_per_ha": (20.0, 70.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "high",
        "description": "Drought-tolerant fruit with excellent processing potential. Export and juice markets strong.",
    },
    "citrus": {
        "name": "Citrus (Orange, Lemon, Lime)",
        "family": "Rutaceae",
        "optimal_temp_c": (23, 34),
        "rainfall_mm": (900, 2000),
        "soil_preference": ["loamy", "sandy_loam", "alluvial"],
        "ph_range": (5.5, 7.5),
        "days_to_maturity": (730, 1095),
        "regions": ["west_africa", "east_africa", "southern_africa", "north_africa", "central_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Budded seedlings
        "spacing_cm": (6, 6),
        "fertilizer_npk": "200:100:150",
        "common_pests": ["fruit_fly", "citrus_psylla", "aphids", "red_scale"],
        "common_diseases": ["citrus_greening", "tristeza", "anthracnose", "gummosis"],
        "companion_crops": ["beans", "groundnut", "maize"],
        "yield_tons_per_ha": (10.0, 40.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "moderate",
        "description": "High-value fruit trees. Sweet orange, lime, and lemon most common. Process into juice.",
    },
    "pawpaw": {
        "name": "Pawpaw (Papaya)",
        "family": "Caricaceae",
        "optimal_temp_c": (21, 33),
        "rainfall_mm": (1000, 2000),
        "soil_preference": ["loamy", "sandy_loam", "alluvial"],
        "ph_range": (5.5, 7.0),
        "days_to_maturity": (180, 270),
        "regions": ["west_africa", "east_africa", "central_africa", "southern_africa"],
        "seasons": ["rainy", "wet"],
        "seed_rate_kg_per_ha": 0,  # Seeds
        "spacing_cm": (2, 2),
        "fertilizer_npk": "100:50:100",
        "common_pests": ["fruit_fly", "aphids", "mealybug", "spider_mite"],
        "common_diseases": ["papaya_ring_spot", "anthracnose", "powdery_mildew", "root_rot"],
        "companion_crops": ["beans", "vegetables", "maize"],
        "yield_tons_per_ha": (20.0, 60.0),
        "storage_moisture_percent": 0,
        "drought_tolerance": "moderate",
        "description": "Fast-maturing fruit tree. Female trees bear fruit. Process into dried papaya or juice.",
    },
}

# ---------------------------------------------------------------------------
# Constants — Livestock Database
# ---------------------------------------------------------------------------

LIVESTOCK: Dict[str, Dict[str, Any]] = {
    "cattle": {
        "name": "Cattle",
        "local_breeds": ["Boran", "Ankole", "Nguni", "Afrikaner", "Zebu", "Sahiwal", "Tuli", "Mashona"],
        "exotic_breeds": ["Holstein-Friesian", "Jersey", "Guernsey", "Ayrshire"],
        "optimal_temp_c": (15, 28),
        "housing": "Open kraal or boma with shade. Minimum 3m² per adult.",
        "feeding_system": "Grazing + supplementation",
        "water_litres_per_day": (30, 80),
        "gestation_days": 283,
        "age_at_first_calving_months": (24, 36),
        "calving_interval_months": (12, 18),
        "common_diseases": ["east_coast_fever", "foot_and_mouth", "brucellosis", "anaplasmosis", "trypanosomiasis"],
        "vaccination_schedule": {
            "3_months": "Contagious bovine pleuropneumonia (CBPP)",
            "6_months": "Foot-and-mouth disease (FMD)",
            "9_months": "Black quarter (BQ)",
            "annually": "Lumpy skin disease, Rift Valley fever",
        },
        "local_feeds": ["Napier grass", " Rhodes grass", "maize stover", "bean haulms", "banana peels", "cotton seed cake"],
        "supplements": ["mineral blocks", "molasses-urea blocks", "dairy meal"],
    },
    "goats": {
        "name": "Goats",
        "local_brereds": ["East African", "West African Dwarf", "Boer", "Somali", "Galla", "Mubende", "Small East African"],
        "exotic_breeds": ["Saanen", "Toggenburg", "Alpine", "Angora"],
        "optimal_temp_c": (15, 35),
        "housing": "Raised slatted floor or kraal. 1.5m² per adult.",
        "feeding_system": "Browsing + grazing + supplementation",
        "water_litres_per_day": (3, 10),
        "gestation_days": 150,
        "age_at_first_kidding_months": (10, 18),
        "kidding_interval_months": (8, 12),
        "common_diseases": ["peste_des_petits_ruminants", "contagious_caprine_pleuropneumonia", "goat_pox", "helminthiasis", "coccidiosis"],
        "vaccination_schedule": {
            "3_months": "Peste des petits ruminants (PPR)",
            "6_months": "Contagious caprine pleuropneumonia (CCPP)",
            "annually": "Goat pox, Enterotoxaemia",
        },
        "local_feeds": ["Napier grass", "calliandra", "leucaena", "maize stover", "sweet potato vines", "banana leaves"],
        "supplements": ["mineral salts", "dairy goat pellets", "molasses"],
    },
    "sheep": {
        "name": "Sheep",
        "local_breeds": ["Red Maasai", "Dorper", "Somali", "Sahelian", "West African Dwarf", "Barbados Blackbelly"],
        "exotic_breeds": ["Merino", "Suffolk", "Hampshire", "Dorper"],
        "optimal_temp_c": (15, 32),
        "housing": "Open kraal with shelter. 1.5m² per adult.",
        "feeding_system": "Grazing + supplementation",
        "water_litres_per_day": (2, 8),
        "gestation_days": 152,
        "age_at_first_lambing_months": (12, 18),
        "lambing_interval_months": (8, 12),
        "common_diseases": ["peste_des_petits_ruminants", "bluetongue", "sheep_pox", "helminthiasis", "pneumonia"],
        "vaccination_schedule": {
            "3_months": "Peste des petits ruminants (PPR)",
            "4_months": "Bluetongue",
            "annually": "Sheep pox, Anthrax, Enterotoxaemia",
        },
        "local_feeds": ["grass hay", "maize stover", "bean haulms", "sweet potato vines", "Napier grass"],
        "supplements": ["mineral salts", "urea-molasses blocks", "sheep pellets"],
    },
    "chickens": {
        "name": "Chickens",
        "local_breeds": ["Kienyeji", "Kuroiler", "Kenbro", "Rhode Island Red", "Australorp"],
        "exotic_breeds": ["Leghorn", "Isa Brown", "Hubbard", "Cobb"],
        "optimal_temp_c": (18, 28),
        "housing": "Deep litter or raised house. 3–5 birds/m² for layers, 8–10/m² for broilers.",
        "feeding_system": "Commercial feed + kitchen scraps + free range",
        "water_litres_per_day": (0.2, 0.5),
        "incubation_days": 21,
        "age_at_first_lay_weeks": (18, 24),
        "eggs_per_year": (150, 320),
        "common_diseases": ["newcastle_disease", "infectious_bronchitis", "fowl_pox", "coccidiosis", "gumboro"],
        "vaccination_schedule": {
            "day_1": "Marek's disease",
            "day_7": "Newcastle disease (NDV)",
            "day_14": "Gumboro (IBD)",
            "day_21": "Newcastle disease (booster)",
            "day_28": "Fowl pox",
            "week_18": "Newcastle disease + Infectious bronchitis",
        },
        "local_feeds": ["maize bran", "chicken mash", "kitchen scraps", "green vegetables", "termite larvae", "oyster shells"],
        "supplements": ["vitamin premix", "grit", "limestone"],
    },
    "pigs": {
        "name": "Pigs",
        "local_breeds": ["Large White", "Landrace", "Duroc", "Hampshire", "African indigenous"],
        "exotic_breeds": ["Large White", "Landrace", "Duroc", "Pietrain"],
        "optimal_temp_c": (15, 25),
        "housing": "Sty with concrete or slatted floor. 2–3m² per adult.",
        "feeding_system": "Concentrate + kitchen waste + forage",
        "water_litres_per_day": (10, 30),
        "gestation_days": 114,
        "age_at_first_farrowing_months": (8, 12),
        "farrowing_interval_months": (6, 8),
        "common_diseases": ["african_swine_fever", "swine_fever", "pneumonia", "diarrhoea", "internal_parasites"],
        "vaccination_schedule": {
            "6_weeks": "Swine fever",
            "8_weeks": "Erysipelas",
            "annually": "Swine fever booster",
        },
        "local_feeds": ["maize bran", "sweet potato", "cassava", "banana stems", "brewery waste", "kitchen waste"],
        "supplements": ["soybean cake", "fish meal", "mineral premix", "vitamins"],
    },
    "rabbits": {
        "name": "Rabbits",
        "local_breeds": ["New Zealand White", "California", "Chinchilla", "Flemish Giant", "Local indigenous"],
        "exotic_breeds": ["New Zealand White", "California", "Angora"],
        "optimal_temp_c": (10, 25),
        "housing": "Hutch with wire mesh floor. 0.5m² per adult.",
        "feeding_system": "Forage + concentrate pellets",
        "water_litres_per_day": (0.1, 0.5),
        "gestation_days": 31,
        "age_at_first_kindling_months": (5, 7),
        "kindling_interval_months": (2, 3),
        "common_diseases": ["coccidiosis", "snuffles", "ear_canker", "enteritis", "mastitis"],
        "vaccination_schedule": {
            "monthly": "Coccidiosis prevention",
        },
        "local_feeds": ["Napier grass", "sweet potato vines", "banana leaves", "maize leaves", "bean leaves", "carrot tops"],
        "supplements": ["rabbit pellets", "mineral salts", "legume fodder"],
    },
}

# ---------------------------------------------------------------------------
# Constants — Pest & Disease Database
# ---------------------------------------------------------------------------

PEST_DATABASE: Dict[str, Dict[str, Any]] = {
    "stem_borer": {
        "name": "Stem Borer",
        "affected_crops": ["maize", "sorghum", "millet", "rice"],
        "symptoms": [
            "Dead heart in young plants (central leaf dries up)",
            "Holes in stems with frass (sawdust-like excrement)",
            "Stunted growth and yellowing",
            "Broken stems or lodging in older plants",
        ],
        "organic_control": [
            "Intercrop with desmodium (push-pull system) — push-pull is highly effective",
            "Apply wood ash at plant base to deter egg-laying",
            "Use neem seed extract (50g/L water) as foliar spray",
            "Plant Napier grass as trap crop on field borders",
            "Release Trichogramma wasps as biological control",
            "Practice crop rotation with non-cereal crops",
        ],
        "chemical_control": [
            "Apply imidacloprid seed treatment before planting",
            "Spray lambda-cyhalothrin at 2 weeks after emergence",
            "Apply deltamethrin if infestation exceeds 5% of plants",
        ],
        "prevention": [
            "Use certified resistant varieties",
            "Plant early to avoid peak borer populations",
            "Remove and destroy crop residues after harvest",
            "Practice crop rotation with legumes",
        ],
        "severity": "high",
    },
    "fall_armyworm": {
        "name": "Fall Armyworm (Spodoptera frugiperda)",
        "affected_crops": ["maize", "sorghum", "millet", "rice", "vegetables"],
        "symptoms": [
            "Large ragged holes in leaves",
            "Frass (excrement) in leaf whorls",
            "Severely damaged whorls giving 'dead heart' appearance",
            "Young larvae are green; mature larvae have inverted Y on head",
        ],
        "organic_control": [
            "Handpick and crush larvae — effective for small plots",
            "Spray neem oil (5ml/L water) every 7 days",
            "Apply crushed chilli-garlic spray (50g chilli + 50g garlic per litre)",
            "Use Beauveria bassiana fungal biopesticide",
            "Apply wood ash + chilli powder mixture in leaf whorls",
            "Encourage natural predators: birds, parasitic wasps",
        ],
        "chemical_control": [
            "Spray lambda-cyhalothrin or deltamethrin at first sign",
            "Apply chlorantraniliprole (Coragen) — highly effective",
            "Use emamectin benzoate for severe infestations",
            "Rotate chemicals to prevent resistance development",
        ],
        "prevention": [
            "Scout fields twice weekly during vulnerable stages",
            "Plant early with the rains to avoid peak populations",
            "Maintain field hygiene — remove weeds that host pests",
            "Use pheromone traps to monitor adult moth populations",
        ],
        "severity": "critical",
    },
    "aphids": {
        "name": "Aphids",
        "affected_crops": ["maize", "beans", "tomato", "cabbage", "cassava", "groundnut", "cotton"],
        "symptoms": [
            "Clusters of small green, black, or yellow insects on undersides of leaves",
            "Curled or distorted leaves",
            "Sticky honeydew on leaves promoting sooty mold",
            "Stunted growth and yellowing",
        ],
        "organic_control": [
            "Spray soapy water (20g soap per litre) on affected plants",
            "Apply neem oil (5ml/L) as foliar spray",
            "Introduce ladybugs (natural predator of aphids)",
            "Plant marigolds, nasturtiums, or garlic as companion plants",
            "Blast aphids off with strong water spray",
        ],
        "chemical_control": [
            "Spray imidacloprid or acetamiprid at first sign",
            "Apply pymetrozine for resistant populations",
            "Use soap-based insecticides approved for organic use",
        ],
        "prevention": [
            "Control weeds that host aphids",
            "Encourage natural predator populations",
            "Avoid excessive nitrogen fertilization which promotes soft growth",
            "Use reflective mulches to deter aphids",
        ],
        "severity": "medium",
    },
    "whitefly": {
        "name": "Whitefly",
        "affected_crops": ["tomato", "pepper", "cassava", "cotton", "beans", "cabbage"],
        "symptoms": [
            "Tiny white flying insects when plant is disturbed",
            "Yellowing and curling of leaves",
            "Sooty mold on leaves from honeydew",
            "Stunted plant growth",
            "Virus transmission (e.g., cassava mosaic, TYLCV)",
        ],
        "organic_control": [
            "Hang yellow sticky traps to monitor and catch adults",
            "Spray neem oil (5ml/L) targeting undersides of leaves",
            "Apply soapy water spray (insecticidal soap)",
            "Release Encarsia formosa parasitic wasps",
            "Plant repellent crops: basil, marigold, nasturtium",
        ],
        "chemical_control": [
            "Spray imidacloprid or thiamethoxam as soil drench or foliar",
            "Apply pyriproxyfen (insect growth regulator)",
            "Rotate with spiromesifen for resistance management",
        ],
        "prevention": [
            "Use resistant varieties where available",
            "Remove and destroy heavily infested plants",
            "Control weeds in and around fields",
            "Use fine insect-proof netting on nurseries",
        ],
        "severity": "high",
    },
    "cassava_mealybug": {
        "name": "Cassava Mealybug (Phenacoccus manihoti)",
        "affected_crops": ["cassava"],
        "symptoms": [
            "White woolly masses at leaf axils and stem tips",
            "Distorted and stunted shoot tips (bunchy top appearance)",
            "Shortened internodes and small leaves",
            "Honeydew secretion leading to sooty mold",
            "Tuber yield reduction up to 60–80%",
        ],
        "organic_control": [
            "Release Anagyrus lopezi parasitic wasp (biological control)",
            "Apply neem oil or neem seed kernel extract",
            "Use tolerant varieties: TMS 30572, MM96",
            "Remove and destroy severely infested plants",
        ],
        "chemical_control": [
            "Spray acetamiprid or imidacloprid at first detection",
            "Apply systemic insecticides as soil drench",
        ],
        "prevention": [
            "Use clean, certified planting material",
            "Plant early at onset of rains",
            "Establish border plantings early to attract natural enemies",
            "Avoid moving infested planting material between fields",
        ],
        "severity": "critical",
    },
    "fruit_fly": {
        "name": "Fruit Fly",
        "affected_crops": ["mango", "citrus", "pawpaw", "tomato", "pepper"],
        "symptoms": [
            "Small puncture wounds (sting marks) on fruit skin",
            "Soft brown rotten spots on fruit",
            "Larvae (maggots) visible inside infested fruit",
            "Premature fruit drop",
            "Fruit cracking and secondary infections",
        ],
        "organic_control": [
            "Use methyl eugenol or terpinyl acetate bait traps",
            "Bag individual fruits with paper bags at pea stage",
            "Apply protein bait sprays (yeast + molasses + insecticide)",
            "Pick and destroy all fallen and infested fruits weekly",
            "Release parasitoids like Fopius arisanus",
            "Spray neem-based fruit fly repellent",
        ],
        "chemical_control": [
            "Apply spinosad-based protein bait sprays",
            "Use deltamethrin cover sprays at fruit set (with caution)",
            "Apply fipronil bait stations",
        ],
        "prevention": [
            "Harvest fruits early before full ripening",
            "Remove alternative host plants (wild fruit trees)",
            "Practice orchard sanitation — collect fallen fruits",
            "Use fruit fly exclusion netting (fine mesh)",
        ],
        "severity": "high",
    },
    "coffee_berry_borer": {
        "name": "Coffee Berry Borer (Hypothenemus hampei)",
        "affected_crops": ["coffee"],
        "symptoms": [
            "Tiny pinhole at tip of coffee berry",
            "Discoloured, shrivelled berries",
            "Premature berry drop",
            "Presence of fine sawdust-like frass at hole entrance",
            "Damaged beans with tunnels inside",
        ],
        "organic_control": [
            "Pick and destroy all remaining berries after harvest (strip picking)",
            "Use Beauveria bassiana fungal sprays during berry development",
            "Plant shade trees to reduce temperature favouring borers",
            "Use botanical extracts: neem, pyrethrum",
        ],
        "chemical_control": [
            "Apply endosulfan or chlorpyrifos during flight periods",
            "Use fipronil bait stations in severe cases",
            "Rotate insecticides to prevent resistance",
        ],
        "prevention": [
            "Remove all berries (including over-ripe) from trees and ground",
            "Prune to improve air circulation and reduce humidity",
            "Maintain consistent picking rounds (every 2 weeks)",
            "Use pheromone traps to monitor adult populations",
        ],
        "severity": "high",
    },
    "nematodes": {
        "name": "Plant-Parasitic Nematodes",
        "affected_crops": ["tomato", "pepper", "cabbage", "carrot", "cassava", "yam", "banana", "plantain"],
        "symptoms": [
            "Stunted growth and yellowing despite adequate nutrients",
            "Root galls, knots, or swellings (especially Meloidogyne)",
            "Root pruning and reduced root system",
            "Wilting during hot periods even with adequate soil moisture",
            "Necrotic lesions on roots and tubers",
        ],
        "organic_control": [
            "Apply neem cake to soil at 250 kg/ha before planting",
            "Incorporate marigold (Tagetes) residues into soil",
            "Use composted manure to increase beneficial microbes",
            "Apply Trichoderma harzianum as soil treatment",
            "Practice biofumigation with mustard or brassica residues",
        ],
        "chemical_control": [
            "Fumigate soil with metam sodium (pre-planting)",
            "Apply oxamyl or fenamiphos (use with extreme caution)",
            "Use abamectin-based nematicides",
        ],
        "prevention": [
            "Use certified nematode-free planting material",
            "Practice crop rotation with non-host crops (cereals)",
            "Solarize soil during hot season with clear plastic",
            "Improve soil organic matter content",
            "Use resistant rootstocks and varieties",
        ],
        "severity": "high",
    },
    "banana_weevil": {
        "name": "Banana Weevil (Cosmopolites sordidus)",
        "affected_crops": ["banana", "plantain"],
        "symptoms": [
            "Serrated notches on pseudostem base (adult feeding marks)",
            "Sawdust-like frass at base of pseudostem",
            "Wilting and death of young suckers",
            "Tunnels in corm with larvae inside",
            "Plant topples over easily",
        ],
        "organic_control": [
            "Use clean tissue-culture plantlets or pared suckers",
            "Apply neem cake powder around plant base (50g/plant)",
            "Use pseudostem traps: split stems laid on ground to attract adults",
            "Release Beauveria bassiana as biocontrol",
            "Parry (trim) corms thoroughly before planting to remove eggs",
        ],
        "chemical_control": [
            "Apply imidacloprid as soil drench at planting",
            "Use chlorpyrifos drench on severely affected mats",
        ],
        "prevention": [
            "Use tissue-culture planting material",
            "Trim and clean all suckers before planting (paring)",
            "Remove and destroy old pseudostems after harvest",
            "Rotate with non-host crops for 2+ years if possible",
        ],
        "severity": "high",
    },
    "bollworm": {
        "name": "Cotton Bollworm (Helicoverpa armigera)",
        "affected_crops": ["cotton", "tomato", "beans", "sorghum"],
        "symptoms": [
            "Holes in cotton bolls with frass",
            "Damaged flower buds and flowers",
            "Larvae visible inside bolls or fruit",
            "Premature boll opening with stained lint",
            "Ragged holes in leaves and stems",
        ],
        "organic_control": [
            "Handpick and destroy eggs and larvae",
            "Apply neem seed kernel extract (NSKE 5%)",
            "Use HaNPV (nuclear polyhedrosis virus) biopesticide",
            "Release Trichogramma spp. parasitoid wasps",
            "Use pheromone traps for mating disruption",
        ],
        "chemical_control": [
            "Apply spinosad or indoxacarb at egg hatch",
            "Use chlorantraniliprole (Prevathon) for resistant populations",
            "Rotate with emamectin benzoate",
            "Apply lambda-cyhalothrin for quick knockdown",
        ],
        "prevention": [
            "Monitor with pheromone traps weekly",
            "Plant trap crops (okra, marigold) on borders",
            "Maintain field sanitation — remove crop residues",
            "Use Bt cotton varieties where approved",
            "Avoid broad-spectrum insecticides that kill natural enemies",
        ],
        "severity": "critical",
    },
}

# ---------------------------------------------------------------------------
# Constants — Market Price Data (Indicative USD/kg)
# ---------------------------------------------------------------------------

MARKET_PRICES: Dict[str, Dict[str, float]] = {
    "maize": {"farm_gate_min": 0.20, "farm_gate_max": 0.45, "market_min": 0.30, "market_max": 0.60},
    "cassava": {"farm_gate_min": 0.08, "farm_gate_max": 0.20, "market_min": 0.15, "market_max": 0.35},
    "rice": {"farm_gate_min": 0.35, "farm_gate_max": 0.70, "market_min": 0.50, "market_max": 1.00},
    "sorghum": {"farm_gate_min": 0.18, "farm_gate_max": 0.40, "market_min": 0.25, "market_max": 0.55},
    "millet": {"farm_gate_min": 0.25, "farm_gate_max": 0.50, "market_min": 0.35, "market_max": 0.70},
    "beans": {"farm_gate_min": 0.60, "farm_gate_max": 1.50, "market_min": 0.90, "market_max": 2.00},
    "groundnut": {"farm_gate_min": 0.40, "farm_gate_max": 0.90, "market_min": 0.60, "market_max": 1.30},
    "sesame": {"farm_gate_min": 0.70, "farm_gate_max": 1.50, "market_min": 1.00, "market_max": 2.20},
    "cotton": {"farm_gate_min": 0.30, "farm_gate_max": 0.60, "market_min": 0.45, "market_max": 0.85},
    "tomato": {"farm_gate_min": 0.20, "farm_gate_max": 0.80, "market_min": 0.40, "market_max": 1.50},
    "pepper": {"farm_gate_min": 0.30, "farm_gate_max": 1.20, "market_min": 0.60, "market_max": 2.00},
    "onion": {"farm_gate_min": 0.15, "farm_gate_max": 0.50, "market_min": 0.30, "market_max": 0.80},
    "cabbage": {"farm_gate_min": 0.15, "farm_gate_max": 0.50, "market_min": 0.25, "market_max": 0.70},
    "mango": {"farm_gate_min": 0.30, "farm_gate_max": 0.80, "market_min": 0.50, "market_max": 1.50},
    "banana": {"farm_gate_min": 0.15, "farm_gate_max": 0.40, "market_min": 0.25, "market_max": 0.70},
    "pineapple": {"farm_gate_min": 0.20, "farm_gate_max": 0.50, "market_min": 0.35, "market_max": 0.90},
    "citrus": {"farm_gate_min": 0.25, "farm_gate_max": 0.70, "market_min": 0.40, "market_max": 1.20},
    "pawpaw": {"farm_gate_min": 0.20, "farm_gate_max": 0.60, "market_min": 0.35, "market_max": 1.00},
    "cocoa": {"farm_gate_min": 1.50, "farm_gate_max": 3.00, "market_min": 2.50, "market_max": 4.50},
    "coffee": {"farm_gate_min": 1.00, "farm_gate_max": 3.00, "market_min": 2.00, "market_max": 5.00},
    "yam": {"farm_gate_min": 0.25, "farm_gate_max": 0.70, "market_min": 0.40, "market_max": 1.20},
    "plantain": {"farm_gate_min": 0.15, "farm_gate_max": 0.50, "market_min": 0.25, "market_max": 0.80},
    "tea": {"farm_gate_min": 0.30, "farm_gate_max": 1.00, "market_min": 1.50, "market_max": 4.00},
}

# ---------------------------------------------------------------------------
# Constants — Buyer / Market Connections
# ---------------------------------------------------------------------------

BUYER_CONNECTIONS: Dict[str, Dict[str, List[str]]] = {
    "west_africa": {
        "maize": ["Local grain markets", "WFP procurement", "School feeding programs", "Feed mills", "Breweries"],
        "cassava": ["Garri processors", "Fufu makers", "Flour mills", "Animal feed manufacturers", "Starch factories"],
        "rice": ["Rice millers", "Urban wholesalers", "Supermarkets", "Restaurant chains", "Export brokers"],
        "cocoa": ["Licensed buying companies (LBCs)", "Cocoa Marketing Company", "CACAOBI", "Direct to exporters"],
        "yam": ["Urban markets", "Yam barn aggregators", "Export to diaspora markets", "Processors"],
        "tomato": ["Fresh markets", "Canning factories", "Juice processors", "Restaurant suppliers", "Export (neighbouring countries)"],
        "groundnut": ["Oil processors", "Snack makers", "Animal feed mills", "Export brokers"],
        "mango": ["Fresh fruit exporters", "Juice processors", "Dried fruit processors", "Urban markets"],
        "poultry": ["Live bird markets", "Hotels and restaurants", "Supermarkets", "Butcheries"],
    },
    "east_africa": {
        "maize": ["NCPB (Kenya)", "WFP", "UGMA (Uganda)", "Local millers", "School feeding"],
        "coffee": ["Cooperatives", "Coffee Board", "Direct exporters", "Auction houses", "Specialty buyers"],
        "tea": ["Tea factories", "KTDA (Kenya)", "Auctions at Mombasa", "Direct exporters"],
        "beans": ["Urban markets", "School feeding", "WFP", "Regional traders", "Canneries"],
        "banana": ["Urban markets", "Matooke traders", "Breweries", "Juice processors"],
        "dairy": ["Cooperative societies", "Processors (Brookside, Sameer)", "Direct to hotels", "Milk ATMs"],
        "horticulture": ["Export agents (flowers)", "Supermarkets (fresh produce)", "Air freight exporters", "Processing factories"],
    },
    "southern_africa": {
        "maize": ["FRA (Zambia)", "GMB (Zimbabwe)", "Millers", "WFP", "Regional traders"],
        "tobacco": ["Tobacco auction floors", "Contract buyers", "Export processors"],
        "cotton": ["Cotton Company", "Ginneries", "Lint exporters"],
        "groundnut": ["Processors", "Export traders", "Oil mills"],
        "sorghum": ["Breweries", "Livestock feed mills", "Urban markets"],
        "soybean": ["Oil processors", "Animal feed mills", "Export market"],
    },
    "central_africa": {
        "cassava": ["Local processors", "Urban markets", "Regional traders", "Fufu/garri makers"],
        "plantain": ["Urban markets", "Banana beer brewers", "Neighbouring countries"],
        "cocoa": ["ONCC (Cameroon)", "SODECAO", "International buyers"],
        "coffee": ["Cooperatives", "Export processors", "Local roasters"],
        "palm_oil": ["Village processors", "Industrial mills", "Soap manufacturers"],
    },
    "north_africa": {
        "wheat": ["Government buyers", "Millers", "Bakeries"],
        "dates": ["Export markets", "Processors", "Tourism gift markets"],
        "citrus": ["European exporters", "Juice processors", "Fresh markets"],
        "olives": ["Oil mills", "Export market", "Table olive processors"],
        "tomato": ["Canning factories", "Tomato paste processors", "Export (EU)", "Fresh markets"],
    },
}



# ---------------------------------------------------------------------------
# Class: CropAdvisor
# ---------------------------------------------------------------------------

class CropAdvisor:
    """Comprehensive crop advisory engine for African smallholder farmers.

    Provides detailed, context-aware guidance on planting, pest control,
    fertilization, harvesting, and seasonal crop calendars. All advice is
    tailored to the constraints and opportunities of 1–5 acre farms.

    Attributes:
        CROPS: Class-level reference to the comprehensive crop database.
        PEST_DATABASE: Class-level reference to the pest/disease database.
    """

    CROPS: Dict[str, Dict[str, Any]] = CROPS
    PEST_DATABASE: Dict[str, Dict[str, Any]] = PEST_DATABASE

    def __init__(self) -> None:
        """Initialize the CropAdvisor with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.CropAdvisor"
        )
        self._logger.info("CropAdvisor initialized")

    # ------------------------------------------------------------------
    # Planting Guidance
    # ------------------------------------------------------------------

    def get_planting_guide(
        self,
        crop: str,
        region: str = "west_africa",
        season: str = "rainy",
    ) -> Dict[str, Any]:
        """Generate a step-by-step planting guide for a specific crop.

        Args:
            crop: Crop name (e.g., 'maize', 'cassava', 'tomato').
            region: African region identifier.
            season: Planting season.

        Returns:
            Dictionary with detailed planting instructions.

        Raises:
            ValueError: If the crop is not in the database.
        """
        crop_key = crop.lower().strip()
        region_key = region.lower().strip().replace(" ", "_")
        season_key = season.lower().strip()

        if crop_key not in self.CROPS:
            available = ", ".join(sorted(self.CROPS.keys()))
            raise ValueError(
                f"Unknown crop '{crop}'. Available: {available}"
            )

        crop_data = self.CROPS[crop_key]
        steps = self._build_planting_steps(crop_key, region_key, season_key, crop_data)
        warnings = self._build_planting_warnings(crop_key, region_key, crop_data)

        guide: Dict[str, Any] = {
            "crop": crop_data["name"],
            "region": region_key,
            "season": season_key,
            "steps": steps,
            "spacing": f"{crop_data['spacing_cm'][0]}cm x {crop_data['spacing_cm'][1]}cm",
            "seed_rate": self._format_seed_rate(crop_key, crop_data),
            "planting_depth": self._get_planting_depth(crop_key),
            "days_to_germination": self._get_germination_days(crop_key),
            "days_to_maturity": f"{crop_data['days_to_maturity'][0]}-{crop_data['days_to_maturity'][1]}",
            "companion_crops": crop_data.get("companion_crops", []),
            "warnings": warnings,
            "optimal_ph": f"{crop_data['ph_range'][0]}-{crop_data['ph_range'][1]}",
            "rainfall_requirement_mm": f"{crop_data['rainfall_mm'][0]}-{crop_data['rainfall_mm'][1]}",
            "temperature_range_c": f"{crop_data['optimal_temp_c'][0]}-{crop_data['optimal_temp_c'][1]}",
            "disclaimer": GENERAL_DISCLAIMER,
        }

        self._logger.info(
            "Generated planting guide for %s in %s (%s)",
            crop_data["name"],
            region_key,
            season_key,
        )
        return guide

    def _build_planting_steps(
        self,
        crop: str,
        region: str,
        season: str,
        data: Dict[str, Any],
    ) -> List[str]:
        """Build context-aware planting steps."""
        steps: List[str] = []

        # Step 1: Land preparation
        if crop in ["rice"]:
            steps.append(
                "1. LAND PREPARATION: Puddle the field (plough and harrow under water) "
                "to create a soft mud for transplanting. Level the field for even water distribution. "
                "Construct bunds (embankments) 20–30cm high to retain water."
            )
        elif crop in ["cassava", "yam"]:
            steps.append(
                "1. LAND PREPARATION: Clear vegetation and plough to 25–30cm depth. "
                "Form ridges or mounds 30–40cm high for good tuber development. "
                "Space ridges 1 metre apart."
            )
        elif crop in ["cocoa", "coffee", "mango", "citrus", "banana", "plantain", "pawpaw"]:
            steps.append(
                "1. LAND PREPARATION: Dig planting holes 60cm x 60cm x 60cm at least 2 weeks "
                "before planting. Mix topsoil with 10–20kg well-decomposed manure per hole. "
                "Leave hole open for sun sterilization of soil."
            )
        else:
            steps.append(
                "1. LAND PREPARATION: Clear vegetation and plough to 15–20cm depth. "
                "Harrow to break clods and create fine tilth. For dry season planting, "
                "conserve soil moisture by minimum tillage or ripping."
            )

        # Step 2: Soil testing and amendment
        steps.append(
            "2. SOIL TESTING: Test soil pH and nutrient levels if possible. "
            f"Target pH: {data['ph_range'][0]}-{data['ph_range'][1]}. "
            "If soil testing is unavailable, observe: sandy soils need more organic matter, "
            "clay soils need drainage improvement. Add lime if soil is very acidic (pH < 5.0)."
        )

        # Step 3: Seed/Planting material selection
        if crop == "cassava":
            steps.append(
                "3. PLANTING MATERIAL: Select healthy, disease-free stem cuttings 20–30cm long "
                "from mature plants (8–12 months old). Use the middle portion of the stem. "
                "Avoid cuttings with brown streak disease symptoms. Treat cuttings with neem solution "
                "or wood ash before planting."
            )
        elif crop == "yam":
            steps.append(
                "3. PLANTING MATERIAL: Use whole seed yams (100–200g) or cut larger tubers into "
                "setts (100–150g each). Treat cut surfaces with wood ash or fungicide to prevent rot. "
                "Pre-sprout setts in a warm, humid place for 2–3 weeks before planting."
            )
        elif crop in ["banana", "plantain"]:
            steps.append(
                "3. PLANTING MATERIAL: Select sword suckers (40–60cm tall) with well-developed roots. "
                "Parry (trim) roots and remove all necrotic tissue. Dip in hot water (50°C for 20 minutes) "
                "or neem solution to kill nematodes and weevils before planting."
            )
        elif crop in ["cocoa", "coffee", "citrus"]:
            steps.append(
                "3. PLANTING MATERIAL: Purchase certified seedlings from reputable nurseries. "
                "Ensure seedlings are 6–12 months old, healthy, and disease-free. "
                "For coffee, choose disease-resistant varieties like Batian or Ruiru 11. "
                "Water seedlings thoroughly 24 hours before transplanting."
            )
        else:
            steps.append(
                "3. SEED SELECTION: Buy certified seeds from reputable agro-dealers. "
                "Check seed packaging for certification marks and expiry dates. "
                "For subsistence farmers, select the largest, healthiest seeds from your "
                "previous harvest. Treat seeds with appropriate seed dressing to prevent "
                "soil-borne diseases."
            )

        # Step 4: Planting timing
        if region in ["west_africa", "central_africa"]:
            steps.append(
                "4. PLANTING TIMING: Plant with the first reliable rains (March–April in the south, "
                "May–June in the north of the region). Ensure soil is moist to at least 10cm depth. "
                "Avoid planting if heavy rains are forecast within 48 hours (risk of seed washout)."
            )
        elif region in ["east_africa"]:
            steps.append(
                "4. PLANTING TIMING: For long rains, plant in March–April. For short rains, "
                "plant in October–November. Ensure 2–3 consecutive days of light rain have moistened "
                "the soil profile before planting."
            )
        elif region in ["southern_africa"]:
            steps.append(
                "4. PLANTING TIMING: Plant in November–December with the first reliable rains. "
                "In areas with supplementary irrigation, stagger plantings from October to January "
                "to spread labour and market risk."
            )
        elif region in ["sahel", "horn_of_africa"]:
            steps.append(
                "4. PLANTING TIMING: Plant immediately after the first 30–40mm of rainfall "
                "that wets the soil to 15cm depth. This is typically late June to early July. "
                "Use drought-tolerant varieties and plant slightly deeper (5–8cm) to access moisture."
            )
        elif region in ["north_africa"]:
            steps.append(
                "4. PLANTING TIMING: Plant in October–November for winter crops, or February–March "
                "for spring/summer crops under irrigation. Avoid mid-summer planting due to heat stress."
            )
        else:
            steps.append(
                "4. PLANTING TIMING: Plant at the onset of the rainy season when soil moisture "
                "is adequate for germination. Consult local agricultural extension for specific dates."
            )

        # Step 5: Planting method
        spacing_x, spacing_y = data["spacing_cm"]
        if crop in ["rice"]:
            steps.append(
                "5. PLANTING METHOD: For direct seeding, broadcast pre-germinated seeds on "
                "puddled field at 80–100kg/ha. For transplanting, plant 2–3 seedlings per hill "
                "at 20cm x 20cm spacing. Plant at 2–3cm depth in puddled soil."
            )
        elif crop in ["maize", "sorghum", "millet"]:
            steps.append(
                f"5. PLANTING METHOD: Plant seeds at {spacing_x}cm between rows and "
                f"{spacing_y}cm between plants within the row. Plant 2–3 seeds per hole "
                f"at {self._get_planting_depth(crop)} depth. Thin to 1 plant per hole "
                f"2–3 weeks after emergence, keeping the strongest seedling."
            )
        elif crop in ["cassava", "yam"]:
            steps.append(
                f"5. PLANTING METHOD: Place cuttings/setts on top of ridges/mounds at "
                f"{spacing_x}cm x {spacing_y}cm spacing. Plant yam setts with cut surface "
                "facing up, 5–10cm deep. Cover cassava cuttings with 5–8cm of soil, "
                "leaving 2–3 nodes above ground."
            )
        elif crop in ["beans", "groundnut", "sesame"]:
            steps.append(
                f"5. PLANTING METHOD: Plant seeds at {spacing_x}cm between rows and "
                f"{spacing_y}cm between plants. Sow 2 seeds per hole at "
                f"{self._get_planting_depth(crop)} depth. Inoculate legume seeds "
                "with Rhizobium culture for better nitrogen fixation."
            )
        elif crop in ["tomato", "pepper", "cabbage", "onion"]:
            steps.append(
                f"5. PLANTING METHOD: For transplanted vegetables, harden seedlings 7–10 days "
                "before transplanting. Plant at {spacing_x}cm x {spacing_y}cm spacing. "
                "Water immediately after transplanting. Use mulch to conserve moisture "
                "and suppress weeds."
            )
        else:
            steps.append(
                f"5. PLANTING METHOD: Plant at {spacing_x}cm x {spacing_y}cm spacing. "
                f"Follow depth guidelines of {self._get_planting_depth(crop)}. "
                "Ensure good soil-to-seed contact for moisture uptake."
            )

        # Step 6: Fertilizer application
        npk = data.get("fertilizer_npk", "NPK application based on soil test")
        steps.append(
            f"6. FERTILIZER: Apply basal fertilizer at planting — {npk} kg/ha of NPK. "
            "Place fertilizer 5cm to the side and 5cm below the seed (do not mix directly with seed). "
            "Top-dress with nitrogen 4–6 weeks after planting. Use compost or well-rotted manure "
            "as organic alternative: 5–10 tonnes/ha applied before planting."
        )

        # Step 7: Weed management
        steps.append(
            "7. WEED MANAGEMENT: Keep the field weed-free for the first 6–8 weeks after planting. "
            "Weed by hand-hoeing (most common for smallholders) or use a mechanical hand weeder. "
            "Weed at 2, 4, and 6 weeks after planting. Apply mulch between rows to suppress weed "
            "growth and conserve moisture."
        )

        # Step 8: Water management
        if crop in ["rice"]:
            steps.append(
                "8. WATER MANAGEMENT: Maintain 2–5cm water depth in the field for the first "
                "4 weeks after transplanting. Gradually increase to 5–10cm at flowering. "
                "Drain field 2 weeks before harvest for easier harvesting."
            )
        elif crop in ["cassava", "sorghum", "millet", "sesame"]:
            steps.append(
                "8. WATER MANAGEMENT: These crops are drought-tolerant but yield better with "
                "consistent moisture during establishment (first 4 weeks). If rains fail, "
                "consider supplementary watering or water harvesting techniques."
            )
        else:
            steps.append(
                "8. WATER MANAGEMENT: Ensure consistent soil moisture, especially during "
                "flowering and grain-filling stages. If rainfall is inadequate, use drip irrigation "
                "bottles, watering cans, or simple bucket drip systems. Apply mulch to reduce "
                "evaporation by 30–50%."
            )

        # Step 9: Pest monitoring
        steps.append(
            "9. PEST MONITORING: Scout your field twice weekly for signs of pests and diseases. "
            "Check leaf undersides, stems, and soil surface. Early detection saves crops. "
            "Use pheromone traps where available. Identify unknown pests using this app's "
            "pest diagnosis feature or consult your local extension officer."
        )

        # Step 10: Harvest preparation
        maturity_range = data["days_to_maturity"]
        steps.append(
            f"10. HARVEST PLANNING: Crop matures in {maturity_range[0]}-{maturity_range[1]} days. "
            "Arrange labour and storage before maturity. Identify buyers or markets in advance. "
            "Harvest during dry weather to reduce post-harvest losses."
        )

        return steps

    def _build_planting_warnings(
        self, crop: str, region: str, data: Dict[str, Any]
    ) -> List[str]:
        """Build region and crop-specific warnings."""
        warnings: List[str] = []

        if region in ["sahel", "horn_of_africa"]:
            warnings.append(
                "⚠️ ARID REGION: Rainfall is unreliable. Use drought-tolerant varieties, "
                "plant early with the rains, and consider water harvesting techniques. "
                "Have a contingency plan for crop failure."
            )

        if region in ["central_africa"]:
            warnings.append(
                "⚠️ HIGH RAINFALL: Excess moisture can cause root rot and fungal diseases. "
                "Ensure good drainage. Plant on raised beds or ridges."
            )

        if crop in ["maize", "sorghum", "millet"]:
            warnings.append(
                "⚠️ FALL ARMYWORM: This pest can destroy entire fields within days. "
                "Scout twice weekly during the first 8 weeks. Have neem oil or recommended "
                "insecticide ready at planting."
            )

        if crop in ["cassava"]:
            warnings.append(
                "⚠️ CASSAVA BROWN STREAK DISEASE: Use disease-free planting material only. "
                "Do not plant cuttings from diseased fields. Report suspected cases to extension officers."
            )

        if crop in ["tomato", "pepper"]:
            warnings.append(
                "⚠️ TOMATO YELLOW LEAF CURL VIRUS: Spread by whiteflies. Use resistant varieties, "
                "netting for nurseries, and whitefly control from early growth stages."
            )

        if crop in ["cocoa", "coffee"]:
            warnings.append(
                "⚠️ LONG-TERM INVESTMENT: First harvest is 2–4 years after planting. "
                "Ensure you have alternative income sources during the establishment period."
            )

        if data["drought_tolerance"] in ["low", "very_low"]:
            warnings.append(
                "⚠️ WATER SENSITIVE: This crop requires consistent moisture. "
                "In rain-fed systems, yield loss is high during drought. Consider irrigation "
                "or plant only in reliable rainfall zones."
            )

        warnings.append(GENERAL_DISCLAIMER)
        return warnings

    def _format_seed_rate(self, crop: str, data: Dict[str, Any]) -> str:
        """Format seed rate information for display."""
        rate = data.get("seed_rate_kg_per_ha", 0)
        if rate == 0:
            if crop in ["cassava"]:
                return "10,000–15,000 stem cuttings per hectare (20–30cm long)"
            elif crop in ["yam"]:
                return "Whole seed yams or 100–150g setts; 10,000–15,000 setts/hectare"
            elif crop in ["banana", "plantain"]:
                return "1,100–1,300 suckers per hectare"
            elif crop in ["cocoa", "coffee", "citrus", "mango"]:
                return "Seedlings from certified nursery: 1,000–1,200 per hectare"
            else:
                return "See planting material section above"
        return f"{rate} kg per hectare ({rate * 0.4:.1f} kg per acre)"

    def _get_planting_depth(self, crop: str) -> str:
        """Return recommended planting depth for a crop."""
        depth_map: Dict[str, str] = {
            "maize": "3–5cm",
            "sorghum": "3–5cm",
            "millet": "2–3cm",
            "rice": "2–3cm (puddled soil)",
            "cassava": "5–8cm (angled at 45°)",
            "yam": "5–10cm on mounds",
            "beans": "3–5cm",
            "groundnut": "3–5cm",
            "sesame": "1–2cm",
            "cotton": "2–3cm",
            "tomato": "Transplant seedlings at cotyledon level",
            "pepper": "Transplant seedlings at root ball depth",
            "onion": "1–2cm (direct seed) or transplant seedlings",
            "cabbage": "Transplant at root ball depth",
            "banana": "50cm deep in prepared hole",
            "plantain": "50cm deep in prepared hole",
            "cocoa": "Level with nursery soil in 60cm hole",
            "coffee": "Level with nursery soil in 60cm hole",
            "mango": "Level with nursery soil in 60cm hole",
            "citrus": "Level with nursery soil in 60cm hole",
            "pawpaw": "Level with nursery soil in 40cm hole",
            "pineapple": "5–8cm deep",
        }
        return depth_map.get(crop, "3–5cm (consult local guidelines)")

    def _get_germination_days(self, crop: str) -> int:
        """Return typical days to germination."""
        germination_map: Dict[str, int] = {
            "maize": 5, "sorghum": 5, "millet": 4, "rice": 7,
            "cassava": 14, "yam": 21, "beans": 7, "groundnut": 7,
            "sesame": 5, "cotton": 7, "tomato": 7, "pepper": 10,
            "onion": 10, "cabbage": 5, "banana": 21, "plantain": 21,
            "cocoa": 14, "coffee": 21, "mango": 14, "citrus": 21,
            "pawpaw": 14, "pineapple": 30,
        }
        return germination_map.get(crop, 7)

    # ------------------------------------------------------------------
    # Pest Control
    # ------------------------------------------------------------------

    def get_pest_control(
        self,
        crop: str,
        pest_symptoms: str,
    ) -> Dict[str, Any]:
        """Identify pests based on crop and symptoms, provide control recommendations.

        Args:
            crop: Crop name.
            pest_symptoms: Description of observed symptoms.

        Returns:
            Dictionary with pest identification and control measures.
        """
        crop_key = crop.lower().strip()
        symptoms_lower = pest_symptoms.lower()

        matched_pests: List[str] = []

        # Match against pest database
        for pest_key, pest_data in self.PEST_DATABASE.items():
            if crop_key in [c.lower() for c in pest_data.get("affected_crops", [])]:
                # Check symptom keywords
                for symptom in pest_data.get("symptoms", []):
                    symptom_words = symptom.lower().split()
                    match_count = sum(
                        1 for word in symptom_words if len(word) > 3 and word in symptoms_lower
                    )
                    if match_count >= 2:
                        matched_pests.append(pest_key)
                        break

        # Also do keyword matching on pest names and symptoms
        keyword_matches = self._match_pest_by_keywords(crop_key, symptoms_lower)
        for kw_match in keyword_matches:
            if kw_match not in matched_pests:
                matched_pests.append(kw_match)

        if not matched_pests:
            # Return general guidance
            return {
                "crop": crop,
                "symptoms_reported": pest_symptoms,
                "pest_identified": "Could not identify specific pest from description",
                "matched_pests": [],
                "organic_control": [
                    "1. Inspect plants carefully and collect samples of the pest/damage.",
                    "2. Remove and destroy heavily infested plant parts.",
                    "3. Spray neem oil (5ml per litre of water) as a broad-spectrum organic treatment.",
                    "4. Apply wood ash around plant bases to deter soft-bodied pests.",
                    "5. Encourage natural predators (birds, spiders, wasps) by reducing pesticide use.",
                    "6. Maintain field hygiene — remove crop residues and weeds.",
                ],
                "chemical_control": [
                    "Consult a local agro-dealer or extension officer for specific pesticide recommendations.",
                    "Always follow label instructions and pre-harvest intervals.",
                    "Rotate chemical classes to prevent resistance.",
                ],
                "prevention": [
                    "Use certified, disease-free seeds and planting material.",
                    "Practice crop rotation.",
                    "Maintain optimal plant spacing for air circulation.",
                    "Scout fields regularly for early pest detection.",
                ],
                "disclaimer": (
                    "Could not match symptoms to a known pest in our database. "
                    "Please consult your local agricultural extension officer with photos "
                    "or samples for accurate diagnosis."
                ),
            }

        # Build detailed response for matched pests
        pest_details: List[Dict[str, Any]] = []
        for pest_key in matched_pests[:3]:  # Top 3 matches
            pest_data = self.PEST_DATABASE[pest_key]
            pest_details.append({
                "pest_name": pest_data["name"],
                "matched_symptoms": [
                    s for s in pest_data["symptoms"]
                    if any(w in symptoms_lower for w in s.lower().split() if len(w) > 4)
                ] or pest_data["symptoms"][:2],
                "severity": pest_data.get("severity", "medium"),
                "organic_control": pest_data.get("organic_control", []),
                "chemical_control": pest_data.get("chemical_control", []),
                "prevention": pest_data.get("prevention", []),
            })

        return {
            "crop": crop,
            "symptoms_reported": pest_symptoms,
            "matched_pests": pest_details,
            "top_recommendation": pest_details[0] if pest_details else None,
            "general_organic_tips": [
                "Neem oil spray: Mix 5ml neem oil + 2ml soap per litre of water. Spray every 7–10 days.",
                "Wood ash: Sprinkle dry wood ash on leaves and around stems to deter pests.",
                "Chilli-garlic spray: Blend 50g chilli + 50g garlic + 1L water. Strain and spray.",
                "Companion planting: Plant marigolds, basil, or onions near crops to repel pests.",
            ],
            "disclaimer": (
                "Pest identification is based on symptom matching. For definitive diagnosis, "
                "consult your local agricultural extension officer with physical samples."
            ),
        }

    def _match_pest_by_keywords(
        self, crop: str, symptoms: str
    ) -> List[str]:
        """Match pests using keyword heuristics."""
        matches: List[str] = []
        keyword_map: Dict[str, List[str]] = {
            "fall_armyworm": ["armyworm", "ragged holes", "whorl", "frass", "y shape", "y mark"],
            "stem_borer": ["dead heart", "stem hole", "lodging", "sawdust", "stem tunnel"],
            "aphids": ["aphid", "green fly", "black fly", "cluster", "honeydew", "sooty mold"],
            "whitefly": ["white fly", "whitefly", "white insect", "yellow curl"],
            "cassava_mealybug": ["mealybug", "woolly", "bunchy top", "cassava"],
            "fruit_fly": ["fruit fly", "maggot in fruit", "fruit drop", "fruit sting"],
            "coffee_berry_borer": ["berry borer", "pinhole", "coffee berry"],
            "nematodes": ["root knot", "gall", "stunted", "root swelling", "nematode"],
            "banana_weevil": ["weevil", "pseudostem", "notch", "corm tunnel"],
            "bollworm": ["bollworm", "boll hole", "lint stain", "fruit borer"],
        }
        for pest, keywords in keyword_map.items():
            if any(kw in symptoms for kw in keywords):
                pest_data = self.PEST_DATABASE.get(pest, {})
                affected = [c.lower() for c in pest_data.get("affected_crops", [])]
                if not affected or crop in affected:
                    matches.append(pest)
        return matches

    # ------------------------------------------------------------------
    # Fertilizer Guidance
    # ------------------------------------------------------------------

    def get_fertilizer_guide(
        self,
        crop: str,
        soil_type: str = "loamy",
        budget: str = "low",
    ) -> Dict[str, Any]:
        """Generate fertilizer recommendations based on crop, soil, and budget.

        Args:
            crop: Crop name.
            soil_type: Soil type description.
            budget: Budget level (very_low, low, medium, high).

        Returns:
            Dictionary with fertilizer recommendations.
        """
        crop_key = crop.lower().strip()
        soil_key = soil_type.lower().strip().replace(" ", "_")
        budget_key = budget.lower().strip()

        if crop_key not in self.CROPS:
            available = ", ".join(sorted(self.CROPS.keys()))
            raise ValueError(f"Unknown crop '{crop}'. Available: {available}")

        crop_data = self.CROPS[crop_key]
        base_npk = crop_data.get("fertilizer_npk", "NPK based on soil test")

        # Adjust NPK based on soil type
        adjusted_npk = self._adjust_npk_for_soil(base_npk, soil_key)

        # Build organic options based on budget
        organic_options = self._get_organic_fertilizer_options(crop_key, budget_key)

        # Build inorganic options based on budget
        inorganic_options = self._get_inorganic_fertilizer_options(
            crop_key, adjusted_npk, budget_key
        )

        # Application timing
        application_timing = self._get_fertilizer_timing(crop_key)

        # Cost estimate
        estimated_cost = self._estimate_fertilizer_cost(crop_key, budget_key, adjusted_npk)

        # Micronutrients
        micronutrients = self._get_micronutrient_recommendations(crop_key, soil_key)

        return {
            "crop": crop_data["name"],
            "soil_type": soil_key,
            "budget_level": budget_key,
            "npk_recommendation_kg_per_ha": adjusted_npk,
            "organic_options": organic_options,
            "inorganic_options": inorganic_options,
            "application_timing": application_timing,
            "estimated_cost_usd_per_acre": estimated_cost,
            "micronutrients": micronutrients,
            "soil_specific_tips": self._get_soil_specific_tips(soil_key),
            "disclaimer": (
                "Fertilizer recommendations are general guidelines. For precise rates, "
                "conduct a soil test through your local extension service or agro-dealer."
            ),
        }

    def _adjust_npk_for_soil(self, base_npk: str, soil_type: str) -> str:
        """Adjust NPK ratio based on soil characteristics."""
        try:
            parts = base_npk.split(":")
            n, p, k = int(parts[0]), int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            return base_npk

        if "sandy" in soil_type:
            # Sandy soils leach nutrients; increase all + add organic matter
            n, p, k = int(n * 1.2), int(p * 1.1), int(k * 1.2)
        elif "clay" in soil_type:
            # Clay holds nutrients; reduce slightly, emphasize drainage
            n, p, k = int(n * 0.9), p, int(k * 0.9)
        elif "laterite" in soil_type:
            # Acidic, phosphorus fixation
            p = int(p * 1.3)
            # Recommend lime
        elif "volcanic" in soil_type:
            # Rich soils; reduce inputs
            n, p, k = int(n * 0.8), int(p * 0.8), int(k * 0.8)
        elif "alluvial" in soil_type:
            # Generally fertile; moderate inputs
            pass

        return f"{n}:{p}:{k}"

    def _get_organic_fertilizer_options(
        self, crop: str, budget: str
    ) -> List[str]:
        """Get organic fertilizer options tailored to budget."""
        options: List[str] = []

        if budget in ["very_low", "low"]:
            options.extend([
                "Compost: Collect crop residues, animal manure, and kitchen waste. "
                "Pile and turn every 2 weeks. Apply 5–10 tonnes/hectare (2–4 tons/acre) "
                "2 weeks before planting. Cost: labour only.",
                "Farmyard manure (FYM): Apply well-rotted cattle/goat manure at "
                "5 tonnes/hectare. Spread and incorporate into soil before planting.",
                "Green manure: Plant Tithonia (Mexican sunflower), Crotalaria, or "
                "Mucuna 6–8 weeks before main crop. Plough into soil at flowering.",
                "Wood ash: Rich in potassium and calcium. Apply 2–3 handfuls per planting hole. "
                "Especially good for acidic soils.",
                "Vermicompost: If available, apply 2–3 tonnes/hectare. High quality but "
                "requires initial worm culture setup.",
            ])
        else:
            options.extend([
                "Compost: 5–10 tonnes/hectare, incorporated 2 weeks before planting.",
                "Vermicompost: 2–3 tonnes/hectare for high-value crops.",
                "Green manure crops: Crotalaria, Tithonia, Mucuna — incorporate at flowering.",
                "Biofertilizers: Rhizobium for legumes, Azospirillum for cereals, "
                "PSB (phosphate solubilizing bacteria) for phosphorus availability.",
                "Liquid organic fertilizers: Fermented plant extracts (Tithonia, Comfrey) "
                "as foliar feeds.",
            ])

        if crop in ["maize", "sorghum", "millet", "rice"]:
            options.append(
                "Legume intercrop: Plant beans, cowpea, or groundnut between cereal rows "
                "to fix nitrogen naturally."
            )

        return options

    def _get_inorganic_fertilizer_options(
        self, crop: str, npk: str, budget: str
    ) -> List[str]:
        """Get inorganic fertilizer options."""
        options: List[str] = []

        try:
            parts = npk.split(":")
            n, p, k = int(parts[0]), int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            n, p, k = 50, 30, 30

        if budget == "very_low":
            options.extend([
                f"Urea (46% N): Apply {n}kg N/ha. Split application: half at planting, "
                f"half at top-dressing (4–6 weeks). Cost-effective nitrogen source.",
                f"DAP (18-46-0): Apply {max(30, p // 2)}kg/ha at planting for phosphorus "
                "and starter nitrogen.",
            ])
        elif budget == "low":
            options.extend([
                f"NPK {self._nearest_npk_grade(n, p, k)}: Apply as basal fertilizer at planting. "
                f"Rate: {n + p + k}kg/hectare total nutrients.",
                f"Urea (46% N): Top-dress with {n // 2}kg/ha at 4–6 weeks after planting.",
                f"MOP (60% K): Apply {k}kg/ha if soil is low in potassium.",
            ])
        elif budget == "medium":
            options.extend([
                f"NPK {self._nearest_npk_grade(n, p, k)}: Basal application at planting.",
                f"Urea: Top-dress in splits — first at 3 weeks, second at 6 weeks.",
                f"Calcium Ammonium Nitrate (CAN): Alternative to urea for acid soils. "
                f"Apply {n}kg N equivalent.",
                "Micronutrient fertilizer: Apply Zinc sulphate (10kg/ha) if deficiency symptoms observed.",
            ])
        else:  # high
            options.extend([
                f"NPK {self._nearest_npk_grade(n, p, k)} + micronutrients: Precision application.",
                "Controlled-release fertilizers: Reduce leaching, improve nutrient use efficiency.",
                "Fertigation: Apply fertilizer through drip irrigation for precision.",
                "Foliar feeding: Apply micronutrient sprays during critical growth stages.",
                "Soil testing: Conduct annual soil tests to fine-tune recommendations.",
            ])

        return options

    def _nearest_npk_grade(self, n: int, p: int, k: int) -> str:
        """Return the nearest commercial NPK fertilizer grade."""
        # Common African fertilizer grades
        grades = ["15-15-15", "17-17-17", "20-10-10", "23-23-0", "25-10-10",
                  "12-24-12", "10-20-10", "0-0-60", "18-46-0"]
        # Simple matching — in production, compute actual nearest
        if n >= 20:
            return "23-23-0" if k < 15 else "20-10-10"
        elif n >= 15:
            return "15-15-15" if k >= 10 else "23-23-0"
        elif p >= 20:
            return "0-20-0" if k < 10 else "12-24-12"
        else:
            return "15-15-15"

    def _get_fertilizer_timing(self, crop: str) -> List[str]:
        """Get fertilizer application timing for a crop."""
        timing: List[str] = []

        timing.append(
            "BASAL (At planting): Apply all phosphorus, half nitrogen, and "
            "half potassium. Place 5cm to the side and 5cm below the seed."
        )

        if crop in ["maize", "sorghum", "millet", "rice"]:
            timing.append(
                "TOP-DRESS 1 (4–5 weeks): Apply remaining nitrogen when crop is knee-high. "
                "Side-dress along rows and cover with soil."
            )
            timing.append(
                "TOP-DRESS 2 (8–9 weeks, for maize only): Apply additional nitrogen "
                "at tasseling if growth is poor."
            )
        elif crop in ["tomato", "pepper", "cabbage"]:
            timing.append(
                "TOP-DRESS (3–4 weeks after transplanting): Side-dress nitrogen and potassium. "
                "Repeat at flowering/head formation."
            )
        elif crop in ["cassava", "yam"]:
            timing.append(
                "TOP-DRESS (6–8 weeks): Apply nitrogen when tuber initiation begins. "
                "Do not apply after 12 weeks as it promotes leaf over tuber growth."
            )
        elif crop in ["beans", "groundnut"]:
            timing.append(
                "TOP-DRESS (3–4 weeks): Light nitrogen application only if poor nodulation. "
                "Focus on phosphorus and micronutrients (molybdenum for nodulation)."
            )
        elif crop in ["cocoa", "coffee"]:
            timing.append(
                "SPLIT APPLICATION: Apply fertilizer in 2–3 splits during rainy season. "
                "Avoid application during dry periods. Band apply under tree canopy."
            )

        timing.append(
            "IMPORTANT: Always apply fertilizer when soil is moist. "
            "Water immediately after application if no rain is expected within 48 hours."
        )

        return timing

    def _estimate_fertilizer_cost(
        self, crop: str, budget: str, npk: str
    ) -> float:
        """Estimate fertilizer cost per acre in USD."""
        cost_map: Dict[str, float] = {
            "very_low": 15.0,
            "low": 35.0,
            "medium": 75.0,
            "high": 150.0,
        }
        base_cost = cost_map.get(budget, 35.0)

        # Adjust for crop nutrient demand
        high_demand_crops = ["tomato", "pepper", "cabbage", "cocoa", "coffee", "tea"]
        low_demand_crops = ["millet", "sorghum", "sesame", "cassava"]

        if crop in high_demand_crops:
            base_cost *= 1.3
        elif crop in low_demand_crops:
            base_cost *= 0.8

        return round(base_cost, 2)

    def _get_micronutrient_recommendations(
        self, crop: str, soil_type: str
    ) -> List[str]:
        """Get micronutrient recommendations."""
        recommendations: List[str] = []

        if crop in ["maize", "rice", "sorghum"]:
            recommendations.append(
                "Zinc (Zn): Apply zinc sulphate at 10kg/ha if deficiency is suspected "
                "(interveinal chlorosis on young leaves)."
            )

        if crop in ["beans", "groundnut", "soybean"]:
            recommendations.append(
                "Molybdenum (Mo): Essential for nitrogen fixation. Apply sodium molybdate "
                "at 100g/ha as seed treatment or foliar spray."
            )

        if crop in ["tomato", "pepper", "cabbage"]:
            recommendations.append(
                "Calcium (Ca): Apply agricultural lime or gypsum to prevent blossom end rot "
                "in tomatoes and peppers. Ensure adequate watering."
            )
            recommendations.append(
                "Boron (B): Apply borax at 5kg/ha for fruit set and development."
            )

        if "laterite" in soil_type or "sandy" in soil_type:
            recommendations.append(
                "Magnesium (Mg): Sandy and lateritic soils are often magnesium deficient. "
                "Apply dolomitic lime or magnesium sulphate at 20kg/ha."
            )

        if crop in ["citrus", "mango", "pawpaw"]:
            recommendations.append(
                "Iron (Fe): Apply iron chelate or ferrous sulphate if interveinal chlorosis "
                "appears on new growth (common in alkaline soils)."
            )

        if not recommendations:
            recommendations.append(
                "Micronutrients: Apply a general micronutrient mix at 2–5kg/ha if "
                "deficiency symptoms are observed."
            )

        return recommendations

    def _get_soil_specific_tips(self, soil_type: str) -> List[str]:
        """Get soil management tips."""
        tips: Dict[str, List[str]] = {
            "sandy": [
                "Sandy soils drain quickly and lose nutrients. Add organic matter regularly.",
                "Apply fertilizer in small, frequent doses (split application).",
                "Use mulch to reduce evaporation and temperature fluctuations.",
                "Consider raised beds to concentrate nutrients in root zone.",
            ],
            "clay": [
                "Clay soils hold water but may drain poorly. Add sand and organic matter to improve structure.",
                "Avoid working clay soil when wet — it damages soil structure.",
                "Plant on ridges or raised beds to improve drainage.",
                "Apply lime to improve structure if soil is acidic.",
            ],
            "loamy": [
                "Loamy soils are ideal — maintain with regular organic matter additions.",
                "Practice crop rotation to prevent nutrient depletion.",
                "Use cover crops during off-seasons to protect soil structure.",
            ],
            "laterite": [
                "Lateritic soils are acidic and phosphorus-fixing. Apply lime to raise pH.",
                "Use rock phosphate instead of soluble P fertilizers for better efficiency.",
                "Build organic matter content — it buffers acidity and improves nutrient availability.",
            ],
            "volcanic": [
                "Volcanic soils are naturally fertile. Focus on maintaining organic matter.",
                "Monitor for micronutrient deficiencies despite overall fertility.",
            ],
            "alluvial": [
                "Alluvial soils are generally fertile. Maintain with compost additions.",
                "Watch for waterlogging — ensure adequate drainage.",
            ],
        }
        return tips.get(soil_type, ["Maintain soil health through regular organic matter additions."])

    # ------------------------------------------------------------------
    # Harvest Guidance
    # ------------------------------------------------------------------

    def get_harvest_guide(self, crop: str) -> Dict[str, Any]:
        """Generate harvest and post-harvest handling guidance.

        Args:
            crop: Crop name.

        Returns:
            Dictionary with harvest timing, methods, and post-harvest advice.
        """
        crop_key = crop.lower().strip()

        if crop_key not in self.CROPS:
            available = ", ".join(sorted(self.CROPS.keys()))
            raise ValueError(f"Unknown crop '{crop}'. Available: {available}")

        crop_data = self.CROPS[crop_key]

        return {
            "crop": crop_data["name"],
            "maturity_indicators": self._get_maturity_indicators(crop_key),
            "harvest_method": self._get_harvest_method(crop_key),
            "tools_needed": self._get_harvest_tools(crop_key),
            "post_harvest_handling": self._get_post_harvest_steps(crop_key),
            "storage_methods": self._get_storage_methods(crop_key, crop_data),
            "expected_yield_per_acre": self._format_yield_per_acre(crop_data),
            "value_addition_opportunities": self._get_value_addition(crop_key),
            "disclaimer": GENERAL_DISCLAIMER,
        }

    def _get_maturity_indicators(self, crop: str) -> List[str]:
        """Return maturity indicators for a crop."""
        indicators: Dict[str, List[str]] = {
            "maize": [
                "Kernels are hard and dry (not milky when pressed)",
                "Husks turn brown and dry",
                "Black layer visible at base of kernel (physiological maturity)",
                "Grain moisture content: 20–25% at harvest, dry to 13.5% for storage",
            ],
            "cassava": [
                "Leaves start yellowing and falling (natural senescence)",
                "Tuber skin becomes firm and easy to peel",
                "Typically 9–12 months after planting (varies by variety)",
                "Harvest a few plants first to check tuber size",
            ],
            "rice": [
                "Grains turn golden yellow and firm",
                "80–85% of grains on panicle are golden (not green)",
                "Grain moisture: 20–25% at harvest",
                "Harvest before shattering (grain falling from panicle)",
            ],
            "sorghum": [
                "Grains are hard and cannot be dented with fingernail",
                "Panicle bends downward (droop)",
                "Black layer formed at grain base",
                "Moisture content: 20–25%",
            ],
            "millet": [
                "Grains turn from green to golden brown",
                "Heads droop when mature",
                "Grains are hard and shiny",
                "Harvest before birds consume the grains",
            ],
            "yam": [
                "Vines yellow and dry completely (8–10 months)",
                "Tuber skin becomes firm with visible scaling",
                "Harvest during dry season for best storage quality",
                "Handle very carefully — yams bruise easily",
            ],
            "beans": [
                "Pods turn yellow/brown and dry",
                "Beans inside are hard and show variety colour",
                "Harvest before pods shatter (split open)",
                "Moisture content: 15–18% at harvest, dry to 14% for storage",
            ],
            "groundnut": [
                "Leaves turn yellow (not due to disease)",
                "Inside shells, kernels show typical skin colour",
                "Test: scrape shell — dark marks indicate maturity",
                "Harvest immediately — delay causes pod shedding and aflatoxin",
            ],
            "tomato": [
                "Fruits reach full size and develop characteristic colour (red, yellow, etc.)",
                "Firm but slightly soft to touch",
                "Harvest breaker stage (first blush) for distant markets",
                "Harvest fully ripe for local consumption",
            ],
            "pepper": [
                "Fruits reach full size and develop colour",
                "Green peppers: harvest when full-sized and firm",
                "Coloured peppers: allow to ripen on plant for premium price",
                "Cut with scissors — do not pull (damages plant)",
            ],
            "onion": [
                "Tops fall over and begin to dry",
                "Necks soften and outer scales become papery",
                "Harvest when 50–80% of tops have fallen",
                "Lift bulbs carefully and cure in sun for 5–7 days",
            ],
            "cabbage": [
                "Head is firm and solid when squeezed",
                "Head reaches desired size (varies by market)",
                "Harvest before head splits (especially after rain)",
                "Cut with knife, leaving 2–3 wrapper leaves for protection",
            ],
            "mango": [
                "Shoulder (shoulder of fruit near stem) fills out and becomes rounded",
                "Fruit shows colour break (development of variety colour)",
                "Lenticels (dots) become more visible",
                "Sap flow reduces; test sample for sugar content (BRIX)",
            ],
            "banana": [
                "Fruits are full-sized with edges still angular (not rounded)",
                "One hand can be cut to test ripening",
                "Harvest at 3/4 mature (green stage) for distant transport",
                "Use clean, sharp tools to avoid bruising",
            ],
            "pineapple": [
                "Fruit skin colour changes from dark green to yellow/orange at base",
                "Fruit emits strong pineapple aroma at base",
                "A leaf from crown pulls out easily",
                "BRIX reading: 12–14% soluble solids",
            ],
            "cocoa": [
                "Pods turn from green/green-purple to yellow/orange/red (varies by variety)",
                "Rattle test: seeds rattle when pod is shaken (over-mature if loud)",
                "Harvest every 2–3 weeks during main season",
                "Use long-handled hook or cutlass — do not damage tree",
            ],
            "coffee": [
                "Cherries turn from green to red (Arabica) or yellow (some varieties)",
                "Pick only fully ripe cherries for best quality",
                "Harvest selectively (multiple passes, every 2–3 weeks)",
                "Wet process within 24 hours of picking for quality",
            ],
        }
        return indicators.get(crop, ["Consult local guidelines for maturity indicators.",
                                       "Harvest at physiological maturity for best quality and yield."])

    def _get_harvest_method(self, crop: str) -> str:
        """Return recommended harvest method."""
        methods: Dict[str, str] = {
            "maize": "Hand-pick cobs or cut stalks with cutlass. Shell using hand sheller or by hand.",
            "cassava": "Loosen soil with hoe/cutlass, pull out tubers carefully. Handle gently to avoid bruising.",
            "rice": "Cut with sickle 10–15cm above ground. Bundle and thresh on clean surface. Winnow to remove chaff.",
            "sorghum": "Cut heads with sickle or knife. Dry thoroughly before threshing.",
            "millet": "Cut heads with sickle. Dry and thresh by beating on clean tarpaulin.",
            "yam": "Dig carefully around tuber with hoe. Lift gently — do not cut or bruise skin.",
            "beans": "Pull entire plant or pick dry pods. Dry in sun for 3–5 days before threshing.",
            "groundnut": "Uproot entire plant with fork/hoe. Shake off soil and dry plants in windrows for 3–4 days.",
            "tomato": "Twist gently or cut with scissors. Harvest into clean containers.",
            "pepper": "Cut with scissors or pruning shears. Handle carefully to avoid bruising.",
            "onion": "Pull bulbs from ground, trim roots and tops after curing.",
            "cabbage": "Cut head with knife, leaving wrapper leaves intact.",
            "mango": "Use picking pole with cloth bag attachment. Handle gently — do not drop.",
            "banana": "Cut entire bunch with sharp knife/cutlass. Carry on padded shoulder or cart.",
            "pineapple": "Cut fruit stalk with knife, leaving crown attached.",
            "cocoa": "Cut pod with knife/hook. Do not damage tree bark or flower cushions.",
            "coffee": "Pick cherries selectively by hand. Only pick ripe (red) cherries.",
        }
        return methods.get(crop, "Harvest using appropriate hand tools. Avoid damage to produce.")

    def _get_harvest_tools(self, crop: str) -> List[str]:
        """Return list of tools needed for harvest."""
        tools: Dict[str, List[str]] = {
            "maize": ["Cutlass or machete", "Basket or sack", "Hand sheller (optional)", "Clean drying surface/tarpaulin"],
            "cassava": ["Hoe or digging fork", "Knife for trimming", "Basket for transport", "Clean water for washing"],
            "rice": ["Sickle", "Threshing floor or tarpaulin", "Winnowing basket", "Bags for storage"],
            "sorghum": ["Sickle", "Threshing stick", "Tarpaulin", "Winnowing basket"],
            "millet": ["Sickle", "Threshing stick", "Tarpaulin", "Winnowing basket"],
            "yam": ["Hoe or digging fork", "Knife", "Baskets with padding", "Transport cart (if available)"],
            "beans": ["Sickle (optional)", "Tarpaulin for drying/threshing", "Winnowing basket", "Storage bags"],
            "groundnut": ["Garden fork or hoe", "Tarpaulin for drying", "Stripping tools or hand-shelling", "Bags"],
            "tomato": ["Scissors or pruning shears", "Clean plastic crates (NOT sacks — causes bruising)", "Clean water"],
            "pepper": ["Scissors", "Clean baskets or crates", "Gloves (for hot varieties)"],
            "onion": ["Garden fork", "Knife for trimming", "Drying racks or mesh", "Net bags for storage"],
            "cabbage": ["Sharp knife", "Plastic crates for transport", "Clean water for washing"],
            "mango": ["Picking pole with bag", "Ladder (for tall trees)", "Padded baskets or crates", "Clean water"],
            "banana": ["Sharp knife or cutlass", "Padded carrying frame", "Clean water for washing hands"],
            "pineapple": ["Sharp knife", "Gloves (leaves are spiny)", "Crates for transport"],
            "cocoa": ["Harvesting knife/hook", "Opened cocoa pod for collection", "Basket for wet beans"],
            "coffee": ["Harvesting basket", "Cherry pulper (for wet processing)", "Drying tables or raised beds"],
        }
        return tools.get(crop, ["Sharp knife or cutlass", "Clean baskets or sacks", "Tarpaulin for drying"])

    def _get_post_harvest_steps(self, crop: str) -> List[str]:
        """Return post-harvest handling steps."""
        steps: Dict[str, List[str]] = {
            "maize": [
                "Sort cobs — remove damaged, mouldy, or pest-infested cobs immediately.",
                "Dry cobs in sun on raised platforms or clean tarpaulin for 5–7 days.",
                "Turn regularly for even drying. Target moisture: 13.5%.",
                "Shell using hand sheller or by hand beating.",
                "Winnow to remove chaff, broken grains, and dust.",
                "Store in hermetic bags (PICS bags) or metal silos with tight lids.",
                "Add wood ash or neem leaves as natural insect repellent.",
            ],
            "cassava": [
                "Process within 24–48 hours of harvest (perishable).",
                "For garri: Peel, grate, ferment for 3–4 days, press, sieve, and fry.",
                "For fufu: Peel, soak, ferment, and pound.",
                "For flour: Peel, chip, dry thoroughly, and mill.",
                "Store fresh tubers in cool, shaded, well-ventilated area. Use within 1 week.",
            ],
            "rice": [
                "Thresh bundles on clean tarpaulin using sticks or by hand.",
                "Winnow to remove straw, chaff, and empty grains.",
                "Dry paddy in sun on clean surface for 3–5 days.",
                "Monitor moisture: should crack when bitten (not bend).",
                "Store paddy at 12–14% moisture in clean sacks.",
                "Mill as needed to maintain freshness and reduce storage losses.",
            ],
            "sorghum": [
                "Dry heads in sun for 3–5 days on raised platform or tarpaulin.",
                "Thresh by beating with stick or trampling (carefully).",
                "Winnow to remove chaff and debris.",
                "Dry grains to 13% moisture before storage.",
                "Store in PICS bags or metal drums with tight lids.",
            ],
            "millet": [
                "Dry heads thoroughly in sun for 3–4 days.",
                "Thresh by beating or light trampling on tarpaulin.",
                "Winnow carefully — millet grains are small.",
                "Dry to 12% moisture.",
                "Store in airtight containers or PICS bags.",
            ],
            "yam": [
                "Handle with extreme care — yams bruise and cut easily.",
                "Air dry in shade for 2–3 hours to harden skin (cure).",
                "Do not wash before storage — soil protects the skin.",
                "Sort by size and quality. Separate damaged tubers for immediate consumption.",
                "Store in yam barn (raised platform with good ventilation) or pit store.",
                "Check regularly and remove any tubers showing signs of rot.",
            ],
            "beans": [
                "Dry pods in sun for 3–5 days until they crackle when handled.",
                "Thresh by beating lightly or hand-shelling.",
                "Winnow to remove chaff and broken seeds.",
                "Dry to 14% moisture (hard to bite).",
                "Store in PICS bags or add wood ash to repel bean bruchids.",
                "Inspect monthly for insect damage.",
            ],
            "groundnut": [
                "Dry plants in windrows for 3–5 days (pods facing up).",
                "Strip pods from plants by hand.",
                "Dry pods in sun for 4–7 days until shells are crisp.",
                "Test: kernel should separate easily from testa (skin).",
                "Store pods (in-shell) at 8% moisture for longer shelf life.",
                "Shelled nuts: store at 6–7% moisture in airtight containers.",
            ],
            "tomato": [
                "Sort by size, colour, and quality immediately after harvest.",
                "Wash gently in clean water if necessary.",
                "Air dry on clean surface or rack before packing.",
                "Pack in single layers in crates — NEVER stack or use sacks.",
                "Store in cool, shaded area. For longer storage, use evaporative cooling (charcoal cooler).",
                "Process surplus into paste, sauce, or dried tomatoes.",
            ],
            "pepper": [
                "Sort by colour, size, and quality.",
                "Remove damaged or diseased fruits immediately.",
                "Dry in shade or sun depending on intended use (fresh vs. dried).",
                "For dried pepper: sun-dry on clean surface for 5–7 days until brittle.",
                "Store dried pepper in airtight containers away from moisture.",
                "Fresh pepper: store in cool ventilated crates; process surplus.",
            ],
            "onion": [
                "Cure bulbs in sun for 5–7 days with tops intact (if possible).",
                "Braid tops together or trim to 2–3cm after curing.",
                "Remove loose outer scales and dirt.",
                "Sort by size — premium grade for market, smaller for home use.",
                "Store in mesh bags in cool, dry, well-ventilated area.",
                "Check regularly and remove any bulbs showing rot.",
            ],
            "cabbage": [
                "Trim outer wrapper leaves but leave 2–3 for protection.",
                "Sort by size and firmness.",
                "Pack in crates — do not compress heads.",
                "Store in cool, shaded place. Can store 2–4 weeks at 10–15°C.",
                "Market promptly — cabbage does not store long in warm conditions.",
            ],
            "mango": [
                "Handle extremely gently — mangoes bruise easily.",
                "Wash in clean water with mild disinfectant (bleach solution 1%).",
                "Air dry on padded surface.",
                "Hot water treatment (55°C for 5 min) to control fruit fly and anthracnose.",
                "Grade by size, shape, and colour.",
                "Pack in single-layer cartons with tissue paper.",
                "Store at 12–13°C for mature-green fruit; 10°C for ripe fruit.",
            ],
            "banana": [
                "Handle carefully — no dropping or throwing.",
                "Wash hands and tools before handling.",
                "De-hand (separate hands from bunch) for retail.",
                "Wash in clean chlorinated water.",
                "Pack in ventilated cartons with paper lining.",
                "Ripen at 15–18°C for retail; store green at 13–14°C.",
            ],
            "pineapple": [
                "Trim crown (remove top leaves) unless selling with crown.",
                "Remove any soil and debris.",
                "Do not wash — dry brush clean instead.",
                "Grade by size, colour, and shape.",
                "Pack in crates or cartons with padding.",
                "Store at 10–12°C for export quality; 7–10°C for longer storage.",
            ],
            "cocoa": [
                "Split pods with wooden club or machete within 24 hours of harvest.",
                "Extract beans and surrounding pulp.",
                "Discard diseased, germinated, or flat beans.",
                "Ferment beans in wooden boxes or banana leaves for 5–7 days.",
                "Turn beans every 48 hours during fermentation.",
                "Dry fermented beans in sun on raised bamboo racks for 7–10 days.",
                "Turn regularly. Target moisture: 7–8%.",
                "Bag in jute sacks for storage and sale.",
            ],
            "coffee": [
                "Pulp cherries within 24 hours of harvest (wet processing).",
                "Ferment depulped beans for 12–48 hours to remove mucilage.",
                "Wash thoroughly in clean running water.",
                "Dry on raised African drying beds for 10–20 days.",
                "Turn hourly during peak sun. Cover at night and during rain.",
                "Target moisture: 11–12%.",
                "Hull, grade, and bag in clean sacks.",
            ],
        }
        return steps.get(crop, [
            "Sort and grade produce immediately after harvest.",
            "Remove damaged, diseased, or immature items.",
            "Dry to recommended moisture content before storage.",
            "Store in clean, dry, pest-free containers.",
        ])

    def _get_storage_methods(
        self, crop: str, crop_data: Dict[str, Any]
    ) -> List[str]:
        """Return storage methods for a crop."""
        moisture = crop_data.get("storage_moisture_percent", 0)
        methods: Dict[str, List[str]] = {
            "maize": [
                f"Dry to {moisture}% moisture before storage.",
                "Hermetic storage: PICS bags (triple bagging) — effective for 1+ years.",
                "Metal silo with tight-fitting lid — store 100–1000kg.",
                "Add wood ash or dried neem leaves at 1% by weight to repel insects.",
                "Store in a cool, dry, well-ventilated room raised off the ground.",
                "Check monthly for weevil damage (holes in grains).",
            ],
            "cassava": [
                "Fresh tubers: Store in cool, shaded, ventilated area. Use within 1 week.",
                "Processed (garri/fufu/flour): Store in airtight containers in dry place.",
                "Garri keeps 6–12 months when properly dried and stored.",
                "Chips: Dry thoroughly and store in sacks. Reconstitute by soaking before use.",
            ],
            "rice": [
                f"Store paddy at {moisture}% moisture.",
                "PICS bags — store for 1+ years without insect damage.",
                "Raised platforms or pallets (keep bags off ground and away from walls).",
                "Store in clean, dry, rodent-proof room.",
            ],
            "groundnut": [
                "Store in-shell at 8% moisture for longest shelf life.",
                "Shelled nuts: Store at 6–7% moisture in airtight containers.",
                "Add wood ash to repel groundnut bruchids.",
                "PICS bags are highly effective for groundnut storage.",
                "Check regularly for aflatoxin (discard mouldy nuts).",
            ],
            "tomato": [
                "Fresh: Store in evaporative cooling system (charcoal cooler) for 1–2 weeks.",
                "Do not refrigerate ripe tomatoes — it damages flavour.",
                "Process surplus into paste, sauce, or dried tomatoes.",
                "Dried tomatoes: Sun-dry halves for 3–5 days. Store in oil or airtight jars.",
            ],
            "onion": [
                "Store in mesh bags or braided strings in cool, dry, well-ventilated area.",
                "Good ventilation is critical — onions rot in humid conditions.",
                "Red onions store 2–3 months; yellow varieties up to 6 months.",
                "Check regularly and remove any bulbs showing soft spots.",
            ],
            "yam": [
                "Yam barn: Raised wooden platform with slatted floor and thatched roof.",
                "Pit store: Line pit with dry grass, place yams, cover with soil.",
                "Room storage: Spread on floor in cool, dark, ventilated room.",
                "Tuber pieces: Store in dry sawdust or sand.",
                "Check weekly — remove any tubers showing rot immediately.",
                "Do not store near fruits (ethylene gas causes sprouting).",
            ],
        }
        return methods.get(crop, [
            f"Dry to recommended moisture ({moisture}%) before storage.",
            "Store in clean, dry, pest-proof containers.",
            "Use PICS bags or airtight containers for grain/seed crops.",
            "Keep storage area off the ground and away from walls.",
            "Inspect regularly for pests and mould.",
        ])

    def _format_yield_per_acre(self, data: Dict[str, Any]) -> str:
        """Format expected yield per acre."""
        min_tons = data["yield_tons_per_ha"][0] * 0.4047
        max_tons = data["yield_tons_per_ha"][1] * 0.4047
        return f"{min_tons:.1f}–{max_tons:.1f} tonnes per acre (with good management)"

    def _get_value_addition(self, crop: str) -> List[str]:
        """Return value addition opportunities for a crop."""
        opportunities: Dict[str, List[str]] = {
            "cassava": [
                "Garri production: Ferment, press, sieve, and fry. 3x value increase.",
                "Fufu flour: Process into instant fufu flour for urban markets.",
                "Cassava chips: Dry and sell to animal feed processors.",
                "High-quality cassava flour (HQCF): Substitute for wheat flour in baking.",
                "Starch extraction: Supply to textile and pharmaceutical industries.",
            ],
            "maize": [
                "Maize flour: Mill into maize meal for local markets.",
                "Animal feed: Sell to poultry and pig farmers.",
                "Popcorn: Process for urban snack markets.",
            ],
            "tomato": [
                "Tomato paste/sauce: Cook down and package in sachets.",
                "Dried tomatoes: Sun-dry and sell to restaurants and exporters.",
                "Fresh tomato bundles: Grade and bundle for market presentation.",
            ],
            "mango": [
                "Dried mango slices: Solar-dry and package for export (high value).",
                "Mango juice: Extract and bottle for local sale.",
                "Mango jam: Process with sugar for extended shelf life.",
                "Fresh export: Grade and pack for European/Middle Eastern markets.",
            ],
            "coffee": [
                "Wet processing: Produces higher-quality Arabica for specialty market.",
                "Roasting: Small-scale roasting for local café market.",
                "Direct trade: Sell to specialty roasters at premium prices.",
            ],
            "cocoa": [
                "Proper fermentation: Essential for flavour — commands premium price.",
                "Rural processing: Convert to cocoa butter or powder for local market.",
                "Direct to chocolate makers: Bypass middlemen for higher prices.",
            ],
            "groundnut": [
                "Groundnut oil: Small-scale pressing for cooking oil.",
                "Roasted nuts: Package for snack market.",
                "Groundnut paste (peanut butter): Popular urban product.",
            ],
            "sesame": [
                "Hulled sesame: Process for bakery and confectionery markets.",
                "Sesame oil: Cold-press for premium cooking oil.",
                "Export: Sesame has strong export demand (Middle East, Asia, Europe).",
            ],
        }
        return opportunities.get(crop, [
            "Grade and sort produce by size and quality for premium pricing.",
            "Package in labelled containers to attract better prices.",
            "Process surplus into dried, pickled, or preserved forms.",
            "Form farmer groups to bulk produce for better bargaining power.",
        ])

    # ------------------------------------------------------------------
    # Crop Calendar
    # ------------------------------------------------------------------

    def get_crop_calendar(self, region: str) -> Dict[str, Any]:
        """Generate a seasonal crop calendar for a region.

        Args:
            region: African region identifier.

        Returns:
            Dictionary with month-by-month planting and harvesting guide.
        """
        region_key = region.lower().strip().replace(" ", "_")

        calendars: Dict[str, Dict[str, Any]] = {
            "west_africa": {
                "description": "West Africa has a bimodal rainfall pattern in the south and unimodal in the north.",
                "calendar": {
                    "January": {"plant": ["irrigated_vegetables", "maize_north"], "harvest": ["cotton", "groundnut", "sorghum"]},
                    "February": {"plant": ["early_maize_south", "irrigated_tomato"], "harvest": ["cotton", "groundnut"]},
                    "March": {"plant": ["maize", "cassava", "yam", "vegetables"], "harvest": ["late_sorghum", "cowpea"]},
                    "April": {"plant": ["maize", "rice", "cassava", "groundnut"], "harvest": []},
                    "May": {"plant": ["maize", "rice", "sorghum", "millet", "cotton"], "harvest": []},
                    "June": {"plant": ["sorghum", "millet", "cowpea", "sesame"], "harvest": ["early_maize"]},
                    "July": {"plant": ["late_millet", "cowpea"], "harvest": ["early_maize", "beans"]},
                    "August": {"plant": ["second_season_maize_south", "vegetables"], "harvest": ["maize", "groundnut"]},
                    "September": {"plant": ["second_season_vegetables"], "harvest": ["maize", "rice", "cowpea"]},
                    "October": {"plant": ["early_yam", "cassava"], "harvest": ["rice", "sorghum", "millet", "cotton"]},
                    "November": {"plant": ["cassava", "vegetables_harmattan"], "harvest": ["rice", "yam", "sorghum", "millet"]},
                    "December": {"plant": ["irrigated_vegetables", "onion"], "harvest": ["yam", "cassava", "late_rice"]},
                },
                "priority_crops": ["maize", "cassava", "rice", "yam", "groundnut", "sorghum"],
            },
            "east_africa": {
                "description": "East Africa has bimodal rainfall with long rains (March–May) and short rains (October–December).",
                "calendar": {
                    "January": {"plant": [], "harvest": ["maize_short_rains", "beans_short_rains"]},
                    "February": {"plant": ["early_irrigated_tomato", "onion"], "harvest": ["maize_short_rains", "sorghum"]},
                    "March": {"plant": ["maize_long_rains", "beans", "irish_potato", "vegetables"], "harvest": []},
                    "April": {"plant": ["maize", "beans", "sorghum", "millet", "cassava"], "harvest": []},
                    "May": {"plant": ["sorghum", "millet", "cowpea", "groundnut"], "harvest": []},
                    "June": {"plant": [], "harvest": ["early_maize", "peas"]},
                    "July": {"plant": ["wheat_barley_highlands", "second_season_potato"], "harvest": ["maize_long_rains", "beans"]},
                    "August": {"plant": ["wheat", "barley"], "harvest": ["maize", "irish_potato"]},
                    "September": {"plant": ["short_rains_maize", "beans"], "harvest": ["wheat", "barley"]},
                    "October": {"plant": ["maize_short_rains", "beans", "sorghum", "greengrams"], "harvest": []},
                    "November": {"plant": ["maize", "cowpea", "vegetables"], "harvest": []},
                    "December": {"plant": ["vegetables", "onion"], "harvest": ["early_short_rains_maize"]},
                },
                "priority_crops": ["maize", "beans", "coffee", "tea", "irish_potato", "sorghum"],
            },
            "southern_africa": {
                "description": "Southern Africa has a single rainy season from November to April.",
                "calendar": {
                    "January": {"plant": ["maize", "sorghum", "groundnut", "cowpea"], "harvest": []},
                    "February": {"plant": ["late_maize", "sweet_potato"], "harvest": []},
                    "March": {"plant": ["vegetables", "tobacco"], "harvest": ["early_maize"]},
                    "April": {"plant": ["winter_vegetables"], "harvest": ["maize", "groundnut", "cowpea"]},
                    "May": {"plant": ["wheat_irrigation", "winter_vegetables"], "harvest": ["maize", "sorghum", "tobacco"]},
                    "June": {"plant": ["wheat", "barley", "winter_vegetables"], "harvest": ["cotton", "sweet_potato"]},
                    "July": {"plant": ["wheat", "barley"], "harvest": ["groundnut", "cowpea"]},
                    "August": {"plant": ["early_maize_under_irrigation", "potato"], "harvest": ["wheat", "barley"]},
                    "September": {"plant": ["maize_irrigation", "vegetables"], "harvest": ["wheat", "winter_vegetables"]},
                    "October": {"plant": ["maize", "sorghum", "cotton", "tobacco", "groundnut"], "harvest": []},
                    "November": {"plant": ["maize", "sorghum", "millet", "cowpea", "sesame"], "harvest": []},
                    "December": {"plant": ["maize", "sweet_potato", "cassava", "vegetables"], "harvest": []},
                },
                "priority_crops": ["maize", "tobacco", "cotton", "groundnut", "sorghum"],
            },
            "sahel": {
                "description": "The Sahel has a short, intense rainy season from June to September.",
                "calendar": {
                    "January": {"plant": [], "harvest": ["irrigated_onion", "irrigated_tomato"]},
                    "February": {"plant": [], "harvest": ["irrigated_vegetables"]},
                    "March": {"plant": [], "harvest": []},
                    "April": {"plant": [], "harvest": []},
                    "May": {"plant": ["early_millet", "short_duration_sorghum"], "harvest": []},
                    "June": {"plant": ["millet", "sorghum", "cowpea", "groundnut", "sesame"], "harvest": []},
                    "July": {"plant": ["cowpea", "okra", "roselle"], "harvest": []},
                    "August": {"plant": [], "harvest": ["early_millet"]},
                    "September": {"plant": ["off_season_vegetables_irrigated"], "harvest": ["millet", "sorghum", "cowpea"]},
                    "October": {"plant": [], "harvest": ["millet", "sorghum", "groundnut", "sesame"]},
                    "November": {"plant": ["irrigated_onion", "irrigated_wheat"], "harvest": ["groundnut", "cowpea"]},
                    "December": {"plant": ["irrigated_vegetables", "onion"], "harvest": ["late_sorghum"]},
                },
                "priority_crops": ["millet", "sorghum", "cowpea", "groundnut", "sesame"],
            },
            "central_africa": {
                "description": "Central Africa has year-round rainfall with drier periods.",
                "calendar": {
                    "January": {"plant": ["cassava", "plantain", "maize"], "harvest": ["cocoa_main", "coffee"]},
                    "February": {"plant": ["cassava", "groundnut"], "harvest": ["cocoa", "coffee"]},
                    "March": {"plant": ["maize", "cassava", "rice", "groundnut"], "harvest": ["cocoa"]},
                    "April": {"plant": ["maize", "rice", "vegetables"], "harvest": []},
                    "May": {"plant": ["maize", "rice", "cowpea"], "harvest": []},
                    "June": {"plant": ["maize", "cowpea"], "harvest": ["early_maize"]},
                    "July": {"plant": ["second_season_maize", "vegetables"], "harvest": ["maize"]},
                    "August": {"plant": ["rice", "vegetables"], "harvest": ["maize", "groundnut"]},
                    "September": {"plant": ["maize", "cassava"], "harvest": ["rice", "groundnut"]},
                    "October": {"plant": ["cassava", "maize"], "harvest": ["rice", "maize"]},
                    "November": {"plant": ["cassava", "plantain_suckers", "cocoa_seedlings"], "harvest": ["cocoa_mid_crop", "coffee"]},
                    "December": {"plant": ["cassava", "plantain"], "harvest": ["cocoa_mid_crop"]},
                },
                "priority_crops": ["cassava", "plantain", "cocoa", "coffee", "maize", "rice"],
            },
            "north_africa": {
                "description": "North Africa has winter rains and hot, dry summers. Crops grown under irrigation.",
                "calendar": {
                    "January": {"plant": [], "harvest": ["citrus", "olives", "wheat"]},
                    "February": {"plant": [], "harvest": ["citrus", "wheat"]},
                    "March": {"plant": ["maize_spring", "tomato_spring", "melon"], "harvest": ["citrus", "wheat"]},
                    "April": {"plant": ["maize", "cotton", "groundnut", "vegetables"], "harvest": ["late_citrus"]},
                    "May": {"plant": ["cotton", "rice", "sorghum"], "harvest": []},
                    "June": {"plant": ["rice", "sorghum", "sesame"], "harvest": ["wheat", "barley"]},
                    "July": {"plant": ["second_crop_maize", "vegetables"], "harvest": ["wheat", "barley"]},
                    "August": {"plant": ["winter_vegetables", "onion"], "harvest": ["maize_spring", "tomato"]},
                    "September": {"plant": ["wheat", "barley", "fava_bean", "onion"], "harvest": ["cotton", "rice"]},
                    "October": {"plant": ["wheat", "barley", "fava_bean", "garlic"], "harvest": ["maize", "sorghum"]},
                    "November": {"plant": ["wheat", "barley", "chickpea"], "harvest": ["groundnut", "sesame"]},
                    "December": {"plant": [], "harvest": ["citrus", "dates"]},
                },
                "priority_crops": ["wheat", "barley", "citrus", "dates", "olives", "tomato"],
            },
        }

        calendar = calendars.get(region_key, {
            "description": "Regional calendar not available. Consult local agricultural extension.",
            "calendar": {},
            "priority_crops": [],
        })

        self._logger.info("Generated crop calendar for region: %s", region_key)
        return {
            "region": region_key,
            **calendar,
            "disclaimer": WEATHER_DISCLAIMER,
        }



# ---------------------------------------------------------------------------
# Class: LivestockAdvisor
# ---------------------------------------------------------------------------

class LivestockAdvisor:
    """Comprehensive livestock advisory for African smallholder farmers.

    Provides guidance on animal husbandry, disease management, feeding,
    breeding, and vaccination schedules. Designed for the common livestock
    species kept by African smallholders: cattle, goats, sheep, chickens,
    pigs, and rabbits.

    Attributes:
        LIVESTOCK: Class-level reference to the livestock database.
    """

    LIVESTOCK: Dict[str, Dict[str, Any]] = LIVESTOCK

    def __init__(self) -> None:
        """Initialize the LivestockAdvisor with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.LivestockAdvisor"
        )
        self._logger.info("LivestockAdvisor initialized")

    # ------------------------------------------------------------------
    # Animal Care Guide
    # ------------------------------------------------------------------

    def get_care_guide(self, animal: str) -> Dict[str, Any]:
        """Generate a comprehensive care guide for a livestock species.

        Args:
            animal: Animal species (cattle, goats, sheep, chickens, pigs, rabbits).

        Returns:
            Dictionary with detailed care instructions.

        Raises:
            ValueError: If the animal is not in the database.
        """
        animal_key = animal.lower().strip()

        if animal_key not in self.LIVESTOCK:
            available = ", ".join(sorted(self.LIVESTOCK.keys()))
            raise ValueError(
                f"Unknown animal '{animal}'. Available: {available}"
            )

        data = self.LIVESTOCK[animal_key]

        care_guide: Dict[str, Any] = {
            "animal": data["name"],
            "breeds": {
                "local": data.get("local_breeds", data.get("local_brereds", [])),
                "exotic": data.get("exotic_breeds", []),
                "recommendation": (
                    "For smallholders, crossbreed local females with exotic males "
                    "to combine hardiness with improved productivity. "
                    "Local breeds are more disease-resistant and better adapted to local conditions."
                ),
            },
            "housing": data.get("housing", "Provide adequate shelter"),
            "housing_construction": self._get_housing_construction(animal_key),
            "feeding": {
                "system": data.get("feeding_system", "Mixed feeding"),
                "daily_water": f"{data['water_litres_per_day'][0]}-{data['water_litres_per_day'][1]} litres per day",
                "local_feeds": data.get("local_feeds", []),
                "supplements": data.get("supplements", []),
                "feeding_schedule": self._get_feeding_schedule(animal_key),
            },
            "health_management": {
                "common_diseases": data.get("common_diseases", []),
                "vaccination_schedule": data.get("vaccination_schedule", {}),
                "deworming": self._get_deworming_schedule(animal_key),
                "signs_of_health": self._get_health_signs(animal_key),
                "signs_of_illness": self._get_illness_signs(animal_key),
            },
            "breeding": {
                "gestation_period": f"{data.get('gestation_days', data.get('incubation_days', 'N/A'))} days"
                if data.get('gestation_days') or data.get('incubation_days') else "See species-specific guide",
                "age_at_first_breeding": (
                    data.get("age_at_first_calving_months")
                    or data.get("age_at_first_kidding_months")
                    or data.get("age_at_first_lambing_months")
                    or data.get("age_at_first_farrowing_months")
                    or data.get("age_at_first_kindling_months")
                    or data.get("age_at_first_lay_weeks")
                    or "See details"
                ),
                "breeding_interval_months": (
                    data.get("calving_interval_months")
                    or data.get("kidding_interval_months")
                    or data.get("lambing_interval_months")
                    or data.get("farrowing_interval_months")
                    or data.get("kindling_interval_months")
                    or "See details"
                ),
                "breeding_tips": self._get_breeding_tips(animal_key),
            },
            "daily_care_routine": self._get_daily_routine(animal_key),
            "economic_tips": self._get_economic_tips(animal_key),
            "optimal_temperature_c": f"{data['optimal_temp_c'][0]}-{data['optimal_temp_c'][1]}",
            "disclaimer": MEDICAL_DISCLAIMER,
        }

        self._logger.info("Generated care guide for %s", data["name"])
        return care_guide

    def _get_housing_construction(self, animal: str) -> List[str]:
        """Get detailed housing construction guidance."""
        guides: Dict[str, List[str]] = {
            "cattle": [
                "Site: Choose well-drained, elevated ground away from water sources.",
                "Orientation: East-west alignment for maximum shade and ventilation.",
                "Floor: Concrete or compacted earth with 1:20 slope for drainage.",
                "Roof: Corrugated iron or thatch, minimum 3m height for air circulation.",
                "Space: 3m² per adult, 1.5m² per calf. Increase in hot climates.",
                "Feeding: Build raised feed troughs (60cm high) to prevent contamination.",
                "Water: Provide automatic waterers or large troughs cleaned daily.",
                "Milking area: Separate clean area with concrete floor and drainage.",
                "Waste: Design for easy collection of manure for composting.",
            ],
            "goats": [
                "Site: Elevated, well-drained area. Goats hate wet conditions.",
                "Floor: Raised slatted floor (wooden or bamboo) 1m above ground keeps animals dry.",
                "Walls: 1.5m high walls or strong fencing. Goats are escape artists.",
                "Roof: Thatch or corrugated iron with good overhang for rain protection.",
                "Space: 1.5m² per adult goat, 0.5m² per kid.",
                "Feeding: Hanging feed racks prevent waste and contamination.",
                "Water: Clean water in suspended buckets or nipple drinkers.",
                "Kidding pen: Separate clean pen for kidding with straw bedding.",
            ],
            "sheep": [
                "Site: Well-drained ground with good windbreaks.",
                "Floor: Slatted or compacted earth with bedding (straw, wood shavings).",
                "Walls: Low walls (1m) or sturdy fencing. Sheep need good ventilation.",
                "Roof: Thatched or corrugated iron. Sheep tolerate cold better than heat.",
                "Space: 1.5m² per adult sheep, 0.5m² per lamb.",
                "Feeding: Troughs raised 30cm off ground.",
                "Lambing pen: Clean, dry, draft-free pen for lambing.",
            ],
            "chickens": [
                "Site: Raised ground, well-drained, away from predators.",
                "House: Raised house 1m off ground (reduces parasites, predators).",
                "Floor: Wire mesh or slatted floor with droppings collection tray underneath.",
                "Walls: Chicken wire or open sides with 1m high solid lower wall.",
                "Roof: Thatch or corrugated iron. Insulate roof in hot areas.",
                "Space: 3–5 birds/m² for layers, 8–10/m² for broilers.",
                "Nesting: 1 nest box per 4–5 hens, 30cm x 30cm x 30cm.",
                "Perches: Wooden perches 5cm diameter, 30cm per bird, 50cm high.",
                "Ventilation: Cross-ventilation essential — prevents respiratory diseases.",
                "Biosecurity: Footbath at entrance, fence perimeter, restricted access.",
            ],
            "pigs": [
                "Site: Downwind from human dwellings (odour). Well-drained slope.",
                "Floor: Concrete preferred (1:20 slope for drainage). Partially slatted for sows.",
                "Walls: 1.2m high solid or semi-solid walls. Pigs need protection from wind.",
                "Roof: Corrugated iron or thatch. Shade essential in hot climates.",
                "Space: 2–3m² per adult pig, 4–5m² per sow with piglets.",
                "Feeding: Concrete troughs (60cm long per pig) or automatic feeders.",
                "Water: Nipple drinkers or troughs — pigs need constant water access.",
                "Wallow: Mud wallow or shower system for cooling in hot weather.",
                "Farrowing crate: Protective rails to prevent sow crushing piglets.",
                "Waste: Pit or lagoon system for manure collection.",
            ],
            "rabbits": [
                "Site: Quiet area, shaded, well-ventilated but not drafty.",
                "Hutch: Wire mesh front, solid back and sides. 0.5m² per adult rabbit.",
                "Floor: Wire mesh (1cm x 2.5cm) for droppings to fall through.",
                "Nest box: 30cm x 25cm x 25cm with nesting material (straw, hay).",
                "Feeding: Hanging hay rack, pellet feeder, water bottle/nipple.",
                "Cleaning: Clean hutches daily. Remove soiled bedding.",
                "Breeding units: Separate bucks and does except during mating.",
            ],
        }
        return guides.get(animal, ["Provide clean, dry, well-ventilated shelter appropriate for the species."])

    def _get_feeding_schedule(self, animal: str) -> Dict[str, Any]:
        """Get species-specific feeding schedules."""
        schedules: Dict[str, Dict[str, Any]] = {
            "cattle": {
                "grazing": "Graze 6–8 hours daily on quality pasture. Rotate paddocks every 2–3 weeks.",
                "morning": "6:00 AM — Fresh pasture or cut fodder + mineral block",
                "midday": "12:00 PM — Water + shade rest",
                "evening": "4:00 PM — Cut fodder or crop residues + supplement",
                "milking_cows": "Provide dairy meal 1–2kg per litre of milk produced",
                "dry_season": "Feed hay, silage, or crop residues. Supplement with urea-molasses blocks.",
                "water": "Provide clean water 3 times daily. Lactating cows need 50–80 litres/day.",
            },
            "goats": [
                "Morning (7:00 AM): Fresh cut fodder or browsing (2–3kg per adult)",
                "Midday: Fresh water + mineral lick",
                "Evening (4:00 PM): Cut fodder + 200g concentrate for milking does",
                "Dry season: Feed crop residues, hay, and tree fodder (calliandra, leucaena)",
                "Kids: Allow to suckle for 2–3 months, then wean gradually",
            ],
            "sheep": [
                "Morning (7:00 AM): Graze on pasture or feed cut grass (1.5–2kg per adult)",
                "Midday: Fresh water + shade",
                "Evening (4:00 PM): Supplement with crop residues or hay",
                "Pregnant ewes: Increase feed by 20% in last 6 weeks of pregnancy",
                "Lambs: Ensure access to creep feed (high protein) from 2 weeks old",
            ],
            "chickens": [
                "Layers: Provide layer mash/pellets ad libitum (100–120g per hen per day)",
                "Broilers: Provide broiler starter (0–3 weeks), then finisher (3–8 weeks)",
                "Water: Clean, fresh water available at ALL TIMES",
                "Grit: Provide insoluble grit (small stones) for digestion",
                "Calcium: Provide oyster shells or limestone for layers (separate from feed)",
                "Kitchen scraps: Supplement with vegetable peels, leftover ugali, etc.",
                "Free range: Allow 2–3 hours daily scavenging for insects and greens",
            ],
            "pigs": [
                "Adults: 2–3kg feed per day (commercial feed or mixture)",
                "Weaners: Feed starter ration 3–4 times daily (0.5–1kg per piglet)",
                "Growers: 1.5–2kg grower ration per day",
                "Pregnant sows: 2–2.5kg maintenance ration + greens",
                "Lactating sows: 3–5kg per day + unlimited water",
                "Water: Continuous access — pigs drink 10–30 litres per day",
                "Wet feeding: Mixing feed with water improves intake and reduces waste",
            ],
            "rabbits": [
                "Adults: 100–150g pellets per day + unlimited hay/fresh greens",
                "Pregnant does: Increase to 180–200g pellets per day",
                "Lactating does: 200–250g pellets + unlimited greens",
                "Growing kits: Free access to pellets from 3 weeks of age",
                "Fresh greens: Provide daily — Napier grass, sweet potato vines, bean leaves",
                "Water: Clean water in bottles or bowls, changed daily",
                "Avoid: Never feed wilted greens, cassava leaves, or toxic plants",
            ],
        }
        return schedules.get(animal, ["Feed twice daily with quality feed appropriate for the species and production stage."])

    def _get_deworming_schedule(self, animal: str) -> str:
        """Get deworming recommendations."""
        schedules: Dict[str, str] = {
            "cattle": "Deworm every 3–4 months using broad-spectrum anthelmintic (albendazole or levamisole). "
                      "Increase frequency in wet, high-parasite areas. Rotate drug classes to prevent resistance. "
                      "Deworm all animals at start of dry season.",
            "goats": "Deworm every 3 months. Goats are highly susceptible to internal parasites. "
                     "Use FAMACHA method (check eyelid colour) to identify anaemic animals needing treatment. "
                     "Rotate pastures to break parasite life cycle.",
            "sheep": "Deworm every 3–4 months. Deworm pregnant ewes 2–3 weeks before lambing. "
                     "Use FAMACHA scoring. Rotate drug classes annually.",
            "chickens": "Deworm every 3 months with piperazine or levamisole in drinking water. "
                       "Control coccidiosis with amprolium in feed or water during first 8 weeks.",
            "pigs": "Deworm every 3–4 months with ivermectin or fenbendazole. "
                    "Deworm sows 2 weeks before farrowing to prevent transmission to piglets.",
            "rabbits": "Deworm every 3 months. Use ivermectin or fenbendazole. "
                      "Coccidiosis prevention: keep hutches clean and dry. Treat with sulfa drugs if needed.",
        }
        return schedules.get(animal, "Consult a veterinarian for deworming schedule.")

    def _get_health_signs(self, animal: str) -> List[str]:
        """Get signs of a healthy animal."""
        return [
            "Bright, alert eyes with no discharge",
            "Clean, moist nose (no excessive mucus)",
            "Smooth, shiny coat or feathers",
            "Good appetite and normal drinking",
            "Active movement and normal posture",
            "Normal, firm droppings (not diarrhoea)",
            "Normal body temperature (varies by species)",
            "Normal breathing (no coughing or wheezing)",
        ]

    def _get_illness_signs(self, animal: str) -> List[str]:
        """Get early signs of illness."""
        return [
            "⚠️ ISOLATE any animal showing these signs immediately",
            "Loss of appetite or refusal to drink",
            "Lethargy, depression, or separation from the herd/flock",
            "Diarrhoea or constipation",
            "Coughing, sneezing, or difficulty breathing",
            "Discharge from eyes, nose, or ears",
            "Lameness or difficulty walking",
            "Swollen joints, udder, or abdomen",
            "Fever (hot ears, dry nose)",
            "Dramatic drop in milk production or egg laying",
            "Abnormal coat/feather condition (rough, dull, ruffled)",
            "Bloating or grinding teeth",
        ]

    def _get_breeding_tips(self, animal: str) -> List[str]:
        """Get breeding management tips."""
        tips: Dict[str, List[str]] = {
            "cattle": [
                "Keep breeding records: date of service, bull used, expected calving date.",
                "Use AI (artificial insemination) for genetic improvement — contact local veterinary service.",
                "Observe cows for heat (standing to be mounted, restlessness, mucus discharge) twice daily.",
                "Most cows come into heat 40–60 days after calving.",
                "Calve in dry season for best calf survival and pasture availability.",
                "Ensure body condition score of 3–3.5 at calving for good fertility.",
            ],
            "goats": [
                "Does come into heat every 18–21 days during breeding season.",
                "Signs of heat: Tail wagging, mucus discharge, mounting other goats, bleating.",
                "Breeding ratio: 1 buck per 25–30 does.",
                "Separate young bucks from does at 3 months to prevent unplanned breeding.",
                "Keep kidding pens clean and dry. Assist only if kidding is prolonged (>30 min).",
                "Ensure kids receive colostrum within 2 hours of birth.",
            ],
            "sheep": [
                "Most breeds are seasonal breeders — cycle with shortening daylight.",
                "Ewes come into heat every 16–17 days during breeding season.",
                "Flushing: Increase feed 2 weeks before and during breeding for higher ovulation rate.",
                "Lambing pen: Clean, dry, draft-free with fresh bedding.",
                "Assist lambing only if ewe is straining for 30+ minutes with no progress.",
                "Ensure lambs receive colostrum within 1 hour of birth.",
            ],
            "chickens": [
                "Natural mating: 1 rooster per 10–15 hens for fertile eggs.",
                "For hatching: Select clean, well-shaped eggs less than 10 days old.",
                "Broody hens: Provide quiet, dark nest box. Mark eggs and remove any new ones daily.",
                "Incubation: 21 days. Turn eggs 3–5 times daily if using manual incubator.",
                "Temperature: 37.5–37.8°C for incubator. Humidity: 50–55% (increase to 65% last 3 days).",
                "Candle eggs at day 7 to check fertility — remove infertile eggs.",
            ],
            "pigs": [
                "Sows come into heat every 21 days (lasting 2–3 days).",
                "Signs of heat: Swollen vulva, restlessness, mounting, standing reflex.",
                "Best time to breed: 12–36 hours after onset of standing heat.",
                "Breeding ratio: 1 boar per 15–20 sows (natural service).",
                "Farrowing: Provide clean, warm (25-30C) farrowing pen with protective rails.",
                "Iron injection: Give piglets iron dextran at 1–3 days old (prevents anaemia).",
                "Castrate male piglets at 7–10 days old.",
            ],
            "rabbits": [
                "Does are induced ovulators — breeding triggers ovulation.",
                "Always take doe to buck's cage (not vice versa — does are territorial).",
                "Breeding age: 5–7 months for small breeds, 8–10 months for large breeds.",
                "Palpate doe at day 10–14 to confirm pregnancy (grape-sized embryos).",
                "Kindling box: Provide nest box with straw 3 days before expected kindling.",
                "Litter size: 4–12 kits average. Remove dead kits immediately.",
                "Check kits daily but minimize disturbance for first week.",
                "Wean at 6–8 weeks of age.",
            ],
        }
        return tips.get(animal, ["Consult local veterinary officer for species-specific breeding advice."])

    def _get_daily_routine(self, animal: str) -> List[str]:
        """Get recommended daily care routine."""
        routines: Dict[str, List[str]] = {
            "cattle": [
                "5:30 AM — Check herd, count animals",
                "6:00 AM — Release to pasture or provide fresh fodder",
                "7:00 AM — Clean water troughs and refill",
                "8:00 AM — Milking (for dairy cows)",
                "12:00 PM — Check pasture/water, provide shade",
                "3:00 PM — Provide supplement feed (dry season)",
                "4:00 PM — Second milking (dairy)",
                "5:00 PM — Return to shelter, check for injuries or illness",
                "6:00 PM — Final water check, secure shelter",
            ],
            "goats": [
                "6:00 AM — Count goats, check for overnight issues",
                "7:00 AM — Provide fresh cut fodder or release for browsing",
                "8:00 AM — Clean water containers, fresh water",
                "10:00 AM — Check kids, ensure they are nursing",
                "12:00 PM — Midday check, shade, water refresh",
                "4:00 PM — Evening feed (fodder + supplement for milkers)",
                "5:00 PM — Return to shelter, health check",
                "6:00 PM — Final water, secure housing",
            ],
            "chickens": [
                "6:00 AM — Open house, check water and feed",
                "7:00 AM — Collect eggs (morning lay)",
                "8:00 AM — Remove soiled litter, add fresh bedding",
                "10:00 AM — Health check: observe droppings, activity, feed intake",
                "12:00 PM — Collect eggs, refresh water",
                "3:00 PM — Check feed levels, collect eggs",
                "5:00 PM — Final feed check, ensure water is clean",
                "6:00 PM — Secure house, close doors (predator protection)",
                "Weekly: Deep clean house, disinfect waterers and feeders",
            ],
            "pigs": [
                "6:00 AM — Check pigs, count, observe behaviour",
                "7:00 AM — First feeding, clean water troughs",
                "8:00 AM — Remove soiled bedding, add fresh straw",
                "10:00 AM — Health check, observe for illness signs",
                "12:00 PM — Second feeding, water refresh",
                "3:00 PM — Check temperature, provide cooling if needed",
                "4:00 PM — Third feeding (for growing pigs)",
                "5:00 PM — Final check, secure housing",
            ],
            "rabbits": [
                "7:00 AM — Check all rabbits, count, observe behaviour",
                "7:30 AM — Fresh water in all bottles/bowls",
                "8:00 AM — Provide fresh greens and hay",
                "9:00 AM — Clean hutches (remove soiled bedding)",
                "10:00 AM — Check nest boxes, handle kits gently",
                "3:00 PM — Refresh water, check feed pellets",
                "4:00 PM — Evening greens and hay",
                "5:00 PM — Final health check, observe droppings",
            ],
        }
        return routines.get(animal, ["Feed and water animals twice daily. Observe for signs of illness. Keep housing clean."])

    def _get_economic_tips(self, animal: str) -> List[str]:
        """Get economic management tips."""
        return [
            "Keep detailed records: births, deaths, sales, purchases, feed costs, veterinary expenses.",
            "Cull unproductive animals: Remove chronic poor performers to reduce feed costs.",
            "Sell at optimal weight/age — overfeeding beyond market weight wastes money.",
            "Form cooperative groups for bulk purchasing of feed and veterinary supplies.",
            "Market directly to consumers or restaurants for better prices than middlemen.",
            "Process value-added products: cheese from goat milk, smoked meat, packaged eggs.",
            "Utilize manure as fertilizer or sell to crop farmers — additional income stream.",
        ]

    # ------------------------------------------------------------------
    # Disease Symptoms & Treatment
    # ------------------------------------------------------------------

    def get_disease_symptoms(
        self,
        animal: str,
        symptoms: str,
    ) -> Dict[str, Any]:
        """Identify diseases based on animal and observed symptoms.

        Args:
            animal: Animal species.
            symptoms: Description of observed symptoms.

        Returns:
            Dictionary with disease identification and treatment recommendations.
        """
        animal_key = animal.lower().strip()
        symptoms_lower = symptoms.lower()

        if animal_key not in self.LIVESTOCK:
            available = ", ".join(sorted(self.LIVESTOCK.keys()))
            raise ValueError(f"Unknown animal '{animal}'. Available: {available}")

        # Comprehensive disease database
        disease_db = self._build_disease_database()

        matched_diseases: List[Dict[str, Any]] = []

        for disease_key, disease_data in disease_db.items():
            if animal_key not in disease_data.get("affected_animals", []):
                continue

            # Score symptom matches
            score = 0
            for sym in disease_data.get("symptoms", []):
                sym_words = [w for w in sym.lower().split() if len(w) > 4]
                for word in sym_words:
                    if word in symptoms_lower:
                        score += 1

            if score >= 1:
                matched_diseases.append({
                    "disease_name": disease_data["name"],
                    "match_score": score,
                    "symptoms": disease_data["symptoms"],
                    "treatment": disease_data.get("treatment", []),
                    "prevention": disease_data.get("prevention", []),
                    "severity": disease_data.get("severity", "medium"),
                    "contagious": disease_data.get("contagious", False),
                })

        # Sort by match score
        matched_diseases.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "animal": self.LIVESTOCK[animal_key]["name"],
            "symptoms_reported": symptoms,
            "matched_diseases": matched_diseases[:5],
            "top_recommendation": matched_diseases[0] if matched_diseases else None,
            "emergency_signs": self._get_emergency_signs(animal_key),
            "general_first_aid": [
                "1. ISOLATE the sick animal immediately to prevent disease spread.",
                "2. Provide clean water, shade, and comfortable bedding.",
                "3. Do NOT self-medicate with human drugs — many are toxic to animals.",
                "4. Contact your local veterinary officer or community animal health worker.",
                "5. Keep detailed records of symptoms, when they started, and any treatments given.",
            ],
            "disclaimer": MEDICAL_DISCLAIMER,
        }

    def _build_disease_database(self) -> Dict[str, Dict[str, Any]]:
        """Build comprehensive disease database for all livestock."""
        return {
            "east_coast_fever": {
                "name": "East Coast Fever (Theileriosis)",
                "affected_animals": ["cattle"],
                "symptoms": ["High fever (40–42°C)", "Swollen lymph nodes", "Laboured breathing", "Loss of appetite", "Weakness and dullness", "Diarrhoea (sometimes bloody)", "Discharge from eyes and nose"],
                "treatment": ["Treatment must begin EARLY — consult vet immediately", "Buparvaquone injection (vet prescription)", "Supportive care: fluids, shade, good nutrition"],
                "prevention": ["Tick control: dip or spray weekly during rainy season", "Use acaricides regularly", "Zero-grazing reduces tick exposure", "East Coast Fever vaccine available in some areas"],
                "severity": "critical", "contagious": False,
            },
            "foot_and_mouth": {
                "name": "Foot-and-Mouth Disease",
                "affected_animals": ["cattle", "goats", "sheep", "pigs"],
                "symptoms": ["High fever", "Drooling and frothing at mouth", "Blisters/ulcers on tongue, gums, lips", "Lameness due to foot blisters", "Sudden drop in milk production", "Loss of appetite"],
                "treatment": ["No specific treatment — supportive care only", "Antiseptic foot baths for foot lesions", "Soft, palatable feed (mash, greens)", "Report to veterinary authorities immediately — NOTIFIABLE DISEASE"],
                "prevention": ["Vaccinate every 6 months in endemic areas", "Quarantine new animals for 30 days", "Control animal movement", "Report outbreaks immediately"],
                "severity": "high", "contagious": True,
            },
            "brucellosis": {
                "name": "Brucellosis",
                "affected_animals": ["cattle", "goats", "sheep"],
                "symptoms": ["Abortion in late pregnancy", "Retained afterbirth", "Infertility", "Weak calves/lambs/kids", "Swollen joints", "Reduced milk production"],
                "treatment": ["No effective treatment — culling recommended", "Antibiotics may reduce symptoms but do not cure", "Consult veterinarian for herd management strategy"],
                "prevention": ["Vaccinate replacement heifers", "Cull infected animals", "Use AI instead of natural service", "Wear gloves when assisting births — ZOONOTIC (spreads to humans)", "Test herd annually"],
                "severity": "high", "contagious": True,
            },
            "anaplasmosis": {
                "name": "Anaplasmosis",
                "affected_animals": ["cattle"],
                "symptoms": ["High fever", "Pale or yellow mucous membranes", "Weakness and depression", "Rapid breathing", "Dark brown urine", "Constipation followed by diarrhoea", "Weight loss"],
                "treatment": ["Oxytetracycline injection (vet prescription)", "Blood transfusion in severe cases (vet only)", "Iron supplements for recovery", "Provide good nutrition and rest"],
                "prevention": ["Tick control — regular dipping/spraying", "Blood transfusion from recovered animals (in some regions)", "Avoid stressing infected animals"],
                "severity": "high", "contagious": False,
            },
            "trypanosomiasis": {
                "name": "Trypanosomiasis (Nagana)",
                "affected_animals": ["cattle", "goats", "sheep", "pigs"],
                "symptoms": ["Intermittent fever", "Progressive weight loss despite eating", "Swollen lymph nodes", "Pale mucous membranes (anaemia)", "Oedema under jaw (bottle jaw)", "Lethargy and weakness"],
                "treatment": ["Diminazene aceturate (Berenil) or Isometamidium chloride (Samorin) — vet prescription", "Supportive care: iron supplements, good nutrition", "Rest in shade"],
                "prevention": ["Tsetse fly control: traps, targets, clearing bush", "Use trypanotolerant breeds (N'Dama, West African Shorthorn)", "Prophylactic treatment in high-risk areas", "Avoid grazing in tsetse-infested areas during peak fly activity"],
                "severity": "critical", "contagious": False,
            },
            "peste_des_petits_ruminants": {
                "name": "Peste des Petits Ruminants (PPR / Goat Plague)",
                "affected_animals": ["goats", "sheep"],
                "symptoms": ["High fever (40–41°C)", "Discharge from eyes and nose", "Mouth ulcers and sores", "Severe diarrhoea", "Coughing and difficulty breathing", "Sudden death in acute cases"],
                "treatment": ["No specific antiviral treatment", "Antibiotics for secondary bacterial infections", "Supportive care: fluids, electrolytes, soft feed", "Report immediately — NOTIFIABLE DISEASE"],
                "prevention": ["Vaccinate ALL animals annually", "Quarantine new animals for 30 days", "Report outbreaks to veterinary authorities"],
                "severity": "critical", "contagious": True,
            },
            "newcastle_disease": {
                "name": "Newcastle Disease",
                "affected_animals": ["chickens"],
                "symptoms": ["Sudden death with no signs", "Paralysis of wings and legs", "Twisted necks (torticollis)", "Greenish diarrhoea", "Swelling of head and neck", "Coughing and gasping", "Drop in egg production"],
                "treatment": ["No treatment — cull infected birds", "Supportive care for mild cases: vitamins, electrolytes", "Disinfect thoroughly after outbreak"],
                "prevention": ["Vaccinate every 3–4 months (eye drop or drinking water)", "Buy day-old chicks from reputable hatcheries", "Quarantine new birds for 2 weeks", "Restrict visitor access to chicken house", "Dispose of dead birds by burning or deep burial"],
                "severity": "critical", "contagious": True,
            },
            "gumboro": {
                "name": "Gumboro (Infectious Bursal Disease)",
                "affected_animals": ["chickens"],
                "symptoms": ["Sudden death in young chicks (2–6 weeks)", "Diarrhoea (white, watery)", "Depression and huddling", "Poor appetite", "Soiled vent feathers", "Immunosuppression (increased susceptibility to other diseases)"],
                "treatment": ["No specific treatment", "Electrolytes in drinking water", "Broad-spectrum antibiotics for secondary infections", "Improve biosecurity and sanitation"],
                "prevention": ["Vaccinate at day 14–16 (intermediate vaccine)", "Maintain strict biosecurity", "Avoid bringing infected birds or equipment onto farm", "Ensure good ventilation"],
                "severity": "high", "contagious": True,
            },
            "coccidiosis": {
                "name": "Coccidiosis",
                "affected_animals": ["chickens", "rabbits", "goats", "sheep"],
                "symptoms": ["Bloody diarrhoea", "Lethargy and huddling", "Loss of appetite", "Weight loss or poor growth", "Ruffled feathers (in birds)", "Pale comb and wattles"],
                "treatment": ["Amprolium in drinking water for 5–7 days", "Sulfa drugs (sulfadimidine) for severe cases", "Vitamin K supplement to prevent bleeding", "Probiotics to restore gut flora after treatment"],
                "prevention": ["Keep housing clean and dry — moisture promotes coccidia", "Raise drinkers and feeders to prevent faecal contamination", "Use coccidiostat in starter feed", "Avoid overcrowding", "Clean and disinfect between batches"],
                "severity": "high", "contagious": True,
            },
            "african_swine_fever": {
                "name": "African Swine Fever (ASF)",
                "affected_animals": ["pigs"],
                "symptoms": ["High fever (40–42°C)", "Red or purple skin blotches (especially ears, snout, legs)", "Vomiting and diarrhoea (sometimes bloody)", "Coughing and difficulty breathing", "Sudden death (within 7 days)", "Abortion in pregnant sows", "High mortality (up to 100%)"],
                "treatment": ["NO TREATMENT — 100% fatal in most cases", "CULL all infected and in-contact pigs immediately", "Compensate farmers where government schemes exist", "Report immediately — NOTIFIABLE DISEASE"],
                "prevention": ["Strict biosecurity: no visitors, no pig meat products on farm", "Fence farms to prevent contact with wild pigs", "Quarantine new pigs for 30 days", "Control ticks (soft ticks vector ASF)", "Do NOT feed kitchen scraps containing pork", "Vaccine in development — not yet widely available"],
                "severity": "critical", "contagious": True,
            },
            "helminthiasis": {
                "name": "Internal Parasites (Worms)",
                "affected_animals": ["cattle", "goats", "sheep", "pigs"],
                "symptoms": ["Poor body condition despite good feeding", "Pale mucous membranes (eyelids, gums)", "Bloated abdomen (especially in young animals)", "Diarrhoea or constipated droppings", "Coughing (lungworm)", "Poor growth in young animals", "Rough, dull coat"],
                "treatment": ["Broad-spectrum dewormer: albendazole, levamisole, or ivermectin", "Follow label dosing by body weight", "For goats: use 1.5x cattle dose (goats metabolize drugs faster)", "Repeat treatment in 2–3 weeks to catch emerging larvae"],
                "prevention": ["Regular deworming every 3–4 months", "Rotate pastures to break parasite cycle", "Avoid grazing young stock on contaminated pastures", "Raise feed and water troughs off ground", "Use FAMACHA method for targeted selective treatment (goats/sheep)"],
                "severity": "medium", "contagious": False,
            },
            "pneumonia": {
                "name": "Pneumonia",
                "affected_animals": ["cattle", "goats", "sheep", "pigs"],
                "symptoms": ["Coughing (moist or dry)", "Nasal discharge", "Rapid, laboured breathing", "Fever", "Loss of appetite", "Depression and isolation from herd"],
                "treatment": ["Antibiotics: oxytetracycline, tylosin, or penicillin (vet prescription)", "Anti-inflammatory drugs to reduce fever", "Move to well-ventilated, warm, dry area", "Ensure access to fresh water"],
                "prevention": ["Good ventilation in housing", "Avoid overcrowding", "Minimize stress (transport, weather changes)", "Vaccinate against specific pneumonia pathogens", "Ensure adequate nutrition for immune function"],
                "severity": "high", "contagious": True,
            },
        }

    def _get_emergency_signs(self, animal: str) -> List[str]:
        """Get emergency signs requiring immediate veterinary attention."""
        return [
            "🔴 SEEK VETERINARY HELP IMMEDIATELY if you observe:",
            "Severe difficulty breathing or gasping",
            "Continuous seizure or convulsions",
            "Complete inability to stand",
            "Severe bleeding that won't stop",
            "Prolonged labour (>2 hours with no progress)",
            "Bloating with severe distress (especially cattle, goats, sheep)",
            "Sudden death of multiple animals",
            "Severe dehydration with sunken eyes and dry gums",
            "Heat stroke: panting excessively, drooling, collapse (move to shade immediately)",
        ]

    # ------------------------------------------------------------------
    # Feeding Guide
    # ------------------------------------------------------------------

    def get_feeding_guide(
        self,
        animal: str,
        budget: str = "low",
    ) -> Dict[str, Any]:
        """Generate feeding recommendations based on animal and budget.

        Args:
            animal: Animal species.
            budget: Budget level (very_low, low, medium, high).

        Returns:
            Dictionary with feeding plan and cost estimates.
        """
        animal_key = animal.lower().strip()
        budget_key = budget.lower().strip()

        if animal_key not in self.LIVESTOCK:
            available = ", ".join(sorted(self.LIVESTOCK.keys()))
            raise ValueError(f"Unknown animal '{animal}'. Available: {available}")

        data = self.LIVESTOCK[animal_key]

        local_feeds = data.get("local_feeds", [])
        supplements = data.get("supplements", [])

        # Budget-specific feed formulation
        feed_formulations = self._get_feed_formulations(animal_key, budget_key)

        return {
            "animal": data["name"],
            "budget_level": budget_key,
            "daily_water": f"{data['water_litres_per_day'][0]}-{data['water_litres_per_day'][1]} litres",
            "local_feed_sources": local_feeds,
            "supplements": supplements,
            "feed_formulations": feed_formulations,
            "seasonal_adjustments": self._get_seasonal_feeding_adjustments(animal_key),
            "cost_saving_tips": [
                "Grow your own fodder: Napier grass, Calliandra, Desmodium",
                "Collect and store crop residues during harvest season",
                "Use kitchen waste and food processing by-products (brewery waste, etc.)",
                "Ferment crop residues with urea to improve digestibility",
                "Form buying groups with neighbours for bulk feed purchases",
                "Use food scraps from hotels and restaurants (pigs, chickens)",
            ],
            "disclaimer": "Feed recommendations are general guidelines. Adjust based on body condition, production level, and local feed availability.",
        }

    def _get_feed_formulations(
        self, animal: str, budget: str
    ) -> List[str]:
        """Get budget-specific feed formulations."""
        formulations: Dict[str, Dict[str, List[str]]] = {
            "cattle": {
                "very_low": [
                    "Grazing on communal or own pasture (free)",
                    "Crop residues: maize stover, bean haulms, rice straw",
                    "Kitchen waste and vegetable peelings",
                    "Mineral lick (salt + trace minerals)",
                ],
                "low": [
                    "Improved pasture or cut-and-carry fodder",
                    "Crop residues + 0.5–1kg dairy meal for milking cows",
                    "Urea-molasses block for dry season supplementation",
                    "Mineral supplements",
                ],
                "medium": [
                    "Fodder banks (Napier grass, Rhodes grass)",
                    "Silage or hay for dry season",
                    "1–2kg commercial dairy meal per litre of milk",
                    "Complete mineral mixture",
                    "Protein supplement (cotton seed cake or sunflower cake)",
                ],
                "high": [
                    "Total mixed ration (TMR) based on nutritional analysis",
                    "Commercial concentrates with precise nutrient balance",
                    "Silage and high-quality hay year-round",
                    "Bypass protein sources for high-producing cows",
                    "Regular body condition scoring and ration adjustment",
                ],
            },
            "chickens": {
                "very_low": [
                    "Free-range scavenging (insects, greens, grains)",
                    "Kitchen scraps and leftover food",
                    "Maize bran mixed with small amounts of protein",
                    "Clean water with occasional charcoal (digestive aid)",
                ],
                "low": [
                    "50% commercial feed + 50% scavenging/supplements",
                    "Maize bran + fish meal or omena (dagaa) for protein",
                    "Vegetable scraps and greens daily",
                    "Calcium source: crushed eggshells or oyster shells",
                ],
                "medium": [
                    "Commercial layer or broiler pellets (80% of diet)",
                    "Supplement with greens and kitchen scraps",
                    "Grit for digestion",
                    "Vitamin and mineral premix in water",
                ],
                "high": [
                    "100% commercial formulated feed (layer/broiler)",
                    "Automated feeding and watering systems",
                    "Precision nutrition based on production stage",
                    "Probiotics and acidifiers in feed",
                ],
            },
            "pigs": {
                "very_low": [
                    "Kitchen waste and food scraps",
                    "Cassava, sweet potato, banana stems",
                    "Forage greens: sweet potato vines, pumpkin leaves",
                    "Maize bran when available",
                ],
                "low": [
                    "70% maize bran + 20% protein source + 10% greens",
                    "Protein: soybean cake, fish meal, or blood meal",
                    "Sweet potato and cassava as energy source",
                    "Mineral premix",
                ],
                "medium": [
                    "Commercial pig feed (grower/finisher/sow)",
                    "Supplement with sweet potato and greens",
                    "Protein: soybean cake or commercial protein concentrate",
                    "Wet feeding system (mixing feed with water)",
                ],
                "high": [
                    "Formulated commercial diets by production stage",
                    "Precision feeding based on growth curves",
                    "Automated feeding systems",
                    "Regular feed conversion ratio monitoring",
                ],
            },
        }
        return formulations.get(animal, {}).get(budget, [
            "Provide a balanced diet appropriate for the species.",
            "Ensure adequate protein, energy, minerals, and vitamins.",
            "Fresh, clean water must be available at all times.",
        ])

    def _get_seasonal_feeding_adjustments(self, animal: str) -> List[str]:
        """Get seasonal feeding adjustments."""
        return [
            "Rainy season: Abundant pasture — maximize grazing, make hay/silage for dry season",
            "Dry season: Pasture quality drops — supplement with crop residues, hay, and concentrates",
            "Hot season: Increase water provision, feed during cooler parts of day",
            "Cold season: Increase energy feed to maintain body temperature",
            "Lactation/drought: Increase feed quantity and quality — production demands high nutrition",
        ]

    # ------------------------------------------------------------------
    # Breeding Guide
    # ------------------------------------------------------------------

    def get_breeding_guide(self, animal: str) -> Dict[str, Any]:
        """Generate breeding management guide.

        Args:
            animal: Animal species.

        Returns:
            Dictionary with breeding management information.
        """
        animal_key = animal.lower().strip()

        if animal_key not in self.LIVESTOCK:
            available = ", ".join(sorted(self.LIVESTOCK.keys()))
            raise ValueError(f"Unknown animal '{animal}'. Available: {available}")

        data = self.LIVESTOCK[animal_key]

        # Determine appropriate breeding parameters
        gestation = data.get("gestation_days") or data.get("incubation_days", 0)
        age_first = (
            data.get("age_at_first_calving_months")
            or data.get("age_at_first_kidding_months")
            or data.get("age_at_first_lambing_months")
            or data.get("age_at_first_farrowing_months")
            or data.get("age_at_first_kindling_months")
            or data.get("age_at_first_lay_weeks")
        )
        interval = (
            data.get("calving_interval_months")
            or data.get("kidding_interval_months")
            or data.get("lambing_interval_months")
            or data.get("farrowing_interval_months")
            or data.get("kindling_interval_months")
        )

        return {
            "animal": data["name"],
            "gestation_period_days": gestation,
            "age_at_first_breeding": age_first,
            "breeding_interval_months": interval,
            "breeding_tips": self._get_breeding_tips(animal_key),
            "record_keeping_template": {
                "animal_id": "Unique tag or ear mark",
                "birth_date": "Date of birth",
                "sire": "Father's ID",
                "dam": "Mother's ID",
                "breeding_date": "Date bred",
                "expected_birth": "Calculated due date",
                "actual_birth": "Actual birth date",
                "offspring": "Number born, sexes, weights",
                "weaning_date": "Date weaned",
                "notes": "Any complications or observations",
            },
            "signs_of_approaching_birth": self._get_birth_signs(animal_key),
            "disclaimer": MEDICAL_DISCLAIMER,
        }

    def _get_birth_signs(self, animal: str) -> List[str]:
        """Get signs of approaching birth/parturition."""
        signs: Dict[str, List[str]] = {
            "cattle": [
                "Udder enlargement and teats fill with colostrum (2–3 weeks before)",
                "Ligaments around tail head relax (sunken appearance)",
                "Restlessness and isolation from herd",
                "Loss of appetite 12–24 hours before",
                "Mucus discharge from vulva",
                "Straining and lying down/getting up repeatedly",
            ],
            "goats": [
                "Udder fills with milk 1–2 days before",
                "Vulva becomes swollen and relaxed",
                "Restless, pawing, and nest-making behaviour",
                "Loss of appetite",
                "Mucus string from vulva",
                "Visible contractions and straining",
            ],
            "sheep": [
                "Udder enlargement in last 2 weeks",
                "Restlessness and pawing 6–12 hours before",
                "Isolation from flock",
                "Mucus discharge",
                "Straining and visible contractions",
            ],
            "chickens": [
                "N/A — chickens lay eggs, not live young",
                "For hatching eggs: broody hen sits on nest continuously",
                "Broody hen may pluck breast feathers for nest lining",
                "Reduced appetite while sitting",
            ],
            "pigs": [
                "Mammary glands enlarge 2–3 days before (milk present 12–24h before)",
                "Restlessness and nest-building with straw 24 hours before",
                "Loss of appetite",
                "Frequent urination",
                "Mucus discharge from vulva",
                "Visible straining when farrowing begins",
            ],
            "rabbits": [
                "Doe pulls fur from chest and belly to line nest (12–24 hours before)",
                "Restlessness and digging in nest box",
                "Reduced appetite",
                "Visible straining during kindling (usually at night)",
            ],
        }
        return signs.get(animal, ["Observe for restlessness, udder enlargement, and mucus discharge.",
                                    "Have clean, warm, dry birthing area prepared in advance."])



# ---------------------------------------------------------------------------
# Class: MarketAdvisor
# ---------------------------------------------------------------------------

class MarketAdvisor:
    """Market advisory for African smallholder farmers.

    Provides price trend guidance, buyer connections, storage advice,
    and value addition strategies to help farmers maximize income
    from their agricultural produce.

    Attributes:
        MARKET_PRICES: Reference to indicative price database.
        BUYER_CONNECTIONS: Reference to buyer/market database.
    """

    MARKET_PRICES: Dict[str, Dict[str, float]] = MARKET_PRICES
    BUYER_CONNECTIONS: Dict[str, Dict[str, List[str]]] = BUYER_CONNECTIONS

    def __init__(self) -> None:
        """Initialize the MarketAdvisor with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.MarketAdvisor"
        )
        self._logger.info("MarketAdvisor initialized")

    # ------------------------------------------------------------------
    # Price Trends
    # ------------------------------------------------------------------

    def get_price_trends(
        self,
        commodity: str,
        region: str = "west_africa",
    ) -> Dict[str, Any]:
        """Get indicative price trends and guidance for a commodity.

        Args:
            commodity: Commodity name (e.g., 'maize', 'tomato', 'mango').
            region: African region.

        Returns:
            Dictionary with price guidance and market intelligence.
        """
        commodity_key = commodity.lower().strip()
        region_key = region.lower().strip().replace(" ", "_")

        price_data = self.MARKET_PRICES.get(commodity_key)

        if price_data is None:
            available = ", ".join(sorted(self.MARKET_PRICES.keys()))
            return {
                "commodity": commodity,
                "region": region_key,
                "error": f"No price data for '{commodity}'.",
                "available_commodities": available,
            }

        # Generate seasonal price intelligence
        seasonal_trends = self._get_seasonal_price_trends(commodity_key, region_key)

        # Price factors
        price_factors = self._get_price_factors(commodity_key)

        return {
            "commodity": commodity_key,
            "region": region_key,
            "price_indicative_usd_per_kg": {
                "farm_gate_min": price_data["farm_gate_min"],
                "farm_gate_max": price_data["farm_gate_max"],
                "market_min": price_data["market_min"],
                "market_max": price_data["market_max"],
            },
            "seasonal_trends": seasonal_trends,
            "price_factors": price_factors,
            "maximizing_price_tips": [
                "Grade and sort produce by size and quality",
                "Clean and package produce attractively",
                "Sell directly to consumers or restaurants (skip middlemen)",
                "Form farmer groups for collective bargaining",
                "Store produce to sell during off-season price peaks",
                "Process into value-added products for higher margins",
                "Time sales to coincide with market shortages",
                "Build relationships with multiple buyers for price comparison",
                "Use mobile phones to check prices at different markets",
                "Consider contract farming for price security",
            ],
            "disclaimer": FINANCIAL_DISCLAIMER,
        }

    def _get_seasonal_price_trends(
        self, commodity: str, region: str
    ) -> List[str]:
        """Get seasonal price trend descriptions."""
        trends: Dict[str, Dict[str, List[str]]] = {
            "west_africa": {
                "maize": [
                    "Prices LOWEST during main harvest (September–November)",
                    "Prices HIGHEST during planting/lean season (April–June)",
                    "Price variation: 30–60% between harvest and lean season",
                    "Store grain and sell during March–June for 40–60% higher prices",
                ],
                "tomato": [
                    "Prices LOWEST during rainy season (June–August) — abundant supply",
                    "Prices HIGHEST during dry season (November–March)",
                    "Price variation: 100–300% between seasons",
                    "Irrigated dry-season tomatoes command premium prices",
                ],
                "cassava": [
                    "Fresh cassava prices LOW during main harvest (October–December)",
                    "Processed products (garri, fufu) maintain more stable prices",
                    "Store fresh roots and process gradually for better returns",
                ],
                "onion": [
                    "Prices LOWEST during main harvest (March–May)",
                    "Prices HIGHEST during rainy season (June–September)",
                    "Proper storage enables selling at premium during off-season",
                ],
            },
            "east_africa": {
                "maize": [
                    "Prices LOWEST after long rains harvest (July–August)",
                    "Prices HIGHEST before short rains harvest (September–October)",
                    "Short rains harvest (January) moderates prices",
                    "Store and sell during March–May for best prices",
                ],
                "beans": [
                    "Prices LOWEST during dual harvest seasons",
                    "Prices HIGHEST during planting season when stocks are depleted",
                    "Red kidney beans command premium over other varieties",
                ],
                "coffee": [
                    "Main harvest (October–December) — prices vary with global market",
                    "Early sales during harvest tend to get lower prices",
                    "Store parchment coffee and sell during February–April for better prices",
                    "Quality premiums: AA grade fetches 20–40% above lower grades",
                ],
            },
            "southern_africa": {
                "maize": [
                    "Prices LOWEST during main harvest (April–May)",
                    "Prices HIGHEST during January–March (pre-harvest)",
                    "Government floor prices may provide price security",
                    "Regional trade with deficit countries offers premium prices",
                ],
                "tobacco": [
                    "Prices determined at auction floors — quality is critical",
                    "Premier grade (A) fetches 3–5x lowest grades",
                    "Proper curing and grading essential for good prices",
                ],
            },
        }

        region_trends = trends.get(region, {})
        commodity_trends = region_trends.get(commodity, [
            "Prices generally LOWEST during main harvest period",
            "Prices HIGHEST during planting/lean season",
            "Consider storage to capture seasonal price differences",
            "Price variation typically 30–80% between harvest and lean season",
        ])
        return commodity_trends

    def _get_price_factors(self, commodity: str) -> List[str]:
        """Get factors that affect commodity prices."""
        return [
            "Weather and production volumes in major growing areas",
            "Regional supply and demand balance",
            "Quality (size, colour, moisture content, defects)",
            "Transport costs and market access",
            "Number of competing sellers at market",
            "Government policies (subsidies, import bans, floor prices)",
            "Global commodity prices (for export crops)",
            "Exchange rate fluctuations",
            "Post-harvest losses reducing effective supply",
            "Political stability and trade agreements",
        ]

    # ------------------------------------------------------------------
    # Buyer Connections
    # ------------------------------------------------------------------

    def get_buyer_connections(
        self,
        commodity: str,
        region: str = "west_africa",
    ) -> Dict[str, Any]:
        """Get buyer and market connection guidance.

        Args:
            commodity: Commodity name.
            region: African region.

        Returns:
            Dictionary with buyer information and market access tips.
        """
        commodity_key = commodity.lower().strip()
        region_key = region.lower().strip().replace(" ", "_")

        buyers = self.BUYER_CONNECTIONS.get(region_key, {})
        commodity_buyers = buyers.get(commodity_key, buyers.get(
            commodity_key.replace("_", " "),
            ["Local open-air markets", "Roadside vendors", "Neighbouring traders"],
        ))

        return {
            "commodity": commodity_key,
            "region": region_key,
            "primary_buyers": commodity_buyers,
            "market_types": self._get_market_types(commodity_key),
            "access_strategies": [
                "Form or join a farmer cooperative — bulk sales attract better buyers",
                "Register with agricultural marketing boards where they exist",
                "Use mobile market information services (SMS price alerts)",
                "Attend agricultural trade fairs and expos",
                "Build relationships with multiple buyers — never rely on just one",
                "Consider forward contracts with buyers for price security",
                "Use social media and farmer networks to find buyers",
                "Explore e-commerce platforms for agricultural products",
                "Link with schools, hospitals, and prisons for institutional buyers",
                "Contact export agents for commodities with export potential",
            ],
            "value_chain_participants": [
                "Input suppliers (seeds, fertilizer, agrochemicals)",
                "Extension officers (technical advice, quality standards)",
                "Transporters (getting produce to market)",
                "Aggregators/bulking agents (combining small volumes)",
                "Processors (adding value — milling, drying, packaging)",
                "Wholesalers (buying in bulk for redistribution)",
                "Retailers (selling to final consumers)",
                "Consumers (end users of the product)",
            ],
            "transport_tips": [
                "Transport early morning to avoid heat damage to perishables",
                "Use appropriate packaging to prevent bruising and loss",
                "Combine loads with neighbouring farmers to reduce transport costs",
                "Consider renting versus owning transport based on frequency",
                "Plan transport routes to minimize distance and road quality issues",
            ],
            "disclaimer": FINANCIAL_DISCLAIMER,
        }

    def _get_market_types(self, commodity: str) -> List[str]:
        """Get relevant market types for a commodity."""
        perishables = ["tomato", "pepper", "onion", "cabbage", "mango", "banana",
                       "pineapple", "pawpaw", "citrus", "vegetables"]
        grains = ["maize", "rice", "sorghum", "millet", "beans", "groundnut", "sesame", "wheat"]
        cash_crops = ["cocoa", "coffee", "tea", "cotton", "tobacco"]
        tubers = ["cassava", "yam", "sweet_potato"]

        if commodity in perishables:
            return [
                "Fresh produce markets (daily, high volume)",
                "Supermarkets and grocery stores",
                "Restaurants and hotels",
                "Institutional buyers (schools, hospitals)",
                "Processing factories",
                "Export markets (for certified produce)",
            ]
        elif commodity in grains:
            return [
                "Grain markets and depots",
                "Government procurement agencies",
                "Millers and processors",
                "Feed manufacturers",
                "WFP and humanitarian buyers",
                "Regional cross-border traders",
            ]
        elif commodity in cash_crops:
            return [
                "Licensed buying companies",
                "Auction floors",
                "Direct exporters",
                "Processing factories",
                "Commodity exchanges",
            ]
        elif commodity in tubers:
            return [
                "Fresh tuber markets",
                "Processors (flour, starch, garri)",
                "Urban wholesale markets",
                "Food service industry",
            ]
        else:
            return [
                "Local open-air markets",
                "Urban wholesale markets",
                "Direct to consumers",
                "Processing companies",
            ]

    # ------------------------------------------------------------------
    # Storage Advice
    # ------------------------------------------------------------------

    def get_storage_advice(self, commodity: str) -> Dict[str, Any]:
        """Get post-harvest storage recommendations.

        Args:
            commodity: Commodity name.

        Returns:
            Dictionary with storage methods and guidelines.
        """
        commodity_key = commodity.lower().strip()

        storage_methods = self._build_storage_methods(commodity_key)

        return {
            "commodity": commodity_key,
            "storage_methods": storage_methods,
            "general_principles": [
                "Clean produce before storage — remove soil, debris, and damaged items",
                "Dry to safe moisture content before storing grains",
                "Store in a clean, dry, well-ventilated structure",
                "Keep produce off the ground and away from walls",
                "Inspect stored produce regularly (weekly for grains, daily for perishables)",
                "Practice first-in-first-out (FIFO) — sell oldest stock first",
                "Protect from rodents, insects, and moisture",
                "Never store chemicals or fuel in the same room as food",
            ],
            "common_storage_structures": [
                "PICS bags (hermetic storage) — excellent for grains, prevents insects without chemicals",
                "Metal silos — 100–1000kg capacity, rodent-proof",
                "Raised granary platform — keeps grain off ground, improves ventilation",
                "Charcoal cooler (zero-energy cold room) — extends shelf life of vegetables",
                "Underground pit store — for root crops in dry areas",
                "Yam barn — ventilated structure for yam storage",
                "Simple cold room (solar-powered) — for high-value perishables",
            ],
            "moisture_content_guidelines": self._get_moisture_guidelines(commodity_key),
            "disclaimer": "Storage recommendations are general guidelines. Adapt based on local climate, infrastructure, and resources.",
        }

    def _build_storage_methods(self, commodity: str) -> List[Dict[str, Any]]:
        """Build detailed storage methods for a commodity."""
        methods: Dict[str, List[Dict[str, Any]]] = {
            "maize": [
                {"method": "PICS bags", "duration": "12+ months", "description": "Triple-bag system excludes oxygen, killing insects without chemicals. Cost-effective for smallholders.", "cost_usd": "2–3 per bag (holds 50–100kg)"},
                {"method": "Metal silo", "duration": "12+ months", "description": "100–1000kg capacity. Airtight when sealed. One-time investment.", "cost_usd": "30–150 depending on size"},
                {"method": "Hermetic drums", "duration": "6–12 months", "description": "Repurposed oil drums with airtight lids. Cost-effective recycled option.", "cost_usd": "5–15 per drum"},
                {"method": "Traditional granary", "duration": "3–6 months", "description": "Raised platform with thatched roof. Good ventilation but less pest protection.", "cost_usd": "Labour and local materials"},
            ],
            "cassava": [
                {"method": "Fresh root storage", "duration": "1–2 weeks", "description": "Store in cool, shaded, ventilated area. Cover with moist jute sacks.", "cost_usd": "Labour only"},
                {"method": "Garri storage", "duration": "6–12 months", "description": "Store processed garri in airtight containers in dry place.", "cost_usd": "Containers: 2–5"},
                {"method": "Dried cassava chips", "duration": "6+ months", "description": "Sun-dry chips thoroughly and store in sacks. Reconstitute by soaking.", "cost_usd": "Sacks and labour"},
            ],
            "tomato": [
                {"method": "Evaporative cooling (charcoal cooler)", "duration": "1–2 weeks", "description": "Zero-energy cooler using wet charcoal and sand. Reduces temperature by 10–15°C.", "cost_usd": "20–50 to construct"},
                {"method": "Shade storage", "duration": "2–4 days", "description": "Store in single layers in shaded, ventilated area.", "cost_usd": "Free"},
                {"method": "Processing into paste/sauce", "duration": "6–12 months", "description": "Cook down with onions and bottle. Sterilize bottles.", "cost_usd": "Bottles and fuel"},
            ],
            "onion": [
                {"method": "Mesh bag hanging", "duration": "2–6 months", "description": "Store in well-ventilated mesh bags hung from rafters. Red varieties store shorter.", "cost_usd": "Mesh bags: 0.5 each"},
                {"method": "Braided string storage", "duration": "3–6 months", "description": "Braid dried tops together and hang in cool, dry, airy room.", "cost_usd": "Labour only"},
                {"method": "Slatted crate storage", "duration": "3–5 months", "description": "Store in ventilated wooden crates in cool, dry place.", "cost_usd": "Crates: 2–5 each"},
            ],
            "mango": [
                {"method": "Ripening room", "duration": "1–2 weeks", "description": "Store mature-green fruit at 12–13°C, 85–90% humidity for gradual ripening.", "cost_usd": "Cool room setup: 500+"},
                {"method": "Shaded single-layer storage", "duration": "3–7 days", "description": "Place in single layers in shaded, ventilated area. Turn daily.", "cost_usd": "Free"},
                {"method": "Dried mango", "duration": "6–12 months", "description": "Slice and solar-dry for 3–5 days. Package in sealed bags.", "cost_usd": "Packaging: 0.2 per bag"},
            ],
        }
        return methods.get(commodity, [
            {"method": "General storage", "duration": "Varies", "description": "Store in clean, dry, well-ventilated area. Keep off ground.", "cost_usd": "Minimal"},
        ])

    def _get_moisture_guidelines(self, commodity: str) -> Dict[str, str]:
        """Get safe moisture content for storage."""
        guidelines: Dict[str, str] = {
            "maize": "13.5% maximum for safe storage",
            "sorghum": "13.0% maximum",
            "millet": "12.0% maximum",
            "rice": "14.0% maximum (paddy)",
            "beans": "14.0% maximum",
            "groundnut": "8.0% in-shell, 6–7% shelled",
            "sesame": "6.0% maximum",
            "cassava": "Process within 48 hours (fresh); 10–12% (chips)",
            "wheat": "13.0% maximum",
        }
        return {commodity: guidelines.get(commodity, "Dry thoroughly before storage. Test by biting — grain should crack, not bend.")}

    # ------------------------------------------------------------------
    # Value Addition
    # ------------------------------------------------------------------

    def get_value_addition(self, commodity: str) -> Dict[str, Any]:
        """Get value addition and processing recommendations.

        Args:
            commodity: Commodity name.

        Returns:
            Dictionary with processing options and potential returns.
        """
        commodity_key = commodity.lower().strip()

        options = self._get_value_addition_options(commodity_key)

        return {
            "commodity": commodity_key,
            "value_addition_options": options,
            "general_processing_tips": [
                "Start small — test market acceptance before scaling up",
                "Ensure food safety: clean equipment, potable water, proper hygiene",
                "Package attractively with clear labels",
                "Register your product and brand where required",
                "Comply with local food safety regulations",
                "Keep detailed cost records to track profitability",
                "Seek training from agricultural colleges or NGOs on processing techniques",
                "Join processors' associations for market linkages and support",
            ],
            "financing_options": [
                "Microfinance institutions specializing in agriculture",
                "Farmer cooperative loans",
                "Government agricultural development funds",
                "NGO grants for youth and women in agribusiness",
                "Crowdfunding platforms for agricultural enterprises",
                "Contract farming with advance payment arrangements",
            ],
            "disclaimer": FINANCIAL_DISCLAIMER,
        }

    def _get_value_addition_options(
        self, commodity: str
    ) -> List[Dict[str, Any]]:
        """Get specific value addition options for a commodity."""
        options: Dict[str, List[Dict[str, Any]]] = {
            "cassava": [
                {"product": "Garri", "investment_usd": "50–200", "equipment": "Grater, press, fryer", "value_increase": "2–3x raw cassava price", "market": "Local staple food — constant demand"},
                {"product": "Fufu flour (HQCF)", "investment_usd": "100–500", "equipment": "Grater, press, dryer, mill", "value_increase": "2–4x", "market": "Urban markets, export to diaspora"},
                {"product": "Cassava chips (for feed)", "investment_usd": "20–100", "equipment": "Chipping machine or manual grater", "value_increase": "1.5–2x", "market": "Animal feed manufacturers"},
                {"product": "Cassava starch", "investment_usd": "500–2000", "equipment": "Processing line", "value_increase": "3–5x", "market": "Textile, pharmaceutical, food industries"},
            ],
            "maize": [
                {"product": "Maize flour (ugali/sadza)", "investment_usd": "100–500", "equipment": "Hammer mill or posho mill", "value_increase": "1.5–2x", "market": "Daily staple — constant demand"},
                {"product": "Animal feed (poultry/pig)", "investment_usd": "50–300", "equipment": "Mixer, grinder", "value_increase": "1.5–2x", "market": "Livestock farmers in your area"},
                {"product": "Popcorn", "investment_usd": "20–100", "equipment": "Popcorn machine", "value_increase": "3–5x", "market": "Schools, markets, events"},
            ],
            "tomato": [
                {"product": "Tomato paste/sauce", "investment_usd": "50–200", "equipment": "Large pots, bottles, labels", "value_increase": "2–3x", "market": "Urban households, restaurants"},
                {"product": "Dried tomatoes", "investment_usd": "20–50", "equipment": "Solar dryer or raised drying racks", "value_increase": "3–5x", "market": "Restaurants, exporters, gourmet markets"},
                {"product": "Tomato juice", "investment_usd": "100–300", "equipment": "Juicer, bottles, pasteurizer", "value_increase": "2–3x", "market": "Urban fresh juice market"},
            ],
            "mango": [
                {"product": "Dried mango slices", "investment_usd": "100–500", "equipment": "Solar dryer, slicing tools, packaging", "value_increase": "5–10x", "market": "Export (Europe, Middle East), urban supermarkets"},
                {"product": "Mango juice", "investment_usd": "200–1000", "equipment": "Extractor, pasteurizer, bottles", "value_increase": "3–5x", "market": "Urban juice bars, supermarkets"},
                {"product": "Mango jam", "investment_usd": "50–200", "equipment": "Large pots, jars, labels", "value_increase": "4–6x", "market": "Urban households, hotels"},
            ],
            "groundnut": [
                {"product": "Groundnut oil", "investment_usd": "100–500", "equipment": "Oil press, filter, bottles", "value_increase": "2–3x", "market": "Local cooking oil market"},
                {"product": "Roasted groundnuts", "investment_usd": "20–100", "equipment": "Roasting pan, packaging", "value_increase": "2–3x", "market": "Snack market, schools"},
                {"product": "Peanut butter", "investment_usd": "50–200", "equipment": "Grinder, jars, labels", "value_increase": "3–5x", "market": "Urban households, supermarkets"},
            ],
            "milk": [
                {"product": "Fresh pasteurized milk", "investment_usd": "200–1000", "equipment": "Pasteurizer, bottles, cold storage", "value_increase": "1.5–2x", "market": "Direct to consumers, shops"},
                {"product": "Yoghurt", "investment_usd": "100–500", "equipment": "Heater, incubator, containers", "value_increase": "2–3x", "market": "Urban households, schools"},
                {"product": "Cheese", "investment_usd": "200–1000", "equipment": "Cheese vat, moulds, aging room", "value_increase": "5–10x", "market": "Hotels, supermarkets, export"},
            ],
            "coffee": [
                {"product": "Roasted coffee", "investment_usd": "500–2000", "equipment": "Roaster, grinder, packaging", "value_increase": "3–5x green price", "market": "Cafés, supermarkets, online"},
                {"product": "Specialty single-origin", "investment_usd": "Training + certification", "equipment": "Small roaster, precision equipment", "value_increase": "5–15x", "market": "Specialty coffee shops, export"},
            ],
            "cocoa": [
                {"product": "Properly fermented & dried beans", "investment_usd": "Boxes, tarps, labour", "equipment": "Fermentation boxes, drying racks", "value_increase": "Quality premium: 10–30% above bulk", "market": "Direct to chocolate makers, premium buyers"},
                {"product": "Cocoa butter/powder", "investment_usd": "5000+", "equipment": "Processing facility", "value_increase": "Significant", "market": "Cosmetic and food industries"},
            ],
        }
        return options.get(commodity, [
            {"product": "Grading and sorting", "investment_usd": "Minimal", "equipment": "Sorting trays, scales", "value_increase": "10–20%", "market": "All markets pay premium for graded produce"},
            {"product": "Basic packaging", "investment_usd": "10–50", "equipment": "Bags, labels, scales", "value_increase": "10–30%", "market": "Supermarkets, urban consumers"},
        ])

# ---------------------------------------------------------------------------
# Class: ClimateAdvisor
# ---------------------------------------------------------------------------

class ClimateAdvisor:
    """Climate resilience and adaptation advisory for African farmers.

    Provides guidance on drought resilience, flood adaptation, soil
    conservation, and seasonal weather advisories tailored to African
    agro-ecological zones.
    """

    def __init__(self) -> None:
        """Initialize the ClimateAdvisor with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.ClimateAdvisor"
        )
        self._logger.info("ClimateAdvisor initialized")

    # ------------------------------------------------------------------
    # Drought Resilience
    # ------------------------------------------------------------------

    def get_drought_resilience(self, crop: str) -> Dict[str, Any]:
        """Get drought resilience strategies for a crop.

        Args:
            crop: Crop name.

        Returns:
            Dictionary with drought adaptation strategies.
        """
        crop_key = crop.lower().strip()

        drought_tolerant_varieties = self._get_drought_tolerant_varieties(crop_key)
        water_conservation = self._get_water_conservation_methods(crop_key)

        return {
            "crop": crop_key,
            "drought_risk_level": self._assess_drought_risk(crop_key),
            "drought_tolerant_varieties": drought_tolerant_varieties,
            "water_conservation_techniques": water_conservation,
            "cultural_practices": [
                "Plant early with the first rains to maximize growing season",
                "Use mulch (crop residues, grass, plastic) to reduce evaporation by 30–50%",
                "Reduce plant population slightly to reduce competition for water",
                "Weed early and thoroughly — weeds compete for moisture",
                "Apply fertilizer in splits — small, frequent applications",
                "Prune lower leaves of crops like cassava to reduce transpiration",
                "Harvest rainwater from rooftops and bare ground into storage",
                "Consider water harvesting techniques: zai pits, demi-lunes, contour bunds",
                "Plant windbreaks to reduce evapotranspiration",
                "Use early-maturing varieties to escape end-of-season drought",
            ],
            "contingency_plan": [
                "If rains fail completely: Consider replanting with shorter-duration crops",
                "Fast-maturing alternatives: cowpea (60 days), vegetables (45–60 days)",
                "Forage crops: Plant drought-tolerant fodder for livestock",
                "Off-farm income: Develop alternative income sources as buffer",
                "Insurance: Explore index-based weather insurance where available",
                "Community support: Join farmer groups for mutual aid during drought",
            ],
            "disclaimer": WEATHER_DISCLAIMER,
        }

    def _assess_drought_risk(self, crop: str) -> str:
        """Assess drought risk for a crop."""
        crop_data = CROPS.get(crop, {})
        tolerance = crop_data.get("drought_tolerance", "moderate")
        rainfall = crop_data.get("rainfall_mm", (500, 1000))

        if tolerance in ["very_high", "high"] and rainfall[0] < 500:
            return "LOW — This crop is naturally drought-tolerant"
        elif tolerance in ["high", "moderate"]:
            return "MODERATE — Use recommended practices to reduce risk"
        else:
            return "HIGH — This crop requires reliable moisture. Consider irrigation or alternative crops in drought-prone areas"

    def _get_drought_tolerant_varieties(self, crop: str) -> List[str]:
        """Get recommended drought-tolerant varieties."""
        varieties: Dict[str, List[str]] = {
            "maize": [
                "SC627 (drought-tolerant hybrid, Southern Africa)",
                "DKC80-53 (medium maturity, good drought escape)",
                "WE2115 (early maturing, West Africa)",
                "ZH561 (Zambia, drought tolerant)",
                "Local early varieties: plant at onset of rains",
                "Open-pollinated varieties: can save seed for replanting",
            ],
            "cassava": [
                "TMS 30572 (widely adapted, drought tolerant)",
                "TME 419 (Nigeria, drought tolerant)",
                "MM96 (East Africa, drought and disease tolerant)",
                "Nase varieties (Uganda, cassava brown streak resistant)",
            ],
            "sorghum": [
                "Serena (East Africa, widely adapted)",
                "Kobo (Ethiopia, drought tolerant)",
                "Macia (Southern Africa, dual purpose)",
                "Local landraces: adapted to local conditions",
            ],
            "millet": [
                "ICMV 221 (Indian variety, widely grown in Sahel)",
                "SOSAT-C88 (West Africa, Striga resistant)",
                "Okashana 1 (Southern Africa, early maturing)",
                "Local pearl millet landraces",
            ],
            "beans": [
                "KAT B1 (bush bean, drought tolerant, Kenya)",
                "Rosecoco / GLP 2 (widely adapted)",
                "Local varieties: early maturing preferred in dry areas",
            ],
            "groundnut": [
                "Samnut 24 (early maturing, drought tolerant)",
                "JL 24 (Spanish type, drought tolerant)",
                "Local varieties: short-duration preferred",
            ],
            "cowpea": [
                "IT89KD-288 (drought tolerant, dual purpose)",
                "IT99K-573-1-1 (Striga and drought tolerant)",
                "Local varieties: well-adapted to dry conditions",
            ],
        }
        return varieties.get(crop, [
            "Choose early-maturing varieties to escape end-of-season drought",
            "Select varieties bred for your specific agro-ecological zone",
            "Use certified seed from reputable sources",
        ])

    def _get_water_conservation_methods(self, crop: str) -> List[str]:
        """Get water conservation methods."""
        return [
            "MULCHING: Apply 5–10cm layer of crop residues, grass, or dried leaves between rows. "
            "Reduces evaporation by 30–60%, suppresses weeds, adds organic matter.",

            "ZAI PITS: Dig planting pits 30cm wide x 30cm deep, fill with compost and manure. "
            "Capture runoff water and concentrate it around plant roots. "
            "Spacing: 1m x 1m for cereals, 80cm x 80cm for sorghum/millet.",

            "HALF-MOON / DEMI-LUNE: Dig semicircular bunds (3m diameter) on contour to capture "
            "and infiltrate runoff water. Plant crops inside the half-moon.",

            "CONTOUR BUNDS / FANYA JUU: Build soil bunds along contours to slow runoff "
            "and allow water infiltration. Plant grass (e.g., Napier) on bunds for fodder.",

            "TIED RIDGES: Make ridges with cross-ties to create small basins that hold "
            "rainwater. Very effective for sorghum and maize in semi-arid areas.",

            "WATER HARVESTING: Collect rooftop runoff into storage tanks. "
            "1,000 litres tank can irrigate 100m² for several weeks.",

            "KEYHOLE GARDENS: Raised circular beds (2m diameter) with compost basket in centre. "
            "Nutrients and water leach from basket to surrounding crops. "
            "Ideal for vegetables near homesteads.",

            "DRIP IRRIGATION (bottle system): Use recycled plastic bottles with small holes "
            "near plant base. Fill bottles manually. Very low cost, highly efficient.",

            "THREE STONE FIRE STOVE WATER: Reuse cooled cooking water (rich in nutrients) "
            "for watering vegetables near the homestead.",

            "SAND DAMS: In seasonal riverbeds, construct concrete or masonry wall across "
            "sandy riverbed to store water in sand aquifer. "
            "Water is accessed through wells downstream.",
        ]

    # ------------------------------------------------------------------
    # Flood Adaptation
    # ------------------------------------------------------------------

    def get_flood_adaptation(self, crop: str) -> Dict[str, Any]:
        """Get flood adaptation strategies for a crop.

        Args:
            crop: Crop name.

        Returns:
            Dictionary with flood adaptation strategies.
        """
        crop_key = crop.lower().strip()

        return {
            "crop": crop_key,
            "flood_risk_level": self._assess_flood_risk(crop_key),
            "adaptation_strategies": [
                "RAISED BEDS: Plant on raised beds (30–50cm high) to keep roots above flood water.",
                "RIDGES AND MOUNDS: Form ridges for root crops and cereals in flood-prone areas.",
                "DRAINAGE CHANNELS: Dig drainage channels between fields to remove excess water.",
                "CONTOUR PLANTING: Plant along contours to slow water flow and reduce erosion.",
                "COVER CROPS: Plant cover crops (Mucuna, Canavalia) to protect soil during floods.",
                "AGROFORESTRY: Plant trees on field borders to reduce runoff velocity and soil erosion.",
                "DIVERSIFICATION: Grow multiple crops — if one fails due to flood, others may survive.",
                "FAST-MATURING VARIETIES: Plant early to harvest before peak flood season.",
                "FIELD LEVELING: Level fields for even water distribution and drainage.",
            ],
            "post_flood_recovery": [
                "Drain standing water as quickly as possible",
                "Aerate soil by light cultivation once water recedes",
                "Apply lime if flooding caused soil acidity",
                "Replenish nutrients — floods leach nitrogen and other nutrients",
                "Remove silt deposits from crop bases carefully",
                "Prune damaged plant parts to encourage new growth",
                "Monitor for increased pest and disease pressure after flooding",
                "Replant if crop damage exceeds 50% — use fast-maturing varieties",
                "Document losses for insurance claims where available",
            ],
            "flood_tolerant_crop_alternatives": [
                "Rice (lowland/floating varieties) — thrives in flooded conditions",
                "Taro / Cocoyam — tolerates waterlogged soils",
                "Water yam (Dioscorea alata) — more flood-tolerant than white yam",
                "Sweet potato — some varieties tolerate short-term flooding",
                "Sugarcane — tolerates periodic flooding",
            ],
            "disclaimer": WEATHER_DISCLAIMER,
        }

    def _assess_flood_risk(self, crop: str) -> str:
        """Assess flood risk for a crop."""
        flood_sensitive = ["tomato", "pepper", "onion", "cassava", "groundnut", "maize"]
        flood_tolerant = ["rice", "taro", "cocoyam", "water_yam"]

        if crop in flood_tolerant:
            return "LOW — This crop tolerates or benefits from flooding"
        elif crop in flood_sensitive:
            return "HIGH — This crop is sensitive to waterlogging. Use raised beds in flood-prone areas"
        else:
            return "MODERATE — Monitor water levels and provide drainage if needed"

    # ------------------------------------------------------------------
    # Soil Conservation
    # ------------------------------------------------------------------

    def get_soil_conservation(self, method: str = "general") -> Dict[str, Any]:
        """Get soil conservation and management guidance.

        Args:
            method: Specific conservation method or 'general'.

        Returns:
            Dictionary with soil conservation techniques.
        """
        method_key = method.lower().strip().replace(" ", "_")

        techniques = self._build_conservation_techniques()

        if method_key in techniques:
            return {
                "method": method_key,
                "description": techniques[method_key],
                "disclaimer": GENERAL_DISCLAIMER,
            }

        return {
            "method": "general",
            "available_methods": list(techniques.keys()),
            "soil_conservation_principles": [
                "MINIMUM TILLAGE: Disturb soil as little as possible to maintain structure and organic matter.",
                "COVER THE SOIL: Keep soil covered with crops, mulch, or cover crops year-round.",
                "CROP ROTATION: Alternate different crop families to break pest cycles and balance nutrient uptake.",
                "DIVERSITY: Grow multiple species (polyculture) for resilience and soil health.",
                "INTEGRATE LIVESTOCK: Use animal manure to fertilize crops; use crop residues as feed.",
                "CONTOUR FARMING: Plant along contours to reduce runoff and soil erosion.",
            ],
            "detailed_techniques": techniques,
            "disclaimer": GENERAL_DISCLAIMER,
        }

    def _build_conservation_techniques(self) -> Dict[str, List[str]]:
        """Build comprehensive soil conservation techniques database."""
        return {
            "terracing": [
                "BENCH TERRACES: Convert steep slopes into level steps. Suitable for slopes >15%.",
                "Construction: Cut and fill to create level benches 3–5m wide.",
                "Plant embankment with grass (Napier, vetiver) to stabilize.",
                "Benefits: Reduces erosion by 80–90%, improves water infiltration.",
                "Labour: High initial investment but lasts 20+ years with maintenance.",
                "Best for: Hillside farming of potatoes, vegetables, tea, coffee.",
            ],
            "cover_crops": [
                "LEGUME COVER CROPS: Plant Mucuna (velvet bean), Canavalia, Crotalaria, or Tithonia.",
                "Benefits: Fix nitrogen, suppress weeds, add organic matter, prevent erosion.",
                "Timing: Plant during off-season or intercrop with main crop.",
                "Management: Slash and leave as mulch, or incorporate into soil at flowering.",
                "Cost: Seed cost only — high return in soil fertility improvement.",
                "Special: Mucuna suppresses Striga (witchweed) in maize fields.",
            ],
            "agroforestry": [
                "ALLEY CROPPING: Plant rows of trees (Gliricidia, Leucaena, Calliandra) with crops between.",
                "Prune trees regularly and use leaves as mulch/green manure.",
                "Trees provide: Nitrogen fixation, shade, windbreak, fodder, firewood, fruit.",
                "Spacing: 5–8m between tree rows, crops planted in alleys.",
                "FODDER BANKS: Plant Calliandra, Leucaena, or Gliricidia for dry season livestock feed.",
                "CONTOUR HEDGEROWS: Plant vetiver grass or fodder trees along contours.",
                "Reduces erosion, provides fodder, and creates natural terraces over time.",
            ],
            "contour_farming": [
                "Use A-frame or simple water level to mark contour lines across slope.",
                "Plant crops along contour lines (not up and down the slope).",
                "Build grass strips or trash lines along contours to slow runoff.",
                "Benefits: Reduces soil loss by 50%, increases water infiltration.",
                "Suitable for: All sloped fields >2% gradient.",
            ],
            "mulching": [
                "Apply 5–15cm layer of organic material between crop rows.",
                "Materials: Crop residues, grass cuttings, straw, leaves, wood chips.",
                "Benefits: Reduces evaporation 30–60%, suppresses weeds, moderates soil temperature, adds organic matter.",
                "Application: After planting, replenish as material decomposes.",
                "Caution: Keep mulch 5cm away from plant stems to prevent rot.",
            ],
            "crop_rotation": [
                "Rotate cereals with legumes to break pest/disease cycles and fix nitrogen.",
                "Example rotation: Maize → Beans → Cassava → Groundnut → Maize.",
                "Benefits: Improves soil fertility, reduces pest pressure, diversifies income.",
                "Avoid: Planting same crop family in same field year after year.",
                "Include: Deep-rooted crops (cassava) to break hardpans and bring up nutrients.",
            ],
            "minimum_tillage": [
                "Use hand hoes or rippers instead of ploughing entire field.",
                "Plant directly into untilled soil (conservation agriculture).",
                "Benefits: Preserves soil structure, reduces erosion, saves labour and fuel.",
                "Requires: Good weed management (mulch helps suppress weeds).",
                "Suitable for: Most smallholder conditions where labour is available for weeding.",
            ],
            " composting ": [
                "PILE METHOD: Layer crop residues, animal manure, and soil in a pile 1.5m x 1.5m x 1.5m.",
                "Turn pile every 2 weeks for aerobic decomposition.",
                "Ready in 6–12 weeks when dark, crumbly, and earthy-smelling.",
                "Apply 5–10 tonnes/hectare before planting.",
                "Benefits: Improves soil structure, water holding capacity, and nutrient availability.",
            ],
            "vetiver_grass": [
                "Plant vetiver grass (Chrysopogon zizanioides) in hedgerows on contour.",
                "Deep roots (up to 3m) stabilize soil and prevent erosion.",
                "Dense hedges slow runoff and filter sediment.",
                "Low maintenance, drought-tolerant once established.",
                "Also used for: Thatch, mulch, handicrafts, essential oil.",
            ],
            "stone_bunds": [
                "Build lines of stones along contours to slow runoff and trap soil.",
                "Over time, soil builds up behind bunds creating natural terraces.",
                "Very low cost — uses locally available stones.",
                "Best for: Semi-arid areas with stone availability (Sahel, Horn of Africa).",
                "Combine with: Zai pits between stone lines for maximum effect.",
            ],
        }

    # ------------------------------------------------------------------
    # Weather Advisory
    # ------------------------------------------------------------------

    def get_weather_advisory(
        self,
        region: str,
        season: str = "rainy",
    ) -> Dict[str, Any]:
        """Generate seasonal weather advisory for a region.

        Args:
            region: African region.
            season: Current or upcoming season.

        Returns:
            Dictionary with weather guidance and farm management advice.
        """
        region_key = region.lower().strip().replace(" ", "_")
        season_key = season.lower().strip()

        region_data = REGIONAL_CLIMATE.get(region_key, {})

        advisory = self._build_seasonal_advisory(region_key, season_key)

        return {
            "region": region_key,
            "season": season_key,
            "climate_summary": {
                "annual_rainfall_mm": region_data.get("annual_rainfall_mm", "Varies"),
                "temperature_range_c": region_data.get("temperature_range_c", "Varies"),
                "dominant_soil_types": region_data.get("dominant_soil", ["Varies"]),
                "key_challenges": region_data.get("challenges", []),
            },
            "seasonal_advisory": advisory,
            "early_warning_indicators": self._get_early_warning_indicators(region_key),
            "climate_change_adaptation": [
                "Diversify crops and income sources for resilience",
                "Invest in water harvesting and storage infrastructure",
                "Use early-maturing and drought-tolerant varieties",
                "Improve soil organic matter to enhance water holding capacity",
                "Join farmer groups for climate information sharing",
                "Keep detailed weather and yield records to identify trends",
                "Explore weather index insurance where available",
                "Integrate trees (agroforestry) for microclimate modification",
            ],
            "disclaimer": WEATHER_DISCLAIMER,
        }

    def _build_seasonal_advisory(
        self, region: str, season: str
    ) -> List[str]:
        """Build seasonal advisory for a region."""
        advisories: Dict[str, Dict[str, List[str]]] = {
            "west_africa": {
                "rainy": [
                    "🌧️ RAINY SEASON (March–October): Main planting and growing season",
                    "Plant early with the first reliable rains — every week of delay reduces yield",
                    "Prioritize land preparation before rains arrive",
                    "Monitor for Fall Armyworm — scout fields weekly",
                    "Apply fertilizer in splits to prevent leaching in heavy rains",
                    "Ensure drainage in low-lying fields to prevent waterlogging",
                    "Store seeds and inputs in dry, elevated places",
                    "Prepare for harvest: arrange labour, storage, and transport",
                ],
                "dry": [
                    "☀️ DRY SEASON (November–March): Plan for water scarcity",
                    "Focus on irrigated vegetables (tomato, pepper, onion) for premium prices",
                    "Maintain livestock — provide adequate water and supplementary feeding",
                    "Harvest and process crops — garri making, grain storage",
                    "Repair farm infrastructure: fences, storage, irrigation",
                    "Attend training and plan for next season",
                    "Sell stored grain during lean season for higher prices",
                ],
                "harmattan": [
                    "🌬️ HARMATTAN (December–February): Cold, dusty northeast winds",
                    "Protect young seedlings from desiccating winds",
                    "Increase irrigation frequency — low humidity increases evaporation",
                    "Cover nurseries with shade nets or grass",
                    "Be aware of increased fire risk — avoid bush burning",
                ],
            },
            "east_africa": {
                "long_rains": [
                    "🌧️ LONG RAINS (March–May): Main planting season",
                    "Plant early — long rains are becoming less reliable",
                    "Use certified seeds of drought-tolerant varieties",
                    "Top-dress fertilizer before heavy rains leach nutrients",
                    "Monitor for pests: stem borers, aphids, Fall Armyworm",
                    "Maintain clean seed beds for vegetable production",
                ],
                "short_rains": [
                    "🌦️ SHORT RAINS (October–December): Second growing season",
                    "Plant early-maturing varieties that complete before rains end",
                    "Opportunity for off-season vegetables at premium prices",
                    "Supplement rainfall with irrigation where possible",
                    "Harvest and store short rains produce carefully",
                ],
                "dry": [
                    "☀️ DRY SEASON (June–September, January–February)",
                    "Focus on irrigated high-value crops: tomatoes, onions, vegetables",
                    "Livestock: conserve fodder, provide water, manage grazing",
                    "Coffee and tea: maintain shade, mulch, and pest control",
                ],
            },
            "southern_africa": {
                "rainy": [
                    "🌧️ RAINY SEASON (November–April): Summer rainfall",
                    "Plant with first rains (November–December) for longest growing period",
                    "Monitor El Niño/La Niña forecasts — they strongly affect this region",
                    "Diversify plantings to spread climate risk",
                    "Control weeds early before they compete for moisture",
                    "Monitor for stalk borer and Fall Armyworm",
                ],
                "dry": [
                    "☀️ DRY SEASON (May–October): Winter",
                    "Grow wheat, barley, and winter vegetables under irrigation",
                    "Harvest and store summer crops — sell strategically",
                    "Provide livestock with conserved fodder (hay, silage)",
                    "Repair equipment and prepare for next season",
                ],
            },
            "sahel": {
                "rainy": [
                    "🌧️ SHORT RAINY SEASON (June–September): Only 3–4 months of rain",
                    "CRITICAL: Every planting day counts — plant immediately when rains are reliable",
                    "Use shortest-duration varieties (60–90 days)",
                    "Concentrate inputs on best-managed portion of land",
                    "Water conservation: zai pits, mulching, tied ridges essential",
                    "Monitor for desert locusts during dry-wet transition",
                    "Post-harvest: store grain meticulously — food security depends on it",
                ],
                "dry": [
                    "☀️ LONG DRY SEASON (October–May): 7–8 months without rain",
                    "Practice irrigated gardening near water points",
                    "Livestock: Transhumance or provide fodder and water",
                    "Grain storage management — monthly inspection",
                    "Income diversification: trade, crafts, remittances",
                    "Plan and prepare inputs for next rainy season",
                ],
            },
        }

        region_advisories = advisories.get(region, {})
        return region_advisories.get(
            season,
            ["Consult local agricultural extension for seasonal guidance specific to your area."]
        )

    def _get_early_warning_indicators(self, region: str) -> List[str]:
        """Get early warning indicators for climate risks."""
        return [
            "📡 EARLY WARNING INDICATORS:",
            "Delayed onset of rains by more than 2 weeks — prepare for drought",
            "Erratic rainfall with long dry spells (>10 days) during growing season",
            "Heavy early rains followed by extended dry period — false start",
            "Increased pest populations (armyworm, locusts) after unusual weather",
            "Drying of water sources (wells, rivers) — indicator of drought",
            "Unusual bird migrations — can indicate weather changes",
            "Listen to local radio for meteorological forecasts and advisories",
            "Join farmer WhatsApp groups for real-time weather and pest alerts",
            "Contact local agricultural extension office for seasonal forecasts",
        ]

# ---------------------------------------------------------------------------
# Class: IrrigationAdvisor
# ---------------------------------------------------------------------------

class IrrigationAdvisor:
    """Irrigation advisory for African smallholder farmers.

    Provides guidance on irrigation methods, water management, and
    conservation techniques suitable for resource-constrained smallholders.
    """

    def __init__(self) -> None:
        """Initialize the IrrigationAdvisor with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.IrrigationAdvisor"
        )
        self._logger.info("IrrigationAdvisor initialized")

    # ------------------------------------------------------------------
    # Irrigation Method Selection
    # ------------------------------------------------------------------

    def get_irrigation_method(
        self,
        crop: str,
        land_size: float = 1.0,
        budget: str = "low",
    ) -> Dict[str, Any]:
        """Recommend irrigation methods based on crop, land size, and budget.

        Args:
            crop: Crop name.
            land_size: Land size in acres.
            budget: Budget level.

        Returns:
            Dictionary with irrigation recommendations.
        """
        crop_key = crop.lower().strip()
        budget_key = budget.lower().strip()

        methods = self._select_irrigation_methods(crop_key, land_size, budget_key)

        return {
            "crop": crop_key,
            "land_size_acres": land_size,
            "budget_level": budget_key,
            "recommended_methods": methods,
            "water_requirements": self._get_crop_water_needs(crop_key, land_size),
            "irrigation_schedule": self._get_irrigation_schedule(crop_key),
            "disclaimer": (
                "Irrigation recommendations depend on water availability, "
                "soil type, and local infrastructure. Adapt to your specific conditions."
            ),
        }

    def _select_irrigation_methods(
        self, crop: str, land_size: float, budget: str
    ) -> List[Dict[str, Any]]:
        """Select appropriate irrigation methods."""
        methods: List[Dict[str, Any]] = []

        if budget == "very_low":
            methods.extend([
                {
                    "method": "Bucket / Watering Can",
                    "suitability": "Vegetables, nurseries, up to 0.5 acres",
                    "cost_usd": "5–15 (bucket/can only)",
                    "pros": ["Very low cost", "Precise water placement", "No infrastructure needed"],
                    "cons": ["Labour intensive", "Limited area coverage", "Inefficient for large areas"],
                    "how_to": "Water at base of plants early morning or late afternoon. 2–5 litres per plant.",
                },
                {
                    "method": "Bottle Drip System (DIY)",
                    "suitability": "Vegetables, tree seedlings, row crops",
                    "cost_usd": "0 (recycled bottles)",
                    "pros": ["Zero cost", "Very efficient water use", "Reduces weed growth"],
                    "cons": ["Small scale only", "Requires regular refilling", "Can clog"],
                    "how_to": "Pierce small holes in plastic bottles, bury neck-down near plant roots. "
                              "Fill bottles manually. One 2L bottle serves one plant for 2–3 days.",
                },
                {
                    "method": "Clay Pot Irrigation",
                    "suitability": "Tree crops, vegetables, very dry areas",
                    "cost_usd": "5–20 (clay pots)",
                    "pros": ["Extremely water efficient", "No moving parts", "Gradual water release"],
                    "cons": ["Small scale", "Pots can break", "Labour to fill"],
                    "how_to": "Bury unglazed clay pot near plant with neck exposed. Fill with water. "
                              "Water seeps through porous walls directly to roots. Refill every 2–5 days.",
                },
            ])

        elif budget == "low":
            methods.extend([
                {
                    "method": "Treadle Pump",
                    "suitability": "Up to 2 acres, shallow water sources",
                    "cost_usd": "50–150",
                    "pros": ["No fuel needed", "2–3x more water than hand watering", "Reliable"],
                    "cons": ["Physical effort required", "Limited lift height (7m max)", "Maintenance needed"],
                    "how_to": "Place pump near water source. Connect hose or channel. "
                              "Operate foot pedals to pump water to field. Can irrigate 0.5–1 acre per day.",
                },
                {
                    "method": "Low-Cost Drip Kit",
                    "suitability": "Vegetables, up to 1 acre",
                    "cost_usd": "50–200",
                    "pros": ["40–60% water savings", "Reduced weed growth", "Higher yields"],
                    "cons": ["Initial cost", "Can clog without filtration", "Limited to row crops"],
                    "how_to": "Lay drip lines along crop rows. Connect to water source (tank or tap). "
                              "Use simple sand filter to prevent clogging. Check and flush lines weekly.",
                },
                {
                    "method": "Furrow Irrigation",
                    "suitability": "Row crops (maize, beans, cotton), up to 5 acres",
                    "cost_usd": "20–50 (labour for furrow construction)",
                    "pros": ["Low cost", "Suitable for grain crops", "Uses gravity"],
                    "cons": ["Less water efficient", "Can cause erosion", "Uneven water distribution"],
                    "how_to": "Create furrows between crop rows. Direct water from source into furrows. "
                              "Use siphon tubes or small channels. Monitor to prevent over-watering.",
                },
            ])

        elif budget == "medium":
            methods.extend([
                {
                    "method": "Motorized Pump (petrol/diesel)",
                    "suitability": "Up to 5 acres, various water sources",
                    "cost_usd": "200–800",
                    "pros": ["High water output", "Can lift from deep sources", "Fast irrigation"],
                    "cons": ["Fuel costs ongoing", "Maintenance required", "Noise and pollution"],
                    "how_to": "Install pump at water source. Connect to pipeline or sprinkler system. "
                              "Irrigate in early morning or evening to reduce evaporation losses.",
                },
                {
                    "method": "Sprinkler System (portable)",
                    "suitability": "Up to 3 acres, various crops",
                    "cost_usd": "300–1000",
                    "pros": ["Good coverage", "Simulates rainfall", "Suitable for many crops"],
                    "cons": ["Higher water use than drip", "Wind affects distribution", "Can promote fungal diseases"],
                    "how_to": "Set up portable sprinklers connected to pump. Move systematically across field. "
                              "Irrigate early morning to minimize evaporation and disease.",
                },
                {
                    "method": "Drip Irrigation (permanent)",
                    "suitability": "Up to 5 acres, vegetables, orchards",
                    "cost_usd": "300–1500",
                    "pros": ["50–70% water savings", "Higher yields", "Reduced disease", "Less weeding"],
                    "cons": ["Higher initial investment", "Requires filtration", "System maintenance"],
                    "how_to": "Install main line, sub-mains, and drip laterals. Use proper filtration. "
                              "Flush system monthly. Replace damaged emitters promptly.",
                },
            ])

        else:  # high budget
            methods.extend([
                {
                    "method": "Solar-Powered Drip Irrigation",
                    "suitability": "Up to 5 acres, any crop",
                    "cost_usd": "1500–5000",
                    "pros": ["No fuel costs", "Reliable", "Environmentally friendly", "Low operating cost"],
                    "cons": ["High initial investment", "Requires solar radiation", "Battery maintenance"],
                    "how_to": "Solar panels power submersible or surface pump. Connect to drip or sprinkler system. "
                              "Battery backup for cloudy days. Automatic controllers available.",
                },
                {
                    "method": "Center Pivot (shared)",
                    "suitability": "10+ acres (cooperative/shared)",
                    "cost_usd": "5000–15000 (shared among group)",
                    "pros": ["Highly efficient", "Large area coverage", "Automated"],
                    "cons": ["Very high cost", "Requires flat land", "Shared management"],
                    "how_to": "Cooperative purchase and management. Share costs and maintenance. "
                              "Suitable for flat, large fields. Program for crop-specific schedules.",
                },
            ])

        # Add rainwater harvesting recommendation for all budgets
        methods.append({
            "method": "Rainwater Harvesting",
            "suitability": "ALL farms — essential supplementary water source",
            "cost_usd": "20–500 depending on storage size",
            "pros": ["Free water", "Reduces dependency on other sources", "Improves water security"],
            "cons": ["Seasonal availability", "Storage space needed", "Initial construction cost"],
            "how_to": "Collect rooftop runoff into tanks or underground cisterns. "
                      "1,000 litre tank captures ~800 litres per 100mm rain on 10m² roof. "
                      "Also harvest runoff from compacted surfaces into farm ponds.",
        })

        return methods

    def _get_crop_water_needs(
        self, crop: str, land_size: float
    ) -> Dict[str, Any]:
        """Get water requirements for a crop."""
        water_needs: Dict[str, Dict[str, float]] = {
            "maize": {"mm_per_season": 500, "critical_stages": ["Flowering", "Grain filling"]},
            "rice": {"mm_per_season": 1200, "critical_stages": ["Tillering", "Flowering"]},
            "sorghum": {"mm_per_season": 400, "critical_stages": ["Booting", "Flowering"]},
            "millet": {"mm_per_season": 350, "critical_stages": ["Flowering", "Grain filling"]},
            "cassava": {"mm_per_season": 600, "critical_stages": ["Establishment", "Tuber initiation"]},
            "beans": {"mm_per_season": 350, "critical_stages": ["Flowering", "Pod filling"]},
            "groundnut": {"mm_per_season": 500, "critical_stages": ["Flowering", "Pod filling"]},
            "tomato": {"mm_per_season": 600, "critical_stages": ["Flowering", "Fruit set"]},
            "pepper": {"mm_per_season": 500, "critical_stages": ["Flowering", "Fruit development"]},
            "onion": {"mm_per_season": 400, "critical_stages": ["Bulbing"]},
            "cabbage": {"mm_per_season": 450, "critical_stages": ["Head formation"]},
            "cotton": {"mm_per_season": 700, "critical_stages": ["Flowering", "Boll development"]},
        }

        needs = water_needs.get(crop, {"mm_per_season": 500, "critical_stages": ["Flowering"]})
        litres_per_acre = needs["mm_per_season"] * 10 * 4047  # mm * 10 = m³/ha, * 4047 = per acre, * 1000 = litres

        return {
            "seasonal_water_need_mm": needs["mm_per_season"],
            "estimated_litres_per_acre_per_season": int(litres_per_acre / 1000),
            "critical_irrigation_stages": needs["critical_stages"],
            "notes": (
                "These are estimates. Actual needs vary with soil type, climate, "
                "and management. Critical stages require reliable moisture — "
                "water stress during these periods causes the greatest yield loss."
            ),
        }

    def _get_irrigation_schedule(self, crop: str) -> List[str]:
        """Get irrigation schedule recommendations."""
        schedules: Dict[str, List[str]] = {
            "maize": [
                "Weeks 1–2: Light, frequent irrigation to establish seedlings (every 2–3 days)",
                "Weeks 3–6: Irrigate every 5–7 days depending on rainfall",
                "CRITICAL — Weeks 7–10 (tasseling/silking): Irrigate every 3–4 days. Water stress causes 50%+ yield loss.",
                "Weeks 11–14 (grain filling): Irrigate every 5–7 days",
                "Final 2 weeks: Reduce irrigation. Dry field slightly before harvest.",
            ],
            "tomato": [
                "Establishment: Water daily or every 2 days for first 2 weeks",
                "Vegetative: Every 3–4 days",
                "CRITICAL — Flowering/fruit set: Every 2–3 days. Irregular watering causes blossom end rot.",
                "Fruit development: Every 3–4 days",
                "Reduce 1 week before harvest to concentrate flavours",
            ],
            "rice": [
                "Transplanting: Maintain 2–5cm water depth for first 2 weeks",
                "Tillering: 5–10cm water depth",
                "CRITICAL — Flowering: Maintain 5–10cm depth",
                "Grain filling: Gradually reduce to 2–5cm",
                "Drain field 2 weeks before harvest",
            ],
            "beans": [
                "Germination: Light, frequent watering",
                "Vegetative: Every 5–7 days",
                "CRITICAL — Flowering/pod filling: Every 3–5 days",
                "Avoid wetting foliage — promotes disease",
            ],
        }
        return schedules.get(crop, [
            "Establishment: Water frequently (every 2–3 days) for first 2–3 weeks",
            "Vegetative: Every 5–7 days depending on soil and weather",
            "Flowering/reproductive: Every 3–5 days — most critical period",
            "Maturity: Gradually reduce watering",
            "Early morning or late afternoon irrigation minimizes evaporation",
        ])

    # ------------------------------------------------------------------
    # Water Management
    # ------------------------------------------------------------------

    def get_water_management(self, region: str) -> Dict[str, Any]:
        """Get water management and conservation guidance for a region.

        Args:
            region: African region.

        Returns:
            Dictionary with water management strategies.
        """
        region_key = region.lower().strip().replace(" ", "_")

        return {
            "region": region_key,
            "water_sources": self._identify_water_sources(region_key),
            "conservation_techniques": [
                "Rooftop rainwater harvesting: Install gutters and direct to storage tanks",
                "Farm ponds: Excavate small ponds (5m x 5m x 2m) to capture runoff",
                "Sand dams: Build across seasonal sandy riverbeds to store water in aquifer",
                "Subsurface dams: Block groundwater flow with impermeable barrier",
                "Check dams: Small stone/concrete barriers across gullies to slow water and recharge groundwater",
                "Contour bunds: Slow runoff and increase infiltration",
                "Mulching: Reduces evaporation by 30–60%",
                "Deep tillage/ripping: Break hardpans to improve water infiltration",
                "Cover crops: Protect soil surface, improve infiltration",
                "Deficit irrigation: Apply less water than full requirement during less critical growth stages",
            ],
            "water_quality": [
                "Test water source for salinity (EC < 2 dS/m for most crops)",
                "Avoid using greywater on leafy vegetables",
                "Let muddy water settle before using for irrigation",
                "Protect water sources from livestock contamination",
                "Use sand filtration for drip irrigation systems",
            ],
            "disclaimer": (
                "Water management must comply with local water rights and regulations. "
                "Some techniques may require community coordination."
            ),
        }

    def _identify_water_sources(self, region: str) -> List[str]:
        """Identify typical water sources for a region."""
        sources: Dict[str, List[str]] = {
            "west_africa": [
                "Shallow wells (hand-dug, 5–15m depth)",
                "Streams and rivers (seasonal in north)",
                "Small reservoirs and farm ponds",
                "Boreholes (where groundwater is accessible)",
                "Rainwater harvesting from rooftops",
            ],
            "east_africa": [
                "Boreholes (common in arid areas)",
                "Shallow wells and springs (highland areas)",
                "Rivers and streams (seasonal in lowlands)",
                "Lake water (where applicable)",
                "Roof catchment and storage tanks",
                "Community water points",
            ],
            "southern_africa": [
                "Boreholes (primary source in dry areas)",
                "Dams and reservoirs",
                "Rivers (Limpopo, Zambezi tributaries)",
                "Farm ponds",
                "Rainwater harvesting",
            ],
            "sahel": [
                "Shallow wells (seasonal water table fluctuations)",
                "Boreholes (often deep, 30–100m)",
                "Seasonal rivers (wadis)",
                "Sand dams in seasonal riverbeds",
                "Hafirs (excavated reservoirs)",
                "Rainwater harvesting (limited by low rainfall)",
            ],
            "north_africa": [
                "Deep boreholes and wells",
                "Canal irrigation (Nile, Maghreb systems)",
                "Desalinated water (coastal areas)",
                "Treated wastewater (where permitted)",
                "Qanats/foggara (traditional systems where they exist)",
            ],
        }
        return sources.get(region, [
            "Shallow wells", "Boreholes", "Rivers and streams",
            "Rainwater harvesting", "Farm ponds",
        ])



# ---------------------------------------------------------------------------
# Class: FarmPlanner
# ---------------------------------------------------------------------------

class FarmPlanner:
    """Comprehensive farm planning and ROI calculation for African smallholders.

    Helps farmers create season plans, calculate returns on investment,
    and optimize resource allocation for maximum profitability.
    """

    def __init__(self) -> None:
        """Initialize the FarmPlanner with logging."""
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.FarmPlanner"
        )
        self._logger.info("FarmPlanner initialized")

    # ------------------------------------------------------------------
    # Farm Plan Creation
    # ------------------------------------------------------------------

    def create_farm_plan(
        self,
        land_size: float,
        region: str = "west_africa",
        budget: float = 500.0,
        goals: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a comprehensive farm plan based on land, region, budget, and goals.

        Args:
            land_size: Farm size in acres.
            region: African region.
            budget: Total budget in USD.
            goals: List of farmer goals (e.g., 'food_security', 'income', 'livestock').

        Returns:
            Dictionary with detailed farm plan.
        """
        region_key = region.lower().strip().replace(" ", "_")
        goals_list = goals or ["food_security", "income_generation"]

        # Determine optimal crop mix
        crop_mix = self._determine_crop_mix(land_size, region_key, budget, goals_list)

        # Calculate input requirements
        input_requirements = self._calculate_input_requirements(crop_mix, land_size)

        # Labour plan
        labour_plan = self._create_labour_plan(crop_mix, land_size)

        # Marketing plan
        marketing_plan = self._create_marketing_plan(crop_mix, region_key)

        # Risk management
        risk_management = self._create_risk_management_plan(region_key, crop_mix)

        return {
            "farm_summary": {
                "land_size_acres": land_size,
                "region": region_key,
                "total_budget_usd": budget,
                "budget_per_acre": round(budget / land_size, 2) if land_size > 0 else 0,
                "goals": goals_list,
            },
            "recommended_crop_mix": crop_mix,
            "input_requirements": input_requirements,
            "labour_plan": labour_plan,
            "marketing_plan": marketing_plan,
            "risk_management": risk_management,
            "seasonal_timeline": self._create_seasonal_timeline(crop_mix, region_key),
            "financial_projections": self._project_financials(crop_mix, land_size, budget),
            "record_keeping_template": {
                "date": "Activity date",
                "activity": "Planting, weeding, harvest, etc.",
                "crop": "Which crop",
                "labour_hours": "Hours spent",
                "labour_cost": "Cost of labour",
                "inputs_used": "Seeds, fertilizer, chemicals",
                "input_cost": "Cost of inputs",
                "yield_kg": "Harvest quantity",
                "sales_kg": "Quantity sold",
                "revenue": "Income from sales",
                "buyer": "Who bought the produce",
                "notes": "Observations, weather, issues",
            },
            "disclaimer": FINANCIAL_DISCLAIMER,
        }

    def _determine_crop_mix(
        self,
        land_size: float,
        region: str,
        budget: float,
        goals: List[str],
    ) -> List[Dict[str, Any]]:
        """Determine optimal crop mix for the farm."""
        crop_mix: List[Dict[str, Any]] = []

        budget_per_acre = budget / land_size if land_size > 0 else budget

        # Food security focus
        if "food_security" in goals:
            crop_mix.append({
                "crop": "maize",
                "area_acres": land_size * 0.3,
                "purpose": "Staple food for household consumption",
                "priority": "high",
                "rationale": "Maize is the staple cereal across most of Africa. Provides food security.",
            })
            crop_mix.append({
                "crop": "beans",
                "area_acres": land_size * 0.15,
                "purpose": "Protein source + nitrogen fixation",
                "priority": "high",
                "rationale": "Beans provide protein, fix nitrogen, and can be intercropped with maize.",
            })
            crop_mix.append({
                "crop": "cassava",
                "area_acres": land_size * 0.15,
                "purpose": "Drought reserve food security crop",
                "priority": "high",
                "rationale": "Cassava survives drought and provides food when other crops fail.",
            })

        # Income generation focus
        if "income_generation" in goals:
            if budget_per_acre >= 200:
                crop_mix.append({
                    "crop": "tomato",
                    "area_acres": land_size * 0.15,
                    "purpose": "High-value cash crop",
                    "priority": "high",
                    "rationale": "Tomatoes command high prices, especially off-season. High input but high return.",
                })
            crop_mix.append({
                "crop": "groundnut",
                "area_acres": land_size * 0.1,
                "purpose": "Cash crop + soil improvement",
                "priority": "medium",
                "rationale": "Groundnuts have consistent demand and improve soil through nitrogen fixation.",
            })

        # Livestock integration
        if "livestock" in goals:
            crop_mix.append({
                "crop": "sorghum",
                "area_acres": land_size * 0.1,
                "purpose": "Fodder and grain for livestock",
                "priority": "medium",
                "rationale": "Sorghum provides grain for feed and stover for fodder.",
            })
            crop_mix.append({
                "crop": "napier_grass",
                "area_acres": land_size * 0.05,
                "purpose": "Fodder bank for dairy/meat animals",
                "priority": "medium",
                "rationale": "Napier grass is high-yielding fodder for cattle, goats, and rabbits.",
            })

        # Diversification
        if "diversification" in goals or len(crop_mix) < 2:
            remaining = land_size - sum(c["area_acres"] for c in crop_mix)
            if remaining > land_size * 0.05:
                crop_mix.append({
                    "crop": "vegetables",
                    "area_acres": remaining,
                    "purpose": "Quick cash + dietary diversity",
                    "priority": "medium",
                    "rationale": "Vegetables mature quickly and provide regular income throughout the season.",
                })

        # Adjust for region
        crop_mix = self._adjust_for_region(crop_mix, region)

        # Normalize areas to total land size
        total_allocated = sum(c["area_acres"] for c in crop_mix)
        if total_allocated > 0 and abs(total_allocated - land_size) > 0.01:
            factor = land_size / total_allocated
            for c in crop_mix:
                c["area_acres"] = round(c["area_acres"] * factor, 2)

        return crop_mix

    def _adjust_for_region(
        self, crop_mix: List[Dict[str, Any]], region: str
    ) -> List[Dict[str, Any]]:
        """Adjust crop recommendations based on region."""
        if region == "sahel":
            # Replace maize with millet/sorghum, add cowpea
            for c in crop_mix:
                if c["crop"] == "maize":
                    c["crop"] = "millet"
                    c["rationale"] = "Millet is the most drought-tolerant cereal for the Sahel."
                if c["crop"] == "tomato":
                    c["crop"] = "onion"
                    c["rationale"] = "Onions store well and command premium prices in the Sahel."

        elif region == "north_africa":
            for c in crop_mix:
                if c["crop"] == "maize":
                    c["crop"] = "wheat"
                    c["rationale"] = "Wheat is the primary winter crop in North Africa."
                if c["crop"] == "cassava":
                    c["crop"] = "barley"
                    c["rationale"] = "Barley is drought-tolerant and used for feed and food."

        elif region == "east_africa" and any(c["crop"] == "maize" for c in crop_mix):
            # Add coffee/tea for highland areas
            pass  # Keep as-is, coffee requires specific altitude

        elif region == "central_africa":
            for c in crop_mix:
                if c["crop"] == "maize":
                    c["area_acres"] *= 0.8  # Reduce maize, add plantain

        return crop_mix

    def _calculate_input_requirements(
        self, crop_mix: List[Dict[str, Any]], land_size: float
    ) -> Dict[str, Any]:
        """Calculate input requirements for the crop mix."""
        total_seed_cost = 0.0
        total_fertilizer_cost = 0.0
        total_labour_days = 0
        input_details: List[Dict[str, Any]] = []

        for crop_plan in crop_mix:
            crop = crop_plan["crop"]
            area = crop_plan["area_acres"]
            crop_data = CROPS.get(crop, {})

            if not crop_data:
                continue

            # Seed requirement
            seed_rate_ha = crop_data.get("seed_rate_kg_per_ha", 0)
            seed_needed_kg = seed_rate_ha * area * 0.4047
            seed_cost = seed_needed_kg * 2.0  # ~$2/kg average

            # Fertilizer
            npk = crop_data.get("fertilizer_npk", "NPK")
            fertilizer_cost = area * 30  # ~$30/acre average

            # Labour
            labour_days = area * 15  # ~15 days/acre/season

            total_seed_cost += seed_cost
            total_fertilizer_cost += fertilizer_cost
            total_labour_days += int(labour_days)

            input_details.append({
                "crop": crop,
                "area_acres": area,
                "seed_needed_kg": round(seed_needed_kg, 1),
                "seed_cost_usd": round(seed_cost, 2),
                "fertilizer_npk": npk,
                "fertilizer_cost_usd": round(fertilizer_cost, 2),
                "labour_days": int(labour_days),
            })

        return {
            "input_details": input_details,
            "total_seed_cost_usd": round(total_seed_cost, 2),
            "total_fertilizer_cost_usd": round(total_fertilizer_cost, 2),
            "total_labour_days": total_labour_days,
            "estimated_labour_cost_usd": total_labour_days * 3,  # $3/day
            "other_costs_usd": {
                "pesticides": round(land_size * 15, 2),
                "tools_equipment": round(land_size * 5, 2),
                "transport": round(land_size * 10, 2),
            },
        }

    def _create_labour_plan(
        self, crop_mix: List[Dict[str, Any]], land_size: float
    ) -> Dict[str, Any]:
        """Create a labour calendar for the farm."""
        return {
            "peak_labour_periods": [
                "Land preparation: 2–3 weeks before planting",
                "Planting: 1–2 weeks (time-critical, especially for rain-fed crops)",
                "First weeding: 2–4 weeks after planting",
                "Second weeding: 6–8 weeks after planting",
                "Harvest: 1–3 weeks depending on crop mix",
                "Post-harvest processing: 2–4 weeks",
            ],
            "labour_sources": [
                "Family labour (primary source for smallholders)",
                "Hired labour for peak periods (planting, weeding, harvest)",
                "Exchange labour groups (neighbours helping each other)",
                "Youth groups for manual tasks",
            ],
            "labour_saving_tips": [
                "Stagger planting dates to spread labour demand",
                "Use herbicides for initial weed control (carefully follow labels)",
                "Mechanize land preparation where possible (tractor hire)",
                "Form labour-sharing groups with neighbouring farmers",
                "Hire labour early — rates increase during peak demand periods",
            ],
            "estimated_total_labour_days": int(land_size * 20),
        }

    def _create_marketing_plan(
        self, crop_mix: List[Dict[str, Any]], region: str
    ) -> List[str]:
        """Create a marketing plan for the farm's produce."""
        crops = [c["crop"] for c in crop_mix]
        return [
            "Pre-season: Identify 2–3 potential buyers for each crop",
            "During season: Maintain produce quality — grade, clean, and package well",
            "Harvest timing: Monitor market prices and sell during price peaks",
            "Storage strategy: Store grains and sell during lean season (30–60% price premium)",
            "Direct sales: Sell directly to consumers, restaurants, or institutions when possible",
            "Group marketing: Join farmer groups for collective bargaining power",
            "Value addition: Process surplus into higher-value products",
            "Record keeping: Track all sales, buyers, and prices for future planning",
        ]

    def _create_risk_management_plan(
        self, region: str, crop_mix: List[Dict[str, Any]]
    ) -> List[str]:
        """Create a risk management plan."""
        risks = [
            "WEATHER RISK: Diversify crop maturity dates. Mix early and late varieties.",
            "DROUGHT RISK: Include drought-tolerant crops (cassava, sorghum, millet).",
            "PEST RISK: Scout fields weekly. Have control measures ready.",
            "PRICE RISK: Store grain and sell during off-season price peaks.",
            "DISEASE RISK: Use certified seeds. Practice crop rotation.",
            "LABOUR RISK: Plan labour needs in advance. Form labour-sharing groups.",
            "FINANCIAL RISK: Keep emergency fund (10–20% of budget).",
            "MARKET ACCESS: Build relationships with multiple buyers.",
        ]

        if region in ["sahel", "horn_of_africa"]:
            risks.insert(0, "🔴 HIGH DROUGHT RISK: Have contingency plan for total crop failure.")
            risks.append("LIVESTOCK BUFFER: Keep small livestock as insurance against crop failure.")

        if region in ["central_africa"]:
            risks.append("FLOOD RISK: Plant on raised beds in flood-prone areas.")

        return risks

    def _create_seasonal_timeline(
        self, crop_mix: List[Dict[str, Any]], region: str
    ) -> List[Dict[str, Any]]:
        """Create a seasonal activity timeline."""
        timeline = []

        # Add generic timeline (region-specific would be more detailed)
        timeline.append({
            "period": "Pre-season (1–2 months before rains)",
            "activities": [
                "Plan crop mix and allocate land",
                "Purchase inputs (seeds, fertilizer, tools)",
                "Arrange labour for land preparation",
                "Repair storage structures",
                "Identify buyers and markets",
            ],
        })
        timeline.append({
            "period": "Land preparation (2–3 weeks before planting)",
            "activities": [
                "Clear land and remove previous crop residues",
                "Plough and harrow (or practice minimum tillage)",
                "Form ridges, mounds, or raised beds as needed",
                "Apply basal fertilizer and manure",
                "Prepare planting materials (seeds, cuttings)",
            ],
        })
        timeline.append({
            "period": "Planting (with first reliable rains)",
            "activities": [
                "Plant all crops according to plan",
                "Apply seed dressing if available",
                "Water transplanted seedlings immediately",
                "Apply mulch where available",
            ],
        })
        timeline.append({
            "period": "Early growth (Weeks 2–6)",
            "activities": [
                "First weeding (critical — weed-free first 6 weeks)",
                "Thin seedlings to correct spacing",
                "Top-dress with nitrogen fertilizer",
                "Monitor for pests and diseases",
                "Repair any gaps (replant if needed)",
            ],
        })
        timeline.append({
            "period": "Mid-season (Weeks 7–12)",
            "activities": [
                "Second weeding",
                "Pest and disease control as needed",
                "Supplementary irrigation if available",
                "Side-dress fertilizer for heavy feeders",
                "Support/stake crops like tomatoes",
            ],
        })
        timeline.append({
            "period": "Late season / Harvest (Weeks 12–20+)",
            "activities": [
                "Monitor maturity indicators",
                "Arrange harvest labour and transport",
                "Harvest at optimal maturity",
                "Sort, grade, and clean produce",
                "Begin post-harvest processing",
            ],
        })
        timeline.append({
            "period": "Post-harvest",
            "activities": [
                "Dry and store grains properly",
                "Process perishables quickly",
                "Market produce strategically",
                "Store seeds for next season",
                "Record yields, sales, and lessons learned",
                "Plan next season based on this season's results",
            ],
        })

        return timeline

    def _project_financials(
        self,
        crop_mix: List[Dict[str, Any]],
        land_size: float,
        budget: float,
    ) -> Dict[str, Any]:
        """Project financial outcomes for the farm plan."""
        total_revenue = 0.0
        total_costs = budget
        crop_financials: List[Dict[str, Any]] = []

        for crop_plan in crop_mix:
            crop = crop_plan["crop"]
            area = crop_plan["area_acres"]
            crop_data = CROPS.get(crop, {})

            if not crop_data:
                continue

            # Yield estimate
            avg_yield_tons_ha = sum(crop_data.get("yield_tons_per_ha", (1, 3))) / 2
            yield_tons = avg_yield_tons_ha * area * 0.4047
            yield_kg = yield_tons * 1000

            # Price estimate
            price_data = MARKET_PRICES.get(crop, {"farm_gate_min": 0.2, "farm_gate_max": 0.5})
            avg_price = (price_data["farm_gate_min"] + price_data["farm_gate_max"]) / 2

            revenue = yield_kg * avg_price
            crop_cost = area * (budget / land_size) if land_size > 0 else 0
            profit = revenue - crop_cost

            total_revenue += revenue

            crop_financials.append({
                "crop": crop,
                "area_acres": area,
                "expected_yield_kg": int(yield_kg),
                "price_usd_per_kg": round(avg_price, 2),
                "expected_revenue_usd": round(revenue, 2),
                "allocated_cost_usd": round(crop_cost, 2),
                "estimated_profit_usd": round(profit, 2),
            })

        net_profit = total_revenue - total_costs
        roi = (net_profit / total_costs * 100) if total_costs > 0 else 0

        return {
            "crop_projections": crop_financials,
            "total_expected_revenue_usd": round(total_revenue, 2),
            "total_expected_costs_usd": round(total_costs, 2),
            "net_profit_usd": round(net_profit, 2),
            "roi_percent": round(roi, 1),
            "notes": (
                "These are projections based on average yields and prices. "
                "Actual results vary with weather, management, and market conditions. "
                "Best-case scenario (good weather, high prices): +50% above projections. "
                "Worst-case scenario (drought, low prices): -50% below projections."
            ),
        }

    # ------------------------------------------------------------------
    # ROI Calculation
    # ------------------------------------------------------------------

    def calculate_roi(
        self,
        crop: str,
        land_size: float,
        input_costs: float,
    ) -> ROIEstimate:
        """Calculate return on investment for a specific crop enterprise.

        Args:
            crop: Crop name.
            land_size: Land size in acres.
            input_costs: Total input costs in USD.

        Returns:
            ROIEstimate dataclass with detailed projections.
        """
        crop_key = crop.lower().strip()
        crop_data = CROPS.get(crop_key)

        if not crop_data:
            raise ValueError(f"Unknown crop: {crop}. Available: {', '.join(sorted(CROPS.keys()))}")

        # Calculate expected yield
        avg_yield_tons_ha = sum(crop_data["yield_tons_per_ha"]) / 2
        # Smallholder management factor (70% of research station yield)
        smallholder_factor = 0.7
        expected_yield_tons = avg_yield_tons_ha * land_size * 0.4047 * smallholder_factor
        expected_yield_kg = expected_yield_tons * 1000

        # Price
        price_data = MARKET_PRICES.get(crop_key, {"farm_gate_min": 0.2, "farm_gate_max": 0.5})
        expected_price = (price_data["farm_gate_min"] + price_data["farm_gate_max"]) / 2

        # Conservative and optimistic scenarios
        conservative_yield = expected_yield_kg * 0.6
        optimistic_yield = expected_yield_kg * 1.3

        expected_revenue = expected_yield_kg * expected_price
        net_profit = expected_revenue - input_costs
        roi_pct = (net_profit / input_costs * 100) if input_costs > 0 else 0
        break_even_kg = input_costs / expected_price if expected_price > 0 else 0

        risk_factors = self._identify_risk_factors(crop_key)

        return ROIEstimate(
            crop=crop_data["name"],
            land_size_acres=land_size,
            input_costs=input_costs,
            expected_yield_kg=round(expected_yield_kg, 0),
            expected_price_per_kg=round(expected_price, 2),
            expected_revenue=round(expected_revenue, 2),
            net_profit=round(net_profit, 2),
            roi_percentage=round(roi_pct, 1),
            break_even_yield_kg=round(break_even_kg, 0),
            risk_factors=risk_factors,
        )

    def _identify_risk_factors(self, crop: str) -> List[str]:
        """Identify risk factors for a crop."""
        factors = []

        crop_data = CROPS.get(crop, {})
        if crop_data.get("drought_tolerance") in ["low", "very_low"]:
            factors.append("Drought sensitivity — yield highly dependent on rainfall timing")
        if crop_data.get("drought_tolerance") == "moderate":
            factors.append("Moderate drought tolerance — water stress during flowering reduces yield")

        common_pests = crop_data.get("common_pests", [])
        if "fall_armyworm" in common_pests or "armyworm" in common_pests:
            factors.append("Fall Armyworm risk — can cause 30–100% yield loss if uncontrolled")
        if len(common_pests) > 3:
            factors.append("Multiple pest species require active management")

        if crop in ["tomato", "pepper", "cabbage"]:
            factors.append("Perishable — requires quick marketing or processing")
            factors.append("Higher input costs (fertilizer, pesticides) than cereal crops")

        if crop in ["cocoa", "coffee", "mango"]:
            factors.append("Long establishment period (2–4 years) before first income")
            factors.append("Long-term investment with delayed returns")

        factors.append("Market price volatility — prices vary 30–80% between seasons")
        factors.append("Weather variability — climate change increasing uncertainty")

        return factors

# ---------------------------------------------------------------------------
# Class: FarmDatabaseManager
# ---------------------------------------------------------------------------

class FarmDatabaseManager:
    """SQLite database manager for tracking farm records.

    Provides persistent storage for farm activities, expenses,
    income, and observations. Enables data-driven decision making
    and performance tracking over time.
    """

    def __init__(self, db_path: str = "farm_records.db") -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to SQLite database file.
                        Use ':memory:' for in-memory (testing only).
        """
        self._db_path: str = db_path
        self._logger: logging.Logger = logging.getLogger(
            "luqi_agri_advisor.FarmDatabaseManager"
        )
        # For in-memory databases, keep a persistent connection so that
        # tables created in _init_database remain available for subsequent
        # operations (each new sqlite3.connect(':memory:') creates a fresh DB).
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(db_path)
            self._persistent_conn.row_factory = sqlite3.Row
        self._init_database()
        self._logger.info("FarmDatabaseManager initialized with DB: %s", db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection.

        Returns:
            sqlite3.Connection — a new connection for file-backed databases,
            or the persistent connection for ':memory:'.
        """
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialize database tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Farm records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS farm_records (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        farm_name TEXT NOT NULL,
                        activity_type TEXT NOT NULL,
                        crop_or_animal TEXT,
                        date TEXT NOT NULL,
                        details TEXT,
                        quantity REAL,
                        unit TEXT,
                        cost REAL,
                        revenue REAL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Crop performance table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS crop_performance (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        farm_name TEXT NOT NULL,
                        crop TEXT NOT NULL,
                        season TEXT NOT NULL,
                        year INTEGER NOT NULL,
                        area_acres REAL,
                        seed_variety TEXT,
                        planting_date TEXT,
                        harvest_date TEXT,
                        yield_kg REAL,
                        revenue_usd REAL,
                        input_costs_usd REAL,
                        profit_usd REAL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Livestock records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS livestock_records (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        farm_name TEXT NOT NULL,
                        animal_type TEXT NOT NULL,
                        animal_id TEXT,
                        birth_date TEXT,
                        breed TEXT,
                        sex TEXT,
                        acquisition_date TEXT,
                        acquisition_cost REAL,
                        sale_date TEXT,
                        sale_price REAL,
                        death_date TEXT,
                        death_cause TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Weather observations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS weather_observations (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        farm_name TEXT NOT NULL,
                        date TEXT NOT NULL,
                        rainfall_mm REAL,
                        max_temp_c REAL,
                        min_temp_c REAL,
                        humidity_percent REAL,
                        wind_speed REAL,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()
                self._logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            self._logger.error("Database initialization error: %s", e)
            raise

    # ------------------------------------------------------------------
    # Farm Records CRUD
    # ------------------------------------------------------------------

    def add_farm_record(self, record: FarmRecord) -> int:
        """Add a farm activity record.

        Args:
            record: FarmRecord dataclass instance.

        Returns:
            ID of the inserted record.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO farm_records
                    (farm_name, activity_type, crop_or_animal, date, details,
                     quantity, unit, cost, revenue, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.farm_name, record.activity_type, record.crop_or_animal,
                    record.date, record.details, record.quantity, record.unit,
                    record.cost, record.revenue, record.notes,
                ))
                conn.commit()
                record_id = cursor.lastrowid
                self._logger.info("Added farm record ID: %d", record_id)
                return record_id if record_id is not None else 0
        except sqlite3.Error as e:
            self._logger.error("Error adding farm record: %s", e)
            raise

    def get_farm_records(
        self,
        farm_name: Optional[str] = None,
        activity_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve farm records with optional filtering.

        Args:
            farm_name: Filter by farm name.
            activity_type: Filter by activity type.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            limit: Maximum records to return.

        Returns:
            List of farm records as dictionaries.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM farm_records WHERE 1=1"
                params: List[Any] = []

                if farm_name:
                    query += " AND farm_name = ?"
                    params.append(farm_name)
                if activity_type:
                    query += " AND activity_type = ?"
                    params.append(activity_type)
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)

                query += " ORDER BY date DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except sqlite3.Error as e:
            self._logger.error("Error retrieving farm records: %s", e)
            return []

    def get_financial_summary(
        self,
        farm_name: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get financial summary for a farm.

        Args:
            farm_name: Farm name.
            year: Filter by year.

        Returns:
            Dictionary with financial summary.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                base_query = "FROM farm_records WHERE 1=1"
                params: List[Any] = []

                if farm_name:
                    base_query += " AND farm_name = ?"
                    params.append(farm_name)
                if year:
                    base_query += " AND strftime('%Y', date) = ?"
                    params.append(str(year))

                cursor.execute(f"SELECT COALESCE(SUM(cost), 0) {base_query}", params)
                total_costs = cursor.fetchone()[0]

                cursor.execute(f"SELECT COALESCE(SUM(revenue), 0) {base_query}", params)
                total_revenue = cursor.fetchone()[0]

                cursor.execute(f"SELECT COUNT(*) {base_query}", params)
                record_count = cursor.fetchone()[0]

                cursor.execute(f"""
                    SELECT activity_type, COALESCE(SUM(cost), 0) as total_cost,
                           COALESCE(SUM(revenue), 0) as total_revenue
                    {base_query}
                    GROUP BY activity_type
                """, params)
                by_activity = [dict(row) for row in cursor.fetchall()]

                return {
                    "total_costs_usd": round(total_costs, 2),
                    "total_revenue_usd": round(total_revenue, 2),
                    "net_profit_usd": round(total_revenue - total_costs, 2),
                    "record_count": record_count,
                    "breakdown_by_activity": by_activity,
                }

        except sqlite3.Error as e:
            self._logger.error("Error getting financial summary: %s", e)
            return {"total_costs_usd": 0, "total_revenue_usd": 0, "net_profit_usd": 0, "record_count": 0, "breakdown_by_activity": []}

    # ------------------------------------------------------------------
    # Crop Performance Tracking
    # ------------------------------------------------------------------

    def record_crop_performance(
        self,
        farm_name: str,
        crop: str,
        season: str,
        year: int,
        area_acres: float,
        seed_variety: str = "",
        planting_date: str = "",
        harvest_date: str = "",
        yield_kg: float = 0.0,
        revenue_usd: float = 0.0,
        input_costs_usd: float = 0.0,
        notes: str = "",
    ) -> int:
        """Record crop performance data.

        Args:
            farm_name: Farm name.
            crop: Crop name.
            season: Season name.
            year: Year.
            area_acres: Area planted in acres.
            seed_variety: Seed variety used.
            planting_date: Planting date (YYYY-MM-DD).
            harvest_date: Harvest date (YYYY-MM-DD).
            yield_kg: Yield in kilograms.
            revenue_usd: Revenue in USD.
            input_costs_usd: Input costs in USD.
            notes: Additional notes.

        Returns:
            Record ID.
        """
        profit = revenue_usd - input_costs_usd
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO crop_performance
                    (farm_name, crop, season, year, area_acres, seed_variety,
                     planting_date, harvest_date, yield_kg, revenue_usd,
                     input_costs_usd, profit_usd, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    farm_name, crop, season, year, area_acres, seed_variety,
                    planting_date, harvest_date, yield_kg, revenue_usd,
                    input_costs_usd, profit, notes,
                ))
                conn.commit()
                record_id = cursor.lastrowid
                self._logger.info("Recorded crop performance ID: %d", record_id)
                return record_id if record_id is not None else 0
        except sqlite3.Error as e:
            self._logger.error("Error recording crop performance: %s", e)
            raise

    def get_crop_performance_summary(
        self,
        farm_name: Optional[str] = None,
        crop: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get crop performance summary.

        Args:
            farm_name: Farm name.
            crop: Crop name.

        Returns:
            List of crop performance summaries.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT crop,
                           COUNT(*) as seasons,
                           AVG(yield_kg) as avg_yield_kg,
                           AVG(profit_usd) as avg_profit_usd,
                           MAX(profit_usd) as best_profit_usd,
                           MIN(profit_usd) as worst_profit_usd
                    FROM crop_performance WHERE 1=1
                """
                params: List[Any] = []

                if farm_name:
                    query += " AND farm_name = ?"
                    params.append(farm_name)
                if crop:
                    query += " AND crop = ?"
                    params.append(crop)

                query += " GROUP BY crop ORDER BY avg_profit_usd DESC"

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            self._logger.error("Error getting crop performance: %s", e)
            return []

    # ------------------------------------------------------------------
    # Livestock Records
    # ------------------------------------------------------------------

    def add_livestock_record(
        self,
        farm_name: str,
        animal_type: str,
        animal_id: str = "",
        birth_date: str = "",
        breed: str = "",
        sex: str = "",
        acquisition_date: str = "",
        acquisition_cost: float = 0.0,
        notes: str = "",
    ) -> int:
        """Add a livestock record.

        Args:
            farm_name: Farm name.
            animal_type: Type of animal.
            animal_id: Unique animal identifier.
            birth_date: Birth date.
            breed: Breed.
            sex: Sex.
            acquisition_date: Date acquired.
            acquisition_cost: Cost of acquisition.
            notes: Notes.

        Returns:
            Record ID.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO livestock_records
                    (farm_name, animal_type, animal_id, birth_date, breed, sex,
                     acquisition_date, acquisition_cost, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    farm_name, animal_type, animal_id, birth_date, breed, sex,
                    acquisition_date, acquisition_cost, notes,
                ))
                conn.commit()
                record_id = cursor.lastrowid
                self._logger.info("Added livestock record ID: %d", record_id)
                return record_id if record_id is not None else 0
        except sqlite3.Error as e:
            self._logger.error("Error adding livestock record: %s", e)
            raise

    def get_livestock_inventory(
        self,
        farm_name: Optional[str] = None,
        animal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get livestock inventory summary.

        Args:
            farm_name: Farm name.
            animal_type: Animal type filter.

        Returns:
            Inventory summary.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT animal_type,
                           COUNT(*) as total,
                           SUM(CASE WHEN death_date IS NULL THEN 1 ELSE 0 END) as alive,
                           SUM(CASE WHEN death_date IS NOT NULL THEN 1 ELSE 0 END) as dead,
                           SUM(CASE WHEN sale_date IS NOT NULL THEN 1 ELSE 0 END) as sold,
                           SUM(acquisition_cost) as total_investment
                    FROM livestock_records WHERE 1=1
                """
                params: List[Any] = []

                if farm_name:
                    query += " AND farm_name = ?"
                    params.append(farm_name)
                if animal_type:
                    query += " AND animal_type = ?"
                    params.append(animal_type)

                query += " GROUP BY animal_type"

                cursor.execute(query, params)
                return {
                    "inventory": [dict(row) for row in cursor.fetchall()],
                    "disclaimer": MEDICAL_DISCLAIMER,
                }

        except sqlite3.Error as e:
            self._logger.error("Error getting livestock inventory: %s", e)
            return {"inventory": [], "disclaimer": MEDICAL_DISCLAIMER}

    # ------------------------------------------------------------------
    # Weather Observations
    # ------------------------------------------------------------------

    def record_weather(
        self,
        farm_name: str,
        date: str,
        rainfall_mm: float = 0.0,
        max_temp_c: float = 0.0,
        min_temp_c: float = 0.0,
        humidity_percent: float = 0.0,
        wind_speed: float = 0.0,
        notes: str = "",
    ) -> int:
        """Record weather observation.

        Args:
            farm_name: Farm name.
            date: Date (YYYY-MM-DD).
            rainfall_mm: Rainfall in mm.
            max_temp_c: Maximum temperature in Celsius.
            min_temp_c: Minimum temperature in Celsius.
            humidity_percent: Humidity percentage.
            wind_speed: Wind speed.
            notes: Notes.

        Returns:
            Record ID.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO weather_observations
                    (farm_name, date, rainfall_mm, max_temp_c, min_temp_c,
                     humidity_percent, wind_speed, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    farm_name, date, rainfall_mm, max_temp_c, min_temp_c,
                    humidity_percent, wind_speed, notes,
                ))
                conn.commit()
                record_id = cursor.lastrowid
                return record_id if record_id is not None else 0
        except sqlite3.Error as e:
            self._logger.error("Error recording weather: %s", e)
            raise

    def get_weather_summary(
        self,
        farm_name: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Get weather summary for a period.

        Args:
            farm_name: Farm name.
            start_date: Start date.
            end_date: End date.

        Returns:
            Weather summary.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(rainfall_mm), 0) as total_rainfall,
                        COALESCE(AVG(max_temp_c), 0) as avg_max_temp,
                        COALESCE(AVG(min_temp_c), 0) as avg_min_temp,
                        COUNT(*) as observation_days
                    FROM weather_observations
                    WHERE farm_name = ? AND date BETWEEN ? AND ?
                """, (farm_name, start_date, end_date))

                row = cursor.fetchone()
                return {
                    "period": f"{start_date} to {end_date}",
                    "total_rainfall_mm": round(row[0], 1),
                    "average_max_temp_c": round(row[1], 1),
                    "average_min_temp_c": round(row[2], 1),
                    "observation_days": row[3],
                }

        except sqlite3.Error as e:
            self._logger.error("Error getting weather summary: %s", e)
            return {}

    def export_to_json(self, farm_name: Optional[str] = None) -> str:
        """Export all records to JSON string.

        Args:
            farm_name: Optional farm name filter.

        Returns:
            JSON string of all records.
        """
        try:
            data: Dict[str, Any] = {
                "farm_records": self.get_farm_records(farm_name=farm_name, limit=10000),
                "crop_performance": [],
                "livestock_records": [],
                "weather_observations": [],
            }

            with self._get_connection() as conn:
                cursor = conn.cursor()

                if farm_name:
                    cursor.execute("SELECT * FROM crop_performance WHERE farm_name = ?", (farm_name,))
                else:
                    cursor.execute("SELECT * FROM crop_performance")
                data["crop_performance"] = [dict(row) for row in cursor.fetchall()]

                if farm_name:
                    cursor.execute("SELECT * FROM livestock_records WHERE farm_name = ?", (farm_name,))
                else:
                    cursor.execute("SELECT * FROM livestock_records")
                data["livestock_records"] = [dict(row) for row in cursor.fetchall()]

                if farm_name:
                    cursor.execute("SELECT * FROM weather_observations WHERE farm_name = ?", (farm_name,))
                else:
                    cursor.execute("SELECT * FROM weather_observations")
                data["weather_observations"] = [dict(row) for row in cursor.fetchall()]

            return json.dumps(data, indent=2, default=str)

        except sqlite3.Error as e:
            self._logger.error("Error exporting data: %s", e)
            return "{}"



# ---------------------------------------------------------------------------
# Module-Level Convenience Functions
# ---------------------------------------------------------------------------

"""Convenience functions for quick access to advisory services.

These functions provide a simple, unified interface to the advisory system
without requiring direct class instantiation. They are suitable for:
    - Command-line usage
    - Simple scripts
    - API endpoints
    - Chatbot integrations

Each function returns a structured dictionary that can be serialized to JSON
or displayed to the user.

Examples:
    >>> result = farming_advice("How do I plant maize?", "west_africa", "maize")
    >>> print(result["advice"])

    >>> diagnosis = pest_diagnosis("tomato", "white insects on leaves")
    >>> print(diagnosis["matched_pests"])
"""


# Singleton instances for convenience functions
_crop_advisor: Optional[CropAdvisor] = None
_livestock_advisor: Optional[LivestockAdvisor] = None
_market_advisor: Optional[MarketAdvisor] = None
_climate_advisor: Optional[ClimateAdvisor] = None
_irrigation_advisor: Optional[IrrigationAdvisor] = None
_farm_planner: Optional[FarmPlanner] = None
_db_manager: Optional[FarmDatabaseManager] = None


def _get_crop_advisor() -> CropAdvisor:
    """Get or create singleton CropAdvisor instance."""
    global _crop_advisor
    if _crop_advisor is None:
        _crop_advisor = CropAdvisor()
    return _crop_advisor


def _get_livestock_advisor() -> LivestockAdvisor:
    """Get or create singleton LivestockAdvisor instance."""
    global _livestock_advisor
    if _livestock_advisor is None:
        _livestock_advisor = LivestockAdvisor()
    return _livestock_advisor


def _get_market_advisor() -> MarketAdvisor:
    """Get or create singleton MarketAdvisor instance."""
    global _market_advisor
    if _market_advisor is None:
        _market_advisor = MarketAdvisor()
    return _market_advisor


def _get_climate_advisor() -> ClimateAdvisor:
    """Get or create singleton ClimateAdvisor instance."""
    global _climate_advisor
    if _climate_advisor is None:
        _climate_advisor = ClimateAdvisor()
    return _climate_advisor


def _get_irrigation_advisor() -> IrrigationAdvisor:
    """Get or create singleton IrrigationAdvisor instance."""
    global _irrigation_advisor
    if _irrigation_advisor is None:
        _irrigation_advisor = IrrigationAdvisor()
    return _irrigation_advisor


def _get_farm_planner() -> FarmPlanner:
    """Get or create singleton FarmPlanner instance."""
    global _farm_planner
    if _farm_planner is None:
        _farm_planner = FarmPlanner()
    return _farm_planner


def _get_db_manager(db_path: str = "farm_records.db") -> FarmDatabaseManager:
    """Get or create singleton FarmDatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = FarmDatabaseManager(db_path)
    return _db_manager


def farming_advice(
    query: str,
    region: str = "west_africa",
    crop: Optional[str] = None,
) -> Dict[str, Any]:
    """Get general farming advice based on a natural language query.

    This function parses the query and routes it to the appropriate
    advisory service. It handles common farming questions about planting,
    pests, fertilization, harvesting, and general crop management.

    Args:
        query: Natural language query string.
        region: African region identifier.
        crop: Optional crop name for context-specific advice.

    Returns:
        Dictionary with advice and relevant information.

    Examples:
        >>> farming_advice("How do I plant maize?", "west_africa", "maize")
        >>> farming_advice("What fertilizer should I use for tomatoes?", "east_africa", "tomato")
        >>> farming_advice("When should I harvest my beans?", region="southern_africa", crop="beans")
    """
    query_lower = query.lower().strip()
    result: Dict[str, Any] = {
        "query": query,
        "region": region,
        "crop": crop,
        "disclaimer": GENERAL_DISCLAIMER,
    }

    try:
        # Route to appropriate advisor based on query keywords
        if any(kw in query_lower for kw in ["plant", "sow", "seed", "spacing", "when to plant", "how to grow"]):
            if crop:
                advisor = _get_crop_advisor()
                guide = advisor.get_planting_guide(crop, region)
                result["advice_type"] = "planting_guide"
                result["advice"] = guide
            else:
                result["advice_type"] = "general"
                result["advice"] = (
                    "To provide specific planting advice, please specify the crop you want to plant. "
                    "Available crops include: maize, cassava, rice, beans, groundnut, tomato, "
                    "pepper, onion, cabbage, and many more. Use the crop parameter."
                )

        elif any(kw in query_lower for kw in ["fertilizer", "manure", "npk", "nutrient", "feed the soil"]):
            if crop:
                advisor = _get_crop_advisor()
                guide = advisor.get_fertilizer_guide(crop, region)
                result["advice_type"] = "fertilizer_guide"
                result["advice"] = guide
            else:
                result["advice_type"] = "general"
                result["advice"] = (
                    "For fertilizer recommendations, please specify your crop. "
                    "General principle: Test soil if possible. Apply compost or well-rotted manure "
                    "as basal dressing. Use NPK fertilizer based on crop needs. Legumes need less "
                    "nitrogen (they fix their own). Cereals need nitrogen top-dressing at knee height."
                )

        elif any(kw in query_lower for kw in ["harvest", "when to harvest", "maturity", "ready to pick", "collect"]):
            if crop:
                advisor = _get_crop_advisor()
                guide = advisor.get_harvest_guide(crop)
                result["advice_type"] = "harvest_guide"
                result["advice"] = guide
            else:
                result["advice_type"] = "general"
                result["advice"] = (
                    "Harvest timing depends on the crop. General indicators: grains are hard and dry, "
                    "vegetables have reached full size and colour, roots have filled out. "
                    "Harvest during dry weather. Please specify your crop for detailed guidance."
                )

        elif any(kw in query_lower for kw in ["pest", "disease", "insect", "worm", "rot", "damage", "attack"]):
            if crop:
                # Extract symptoms from query
                symptoms = query_lower
                for kw in ["pest", "disease", "insect", "worm", "rot", "damage", "attack", "on my", "in my", "i see", "there are"]:
                    symptoms = symptoms.replace(kw, "")
                result.update(pest_diagnosis(crop, symptoms.strip()))
            else:
                result["advice_type"] = "general"
                result["advice"] = (
                    "For pest and disease identification, please specify the affected crop "
                    "and describe the symptoms you observe (colours, patterns, damage type, "
                    "location on plant). Early identification and treatment save crops."
                )

        elif any(kw in query_lower for kw in ["calendar", "when to plant", "season", "month"]):
            advisor = _get_crop_advisor()
            calendar = advisor.get_crop_calendar(region)
            result["advice_type"] = "crop_calendar"
            result["advice"] = calendar

        elif any(kw in query_lower for kw in ["animal", "cow", "goat", "chicken", "pig", "sheep", "rabbit", "livestock"]):
            result["advice_type"] = "livestock"
            result["advice"] = (
                "For detailed livestock advice, please use the livestock-specific functions: "
                "get_care_guide(), get_disease_symptoms(), get_feeding_guide(), or get_breeding_guide()."
            )

        elif any(kw in query_lower for kw in ["irrigation", "water", "drip", "sprinkle", "pump"]):
            advisor = _get_irrigation_advisor()
            if crop:
                guide = advisor.get_irrigation_method(crop)
                result["advice_type"] = "irrigation_guide"
                result["advice"] = guide
            else:
                water_mgmt = advisor.get_water_management(region)
                result["advice_type"] = "water_management"
                result["advice"] = water_mgmt

        elif any(kw in query_lower for kw in ["climate", "drought", "flood", "rain", "weather", "dry"]):
            advisor = _get_climate_advisor()
            if crop and "drought" in query_lower:
                guide = advisor.get_drought_resilience(crop)
                result["advice_type"] = "drought_resilience"
                result["advice"] = guide
            elif crop and "flood" in query_lower:
                guide = advisor.get_flood_adaptation(crop)
                result["advice_type"] = "flood_adaptation"
                result["advice"] = guide
            else:
                guide = advisor.get_weather_advisory(region)
                result["advice_type"] = "weather_advisory"
                result["advice"] = guide

        elif any(kw in query_lower for kw in ["soil", "terrace", "mulch", "cover crop", "agroforestry", "erosion", "conservation"]):
            advisor = _get_climate_advisor()
            method = "general"
            for m in ["terracing", "cover_crops", "agroforestry", "mulching", "contour", "compost"]:
                if m in query_lower:
                    method = m
                    break
            guide = advisor.get_soil_conservation(method)
            result["advice_type"] = "soil_conservation"
            result["advice"] = guide

        elif any(kw in query_lower for kw in ["market", "price", "sell", "buyer", "storage", "value addition"]):
            result.update(market_advice(crop or "maize", region))

        elif any(kw in query_lower for kw in ["plan", "budget", "roi", "profit", "farm plan"]):
            if crop:
                planner = _get_farm_planner()
                roi = planner.calculate_roi(crop, 1.0, 200.0)
                result["advice_type"] = "roi_estimate"
                result["advice"] = {
                    "crop": roi.crop,
                    "land_size_acres": roi.land_size_acres,
                    "input_costs": roi.input_costs,
                    "expected_yield_kg": roi.expected_yield_kg,
                    "expected_revenue": roi.expected_revenue,
                    "net_profit": roi.net_profit,
                    "roi_percent": roi.roi_percentage,
                    "break_even_yield_kg": roi.break_even_yield_kg,
                    "risk_factors": roi.risk_factors,
                }
            else:
                result["advice_type"] = "general"
                result["advice"] = (
                    "For farm planning and ROI calculations, please specify the crop and "
                    "use the farm_plan() function for comprehensive planning, or "
                    "provide land_size, budget, and goals parameters."
                )

        else:
            # General farming advice
            result["advice_type"] = "general"
            result["advice"] = (
                f"Welcome to Luqi AI Agricultural Advisor. I can help you with:\n\n"
                f"1. PLANTING: When and how to plant specific crops\n"
                f"2. PEST CONTROL: Identify and treat pests and diseases\n"
                f"3. FERTILIZER: Recommendations for soil nutrition\n"
                f"4. HARVESTING: When and how to harvest your crops\n"
                f"5. LIVESTOCK: Care, feeding, and health management\n"
                f"6. MARKETS: Price trends, buyers, and value addition\n"
                f"7. CLIMATE: Drought resilience, flood adaptation, weather advisories\n"
                f"8. IRRIGATION: Water management techniques\n"
                f"9. FARM PLANNING: Comprehensive farm plans and ROI calculations\n\n"
                f"Please ask a more specific question or specify your crop and region "
                f"for targeted advice. Your current region is set to: {region}"
            )

    except Exception as e:
        result["advice_type"] = "error"
        result["advice"] = f"An error occurred: {str(e)}. Please try again with more specific details."
        logger.error("Error in farming_advice: %s", e, exc_info=True)

    return result


def pest_diagnosis(
    crop: str,
    symptoms: str,
) -> Dict[str, Any]:
    """Diagnose pests and diseases based on crop and symptoms.

    This function provides quick pest/disease identification and
    treatment recommendations for affected crops.

    Args:
        crop: Affected crop name.
        symptoms: Description of observed symptoms.

    Returns:
        Dictionary with pest identification and control measures.

    Examples:
        >>> pest_diagnosis("maize", "ragged holes in leaves, frass in whorl")
        >>> pest_diagnosis("tomato", "white insects on underside of leaves")
        >>> pest_diagnosis("cassava", "woolly white masses on stems, stunted growth")
    """
    try:
        advisor = _get_crop_advisor()
        result = advisor.get_pest_control(crop, symptoms)
        result["query_summary"] = f"Crop: {crop}, Symptoms: {symptoms}"
        return result
    except Exception as e:
        return {
            "crop": crop,
            "symptoms_reported": symptoms,
            "error": str(e),
            "disclaimer": (
                "Could not complete diagnosis. Please consult your local agricultural "
                "extension officer with photos or physical samples of the affected plants."
            ),
        }


def market_advice(
    commodity: str,
    region: str = "west_africa",
) -> Dict[str, Any]:
    """Get market guidance for a commodity.

    Provides price trends, buyer connections, storage advice, and
    value addition strategies for agricultural commodities.

    Args:
        commodity: Commodity name.
        region: African region.

    Returns:
        Dictionary with comprehensive market guidance.

    Examples:
        >>> market_advice("maize", "west_africa")
        >>> market_advice("tomato", "east_africa")
        >>> market_advice("cocoa", "west_africa")
    """
    try:
        advisor = _get_market_advisor()

        prices = advisor.get_price_trends(commodity, region)
        buyers = advisor.get_buyer_connections(commodity, region)
        storage = advisor.get_storage_advice(commodity)
        value_add = advisor.get_value_addition(commodity)

        return {
            "commodity": commodity,
            "region": region,
            "advice_type": "market_guidance",
            "price_trends": prices,
            "buyer_connections": buyers,
            "storage_advice": storage,
            "value_addition": value_add,
            "disclaimer": FINANCIAL_DISCLAIMER,
        }
    except Exception as e:
        return {
            "commodity": commodity,
            "region": region,
            "error": str(e),
            "disclaimer": FINANCIAL_DISCLAIMER,
        }


def farm_plan(
    land_size: float,
    region: str = "west_africa",
    budget: float = 500.0,
    goals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a comprehensive farm plan.

    Creates a detailed farm plan including crop mix, input requirements,
    labour planning, marketing strategy, risk management, and financial
    projections.

    Args:
        land_size: Farm size in acres.
        region: African region.
        budget: Total budget in USD.
        goals: List of goals (food_security, income_generation, livestock, diversification).

    Returns:
        Dictionary with comprehensive farm plan.

    Examples:
        >>> farm_plan(2.0, "west_africa", 800.0, ["food_security", "income_generation"])
        >>> farm_plan(5.0, "east_africa", 2000.0, ["income_generation", "diversification"])
        >>> farm_plan(1.0, "sahel", 300.0, ["food_security"])
    """
    try:
        planner = _get_farm_planner()
        return planner.create_farm_plan(land_size, region, budget, goals)
    except Exception as e:
        return {
            "error": str(e),
            "message": "Could not generate farm plan. Please check your parameters.",
            "disclaimer": FINANCIAL_DISCLAIMER,
        }


def livestock_advice(
    animal: str,
    topic: str = "care",
    symptoms: str = "",
    budget: str = "low",
) -> Dict[str, Any]:
    """Get livestock advice on a specific topic.

    Args:
        animal: Animal species (cattle, goats, sheep, chickens, pigs, rabbits).
        topic: Topic (care, disease, feeding, breeding).
        symptoms: Symptoms description (for disease topic).
        budget: Budget level (very_low, low, medium, high).

    Returns:
        Dictionary with livestock advice.

    Examples:
        >>> livestock_advice("chickens", "care")
        >>> livestock_advice("goats", "disease", "diarrhoea and lethargy")
        >>> livestock_advice("cattle", "feeding", budget="medium")
    """
    try:
        advisor = _get_livestock_advisor()

        if topic == "care":
            return advisor.get_care_guide(animal)
        elif topic == "disease":
            return advisor.get_disease_symptoms(animal, symptoms)
        elif topic == "feeding":
            return advisor.get_feeding_guide(animal, budget)
        elif topic == "breeding":
            return advisor.get_breeding_guide(animal)
        else:
            return {
                "error": f"Unknown topic '{topic}'. Available: care, disease, feeding, breeding",
            }
    except Exception as e:
        return {
            "animal": animal,
            "topic": topic,
            "error": str(e),
            "disclaimer": MEDICAL_DISCLAIMER,
        }


# ---------------------------------------------------------------------------
# Main Execution Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("Luqi AI v20 - Agricultural Advisor for Africa")
    print("=" * 70)
    print(f"Version: {__version__}")
    print(f"Author: {__author__}")
    print()
    print("This is a self-contained Python module. Import it in your scripts:")
    print()
    print("    from agricultural_advisor import (")
    print("        CropAdvisor, LivestockAdvisor, MarketAdvisor,")
    print("        ClimateAdvisor, IrrigationAdvisor, FarmPlanner,")
    print("        farming_advice, pest_diagnosis, market_advice, farm_plan,")
    print("    )")
    print()
    print("Or use the convenience functions directly:")
    print()
    print("    advice = farming_advice('How do I plant maize?', 'west_africa', 'maize')")
    print("    diagnosis = pest_diagnosis('tomato', 'white insects on leaves')")
    print("    plan = farm_plan(2.0, 'west_africa', 800.0)")
    print()
    print("-" * 70)
    print("Running demonstration...")
    print("-" * 70)
    print()

    # Demonstration
    print("[1] CROP ADVISOR — Planting Guide for Maize in West Africa")
    print("-" * 50)
    crop_advisor = CropAdvisor()
    maize_guide = crop_advisor.get_planting_guide("maize", "west_africa", "rainy")
    print(f"Crop: {maize_guide['crop']}")
    print(f"Region: {maize_guide['region']}")
    print(f"Spacing: {maize_guide['spacing']}")
    print(f"Steps ({len(maize_guide['steps'])}):")
    for step in maize_guide['steps'][:3]:
        print(f"  {step[:100]}...")
    print()

    print("[2] PEST DIAGNOSIS — Fall Armyworm on Maize")
    print("-" * 50)
    pest_result = pest_diagnosis("maize", "ragged holes in leaves, frass in whorl, green caterpillars")
    if pest_result.get("matched_pests"):
        top = pest_result["matched_pests"][0]
        print(f"Pest: {top['pest_name']}")
        print(f"Severity: {top['severity']}")
        print(f"Organic control: {top['organic_control'][0][:80]}...")
    print()

    print("[3] MARKET ADVISOR — Maize Price Trends in West Africa")
    print("-" * 50)
    market_result = market_advice("maize", "west_africa")
    prices = market_result.get("price_trends", {})
    if "price_indicative_usd_per_kg" in prices:
        p = prices["price_indicative_usd_per_kg"]
        print(f"Farm gate: ${p['farm_gate_min']:.2f} - ${p['farm_gate_max']:.2f} per kg")
        print(f"Market: ${p['market_min']:.2f} - ${p['market_max']:.2f} per kg")
    print()

    print("[4] CLIMATE ADVISOR — Drought Resilience for Maize")
    print("-" * 50)
    climate_advisor = ClimateAdvisor()
    drought_guide = climate_advisor.get_drought_resilience("maize")
    print(f"Drought risk: {drought_guide['drought_risk_level']}")
    print(f"Varieties: {len(drought_guide['drought_tolerant_varieties'])} recommended")
    print(f"Water conservation methods: {len(drought_guide['water_conservation_techniques'])} techniques")
    print()

    print("[5] FARM PLANNER — 2-Acre Farm in East Africa")
    print("-" * 50)
    farm_plan_result = farm_plan(2.0, "east_africa", 800.0, ["food_security", "income_generation"])
    summary = farm_plan_result.get("farm_summary", {})
    print(f"Land: {summary.get('land_size_acres')} acres")
    print(f"Budget: ${summary.get('total_budget_usd')} (${summary.get('budget_per_acre')}/acre)")
    crops = farm_plan_result.get("recommended_crop_mix", [])
    print(f"Crops: {len(crops)} enterprises planned")
    for c in crops:
        print(f"  - {c['crop']}: {c['area_acres']} acres ({c['purpose']})")
    financials = farm_plan_result.get("financial_projections", {})
    print(f"Projected revenue: ${financials.get('total_expected_revenue_usd')}")
    print(f"Projected profit: ${financials.get('net_profit_usd')}")
    print(f"ROI: {financials.get('roi_percent')}%")
    print()

    print("[6] LIVESTOCK ADVISOR — Chicken Care Guide")
    print("-" * 50)
    livestock_advisor = LivestockAdvisor()
    chicken_guide = livestock_advisor.get_care_guide("chickens")
    print(f"Animal: {chicken_guide['animal']}")
    print(f"Water: {chicken_guide['feeding']['daily_water']}")
    print(f"Eggs/year: {LIVESTOCK['chickens']['eggs_per_year'][0]}-{LIVESTOCK['chickens']['eggs_per_year'][1]}")
    print(f"Housing: {chicken_guide['housing'][:80]}...")
    print()

    print("[7] DATABASE — Farm Records Demo")
    print("-" * 50)
    db = FarmDatabaseManager("demo_farm.db")

    # Add sample records
    record = FarmRecord(
        record_id=None,
        farm_name="Demo Farm",
        activity_type="planting",
        crop_or_animal="maize",
        date=datetime.date.today().isoformat(),
        details="Planted SC627 maize variety",
        quantity=1.0,
        unit="acre",
        cost=50.0,
        revenue=0.0,
        notes="Good rain at planting",
    )
    record_id = db.add_farm_record(record)
    print(f"Added farm record ID: {record_id}")

    # Add crop performance record
    perf_id = db.record_crop_performance(
        farm_name="Demo Farm",
        crop="maize",
        season="rainy",
        year=datetime.date.today().year,
        area_acres=1.0,
        seed_variety="SC627",
        planting_date=datetime.date.today().isoformat(),
        yield_kg=1500.0,
        revenue_usd=450.0,
        input_costs_usd=200.0,
    )
    print(f"Added crop performance ID: {perf_id}")

    # Get financial summary
    summary = db.get_financial_summary("Demo Farm")
    print(f"Total costs: ${summary['total_costs_usd']}")
    print(f"Total revenue: ${summary['total_revenue_usd']}")
    print(f"Net profit: ${summary['net_profit_usd']}")
    print()

    print("=" * 70)
    print("Demonstration complete!")
    print("=" * 70)
    print()
    print("IMPORTANT DISCLAIMERS:")
    print(f"  {GENERAL_DISCLAIMER[:100]}...")
    print(f"  {FINANCIAL_DISCLAIMER[:100]}...")
    print(f"  {MEDICAL_DISCLAIMER[:100]}...")
    print(f"  {WEATHER_DISCLAIMER[:100]}...")
    print()

