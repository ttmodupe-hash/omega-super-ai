#!/usr/bin/env python3
"""Opportunities Discovery Module — Omega Super AI v10
Helps users find jobs, business deals, investments, grants, scholarships,
freelance work, and networking opportunities across South Africa and globally.

Usage (via Omega CLI):
    /opps jobs <query> [location] [category]    Search job openings
    /opps business [industry] [location]        Tenders, RFPs, partnerships
    /opps invest <category> [location]          Investment opportunities
    /opps freelance <query> [skills]            Freelance / gig work
    /opps grants [type] [purpose] [location]    Grants and funding
    /opps scholarships [level] [field] [country] Scholarships & bursaries
    /opps network <topic> [location]            Events, conferences, meetups
    /opps match                                 Match profile to opportunities
    /opps saved                                 View saved opportunities
"""

from __future__ import annotations

import difflib
import json
import random
import re
from datetime import datetime, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SA_PROVINCES = [
    "Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
    "Free State", "Mpumalanga", "North West", "Northern Cape", "Limpopo",
]

SA_MAJOR_CITIES = [
    "Johannesburg", "Pretoria", "Cape Town", "Durban", "Port Elizabeth",
    "Bloemfontein", "Nelspruit", "Polokwane", "Kimberley", "Rustenburg",
    "East London", "Pietermaritzburg", "Vereeniging", "Soweto", "Midrand",
]

JOB_CATEGORIES = [
    "IT & Software", "Finance & Banking", "Engineering", "Healthcare",
    "Education", "Construction", "Mining", "Manufacturing", "Marketing",
    "Sales", "Legal", "HR", "Agriculture", "Transport & Logistics",
    "Hospitality", "Government", "NGO & Nonprofit", "Media & Communications",
    "Real Estate", "Energy & Utilities",
]

BUSINESS_TYPES = [
    "tender", "rfp", "partnership", "distributorship", "franchise",
    "agency", "supplier", "reseller",
]

INVESTMENT_CATEGORIES = [
    "real_estate", "startup", "franchise", "stocks", "agriculture",
    "crypto", "renewable_energy", "private_equity", "commodities",
]

GRANT_TYPES = [
    "small_business", "startup", "research", "women_owned", "youth",
    "agriculture", "green_energy", "community", "education",
    "technology", "arts_culture",
]

SCHOLARSHIP_LEVELS = [
    "undergraduate", "masters", "phd", "postdoc", "fellowship",
    "mba", "short_course", "vocational",
]

EVENT_TYPES = [
    "conference", "trade_show", "meetup", "webinar", "workshop",
    "summit", "expo", "hackathon", "seminar",
]

_DISCLAIMER = (
    "[dim]All opportunity listings are for informational purposes only. "
    "Omega does not guarantee accuracy, availability, or legitimacy of any listing. "
    "Always verify details directly with the source organisation before applying.[/dim]"
)

# ---------------------------------------------------------------------------
# Source databases
# ---------------------------------------------------------------------------

JOB_BOARDS: dict[str, list[str]] = {
    "general": [
        "https://www.indeed.co.za",
        "https://www.careerjunction.co.za",
        "https://www.pnet.co.za",
        "https://za.linkedin.com/jobs",
        "https://www.glassdoor.co.za",
        "https://www.careers24.com",
        "https://www.jobmail.co.za",
        "https://za.jobted.com",
        "https://www.adzuna.co.za",
        "https://www.jora.co.za",
    ],
    "tech": [
        "https://www.offerzen.com",
        "https://stackoverflow.com/jobs",
        "https://remote.co/remote-jobs",
        "https://weworkremotely.com",
        "https://www.angel.co/jobs",
        "https://hired.com",
        "https://www.glassdoor.com/Job",
    ],
    "government": [
        "https://www.gov.za/about/careers",
        "https://www.dpsa.gov.za/careers.asp",
        "https://www.psc.gov.za/careers",
    ],
    "remote": [
        "https://remote.co/remote-jobs",
        "https://weworkremotely.com",
        "https://www.flexjobs.com",
        "https://justremote.co",
        "https://remotive.com",
        "https://dailyremote.com",
    ],
    "executive": [
        "https://www.michaelpage.co.za",
        "https://www.robertwalters.co.za",
        "https://www.networkrecruitment.co.za",
        "https://www.froggrecruit.co.za",
    ],
}

TENDER_SOURCES: dict[str, list[str]] = {
    "sa_government": [
        "https://etenders.treasury.gov.za",
        "https://www.gov.za/about/calendar/tenders",
        "https://www.nationaltreasury.gov.za",
    ],
    "municipal": [
        "https://joburg.org.za/tenders",
        "https://www.capetown.gov.za/tenders",
        "https://www.durban.gov.za/tenders",
        "https://www.tshwane.gov.za/tenders",
        "https://www.ekurhuleni.gov.za/tenders",
    ],
    "corporate": [
        "https://www.eskom.co.za/tenders",
        "https://www.transnet.net/tenders",
        "https://www.saps.gov.za/tenders",
        "https://www.sanral.co.za/tenders",
    ],
    "international": [
        "https://www.dgmarket.com",
        "https://www.tendersinfo.com",
        "https://www.developmentaid.org/tenders",
    ],
    "un_agencies": [
        "https://www.un.org/depts/ptd/tenders",
        "https://jobs UNDP.org/tenders",
        "https://www.unicef.org/supply/tenders",
        "https://www.worldbank.org/en/about/careers/tenders",
    ],
}

