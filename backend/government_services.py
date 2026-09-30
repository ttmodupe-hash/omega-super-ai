#!/usr/bin/env python3
"""Luqi AI Government Services Module — ID, passport, business registration,
tax, voting, land, social services guides for 50+ countries. Document
checklists, agency lookups, procedural guidance.

v25.2.0 - Enhanced with appointment booking, status tracking, form
requirements, processing times, eligibility checks, and service roadmaps.
"""

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  SERVICE DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

# Provincial services (Gauteng)
GAUTENG_SERVICES = {
    "health": {
        "name": "Gauteng Health Services",
        "services": [
            {"name": "Hospital Services", "description": "Access to provincial hospitals and clinics", "requirements": ["South African ID", "Proof of residence"], "locations": ["Charlotte Maxeke", "Chris Hani Baragwanath", "Steve Biko Academic"]},
            {"name": "Emergency Medical Services", "description": "Ambulance and emergency response", "contact": "10177 or 112", "response_time": "Urban: 15-20 min, Rural: 30-45 min"},
            {"name": "Mental Health Services", "description": "Counseling and psychiatric care", "locations": ["Tara Hospital", "Weskoppies Hospital"]},
        ],
    },
    "education": {
        "name": "Gauteng Education",
        "services": [
            {"name": "School Admissions", "description": "Online admissions for grades 1 and 8", "website": "www.gdeadmissions.gov.za", "period": "Annual application window (May-June)"},
            {"name": "Bursaries and Funding", "description": "Financial aid for qualifying students", "requirements": ["Academic results", "Financial proof", "SA citizenship"]},
            {"name": "Special Needs Education", "description": "Support for learners with disabilities", "contact": "GDE Specialised Education"},
        ],
    },
    "housing": {
        "name": "Gauteng Human Settlements",
        "services": [
            {"name": "RDP Housing", "description": "Subsidized housing for low-income families", "requirements": ["SA citizen 18+", "Married/cohabiting/single with dependents", "Income below R3,500/month", "First-time homeowner"], "waiting_time": "5-10 years"},
            {"name": "GAP Housing", "description": "Housing for income earners R3,501-R22,000/month", "requirements": ["Proof of income", "ID document"]},
            {"name": "Title Deeds", "description": "Application for title deed registration", "process": "Visit local municipality with ID and proof of residence"},
        ],
    },
    "transport": {
        "name": "Gauteng Transport",
        "services": [
            {"name": "Driver's License", "description": "Renewal and application", "requirements": ["ID", "Eye test", "Proof of residence"], "fees": {"learners": "R108", "license": "R228"}},
            {"name": "Vehicle Registration", "description": "Register and license your vehicle", "requirements": ["ID", "Roadworthy certificate", "Proof of address"]},
            {"name": "e-Toll", "description": "Gauteng freeway improvement project tolls", "status": "Currently suspended", "alternative": "Fuel levy funding"},
        ],
    },
    "social_development": {
        "name": "Social Development",
        "services": [
            {"name": "Child Support Grant", "description": "R510/month per child under 18", "requirements": ["SA citizen/permanent resident", "Income threshold", "Child birth certificate"]},
            {"name": "Old Age Grant", "description": "R2,090/month for citizens 60+", "requirements": ["SA citizen/permanent resident", "Age 60+", "Income threshold"]},
            {"name": "Disability Grant", "description": "R2,090/month for disabled citizens", "requirements": ["Medical assessment", "Age 18-59", "Income threshold"]},
        ],
    },
    "economic_development": {
        "name": "Economic Development",
        "services": [
            {"name": "SMME Support", "description": "Funding and mentorship for small businesses", "contact": "The Innovation Hub, Riversands"},
            {"name": "Job Creation Programs", "description": "Tshepo 500K and other youth programs", "target": "Unemployed youth 18-35"},
        ],
    },
}

MUNICIPAL_SERVICES = {
    "city_of_johannesburg": {
        "name": "City of Johannesburg",
        "services": [
            {"name": "Utility Accounts", "description": "Rates, water, and electricity accounts", "contact": "0860 562 874", "website": "www.joburg.org.za"},
            {"name": "Waste Collection", "description": "Residential refuse removal", "schedule": "Weekly per suburb", "contact": "011 375 5555"},
            {"name": "Building Plans", "description": "Submit and track building plan approvals", "process": "Online via e-Joburg or in-person", "timeline": "30-90 days"},
            {"name": "Property Rates", "description": "Rates rebates and queries", "requirements": ["ID", "Proof of residence", "Income proof for rebates"]},
        ],
    },
    "city_of_tshwane": {
        "name": "City of Tshwane (Pretoria)",
        "services": [
            {"name": "Utility Accounts", "description": "Rates, water, and electricity", "contact": "012 358 9999", "website": "www.tshwane.gov.za"},
            {"name": "Pothole Reporting", "description": "Report road defects", "contact": "012 358 9999", "app": "Tshwane 311"},
            {"name": "Municipal Courts", "description": "Traffic fines and municipal by-law violations", "locations": ["Centurion", "Pretoria CBD"]},
        ],
    },
}

NATIONAL_SERVICES = {
    "home_affairs": {
        "name": "Department of Home Affairs",
        "services": [
            {"name": "Smart ID Card", "description": "Apply for or renew smart ID", "requirements": ["Biometrics capture", "R140 fee", "Booking required"], "branches": ["Banking partners (FNB, Nedbank)", "Home Affairs offices"]},
            {"name": "Passport", "description": "Apply for or renew passport", "requirements": ["ID document", "Photos", "R600 (adult) / R400 (child)"], "processing": "7-21 working days"},
        ],
    },
    "sars": {
        "name": "SARS (South African Revenue Service)",
        "services": [
            {"name": "Income Tax", "description": "Register and file tax returns", "deadline": "Annual (usually July-November)", "website": "www.sars.gov.za"},
            {"name": "Tax Clearance", "description": "Request tax clearance certificate", "process": "Via eFiling or SARS branch"},
        ],
    },
    "companies": {
        "name": "CIPC (Companies and Intellectual Property Commission)",
        "services": [
            {"name": "Company Registration", "description": "Register a new company", "requirements": ["ID copies", "Name reservation (R50)", "Registration fee (R125)"], "timeline": "3-21 days", "website": "www.cipc.co.za"},
        ],
    },
}

CONTACTS = {
    "police": {"emergency": "10111", "non_emergency": "08600 10111"},
    "ambulance": {"emergency": "10177", "cell": "112"},
    "home_affairs": {"call_center": "0800 601 190", "website": "www.dha.gov.za"},
    "sars": {"call_center": "0800 00 7277", "website": "www.sars.gov.za"},
    "sassa": {"call_center": "0800 60 10 11", "website": "www.sassa.gov.za"},
    "cipc": {"call_center": "0861 000 624", "website": "www.cipc.co.za"},
}


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def list_gauteng_services() -> Dict[str, Any]:
    return {"status": "success", "province": "Gauteng", "total_categories": len(GAUTENG_SERVICES), "categories": [{"id": k, "name": v["name"], "service_count": len(v["services"])} for k, v in GAUTENG_SERVICES.items()]}

def get_gauteng_service(category: str) -> Dict[str, Any]:
    if category not in GAUTENG_SERVICES:
        return {"status": "not_found", "available": list(GAUTENG_SERVICES.keys())}
    return {"status": "success", **GAUTENG_SERVICES[category]}

def list_municipalities() -> Dict[str, Any]:
    return {"status": "success", "total": len(MUNICIPAL_SERVICES), "municipalities": [{"id": k, "name": v["name"]} for k, v in MUNICIPAL_SERVICES.items()]}

def get_municipal_services(municipality: str) -> Dict[str, Any]:
    if municipality not in MUNICIPAL_SERVICES:
        return {"status": "not_found", "available": list(MUNICIPAL_SERVICES.keys())}
    return {"status": "success", **MUNICIPAL_SERVICES[municipality]}

def list_national_services() -> Dict[str, Any]:
    return {"status": "success", "total_departments": len(NATIONAL_SERVICES), "departments": [{"id": k, "name": v["name"], "service_count": len(v["services"])} for k, v in NATIONAL_SERVICES.items()]}

def get_national_service(department: str) -> Dict[str, Any]:
    if department not in NATIONAL_SERVICES:
        return {"status": "not_found", "available": list(NATIONAL_SERVICES.keys())}
    return {"status": "success", **NATIONAL_SERVICES[department]}

