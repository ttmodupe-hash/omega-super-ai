#!/usr/bin/env python3
"""Luqi AI v20 - Business Advisor for Africa
=============================================
Business and financial advisory system for African entrepreneurs,
small business owners, and traders. Focuses on mobile money,
micro-businesses, formalization, and financial literacy.

Covers Nigeria, South Africa, Kenya, Ghana, Tanzania, Ethiopia,
Uganda, and Rwanda with localised guidance on registration,
taxation, marketing, and operations for micro and small
enterprises (1-10 employees).

DISCLAIMER
----------
The information provided by this module is for educational and
informational purposes only. It does **NOT** constitute professional
financial, legal, tax, or investment advice. Always consult a
qualified accountant, lawyer, or financial advisor before making
business decisions. Tax laws and regulations change frequently;
verify all information with your local tax authority.

Author: Luqi AI System
License: MIT
Python: >=3.8
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.business_advisor")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    _handler.setFormatter(_fmt)
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_DIR = Path(os.environ.get("LUQI_DATA_DIR", "/mnt/agents/output/project/backend/data"))
DB_DIR.mkdir(parents=True, exist_ok=True)
RECORDS_DB = DB_DIR / "business_records.db"

# African countries supported
SUPPORTED_COUNTRIES: List[str] = [
    "nigeria", "south_africa", "kenya", "ghana",
    "tanzania", "ethiopia", "uganda", "rwanda",
]

# Mobile money providers by country
MOBILE_MONEY_PROVIDERS: Dict[str, List[Dict[str, str]]] = {
    "kenya": [
        {"name": "M-Pesa", "provider": "Safaricom",
         "features": "Send money, pay bills, buy goods, savings (M-Shwari), loans",
         "ussd": "*334#", "app": "M-Pesa App"},
        {"name": "Airtel Money", "provider": "Airtel Kenya",
         "features": "Money transfer, airtime, bill payments, KCB partnership",
         "ussd": "*222#", "app": "My Airtel App"},
    ],
    "nigeria": [
        {"name": "OPay", "provider": "OPay Digital Services",
         "features": "Transfers, bill pay, savings (OWealth), POS services",
         "ussd": "*955#", "app": "OPay App"},
        {"name": "Paga", "provider": "Paga Technologies",
         "features": "Send/receive money, bill payments, agent network",
         "ussd": "*242#", "app": "Paga App"},
        {"name": "PalmPay", "provider": "PalmPay Limited",
         "features": "Airtime cashback, transfers, bill payments",
         "ussd": "*652#", "app": "PalmPay App"},
    ],
    "ghana": [
        {"name": "MTN Mobile Money", "provider": "MTN Ghana",
         "features": "Send money, pay bills, merchant payments, MoMo loans",
         "ussd": "*170#", "app": "MyMTN App"},
        {"name": "Vodafone Cash", "provider": "Vodafone Ghana",
         "features": "Money transfer, bill payments, zero-fee transfers",
         "ussd": "*110#", "app": "My Vodafone App"},
        {"name": "AirtelTigo Money", "provider": "AirtelTigo",
         "features": "Send money, pay bills, airtime purchase",
         "ussd": "*500#", "app": "AirtelTigo App"},
    ],
    "tanzania": [
        {"name": "M-Pesa", "provider": "Vodacom Tanzania",
         "features": "Money transfer, bill pay, merchant payments",
         "ussd": "*150*00#", "app": "M-Pesa Tanzania App"},
        {"name": "Tigo Pesa", "provider": "Tigo Tanzania",
         "features": "Send money, pay bills, savings, international transfer",
         "ussd": "*150*01#", "app": "Tigo Pesa App"},
        {"name": "Airtel Money", "provider": "Airtel Tanzania",
         "features": "Money transfer, bill payments, merchant services",
         "ussd": "*150*60#", "app": "Airtel Money App"},
    ],
    "uganda": [
        {"name": "MTN Mobile Money", "provider": "MTN Uganda",
         "features": "Send money, pay bills, school fees, merchant payments",
         "ussd": "*165#", "app": "MTN MoMo App"},
        {"name": "Airtel Money", "provider": "Airtel Uganda",
         "features": "Money transfer, bill payments, merchant services",
         "ussd": "*185#", "app": "Airtel Money App"},
    ],
    "rwanda": [
        {"name": "MTN Mobile Money", "provider": "MTN Rwanda",
         "features": "Send money, pay bills, merchant payments",
         "ussd": "*182#", "app": "MTN MoMo App"},
        {"name": "Airtel Money", "provider": "Airtel Rwanda",
         "features": "Money transfer, bill payments",
         "ussd": "*182*2#", "app": "Airtel Money App"},
    ],
    "south_africa": [
        {"name": "Vodapay", "provider": "Vodacom",
         "features": "Digital wallet, merchant payments, rewards",
         "ussd": "*111*277#", "app": "Vodapay App"},
        {"name": "MTN MoMo", "provider": "MTN South Africa",
         "features": "Money transfer, bill payments, merchant services",
         "ussd": "*151#", "app": "MTN MoMo App"},
    ],
    "ethiopia": [
        {"name": "Telebirr", "provider": "Ethio Telecom",
         "features": "Money transfer, bill payments, merchant services, savings",
         "ussd": "*127#", "app": "Telebirr App"},
    ],
}

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BusinessSize(Enum):
    """Business size classification for MSEs."""
    MICRO = "micro"           # 1 employee (owner)
    VERY_SMALL = "very_small" # 2-4 employees
    SMALL = "small"           # 5-10 employees


class BusinessStage(Enum):
    """Stages of business development."""
    IDEA = "idea"
    STARTUP = "startup"
    GROWTH = "growth"
    ESTABLISHED = "established"
    EXPANSION = "expansion"


class Season(Enum):
    """Seasonal classification for agricultural and seasonal businesses."""
    DRY = "dry_season"
    WET = "wet_season"
    HARVEST = "harvest_season"
    PLANTING = "planting_season"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BudgetItem:
    """A single line item in a budget."""
    name: str
    amount: float
    category: str = "general"
    is_essential: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "amount": round(self.amount, 2),
            "category": self.category,
            "is_essential": self.is_essential,
        }


@dataclass
class CashFlowRecord:
    """A single cash flow record (income or expense)."""
    date_str: str
    description: str
    amount: float
    record_type: str  # "income" or "expense"
    category: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "date": self.date_str,
            "description": self.description,
            "amount": round(self.amount, 2),
            "type": self.record_type,
            "category": self.category,
        }


@dataclass
class FinancialProjection:
    """Monthly financial projection for a business plan."""
    month: int
    revenue: float
    costs: float
    net_profit: float
    cumulative: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "month": self.month,
            "revenue": round(self.revenue, 2),
            "costs": round(self.costs, 2),
            "net_profit": round(self.net_profit, 2),
            "cumulative": round(self.cumulative, 2),
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _format_currency(amount: float, currency: str = "USD") -> str:
    """Format an amount as currency string."""
    currency_symbols = {
        "USD": "$", "NGN": "\u20a6", "ZAR": "R", "KES": "KSh",
        "GHS": "GH\u20b5", "TZS": "TSh", "ETB": "Br", "UGX": "USh",
        "RWF": "RF",
    }
    sym = currency_symbols.get(currency, currency + " ")
    return f"{sym}{amount:,.2f}"


def _get_currency_for_country(country: str) -> str:
    """Return the ISO currency code for a given African country."""
    mapping = {
        "nigeria": "NGN", "south_africa": "ZAR", "kenya": "KES",
        "ghana": "GHS", "tanzania": "TZS", "ethiopia": "ETB",
        "uganda": "UGX", "rwanda": "RWF",
    }
    return mapping.get(country.lower(), "USD")


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Failed to convert %r to float; using default %s", value, default)
        return default


def _init_db(db_path: Path) -> None:
    """Initialise the SQLite database for business records if not present."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ledgers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id TEXT NOT NULL,
                entry_date  TEXT NOT NULL,
                description TEXT NOT NULL,
                debit       REAL DEFAULT 0,
                credit      REAL DEFAULT 0,
                category    TEXT DEFAULT 'general',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no  TEXT UNIQUE NOT NULL,
                business_id TEXT NOT NULL,
                customer    TEXT NOT NULL,
                amount      REAL NOT NULL,
                tax_rate    REAL DEFAULT 0,
                total       REAL NOT NULL,
                issue_date  TEXT NOT NULL,
                due_date    TEXT,
                paid        INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no  TEXT UNIQUE NOT NULL,
                business_id TEXT NOT NULL,
                customer    TEXT,
                amount      REAL NOT NULL,
                payment_method TEXT DEFAULT 'cash',
                issue_date  TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS businesses (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL,
                country     TEXT,
                location    TEXT,
                capital     REAL DEFAULT 0,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()
        logger.debug("Database initialised at %s", db_path)
    except sqlite3.Error as exc:
        logger.error("Database initialisation failed: %s", exc)
        raise


# Ensure DB exists on import
_init_db(RECORDS_DB)


# =============================================================================
# CLASS: BusinessPlanner
# =============================================================================

class BusinessPlanner:
    """Generate business plans, ideas, and startup checklists tailored to
    the African micro and small enterprise context.
    """

    BUSINESS_TEMPLATES: Dict[str, Dict[str, Any]] = {
        "retail_shop": {
            "description": "General retail store selling groceries, household items, or electronics.",
            "avg_startup_cost": {"min": 50000, "max": 500000, "currency": "local"},
            "key_equipment": ["shelving", "cash box / POS", "refrigerator", "weighing scale", "display counter"],
            "daily_tasks": ["open shop", "arrange stock", "serve customers", "record sales", "reconcile cash", "close shop"],
            "seasonal_factors": ["holiday seasons boost sales", "harvest season increases rural spending"],
            "challenges": ["stock theft", "price competition from supermarkets", "credit sales"],
            "profit_margin_pct": 15,
        },
        "farming": {
            "description": "Crop farming on small to medium plots of land.",
            "avg_startup_cost": {"min": 20000, "max": 300000, "currency": "local"},
            "key_equipment": ["hoes", "seeds", "fertilizer", "sprayer", "watering can / irrigation"],
            "daily_tasks": ["inspect crops", "water/irrigate", "weed control", "pest management", "record activities"],
            "seasonal_factors": ["planting at season start", "harvest timing critical for prices"],
            "challenges": ["weather dependency", "pest and disease", "market price fluctuation", "access to quality inputs"],
            "profit_margin_pct": 25,
        },
        "food_vendor": {
            "description": "Street food or small restaurant selling local dishes.",
            "avg_startup_cost": {"min": 10000, "max": 150000, "currency": "local"},
            "key_equipment": ["cooking stove", "pots and pans", "food containers", "table/chairs", "water storage"],
            "daily_tasks": ["buy fresh ingredients", "prep and cook", "serve customers", "clean workspace", "count earnings"],
            "seasonal_factors": ["rainy season may reduce foot traffic", "festivals boost sales"],
            "challenges": ["food safety compliance", "ingredient price volatility", "waste management"],
            "profit_margin_pct": 35,
        },
        "tailoring": {
            "description": "Clothing design, alterations, and custom tailoring.",
            "avg_startup_cost": {"min": 30000, "max": 200000, "currency": "local"},
            "key_equipment": ["sewing machine", "measuring tape", "scissors", "ironing board", "fabrics"],
            "daily_tasks": ["take measurements", "cut fabrics", "sew garments", "fit and alter", "deliver to customers"],
            "seasonal_factors": ["festive seasons (Christmas, Eid, weddings) drive demand"],
            "challenges": ["competition from imported clothes", "power outages affect machine work", "client payment delays"],
            "profit_margin_pct": 40,
        },
        "hairdressing": {
            "description": "Hair salon offering braiding, weaving, styling, and treatments.",
            "avg_startup_cost": {"min": 25000, "max": 150000, "currency": "local"},
            "key_equipment": ["hair dryer", "combs and brushes", "hair products", "mirrors", "chairs", "extension hair"],
            "daily_tasks": ["open salon", "attend to clients", "manage appointments", "restock products", "clean salon"],
            "seasonal_factors": ["wedding and festive seasons are peak", "school holidays increase demand"],
            "challenges": ["high product costs", "stylist turnover", "power issues for dryers"],
            "profit_margin_pct": 45,
        },
        "phone_repair": {
            "description": "Mobile phone and electronics repair service.",
            "avg_startup_cost": {"min": 50000, "max": 200000, "currency": "local"},
            "key_equipment": ["screwdriver set", "soldering iron", "multimeter", "screen replacement kits", "magnifying lamp"],
            "daily_tasks": ["diagnose phone issues", "perform repairs", "source spare parts", "test devices", "record jobs"],
            "seasonal_factors": ["consistent demand year-round", "back-to-school increases demand"],
            "challenges": ["sourcing genuine parts", "technology changes fast", "warranty disputes"],
            "profit_margin_pct": 50,
        },
        "transport": {
            "description": "Transport services including boda-boda, tuk-tuk, taxi, or delivery.",
            "avg_startup_cost": {"min": 100000, "max": 2000000, "currency": "local"},
            "key_equipment": ["motorcycle / vehicle", "helmet", "phone for bookings", "fuel can", "first aid kit"],
            "daily_tasks": ["fuel up", "pick up passengers/deliveries", "navigate routes", "collect fares", "basic maintenance"],
            "seasonal_factors": ["rainy season may increase demand (harder to walk)", "holiday travel peaks"],
            "challenges": ["fuel price volatility", "accident risks", "vehicle maintenance costs", "regulatory compliance"],
            "profit_margin_pct": 30,
        },
        "cyber_cafe": {
            "description": "Internet cafe offering browsing, printing, and typing services.",
            "avg_startup_cost": {"min": 100000, "max": 500000, "currency": "local"},
            "key_equipment": ["computers/laptops", "printer/scanner", "router/Wi-Fi", "UPS/generator backup", "chairs and desks"],
            "daily_tasks": ["open cafe", "assist customers", "manage printing", "monitor internet usage", "close and reconcile"],
            "seasonal_factors": ["school periods increase demand for printing", "holidays may reduce usage"],
            "challenges": ["unreliable electricity", "internet downtime", "equipment theft/damage"],
            "profit_margin_pct": 40,
        },
        "poultry": {
            "description": "Poultry farming for eggs (layers) or meat (broilers).",
            "avg_startup_cost": {"min": 50000, "max": 500000, "currency": "local"},
            "key_equipment": ["chicken house / coop", "feeders and drinkers", "heating lamps", "vaccines", "feed storage"],
            "daily_tasks": ["feed chickens", "collect eggs (layers)", "clean coops", "monitor health", "record mortality and production"],
            "seasonal_factors": ["dry season preferred for housing", "festive seasons increase demand for broilers"],
            "challenges": ["disease outbreaks (Newcastle, Gumboro)", "feed costs", "market price fluctuations"],
            "profit_margin_pct": 30,
        },
        "fish_farming": {
            "description": "Aquaculture (catfish, tilapia) in ponds or tanks.",
            "avg_startup_cost": {"min": 80000, "max": 600000, "currency": "local"},
            "key_equipment": ["pond or tanks", "fingerlings", "fish feed", "aeration system", "net/harvesting tools"],
            "daily_tasks": ["feed fish", "check water quality", "remove dead fish", "monitor growth", "prepare for harvest"],
            "seasonal_factors": ["rainy season helps pond water levels", "festive periods increase demand"],
            "challenges": ["water quality management", "predators and theft", "high feed costs", "market access"],
            "profit_margin_pct": 35,
        },
        "agro_processor": {
            "description": "Processing agricultural produce: milling, oil extraction, drying.",
            "avg_startup_cost": {"min": 150000, "max": 2000000, "currency": "local"},
            "key_equipment": ["processing machine (mill/oil press)", "storage facility", "weighing scale", "packaging materials"],
            "daily_tasks": ["receive raw materials", "process products", "package finished goods", "manage quality", "deliver orders"],
            "seasonal_factors": ["harvest season = high raw material supply", "dry season easier for drying operations"],
            "challenges": ["machine maintenance", "raw material supply inconsistency", "quality control standards"],
            "profit_margin_pct": 25,
        },
        "crafts": {
            "description": "Handicrafts, beadwork, weaving, wood carving, and artisan goods.",
            "avg_startup_cost": {"min": 10000, "max": 100000, "currency": "local"},
            "key_equipment": ["raw materials (beads, wood, fabric)", "hand tools", "work table", "display materials"],
            "daily_tasks": ["create products", "source materials", "photograph items", "manage orders", "deliver items"],
            "seasonal_factors": ["tourist season boosts sales", "festive gift-giving periods"],
            "challenges": ["low local appreciation of crafts", "copycat products", "market access for tourists"],
            "profit_margin_pct": 50,
        },
        "import_export": {
            "description": "Trading goods across borders within Africa or internationally.",
            "avg_startup_cost": {"min": 200000, "max": 5000000, "currency": "local"},
            "key_equipment": ["phone/laptop for communication", "storage space", "transport arrangement", "capital for stock"],
            "daily_tasks": ["communicate with suppliers/buyers", "arrange logistics", "track shipments", "manage customs", "collect payments"],
            "seasonal_factors": ["pre-holiday stocking periods", "currency exchange rate fluctuations"],
            "challenges": ["customs regulations", "currency risk", "shipping delays", "payment security"],
            "profit_margin_pct": 20,
        },
    }

    # ------------------------------------------------------------------
    # create_business_plan
    # ------------------------------------------------------------------
    def create_business_plan(
        self,
        business_type: str,
        capital: float,
        location: str,
    ) -> Dict[str, Any]:
        """Generate a full business plan for a given business type, capital, and location.

        Parameters
        ----------
        business_type : str
            One of the keys in BUSINESS_TEMPLATES.
        capital : float
            Available startup capital in local currency.
        location : str
            City or region description.

        Returns
        -------
        dict
            Comprehensive business plan with executive summary, market analysis,
            operations plan, and 12-month financial projections.
        """
        logger.info("Creating business plan: type=%s capital=%s location=%s",
                    business_type, capital, location)
        template = self.BUSINESS_TEMPLATES.get(business_type.lower())
        if template is None:
            known = ", ".join(self.BUSINESS_TEMPLATES.keys())
            raise ValueError(f"Unknown business_type '{business_type}'. Known: {known}")

        currency = _get_currency_for_country(location.split(",")[-1].strip().lower()) if "," in location else "USD"

        # Executive summary
        exec_summary = (
            f"Executive Summary for {business_type.replace('_', ' ').title()}\n"
            f"{'=' * 60}\n"
            f"Business Concept: {template['description']}\n"
            f"Location: {location}\n"
            f"Startup Capital: {_format_currency(capital, currency)}\n"
            f"Estimated Profit Margin: {template['profit_margin_pct']}%\n"
            f"Key Equipment Needed: {', '.join(template['key_equipment'])}\n"
        )

        # Market analysis
        market_analysis = (
            f"Market Analysis\n{'=' * 40}\n"
            f"Target Market: Local consumers in {location}\n"
            f"Demand Factors: {', '.join(template['seasonal_factors'])}\n"
            f"Competition: Other {business_type.replace('_', ' ')} businesses in the area\n"
            f"Challenges: {', '.join(template['challenges'])}\n"
            f"Pricing Strategy: Cost-plus pricing with {template['profit_margin_pct']}% margin\n"
        )

        # Operations plan
        operations = (
            f"Operations Plan\n{'=' * 40}\n"
            f"Daily Activities:\n"
            + "\n".join(f"  - {task}" for task in template["daily_tasks"])
            + f"\n\nKey Equipment:\n"
            + "\n".join(f"  - {eq}" for eq in template["key_equipment"])
            + f"\n\nStaffing: 1-3 employees (owner-operated initially)\n"
            f"Operating Hours: 8-12 hours per day, 6 days per week\n"
        )

        # Financial projections (12 months)
        monthly_revenue = capital * 0.15  # assume ~15% monthly turnover of capital
        monthly_costs = monthly_revenue * (1 - template["profit_margin_pct"] / 100)
        projections: List[Dict[str, Any]] = []
        cumulative = 0.0
        for month in range(1, 13):
            # Seasonal adjustment
            seasonal_multiplier = 1.0
            if month in [11, 12]:  # holiday season
                seasonal_multiplier = 1.2
            elif month in [6, 7]:  # mid-year dip
                seasonal_multiplier = 0.9
            rev = monthly_revenue * seasonal_multiplier
            cost = monthly_costs * seasonal_multiplier
            profit = rev - cost
            cumulative += profit
            projections.append(FinancialProjection(
                month=month, revenue=rev, costs=cost,
                net_profit=profit, cumulative=cumulative,
            ).to_dict())

        financial_projections = (
            f"12-Month Financial Projections\n{'=' * 40}\n"
            f"Projected Monthly Revenue (avg): {_format_currency(monthly_revenue, currency)}\n"
            f"Projected Monthly Costs (avg): {_format_currency(monthly_costs, currency)}\n"
            f"Expected Monthly Profit (avg): {_format_currency(monthly_revenue - monthly_costs, currency)}\n"
            f"12-Month Cumulative Profit: {_format_currency(cumulative, currency)}\n"
            + "\nMonth-by-month:\n"
            + "\n".join(
                f"  Month {p['month']}: Revenue {_format_currency(p['revenue'], currency)} | "
                f"Costs {_format_currency(p['costs'], currency)} | "
                f"Net {_format_currency(p['net_profit'], currency)} | "
                f"Cumulative {_format_currency(p['cumulative'], currency)}"
                for p in projections
            )
        )

        plan = {
            "business_type": business_type,
            "location": location,
            "capital": capital,
            "currency": currency,
            "executive_summary": exec_summary,
            "market_analysis": market_analysis,
            "operations_plan": operations,
            "financial_projections": {
                "projections": projections,
                "formatted": financial_projections,
            },
            "profit_margin_pct": template["profit_margin_pct"],
            "key_equipment": template["key_equipment"],
            "daily_tasks": template["daily_tasks"],
            "seasonal_factors": template["seasonal_factors"],
            "challenges": template["challenges"],
            "disclaimer": (
                "DISCLAIMER: These projections are estimates for planning purposes only. "
                "Actual results will vary based on market conditions, execution, and external factors. "
                "This is not professional financial advice."
            ),
        }
        logger.info("Business plan created successfully for %s", business_type)
        return plan

    # ------------------------------------------------------------------
    # get_business_ideas
    # ------------------------------------------------------------------
    def get_business_ideas(
        self,
        location: str,
        capital: float,
        skills: str,
    ) -> List[Dict[str, str]]:
        """Suggest business ideas based on location, available capital, and skills.

        Parameters
        ----------
        location : str
            City or region (e.g., 'Lagos, Nigeria').
        capital : float
            Available startup capital.
        skills : str
            Comma-separated skills (e.g., 'cooking, sewing, computer').

        Returns
        -------
        list of dict
            Matching business ideas with descriptions, estimated costs, and tips.
        """
        logger.info("Getting business ideas: location=%s capital=%s skills=%s",
                    location, capital, skills)
        skills_lower = [s.strip().lower() for s in skills.split(",")]
        ideas: List[Dict[str, str]] = []

        # Skill-to-business mapping
        skill_map: Dict[str, List[str]] = {
            "cooking": ["food_vendor"],
            "sewing": ["tailoring"],
            "computer": ["cyber_cafe", "phone_repair"],
            "phone": ["phone_repair"],
            "driving": ["transport"],
            "farming": ["farming", "poultry", "fish_farming", "agro_processor"],
            "agriculture": ["farming", "poultry", "fish_farming", "agro_processor"],
            "hair": ["hairdressing"],
            "braiding": ["hairdressing"],
            "crafts": ["crafts"],
            "beads": ["crafts"],
            "wood": ["crafts"],
            "trading": ["retail_shop", "import_export"],
            "sales": ["retail_shop"],
            "typing": ["cyber_cafe"],
            "internet": ["cyber_cafe"],
        }

        matched_types: set = set()
        for sk in skills_lower:
            matched_types.update(skill_map.get(sk, []))

        # If no specific skill match, suggest based on capital level
        if not matched_types:
            if capital < 50000:
                matched_types = {"food_vendor", "crafts", "hairdressing"}
            elif capital < 200000:
                matched_types = {"retail_shop", "tailoring", "phone_repair", "poultry"}
            else:
                matched_types = {"transport", "cyber_cafe", "agro_processor", "fish_farming", "import_export"}

        for bt in matched_types:
            tmpl = self.BUSINESS_TEMPLATES.get(bt)
            if tmpl is None:
                continue
            startup = tmpl["avg_startup_cost"]
            min_cap, max_cap = startup["min"], startup["max"]
            suitability = "ideal" if min_cap <= capital <= max_cap * 2 else "stretch" if capital >= min_cap * 0.5 else "underfunded"

            ideas.append({
                "business_type": bt.replace("_", " ").title(),
                "description": tmpl["description"],
                "estimated_startup": f"{min_cap:,.0f} - {max_cap:,.0f} (local currency)",
                "profit_margin": f"{tmpl['profit_margin_pct']}%",
                "suitability": suitability,
                "why_fit": f"Matches your skills in {skills} and capital level in {location}.",
                "tip": f"Start small with {tmpl['key_equipment'][0]} and scale gradually.",
            })

        # Sort by suitability
        order = {"ideal": 0, "stretch": 1, "underfunded": 2}
        ideas.sort(key=lambda x: order.get(x["suitability"], 3))
        logger.info("Found %d business ideas", len(ideas))
        return ideas

    # ------------------------------------------------------------------
    # get_startup_checklist
    # ------------------------------------------------------------------
    def get_startup_checklist(self, business_type: str) -> List[Dict[str, Any]]:
        """Return a step-by-step registration and setup checklist.

        Parameters
        ----------
        business_type : str
            Type of business (key from BUSINESS_TEMPLATES).

        Returns
        -------
        list of dict
            Ordered checklist items with step number, action, and notes.
        """
        logger.info("Generating startup checklist for %s", business_type)
        checklist = [
            {"step": 1, "action": "Research the market and validate demand", "category": "planning", "done": False},
            {"step": 2, "action": "Choose a business name and check availability", "category": "registration", "done": False},
            {"step": 3, "action": "Write a simple business plan", "category": "planning", "done": False},
            {"step": 4, "action": "Register the business with local authorities", "category": "registration", "done": False},
            {"step": 5, "action": "Open a business bank account or mobile money business account", "category": "finance", "done": False},
            {"step": 6, "action": "Obtain necessary permits and licenses", "category": "compliance", "done": False},
            {"step": 7, "action": "Set up a bookkeeping system (manual or digital)", "category": "finance", "done": False},
            {"step": 8, "action": "Purchase or lease essential equipment", "category": "operations", "done": False},
            {"step": 9, "action": "Find reliable suppliers and negotiate terms", "category": "operations", "done": False},
            {"step": 10, "action": "Set up your physical or online presence", "category": "marketing", "done": False},
            {"step": 11, "action": "Create a simple pricing list", "category": "marketing", "done": False},
            {"step": 12, "action": "Start serving customers and collect feedback", "category": "launch", "done": False},
            {"step": 13, "action": "Register for taxes with local tax authority", "category": "compliance", "done": False},
            {"step": 14, "action": "Join a local business association or cooperative", "category": "networking", "done": False},
            {"step": 15, "action": "Review performance monthly and adjust strategy", "category": "growth", "done": False},
        ]

        # Add business-type-specific items
        template = self.BUSINESS_TEMPLATES.get(business_type.lower())
        if template:
            for idx, equip in enumerate(template["key_equipment"][:3], start=16):
                checklist.append({
                    "step": idx,
                    "action": f"Acquire: {equip}",
                    "category": "equipment",
                    "done": False,
                })

        logger.info("Generated checklist with %d items", len(checklist))
        return checklist


# =============================================================================
# CLASS: FinancialManager
# =============================================================================

class FinancialManager:
    """Financial management tools for micro and small businesses including
    budgeting, cash flow tracking, profit calculation, savings planning,
    loan analysis, and mobile money integration guidance.
    """

    # ------------------------------------------------------------------
    # create_budget
    # ------------------------------------------------------------------
    def create_budget(
        self,
        income: float,
        expenses: List[BudgetItem],
    ) -> Dict[str, Any]:
        """Create a monthly budget plan from income and expense items.

        Parameters
        ----------
        income : float
            Total monthly income.
        expenses : list of BudgetItem
            List of expense line items.

        Returns
        -------
        dict
            Budget summary with totals, percentages, recommendations, and alerts.
        """
        logger.info("Creating budget: income=%s expenses=%d items", income, len(expenses))
        income = _safe_float(income)

        total_expenses = sum(e.amount for e in expenses)
        essential = sum(e.amount for e in expenses if e.is_essential)
        discretionary = total_expenses - essential

        balance = income - total_expenses
        savings_rate = (balance / income * 100) if income > 0 else 0
        essential_pct = (essential / income * 100) if income > 0 else 0

        recommendations: List[str] = []
        if savings_rate < 0:
            recommendations.append("ALERT: Your expenses exceed your income. Reduce discretionary spending immediately.")
        elif savings_rate < 10:
            recommendations.append("Your savings rate is below 10%. Try to cut non-essential expenses.")
        elif savings_rate >= 20:
            recommendations.append("Excellent! You are saving 20%+ of your income. Consider investing surplus.")

        if essential_pct > 70:
            recommendations.append("Essential expenses exceed 70% of income. Look for ways to reduce fixed costs.")

        # 50/30/20 rule analysis
        needs_target = income * 0.50
        wants_target = income * 0.30
        savings_target = income * 0.20

        budget = {
            "monthly_income": round(income, 2),
            "total_expenses": round(total_expenses, 2),
            "essential_expenses": round(essential, 2),
            "discretionary_expenses": round(discretionary, 2),
            "balance": round(balance, 2),
            "savings_rate_pct": round(savings_rate, 1),
            "essential_expenses_pct": round(essential_pct, 1),
            "expense_breakdown": [e.to_dict() for e in expenses],
            "rule_50_30_20": {
                "needs_target": round(needs_target, 2),
                "wants_target": round(wants_target, 2),
                "savings_target": round(savings_target, 2),
                "your_needs": round(essential, 2),
                "your_wants": round(discretionary, 2),
                "your_savings": round(balance, 2),
            },
            "recommendations": recommendations,
            "formatted": self._format_budget(income, expenses, balance, savings_rate),
        }
        logger.info("Budget created: balance=%s savings_rate=%s%%", balance, round(savings_rate, 1))
        return budget

    def _format_budget(
        self,
        income: float,
        expenses: List[BudgetItem],
        balance: float,
        savings_rate: float,
    ) -> str:
        """Format budget as human-readable string."""
        lines = [
            f"Monthly Budget Summary",
            f"{'=' * 50}",
            f"Income:          {income:,.2f}",
            f"Total Expenses:  {sum(e.amount for e in expenses):,.2f}",
            f"{'-' * 50}",
        ]
        for exp in expenses:
            marker = "*" if exp.is_essential else " "
            lines.append(f"  {marker} {exp.name:<25} {exp.amount:>10,.2f}  ({exp.category})")
        lines.extend([
            f"{'-' * 50}",
            f"Balance:         {balance:,.2f}  ({savings_rate:.1f}% savings rate)",
            f"{'=' * 50}",
        ])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # track_cash_flow
    # ------------------------------------------------------------------
    def track_cash_flow(
        self,
        records: List[CashFlowRecord],
    ) -> Dict[str, Any]:
        """Track and analyse cash flow from a list of income/expense records.

        Parameters
        ----------
        records : list of CashFlowRecord
            Daily or weekly cash flow entries.

        Returns
        -------
        dict
            Cash flow summary with totals, net flow, running balance,
            and category breakdown.
        """
        logger.info("Tracking cash flow with %d records", len(records))
        if not records:
            return {"error": "No records provided."}

        total_income = sum(r.amount for r in records if r.record_type == "income")
        total_expenses = sum(r.amount for r in records if r.record_type == "expense")
        net_flow = total_income - total_expenses

        # Category breakdown
        categories: Dict[str, Dict[str, float]] = {}
        for r in records:
            cat = r.category
            if cat not in categories:
                categories[cat] = {"income": 0.0, "expense": 0.0}
            categories[cat][r.record_type] += r.amount

        running_balance = 0.0
        running: List[Dict[str, Any]] = []
        for r in records:
            delta = r.amount if r.record_type == "income" else -r.amount
            running_balance += delta
            running.append({
                "date": r.date_str,
                "description": r.description,
                "type": r.record_type,
                "amount": round(r.amount, 2),
                "running_balance": round(running_balance, 2),
            })

        result = {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_flow": round(net_flow, 2),
            "record_count": len(records),
            "category_breakdown": {
                k: {"income": round(v["income"], 2), "expense": round(v["expense"], 2)}
                for k, v in categories.items()
            },
            "running_balance": running,
            "status": "positive" if net_flow >= 0 else "negative",
            "recommendation": (
                "Cash flow is positive. Consider building a 3-month reserve."
                if net_flow >= 0
                else "Cash flow is negative. Review expenses and increase revenue urgently."
            ),
        }
        logger.info("Cash flow tracked: net=%s status=%s", net_flow, result["status"])
        return result

    # ------------------------------------------------------------------
    # calculate_profit
    # ------------------------------------------------------------------
    def calculate_profit(
        self,
        revenue: float,
        costs: float,
    ) -> Dict[str, Any]:
        """Calculate profit or loss from revenue and costs.

        Parameters
        ----------
        revenue : float
            Total revenue / sales.
        costs : float
            Total costs (COGS + operating expenses).

        Returns
        -------
        dict
            Profit/loss breakdown with margins and recommendations.
        """
        logger.info("Calculating profit: revenue=%s costs=%s", revenue, costs)
        revenue = _safe_float(revenue)
        costs = _safe_float(costs)
        gross_profit = revenue - costs
        profit_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

        status = "profit" if gross_profit > 0 else "loss" if gross_profit < 0 else "break_even"

        recommendations: List[str] = []
        if profit_margin < 10:
            recommendations.append("Profit margin is very low. Consider raising prices or reducing costs.")
        elif profit_margin < 20:
            recommendations.append("Profit margin is moderate. Look for cost efficiencies.")
        else:
            recommendations.append("Healthy profit margin. Reinvest profits for growth.")

        return {
            "revenue": round(revenue, 2),
            "costs": round(costs, 2),
            "gross_profit": round(gross_profit, 2),
            "profit_margin_pct": round(profit_margin, 2),
            "status": status,
            "recommendations": recommendations,
            "formatted": (
                f"Profit/Loss Statement\n{'=' * 40}\n"
                f"Revenue:       {revenue:,.2f}\n"
                f"Costs:         {costs:,.2f}\n"
                f"{'-' * 40}\n"
                f"Gross Profit:  {gross_profit:,.2f}  ({profit_margin:.1f}% margin)\n"
                f"Status:        {status.upper()}\n"
                f"{'=' * 40}"
            ),
        }

    # ------------------------------------------------------------------
    # get_savings_plan
    # ------------------------------------------------------------------
    def get_savings_plan(
        self,
        income: float,
        goal: float,
        timeline_months: int,
    ) -> Dict[str, Any]:
        """Create a savings goal plan.

        Parameters
        ----------
        income : float
            Monthly income.
        goal : float
            Savings target amount.
        timeline_months : int
            Number of months to reach the goal.

        Returns
        -------
        dict
            Savings plan with monthly target, feasibility analysis, and tips.
        """
        logger.info("Savings plan: income=%s goal=%s timeline=%s months", income, goal, timeline_months)
        income = _safe_float(income)
        goal = _safe_float(goal)
        timeline_months = max(1, int(timeline_months))

        monthly_target = goal / timeline_months
        monthly_pct = (monthly_target / income * 100) if income > 0 else 0

        feasible = monthly_pct <= 30  # generally feasible if <= 30% of income
        adjusted_timeline = int(goal / (income * 0.20)) if income > 0 and monthly_pct > 30 else timeline_months

        tips = [
            "Set up an automatic transfer to savings on payday.",
            "Use a mobile money savings feature (e.g., M-Shwari, OWealth) for discipline.",
            "Track every expense to find areas to cut.",
            "Avoid borrowing to save — focus on real surplus.",
            "Celebrate small milestones to stay motivated.",
        ]

        if not feasible:
            tips.insert(0, f"This goal requires saving {monthly_pct:.1f}% of income, which is aggressive. Consider extending to {adjusted_timeline} months.")

        return {
            "goal_amount": round(goal, 2),
            "timeline_months": timeline_months,
            "monthly_income": round(income, 2),
            "monthly_savings_target": round(monthly_target, 2),
            "savings_rate_required_pct": round(monthly_pct, 1),
            "is_feasible": feasible,
            "suggested_timeline_months": adjusted_timeline,
            "tips": tips,
            "progress_tracker": [
                {
                    "month": m,
                    "saved_so_far": round(monthly_target * m, 2),
                    "remaining": round(goal - monthly_target * m, 2),
                    "pct_complete": round(min(100, (monthly_target * m / goal) * 100), 1),
                }
                for m in range(1, timeline_months + 1)
            ],
            "formatted": (
                f"Savings Plan: Goal {goal:,.2f} in {timeline_months} months\n"
                f"{'=' * 50}\n"
                f"Monthly Target:   {monthly_target:,.2f} ({monthly_pct:.1f}% of income)\n"
                f"Feasible:         {'YES' if feasible else 'NO - Consider ' + str(adjusted_timeline) + ' months'}\n"
                f"{'=' * 50}"
            ),
            "disclaimer": (
                "DISCLAIMER: This savings plan is a guideline only. Personal circumstances vary. "
                "This does not constitute financial advice."
            ),
        }

    # ------------------------------------------------------------------
    # get_loan_info
    # ------------------------------------------------------------------
    def get_loan_info(
        self,
        amount: float,
        annual_rate: float,
        duration_months: int,
    ) -> Dict[str, Any]:
        """Calculate loan repayment schedule and total cost.

        Parameters
        ----------
        amount : float
            Principal loan amount.
        annual_rate : float
            Annual interest rate (percentage, e.g., 24 for 24%).
        duration_months : int
            Loan duration in months.

        Returns
        -------
        dict
            Loan details with monthly payment, total interest, amortisation schedule, and warnings.
        """
        logger.info("Loan info: amount=%s rate=%s%% duration=%s months", amount, annual_rate, duration_months)
        amount = _safe_float(amount)
        annual_rate = _safe_float(annual_rate)
        duration_months = max(1, int(duration_months))

        monthly_rate = annual_rate / 100 / 12
        if monthly_rate > 0:
            monthly_payment = amount * (monthly_rate * (1 + monthly_rate) ** duration_months) / \
                              ((1 + monthly_rate) ** duration_months - 1)
        else:
            monthly_payment = amount / duration_months

        total_repayment = monthly_payment * duration_months
        total_interest = total_repayment - amount

        # Amortisation schedule
        schedule: List[Dict[str, float]] = []
        remaining = amount
        for m in range(1, duration_months + 1):
            interest_payment = remaining * monthly_rate
            principal_payment = monthly_payment - interest_payment
            remaining -= principal_payment
            schedule.append({
                "month": m,
                "payment": round(monthly_payment, 2),
                "principal": round(principal_payment, 2),
                "interest": round(interest_payment, 2),
                "remaining": round(max(0, remaining), 2),
            })

        warnings: List[str] = []
        if annual_rate > 36:
            warnings.append(f"WARNING: Annual rate of {annual_rate}% is very high. Consider alternative lenders.")
        if monthly_payment > 0 and amount > 0 and (monthly_payment / (amount / duration_months)) > 1.5:
            warnings.append("Total interest exceeds 50% of principal. Explore cheaper options.")

        return {
            "principal": round(amount, 2),
            "annual_rate_pct": round(annual_rate, 2),
            "duration_months": duration_months,
            "monthly_payment": round(monthly_payment, 2),
            "total_repayment": round(total_repayment, 2),
            "total_interest": round(total_interest, 2),
            "interest_as_pct_of_principal": round(total_interest / amount * 100, 1) if amount > 0 else 0,
            "amortisation_schedule": schedule,
            "warnings": warnings,
            "formatted": (
                f"Loan Repayment Summary\n{'=' * 50}\n"
                f"Principal:         {amount:,.2f}\n"
                f"Annual Rate:       {annual_rate}%\n"
                f"Duration:          {duration_months} months\n"
                f"Monthly Payment:   {monthly_payment:,.2f}\n"
                f"Total Repayment:   {total_repayment:,.2f}\n"
                f"Total Interest:    {total_interest:,.2f}\n"
                f"{'=' * 50}"
            ),
            "disclaimer": (
                "DISCLAIMER: This is a simplified loan calculator for illustration only. "
                "Actual loan terms vary by lender. Fees, insurance, and other charges are not included. "
                "Always read the full loan agreement and consult a financial advisor."
            ),
        }

    # ------------------------------------------------------------------
    # get_mobile_money_guide
    # ------------------------------------------------------------------
    def get_mobile_money_guide(self, country: Optional[str] = None) -> Dict[str, Any]:
        """Return mobile money integration guidance for businesses.

        Parameters
        ----------
        country : str, optional
            Country name to filter providers. If None, returns all.

        Returns
        -------
        dict
            Mobile money provider details, setup steps, fees, and best practices.
        """
        logger.info("Getting mobile money guide for country=%s", country)
        result: Dict[str, Any] = {
            "overview": (
                "Mobile money is essential for African micro-businesses. "
                "It enables cashless payments, reduces theft risk, creates transaction records, "
                "and opens access to digital financial services (savings, loans, insurance)."
            ),
            "setup_steps": [
                "1. Register a personal mobile money account with your phone number.",
                "2. Upgrade to a merchant/business account (requires business registration).",
                "3. Display your payment number / QR code at your business point.",
                "4. Train staff to confirm payments before releasing goods/services.",
                "5. Reconcile transactions daily using the provider app or USSD statement.",
                "6. Link your mobile money to a business bank account for larger transactions.",
            ],
            "best_practices": [
                "Always verify payment confirmation SMS before delivering goods.",
                "Keep a separate business mobile money line — do not mix personal and business.",
                "Download monthly statements for tax record-keeping.",
                "Use the savings feature to set aside tax money weekly.",
                "Enable PIN protection and never share your PIN.",
                "Watch out for fake payment confirmation messages — verify in your app.",
            ],
            "fee_structure_note": (
                "Typical fees: 0.5% - 3% per transaction for merchant payments. "
                "Transfers between personal accounts may cost a flat fee (e.g., 10-100 local currency). "
                "Cash-out at agents typically carries the highest fee. Check with your provider for exact rates."
            ),
            "disclaimer": (
                "DISCLAIMER: Fee structures change frequently. Verify current rates with your mobile money provider. "
                "This information is for guidance only and not financial advice."
            ),
        }

        if country:
            country_key = country.lower().replace(" ", "_")
            providers = MOBILE_MONEY_PROVIDERS.get(country_key, [])
            if not providers:
                result["providers"] = []
                result["note"] = f"No detailed provider data for {country}. Check with local telecoms."
            else:
                result["providers"] = providers
                result["country"] = country_key
        else:
            result["all_providers"] = MOBILE_MONEY_PROVIDERS

        logger.info("Mobile money guide returned for %s", country or "all countries")
        return result


# =============================================================================
# CLASS: MarketAdvisor
# =============================================================================

class MarketAdvisor:
    """Provide pricing guidance, market research, supplier information,
    and customer acquisition strategies for African micro-businesses.
    """

    # Localised pricing benchmarks (local currency units, approximate)
    PRICING_BENCHMARKS: Dict[str, Dict[str, Dict[str, Any]]] = {
        "food_vendor": {
            "default": {"cost_portion": 0.40, "competitive_range": "cost * 2.0 to 2.5",
                        "tip": "Price by plate size. Offer combo deals to increase average ticket."},
        },
        "retail_shop": {
            "default": {"cost_portion": 0.65, "competitive_range": "cost / 0.65 to cost / 0.55",
                        "tip": "Use keystone pricing (double cost) for fast-moving goods. Bulk items can have lower margin."},
        },
        "tailoring": {
            "default": {"cost_portion": 0.30, "competitive_range": "material + (hours * rate)",
                        "tip": "Charge by complexity, not just material. Fitting and alteration fees are additional revenue."},
        },
        "hairdressing": {
            "default": {"cost_portion": 0.25, "competitive_range": "service-based pricing",
                        "tip": "Braiding by length/size. Treatments at premium. Loyalty cards boost repeat visits."},
        },
        "phone_repair": {
            "default": {"cost_portion": 0.35, "competitive_range": "parts + labour (30-50% markup on parts)",
                        "tip": "Offer warranty on repairs (e.g., 30 days) to build trust. Diagnostic fees discourage time-wasters."},
        },
        "transport": {
            "default": {"cost_portion": 0.50, "competitive_range": "market rate per km or per trip",
                        "tip": "Fixed routes = predictable income. Hired rides = higher margin but variable demand."},
        },
        "poultry": {
            "default": {"cost_portion": 0.60, "competitive_range": "feed cost + (feed cost * 0.6 to 0.8)",
                        "tip": "Sell eggs daily for cash flow. Sell mature birds before festive seasons for best prices."},
        },
        "fish_farming": {
            "default": {"cost_portion": 0.55, "competitive_range": "weight-based pricing per kg",
                        "tip": "Harvest when market prices are high. Live fish fetch premium over frozen."},
        },
    }

    SEASONAL_DEMAND: Dict[str, Dict[str, List[int]]] = {
        "retail": {"high": [11, 12, 1], "low": [2, 3, 6]},
        "food": {"high": [12, 1, 7, 8], "low": [2, 3]},
        "farming": {"high": [3, 4, 5], "low": [7, 8, 9]},
        "tailoring": {"high": [11, 12, 4, 5], "low": [1, 2, 6]},
        "hairdressing": {"high": [12, 1, 6, 7], "low": [2, 3]},
        "poultry": {"high": [11, 12, 4], "low": [1, 2, 7]},
    }

    # ------------------------------------------------------------------
    # get_pricing_guide
    # ------------------------------------------------------------------
    def get_pricing_guide(
        self,
        product: str,
        location: str,
    ) -> Dict[str, Any]:
        """Provide a pricing strategy guide for a product/service.

        Parameters
        ----------
        product : str
            Product or service type.
        location : str
            City/region for local context.

        Returns
        -------
        dict
            Pricing strategy with cost-based, competition-based, and value-based approaches.
        """
        logger.info("Pricing guide: product=%s location=%s", product, location)
        product_key = product.lower().replace(" ", "_")
        benchmark = self.PRICING_BENCHMARKS.get(product_key, {}).get("default", {})

        if not benchmark:
            benchmark = {
                "cost_portion": 0.50,
                "competitive_range": "cost * 2.0 to 3.0",
                "tip": "Research what competitors charge. Start at market average, adjust based on quality.",
            }

        return {
            "product": product,
            "location": location,
            "cost_based_pricing": {
                "description": "Calculate all costs, add desired profit margin.",
                "formula": f"Selling Price = Cost / (1 - desired_margin)",
                "example": f"If cost is 100 and you want {(1 - benchmark['cost_portion']) * 100:.0f}% margin, sell at {100 / benchmark['cost_portion']:.0f}",
            },
            "competition_based_pricing": {
                "description": "Price relative to competitors in your area.",
                "approach": benchmark["competitive_range"],
                "tip": "Visit 3-5 competitors in " + location + " and note their prices.",
            },
            "value_based_pricing": {
                "description": "Price based on perceived value to the customer.",
                "tip": "If you offer convenience, quality, or speed, you can charge a premium.",
            },
            "pricing_tip": benchmark["tip"],
            "common_mistakes": [
                "Pricing too low to 'get customers' — attracts price-shoppers only.",
                "Not accounting for all costs (transport, packaging, waste).",
                "Charging the same price year-round without seasonal adjustments.",
                "Not offering tiered pricing (basic / premium / deluxe).",
            ],
        }

    # ------------------------------------------------------------------
    # get_market_research
    # ------------------------------------------------------------------
    def get_market_research(
        self,
        product: str,
        location: str,
    ) -> Dict[str, Any]:
        """Provide market research insights for a product/service.

        Parameters
        ----------
        product : str
            Product or service type.
        location : str
            City/region for local context.

        Returns
        -------
        dict
            Demand assessment, competition analysis, seasonality, and opportunities.
        """
        logger.info("Market research: product=%s location=%s", product, location)
        product_key = product.lower().replace(" ", "_")

        # Determine season
        current_month = datetime.now().month
        seasonal = self.SEASONAL_DEMAND.get(product_key, {})
        if current_month in seasonal.get("high", []):
            season_status = "peak_season"
        elif current_month in seasonal.get("low", []):
            season_status = "low_season"
        else:
            season_status = "normal"

        demand_factors = [
            f"Population density in {location} drives foot traffic.",
            "Income levels determine purchasing power — target the right segment.",
            "Cultural preferences influence product choice — adapt to local taste.",
            "Mobile penetration enables digital marketing and mobile payments.",
        ]

        competition_tips = [
            f"Walk through {location} market areas to count direct competitors.",
            "Talk to potential customers about what they dislike about current options.",
            "Identify a gap — maybe no one offers home delivery, quality, or fair pricing.",
            "Join local business WhatsApp groups to monitor competitor activity.",
        ]

        return {
            "product": product,
            "location": location,
            "demand_assessment": {
                "current_season": season_status,
                "current_month": current_month,
                "demand_factors": demand_factors,
                "recommendation": "Focus on quality and customer service to differentiate."
            },
            "competition_analysis": {
                "tips": competition_tips,
                "differentiation_strategies": [
                    "Better quality than competitors at similar price.",
                    "Faster service or delivery.",
                    "More convenient location or hours.",
                    "Friendly customer relationships (know customers by name).",
                    "Bundle products or services for added value.",
                ],
            },
            "seasonality": {
                "high_months": seasonal.get("high", ["varies"]),
                "low_months": seasonal.get("low", ["varies"]),
                "strategy": "Build cash reserves in high season to survive low season.",
            },
            "opportunities": [
                "Mobile-first marketing reaches customers where they are.",
                "Partner with other small businesses for cross-promotion.",
                "Offer credit carefully to trusted repeat customers.",
                "Consider home delivery or mobile service for convenience.",
            ],
            "disclaimer": (
                "DISCLAIMER: Market conditions vary by location and time. "
                "Conduct on-the-ground research to validate these insights."
            ),
        }

    # ------------------------------------------------------------------
    # get_supplier_guide
    # ------------------------------------------------------------------
    def get_supplier_guide(
        self,
        product: str,
        location: str,
    ) -> Dict[str, Any]:
        """Provide guidance on sourcing suppliers for a product/service.

        Parameters
        ----------
        product : str
            Product or service type.
        location : str
            City/region.

        Returns
        -------
        dict
            Supplier types, sourcing tips, and quality control advice.
        """
        logger.info("Supplier guide: product=%s location=%s", product, location)
        product_key = product.lower().replace(" ", "_")

        supplier_types: Dict[str, List[str]] = {
            "retail": ["Wholesale markets", "Importers/distributors", "Manufacturer direct", "Online B2B platforms"],
            "food": ["Local farmers markets", "Wholesale food markets", "Direct from farms", "Food processing companies"],
            "tailoring": ["Fabric markets", "Textile importers", "Online fabric suppliers", "Local weavers"],
            "hairdressing": ["Beauty supply shops", "Importers", "Online wholesale", "Brand distributors"],
            "phone_repair": ["Spare parts markets", "Online parts suppliers (AliExpress, Jumia)", "Authorised distributors"],
            "poultry": ["Hatcheries", "Feed mills", "Veterinary suppliers", "Farmer cooperatives"],
            "fish_farming": ["Hatcheries", "Feed suppliers", "Pond construction services", "Veterinary suppliers"],
            "farming": ["Agro-dealers", "Seed companies", "Government extension services", "Farmer cooperatives"],
        }

        matched_suppliers = supplier_types.get(product_key, supplier_types.get("retail", []))

        return {
            "product": product,
            "location": location,
            "supplier_types": matched_suppliers,
            "sourcing_tips": [
                "Compare prices from at least 3 suppliers before committing.",
                "Build long-term relationships for better credit terms.",
                "Join a buyers' cooperative to get bulk pricing.",
                "Always inspect goods before payment — especially with new suppliers.",
                "Negotiate payment terms: cash on delivery is safest for new relationships.",
                "Ask for references from other businesses that use the supplier.",
            ],
            "quality_control": [
                "Check expiry dates on all perishable goods.",
                "Test a small sample before placing a large order.",
                "Keep records of supplier quality — drop consistently poor suppliers.",
                "Have a backup supplier for critical items.",
            ],
            "red_flags": [
                "Prices that are 'too good to be true' — may be counterfeit or stolen.",
                "Suppliers who refuse to provide samples or references.",
                "No physical address or business registration.",
                "Pressure to pay full amount upfront with no contract.",
            ],
        }

    # ------------------------------------------------------------------
    # get_customer_strategy
    # ------------------------------------------------------------------
    def get_customer_strategy(
        self,
        business_type: str,
    ) -> Dict[str, Any]:
        """Provide customer acquisition and retention strategies.

        Parameters
        ----------
        business_type : str
            Type of business.

        Returns
        -------
        dict
            Acquisition channels, retention tactics, and loyalty ideas.
        """
        logger.info("Customer strategy for %s", business_type)

        strategies: Dict[str, Dict[str, Any]] = {
            "retail_shop": {
                "acquisition": ["Word-of-mouth in community", "WhatsApp status updates", "Loyalty stamp cards", "Bundle deals"],
                "retention": ["Remember regular customers' preferences", "Credit facility for trusted customers", "Home delivery for bulk orders"],
            },
            "food_vendor": {
                "acquisition": ["Free samples to passersby", "Social media food photos", "Consistency in taste and portion", "Strategic location choice"],
                "retention": ["Know customers by name", "Remember regular orders", "Cleanliness as a differentiator", "Loyalty meal deals"],
            },
            "tailoring": {
                "acquisition": ["Display finished work on mannequins", "Social media portfolio", "Satisfied customer referrals", "Fashion show participation"],
                "retention": ["Perfect fit guarantee", "Alteration services", "Seasonal collection previews for regulars", "SMS reminders for fittings"],
            },
            "hairdressing": {
                "acquisition": ["Before/after photos on Instagram/Facebook", "Referral discounts", "Pop-up styling at events", "Competitive pricing for first visit"],
                "retention": ["Appointment reminders via WhatsApp", "Loyalty discounts (every 5th visit)", "Birthday discounts", "Consistent quality"],
            },
            "phone_repair": {
                "acquisition": ["Quick turnaround as marketing", "Warranty on repairs advertised", "Partnerships with phone sellers", "Online reviews request"],
                "retention": ["Follow-up call after repair", "Discount on accessories with repair", "Repair tracking via WhatsApp", "Free screen protector with repair"],
            },
            "transport": {
                "acquisition": ["Reliability and punctuality", "Fixed schedule published", "Word-of-mouth in neighbourhood", "Community group presence"],
                "retention": ["Regular route consistency", "Safe and clean vehicle", "Fair pricing", "Loyalty card (10th ride free)"],
            },
        }

        strat = strategies.get(business_type.lower(), {
            "acquisition": ["Word-of-mouth", "Social media presence", "Community involvement", "Quality service"],
            "retention": ["Consistent quality", "Personal relationships", "Fair pricing", "Follow-up communication"],
        })

        return {
            "business_type": business_type,
            "acquisition_channels": strat["acquisition"],
            "retention_tactics": strat["retention"],
            "universal_tips": [
                "Treat every customer like they are your only customer.",
                "Ask for feedback and act on it visibly.",
                "Resolve complaints quickly — a recovered customer is more loyal.",
                "Use the customer's name. People do business with people they like.",
                "Under-promise and over-deliver on quality and speed.",
            ],
            "digital_tips": [
                "Create a WhatsApp Business catalog with prices and photos.",
                "Post regularly on Facebook community groups.",
                "Ask happy customers to leave reviews.",
                "Use Instagram for visual businesses (food, fashion, crafts).",
            ],
        }


# =============================================================================
# CLASS: TaxCompliance
# =============================================================================

class TaxCompliance:
    """Tax registration, compliance guidance, and record-keeping advice
    for businesses across supported African countries.
    """

    TAX_DATA: Dict[str, Dict[str, Any]] = {
        "nigeria": {
            "tax_authority": "FIRS (Federal Inland Revenue Service) + State IRS",
            "business_registrar": "CAC (Corporate Affairs Commission)",
            "registration_types": [
                "Business Name (sole proprietorship / partnership)",
                "Limited Liability Company (LTD)",
                "Incorporated Trustee (NGOs)",
            ],
            "taxes": [
                {"name": "Company Income Tax (CIT)", "rate": "30% of profit (large companies), 20% (small companies with turnover < 25M NGN)"},
                {"name": "Value Added Tax (VAT)", "rate": "7.5% on goods and services"},
                {"name": "Personal Income Tax (PIT)", "rate": "Progressive 7% - 24% for self-employed"},
                {"name": "Withholding Tax (WHT)", "rate": "5% - 10% on contracts and services"},
            ],
            "filing_frequency": "Monthly (VAT, WHT), Annual (CIT, PIT)",
            "penalties": "Late filing: 25,000 NGN first month + 5,000 NGN per subsequent month. Late payment: 10% + interest.",
            "useful_links": [
                "CAC: www.cac.gov.ng",
                "FIRS: www.firs.gov.ng",
            ],
            "informal_to_formal_steps": [
                "Register a Business Name with CAC (costs ~10,000-20,000 NGN)",
                "Obtain a TIN (Tax Identification Number) from FIRS",
                "Open a business bank account using CAC certificate",
                "Register for VAT if turnover exceeds 25M NGN annually",
                "Start filing monthly VAT returns even if zero",
                "Keep all receipts and invoices for at least 6 years",
            ],
        },
        "south_africa": {
            "tax_authority": "SARS (South African Revenue Service)",
            "business_registrar": "CIPC (Companies and Intellectual Property Commission)",
            "registration_types": [
                "Sole Proprietorship",
                "Private Company (Pty) Ltd",
                "Close Corporation (CC) — no longer registered but existing ones operate",
                "Partnership",
            ],
            "taxes": [
                {"name": "Income Tax", "rate": "28% for companies, progressive for individuals"},
                {"name": "VAT", "rate": "15% (mandatory if turnover > 1M ZAR)"},
                {"name": "PAYE (Pay As You Earn)", "rate": "Deducted from employee salaries"},
                {"name": "UIF (Unemployment Insurance)", "rate": "2% of salary (split employer/employee)"},
                {"name": "Skills Development Levy", "rate": "1% of payroll if annual payroll > 500K ZAR"},
            ],
            "filing_frequency": "Monthly (PAYE, UIF, VAT), Annual (Income Tax), Bi-annual (provisional tax)",
            "penalties": "Late submission: up to 10% of tax due. Interest on late payment.",
            "useful_links": [
                "CIPC: www.cipc.co.za",
                "SARS: www.sars.gov.za",
            ],
            "informal_to_formal_steps": [
                "Register your company with CIPC",
                "Register with SARS for income tax and get a tax reference number",
                "Register for VAT if turnover exceeds 1M ZAR",
                "Register for PAYE and UIF if you have employees",
                "Open a business bank account",
                "Keep financial records for 5 years",
            ],
        },
        "kenya": {
            "tax_authority": "KRA (Kenya Revenue Authority)",
            "business_registrar": "eCitizen / BRS (Business Registration Service)",
            "registration_types": [
                "Sole Proprietorship",
                "Partnership",
                "Private Limited Company",
            ],
            "taxes": [
                {"name": "Income Tax (Turnover Tax)", "rate": "3% of gross receipts (for businesses with turnover 1M - 25M KES)"},
                {"name": "Income Tax (Corporate)", "rate": "30% of profit (for turnover > 25M KES)"},
                {"name": "VAT", "rate": "16% (mandatory if turnover > 5M KES)"},
                {"name": "PAYE", "rate": "Progressive 10% - 30% deducted from employees"},
                {"name": "NHIF / NSSF", "rate": "Mandatory health and pension contributions"},
            ],
            "filing_frequency": "Monthly (VAT, PAYE, Turnover Tax), Annual (Corporate Tax)",
            "penalties": "Late filing: 1,000-20,000 KES. Late payment: 5% interest per month.",
            "useful_links": [
                "eCitizen: ecitizen.go.ke",
                "KRA: www.kra.go.ke",
            ],
            "informal_to_formal_steps": [
                "Register your business name via eCitizen",
                "Apply for a KRA PIN (both personal and company)",
                "Register for Turnover Tax if applicable",
                "Open a business bank account",
                "Keep sales records and receipts",
                "File monthly returns via iTax",
            ],
        },
        "ghana": {
            "tax_authority": "GRA (Ghana Revenue Authority)",
            "business_registrar": "Registrar General's Department",
            "registration_types": [
                "Sole Proprietorship",
                "Partnership",
                "Private Limited Company",
            ],
            "taxes": [
                {"name": "Corporate Income Tax", "rate": "25% standard, 35% for non-resident"},
                {"name": "VAT", "rate": "15% (standard rate, threshold 200K GHS)"},
                {"name": "GETFund Levy + NHIL", "rate": "2.5% each on VAT base"},
                {"name": "PAYE", "rate": "Progressive 0% - 35%"},
            ],
            "filing_frequency": "Monthly (VAT, PAYE), Quarterly (income tax instalments), Annual (final return)",
            "penalties": "Late filing: 500 GHS + 10 GHS per day. Late payment: 125% of statutory rate interest.",
            "useful_links": [
                "GRA: gra.gov.gh",
                "RGD: rgd.gov.gh",
            ],
            "informal_to_formal_steps": [
                "Register business name at Registrar General's Department",
                "Obtain a TIN from GRA",
                "Register for VAT if turnover exceeds threshold",
                "Open a business bank account",
                "Register for PAYE if you have employees",
                "File monthly VAT and PAYE returns",
            ],
        },
        "tanzania": {
            "tax_authority": "TRA (Tanzania Revenue Authority)",
            "business_registrar": "BRELA (Business Registrations and Licensing Agency)",
            "registration_types": [
                "Sole Proprietorship",
                "Partnership",
                "Private Limited Company",
            ],
            "taxes": [
                {"name": "Corporate Income Tax", "rate": "30%"},
                {"name": "VAT", "rate": "18% (threshold 100M TZS)"},
                {"name": "PAYE", "rate": "Progressive 0% - 30%"},
                {"name": "SDL (Skills Development Levy)", "rate": "4.5% of gross emoluments"},
            ],
            "filing_frequency": "Monthly (VAT, PAYE, SDL), Annual (Corporate Tax)",
            "penalties": "Late filing: 2.5% of tax due per month. Additional penalties for persistent non-compliance.",
            "useful_links": [
                "TRA: www.tra.go.tz",
                "BRELA: www.brela.go.tz",
            ],
            "informal_to_formal_steps": [
                "Register business with BRELA",
                "Obtain TIN from TRA",
                "Register for VAT if turnover exceeds threshold",
                "Open a business bank account",
                "Register for PAYE and SDL if employing staff",
                "File monthly returns via TRA online portal",
            ],
        },
        "ethiopia": {
            "tax_authority": "Ministry of Revenue / Ethiopian Revenue and Customs Authority (ERCA)",
            "business_registrar": "Ministry of Trade and Regional Integration",
            "registration_types": [
                "Sole Proprietorship",
                "Private Limited Company (PLC)",
                "Partnership",
            ],
            "taxes": [
                {"name": "Corporate Income Tax", "rate": "30%"},
                {"name": "VAT", "rate": "15% (threshold 500K ETB)"},
                {"name": "Turnover Tax", "rate": "2% on goods, 10% on services (for small taxpayers below VAT threshold)"},
                {"name": "Withholding Tax", "rate": "2% on goods, 10% on services"},
            ],
            "filing_frequency": "Monthly (VAT, Turnover Tax, Withholding), Annual (Income Tax)",
            "penalties": "Late filing: 10% of tax due. Late payment: 25% penalty + interest.",
            "useful_links": [
                "Ministry of Revenue: www.mor.gov.et",
            ],
            "informal_to_formal_steps": [
                "Register trade name with Ministry of Trade",
                "Obtain a TIN from the Revenue Authority",
                "Register for Turnover Tax (if small) or VAT (if above threshold)",
                "Open a business bank account",
                "Keep all sales and purchase records",
                "File monthly returns",
            ],
        },
        "uganda": {
            "tax_authority": "URA (Uganda Revenue Authority)",
            "business_registrar": "URSB (Uganda Registration Services Bureau)",
            "registration_types": [
                "Sole Proprietorship",
                "Partnership",
                "Private Limited Company",
            ],
            "taxes": [
                {"name": "Corporate Income Tax", "rate": "30%"},
                {"name": "VAT", "rate": "18% (threshold 150M UGX)"},
                {"name": "PAYE", "rate": "Progressive 0% - 40%"},
                {"name": "Presumptive Tax", "rate": "Varies by sector for small taxpayers"},
            ],
            "filing_frequency": "Monthly (VAT, PAYE, withholding), Annual (Income Tax)",
            "penalties": "Late filing: 2% of tax due per month. Late payment: 2% interest per month.",
            "useful_links": [
                "URA: www.ura.go.ug",
                "URSB: www.ursb.go.ug",
            ],
            "informal_to_formal_steps": [
                "Register business name with URSB",
                "Obtain TIN from URA",
                "Register for VAT if turnover exceeds threshold",
                "Open a business bank account",
                "Register for PAYE if you have employees",
                "File monthly returns via URA portal",
            ],
        },
        "rwanda": {
            "tax_authority": "RRA (Rwanda Revenue Authority)",
            "business_registrar": "RDB (Rwanda Development Board)",
            "registration_types": [
                "Sole Proprietorship",
                "Partnership",
                "Private Limited Company",
            ],
            "taxes": [
                {"name": "Corporate Income Tax", "rate": "30%"},
                {"name": "VAT", "rate": "18% (threshold 50M RWF)"},
                {"name": "PAYE", "rate": "Progressive 0% - 30%"},
                {"name": "Withholding Tax", "rate": "15% on dividends, 15% on services"},
            ],
            "filing_frequency": "Monthly (VAT, PAYE, withholding), Annual (Income Tax)",
            "penalties": "Late filing: 10% of tax due. Late payment: 1.5% interest per month.",
            "useful_links": [
                "RRA: www.rra.gov.rw",
                "RDB: rdb.rw",
            ],
            "informal_to_formal_steps": [
                "Register business with RDB (online via IREMBO)",
                "Obtain TIN from RRA",
                "Register for VAT if turnover exceeds threshold",
                "Open a business bank account",
                "Register for PAYE if employing staff",
                "File monthly returns via RRA e-tax system",
            ],
        },
    }

    # ------------------------------------------------------------------
    # get_tax_guide
    # ------------------------------------------------------------------
    def get_tax_guide(
        self,
        country: str,
        business_type: str,
    ) -> Dict[str, Any]:
        """Return comprehensive tax guidance for a country and business type.

        Parameters
        ----------
        country : str
            Country name (e.g., 'nigeria', 'kenya').
        business_type : str
            Type of business (for tailored advice).

        Returns
        -------
        dict
            Tax authority info, applicable taxes, filing requirements, and penalties.
        """
        logger.info("Tax guide: country=%s business=%s", country, business_type)
        country_key = country.lower().replace(" ", "_")
        data = self.TAX_DATA.get(country_key)

        if data is None:
            return {
                "error": f"No tax data available for '{country}'. Supported: {', '.join(SUPPORTED_COUNTRIES)}",
            }

        return {
            "country": country_key,
            "business_type": business_type,
            "tax_authority": data["tax_authority"],
            "business_registrar": data["business_registrar"],
            "registration_types": data["registration_types"],
            "taxes": data["taxes"],
            "filing_frequency": data["filing_frequency"],
            "penalties": data["penalties"],
            "useful_links": data["useful_links"],
            "informal_to_formal_steps": data["informal_to_formal_steps"],
            "tailored_advice": (
                f"For {business_type}: Focus on registering first, then activate your "
                f"tax filings gradually. Most countries offer simplified tax regimes for micro-businesses."
            ),
            "disclaimer": (
                "DISCLAIMER: Tax laws change frequently. Verify all details with the official "
                f"{data['tax_authority']} website or consult a registered tax practitioner. "
                "This information is for educational purposes only."
            ),
        }

    # ------------------------------------------------------------------
    # get_registration_steps
    # ------------------------------------------------------------------
    def get_registration_steps(self, country: str) -> Dict[str, Any]:
        """Return step-by-step business registration process for a country.

        Parameters
        ----------
        country : str
            Country name.

        Returns
        -------
        dict
            Registration authority, steps, costs, and timeline.
        """
        logger.info("Registration steps for %s", country)
        country_key = country.lower().replace(" ", "_")
        data = self.TAX_DATA.get(country_key)

        if data is None:
            return {"error": f"No registration data for '{country}'."}

        steps = data["informal_to_formal_steps"]
        return {
            "country": country_key,
            "registration_authority": data["business_registrar"],
            "tax_authority": data["tax_authority"],
            "steps": [{"step": i + 1, "action": s} for i, s in enumerate(steps)],
            "estimated_timeline": "2 - 8 weeks depending on country and business type",
            "estimated_cost_range": "Varies: 10,000 - 100,000 local currency (sole proprietorship)",
            "tip": "Start with the simplest registration (Business Name / Sole Proprietorship) and upgrade as you grow.",
            "online_registration": "Most countries now offer online registration portals — check the links provided.",
            "disclaimer": (
                "DISCLAIMER: Registration requirements and fees change. Check the official "
                f"{data['business_registrar']} website for current information."
            ),
        }

    # ------------------------------------------------------------------
    # get_tax_calendar
    # ------------------------------------------------------------------
    def get_tax_calendar(self, country: str) -> Dict[str, Any]:
        """Return tax filing deadlines for a given country.

        Parameters
        ----------
        country : str
            Country name.

        Returns
        -------
        dict
            Monthly, quarterly, and annual deadlines.
        """
        logger.info("Tax calendar for %s", country)
        country_key = country.lower().replace(" ", "_")

        calendars: Dict[str, Dict[str, Any]] = {
            "nigeria": {
                "monthly": [
                    {"deadline": "21st of each month", "obligation": "VAT return and payment"},
                    {"deadline": "21st of each month", "obligation": "WHT remittance"},
                    {"deadline": "10th of each month", "obligation": "PAYE remittance (state)"},
                ],
                "annual": [
                    {"deadline": "31st January", "obligation": "Annual income tax return (self-employed)"},
                    {"deadline": "6 months after accounting year-end", "obligation": "Company Income Tax return"},
                ],
            },
            "kenya": {
                "monthly": [
                    {"deadline": "20th of each month", "obligation": "VAT return and payment via iTax"},
                    {"deadline": "9th of each month", "obligation": "PAYE remittance"},
                    {"deadline": "20th of each month", "obligation": "Turnover Tax (if applicable)"},
                ],
                "annual": [
                    {"deadline": "30th June", "obligation": "Annual corporate tax return"},
                    {"deadline": "30th April", "obligation": "Individual tax return"},
                ],
            },
            "south_africa": {
                "monthly": [
                    {"deadline": "25th of each month (or 23rd for e-filing)", "obligation": "PAYE, UIF, SDL"},
                    {"deadline": "End of month (or 25th)", "obligation": "VAT return and payment"},
                ],
                "bi_annual": [
                    {"deadline": "31st August", "obligation": "First provisional tax payment"},
                    {"deadline": "28th February", "obligation": "Second provisional tax payment"},
                ],
                "annual": [
                    {"deadline": "Within 12 months of financial year-end", "obligation": "Annual Income Tax return (ITR14)"},
                ],
            },
            "ghana": {
                "monthly": [
                    {"deadline": "15th of each month", "obligation": "VAT return and payment"},
                    {"deadline": "15th of each month", "obligation": "PAYE remittance"},
                ],
                "quarterly": [
                    {"deadline": "End of quarter (March, June, September, December)", "obligation": "Income tax instalment"},
                ],
                "annual": [
                    {"deadline": "30th April", "obligation": "Annual income tax return"},
                ],
            },
        }

        cal = calendars.get(country_key, {
            "monthly": [
                {"deadline": "Check with local tax authority", "obligation": "VAT and withholding tax"},
            ],
            "annual": [
                {"deadline": "Check with local tax authority", "obligation": "Annual income tax return"},
            ],
        })

        return {
            "country": country_key,
            "calendar": cal,
            "general_advice": [
                "Set calendar reminders 5 days before each deadline.",
                "Use mobile money or online banking for tax payments to avoid queues.",
                "Hire a part-time accountant if you cannot manage filings yourself.",
                "Even with zero transactions, file a nil return to avoid penalties.",
            ],
            "disclaimer": (
                "DISCLAIMER: Filing deadlines may change. Always confirm with the official "
                "tax authority website. This is not legal or tax advice."
            ),
        }

    # ------------------------------------------------------------------
    # get_record_keeping_guide
    # ------------------------------------------------------------------
    def get_record_keeping_guide(self) -> Dict[str, Any]:
        """Return guidance on what records to keep for tax and business purposes.

        Returns
        -------
        dict
            Required records, retention periods, and organisation tips.
        """
        logger.info("Record keeping guide requested")
        return {
            "essential_records": [
                {"record": "Sales invoices / receipts", "why": "Proof of income for tax", "retain": "6 years"},
                {"record": "Purchase invoices / receipts", "why": "Proof of expenses, VAT claims", "retain": "6 years"},
                {"record": "Bank statements", "why": "Reconcile income and expenses", "retain": "6 years"},
                {"record": "Mobile money statements", "why": "Digital transaction evidence", "retain": "6 years"},
                {"record": "Employee records (if applicable)", "why": "PAYE, labour law compliance", "retain": "Duration of employment + 3 years"},
                {"record": "Stock / inventory records", "why": "Cost of goods sold calculation", "retain": "3 years"},
                {"record": "Cash book / petty cash records", "why": "Track all cash movements", "retain": "6 years"},
                {"record": "Contracts and agreements", "why": "Legal protection", "retain": "Duration + 6 years"},
            ],
            "daily_practices": [
                "Record every sale at the time it happens (not at end of day from memory).",
                "File receipts immediately — do not let them pile up.",
                "Reconcile cash and mobile money daily.",
                "Take a photo of paper receipts as backup.",
                "Use a simple notebook or spreadsheet if digital tools are unavailable.",
            ],
            "organisation_tips": [
                "Use one notebook per month. Label clearly (e.g., 'Sales - January 2025').",
                "Separate personal and business transactions completely.",
                "Keep records in a waterproof, fire-safe location.",
                "Back up digital records to cloud storage weekly.",
                "Review records monthly to spot errors early.",
            ],
            "simple_tools": [
                "Notebook + pen (most reliable, no electricity needed)",
                "Spreadsheet (Excel, Google Sheets, LibreOffice Calc)",
                "Mobile apps: Wave, Kippa, or simple notes app",
                "WhatsApp: Send daily totals to yourself as a backup log",
            ],
            "disclaimer": (
                "DISCLAIMER: Retention requirements vary by country. Check with your local "
                "tax authority for specific rules. This is general guidance only."
            ),
        }


# =============================================================================
# CLASS: DigitalMarketing
# =============================================================================

class DigitalMarketing:
    """Digital and local marketing guidance for African micro-businesses
    leveraging mobile-first platforms and community-based channels.
    """

    # ------------------------------------------------------------------
    # get_social_media_guide
    # ------------------------------------------------------------------
    def get_social_media_guide(
        self,
        business_type: str,
    ) -> Dict[str, Any]:
        """Provide social media marketing guidance for a business type.

        Parameters
        ----------
        business_type : str
            Type of business.

        Returns
        -------
        dict
            Platform-specific strategies for WhatsApp, Facebook, and Instagram.
        """
        logger.info("Social media guide for %s", business_type)

        platform_content: Dict[str, Dict[str, Any]] = {
            "retail_shop": {
                "whatsapp": ["Share daily deals via status", "Create a catalog of top products", "Use broadcast lists for promotions"],
                "facebook": ["Post new arrivals", "Run local community group ads", "Share customer testimonials"],
                "instagram": ["Product flat-lays", "Before/after organisation", "Seasonal displays"],
            },
            "food_vendor": {
                "whatsapp": ["Menu of the day via status", "Take pre-orders", "Share location/pickup times"],
                "facebook": ["Food photos with pricing", "Customer review shares", "Live cooking snippets"],
                "instagram": ["High-quality food photography", "Reels of cooking process", "Customer feature stories"],
            },
            "tailoring": {
                "whatsapp": ["Catalog of fabric options", "Status updates of work in progress", "Appointment bookings"],
                "facebook": ["Portfolio of completed designs", "Fashion tips", "Before/after transformations"],
                "instagram": ["Fashion photography", "Design sketches", "Client fitting videos"],
            },
            "hairdressing": {
                "whatsapp": ["Style catalog", "Appointment booking", "Before/after status updates"],
                "facebook": ["Hairstyle gallery", "Product recommendations", "Tutorial videos"],
                "instagram": ["Before/after hair transformations", "Braiding technique Reels", "Client selfies (with permission)"],
            },
            "phone_repair": {
                "whatsapp": ["Service price list", "Quick repair status updates", "Warranty info sharing"],
                "facebook": ["Repair tips and tricks", "Customer reviews", "Common problem solutions"],
                "instagram": ["Repair process videos", "Phone accessory showcases", "Customer unboxing repaired phones"],
            },
        }

        content = platform_content.get(business_type.lower(), {
            "whatsapp": ["Share product/service updates via status", "Catalog of offerings", "Direct customer communication"],
            "facebook": ["Business page with contact info", "Community group engagement", "Regular posting schedule"],
            "instagram": ["Visual product/service showcase", "Behind-the-scenes content", "Customer stories"],
        })

        return {
            "business_type": business_type,
            "platforms": {
                "whatsapp_business": {
                    "why": "Most widely used messaging app in Africa. Free business tools.",
                    "setup_steps": [
                        "Download WhatsApp Business app",
                        "Create a business profile with hours, address, and catalog",
                        "Set up quick replies for common questions",
                        "Use labels to organise chats (New Customer, Pending Payment, etc.)",
                        "Post daily updates to your status (visible to all contacts)",
                    ],
                    "content_ideas": content["whatsapp"],
                    "best_practices": [
                        "Respond within 1 hour during business hours.",
                        "Use professional but friendly language.",
                        "Never spam — 2-3 status updates per day max.",
                        "Include prices in your catalog to reduce back-and-forth.",
                    ],
                },
                "facebook": {
                    "why": "Large user base, free business pages, community groups.",
                    "setup_steps": [
                        "Create a Facebook Business Page",
                        "Add business info, photos, and contact details",
                        "Join local community and buy/sell groups",
                        "Post 3-5 times per week",
                        "Respond to comments and messages promptly",
                    ],
                    "content_ideas": content["facebook"],
                    "best_practices": [
                        "Post at peak times: 12-2pm and 6-9pm.",
                        "Use photos in every post — they get 2x engagement.",
                        "Ask questions to encourage comments.",
                        "Share user-generated content (with permission).",
                    ],
                },
                "instagram": {
                    "why": "Visual platform perfect for product-based businesses.",
                    "setup_steps": [
                        "Create a Business or Creator account",
                        "Write a clear bio with what you sell and location",
                        "Post high-quality photos consistently",
                        "Use relevant hashtags (5-10 per post)",
                        "Engage with local accounts and potential customers",
                    ],
                    "content_ideas": content["instagram"],
                    "best_practices": [
                        "Post 4-7 times per week for growth.",
                        "Use Reels for maximum reach.",
                        "Respond to all comments within 1 hour.",
                        "Collaborate with local micro-influencers.",
                    ],
                },
            },
            "content_calendar_template": {
                "monday": "Motivation / behind-the-scenes",
                "tuesday": "Product showcase / service highlight",
                "wednesday": "Customer testimonial / review",
                "thursday": "Tips and educational content",
                "friday": "Special offer / weekend promo",
                "saturday": "Community / lifestyle content",
                "sunday": "Personal / story content",
            },
            "disclaimer": (
                "DISCLAIMER: Social media strategies should be adapted to your specific "
                "audience and market. Test and measure what works for your business."
            ),
        }

    # ------------------------------------------------------------------
    # get_local_marketing_ideas
    # ------------------------------------------------------------------
    def get_local_marketing_ideas(
        self,
        business_type: str,
        location: str,
    ) -> Dict[str, Any]:
        """Provide offline and community-based marketing ideas.

        Parameters
        ----------
        business_type : str
            Type of business.
        location : str
            City/region.

        Returns
        -------
        dict
            Local marketing strategies, low-cost tactics, and community engagement ideas.
        """
        logger.info("Local marketing ideas: %s in %s", business_type, location)

        return {
            "business_type": business_type,
            "location": location,
            "low_cost_tactics": [
                {
                    "tactic": "Word-of-mouth referral program",
                    "cost": "Free",
                    "how": "Give a small discount or free item to customers who refer friends.",
                },
                {
                    "tactic": "Flyers and posters",
                    "cost": "Low (500-5,000 local currency)",
                    "how": f"Print simple flyers and post at bus stops, churches, and market areas in {location}.",
                },
                {
                    "tactic": "Community event participation",
                    "cost": "Low",
                    "how": "Set up a booth at local markets, church events, or school functions.",
                },
                {
                    "tactic": "Partnerships with complementary businesses",
                    "cost": "Free",
                    "how": "Cross-promote with nearby businesses (e.g., food vendor + tailor = meal + outfit package).",
                },
                {
                    "tactic": "Free samples or demonstrations",
                    "cost": "Low",
                    "how": "Give small free samples to passersby to build trust and showcase quality.",
                },
                {
                    "tactic": "Loyalty cards",
                    "cost": "Very low (printing)",
                    "how": "Stamp card: 'Buy 9, get 1 free' — encourages repeat business.",
                },
                {
                    "tactic": "Branded uniforms or aprons",
                    "cost": "Medium",
                    "how": "Wear branded clothing so you are a walking advertisement.",
                },
            ],
            "community_engagement": [
                f"Join community WhatsApp groups in {location} (with permission of admins).",
                "Sponsor a local sports team or school event.",
                "Offer a discount to community members (e.g., church congregation, association members).",
                "Participate in local clean-up or charity events — builds goodwill.",
                "Become known as the expert in your field — offer free advice.",
            ],
            "traditional_methods": [
                "Radio announcements on local community stations.",
                "Town crier or announcement van in rural areas.",
                "Church/mosque bulletin announcements.",
                "Notice boards at markets, community centres, and transport hubs.",
            ],
            "tracking_tips": [
                "Ask every new customer: 'How did you hear about us?'",
                "Keep a simple log of what marketing you did and sales that followed.",
                "Double down on what works, drop what does not.",
            ],
        }

    # ------------------------------------------------------------------
    # get_branding_basics
    # ------------------------------------------------------------------
    def get_branding_basics(
        self,
        business_name: str,
        business_type: str,
    ) -> Dict[str, Any]:
        """Provide branding fundamentals for a micro-business.

        Parameters
        ----------
        business_name : str
            Current or proposed business name.
        business_type : str
            Type of business.

        Returns
        -------
        dict
            Naming tips, logo guidance, colour psychology, and brand voice advice.
        """
        logger.info("Branding basics for '%s' (%s)", business_name, business_type)

        # Name quality assessment
        name_tips: List[str] = []
        if len(business_name) < 3:
            name_tips.append("Name is too short — may be hard to remember or search for.")
        elif len(business_name) > 25:
            name_tips.append("Name is very long — consider a shorter version for daily use.")
        if " " not in business_name and len(business_name) > 15:
            name_tips.append("Consider adding a space for readability.")
        if any(c.isdigit() for c in business_name):
            name_tips.append("Numbers in names can be confusing — consider spelling them out.")

        colour_psychology = {
            "red": "Energy, urgency, appetite — great for food businesses",
            "blue": "Trust, professionalism — good for services and tech",
            "green": "Growth, health, nature — ideal for farming and organic products",
            "yellow": "Optimism, attention — works for retail and children's products",
            "orange": "Friendly, affordable — great for casual food and services",
            "purple": "Luxury, creativity — good for fashion and crafts",
            "black": "Sophistication, premium — works for high-end any business",
        }

        return {
            "business_name": business_name,
            "business_type": business_type,
            "name_assessment": {
                "current_name": business_name,
                "tips": name_tips if name_tips else ["Name length and format look good!"],
                "naming_best_practices": [
                    "Easy to pronounce and spell",
                    "Memorable and distinctive",
                    "Relevant to what you sell",
                    "Available as a domain name and social media handle",
                    "No negative meanings in local languages",
                    "Check that it is not already trademarked",
                ],
            },
            "logo_guidance": {
                "do_it_yourself": [
                    "Use free tools: Canva, LogoMaker, or Hatchful by Shopify",
                    "Keep it simple — one icon + business name",
                    "Ensure it looks good in black and white (for cheap printing)",
                    "Test it at small sizes (business card, phone screen)",
                ],
                "professional": [
                    "Hire a local graphic designer (5,000-50,000 local currency)",
                    "Get vector files (.AI, .EPS, .SVG) for flexible sizing",
                    "Request versions: full colour, black/white, icon-only",
                ],
                "logo_elements": [
                    "Icon/symbol that represents your business",
                    "Business name in a readable font",
                    "Optional tagline (keep under 5 words)",
                ],
            },
            "colour_psychology": colour_psychology,
            "brand_voice": {
                "description": "How your business 'speaks' to customers",
                "examples": {
                    "friendly": "'Hey there! Welcome to our shop. How can we help you today?'",
                    "professional": "'Welcome. We offer quality services at competitive rates. How may we assist?'",
                    "playful": '"Yo! Check out our latest stuff — you are gonna love it!"',
                    "trustworthy": "'We have served this community for 10 years with honesty and quality.'",
                },
                "tip": "Choose a voice that matches your target customers and stick to it consistently.",
            },
            "one_pager_checklist": [
                f"Business name: {business_name}",
                f"Business type: {business_type}",
                "Logo: designed and saved in multiple formats",
                "Colours: primary + secondary chosen",
                "Brand voice: defined and documented",
                "Business cards: printed with logo and contact info",
                "Signage: shop front branded",
                "Social media: consistent profile pictures and bios",
            ],
        }


# =============================================================================
# CLASS: GrowthAdvisor
# =============================================================================

class GrowthAdvisor:
    """Strategic growth advice for scaling micro and small businesses
    including expansion, hiring, partnerships, and funding options.
    """

    # ------------------------------------------------------------------
    # get_expansion_plan
    # ------------------------------------------------------------------
    def get_expansion_plan(
        self,
        current_business: str,
        target: str,
    ) -> Dict[str, Any]:
        """Generate a growth and expansion plan.

        Parameters
        ----------
        current_business : str
            Current business description.
        target : str
            Growth target description.

        Returns
        -------
        dict
            Expansion strategies, timeline, risks, and action steps.
        """
        logger.info("Expansion plan: current='%s' target='%s'", current_business, target)

        strategies = [
            {
                "strategy": "Market Penetration",
                "description": "Increase sales in existing market with existing products.",
                "actions": ["Increase marketing spend", "Offer promotions", "Improve customer retention"],
                "risk": "Low",
                "timeline": "1-3 months",
            },
            {
                "strategy": "Product Development",
                "description": "Create new products/services for existing customers.",
                "actions": ["Survey customers for needs", "Develop and test new offerings", "Launch to existing base"],
                "risk": "Medium",
                "timeline": "3-6 months",
            },
            {
                "strategy": "Market Expansion",
                "description": "Enter new geographic areas or customer segments.",
                "actions": ["Research new locations", "Adapt offering for new market", "Local marketing campaign"],
                "risk": "Medium",
                "timeline": "3-12 months",
            },
            {
                "strategy": "Diversification",
                "description": "Enter new markets with new products.",
                "actions": ["Market research", "Pilot testing", "Full launch if successful"],
                "risk": "High",
                "timeline": "6-18 months",
            },
        ]

        return {
            "current_business": current_business,
            "growth_target": target,
            "expansion_strategies": strategies,
            "recommended_approach": (
                "Start with Market Penetration (lowest risk), then move to Product Development, "
                "followed by Market Expansion. Only diversify after the core business is stable."
            ),
            "financial_planning": [
                "Calculate the capital required for each expansion step.",
                "Ensure current cash flow is positive and stable for 6+ months.",
                "Build a 3-month emergency fund before expanding.",
                "Project revenue and costs for the expansion — do not rely on hope.",
            ],
            "risk_mitigation": [
                "Start small — test before committing fully.",
                "Keep your core business running while testing expansion.",
                "Have an exit plan if the expansion does not work.",
                "Do not borrow heavily for unproven expansion ideas.",
            ],
            "milestones": [
                {"phase": 1, "duration": "Month 1-3", "focus": "Strengthen core, increase marketing"},
                {"phase": 2, "duration": "Month 4-6", "focus": "Develop new products/services"},
                {"phase": 3, "duration": "Month 7-12", "focus": "Expand to new locations or segments"},
                {"phase": 4, "duration": "Month 13-18", "focus": "Evaluate and scale what works"},
            ],
            "disclaimer": (
                "DISCLAIMER: Expansion involves risk. Conduct thorough research and ensure "
                "your core business is stable before growing. This is guidance, not guaranteed strategy."
            ),
        }

    # ------------------------------------------------------------------
    # get_hiring_guide
    # ------------------------------------------------------------------
    def get_hiring_guide(
        self,
        business_size: str,
    ) -> Dict[str, Any]:
        """Provide guidance on when and how to hire employees.

        Parameters
        ----------
        business_size : str
            Current business size category (micro, very_small, small).

        Returns
        -------
        dict
            Hiring signals, recruitment tips, legal considerations, and cost analysis.
        """
        logger.info("Hiring guide for business size: %s", business_size)

        size_recs = {
            "micro": {
                "when_to_hire": "You are turning away customers or working 12+ hours daily consistently.",
                "first_role": "An assistant/apprentice to handle routine tasks while you focus on growth.",
                "max_staff": 1,
            },
            "very_small": {
                "when_to_hire": "Revenue has been growing for 3+ months and you need specialised skills.",
                "first_role": "A specialist (e.g., a stylist for a salon, a cook for a restaurant).",
                "max_staff": 4,
            },
            "small": {
                "when_to_hire": "You need management help or cannot handle operations alone.",
                "first_role": "A supervisor or operations manager to oversee daily activities.",
                "max_staff": 10,
            },
        }

        rec = size_recs.get(business_size.lower(), size_recs["micro"])

        return {
            "business_size": business_size,
            "when_to_hire": rec["when_to_hire"],
            "recommended_first_hire": rec["first_role"],
            "max_recommended_staff": rec["max_staff"],
            "hiring_process": [
                "1. Define the role clearly — what tasks, hours, and skills needed.",
                "2. Set a budget — salary + benefits + training + equipment.",
                "3. Recruit through word-of-mouth, community notice boards, or local networks.",
                "4. Interview at least 3 candidates — check references.",
                "5. Start with a probation period (1-3 months) with clear expectations.",
                "6. Provide training and a written agreement/contract.",
            ],
            "legal_considerations": [
                "Register for PAYE (Pay As You Earn) tax with your tax authority.",
                "Understand minimum wage laws in your country.",
                "Provide payslips showing gross pay, deductions, and net pay.",
                "Comply with social security / pension contributions if applicable.",
                "Maintain employee records (contracts, attendance, leave).",
                "Provide a safe working environment.",
            ],
            "cost_analysis": {
                "direct_costs": ["Monthly salary", "Social security / pension contributions", "Health insurance (if applicable)"],
                "indirect_costs": ["Training time and materials", "Equipment and workspace", "Supervision time", "Recruitment costs"],
                "rule_of_thumb": "Total cost of an employee = 1.2x to 1.5x their base salary (including all extras).",
            },
            "alternatives_to_hiring": [
                "Train an existing family member or apprentice.",
                "Outsource specific tasks (e.g., accounting, delivery).",
                "Use technology to automate (e.g., POS system, WhatsApp auto-replies).",
                "Partner with another business for shared labour (e.g., shared delivery).",
            ],
            "disclaimer": (
                "DISCLAIMER: Employment laws vary by country. Consult a labour lawyer or "
                "your country's labour department for specific requirements."
            ),
        }

    # ------------------------------------------------------------------
    # get_partnership_guide
    # ------------------------------------------------------------------
    def get_partnership_guide(self) -> Dict[str, Any]:
        """Provide guidance on business partnerships and collaborations.

        Returns
        -------
        dict
            Partnership types, due diligence checklist, agreement essentials, and red flags.
        """
        logger.info("Partnership guide requested")

        return {
            "partnership_types": [
                {
                    "type": "Supply Partnership",
                    "description": "Partner with suppliers for better pricing or exclusive supply.",
                    "example": "A restaurant partners with a local farm for fresh vegetables.",
                },
                {
                    "type": "Distribution Partnership",
                    "description": "Partner with someone who can sell or deliver your products.",
                    "example": "A baker partners with local shops to stock their bread.",
                },
                {
                    "type": "Marketing Partnership",
                    "description": "Cross-promote with complementary businesses.",
                    "example": "A tailor and a hairdresser refer customers to each other.",
                },
                {
                    "type": "Joint Venture",
                    "description": "Temporary partnership for a specific project or market.",
                    "example": "Two farmers jointly buy processing equipment and share costs.",
                },
                {
                    "type": "Equity Partnership",
                    "description": "Give a share of your business in exchange for capital or skills.",
                    "example": "A tech partner joins a retail business to build an online store for equity.",
                },
            ],
            "due_diligence_checklist": [
                "Check the partner's reputation in the community.",
                "Review their financial records (if possible).",
                "Verify their business registration and tax compliance.",
                "Speak to their previous partners or customers.",
                "Start with a small trial collaboration before committing fully.",
                "Define exit terms before you start — how to end the partnership if needed.",
            ],
            "agreement_essentials": [
                "Roles and responsibilities of each partner",
                "Capital contribution (money, assets, skills)",
                "Profit and loss sharing ratio",
                "Decision-making process",
                "Dispute resolution mechanism",
                "Duration of partnership and exit clauses",
                "Non-compete clauses (if applicable)",
                "Confidentiality terms",
            ],
            "red_flags": [
                "Partner wants control without contributing capital or work.",
                "Partner has a history of failed businesses or disputes.",
                "Partner refuses to put the agreement in writing.",
                "Partner's goals and values do not align with yours.",
                "Partner pressures you to decide immediately.",
            ],
            "written_agreement_tip": (
                "ALWAYS put partnerships in writing — even with friends and family. "
                "Verbal agreements lead to the most business disputes. A simple written contract "
                "signed by both parties is legally binding in most African countries."
            ),
            "disclaimer": (
                "DISCLAIMER: Partnership agreements should be reviewed by a lawyer. "
                "This guide provides general principles only and is not legal advice."
            ),
        }

    # ------------------------------------------------------------------
    # get_funding_options
    # ------------------------------------------------------------------
    def get_funding_options(
        self,
        business_stage: str,
    ) -> Dict[str, Any]:
        """Provide funding options appropriate for a given business stage.

        Parameters
        ----------
        business_stage : str
            Stage: idea, startup, growth, established, or expansion.

        Returns
        -------
        dict
            Funding types, eligibility, pros/cons, and application tips.
        """
        logger.info("Funding options for stage: %s", business_stage)
        stage = business_stage.lower()

        all_options = [
            {
                "type": "Personal Savings",
                "stages": ["idea", "startup"],
                "amount_range": "Up to personal capacity",
                "pros": ["No debt", "Full control", "No interest"],
                "cons": ["Limited amount", "Personal financial risk"],
                "how_to_access": "Set aside a portion of income weekly or monthly.",
            },
            {
                "type": "Family and Friends",
                "stages": ["idea", "startup"],
                "amount_range": "Small amounts (10K - 500K local)",
                "pros": ["Flexible terms", "Low or no interest", "Quick access"],
                "cons": ["Can strain relationships", "Informal — no legal protection"],
                "how_to_access": "Present a simple business plan. Put the loan in writing.",
            },
            {
                "type": "Microfinance Loan",
                "stages": ["startup", "growth"],
                "amount_range": "50K - 5M local currency",
                "pros": ["Accessible to unbanked", "Group lending options", "Builds credit history"],
                "cons": ["Interest rates can be high (20-40%)", "Short repayment periods", "May require collateral or group guarantee"],
                "how_to_access": "Join a microfinance institution (e.g., LAPO, FINCA, BRAC). Attend group meetings. Apply with business plan.",
            },
            {
                "type": "Bank Loan",
                "stages": ["growth", "established", "expansion"],
                "amount_range": "500K - 50M+ local currency",
                "pros": ["Larger amounts", "Longer terms", "Structured repayment"],
                "cons": ["Requires collateral", "Strict documentation", "Lengthy approval process", "High rejection rate for small businesses"],
                "how_to_access": "Open a business account, build transaction history, prepare financial statements, apply with collateral.",
            },
            {
                "type": "Government Grant",
                "stages": ["startup", "growth"],
                "amount_range": "Varies by programme",
                "pros": ["Non-repayable", "No equity given up", "Credibility boost"],
                "cons": ["Highly competitive", "Bureaucratic application", "Long waiting periods", "Specific eligibility criteria"],
                "how_to_access": "Check your country's SME development agency, youth fund, or women's enterprise fund.",
            },
            {
                "type": "Angel Investor",
                "stages": ["growth", "expansion"],
                "amount_range": "1M - 50M local currency",
                "pros": ["Mentorship included", "Large amounts", "Networking access"],
                "cons": ["Give up equity", "Loss of some control", "Investor may have different vision"],
                "how_to_access": "Pitch at startup events, join angel networks (e.g., Lagos Angel Network, Savannah Fund).",
            },
            {
                "type": "Crowdfunding",
                "stages": ["startup", "growth"],
                "amount_range": "Varies — depends on campaign success",
                "pros": ["Validates product demand", "Marketing exposure", "No equity or debt (for rewards-based)"],
                "cons": ["Requires strong marketing effort", "Platform fees (5-10%)", "All-or-nothing models risk failure"],
                "how_to_access": "Use platforms like Kickstarter, Indiegogo, or local crowdfunding sites. Create a compelling video and story.",
            },
            {
                "type": "Mobile Money / Fintech Loan",
                "stages": ["startup", "growth"],
                "amount_range": "Small (5K - 500K local)",
                "pros": ["Instant approval", "No paperwork", "Builds digital credit score"],
                "cons": ["Very high interest rates", "Short terms (days to months)", "Can lead to debt cycle"],
                "how_to_access": "Use M-Shwari, Branch, Tala, or your mobile money provider's credit feature. Use only for short-term working capital.",
            },
            {
                "type": "Supplier Credit",
                "stages": ["startup", "growth", "established"],
                "amount_range": "Varies by supplier relationship",
                "pros": ["No cash outlay upfront", "Builds supplier relationship", "Flexible"],
                "cons": ["Higher unit cost", "Limited to inventory only", "Damage relationship if not paid on time"],
                "how_to_access": "Negotiate 30-day or 60-day payment terms with trusted suppliers after establishing a track record.",
            },
        ]

        relevant = [opt for opt in all_options if stage in opt["stages"]]

        return {
            "business_stage": stage,
            "funding_options": relevant,
            "recommendation": (
                f"For {stage} stage: Start with personal savings and family, then explore "
                f"microfinance. As you grow, consider bank loans and supplier credit. "
                f"Avoid high-interest digital loans for long-term needs."
            ),
            "application_tips": [
                "Prepare a simple but clear business plan (1-2 pages).",
                "Keep financial records — lenders and investors will ask for them.",
                "Register your business formally — most funders require this.",
                "Build a relationship with a bank before you need a loan.",
                "Start small with any funder to build trust and a track record.",
            ],
            "warning": (
                "WARNING: Avoid borrowing from multiple sources simultaneously. "
                "Debt stacking can quickly lead to business failure. Borrow only what you "
                "can realistically repay from business cash flow."
            ),
            "disclaimer": (
                "DISCLAIMER: Funding availability and terms vary by country and lender. "
                "Always read the full terms and conditions before accepting any funding. "
                "This is not financial advice."
            ),
        }


# =============================================================================
# CLASS: RecordKeeper
# =============================================================================

class RecordKeeper:
    """SQLite-backed bookkeeping system for creating ledgers, invoices,
    receipts, and financial reports. Designed for businesses with limited
    accounting knowledge.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        """Initialise the RecordKeeper with a database path.

        Parameters
        ----------
        db_path : str or Path, optional
            Path to SQLite database. Defaults to RECORDS_DB.
        """
        self.db_path = Path(db_path) if db_path else RECORDS_DB
        _init_db(self.db_path)
        logger.info("RecordKeeper initialised with DB: %s", self.db_path)

    # ------------------------------------------------------------------
    # create_ledger_template
    # ------------------------------------------------------------------
    def create_ledger_template(self) -> Dict[str, Any]:
        """Return a simple ledger template structure and create the DB table.

        Returns
        -------
        dict
            Ledger structure, sample entries, and guidance.
        """
        logger.info("Creating ledger template")
        template = {
            "ledger_structure": {
                "columns": ["Date", "Description", "Debit (Money Out)", "Credit (Money In)", "Category", "Running Balance"],
                "explanation": (
                    "Debit = money going out (expenses, purchases). "
                    "Credit = money coming in (sales, income). "
                    "Running Balance = previous balance + credit - debit."
                ),
            },
            "sample_entries": [
                {"date": "2025-01-01", "description": "Opening balance", "debit": 0, "credit": 50000, "category": "capital", "balance": 50000},
                {"date": "2025-01-02", "description": "Bought stock", "debit": 15000, "credit": 0, "category": "inventory", "balance": 35000},
                {"date": "2025-01-03", "description": "Daily sales", "debit": 0, "credit": 8000, "category": "sales", "balance": 43000},
                {"date": "2025-01-04", "description": "Rent payment", "debit": 10000, "credit": 0, "category": "rent", "balance": 33000},
            ],
            "categories": [
                "sales", "inventory", "rent", "salaries", "utilities",
                "transport", "marketing", "loan_repayment", "personal_drawings",
                "equipment", "tax", "miscellaneous",
            ],
            "how_to_use": [
                "Record EVERY transaction on the day it happens.",
                "Categorise each entry for easier analysis.",
                "Reconcile weekly: cash + mobile money + bank = ledger balance.",
                "Review monthly to see where money is going.",
            ],
            "disclaimer": (
                "DISCLAIMER: This is a simplified cash-based ledger. For accrual accounting "
                "or complex businesses, consult a professional accountant."
            ),
        }
        return template

    # ------------------------------------------------------------------
    # create_invoice_template
    # ------------------------------------------------------------------
    def create_invoice_template(
        self,
        business_id: str = "default",
        customer: str = "Customer Name",
        items: Optional[List[Dict[str, Any]]] = None,
        tax_rate: float = 0.0,
    ) -> Dict[str, Any]:
        """Generate an invoice template and optionally save to database.

        Parameters
        ----------
        business_id : str
            Unique business identifier.
        customer : str
            Customer name.
        items : list of dict, optional
            Invoice line items with 'description', 'quantity', 'unit_price'.
        tax_rate : float
            Tax rate as percentage.

        Returns
        -------
        dict
            Invoice details, formatted output, and DB save status.
        """
        logger.info("Creating invoice for customer=%s business=%s", customer, business_id)
        invoice_no = f"INV-{uuid.uuid4().hex[:8].upper()}"

        if items is None:
            items = [
                {"description": "Sample Product A", "quantity": 2, "unit_price": 5000},
                {"description": "Sample Service B", "quantity": 1, "unit_price": 10000},
            ]

        subtotal = sum(item["quantity"] * item["unit_price"] for item in items)
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount
        issue_date = date.today().isoformat()
        due_date = (date.today() + timedelta(days=30)).isoformat()

        # Save to DB
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO invoices (invoice_no, business_id, customer, amount, tax_rate, total, issue_date, due_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (invoice_no, business_id, customer, subtotal, tax_rate, total, issue_date, due_date),
            )
            conn.commit()
            conn.close()
            db_status = "saved"
        except sqlite3.Error as exc:
            logger.error("Failed to save invoice: %s", exc)
            db_status = f"error: {exc}"

        formatted = (
            f"{'=' * 60}\n"
            f"INVOICE\n"
            f"{'=' * 60}\n"
            f"Invoice No:  {invoice_no}\n"
            f"Date:        {issue_date}\n"
            f"Due Date:    {due_date}\n"
            f"Customer:    {customer}\n"
            f"{'-' * 60}\n"
            f"{'Description':<30} {'Qty':>5} {'Unit':>10} {'Total':>10}\n"
            f"{'-' * 60}\n"
        )
        for item in items:
            line_total = item["quantity"] * item["unit_price"]
            formatted += f"{item['description']:<30} {item['quantity']:>5} {item['unit_price']:>10,.2f} {line_total:>10,.2f}\n"
        formatted += (
            f"{'-' * 60}\n"
            f"{'Subtotal':>46} {subtotal:>10,.2f}\n"
        )
        if tax_rate > 0:
            formatted += f"{'Tax (' + str(tax_rate) + '%)':>46} {tax_amount:>10,.2f}\n"
        formatted += (
            f"{'TOTAL':>46} {total:>10,.2f}\n"
            f"{'=' * 60}\n"
            f"Payment due within 30 days. Thank you for your business!\n"
            f"{'=' * 60}"
        )

        return {
            "invoice_no": invoice_no,
            "business_id": business_id,
            "customer": customer,
            "issue_date": issue_date,
            "due_date": due_date,
            "items": items,
            "subtotal": round(subtotal, 2),
            "tax_rate": tax_rate,
            "tax_amount": round(tax_amount, 2),
            "total": round(total, 2),
            "formatted": formatted,
            "db_status": db_status,
        }

    # ------------------------------------------------------------------
    # create_receipt_template
    # ------------------------------------------------------------------
    def create_receipt_template(
        self,
        business_id: str = "default",
        customer: str = "",
        amount: float = 0.0,
        payment_method: str = "cash",
    ) -> Dict[str, Any]:
        """Generate a receipt and save to database.

        Parameters
        ----------
        business_id : str
            Business identifier.
        customer : str
            Customer name (optional).
        amount : float
            Amount received.
        payment_method : str
            cash, mobile_money, bank_transfer, or card.

        Returns
        -------
        dict
            Receipt details, formatted output, and DB status.
        """
        logger.info("Creating receipt: amount=%s method=%s", amount, payment_method)
        receipt_no = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        issue_date = date.today().isoformat()

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO receipts (receipt_no, business_id, customer, amount, payment_method, issue_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (receipt_no, business_id, customer, amount, payment_method, issue_date),
            )
            conn.commit()
            conn.close()
            db_status = "saved"
        except sqlite3.Error as exc:
            logger.error("Failed to save receipt: %s", exc)
            db_status = f"error: {exc}"

        formatted = (
            f"{'=' * 50}\n"
            f"RECEIPT\n"
            f"{'=' * 50}\n"
            f"Receipt No:     {receipt_no}\n"
            f"Date:           {issue_date}\n"
            f"Customer:       {customer or 'Walk-in Customer'}\n"
            f"Amount:         {amount:,.2f}\n"
            f"Payment Method: {payment_method.replace('_', ' ').title()}\n"
            f"{'=' * 50}\n"
            f"Thank you for your business!\n"
            f"Goods sold are not returnable after 7 days.\n"
            f"{'=' * 50}"
        )

        return {
            "receipt_no": receipt_no,
            "business_id": business_id,
            "customer": customer,
            "amount": round(amount, 2),
            "payment_method": payment_method,
            "issue_date": issue_date,
            "formatted": formatted,
            "db_status": db_status,
        }

    # ------------------------------------------------------------------
    # get_financial_report_template
    # ------------------------------------------------------------------
    def get_financial_report_template(
        self,
        period: str = "monthly",
    ) -> Dict[str, Any]:
        """Return a financial report template for a given period.

        Parameters
        ----------
        period : str
            'monthly', 'quarterly', or 'annual'.

        Returns
        -------
        dict
            Report template with structure, formulas, and sample data.
        """
        logger.info("Financial report template for period: %s", period)
        period = period.lower()

        if period == "monthly":
            title = "Monthly Financial Report"
            date_range = f"{date.today().strftime('%B %Y')}"
        elif period == "quarterly":
            title = "Quarterly Financial Report"
            q = ((date.today().month - 1) // 3) + 1
            date_range = f"Q{q} {date.today().year}"
        elif period == "annual":
            title = "Annual Financial Report"
            date_range = str(date.today().year)
        else:
            title = "Financial Report"
            date_range = "Custom Period"

        template = {
            "title": title,
            "period": date_range,
            "sections": {
                "income_summary": {
                    "heading": "1. Income Summary",
                    "items": [
                        {"line": "Total Sales (Cash)", "formula": "Sum of all cash sales receipts"},
                        {"line": "Total Sales (Mobile Money)", "formula": "Sum of all mobile money receipts"},
                        {"line": "Total Sales (Credit)", "formula": "Sum of all credit sales (not yet paid)"},
                        {"line": "Other Income", "formula": "Any non-sales income"},
                        {"line": "TOTAL INCOME", "formula": "Sum of all above"},
                    ],
                },
                "expense_summary": {
                    "heading": "2. Expense Summary",
                    "items": [
                        {"line": "Cost of Goods Sold (COGS)", "formula": "Opening stock + purchases - closing stock"},
                        {"line": "Rent", "formula": "Total rent paid in period"},
                        {"line": "Salaries/Wages", "formula": "Total staff payments"},
                        {"line": "Utilities (Electricity, Water)", "formula": "Total utility bills"},
                        {"line": "Transport", "formula": "Business transport costs"},
                        {"line": "Marketing", "formula": "All marketing and advertising spend"},
                        {"line": "Loan Repayments", "formula": "Total loan principal + interest paid"},
                        {"line": "Other Expenses", "formula": "Miscellaneous business expenses"},
                        {"line": "TOTAL EXPENSES", "formula": "Sum of all above"},
                    ],
                },
                "profit_loss": {
                    "heading": "3. Profit & Loss",
                    "items": [
                        {"line": "Gross Profit", "formula": "Total Income - COGS"},
                        {"line": "Net Profit", "formula": "Gross Profit - Total Other Expenses"},
                        {"line": "Profit Margin %", "formula": "(Net Profit / Total Income) * 100"},
                    ],
                },
                "cash_position": {
                    "heading": "4. Cash Position",
                    "items": [
                        {"line": "Cash on Hand", "formula": "Physical cash counted"},
                        {"line": "Mobile Money Balance", "formula": "Balance in business mobile money wallet"},
                        {"line": "Bank Balance", "formula": "Business bank account balance"},
                        {"line": "TOTAL CASH", "formula": "Sum of all above"},
                    ],
                },
                "outstanding": {
                    "heading": "5. Outstanding Items",
                    "items": [
                        {"line": "Money Owed to You (Debtors)", "formula": "Unpaid customer invoices"},
                        {"line": "Money You Owe (Creditors)", "formula": "Unpaid supplier bills"},
                        {"line": "Net Position", "formula": "Debtors - Creditors"},
                    ],
                },
            },
            "sample_data": {
                "total_income": 150000,
                "total_expenses": 105000,
                "net_profit": 45000,
                "profit_margin_pct": 30.0,
                "cash_on_hand": 25000,
                "mobile_money_balance": 35000,
                "bank_balance": 50000,
                "total_cash": 110000,
                "debtors": 15000,
                "creditors": 10000,
            },
            "how_to_use": [
                f"1. Gather all records for the {period} period.",
                "2. Fill in each line item with actual amounts.",
                "3. Calculate totals using the formulas provided.",
                "4. Compare this period to the previous period to spot trends.",
                "5. Use the report to make decisions: cut costs, increase prices, or invest.",
            ],
            "disclaimer": (
                "DISCLAIMER: This is a simplified template for cash-based micro-businesses. "
                "For formal financial reporting, depreciation, accruals, and tax calculations, "
                "consult a qualified accountant."
            ),
        }
        return template

    # ------------------------------------------------------------------
    # Database query helpers
    # ------------------------------------------------------------------
    def get_all_invoices(self, business_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve all invoices for a business from the database.

        Parameters
        ----------
        business_id : str
            Business identifier.

        Returns
        -------
        list of dict
            Invoice records.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM invoices WHERE business_id = ? ORDER BY issue_date DESC",
                (business_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve invoices: %s", exc)
            return []

    def get_all_receipts(self, business_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve all receipts for a business from the database.

        Parameters
        ----------
        business_id : str
            Business identifier.

        Returns
        -------
        list of dict
            Receipt records.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM receipts WHERE business_id = ? ORDER BY issue_date DESC",
                (business_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve receipts: %s", exc)
            return []

    def get_unpaid_invoices(self, business_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve unpaid invoices for a business.

        Parameters
        ----------
        business_id : str
            Business identifier.

        Returns
        -------
        list of dict
            Unpaid invoice records.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM invoices WHERE business_id = ? AND paid = 0 ORDER BY due_date ASC",
                (business_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except sqlite3.Error as exc:
            logger.error("Failed to retrieve unpaid invoices: %s", exc)
            return []

    def mark_invoice_paid(self, invoice_no: str) -> bool:
        """Mark an invoice as paid.

        Parameters
        ----------
        invoice_no : str
            Invoice number.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("UPDATE invoices SET paid = 1 WHERE invoice_no = ?", (invoice_no,))
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated
        except sqlite3.Error as exc:
            logger.error("Failed to mark invoice paid: %s", exc)
            return False


# =============================================================================
# Module-level convenience functions
# =============================================================================

def business_advice(
    query: str,
    location: str,
    business_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Provide general business advice based on a query.

    Parameters
    ----------
    query : str
        The advice query (e.g., 'how to price my products').
    location : str
        City and country.
    business_type : str, optional
        Type of business for tailored advice.

    Returns
    -------
    dict
        Advice response with relevant guidance.
    """
    logger.info("Business advice query='%s' location='%s' type='%s'", query, location, business_type)

    query_lower = query.lower()
    planner = BusinessPlanner()
    market = MarketAdvisor()
    digital = DigitalMarketing()
    growth = GrowthAdvisor()

    response: Dict[str, Any] = {
        "query": query,
        "location": location,
        "business_type": business_type,
        "disclaimer": (
            "DISCLAIMER: This is general business guidance, not professional advice. "
            "Consult a qualified business advisor for your specific situation."
        ),
    }

    if any(k in query_lower for k in ["price", "pricing", "how much to charge"]):
        if business_type:
            response["advice"] = market.get_pricing_guide(business_type, location)
        else:
            response["advice"] = {
                "topic": "Pricing",
                "general_tips": [
                    "Calculate your total cost per unit (materials + labour + overhead).",
                    "Research competitor prices in your area.",
                    "Add your desired profit margin (typically 20-50% for micro-businesses).",
                    "Test your price — if no one complains, you may be too cheap.",
                    "Review and adjust prices every 3-6 months.",
                ],
            }
    elif any(k in query_lower for k in ["market", "demand", "competition", "research"]):
        if business_type:
            response["advice"] = market.get_market_research(business_type, location)
        else:
            response["advice"] = {
                "topic": "Market Research",
                "general_tips": [
                    "Walk around your target area and count competitors.",
                    "Talk to 20+ potential customers about their needs and pain points.",
                    "Observe peak hours and buying patterns.",
                    "Check social media and online forums for demand signals.",
                    "Start small and test before full investment.",
                ],
            }
    elif any(k in query_lower for k in ["marketing", "advertise", "promote", "customer"]):
        if business_type:
            response["advice"] = {
                "social_media": digital.get_social_media_guide(business_type),
                "local_marketing": digital.get_local_marketing_ideas(business_type, location),
                "customer_strategy": market.get_customer_strategy(business_type),
            }
        else:
            response["advice"] = {
                "topic": "Marketing",
                "general_tips": [
                    "Start with word-of-mouth — it is free and most trusted.",
                    "Set up WhatsApp Business with a product catalog.",
                    "Post regularly on Facebook community groups.",
                    "Offer a referral discount to existing customers.",
                    "Participate in community events for visibility.",
                ],
            }
    elif any(k in query_lower for k in ["grow", "expand", "scale", "hire"]):
        response["advice"] = growth.get_expansion_plan(
            current_business=business_type or "your business",
            target="grow customer base and revenue",
        )
    elif any(k in query_lower for k in ["plan", "business plan", "start"]):
        if business_type:
            try:
                response["advice"] = planner.create_business_plan(business_type, 100000, location)
            except ValueError:
                response["advice"] = {"error": f"Unknown business type '{business_type}'"}
        else:
            response["advice"] = {
                "topic": "Starting a Business",
                "steps": planner.get_startup_checklist("retail_shop"),
            }
    elif any(k in query_lower for k in ["idea", "business idea", "what business"]):
        response["advice"] = planner.get_business_ideas(location, 50000, "general")
    else:
        response["advice"] = {
            "topic": "General Business Advice",
            "tips": [
                "Start with what you know and have passion for.",
                "Keep costs low in the beginning — bootstrap.",
                "Focus on one product/service before diversifying.",
                "Build relationships with customers — they are your best marketers.",
                "Track every shilling/cedi/naira — know your numbers.",
                "Formalise your business early to access bigger opportunities.",
                "Seek mentorship from successful business owners in your community.",
            ],
        }

    return response


def financial_plan(
    income: float,
    expenses: List[Dict[str, Any]],
    goals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a comprehensive financial plan.

    Parameters
    ----------
    income : float
        Monthly income.
    expenses : list of dict
        Expense items with 'name', 'amount', 'category', 'is_essential' keys.
    goals : list of dict
        Financial goals with 'name', 'amount', 'timeline_months' keys.

    Returns
    -------
    dict
        Budget, savings plans, and recommendations.
    """
    logger.info("Financial plan: income=%s expenses=%d goals=%d", income, len(expenses), len(goals))
    fm = FinancialManager()

    budget_items = [BudgetItem(
        name=e.get("name", "Expense"),
        amount=e.get("amount", 0),
        category=e.get("category", "general"),
        is_essential=e.get("is_essential", True),
    ) for e in expenses]

    budget = fm.create_budget(income, budget_items)

    savings_plans = []
    for goal in goals:
        plan = fm.get_savings_plan(
            income=income,
            goal=goal.get("amount", 0),
            timeline_months=goal.get("timeline_months", 12),
        )
        savings_plans.append({
            "goal_name": goal.get("name", "Unnamed Goal"),
            "plan": plan,
        })

    return {
        "budget": budget,
        "savings_plans": savings_plans,
        "summary": {
            "monthly_income": income,
            "total_expenses": budget["total_expenses"],
            "balance": budget["balance"],
            "savings_rate": budget["savings_rate_pct"],
            "num_goals": len(goals),
        },
        "recommendations": budget["recommendations"] + [
            "Review your budget every month and adjust as needed.",
            "Build an emergency fund of 3 months' expenses before investing.",
            "Separate business and personal finances completely.",
        ],
        "disclaimer": (
            "DISCLAIMER: This is a simplified financial planning tool for educational purposes. "
            "It does not constitute professional financial advice. Consult a financial advisor "
            "for personalised guidance."
        ),
    }


def register_business(
    country: str,
    business_type: str,
) -> Dict[str, Any]:
    """Get business registration guidance for a country.

    Parameters
    ----------
    country : str
        Country name.
    business_type : str
        Type of business.

    Returns
    -------
    dict
        Registration steps, tax requirements, and timeline.
    """
    logger.info("Registration guidance: country=%s type=%s", country, business_type)
    tax = TaxCompliance()
    planner = BusinessPlanner()

    return {
        "country": country,
        "business_type": business_type,
        "registration_guide": tax.get_registration_steps(country),
        "tax_guide": tax.get_tax_guide(country, business_type),
        "tax_calendar": tax.get_tax_calendar(country),
        "record_keeping": tax.get_record_keeping_guide(),
        "startup_checklist": planner.get_startup_checklist(business_type),
        "disclaimer": (
            "DISCLAIMER: Registration requirements change frequently. Verify all details "
            "with the official business registrar and tax authority in your country. "
            "This information is for guidance only and not legal advice."
        ),
    }


def market_research(
    product: str,
    location: str,
) -> Dict[str, Any]:
    """Conduct market research for a product in a location.

    Parameters
    ----------
    product : str
        Product or service type.
    location : str
        City/region.

    Returns
    -------
    dict
        Market analysis, pricing, suppliers, and customer strategy.
    """
    logger.info("Market research: product=%s location=%s", product, location)
    market = MarketAdvisor()

    return {
        "product": product,
        "location": location,
        "market_research": market.get_market_research(product, location),
        "pricing_guide": market.get_pricing_guide(product, location),
        "supplier_guide": market.get_supplier_guide(product, location),
        "customer_strategy": market.get_customer_strategy(product),
        "disclaimer": (
            "DISCLAIMER: This is a preliminary market analysis. Always conduct "
            "on-the-ground research to validate findings for your specific location "
            "and target market."
        ),
    }


def business_plan(
    business_type: str,
    capital: float,
    location: str,
) -> Dict[str, Any]:
    """Generate a complete business plan.

    Parameters
    ----------
    business_type : str
        Type of business (key from BUSINESS_TEMPLATES).
    capital : float
        Available startup capital.
    location : str
        City and country.

    Returns
    -------
    dict
        Full business plan with projections and supporting guidance.
    """
    logger.info("Business plan: type=%s capital=%s location=%s", business_type, capital, location)
    planner = BusinessPlanner()
    market = MarketAdvisor()
    digital = DigitalMarketing()

    plan = planner.create_business_plan(business_type, capital, location)

    return {
        "business_plan": plan,
        "market_research": market.get_market_research(business_type, location),
        "pricing_guide": market.get_pricing_guide(business_type, location),
        "customer_strategy": market.get_customer_strategy(business_type),
        "social_media_guide": digital.get_social_media_guide(business_type),
        "startup_checklist": planner.get_startup_checklist(business_type),
        "disclaimer": (
            "DISCLAIMER: This business plan is generated for planning and educational "
            "purposes only. Actual business performance will vary. This is not professional "
            "financial or business advice. Consult a qualified advisor before making investment decisions."
        ),
    }


# =============================================================================
# Main execution block (for testing and CLI usage)
# =============================================================================

if __name__ == "__main__":
    # Quick demo of all major classes
    print("=" * 70)
    print("LUQI AI v20 - Business Advisor for Africa")
    print("=" * 70)

    print("\n--- BusinessPlanner Demo ---")
    planner = BusinessPlanner()
    bp = planner.create_business_plan("food_vendor", 50000, "Nairobi, Kenya")
    print(bp["executive_summary"][:300] + "...")
    ideas = planner.get_business_ideas("Lagos, Nigeria", 100000, "cooking, computer")
    print(f"Business ideas found: {len(ideas)}")
    for idea in ideas[:3]:
        print(f"  - {idea['business_type']} (suitability: {idea['suitability']})")
    checklist = planner.get_startup_checklist("food_vendor")
    print(f"Startup checklist items: {len(checklist)}")

    print("\n--- FinancialManager Demo ---")
    fm = FinancialManager()
    expenses = [
        BudgetItem("Rent", 15000, "housing", True),
        BudgetItem("Food Stock", 8000, "inventory", True),
        BudgetItem("Transport", 3000, "operations", True),
        BudgetItem("Phone/Data", 2000, "utilities", True),
        BudgetItem("Entertainment", 1500, "lifestyle", False),
    ]
    budget = fm.create_budget(45000, expenses)
    print(budget["formatted"])
    savings = fm.get_savings_plan(45000, 100000, 12)
    print(f"Savings plan feasible: {savings['is_feasible']}")
    loan = fm.get_loan_info(50000, 24, 12)
    print(f"Loan monthly payment: {loan['monthly_payment']:,.2f}")
    mm_guide = fm.get_mobile_money_guide("kenya")
    print(f"Mobile money providers in Kenya: {len(mm_guide.get('providers', []))}")

    print("\n--- MarketAdvisor Demo ---")
    market = MarketAdvisor()
    pricing = market.get_pricing_guide("food_vendor", "Nairobi, Kenya")
    print(f"Pricing tip: {pricing['pricing_tip'][:80]}...")
    research = market.get_market_research("food_vendor", "Nairobi, Kenya")
    print(f"Season status: {research['demand_assessment']['current_season']}")

    print("\n--- TaxCompliance Demo ---")
    tax = TaxCompliance()
    guide = tax.get_tax_guide("nigeria", "retail_shop")
    print(f"Nigeria tax authority: {guide['tax_authority']}")
    reg = tax.get_registration_steps("kenya")
    print(f"Kenya registration steps: {len(reg['steps'])}")

    print("\n--- DigitalMarketing Demo ---")
    dm = DigitalMarketing()
    sm = dm.get_social_media_guide("food_vendor")
    print(f"Social platforms covered: {len(sm['platforms'])}")
    branding = dm.get_branding_basics("Mama's Kitchen", "food_vendor")
    print(f"Branding for: {branding['business_name']}")

    print("\n--- GrowthAdvisor Demo ---")
    growth = GrowthAdvisor()
    expansion = growth.get_expansion_plan("food_vendor", "open second location")
    print(f"Expansion strategies: {len(expansion['expansion_strategies'])}")
    funding = growth.get_funding_options("startup")
    print(f"Funding options for startup: {len(funding['funding_options'])}")

    print("\n--- RecordKeeper Demo ---")
    rk = RecordKeeper()
    ledger = rk.create_ledger_template()
    print(f"Ledger categories: {len(ledger['categories'])}")
    invoice = rk.create_invoice_template(
        customer="John Doe",
        items=[
            {"description": "Rice and Stew", "quantity": 2, "unit_price": 500},
            {"description": "Delivery", "quantity": 1, "unit_price": 200},
        ],
        tax_rate=7.5,
    )
    print(f"Invoice total: {invoice['total']:,.2f}")
    receipt = rk.create_receipt_template(customer="Jane Smith", amount=1200, payment_method="mobile_money")
    print(f"Receipt saved: {receipt['db_status']}")
    report = rk.get_financial_report_template("monthly")
    print(f"Report sections: {len(report['sections'])}")

    print("\n--- Module Functions Demo ---")
    advice = business_advice("how to price my food", "Accra, Ghana", "food_vendor")
    print(f"Advice topic matched: {list(advice['advice'].keys()) if isinstance(advice['advice'], dict) else 'string'}")
    fp = financial_plan(50000, [
        {"name": "Rent", "amount": 15000, "category": "housing", "is_essential": True},
        {"name": "Stock", "amount": 10000, "category": "inventory", "is_essential": True},
    ], [{"name": "Equipment", "amount": 60000, "timeline_months": 6}])
    print(f"Financial plan balance: {fp['summary']['balance']:,.2f}")

    print("\n" + "=" * 70)
    print("All demos completed successfully!")
    print("DISCLAIMER: This system provides educational business information only.")
    print("It does NOT constitute professional financial, legal, or tax advice.")
    print("=" * 70)