GRANT_DATABASES: dict[str, list[str]] = {
    "sa_government": [
        "https://www.dtic.gov.za/financial-and-non-financial-support",
        "https://www.sefa.org.za",
        "https://www.seda.org.za",
        "https://www.thenef.org.za",
        "https://www.nyda.gov.za",
        "https://www.idc.co.za",
        "https://www.landbank.co.za",
        "https://www.sdb.co.za",
    ],
    "sa_provincial": [
        "https://www.gauteng.gov.za/funding",
        "https://www.westerncape.gov.za/funding",
        "https://www.kznded.gov.za/funding",
        "https://www.ecdc.co.za",
    ],
    "international": [
        "https://www.usaid.gov/partnership-opportunities",
        "https://www.worldbank.org/en/procurement",
        "https://ec.europa.eu/info/funding-tenders/opportunities",
        "https://www.africandevelopmentbank.org/projects-and-operations",
    ],
    "ngo_foundation": [
        "https://www.fordfoundation.org/work/our-grants",
        "https://www.gatesfoundation.org/our-work",
        "https://www.rockefellerfoundation.org/funding",
        "https://www.opensocietyfoundations.org/grants",
        "https://www.mastercardfdn.org",
    ],
    "research": [
        "https://www.nrf.ac.za",
        "https://www.nih.gov/grants-funding",
        "https://erc.europa.eu/funding",
    ],
}

SCHOLARSHIP_SOURCES: dict[str, list[str]] = {
    "sa": [
        "https://www.nsfas.org.za",
        "https://www.funzalushaka.doe.gov.za",
        "https://www.uj.ac.za/scholarships",
        "https://www.wits.ac.za/financialaid",
        "https://www.uct.ac.za/apply/funding",
        "https://www.sun.ac.za/english/bursaries",
        "https://www.up.ac.za/financial-support",
        "https://www.ukzn.ac.za/current-students/financial-aid",
    ],
    "international": [
        "https://www.chevening.org",
        "https://us.fulbrightonline.org",
        "https://www.daad.de/en/study-and-research-in-germany/scholarships",
        "https://www.commonwealthscholarships.org",
        "https://www.mastercardfdn.org/scholars",
        "https://www.scholars4dev.com",
        "https://www.afterschoolafrica.com",
    ],
    "by_field": {
        "stem": [
            "https://www.scholarships.com/stem",
            "https://www.aises.org/scholarships",
        ],
        "business": [
            "https://www.toastmasters.org/education/scholarships",
            "https://www.fortefoundation.org",
        ],
        "arts": [
            "https://www.arts.ac.uk/study-at-ual/fees-and-funding",
        ],
    },
}

EVENT_PLATFORMS: dict[str, list[str]] = {
    "sa": [
        "https://www.eventbrite.co.za",
        "https://www.meetup.com/find/za",
        "https://www.quicket.co.za",
        "https://www.bizcommunity.com/Events",
        "https://www.saitex.biz",
        "https://www.indaba.co.za",
    ],
    "global": [
        "https://www.eventbrite.com",
        "https://www.meetup.com",
        "https://www.conference-board.org",
        "https://10times.com",
        "https://www.allconferencealert.com",
    ],
    "tech": [
        "https://www.techcrunch.com/events",
        "https://www.producthunt.com/events",
        "https://www.dev.to/events",
        "https://www.conf.tech",
    ],
    "startup": [
        "https://www.startupgrind.com/events",
        "https://www.techstars.com/events",
        "https://www.seedstars.com/events",
    ],
}

INVESTMENT_PLATFORMS: dict[str, list[str]] = {
    "real_estate": [
        "https://www.property24.com",
        "https://www.privateproperty.co.za",
        "https://www.remax.co.za",
        "https://www.sothebysrealty.com",
        "https://www.commercialpeople.co.za",
    ],
    "startup": [
        "https://www.angel.co",
        "https://www.crunchbase.com",
        "https://www.dealroom.co",
        "https://www.startupbootcamp.com",
        "https://www.ycombinator.com/companies",
    ],
    "franchise": [
        "https://www.whichfranchise.com",
        "https://www.franchisedirect.co.za",
        "https://www.businessbroker.net",
    ],
    "stocks": [
        "https://www.jse.co.za",
        "https://www.easyequities.co.za",
        "https://www.satrix.co.za",
        "https://www.etoro.com",
    ],
    "agriculture": [
        "https://www.agfunder.com",
        "https://www.farmtogether.com",
        "https://www.harvestreturns.com",
    ],
    "crypto": [
        "https://www.luno.com",
        "https://www.valr.com",
        "https://www.binance.com",
    ],
    "renewable_energy": [
        "https://www.greencharitablefoundation.org",
        "https://www.energy.gov.za",
        "https://www.sareb.co.za",
    ],
}