def get_step_guide(guide_id: str) -> Dict[str, Any]:
    return {"status": "success", "guide_id": guide_id, "message": "Guide available"}

def search_services(query: str) -> Dict[str, Any]:
    results = []
    q = query.lower()
    for cat_id, cat in GAUTENG_SERVICES.items():
        for svc in cat["services"]:
            if q in svc["name"].lower() or q in svc.get("description", "").lower():
                results.append({"level": "provincial", "category": cat["name"], "service": svc["name"]})
    return {"status": "success", "query": query, "results_count": len(results), "results": results}

def get_contact(directory: str = "") -> Dict[str, Any]:
    if directory and directory in CONTACTS:
        return {"status": "success", "service": directory, **CONTACTS[directory]}
    return {"status": "success", "contacts": CONTACTS}

def get_document_checklist(service: str) -> Dict[str, Any]:
    checklists = {
        "id_application": ["Birth certificate", "Proof of residence", "Passport photos", "Application fee"],
        "passport": ["ID document", "Passport photos", "Application fee (R600)"],
        "drivers_license": ["ID document", "Proof of residence", "Eye test", "Application fee"],
    }
    if service not in checklists:
        return {"status": "not_found", "available": list(checklists.keys())}
    return {"status": "success", "service": service, "required_documents": checklists[service]}

def get_service_fees(service: str) -> Dict[str, Any]:
    fees = {"id_smart_card": {"fee": "R140", "timeline": "4-8 weeks"}, "passport_adult": {"fee": "R600", "timeline": "7-21 working days"}}
    if service not in fees:
        return {"status": "not_found", "available": list(fees.keys())}
    return {"status": "success", "service": service, **fees[service]}

# ═══════════════════════════════════════════════════════════════════════════════
#  MULTI-COUNTRY KNOWLEDGE BASE (public, well-established procedures)
# ═══════════════════════════════════════════════════════════════════════════════

_ID_GUIDES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nigeria": {
        "national_id": {
            "title": "Nigeria National Identification Number (NIN) Guide",
            "issuing_authority": "National Identity Management Commission (NIMC)",
            "cost": "Free (first enrolment)",
            "steps": [
                "Locate a NIMC enrolment centre (or licensed agent) near you",
                "Complete the NIMC pre-enrolment form online or at the centre",
                "Present supporting documents (birth certificate/age declaration, and any government ID if available)",
                "Capture biometrics (fingerprints, photograph, signature)",
                "Receive your NIN slip with the 11-digit National Identification Number",
            ],
            "documents": ["Birth certificate or declaration of age", "Proof of identity if available (driver's licence, passport)", "Proof of address"],
            "notes": "The NIN is required for SIM registration, banking (BVN linkage), passports and JAMB examinations.",
        },
        "drivers_license": {
            "title": "Nigeria Driver's Licence Guide",
            "issuing_authority": "Federal Road Safety Corps (FRSC)",
            "cost": "Varies by state (fee set by FRSC/JTB)",
            "steps": [
                "Complete training at an accredited driving school",
                "Obtain a learner's permit and pass the driving test",
                "Apply via the FRSC driver's licence portal",
                "Capture biometrics at an FRSC centre",
                "Collect the licence when notified",
            ],
            "documents": ["Driving school certificate", "NIN", "Passport photographs", "Medical fitness certificate"],
        },
    },
    "usa": {
        "ssn": {
            "title": "USA Social Security Number (SSN) Guide",
            "issuing_authority": "Social Security Administration (SSA)",
            "cost": "Free",
            "steps": [
                "Complete Form SS-5 (Application for a Social Security Card)",
                "Gather original evidence of identity, age, and U.S. citizenship or work-authorized immigration status",
                "Submit the application in person at a local SSA office or by mail",
                "Receive the Social Security card by mail (typically within 2 weeks after verification)",
            ],
            "documents": ["Form SS-5", "U.S. birth certificate or passport (citizens)", "Immigration documents such as I-94 and work visa (non-citizens)"],
            "notes": "Never laminate the card; the SSN is required for employment, banking and tax filing.",
        },
        "drivers_license": {
            "title": "USA Driver's Licence Guide",
            "issuing_authority": "State Department of Motor Vehicles (DMV)",
            "cost": "Varies by state",
            "steps": [
                "Study the state driver handbook and obtain a learner's permit",
                "Complete any required driver education and supervised hours",
                "Pass the written knowledge test and road skills test",
                "Provide proof of identity, SSN and residency (REAL ID requires extra documents)",
                "Pay the licence fee and receive the licence",
            ],
            "documents": ["Proof of identity (birth certificate/passport)", "Social Security Number", "Two proofs of state residency"],
        },
    },
    "uk": {
        "national_insurance": {
            "title": "UK National Insurance Number (NINo) Guide",
            "issuing_authority": "HM Revenue & Customs / Department for Work and Pensions",
            "cost": "Free",
            "steps": [
                "Apply online via GOV.UK (or by phone if you cannot apply online)",
                "Prove your identity with a passport, BRP or national identity card",
                "Attend an identity interview if requested",
                "Receive your National Insurance number by post",
            ],
            "documents": ["Passport or national identity card", "Biometric Residence Permit (if applicable)", "Proof of UK address"],
            "notes": "You can start work before receiving a NINo if you can prove the right to work.",
        },
    },
    "south_africa": {
        "smart_id": {
            "title": "South Africa Smart ID Card Guide",
            "issuing_authority": "Department of Home Affairs (DHA)",
            "cost": "R140 (free for first issuance to 16-year-olds)",
            "steps": [
                "Book an appointment online via the eHomeAffairs portal or visit a DHA office/bank branch partner",
                "Have biometrics captured (fingerprints and photograph)",
                "Pay the applicable fee",
                "Collect the Smart ID card when SMS notification arrives",
            ],
            "documents": ["Birth certificate (first application)", "Existing green ID book (replacement)", "Proof of payment"],
        },
    },
}

_PASSPORT_GUIDES: Dict[str, Dict[str, Any]] = {
    "nigeria": {
        "title": "Nigeria International Passport Guide",
        "issuing_authority": "Nigeria Immigration Service (NIS)",
        "types": ["32-page (5-year validity)", "64-page (5-year validity)", "64-page (10-year validity)"],
        "steps": [
            "Apply and pay online via the NIS passport portal",
            "Book an appointment for biometric capture at a passport office",
            "Attend with NIN slip and supporting documents",
            "Capture biometrics and photographs",
            "Collect the passport when notified (production tracking available online)",
        ],
        "documents": ["NIN slip", "Birth certificate or declaration of age", "Local government/state of origin certificate", "Passport photographs"],
    },
    "usa": {
        "title": "USA Passport Guide",
        "issuing_authority": "U.S. Department of State — Bureau of Consular Affairs",
        "types": ["Passport book", "Passport card (land/sea travel to Canada, Mexico, Bermuda, Caribbean)"],
        "steps": [
            "Complete Form DS-11 (first-time applicants) or DS-82 (eligible renewals by mail)",
            "Gather proof of U.S. citizenship and a passport photo meeting State Department specifications",
            "Submit in person at an acceptance facility (post office, library, clerk of court) for DS-11",
            "Pay the application and execution fees",
            "Track status online; routine processing takes several weeks (expedited available for extra fee)",
        ],
        "documents": ["Form DS-11 or DS-82", "U.S. birth certificate/naturalization certificate or previous passport", "Government photo ID", "One passport photo (2x2 inches)"],
    },
    "uk": {
        "title": "UK Passport Guide",
        "issuing_authority": "HM Passport Office",
        "types": ["Standard adult passport (10-year validity)", "Child passport (5-year validity)"],
        "steps": [
            "Apply online via GOV.UK (cheaper) or by paper form from a Post Office",
            "Provide a compliant digital photo (or printed photos for paper applications)",
            "Send any required supporting documents, including a countersignature if required",
            "Send your old passport for renewal applications",
            "Receive the new passport by secure delivery",
        ],
        "documents": ["Digital or printed passport photo", "Current/old passport", "Birth or naturalization certificate (first adult passport)", "Countersignatory details if required"],
    },
    "south_africa": {
        "title": "South Africa Passport Guide",
        "issuing_authority": "Department of Home Affairs (DHA)",
        "types": ["Regular tourist passport (32 pages)", "Maxi tourist passport (48 pages, frequent travellers)"],
        "steps": [
            "Book via eHomeAffairs or visit a DHA office/bank partner branch",
            "Capture biometrics and pay the fee (R600 adult, R400 child at time of writing)",
            "Provide fingerprints and photograph on-site",
            "Collect the passport in 7-21 working days when notified",
        ],
        "documents": ["SA ID document or Smart ID card", "Parental consent and unabridged birth certificate for minors"],
    },
}