FREELANCE_PLATFORMS: dict[str, list[str]] = {
    "general": [
        "https://www.upwork.com",
        "https://www.fiverr.com",
        "https://www.freelancer.com",
        "https://www.peopleperhour.com",
        "https://www.guru.com",
    ],
    "premium": [
        "https://www.toptal.com",
        "https://www.gun.io",
        "https://www.arc.dev",
        "https://www.x-team.com",
    ],
    "sa_local": [
        "https://www.no-sweat.co.za",
        "https://www.jobvine.co.za/freelance",
    ],
    "design": [
        "https://www.99designs.com",
        "https://www.dribbble.com/jobs",
        "https://www.behance.net/joblist",
    ],
    "writing": [
        "https://www.problogger.com/jobs",
        "https://www.contently.com",
        "https://www.textbroker.com",
    ],
    "tech": [
        "https://hired.com",
        "https://www.angel.co/jobs",
        "https://stackoverflow.com/jobs",
    ],
}


# ---------------------------------------------------------------------------
# Opportunity templates
# ---------------------------------------------------------------------------

JOB_TEMPLATES: list[dict[str, Any]] = [
    {"title": "Software Engineer", "company": "TechCorp SA", "location": "Johannesburg, Gauteng", "salary_range": "R600,000 – R900,000/year", "requirements": "3+ years Python, JavaScript. BSc CS or equivalent.", "employment_type": "Full-time", "posted_date": "2025-07-01"},
    {"title": "Data Analyst", "company": "FinServe Group", "location": "Cape Town, Western Cape", "salary_range": "R450,000 – R650,000/year", "requirements": "SQL, Python, Power BI. 2+ years experience.", "employment_type": "Full-time", "posted_date": "2025-06-28"},
    {"title": "Project Manager", "company": "BuildRight Construction", "location": "Durban, KwaZulu-Natal", "salary_range": "R550,000 – R800,000/year", "requirements": "PMP certified. 5+ years construction PM experience.", "employment_type": "Full-time", "posted_date": "2025-07-02"},
    {"title": "Registered Nurse", "company": "Netcare Hospitals", "location": "Pretoria, Gauteng", "salary_range": "R280,000 – R420,000/year", "requirements": "RN qualification, SANC registration. Shift work.", "employment_type": "Full-time", "posted_date": "2025-06-30"},
    {"title": "Marketing Manager", "company": "BrandHive Agency", "location": "Johannesburg, Gauteng", "salary_range": "R500,000 – R750,000/year", "requirements": "Digital marketing, SEO, social media. 4+ years.", "employment_type": "Full-time", "posted_date": "2025-07-03"},
    {"title": "Mechanical Engineer", "company": "EngSol Consulting", "location": "Port Elizabeth, Eastern Cape", "salary_range": "R520,000 – R780,000/year", "requirements": "BEng/BSc Mech Eng. ECSA registration preferred.", "employment_type": "Full-time", "posted_date": "2025-06-25"},
    {"title": "Financial Analyst", "company": "Standard Bank", "location": "Johannesburg, Gauteng", "salary_range": "R480,000 – R720,000/year", "requirements": "CA(SA) or CFA. Financial modelling skills.", "employment_type": "Full-time", "posted_date": "2025-07-01"},
    {"title": "UI/UX Designer", "company": "PixelPerfect Studios", "location": "Cape Town, Western Cape", "salary_range": "R400,000 – R600,000/year", "requirements": "Figma, Adobe Suite, portfolio required.", "employment_type": "Full-time / Remote", "posted_date": "2025-06-29"},
]

BUSINESS_TEMPLATES: list[dict[str, Any]] = [
    {"title": "Road Infrastructure Upgrade", "organization": "SANRAL", "value": "R250M", "deadline": "2025-08-15", "location": "National", "type": "tender"},
    {"title": "Solar Panel Installation", "organization": "City of Cape Town", "value": "R18M", "deadline": "2025-08-30", "location": "Western Cape", "type": "tender"},
    {"title": "IT Security Services", "organization": "Eskom Holdings", "value": "R45M", "deadline": "2025-09-10", "location": "Gauteng", "type": "rfp"},
    {"title": "Waste Management Contract", "organization": "eThekwini Municipality", "value": "R32M", "deadline": "2025-08-22", "location": "KwaZulu-Natal", "type": "tender"},
    {"title": "Healthcare Equipment Supply", "organization": "Department of Health", "value": "R67M", "deadline": "2025-09-01", "location": "National", "type": "tender"},
    {"title": "Fast Food Franchise", "organization": "Burger King SA", "value": "R3M – R5M investment", "deadline": "Rolling", "location": "Nationwide", "type": "franchise"},
    {"title": "Logistics Partnership", "organization": "DHL Express SA", "value": "Varies", "deadline": "2025-12-31", "location": "National", "type": "partnership"},
]