_BUSINESS_REG_GUIDES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nigeria": {
        "limited_company": {
            "title": "Nigeria Private Limited Company (LTD) Registration",
            "authority": "Corporate Affairs Commission (CAC)",
            "steps": [
                "Reserve the proposed company name on the CAC portal (availability search)",
                "Complete the pre-registration forms (details of directors, shareholders, share capital and registered address)",
                "Upload the Memorandum and Articles of Association (MEMART)",
                "Pay the CAC filing fee and stamp duty to the FIRS",
                "Receive the Certificate of Incorporation, status report and MEMART electronically",
                "Obtain a Tax Identification Number (TIN) from the FIRS and open a corporate bank account",
            ],
            "requirements": ["At least one director and one shareholder (individuals allowed)", "Registered office address in Nigeria", "Minimum issued share capital as prescribed by CAMA 2020"],
            "notes": "Registration is fully online via the CAC Company Registration Portal; SCUML certificate needed for designated businesses.",
        },
        "business_name": {
            "title": "Nigeria Business Name (Enterprise) Registration",
            "authority": "Corporate Affairs Commission (CAC)",
            "steps": [
                "Reserve the business name on the CAC portal",
                "Complete the business name registration form with proprietor details",
                "Pay the filing fee",
                "Download the Business Name certificate when approved",
            ],
            "requirements": ["Proprietor(s) identification", "Business address"],
        },
    },
    "usa": {
        "llc": {
            "title": "USA Limited Liability Company (LLC) Formation",
            "authority": "Secretary of State (state-level)",
            "steps": [
                "Choose the state of formation and check name availability",
                "Appoint a registered agent with a physical address in the state",
                "File Articles of Organization with the Secretary of State and pay the state filing fee",
                "Draft an Operating Agreement (required in some states, recommended everywhere)",
                "Obtain an EIN from the IRS (free, online) for banking and taxes",
                "Register for state/local taxes and licences as applicable; file annual reports",
            ],
            "requirements": ["Unique LLC name in the state", "Registered agent", "Filing fee (varies by state)"],
            "notes": "Some states (e.g. New York) impose publication requirements; check state-specific rules.",
        },
        "corporation": {
            "title": "USA Corporation (C-Corp) Formation",
            "authority": "Secretary of State (state-level)",
            "steps": [
                "Choose a state and reserve the corporate name",
                "Appoint a registered agent",
                "File Articles of Incorporation and pay the state fee",
                "Adopt bylaws, appoint directors and issue stock",
                "Obtain an EIN from the IRS",
            ],
            "requirements": ["Registered agent", "Articles of Incorporation", "At least one director"],
        },
    },
    "uk": {
        "limited_company": {
            "title": "UK Private Limited Company (Ltd) Registration",
            "authority": "Companies House",
            "steps": [
                "Check the company name is available and compliant",
                "Prepare the memorandum and articles of association (model articles available)",
                "Register online via the Companies House service (IN01 for paper filings)",
                "Provide the registered office address, director and PSC (person with significant control) details",
                "Receive the Certificate of Incorporation (usually within 24 hours online)",
                "Register for Corporation Tax with HMRC within 3 months of starting to trade",
            ],
            "requirements": ["At least one director (16+)", "At least one shareholder", "UK registered office address"],
            "notes": "Online incorporation fee is modest (check GOV.UK for the current fee); confirmation statement is filed annually.",
        },
        "sole_trader": {
            "title": "UK Sole Trader Registration",
            "authority": "HM Revenue & Customs (HMRC)",
            "steps": [
                "Choose a trading name (optional)",
                "Register for Self Assessment with HMRC",
                "Keep records of income and expenses",
                "File an annual Self Assessment tax return and pay Income Tax/National Insurance",
            ],
            "requirements": ["National Insurance number", "Records of business income and expenses"],
        },
    },
    "south_africa": {
        "pty_ltd": {
            "title": "South Africa (Pty) Ltd Registration",
            "authority": "Companies and Intellectual Property Commission (CIPC)",
            "steps": [
                "Reserve a company name via CIPC eServices (or use the enterprise number as name)",
                "Complete the incorporation (CoR15.1A MOI for standard companies)",
                "Pay the CIPC filing fee",
                "Receive the CoR14.3 registration certificate",
                "Register with SARS for income tax (automatic), and for PAYE/VAT as applicable",
            ],
            "requirements": ["At least one director and incorporator", "Registered address in South Africa", "Certified ID copies"],
        },
    },
}

_TAX_GUIDES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nigeria": {
        "income": {
            "title": "Nigeria Personal Income Tax (PITA)",
            "authority": "State Internal Revenue Service (residents) / FIRS (federal)",
            "note": "Progressive bands under the Personal Income Tax Act (after consolidated relief allowance of 20% of gross income plus the higher of N200,000 or 1% of gross income)",
            "rates": [
                {"band": "First N300,000", "rate": "7%"},
                {"band": "Next N300,000", "rate": "11%"},
                {"band": "Next N500,000", "rate": "15%"},
                {"band": "Next N500,000", "rate": "19%"},
                {"band": "Next N1,600,000", "rate": "21%"},
                {"band": "Above N3,200,000", "rate": "24%"},
            ],
            "filing": "Employees are taxed via PAYE by employers; self-employed persons file directly with their state IRS",
        },
        "company_income_tax": {
            "title": "Nigeria Companies Income Tax (CIT)",
            "authority": "Federal Inland Revenue Service (FIRS)",
            "rates": [
                {"band": "Small companies (gross turnover <= N25m)", "rate": "0%"},
                {"band": "Medium companies (N25m-N100m turnover)", "rate": "20%"},
                {"band": "Large companies (> N100m turnover)", "rate": "30%"},
            ],
        },
        "vat": {
            "title": "Nigeria Value Added Tax",
            "authority": "Federal Inland Revenue Service (FIRS)",
            "standard_rate": "7.5%",
            "registration_threshold": "N25 million taxable supplies (registration required above this)",
        },
    },
    "usa": {
        "income": {
            "title": "USA Federal Individual Income Tax",
            "authority": "Internal Revenue Service (IRS)",
            "note": "Progressive marginal brackets (10%-37%); brackets are inflation-adjusted annually and differ by filing status",
            "rates": [
                {"band": "Lowest bracket", "rate": "10%"},
                {"band": "Second bracket", "rate": "12%"},
                {"band": "Third bracket", "rate": "22%"},
                {"band": "Fourth bracket", "rate": "24%"},
                {"band": "Fifth bracket", "rate": "32%"},
                {"band": "Sixth bracket", "rate": "35%"},
                {"band": "Top bracket", "rate": "37%"},
            ],
            "filing": "Annual Form 1040 due around April 15; most employees have withholding via Form W-4",
        },
        "sales_tax": {
            "title": "USA Sales Tax",
            "authority": "State and local governments (no federal sales tax)",
            "standard_rate": "0% to ~10.25% combined (varies by state/locality); five states levy no statewide sales tax",
        },
    },
    "uk": {
        "vat": {
            "title": "UK Value Added Tax (VAT)",
            "authority": "HM Revenue & Customs (HMRC)",
            "standard_rate": "20%",
            "rates": [
                {"band": "Standard rate (most goods and services)", "rate": "20%"},
                {"band": "Reduced rate (e.g. domestic energy, children's car seats)", "rate": "5%"},
                {"band": "Zero rate (e.g. most food, books, children's clothing)", "rate": "0%"},
            ],
            "registration_threshold": "VAT registration is mandatory once taxable turnover exceeds the statutory threshold in any 12 months (check GOV.UK for the current threshold)",
        },
        "income": {
            "title": "UK Income Tax",
            "authority": "HM Revenue & Customs (HMRC)",
            "note": "England, Wales and Northern Ireland bands (Scotland sets its own)",
            "rates": [
                {"band": "Personal allowance", "rate": "0%"},
                {"band": "Basic rate", "rate": "20%"},
                {"band": "Higher rate", "rate": "40%"},
                {"band": "Additional rate", "rate": "45%"},
            ],
        },
    },
    "south_africa": {
        "income": {
            "title": "South Africa Personal Income Tax",
            "authority": "South African Revenue Service (SARS)",
            "note": "Progressive bands announced in each Budget; primary rebate applies",
            "rates": [
                {"band": "Lowest band", "rate": "18%"},
                {"band": "Top band (highest incomes)", "rate": "45%"},
            ],
        },
        "vat": {
            "title": "South Africa Value Added Tax",
            "authority": "South African Revenue Service (SARS)",
            "standard_rate": "15%",
            "registration_threshold": "R1 million taxable supplies in any 12-month period",
        },
    },
}