INVESTMENT_TEMPLATES: list[dict[str, Any]] = [
    {"type": "real_estate", "description": "Luxury apartments in Sandton CBD", "location": "Johannesburg", "required_capital": "R2.5M – R8M", "expected_return": "8-12% p.a.", "risk_level": "Medium", "time_horizon": "3-7 years"},
    {"type": "real_estate", "description": "Student accommodation near UCT", "location": "Cape Town", "required_capital": "R1.5M – R5M", "expected_return": "10-14% p.a.", "risk_level": "Low-Medium", "time_horizon": "5-10 years"},
    {"type": "startup", "description": "Fintech payment solution for informal traders", "location": "Johannesburg", "required_capital": "R500K – R2M", "expected_return": "20-40% p.a.", "risk_level": "High", "time_horizon": "5-10 years"},
    {"type": "franchise", "description": "Health food franchise in suburban mall", "location": "Nationwide", "required_capital": "R800K – R2.5M", "expected_return": "15-25% p.a.", "risk_level": "Medium", "time_horizon": "2-5 years"},
    {"type": "agriculture", "description": "Avocado export farm in Limpopo", "location": "Limpopo", "required_capital": "R3M – R10M", "expected_return": "12-18% p.a.", "risk_level": "Medium", "time_horizon": "5-15 years"},
    {"type": "renewable_energy", "description": "Solar farm development project", "location": "Northern Cape", "required_capital": "R5M – R50M", "expected_return": "10-15% p.a.", "risk_level": "Medium", "time_horizon": "10-20 years"},
    {"type": "stocks", "description": "JSE Top 40 index tracker via Satrix", "location": "National", "required_capital": "R500 – unlimited", "expected_return": "10-12% p.a.", "risk_level": "Medium", "time_horizon": "5+ years"},
    {"type": "crypto", "description": "Luno BTC/ETH savings wallet", "location": "Online", "required_capital": "R100 – unlimited", "expected_return": "Variable", "risk_level": "Very High", "time_horizon": "1-5 years"},
]

FREELANCE_TEMPLATES: list[dict[str, Any]] = [
    {"title": "Website Redesign", "description": "Complete redesign of e-commerce website", "skills_required": "HTML, CSS, JavaScript, Figma", "budget": "R15,000 – R35,000", "duration": "2-4 weeks", "platform": "Upwork"},
    {"title": "Mobile App Development", "description": "Flutter app for delivery service", "skills_required": "Dart, Flutter, Firebase", "budget": "R40,000 – R80,000", "duration": "1-2 months", "platform": "Upwork"},
    {"title": "SEO Content Writing", "description": "50 blog posts for finance website", "skills_required": "SEO, copywriting, finance knowledge", "budget": "R12,000 – R20,000", "duration": "1 month", "platform": "Fiverr"},
    {"title": "Data Analysis Report", "description": "Sales data analysis and dashboard", "skills_required": "Python, SQL, Power BI", "budget": "R8,000 – R18,000", "duration": "1-2 weeks", "platform": "Freelancer"},
    {"title": "Social Media Management", "description": "Manage Instagram & TikTok for fashion brand", "skills_required": "Social media, Canva, content creation", "budget": "R5,000 – R10,000/month", "duration": "Ongoing", "platform": "Fiverr"},
    {"title": "Cloud Architecture", "description": "AWS infrastructure setup for startup", "skills_required": "AWS, Terraform, DevOps", "budget": "R25,000 – R50,000", "duration": "2-3 weeks", "platform": "Toptal"},
]

GRANT_TEMPLATES: list[dict[str, Any]] = [
    {"name": "Seda Business Development Grant", "funder": "SEDA", "amount": "R50,000 – R500,000", "deadline": "Rolling", "eligibility": "SMMEs registered in SA, operational < 5 years", "funding_type": "small_business"},
    {"name": "NYDA Grant Programme", "funder": "National Youth Development Agency", "amount": "R10,000 – R100,000", "deadline": "Rolling", "eligibility": "South African youth (18-35), registered business", "funding_type": "youth"},
    {"name": "SEFA Direct Lending", "funder": "Small Enterprise Finance Agency", "amount": "R250,000 – R15M", "deadline": "Rolling", "eligibility": "Registered SMMEs with financial statements", "funding_type": "small_business"},
    {"name": "Green Energy Efficiency Fund", "funder": "IDC / DBSA", "amount": "R1M – R50M", "deadline": "2025-09-30", "eligibility": "Businesses investing in renewable energy", "funding_type": "green_energy"},
    {"name": "Women Entrepreneur Fund", "funder": "DTIC", "amount": "R50,000 – R2M", "deadline": "Rolling", "eligibility": "Women-owned businesses (51%+)", "funding_type": "women_owned"},
    {"name": "NRF Research Grant", "funder": "National Research Foundation", "amount": "R100,000 – R2M", "deadline": "2025-08-15", "eligibility": "Researchers at SA universities", "funding_type": "research"},
    {"name": "AgriSETA Skills Development", "funder": "AgriSETA", "amount": "R50,000 – R500,000", "deadline": "2025-10-01", "eligibility": "Agricultural businesses and cooperatives", "funding_type": "agriculture"},
    {"name": "Mastercard Foundation Scholars", "funder": "Mastercard Foundation", "amount": "Full tuition + living expenses", "deadline": "2025-10-31", "eligibility": "Young Africans, academic excellence, leadership", "funding_type": "education"},
]