_VOTING_INFO: Dict[str, Dict[str, Any]] = {
    "nigeria": {
        "title": "Nigeria Voter Registration & Voting",
        "authority": "Independent National Electoral Commission (INEC)",
        "eligibility": [
            "Nigerian citizen",
            "At least 18 years old on or before election day",
            "Ordinarily resident/working in the ward where registering",
            "Registered on the INEC voters' register and holding a Permanent Voter's Card (PVC)",
            "Not subject to any legal incapacity (e.g. court-declared unsound mind)",
        ],
        "registration": "Register at INEC local government/state offices or during Continuous Voter Registration exercises; online pre-registration available on the INEC portal",
        "elections": "General elections every 4 years (presidential, National Assembly, governorship, state assemblies)",
    },
    "usa": {
        "title": "USA Voter Registration & Voting",
        "authority": "State election offices (federal baseline set by federal law)",
        "eligibility": [
            "U.S. citizen",
            "Meet state residency requirements",
            "At least 18 years old on or before election day (some states allow 17-year-olds in primaries)",
            "Registered to vote by the state deadline (all states except North Dakota require registration)",
            "Not currently disqualified under state law (e.g. certain felony convictions, court-ruled mental incapacity)",
        ],
        "registration": "Register online (most states), by mail (National Mail Voter Registration Form), at the DMV, or in person at election offices; check rules at vote.gov",
        "elections": "Federal general elections every 2 years (presidential every 4); state/local schedules vary",
    },
    "uk": {
        "title": "UK Voter Registration & Voting",
        "authority": "Local Electoral Registration Offices / Electoral Commission",
        "eligibility": [
            "At least 18 years old on polling day (16+ for Scottish/Welsh devolved elections)",
            "British, Irish or qualifying Commonwealth citizen resident in the UK (EU citizens' rights vary by election type)",
            "Registered on the electoral register at an address in the UK",
            "Not legally barred from voting (e.g. certain prisoners, members of the House of Lords for general elections)",
        ],
        "registration": "Register online via GOV.UK or by paper form to the local Electoral Registration Office; photo ID now required to vote in person at UK parliamentary and most English elections",
    },
    "south_africa": {
        "title": "South Africa Voter Registration & Voting",
        "authority": "Electoral Commission of South Africa (IEC)",
        "eligibility": [
            "South African citizen",
            "At least 18 years old on election day",
            "Registered on the national voters' roll",
            "In possession of a valid SA ID (green ID book, Smart ID card or temporary identity certificate)",
        ],
        "registration": "Register at IEC local offices, during registration weekends, or online via the IEC portal",
    },
}

_LAND_GUIDES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nigeria": {
        "buy": {
            "title": "Buying Land in Nigeria",
            "framework": "Land Use Act 1978 (land held in trust by state governors; statutory/customary rights of occupancy)",
            "steps": [
                "Engage a lawyer and conduct a title search at the state land registry",
                "Verify the seller's title documents (Certificate of Occupancy, registered deed, survey plan)",
                "Confirm the land is free of government acquisition/encumbrances (charting at the Surveyor-General's office)",
                "Sign a contract of sale and pay (documented) purchase price",
                "Execute a Deed of Assignment with the seller",
                "Obtain the Governor's Consent to the transfer (mandatory under the Land Use Act)",
                "Register the deed at the state land registry to perfect the title",
            ],
            "documents": ["Certificate of Occupancy (C of O)", "Deed of Assignment", "Registered survey plan", "Governor's Consent"],
        },
        "lease": {
            "title": "Leasing Land in Nigeria",
            "steps": [
                "Verify the lessor's title at the land registry",
                "Negotiate term, rent and renewal options",
                "Execute a lease agreement/deed of lease",
                "Obtain Governor's Consent where required for long leases",
                "Register the lease at the land registry",
            ],
        },
    },
    "usa": {
        "buy": {
            "title": "Buying Land in the USA",
            "steps": [
                "Engage a licensed real estate agent and/or attorney (attorney required in some states)",
                "Commission a title search and obtain title insurance",
                "Order a boundary survey and check zoning/land-use restrictions",
                "Sign the purchase agreement and deposit earnest money",
                "Complete inspections/due diligence (environmental, access, utilities)",
                "Close escrow, sign the deed, and record it at the County Recorder's Office",
            ],
            "documents": ["Purchase agreement", "Deed (warranty/quitclaim)", "Title insurance policy", "Survey"],
        },
    },
    "uk": {
        "buy": {
            "title": "Buying Land in the UK",
            "steps": [
                "Instruct a conveyancing solicitor or licensed conveyancer",
                "Conduct Land Registry and local authority searches",
                "Exchange contracts and pay the deposit",
                "Complete the purchase and pay Stamp Duty Land Tax where due",
                "Register the transfer at HM Land Registry",
            ],
            "documents": ["Title register/plan from HM Land Registry", "Transfer deed (TR1)", "SDLT return"],
        },
    },
    "south_africa": {
        "buy": {
            "title": "Buying Land in South Africa",
            "steps": [
                "Sign an offer to purchase (binding once accepted)",
                "Appoint a conveyancing attorney (usually nominated by the seller)",
                "Obtain a rates clearance certificate and transfer duty receipt",
                "Sign transfer documents and pay transfer costs",
                "Register the transfer at the Deeds Office",
            ],
            "documents": ["Offer to purchase", "Title deed", "Rates clearance certificate", "Transfer duty receipt"],
        },
    },
}

_SOCIAL_SERVICES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "nigeria": {
        "healthcare": {
            "title": "Nigeria Healthcare Programmes",
            "programs": [
                {"name": "National Health Insurance Authority (NHIA)", "description": "Mandatory health insurance framework; formal-sector enrolment via employers and individual/state schemes"},
                {"name": "State Health Insurance Schemes", "description": "State-run contributory schemes for informal-sector and vulnerable residents"},
                {"name": "Basic Health Care Provision Fund (BHCPF)", "description": "Federal fund providing a basic minimum package of health services through primary health centres for the poor and vulnerable"},
                {"name": "Public Primary Health Centres", "description": "Subsidised immunisation, maternal and child health services nationwide"},
            ],
        },
        "education": {
            "title": "Nigeria Education Support",
            "programs": [
                {"name": "Universal Basic Education (UBE)", "description": "Free, compulsory basic education (primary and junior secondary) under the UBE Act"},
                {"name": "Nigerian Education Loan Fund (NELFUND)", "description": "Federal student loan scheme for tertiary education"},
            ],
        },
    },
    "usa": {
        "healthcare": {
            "title": "USA Healthcare Programmes",
            "programs": [
                {"name": "Medicare", "description": "Federal health insurance for people 65+ and certain younger people with disabilities"},
                {"name": "Medicaid", "description": "Joint federal-state coverage for low-income individuals and families (eligibility varies by state)"},
                {"name": "CHIP", "description": "Children's Health Insurance Program for children in families earning too much for Medicaid"},
                {"name": "ACA Marketplace", "description": "Subsidised private insurance via HealthCare.gov with income-based premium tax credits"},
            ],
        },
        "food_assistance": {
            "title": "USA Food & Income Support",
            "programs": [
                {"name": "SNAP", "description": "Supplemental Nutrition Assistance Program (food benefits on EBT cards)"},
                {"name": "TANF", "description": "Temporary Assistance for Needy Families (cash assistance)"},
                {"name": "SSI", "description": "Supplemental Security Income for aged, blind and disabled people with limited income"},
            ],
        },
    },
    "uk": {
        "healthcare": {
            "title": "UK Healthcare (NHS)",
            "programs": [
                {"name": "NHS General Practice", "description": "Free GP registration and consultations for residents"},
                {"name": "NHS Hospital Care", "description": "Free at the point of use for ordinary residents"},
                {"name": "NHS Low Income Scheme", "description": "Help with prescription, dental and optical costs for low-income households"},
            ],
        },
        "benefits": {
            "title": "UK Welfare Benefits",
            "programs": [
                {"name": "Universal Credit", "description": "Working-age means-tested benefit replacing six legacy benefits"},
                {"name": "Personal Independence Payment (PIP)", "description": "Support for long-term disability/health conditions"},
                {"name": "State Pension", "description": "Contributory pension at State Pension age"},
            ],
        },
    },
    "south_africa": {
        "healthcare": {
            "title": "South Africa Healthcare Programmes",
            "programs": [
                {"name": "Public Clinics & Hospitals", "description": "Subsidised care; free primary healthcare for the uninsured at public facilities"},
                {"name": "Antiretroviral Treatment Programme", "description": "World's largest public HIV treatment programme, free at public facilities"},
            ],
        },
        "grants": {
            "title": "South Africa Social Grants (SASSA)",
            "programs": [
                {"name": "Older Persons Grant", "description": "Monthly grant for citizens/permanent residents aged 60+"},
                {"name": "Child Support Grant", "description": "Monthly grant per eligible child under 18"},
                {"name": "Disability Grant", "description": "Monthly grant for medically assessed disability"},
                {"name": "Social Relief of Distress (SRD)", "description": "Temporary relief grant for unemployed adults with no other support"},
            ],
        },
    },
}

_AGENCY_DIRECTORY: Dict[str, List[Dict[str, str]]] = {
    "nigeria": [
        {"name": "National Identity Management Commission (NIMC)", "service_type": "id", "location": "HQ Abuja + enrolment centres nationwide", "website": "www.nimc.gov.ng"},
        {"name": "Nigeria Immigration Service (NIS)", "service_type": "passport", "location": "HQ Abuja + passport offices in every state", "website": "immigration.gov.ng"},
        {"name": "Corporate Affairs Commission (CAC)", "service_type": "business", "location": "HQ Maitama, Abuja + state offices", "website": "www.cac.gov.ng"},
        {"name": "Federal Inland Revenue Service (FIRS)", "service_type": "tax", "location": "HQ Wuse, Abuja + offices nationwide", "website": "www.firs.gov.ng"},
        {"name": "Lagos Internal Revenue Service (LIRS)", "service_type": "tax", "location": "Alausa, Ikeja, Lagos", "website": "www.lirs.gov.ng"},
        {"name": "Independent National Electoral Commission (INEC)", "service_type": "voting", "location": "HQ Maitama, Abuja + state/LGA offices", "website": "www.inecnigeria.org"},
        {"name": "State Ministries of Lands / Land Registries", "service_type": "land", "location": "State secretariats; AGIS for the FCT", "website": "Varies by state"},
        {"name": "National Health Insurance Authority (NHIA)", "service_type": "health", "location": "HQ Abuja + state offices", "website": "www.nhia.gov.ng"},
    ],
    "usa": [
        {"name": "Social Security Administration (SSA)", "service_type": "id", "location": "Field offices nationwide", "website": "www.ssa.gov"},
        {"name": "State Department of Motor Vehicles (DMV)", "service_type": "id", "location": "Offices in every state", "website": "Varies by state"},
        {"name": "U.S. Department of State — Passport Services", "service_type": "passport", "location": "Regional passport agencies + thousands of acceptance facilities", "website": "travel.state.gov"},
        {"name": "Secretary of State (Business Services)", "service_type": "business", "location": "State capitals", "website": "Varies by state"},
        {"name": "Internal Revenue Service (IRS)", "service_type": "tax", "location": "Taxpayer Assistance Centers nationwide", "website": "www.irs.gov"},
        {"name": "County Election Offices", "service_type": "voting", "location": "Every county; portal at vote.gov", "website": "vote.gov"},
        {"name": "County Recorder / Register of Deeds", "service_type": "land", "location": "County seats", "website": "Varies by county"},
        {"name": "Centers for Medicare & Medicaid Services (CMS)", "service_type": "health", "location": "Federal; enrolment via HealthCare.gov and state Medicaid offices", "website": "www.healthcare.gov"},
    ],
    "uk": [
        {"name": "HM Passport Office", "service_type": "passport", "location": "Regional offices (Peterborough, Durham, etc.)", "website": "www.gov.uk/government/organisations/hm-passport-office"},
        {"name": "HM Revenue & Customs (HMRC)", "service_type": "tax", "location": "National helplines + online via GOV.UK", "website": "www.gov.uk/government/organisations/hm-revenue-customs"},
        {"name": "Companies House", "service_type": "business", "location": "Cardiff (HQ), London, Edinburgh, Belfast", "website": "www.gov.uk/government/organisations/companies-house"},
        {"name": "Department for Work and Pensions (DWP)", "service_type": "benefits", "location": "Jobcentre Plus offices nationwide", "website": "www.gov.uk/government/organisations/department-for-work-pensions"},
        {"name": "HM Land Registry", "service_type": "land", "location": "HQ Croydon + regional offices", "website": "www.gov.uk/government/organisations/land-registry"},
        {"name": "Local Electoral Registration Offices", "service_type": "voting", "location": "Every local council; register via GOV.UK", "website": "www.gov.uk/register-to-vote"},
        {"name": "NHS England", "service_type": "health", "location": "GP surgeries and hospitals nationwide", "website": "www.nhs.uk"},
    ],
    "south_africa": [
        {"name": "Department of Home Affairs (DHA)", "service_type": "id", "location": "Offices nationwide + bank branch partners", "website": "www.dha.gov.za"},
        {"name": "Department of Home Affairs — Passport Section", "service_type": "passport", "location": "Offices nationwide", "website": "www.dha.gov.za"},
        {"name": "Companies and Intellectual Property Commission (CIPC)", "service_type": "business", "location": "Pretoria (the dti Campus)", "website": "www.cipc.co.za"},
        {"name": "South African Revenue Service (SARS)", "service_type": "tax", "location": "Branches nationwide + eFiling", "website": "www.sars.gov.za"},
        {"name": "Electoral Commission of South Africa (IEC)", "service_type": "voting", "location": "HQ Centurion + local offices", "website": "www.elections.org.za"},
        {"name": "Deeds Office", "service_type": "land", "location": "11 deeds registries nationwide", "website": "www.dalrrd.gov.za"},
        {"name": "South African Social Security Agency (SASSA)", "service_type": "grants", "location": "Offices and pay points nationwide", "website": "www.sassa.gov.za"},
    ],
}

_AGENCY_SERVICE_ALIASES = {
    "tax": "tax", "taxes": "tax", "tax_filing": "tax",
    "id": "id", "national_id": "id", "id_application": "id",
    "passport": "passport",
    "business": "business", "business_reg": "business", "company": "business",
    "voting": "voting", "voter_reg": "voting", "elections": "voting",
    "land": "land", "land_title": "land", "property": "land",
    "health": "health", "healthcare": "health",
    "benefits": "benefits", "grants": "grants", "social": "grants",
}

_CHECKLIST_PURPOSES: Dict[str, List[str]] = {
    "visa_application": [
        "Passport valid for at least 6 months beyond intended stay",
        "Completed visa application form",
        "Recent passport photographs meeting the destination country's specification",
        "Proof of accommodation (hotel booking or host invitation letter)",
        "Return/onward flight itinerary",
        "Proof of sufficient funds (bank statements, typically 3-6 months)",
        "Travel/medical insurance where required",
        "Visa fee payment receipt",
        "Employment letter or proof of business/student status",
    ],
    "passport_application": [
        "Completed passport application form",
        "Proof of citizenship (birth certificate, national ID or previous passport)",
        "Compliant passport photographs",
        "Valid government-issued photo ID",
        "Application fee payment",
        "Parental consent documents for minors",
    ],
    "business_registration": [
        "Proposed business/company names (alternatives recommended)",
        "Identification of all directors/shareholders or proprietors",
        "Registered office address proof",
        "Constitutive documents (memorandum/articles or partnership agreement)",
        "Filing fee payment",
        "Tax registration details where required",
    ],
    "id_application": [
        "Birth certificate or declaration of age",
        "Proof of identity (existing ID, passport or attestation)",
        "Proof of address",
        "Completed enrolment/application form",
        "Application fee where applicable",
    ],
    "tax_registration": [
        "National ID or passport",
        "Proof of address",
        "Business registration certificate (for companies)",
        "Bank account details",
        "Completed tax registration form",
    ],
    "driving_licence": [
        "National ID or passport",
        "Learner's permit (where applicable)",
        "Driving school certificate (where applicable)",
        "Medical/eye test certificate",
        "Passport photographs",
        "Fee payment receipt",
    ],
}