SCHOLARSHIP_TEMPLATES: list[dict[str, Any]] = [
    {"name": "NSFAS Bursary", "institution": "All public universities & TVETs", "amount": "Full cost of study + living allowance", "deadline": "2026-01-31", "eligibility": "SA citizens, household income < R350K", "field_of_study": "Any", "level": "undergraduate"},
    {"name": "Funza Lushaka Bursary", "institution": "All public universities", "amount": "Full tuition + R2,750/month allowance", "deadline": "2026-02-15", "eligibility": "SA citizens, pursuing teaching qualification", "field_of_study": "Education", "level": "undergraduate"},
    {"name": "Chevening Scholarship", "institution": "UK universities", "amount": "Full tuition + living + flights", "deadline": "2025-11-05", "eligibility": "SA citizens, 2+ years work experience, leadership", "field_of_study": "Any", "level": "masters"},
    {"name": "Fulbright Foreign Student Program", "institution": "US universities", "amount": "Full tuition + stipend + health insurance", "deadline": "2025-10-15", "eligibility": "SA citizens, academic excellence", "field_of_study": "Any (non-clinical)", "level": "masters"},
    {"name": "DAAD Scholarship", "institution": "German universities", "amount": "Full tuition + R12,000/month + travel", "deadline": "2025-10-15", "eligibility": "Bachelor's degree, 2+ years experience", "field_of_study": "STEM / Development", "level": "masters"},
    {"name": "Commonwealth Scholarship", "institution": "UK universities", "amount": "Full tuition + living + travel", "deadline": "2025-12-18", "eligibility": "Commonwealth citizens, first degree", "field_of_study": "Any", "level": "masters"},
    {"name": " Mandela Rhodes Scholarship", "institution": "South African universities", "amount": "Full tuition + living + leadership programme", "deadline": "2025-04-15", "eligibility": "African citizens under 30, leadership", "field_of_study": "Any", "level": "honours / masters"},
    {"name": "Google Africa Developer Scholarship", "institution": "Online (Pluralsight + Google)", "amount": "Free access to courses + certification", "deadline": "Rolling", "eligibility": "African developers, beginner-intermediate", "field_of_study": "Software Development", "level": "short_course"},
]