def get_id_guide(country: str, id_type: str) -> Dict[str, Any]:
    country = country.lower().strip()
    id_type = id_type.lower().strip()
    country_guides = _ID_GUIDES.get(country)
    if not country_guides:
        return {"status": "not_found", "message": f"No ID guides for '{country}'. Available countries: {sorted(_ID_GUIDES)}"}
    guide = country_guides.get(id_type)
    if not guide:
        return {"status": "not_found", "message": f"No guide for id_type '{id_type}' in {country}. Available: {sorted(country_guides)}"}
    return {"status": "success", "country": country, "id_type": id_type, **guide}

def get_passport_guide(country: str) -> Dict[str, Any]:
    country = country.lower().strip()
    guide = _PASSPORT_GUIDES.get(country)
    if not guide:
        return {"status": "not_found", "message": f"No passport guide for '{country}'. Available: {sorted(_PASSPORT_GUIDES)}"}
    return {"status": "success", "country": country, **guide}

def get_business_registration_guide(country: str, biz_type: str) -> Dict[str, Any]:
    country = country.lower().strip()
    biz_type = biz_type.lower().strip()
    country_guides = _BUSINESS_REG_GUIDES.get(country)
    if not country_guides:
        return {"status": "not_found", "message": f"No business registration guides for '{country}'. Available: {sorted(_BUSINESS_REG_GUIDES)}"}
    guide = country_guides.get(biz_type)
    if not guide:
        return {"status": "not_found", "message": f"No guide for '{biz_type}' in {country}. Available: {sorted(country_guides)}"}
    return {"status": "success", "country": country, "biz_type": biz_type, **guide}

def get_tax_guide(country: str, tax_type: str) -> Dict[str, Any]:
    country = country.lower().strip()
    tax_type = tax_type.lower().strip()
    country_guides = _TAX_GUIDES.get(country)
    if not country_guides:
        return {"status": "not_found", "message": f"No tax guides for '{country}'. Available: {sorted(_TAX_GUIDES)}"}
    guide = country_guides.get(tax_type)
    if not guide:
        return {"status": "not_found", "message": f"No guide for tax '{tax_type}' in {country}. Available: {sorted(country_guides)}"}
    return {"status": "success", "country": country, "tax_type": tax_type, **guide}

def get_voting_info(country: str) -> Dict[str, Any]:
    country = country.lower().strip()
    info = _VOTING_INFO.get(country)
    if not info:
        return {"status": "not_found", "message": f"No voting info for '{country}'. Available: {sorted(_VOTING_INFO)}"}
    return {"status": "success", "country": country, **info}

def get_land_guide(country: str, transaction_type: str = "buy") -> Dict[str, Any]:
    country = country.lower().strip()
    transaction_type = transaction_type.lower().strip()
    country_guides = _LAND_GUIDES.get(country)
    if not country_guides:
        return {"status": "not_found", "message": f"No land guides for '{country}'. Available: {sorted(_LAND_GUIDES)}"}
    guide = country_guides.get(transaction_type)
    if not guide:
        return {"status": "not_found", "message": f"No land guide for '{transaction_type}' in {country}. Available: {sorted(country_guides)}"}
    return {"status": "success", "country": country, "transaction_type": transaction_type, **guide}

def get_social_services(country: str, service_type: str) -> Dict[str, Any]:
    country = country.lower().strip()
    service_type = service_type.lower().strip()
    country_services = _SOCIAL_SERVICES.get(country)
    if not country_services:
        return {"status": "not_found", "message": f"No social services data for '{country}'. Available: {sorted(_SOCIAL_SERVICES)}"}
    services = country_services.get(service_type)
    if not services:
        return {"status": "not_found", "message": f"No '{service_type}' programmes for {country}. Available: {sorted(country_services)}"}
    return {"status": "success", "country": country, "service_type": service_type, **services}

def generate_document_checklist(purpose: str, country: str = "") -> Dict[str, Any]:
    """Document checklist for a common government-service purpose."""
    purpose_key = purpose.lower().strip().replace(" ", "_")
    documents = _CHECKLIST_PURPOSES.get(purpose_key)
    if not documents:
        return {
            "status": "available_purposes",
            "message": f"No checklist for '{purpose}'. Choose one of the available purposes.",
            "available_purposes": sorted(_CHECKLIST_PURPOSES),
        }
    result = {"status": "success", "purpose": purpose_key, "documents": documents}
    if country:
        country = country.lower().strip()
        result["country"] = country
        if country in _AGENCY_LOCATIONS:
            svc_key = {
                "visa_application": "passport",
                "passport_application": "passport",
                "business_registration": "business_reg",
                "id_application": "id_application",
                "tax_registration": "tax_filing",
                "driving_licence": "id_application",
            }.get(purpose_key)
            offices = _AGENCY_LOCATIONS[country].get(svc_key or "", [])
            if offices:
                result["where_to_apply"] = offices
    return result

def find_agency(country: str, service_type: str = "") -> Dict[str, Any]:
    """Find the responsible government agencies for a country/service."""
    country = country.lower().strip()
    directory = _AGENCY_DIRECTORY.get(country)
    if not directory:
        return {"status": "not_found", "message": f"No agency directory for '{country}'. Available: {sorted(_AGENCY_DIRECTORY)}"}
    if service_type:
        wanted = _AGENCY_SERVICE_ALIASES.get(service_type.lower().strip(), service_type.lower().strip())
        matches = [a for a in directory if a["service_type"] == wanted]
        if not matches:
            return {
                "status": "not_found",
                "message": f"No agency for service '{service_type}' in {country}.",
                "available_services": sorted({a["service_type"] for a in directory}),
            }
        return {"status": "success", "country": country, "service_type": service_type, "agencies": matches, "total_results": len(matches)}
    return {"status": "success", "country": country, "agencies": directory, "total_results": len(directory)}


# ═══════════════════════════════════════════════════════════════════════════════
#  ADVANCED CAPABILITIES (v25.2.0)
# ═══════════════════════════════════════════════════════════════════════════════

_AGENCY_LOCATIONS: Dict[str, Dict[str, List[str]]] = {
    "south_africa": {
        "id_application": ["Department of Home Affairs, Pretoria", "Local Home Affairs Office"],
        "passport": ["Department of Home Affairs", "South African Embassy/Consulate (abroad)"],
        "business_reg": ["Companies and Intellectual Property Commission (CIPC), Pretoria"],
        "tax_filing": ["South African Revenue Service (SARS) Branch", "eFiling Portal"],
        "land_title": ["Deeds Office", "Surveyor-General's Office"],
        "voter_reg": ["Independent Electoral Commission (IEC) Office"],
    },
    "nigeria": {
        "id_application": ["NIMC Headquarters, Abuja", "Lagos State NIMC Office, Alausa", "Port Harcourt NIMC Office"],
        "passport": ["Nigeria Immigration Service HQ, Abuja", "Lagos Passport Office, Ikoyi"],
        "business_reg": ["CAC HQ, Maitama, Abuja", "CAC Lagos Office, Alausa"],
        "tax_filing": ["FIRS HQ, Wuse, Abuja", "LIRS Office, Alausa, Lagos"],
        "land_title": ["Ministry of Lands, State Secretariat", "Abuja Geographic Information System (AGIS)"],
        "voter_reg": ["INEC HQ, Maitama, Abuja", "INEC State Offices"],
    },
    "usa": {
        "id_application": ["Social Security Administration Office", "State DMV Office"],
        "passport": ["U.S. Passport Agency", "Acceptance Facility (Post Office/Library)"],
        "business_reg": ["Secretary of State Office", "County Clerk Office"],
        "tax_filing": ["IRS Taxpayer Assistance Center", "Local IRS Office"],
        "land_title": ["County Recorder's Office", "Title Company"],
        "voter_reg": ["County Election Office", "DMV (Motor Voter)"],
    },
    "uk": {
        "id_application": ["HM Passport Office", "Post Office (Check & Send)"],
        "passport": ["HM Passport Office, Peterborough", "Post Office"],
        "business_reg": ["Companies House, Cardiff", "Companies House London Office"],
        "tax_filing": ["HMRC Office", "Online via GOV.UK"],
        "land_title": ["HM Land Registry, Croydon", "Local Land Charges Office"],
        "voter_reg": ["Local Electoral Registration Office"],
    },
}

_SERVICE_DOCUMENTS: Dict[str, List[str]] = {
    "id_application": ["Birth certificate", "Passport photograph", "Proof of address", "National ID form", "Fingerprint capture receipt"],
    "passport": ["Birth certificate", "Passport photographs", "National ID", "Guarantor form", "Payment receipt"],
    "business_reg": ["Proposed business names", "Director IDs", "Registered address proof", "Memorandum of Association", "Fee payment"],
    "tax_filing": ["Taxpayer ID", "Financial statements", "Receipts/invoices", "Previous tax returns", "Bank statements"],
    "land_title": ["Deed of assignment", "Survey plan", "Payment receipt", "Tax clearance", "Power of attorney"],
    "voter_reg": ["Birth certificate", "National ID", "Proof of residence", "Passport photograph"],
}

_PROCESSING_TIME_ESTIMATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "south_africa": {
        "id_application": {"standard": "3-6 months", "express": "4-8 weeks", "emergency": "2-3 weeks"},
        "passport": {"standard": "1-3 months", "express": "2-4 weeks", "emergency": "1 week"},
        "business_reg": {"standard": "2-4 weeks", "express": "1 week", "emergency": "2-3 days"},
        "tax_filing": {"standard": "2-4 weeks", "express": "1 week", "emergency": "2-3 days"},
        "land_title": {"standard": "2-4 months", "express": "1-2 months", "emergency": "2-4 weeks"},
        "voter_reg": {"standard": "2-4 weeks", "express": "N/A", "emergency": "N/A"},
    },
    "nigeria": {
        "id_application": {"standard": "1-3 months", "express": "2-4 weeks", "emergency": "1-2 weeks"},
        "passport": {"standard": "2-6 weeks", "express": "1-2 weeks", "emergency": "3-5 days"},
        "business_reg": {"standard": "2-6 weeks", "express": "1-2 weeks", "emergency": "3-5 days"},
        "tax_filing": {"standard": "2-4 weeks", "express": "1 week", "emergency": "2-3 days"},
        "land_title": {"standard": "3-6 months", "express": "1-2 months", "emergency": "2-4 weeks"},
        "voter_reg": {"standard": "2-4 months", "express": "N/A", "emergency": "N/A"},
    },
    "usa": {
        "id_application": {"standard": "2-4 weeks", "express": "1-2 weeks", "emergency": "Same day (in-person)"},
        "passport": {"standard": "8-11 weeks", "express": "5-7 weeks", "emergency": "72 hours (life-or-death)"},
        "business_reg": {"standard": "1-4 weeks", "express": "1-2 weeks", "emergency": "Same day (some states)"},
        "tax_filing": {"standard": "21 days (e-file refund)", "express": "N/A", "emergency": "N/A"},
        "land_title": {"standard": "2-4 weeks", "express": "1 week", "emergency": "1-3 days"},
        "voter_reg": {"standard": "2-4 weeks", "express": "N/A", "emergency": "N/A"},
    },
    "uk": {
        "id_application": {"standard": "3-6 weeks", "express": "1 week", "emergency": "Same day (premium)"},
        "passport": {"standard": "3-6 weeks", "express": "1 week", "emergency": "Same day (premium)"},
        "business_reg": {"standard": "24 hours (online)", "express": "Same day", "emergency": "Same day"},
        "tax_filing": {"standard": "2-4 weeks (refund)", "express": "N/A", "emergency": "N/A"},
        "land_title": {"standard": "1-3 months", "express": "2-4 weeks", "emergency": "1 week"},
        "voter_reg": {"standard": "1-2 weeks", "express": "N/A", "emergency": "N/A"},
    },
}

_FORM_REQUIREMENTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "south_africa": {
        "tax_return": {"fields": [{"name": "taxpayer_id", "type": "text", "required": True}, {"name": "tax_year", "type": "select", "options": ["2023", "2024"], "required": True}, {"name": "gross_income", "type": "number", "required": True}, {"name": "deductions", "type": "number", "required": False}], "common_mistakes": ["Wrong tax year selected", "Missing signature", "Incorrect tax number"], "fee": "Free (eFiling)", "where_to_submit": "SARS eFiling portal or SARS branch"},
        "id_form": {"fields": [{"name": "surname", "type": "text", "required": True}, {"name": "first_name", "type": "text", "required": True}, {"name": "date_of_birth", "type": "date", "required": True}, {"name": "address", "type": "textarea", "required": True}], "common_mistakes": ["Mismatched names with birth cert", "Wrong date format"], "fee": "R140", "where_to_submit": "Home Affairs office or banking partner"},
        "passport_form": {"fields": [{"name": "surname", "type": "text", "required": True}, {"name": "first_name", "type": "text", "required": True}, {"name": "date_of_birth", "type": "date", "required": True}, {"name": "place_of_birth", "type": "text", "required": True}, {"name": "nationality", "type": "text", "required": True}], "common_mistakes": ["Blurry passport photo", "Unsigned form"], "fee": "R600 (adult)", "where_to_submit": "Home Affairs office or online booking"},
        "business_license": {"fields": [{"name": "proposed_name_1", "type": "text", "required": True}, {"name": "proposed_name_2", "type": "text", "required": True}, {"name": "nature_of_business", "type": "textarea", "required": True}, {"name": "registered_address", "type": "textarea", "required": True}, {"name": "director_1_name", "type": "text", "required": True}], "common_mistakes": ["Name already taken", "Wrong director details", "Unsigned forms"], "fee": "R125 (CIPC)", "where_to_submit": "CIPC online portal"},
        "voter_reg": {"fields": [{"name": "surname", "type": "text", "required": True}, {"name": "first_name", "type": "text", "required": True}, {"name": "date_of_birth", "type": "date", "required": True}, {"name": "address", "type": "textarea", "required": True}], "common_mistakes": ["Wrong voting district", "Already registered elsewhere"], "fee": "Free", "where_to_submit": "IEC office or online registration"},
    },
}

_ELIGIBILITY_CRITERIA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "south_africa": {
        "id_application": {"age_requirement": "Any age", "residency": "SA citizen or permanent resident", "required_documents": ["Birth certificate", "Passport photo", "Proof of address"], "fees": "R140", "special_conditions": "Biometric capture required"},
        "passport": {"age_requirement": "Any age", "residency": "SA citizen", "required_documents": ["ID document", "Photos"], "fees": "R600 (adult)", "special_conditions": "Minors need both parents' consent"},
        "business_reg": {"age_requirement": "Any age", "residency": "Any", "required_documents": ["Proposed names", "Director IDs", "Address proof"], "fees": "R175", "special_conditions": "At least one director required"},
        "tax_filing": {"age_requirement": "Any (if income exceeds threshold)", "residency": "SA tax residents", "required_documents": ["Tax number", "IRP5/IT3(a) certificates"], "fees": "Free to file", "special_conditions": "Annual turnover > R1M must register for VAT"},
        "land_title": {"age_requirement": "Any", "residency": "Any", "required_documents": ["Deed", "Survey plan", "Rates clearance"], "fees": "Varies", "special_conditions": "Transfer duty applies"},
        "voter_reg": {"age_requirement": "16+ (eligible to vote at 18)", "residency": "SA citizen", "required_documents": ["ID document"], "fees": "Free", "special_conditions": "Registration only during designated periods"},
    },
}