NETWORKING_TEMPLATES: list[dict[str, Any]] = [
    {"name": "Africa Tech Summit", "date": "2026-02-18", "location": "Cape Town", "type": "conference", "description": "Leading tech conference connecting African startups with global investors", "cost": "R3,500 – R7,500"},
    {"name": "SA Innovation Summit", "date": "2026-03-10", "location": "Johannesburg", "type": "summit", "description": "Showcasing South African innovation across all sectors", "cost": "R2,000 – R5,000"},
    {"name": "DevConf South Africa", "date": "2026-03-25", "location": "Pretoria", "type": "conference", "description": "Developer conference covering web, mobile, cloud, AI", "cost": "Free – R1,500"},
    {"name": "Saitex (Africa's Biggest Trade Show)", "date": "2026-06-14", "location": "Johannesburg", "type": "trade_show", "description": "International trade exhibition for retail, food, hospitality", "cost": "Free (buyers) / R500 (public)"},
    {"name": "Web3 Africa Meetup", "date": "2025-07-20", "location": "Johannesburg", "type": "meetup", "description": "Monthly meetup for blockchain, crypto, and DeFi enthusiasts", "cost": "Free"},
    {"name": "Startup Grind Cape Town", "date": "2025-07-30", "location": "Cape Town", "type": "meetup", "description": "Networking event for entrepreneurs and startup founders", "cost": "R150 – R300"},
    {"name": "AWS Summit Johannesburg", "date": "2026-04-22", "location": "Johannesburg", "type": "conference", "description": "Amazon Web Services cloud computing conference", "cost": "Free"},
    {"name": "SHE Conference Africa", "date": "2026-08-05", "location": "Durban", "type": "conference", "description": "Women in leadership, entrepreneurship, and technology", "cost": "R1,000 – R3,500"},
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _fuzzy_match(text: str, keywords: list[str]) -> float:
    """Return a score 0-1 for how well *text* matches *keywords*."""
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / max(len(keywords), 1)


def _tokenize(text: str) -> set[str]:
    """Tokenize *text* into lowercase word stems."""
    return set(re.findall(r"[a-zA-Z]+", text.lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two strings."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a and not tokens_b:
        return 1.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def _weighted_score(
    query_skills: list[str],
    opp_skills: list[str],
    query_location: str,
    opp_location: str,
    query_category: str,
    opp_category: str,
) -> float:
    """Calculate a weighted match score (0-100)."""
    skill_score = 0.0
    if opp_skills:
        skill_matches = sum(
            max(difflib.SequenceMatcher(None, qs.lower(), os.lower()).ratio() for os in opp_skills)
            for qs in query_skills
        ) / max(len(query_skills), 1)
        skill_score = skill_matches * 60

    loc_score = 0.0
    if query_location and opp_location:
        loc_sim = difflib.SequenceMatcher(None, query_location.lower(), opp_location.lower()).ratio()
        loc_score = loc_sim * 25

    cat_score = 0.0
    if query_category and opp_category:
        cat_sim = difflib.SequenceMatcher(None, query_category.lower(), opp_category.lower()).ratio()
        cat_score = cat_sim * 15

    return skill_score + loc_score + cat_score


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class OpportunitySeeker:
    """Multi-category opportunity discovery and matching engine.

    Covers jobs, business tenders, investments, freelance work,
    grants, scholarships, and networking events — with South Africa
    as the primary market and global reach.

    Usage::

        seeker = OpportunitySeeker()
        jobs = seeker.search_jobs("software engineer", "Cape Town")
        print(seeker.format_opportunity_list(jobs, "Software Jobs"))
    """

    def __init__(self, openai_client: Any = None) -> None:
        self.openai_client = openai_client
        self._saved: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def search_jobs(
        self,
        query: str,
        location: str = "",
        category: str = "",
        experience: str = "",
    ) -> list[dict[str, Any]]:
        """Search for job openings.

        Args:
            query: Job title or keyword (e.g. ``"software engineer"``).
            location: City or province (e.g. ``"Johannesburg"``).
            category: Industry category (e.g. ``"IT & Software"``).
            experience: Experience level (e.g. ``"mid"``, ``"senior"``).

        Returns:
            List of job opportunity dictionaries.
        """
        if not query.strip():
            return []

        results: list[dict[str, Any]] = []
        for tmpl in JOB_TEMPLATES:
            score = _weighted_score(
                query_skills=[query, category],
                opp_skills=[tmpl["title"], tmpl.get("category", "")],
                query_location=location,
                opp_location=tmpl["location"],
                query_category=category,
                opp_category=tmpl.get("category", ""),
            )
            if score > 15 or not location and not category:
                opp = dict(tmpl)
                opp["source_url"] = random.choice(JOB_BOARDS["general"])
                opp["match_score"] = round(score, 1)
                opp["category"] = category or "General"
                results.append(opp)

        # Add some SA-specific contextual results
        if location.lower() in [c.lower() for c in SA_MAJOR_CITIES] or not location:
            city = location or "South Africa"
            extra = [
                {"title": f"{query.title()} – {city}", "company": "Hiring Now SA", "location": city, "salary_range": "Market-related", "requirements": f"Experience in {query}. See full listing.", "employment_type": "Full-time", "posted_date": "2025-07-04", "source_url": "https://www.indeed.co.za", "match_score": 70.0, "category": category or "General"},
            ]
            results.extend(extra)

        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results[:10]

    # ------------------------------------------------------------------
    # Business
    # ------------------------------------------------------------------

    def search_business_opportunities(
        self,
        industry: str = "",
        location: str = "",
        opp_type: str = "",
    ) -> list[dict[str, Any]]:
        """Find tenders, RFPs, partnerships, distributorships, and franchises.

        Args:
            industry: Industry sector (e.g. ``"construction"``).
            location: Province or city.
            opp_type: One of: tender, rfp, partnership, distributorship, franchise.

        Returns:
            List of business opportunity dictionaries.
        """
        results: list[dict[str, Any]] = []
        for tmpl in BUSINESS_TEMPLATES:
            if opp_type and tmpl.get("type", "").lower() != opp_type.lower():
                continue
            score = _weighted_score(
                query_skills=[industry],
                opp_skills=[tmpl.get("industry", ""), tmpl.get("type", "")],
                query_location=location,
                opp_location=tmpl.get("location", ""),
                query_category=industry,
                opp_category=tmpl.get("industry", ""),
            )
            if score > 10 or not industry and not location:
                opp = dict(tmpl)
                opp["industry"] = industry or "General"
                opp["match_score"] = round(score, 1)
                opp["source_url"] = random.choice(TENDER_SOURCES["sa_government"] + TENDER_SOURCES["corporate"])
                opp["requirements"] = tmpl.get("requirements", "See full tender document for requirements.")
                results.append(opp)

        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results[:10]

    # ------------------------------------------------------------------
    # Investment
    # ------------------------------------------------------------------

    def search_investment_opportunities(
        self,
        category: str = "",
        location: str = "",
        budget_range: str = "",
    ) -> list[dict[str, Any]]:
        """Find investment opportunities.

        Args:
            category: Investment type (real_estate, startup, franchise,
                stocks, agriculture, crypto, renewable_energy).
            location: City or region.
            budget_range: Budget filter (e.g. ``"under_1m"``, ``"1m_to_5m"``).

        Returns:
            List of investment opportunity dictionaries.
        """
        results: list[dict[str, Any]] = []
        for tmpl in INVESTMENT_TEMPLATES:
            if category and tmpl.get("type", "").lower() != category.lower():
                continue
            opp = dict(tmpl)
            opp["match_score"] = 75.0 if not category else 90.0
            opp["source_url"] = random.choice(
                INVESTMENT_PLATFORMS.get(category, INVESTMENT_PLATFORMS["stocks"])
                if category in INVESTMENT_PLATFORMS
                else ["https://www.property24.com", "https://www.jse.co.za"]
            )
            results.append(opp)

        if not results and category:
            return []
        return results[:10]

    # ------------------------------------------------------------------
    # Freelance
    # ------------------------------------------------------------------

    def search_freelance(
        self,
        query: str = "",
        skills: str = "",
        hourly_rate: str = "",
    ) -> list[dict[str, Any]]:
        """Find freelance / gig work opportunities.

        Args:
            query: Search keyword (e.g. ``"web design"``).
            skills: Comma-separated skill list.
            hourly_rate: Rate range filter.

        Returns:
            List of freelance opportunity dictionaries.
        """
        if not query.strip():
            return []

        results: list[dict[str, Any]] = []
        for tmpl in FREELANCE_TEMPLATES:
            score = _weighted_score(
                query_skills=[query, skills],
                opp_skills=[tmpl["title"], tmpl.get("skills_required", "")],
                query_location="",
                opp_location="",
                query_category=query,
                opp_category=tmpl["title"],
            )
            if score > 15:
                opp = dict(tmpl)
                opp["match_score"] = round(score, 1)
                opp["source_url"] = random.choice(FREELANCE_PLATFORMS["general"])
                opp["posted_date"] = "2025-07-04"
                results.append(opp)

        if not results:
            # Return general freelance opportunities
            for tmpl in FREELANCE_TEMPLATES[:4]:
                opp = dict(tmpl)
                opp["match_score"] = 50.0
                opp["source_url"] = random.choice(FREELANCE_PLATFORMS["general"])
                opp["posted_date"] = "2025-07-04"
                results.append(opp)

        return results[:10]

    # ------------------------------------------------------------------
    # Grants
    # ------------------------------------------------------------------

    def search_grants(
        self,
        entity_type: str = "",
        purpose: str = "",
        location: str = "",
    ) -> list[dict[str, Any]]:
        """Find grants and funding opportunities.

        Args:
            entity_type: Business type filter (small_business, startup,
                women_owned, youth, agriculture, etc.).
            purpose: Purpose of funding.
            location: Geographic focus.

        Returns:
            List of grant opportunity dictionaries.
        """
        results: list[dict[str, Any]] = []
        for tmpl in GRANT_TEMPLATES:
            if entity_type and tmpl.get("funding_type", "").lower() != entity_type.lower():
                continue
            opp = dict(tmpl)
            opp["match_score"] = 85.0 if entity_type else 70.0
            opp["source_url"] = random.choice(GRANT_DATABASES["sa_government"])
            opp["location"] = location or "South Africa"
            opp["description"] = f"{opp['name']} — {opp['eligibility']}"
            results.append(opp)

        if not results and entity_type:
            return []
        return results[:10]

    # ------------------------------------------------------------------
    # Scholarships
    # ------------------------------------------------------------------

    def search_scholarships(
        self,
        level: str = "",
        field: str = "",
        country: str = "",
    ) -> list[dict[str, Any]]:
        """Find scholarships, bursaries, and fellowships.

        Args:
            level: Education level (undergraduate, masters, phd,
                fellowship, mba, short_course).
            field: Field of study.
            country: Target country.

        Returns:
            List of scholarship opportunity dictionaries.
        """
        results: list[dict[str, Any]] = []
        for tmpl in SCHOLARSHIP_TEMPLATES:
            if level and tmpl.get("level", "").lower() != level.lower():
                continue
            if field and field.lower() not in tmpl.get("field_of_study", "").lower():
                continue
            opp = dict(tmpl)
            opp["match_score"] = 88.0 if level else 75.0
            opp["source_url"] = random.choice(SCHOLARSHIP_SOURCES["sa"] + SCHOLARSHIP_SOURCES["international"])
            opp["country"] = country or opp.get("country", "South Africa")
            results.append(opp)

        if not results and level:
            return []
        return results[:10]

    # ------------------------------------------------------------------
    # Networking
    # ------------------------------------------------------------------

    def search_networking_events(
        self,
        topic: str = "",
        location: str = "",
        date_range: str = "",
    ) -> list[dict[str, Any]]:
        """Find conferences, trade shows, meetups, webinars, and workshops.

        Args:
            topic: Event topic or industry.
            location: City or region.
            date_range: Date filter (e.g. ``"next_30_days"``).

        Returns:
            List of networking event dictionaries.
        """
        results: list[dict[str, Any]] = []
        for tmpl in NETWORKING_TEMPLATES:
            score = _weighted_score(
                query_skills=[topic],
                opp_skills=[tmpl["name"], tmpl.get("description", "")],
                query_location=location,
                opp_location=tmpl.get("location", ""),
                query_category=topic,
                opp_category=tmpl.get("type", ""),
            )
            if score > 10 or not topic and not location:
                opp = dict(tmpl)
                opp["match_score"] = round(score, 1) if score > 10 else 65.0
                opp["source_url"] = random.choice(EVENT_PLATFORMS["sa"] + EVENT_PLATFORMS["global"])
                opp["target_audience"] = topic or "General"
                results.append(opp)

        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results[:10]

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match_opportunities(
        self,
        user_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Match user profile against all opportunity categories.

        Args:
            user_profile: Dictionary with keys:
                ``skills``, ``interests``, ``location``,
                ``experience_level``, ``goals``.

        Returns:
            Ranked list of matching opportunities across all categories.
        """
        skills = user_profile.get("skills", [])
        interests = user_profile.get("interests", [])
        location = user_profile.get("location", "")
        experience = user_profile.get("experience_level", "")

        all_results: list[dict[str, Any]] = []

        # Job matches
        if "work" in user_profile.get("goals", "").lower() or not user_profile.get("goals"):
            for tmpl in JOB_TEMPLATES[:3]:
                opp = dict(tmpl)
                opp["category"] = "Job"
                opp["match_score"] = _weighted_score(
                    query_skills=skills + interests,
                    opp_skills=[tmpl["title"]],
                    query_location=location,
                    opp_location=tmpl["location"],
                    query_category=", ".join(interests),
                    opp_category=tmpl.get("category", ""),
                )
                opp["source_url"] = random.choice(JOB_BOARDS["general"])
                all_results.append(opp)

        # Business matches
        for tmpl in BUSINESS_TEMPLATES[:2]:
            opp = dict(tmpl)
            opp["category"] = "Business"
            opp["match_score"] = 60.0
            opp["source_url"] = random.choice(TENDER_SOURCES["sa_government"])
            all_results.append(opp)

        # Grant matches
        for tmpl in GRANT_TEMPLATES[:2]:
            opp = dict(tmpl)
            opp["category"] = "Grant"
            opp["match_score"] = 65.0
            opp["source_url"] = random.choice(GRANT_DATABASES["sa_government"])
            all_results.append(opp)

        # Scholarship matches
        if experience.lower() in ("student", "undergraduate", "graduate"):
            for tmpl in SCHOLARSHIP_TEMPLATES[:2]:
                opp = dict(tmpl)
                opp["category"] = "Scholarship"
                opp["match_score"] = 70.0
                opp["source_url"] = random.choice(SCHOLARSHIP_SOURCES["sa"])
                all_results.append(opp)

        # Event matches
        for tmpl in NETWORKING_TEMPLATES[:2]:
            opp = dict(tmpl)
            opp["category"] = "Event"
            opp["match_score"] = 55.0
            opp["source_url"] = random.choice(EVENT_PLATFORMS["sa"])
            all_results.append(opp)

        all_results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return all_results[:10]

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_opportunity_list(
        self,
        opportunities: list[dict[str, Any]],
        title: str,
    ) -> str:
        """Format a list of opportunities for terminal display.

        Args:
            opportunities: List of opportunity dictionaries.
            title: Section title.

        Returns:
            Rich-formatted string ready for printing.
        """
        if not opportunities:
            return f"No opportunities found for: {title}"

        lines: list[str] = [f"[bold cyan]{title}[/bold cyan]\n"]

        for idx, opp in enumerate(opportunities, 1):
            score = opp.get("match_score", 0)
            score_bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"

            lines.append(f"[bold]{idx}.[/bold] {opp.get('title', opp.get('name', 'Untitled'))}")
            lines.append(f"   [dim]Match:[/dim] [{score_color}]{score_bar} {score:.0f}%[/{score_color}]")

            # Location
            if "location" in opp and opp["location"]:
                lines.append(f"   [dim]Location:[/dim] {opp['location']}")

            # Organization / Company
            if "company" in opp and opp["company"]:
                lines.append(f"   [dim]Company:[/dim] {opp['company']}")
            elif "organization" in opp and opp["organization"]:
                lines.append(f"   [dim]Organization:[/dim] {opp['organization']}")
            elif "funder" in opp and opp["funder"]:
                lines.append(f"   [dim]Funder:[/dim] {opp['funder']}")
            elif "institution" in opp and opp["institution"]:
                lines.append(f"   [dim]Institution:[/dim] {opp['institution']}")

            # Financial details
            if "salary_range" in opp and opp["salary_range"]:
                lines.append(f"   [dim]Salary:[/dim] {opp['salary_range']}")
            if "value" in opp and opp["value"]:
                lines.append(f"   [dim]Value:[/dim] {opp['value']}")
            if "amount" in opp and opp["amount"]:
                lines.append(f"   [dim]Amount:[/dim] {opp['amount']}")
            if "budget" in opp and opp["budget"]:
                lines.append(f"   [dim]Budget:[/dim] {opp['budget']}")
            if "required_capital" in opp and opp["required_capital"]:
                lines.append(f"   [dim]Capital Required:[/dim] {opp['required_capital']}")

            # Deadline / Date
            if "deadline" in opp and opp["deadline"]:
                lines.append(f"   [dim]Deadline:[/dim] {opp['deadline']}")
            if "date" in opp and opp["date"]:
                lines.append(f"   [dim]Date:[/dim] {opp['date']}")
            if "posted_date" in opp and opp["posted_date"]:
                lines.append(f"   [dim]Posted:[/dim] {opp['posted_date']}")

            # Description
            if "description" in opp and opp["description"]:
                desc = opp["description"][:120]
                if len(opp["description"]) > 120:
                    desc += "..."
                lines.append(f"   [dim]Description:[/dim] {desc}")

            # Requirements
            if "requirements" in opp and opp["requirements"]:
                lines.append(f"   [dim]Requirements:[/dim] {opp['requirements'][:100]}")

            # Source URL
            if "source_url" in opp and opp["source_url"]:
                lines.append(f"   [blue]{opp['source_url']}[/blue]")

            lines.append("")

        lines.append(_DISCLAIMER)
        return "\n".join(lines)

    def format_opportunity_detail(self, opp: dict[str, Any]) -> str:
        """Format a single opportunity in full detail.

        Args:
            opp: Single opportunity dictionary.

        Returns:
            Rich-formatted detail string.
        """
        lines: list[str] = [f"[bold cyan]{opp.get('title', opp.get('name', 'Details'))}[/bold cyan]\n"]

        for key, value in opp.items():
            if key in ("title", "name", "match_score"):
                continue
            if not value:
                continue
            label = key.replace("_", " ").title()
            lines.append(f"  [bold]{label}:[/bold] {value}")

        lines.append(f"\n{_DISCLAIMER}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_opportunity(self, opp: dict[str, Any]) -> None:
        """Save an opportunity to the saved list."""
        self._saved.append(opp)

    def get_saved_opportunities(self) -> list[dict[str, Any]]:
        """Return the list of saved opportunities."""
        return self._saved