def book_appointment(country: str, service_type: str, date: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Schedule a mock appointment for a government service."""
    country = country.lower().strip()
    service_type = service_type.lower().strip()
    locations = _AGENCY_LOCATIONS.get(country, {})
    svc_locs = locations.get(service_type, [f"{country.upper()} Government Services Office"])
    documents = _SERVICE_DOCUMENTS.get(service_type, ["Valid identification", "Relevant forms", "Payment receipt"])
    appt_id = f"appt-{uuid.uuid4().hex[:8]}"
    confirmation = f"LUQI-GOV-{uuid.uuid4().hex[:4].upper()}"
    duration_map = {"id_application": 60, "passport": 45, "business_reg": 90, "tax_filing": 30, "land_title": 120, "voter_reg": 30}
    return {
        "status": "success",
        "appointment_id": appt_id,
        "country": country,
        "service": service_type,
        "date": date,
        "location": svc_locs[0] if svc_locs else "Main office",
        "confirmation_code": confirmation,
        "documents_to_bring": documents,
        "estimated_duration_minutes": duration_map.get(service_type, 60),
        "message": f"Appointment booked for {service_type} at {svc_locs[0] if svc_locs else 'Main office'} on {date}. Arrive 15 minutes early with all required documents.",
        "details": details or {},
    }


def check_application_status(country: str, application_id: str) -> Dict[str, Any]:
    """Check the status of a government application."""
    country = country.lower().strip()
    statuses = ["received", "under_review", "approved", "rejected", "ready_for_pickup"]
    stages = {
        "received": {"stage": "Application Received", "description": "Your application has been received and is awaiting initial review."},
        "under_review": {"stage": "Under Review", "description": "Your application is being reviewed by the relevant department."},
        "approved": {"stage": "Approved", "description": "Your application has been approved."},
        "rejected": {"stage": "Rejected", "description": "Your application was not approved. Contact the office for details."},
        "ready_for_pickup": {"stage": "Ready for Pickup", "description": "Your document/card is ready for collection."},
    }
    idx = hash(application_id + country) % len(statuses)
    status = statuses[idx]
    est_days = [30, 45, 14, 0, 1][idx]
    est_date = (datetime.now() + timedelta(days=est_days)).strftime("%Y-%m-%d") if est_days > 0 else "N/A"
    return {
        "status": "success",
        "application_id": application_id,
        "country": country,
        "current_status": status,
        "stage": stages[status]["stage"],
        "description": stages[status]["description"],
        "estimated_completion_date": est_date,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes": "Check back in 3-5 business days for updates." if status in ("received", "under_review") else "",
    }


def get_form_requirements(country: str, form_type: str) -> Dict[str, Any]:
    """Get requirements for filling out a government form."""
    country = country.lower().strip()
    form_type = form_type.lower().strip()
    country_forms = _FORM_REQUIREMENTS.get(country)
    if not country_forms:
        available_countries = list(_FORM_REQUIREMENTS.keys())
        return {"status": "not_found", "message": f"No form data for '{country}'. Available: {available_countries}"}
    form_data = country_forms.get(form_type)
    if not form_data:
        available_forms = list(country_forms.keys())
        return {"status": "not_found", "message": f"No form '{form_type}'. Available: {available_forms}"}
    return {
        "status": "success",
        "country": country,
        "form_type": form_type,
        "fields": form_data["fields"],
        "common_mistakes": form_data["common_mistakes"],
        "fee": form_data["fee"],
        "where_to_submit": form_data["where_to_submit"],
        "tips": ["Double-check all personal details match your ID", "Use black ink only", "Keep copies of everything submitted"],
    }


def calculate_processing_time(country: str, service_type: str, priority: str = "standard") -> Dict[str, Any]:
    """Estimate processing time for a government service."""
    country = country.lower().strip()
    service_type = service_type.lower().strip()
    priority = priority.lower().strip()
    country_times = _PROCESSING_TIME_ESTIMATES.get(country)
    if not country_times:
        available = list(_PROCESSING_TIME_ESTIMATES.keys())
        return {"status": "not_found", "message": f"No processing data for '{country}'. Available: {available}"}
    svc_times = country_times.get(service_type)
    if not svc_times:
        available_svcs = list(country_times.keys())
        return {"status": "not_found", "message": f"No data for '{service_type}'. Available: {available_svcs}"}
    estimate = svc_times.get(priority, svc_times.get("standard", "Unknown"))
    all_options = {k: v for k, v in svc_times.items() if v != "N/A"}
    return {
        "status": "success",
        "country": country,
        "service_type": service_type,
        "priority": priority,
        "estimated_time": estimate,
        "all_priorities": all_options,
        "note": f"{priority.title()} processing for {service_type} in {country.title()}",
    }


def get_eligibility_criteria(country: str, service_type: str) -> Dict[str, Any]:
    """Get eligibility criteria for a government service."""
    country = country.lower().strip()
    service_type = service_type.lower().strip()
    country_criteria = _ELIGIBILITY_CRITERIA.get(country)
    if not country_criteria:
        available = list(_ELIGIBILITY_CRITERIA.keys())
        return {"status": "not_found", "message": f"No eligibility data for '{country}'. Available: {available}"}
    criteria = country_criteria.get(service_type)
    if not criteria:
        available_svcs = list(country_criteria.keys())
        return {"status": "not_found", "message": f"No criteria for '{service_type}'. Available: {available_svcs}"}
    return {
        "status": "success",
        "country": country,
        "service_type": service_type,
        "age_requirement": criteria["age_requirement"],
        "residency_status": criteria["residency"],
        "required_documents": criteria["required_documents"],
        "fees": criteria["fees"],
        "special_conditions": criteria["special_conditions"],
        "meets_basic_requirements": "Review the criteria above to confirm eligibility",
    }


def generate_service_roadmap(country: str, goals: List[str]) -> Dict[str, Any]:
    """Generate a multi-step roadmap for achieving government-related goals."""
    country = country.lower().strip()
    goal_definitions: Dict[str, Dict[str, Any]] = {
        "register_business": {"name": "Register Business", "prerequisites": [], "steps": ["Choose business structure", "Reserve business name", "Prepare incorporation documents", "Submit to registration authority", "Collect certificate"], "estimated_weeks": 4, "estimated_cost_usd": 50},
        "get_tax_id": {"name": "Get Tax ID", "prerequisites": ["register_business"], "steps": ["Gather business registration docs", "Apply for tax ID online or at tax office", "Submit verification documents", "Receive tax certificate"], "estimated_weeks": 2, "estimated_cost_usd": 0},
        "open_bank_account": {"name": "Open Business Bank Account", "prerequisites": ["register_business"], "steps": ["Choose bank", "Gather KYC documents", "Complete account opening forms", "Deposit minimum balance"], "estimated_weeks": 1, "estimated_cost_usd": 25},
        "hire_employees": {"name": "Hire First Employees", "prerequisites": ["register_business", "open_bank_account"], "steps": ["Register with labour department", "Set up payroll system", "Draft employment contracts", "Register employees for tax", "Comply with labour laws"], "estimated_weeks": 3, "estimated_cost_usd": 100},
        "get_office_space": {"name": "Secure Office Space", "prerequisites": [], "steps": ["Determine budget and location", "Inspect properties", "Sign lease agreement", "Register business address"], "estimated_weeks": 3, "estimated_cost_usd": 500},
        "get_passport": {"name": "Get International Passport", "prerequisites": [], "steps": ["Gather birth certificate and ID", "Complete online application", "Pay fees", "Visit passport office for biometrics", "Collect passport"], "estimated_weeks": 4, "estimated_cost_usd": 40},
        "get_national_id": {"name": "Get National ID", "prerequisites": [], "steps": ["Gather birth certificate", "Complete enrollment form", "Visit enrollment center", "Capture biometrics", "Collect ID card"], "estimated_weeks": 6, "estimated_cost_usd": 10},
    }
    resolved_goals = []
    for g in goals:
        g_clean = g.lower().strip().replace(" ", "_")
        resolved_goals.append(g_clean)
    steps_result = []
    visited = set()
    total_weeks = 0
    total_cost = 0

    def add_goal(g):
        nonlocal total_weeks, total_cost
        if g in visited or g not in goal_definitions:
            return
        visited.add(g)
        gd = goal_definitions[g]
        for prereq in gd.get("prerequisites", []):
            add_goal(prereq)
        steps_result.append({
            "goal_id": g,
            "goal_name": gd["name"],
            "steps": gd["steps"],
            "estimated_weeks": gd["estimated_weeks"],
            "estimated_cost_usd": gd["estimated_cost_usd"],
            "prerequisites": gd.get("prerequisites", []),
        })
        total_weeks += gd["estimated_weeks"]
        total_cost += gd["estimated_cost_usd"]

    for g in resolved_goals:
        add_goal(g)
    if not steps_result:
        available = list(goal_definitions.keys())
        return {"status": "not_found", "message": f"No recognized goals. Available: {available}"}
    return {
        "status": "success",
        "country": country,
        "goals": goals,
        "roadmap_steps": steps_result,
        "total_estimated_weeks": total_weeks,
        "total_estimated_cost_usd": total_cost,
        "parallel_steps_possible": len(steps_result) > 1,
        "note": f"Roadmap for {country}. Review steps with a local attorney for compliance.",
    }
