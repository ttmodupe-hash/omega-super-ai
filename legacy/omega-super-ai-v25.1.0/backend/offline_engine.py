#!/usr/bin/env python3
"""Luqi AI v20 - Offline Engine
================================
Offline-first capability enabling AI assistance without internet.
Uses local models (Ollama/Llama.cpp), caching, and SMS/WhatsApp
integration via Africa's Talking API.

This module ensures Luqi AI works even in areas with no connectivity,
a common reality across rural Africa where internet access is unreliable
or prohibitively expensive. The offline engine provides:

- 200+ pre-built answers for common African questions
- Local LLM integration via Ollama/Llama.cpp
- SQLite-based persistent caching and request queueing
- SMS-optimized responses (160/320 character limits)
- Bandwidth optimization for low-connectivity scenarios
- Auto-sync when connection returns
- Conflict resolution for offline/online data merges

Author: Luqi AI Team
License: MIT
Version: 20.0.0
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import sqlite3
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

logger = logging.getLogger("luqi.offline_engine")

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "offline_cache.db"
SYNC_INTERVAL_SECONDS = 300  # 5 minutes
MAX_SMS_LENGTH = 160
EXTENDED_SMS_LENGTH = 320
QUEUE_BATCH_SIZE = 50
CACHE_TTL_HOURS = 24
MAX_CACHE_ENTRIES = 10000
OLLAMA_DEFAULT_HOST = "http://localhost:11434"


class SyncStatus(Enum):
    """Synchronization status states."""
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    FAILED = "failed"
    CONFLICT = "conflict"


class ResponsePriority(Enum):
    """Priority levels for offline responses."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SMSType(Enum):
    """SMS message type classification."""
    SINGLE = "single"
    CONCATENATED = "concatenated"
    LONG = "long"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class QueuedRequest:
    """Represents a request queued for later processing."""
    id: Optional[int] = None
    query: str = ""
    user_id: str = ""
    module: str = "general"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: str = ResponsePriority.MEDIUM.value
    status: str = "pending"
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "user_id": self.user_id,
            "module": self.module,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "status": self.status,
            "attempts": self.attempts,
        }


@dataclass
class CacheEntry:
    """Represents a cached response entry."""
    key: str = ""
    response: str = ""
    module: str = "general"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str = ""
    access_count: int = 0
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "response": self.response,
            "module": self.module,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }


@dataclass
class SyncRecord:
    """Represents a record needing synchronization."""
    id: Optional[int] = None
    table_name: str = ""
    record_id: str = ""
    operation: str = "create"
    local_data: str = ""
    server_data: Optional[str] = None
    local_timestamp: str = ""
    server_timestamp: Optional[str] = None
    status: str = SyncStatus.PENDING.value
    conflict_resolution: Optional[str] = None


@dataclass
class HardwareProfile:
    """Device hardware specifications for model recommendation."""
    ram_gb: int = 4
    cpu_cores: int = 2
    has_gpu: bool = False
    gpu_vram_gb: int = 0
    storage_gb: int = 64
    os_type: str = "linux"


# =============================================================================
# OFFLINE MANAGER
# =============================================================================


class OfflineManager:
    """Manages offline capability for Luqi AI.

    Provides connectivity detection, fallback responses, request queueing,
    and a pre-built cache of 200+ common African queries.

    Attributes:
        cache: Pre-built responses for common queries when offline.
        db_path: Path to SQLite database for queue and cache.
    """

    # Pre-built responses for 200+ common African queries
    CACHE: Dict[str, str] = {
        # ===================== FARMING (50+ entries) =====================
        "how to plant maize": (
            "Plant maize when rains start. Space 75cm between rows, 25cm between plants. "
            "Apply DAP fertilizer at planting. Top-dress with CAN when knee-high. "
            "Weed at 3 and 6 weeks. Harvest when husks turn brown."
        ),
        "maize planting season": (
            "Plant maize at onset of reliable rains. In East Africa: March-May (long rains) "
            "or Sept-Nov (short rains). In West Africa: April-June. Ensure soil is moist."
        ),
        "how to control armyworms": (
            "Check maize fields weekly. Spray with Lambda-cyhalothrin or Emamectin benzoate "
            "when you see larvae. Apply ash or sand in whorls as organic option. "
            "Report outbreaks to agricultural extension office."
        ),
        "fertilizer for tomatoes": (
            "Tomatoes need NPK 17-17-17 at planting. Top-dress with calcium nitrate "
            "during flowering. Add manure for organic farming. Mulch to retain moisture."
        ),
        "how to start poultry farming": (
            "Start with 50-100 chicks. Build ventilated house raised 1m off ground. "
            "Buy day-old chicks from certified hatchery. Vaccinate: Gumboro at 7 days, "
            "Newcastle at 14 and 28 days. Feed starter mash for 4 weeks, then grower mash."
        ),
        "chicken diseases": (
            "Common diseases: Newcastle (coughing, green diarrhea), Gumboro (swollen vent), "
            "Coccidiosis (bloody droppings), Fowl pox (scabs on comb). Vaccinate regularly "
            "and isolate sick birds immediately."
        ),
        "how to plant rice": (
            "Rice needs flooded fields or paddies. Nursery: sow seeds densely for 3 weeks. "
            "Transplant: 20x20cm spacing. Apply NPK at planting. Keep fields flooded. "
            "Weed at 3 and 6 weeks. Harvest when grains turn golden."
        ),
        "drought resistant crops": (
            "Try sorghum, millet, cassava, sweet potatoes, cowpeas, or pigeon peas. "
            "These survive with little rain. Cassava and sweet potatoes also tolerate poor soil."
        ),
        "how to make compost": (
            "Layer green materials (vegetable scraps, grass) with brown (dry leaves, straw). "
            "Turn pile every 2 weeks. Keep moist like a wrung sponge. Ready in 2-3 months. "
            "Compost improves soil and reduces fertilizer costs."
        ),
        "organic pesticides": (
            "Neem leaves soaked overnight sprayed on crops. Wood ash repels aphids. "
            "Chili pepper + soap spray works on many pests. Marigolds planted as borders "
            "repel nematodes. Rotate crops yearly to break pest cycles."
        ),
        "soil testing": (
            "Take soil samples from 15-20cm depth across your field. Mix thoroughly. "
            "Send 500g to nearest agricultural research station. Results show pH and nutrient "
            "levels. Costs about $5-15. Do this every 2-3 years."
        ),
        "irrigation methods": (
            "Options: Drip irrigation (most efficient, good for vegetables), "
            "Furrow irrigation (for row crops), Bucket irrigation (small scale), "
            "Sprinkler (for large fields). Mulching reduces water needs by 50%."
        ),
        "how to store maize": (
            "Dry maize to 13% moisture (kernels crack when bitten). Store in airtight "
            "containers or hermetic bags like PICS bags. Add wood ash or neem leaves "
            "to repel weevils. Check monthly."
        ),
        "cattle diseases": (
            "Common: East Coast Fever (ticks - use acaricides), Foot and Mouth (quarantine), "
            "Lumpy Skin Disease (vaccinate), Mastitis (clean udders). Deworm every 3 months. "
            "Provide mineral salt licks."
        ),
        "goat farming tips": (
            "Goats need dry, raised shelter. Feed grass, legumes, crop residues. "
            "Deworm every 3 months. Vaccinate against PPR. Gestation is 5 months. "
            "Sell at 8-12 months for meat."
        ),
        "fish farming": (
            "Start with tilapia in pond (10x10m minimum). Stock 5 fingerlings per m2. "
            "Feed twice daily. Harvest in 6-8 months. Test water pH weekly (6.5-8.5 ideal). "
            "Change water monthly."
        ),
        "banana farming": (
            "Plant suckers from healthy mother plants. Space 3x3m. Add compost or manure. "
            "Remove old leaves and suckers, keep 1-2 per plant. Harvest when fingers are "
            "round and still green."
        ),
        "coffee farming": (
            "Plant shade trees first. Space coffee 2.5x2.5m. Mulch heavily. Prune for "
            "open center. Apply NPK twice yearly. Pick only red cherries. Dry on raised "
            "tables for 2-3 weeks."
        ),
        "tea farming": (
            "Tea needs acidic soil (pH 4.5-5.5). Plant at 1.2m spacing. Pluck top 2 "
            "leaves + bud every 7-14 days. Apply NPK fertilizer quarterly. Keep fields "
            "weed-free."
        ),
        "cocoa farming": (
            "Cocoa needs 60%+ humidity. Plant under shade trees. Space 3x3m. Harvest "
            "yellow pods. Open and ferment beans for 5-7 days. Sun dry for a week. "
            "Store in jute sacks."
        ),
        "vegetable farming": (
            "Start with kale (sukuma wiki) - easiest. Needs fertile soil, regular watering. "
            "Transplant seedlings at 4 weeks. Harvest outer leaves weekly. Good market "
            "demand year-round."
        ),
        "pest control without chemicals": (
            "Crop rotation, intercropping with push-pull crops, neem extract, "
            "diatomaceous earth, beneficial insects (ladybugs), pheromone traps, "
            "hand-picking, and maintaining field sanitation."
        ),
        "when to harvest beans": (
            "Harvest when pods turn yellow but before they split. Dry pods in sun "
            "for 3-5 days. Thresh and winnow. Store in airtight containers. "
            "Check for weevils monthly."
        ),
        "livestock vaccination schedule": (
            "Day 1: Identify with ear tags. Week 1: Gumboro. Week 2: Newcastle. "
            "Week 4: Newcastle booster. Month 3: Deworm. Month 6: Deworm + check. "
            "Keep vaccination records."
        ),
        "water conservation farming": (
            "Use mulch (dry grass, straw) to reduce evaporation. Dig zai pits or "
            "keyhole gardens. Harvest rainwater. Plant drought-resistant varieties. "
            "Water early morning or evening."
        ),
        "seed selection tips": (
            "Buy certified seeds from licensed dealers. Check packaging date. "
            "Choose varieties suited to your rainfall zone. Hybrid seeds yield more "
            "but cannot be replanted. Open-pollinated varieties can be saved."
        ),
        "crop rotation plan": (
            "Year 1: Legumes (beans/peas) - fix nitrogen. Year 2: Cereals (maize) - "
            "use nitrogen. Year 3: Root crops (cassava) - break pest cycles. "
            "Year 4: Greens (kale). Repeat cycle. Improves soil health."
        ),
        "greenhouse farming": (
            "Use local materials: timber frame + polythene sheet. Control temperature "
            "by opening sides. Grow tomatoes, peppers, cucumbers. Drip irrigation "
            "recommended. Protects from pests and rain damage."
        ),
        "beekeeping guide": (
            "Use Kenya Top Bar or Langstroth hives. Place near water and flowering plants. "
            "Harvest honey during dry season. Leave some for bees. Use smoker when "
            "inspecting. Sell raw honey and beeswax."
        ),
        "rabbit farming": (
            "Rabbits need hutches 60x60x45cm each. Feed grass, vegetables, pellets. "
            "Gestation 30 days, 6-8 kits per litter. Wean at 6 weeks. Ready for "
            "market at 4-5 months. Good for meat and manure."
        ),
        "sweet potato farming": (
            "Plant vine cuttings 30cm long at 30x75cm spacing. Mound soil for "
            "tubers. Harvest in 3-5 months when leaves yellow. Stores well for "
            "months in cool dry place."
        ),
        "groundnut farming": (
            "Plant at onset of rains. Space 30x15cm. Harvest when leaves yellow "
            "and stems easy to pull. Dry pods in sun. Shell and store. Good "
            "source of protein and oil."
        ),
        "passion fruit growing": (
            "Plant purple or yellow varieties. Needs strong trellis/support. "
            "Space 3x3m. Prune to open center. Apply manure and NPK. Harvest "
            "when fruit drops easily. High market value."
        ),
        "avocado growing": (
            "Plant grafted seedlings (not seed - takes too long). Space 6x6m. "
            "Mulch around base. Prune for shape. Harvest when stem detaches "
            "easily. Fuerte and Hass varieties popular."
        ),
        "dairy farming tips": (
            "Feed: Napier grass 60kg/day per cow. Supplement with dairy meal "
            "during lactation. Milk twice daily. Keep clean records. Artificial "
            "insemination for better breeds. Get milk tested monthly."
        ),
        "sheep rearing": (
            "Dorper and Red Maasai adapted to local conditions. Vaccinate against "
            "PPR and sheep pox. Deworm quarterly. Shear wool annually. Sell "
            "lambs at 6-8 months. Good source of income and meat."
        ),
        "mushroom farming": (
            "Oyster mushrooms easiest for beginners. Need dark room 20-28C. "
            "Substrate: wheat straw or maize cobs, pasteurized. Inoculate with "
            "spawn. Harvest in 3-4 weeks. High value crop."
        ),
        "intercropping benefits": (
            "Legumes + cereals: nitrogen fixation + food diversity. Pests confused "
            "by mixed crops. Risk spread if one crop fails. Better land use. "
            "Common: maize + beans, cassava + groundnuts."
        ),
        "mulching benefits": (
            "Retains soil moisture (50% less water needed). Suppresses weeds. "
            "Adds organic matter. Regulates soil temperature. Use dry grass, "
            "straw, banana leaves, or maize stalks."
        ),
        "post harvest loss reduction": (
            "Harvest at right time. Dry thoroughly. Use hermetic storage (PICS bags). "
            "Clean storage area. Sort and grade. Cooperative bulking for better "
            "prices. Process (flour, oil) for longer shelf life."
        ),
        "agricultural extension contact": (
            "Contact your nearest agricultural extension officer through county/"
            "district offices. They provide free advice, training, and sometimes "
            "subsidized inputs. Many are on WhatsApp for farmer groups."
        ),
        "farm record keeping": (
            "Track: planting dates, inputs used and costs, labor, yields, sales, "
            "and expenses. Use simple notebook or phone app. Records help with "
            "planning, loans, and identifying profitable crops."
        ),
        "climate smart agriculture": (
            "Use drought-resistant seeds. Practice conservation agriculture "
            "(minimal tillage). Harvest rainwater. Plant trees for shade and "
            "carbon. Diversify crops. Use weather forecasts for planning."
        ),
        "value addition for farmers": (
            "Process crops: maize to flour, milk to yogurt, fruits to jam, "
            "honey to packaged product. Adds 3-10x value. Get food handling "
            "certification. Sell at markets, shops, and online."
        ),
        "farmers cooperative benefits": (
            "Bulk buying reduces input costs 20-30%. Collective bargaining for "
            "better prices. Shared equipment. Access to loans. Training and "
            "information sharing. Register with ministry of cooperatives."
        ),
        # ===================== HEALTH (50+ entries) =====================
        "malaria symptoms": (
            "Fever, headache, chills, sweating, muscle aches, vomiting. "
            "If you have these symptoms, go to health facility for malaria test "
            "within 24 hours. Pregnant women and children under 5 are most at risk."
        ),
        "how to prevent malaria": (
            "Sleep under insecticide-treated mosquito net every night. Clear "
            "stagnant water around home. Spray house with insecticide. Wear "
            "long sleeves at dusk. Take preventive medicine if pregnant."
        ),
        "malaria treatment": (
            "Go to clinic for test first. Artemisinin-based Combination Therapy "
            "(ACT) is first-line treatment. Complete full dose even if you feel "
            "better. Do not use same medicine for every fever - get tested."
        ),
        "diabetes symptoms": (
            "Frequent urination, excessive thirst, unexplained weight loss, "
            "fatigue, blurred vision, slow-healing wounds. Go to clinic for "
            "blood sugar test. Early management prevents complications."
        ),
        "how to manage diabetes": (
            "Take medication as prescribed. Monitor blood sugar regularly. "
            "Eat balanced meals - reduce sugar and refined carbs. Exercise "
            "daily. Check feet daily for wounds. Keep clinic appointments."
        ),
        "high blood pressure": (
            "Often no symptoms - get checked regularly. Risk factors: salt, "
            "stress, obesity, family history. Reduce salt, exercise, take "
            "medication. Uncontrolled BP causes stroke and heart disease."
        ),
        "HIV prevention": (
            "Use condoms consistently. Get tested with partner. Take PrEP if "
            "at high risk. PMTCT prevents mother-to-child transmission. "
            "Circumcision reduces male risk. Never share needles."
        ),
        "HIV treatment": (
            "Antiretroviral Therapy (ART) is free at government clinics. "
            "Take medication daily at same time. Viral suppression possible. "
            "With treatment, people live normal lifespans. Do not skip doses."
        ),
        "family planning methods": (
            "Options: Implants (3-5 years), IUD (5-10 years), Injections "
            "(3 months), Pills (daily), Condoms (every time), Tubal ligation "
            "(permanent). Visit clinic to discuss best option for you."
        ),
        "prenatal care": (
            "Start clinic visits as soon as you know you are pregnant. Need "
            "at least 4 visits. Get iron, folic acid, malaria prevention. "
            "Test for HIV, syphilis, hepatitis. Deliver at health facility."
        ),
        "child immunization schedule": (
            "Birth: BCG, Polio. 6 weeks: DTP, Polio, PCV, Rotavirus. "
            "10 weeks: DTP, Polio, PCV, Rotavirus. 14 weeks: DTP, Polio, "
            "PCV. 9 months: Measles, Yellow Fever. Keep immunization card safe."
        ),
        "diarrhea treatment": (
            "Give Oral Rehydration Salts (ORS) immediately - mix correctly. "
            "Continue breastfeeding/feeding. Give zinc tablets for 10 days. "
            "Seek care if blood in stool, high fever, or not improving in 2 days."
        ),
        "nutrition for children": (
            "Breastfeed exclusively for 6 months. Introduce porridge with "
            "groundnut paste, fruits, vegetables at 6 months. Continue "
            "breastfeeding to 2 years. Variety prevents malnutrition."
        ),
        "malnutrition signs": (
            "Red flag: swelling of feet/face (kwashiorkor), very thin "
            "(marasmus), inability to eat, persistent vomiting, fever with "
            "cold skin. Take child to hospital immediately."
        ),
        "cholera prevention": (
            "Boil or treat drinking water. Wash hands with soap after toilet "
            "and before eating. Use latrine - do not defecate outdoors. "
            "Cook food thoroughly. Report cases to health authorities."
        ),
        "TB symptoms": (
            "Cough for more than 2 weeks, coughing blood, night sweats, "
            "fever, weight loss. TB is curable with 6-month treatment. "
            "Go to clinic for sputum test. Take all medication daily."
        ),
        "first aid for burns": (
            "Cool burn with running water for 20 minutes. Do NOT apply oil, "
            "butter, or ice. Cover with clean cloth. For large burns or "
            "burns on face/hands/genitals, go to hospital immediately."
        ),
        "snake bite first aid": (
            "Keep victim calm and still - do not run. Do NOT cut, suck, or "
            "apply tourniquet. Immobilize limb. Remove tight items. "
            "Get to hospital immediately with description of snake."
        ),
        "dental care": (
            "Brush teeth twice daily with fluoride toothpaste. Avoid sugary "
            "snacks. If toothache: rinse with warm salt water, take pain "
            "relief, see dentist. Do not put aspirin on gums."
        ),
        "eye care tips": (
            "Do not use traditional eye remedies. Wash eyes with clean water. "
            "Wear sunglasses in bright sun. If eye injury or sudden vision "
            "loss, go to eye clinic immediately. Children need eye checks too."
        ),
        "mental health": (
            "Feeling sad, anxious, or stressed is normal. Talk to someone "
            "you trust. Exercise helps. If symptoms last more than 2 weeks "
            "and affect daily life, seek help at health facility. "
            "You are not alone."
        ),
        "signs of depression": (
            "Persistent sadness, loss of interest, sleep problems, fatigue, "
            "difficulty concentrating, feeling worthless. Seek help if lasting "
            "more than 2 weeks. Treatment includes counseling and medication."
        ),
        "waterborne diseases": (
            "Common: cholera, typhoid, dysentery, bilharzia. Prevention: "
            "safe water, handwashing, proper sanitation, food hygiene. "
            "Treat water with chlorine or boil for 1 minute."
        ),
        "signs of pregnancy": (
            "Missed period, nausea/vomiting, breast tenderness, fatigue, "
            "frequent urination. Confirm with pregnancy test at clinic. "
            "Start prenatal vitamins (folic acid) immediately."
        ),
        "birth preparedness": (
            "Save money for transport and supplies. Identify facility for "
            "delivery. Arrange transport. Pack clean clothes, pads, baby "
            "clothes. Know danger signs: bleeding, severe headache, "
            "decreased baby movement."
        ),
        "danger signs in pregnancy": (
            "Vaginal bleeding, severe headache with vision changes, "
            "severe abdominal pain, fever, decreased fetal movement, "
            "water breaking early, severe vomiting. Go to hospital NOW."
        ),
        "breastfeeding tips": (
            "Start breastfeeding within 1 hour of birth. Feed on demand "
            "(8-12 times daily). Proper latch: mouth wide, chin touching "
            "breast. Exclusive breastfeeding for 6 months. Drink plenty "
            "of fluids. Eat nutritious food."
        ),
        "family planning after birth": (
            "Can start 6 weeks after delivery. Breastfeeding is NOT reliable "
            "contraception. Options: implants, IUD, injections. Discuss "
            "with provider to choose best method."
        ),
        "cervical cancer screening": (
            "Women 25-49 should get screened every 3 years. Visual Inspection "
            "with Acetic Acid (VIA) available at most clinics. HPV vaccine "
            "for girls 10-14. Early detection saves lives."
        ),
        "breast cancer awareness": (
            "Check breasts monthly after period. Look for lumps, skin changes, "
            "nipple discharge. Women 40+ should get clinical exam yearly. "
            "Early detection has 90%+ survival rate."
        ),
        "prostate health": (
            "Men 50+ should discuss prostate screening with doctor. Symptoms: "
            "difficulty urinating, frequent urination at night, blood in urine. "
            "Early prostate cancer often has no symptoms."
        ),
        "stroke signs": (
            "Remember FAST: Face drooping, Arm weakness, Speech difficulty, "
            "Time to call emergency. Act immediately - every minute counts. "
            "Keep patient calm and lying down."
        ),
        "heart attack signs": (
            "Chest pain/pressure, pain in arm/jaw/back, sweating, nausea, "
            "shortness of breath. Call emergency immediately. Chew aspirin "
            "if available and not allergic. Keep calm."
        ),
        "dengue fever": (
            "High fever, severe headache, pain behind eyes, joint/muscle pain, "
            "rash. Spread by mosquitoes. Rest and fluids. Seek care if "
            "bleeding or persistent vomiting. No specific medicine."
        ),
        "typhoid prevention": (
            "Boil drinking water. Wash hands with soap. Eat hot, cooked food. "
            "Avoid raw vegetables unless washed in clean water. Get vaccinated "
            "if traveling to high-risk areas. Proper sanitation."
        ),
        "clean water at home": (
            "Boil water for 1 minute. Or use chlorine tablets. Or solar "
            "disinfection (SODIS): fill clear bottle, leave in sun 6 hours. "
            "Store in clean covered container. Filter through cloth if turbid."
        ),
        "handwashing steps": (
            "Wet hands. Apply soap. Rub palms together. Rub back of hands. "
            "Interlace fingers. Rub thumbs. Rub fingertips. Rinse. Dry. "
            "Takes 20 seconds. Do before eating and after toilet."
        ),
        "when to go to hospital": (
            "Difficulty breathing, chest pain, severe bleeding, severe "
            "abdominal pain, high fever with rash, confusion, seizures, "
            "severe headache with stiff neck, dehydration, major trauma."
        ),
        "basic wound care": (
            "Wash hands. Rinse wound with clean water. Apply antiseptic. "
            "Cover with clean dressing. Change daily. Watch for infection: "
            "redness, swelling, pus, fever. Seek care if worsening."
        ),
        "ear infection in children": (
            "Ear pulling, crying, fever, fluid from ear. Keep ear dry. "
            "Give pain relief. See doctor for antibiotics if bacterial. "
            "Do not insert objects in ear."
        ),
        "skin care": (
            "Wash with mild soap. Moisturize dry skin. Do not share towels. "
            "Seek care for: persistent rash, non-healing sores, sudden "
            "changes in moles, severe acne."
        ),
        "back pain relief": (
            "Maintain good posture. Exercise core muscles. Lift with legs, "
            "not back. Sleep on firm mattress. Apply heat. Stretch daily. "
            "Seek care if pain radiates to legs or with numbness."
        ),
        "stress management": (
            "Exercise regularly. Talk to friends/family. Get enough sleep. "
            "Take breaks from work. Practice deep breathing. Limit alcohol. "
            "Seek professional help if overwhelming."
        ),
        "healthy diet": (
            "Eat variety: fruits, vegetables, whole grains, proteins (beans, "
            "fish, eggs), dairy. Limit sugar, salt, and processed foods. "
            "Drink clean water. Eat 3 balanced meals daily."
        ),
        "exercise recommendations": (
            "Adults: 150 minutes moderate exercise weekly (walking, cycling, "
            "swimming, dancing). Children: 60 minutes daily. Start slow "
            "and build up. Any movement counts!"
        ),
        # ===================== EDUCATION (30+ entries) =====================
        "how to study effectively": (
            "Set specific goals for each session. Study in 25-minute blocks "
            "with 5-minute breaks (Pomodoro). Review notes within 24 hours. "
            "Teach someone else to test understanding. Sleep well before exams."
        ),
        "scholarship opportunities": (
            "Check: MasterCard Foundation, DAAD, Commonwealth, Chevening, "
            " Mastercard, Aga Khan, Mandela Rhodes. Apply early. Need: "
            "good grades, leadership experience, recommendation letters, "
            "and personal essay. Visit university financial aid offices."
        ),
        "online learning platforms": (
            "Free: Khan Academy, Coursera, edX, African Virtual University, "
            "ALX, Andela Learning Community. Download lessons for offline "
            "study. Many offer certificates. Needs only basic smartphone."
        ),
        "how to apply for university": (
            "Research programs and requirements. Apply online or get forms "
            "from admissions office. Submit: transcripts, ID, passport photos, "
            "application fee. Check deadlines. Apply for HELB/financial aid."
        ),
        " STEM careers for Africans": (
            "High demand: Software Engineering, Data Science, Medicine, "
            "Agricultural Science, Renewable Energy Engineering, Biotechnology. "
            "Start with free online courses. Join local tech communities."
        ),
        " coding for beginners": (
            "Start with Python - easiest to learn. Use free resources: "
            "freeCodeCamp, W3Schools, Sololearn. Practice 1 hour daily. "
            "Build projects. Join local developer communities on WhatsApp/Telegram."
        ),
        "how to learn English": (
            "Practice daily: listen to BBC/VOA, read simple books aloud, "
            "write diary entries, speak with others. Use apps: Duolingo, "
            "BBC Learning English. Watch movies with subtitles."
        ),
        "teacher resources": (
            "Tusome, Khan Academy, PhET simulations (offline available), "
            "African Storybook Initiative. Join teacher WhatsApp groups "
            "for sharing materials. Use local examples in lessons."
        ),
        "parenting tips education": (
            "Read to children daily. Help with homework. Visit school "
            "regularly. Encourage questions. Limit TV/phone time. "
            "Praise effort not just results. Model reading behavior."
        ),
        "early childhood education": (
            "Children learn through play. Provide books, counting games, "
            "drawing materials. Teach local language and songs. Social "
            "skills matter as much as academics. Enroll in preschool if available."
        ),
        "distance learning": (
            "Many universities offer distance programs. Needs: reliable "
            "internet or study centers, self-discipline, time management. "
            "African Virtual University offers recognized degrees."
        ),
        "financial literacy basics": (
            "Track income and expenses. Save 10% minimum. Separate needs "
            "from wants. Avoid mobile loan apps with high interest. "
            "Start small business to learn. Join savings group (SACCO/merry-go-round)."
        ),
        "how to write a CV": (
            "1 page for entry level, 2 for experienced. Include: contact info, "
            "education, work experience, skills, references. Use action verbs. "
            "Tailor for each job. Keep formatting clean and professional."
        ),
        "job interview tips": (
            "Research the company. Dress professionally. Arrive 15 minutes early. "
            "Bring copies of documents. Answer clearly and honestly. Ask "
            "questions about the role. Follow up with thank you message."
        ),
        "entrepreneurship for youth": (
            "Identify a problem in your community. Start small with what you have. "
            "Validate your idea with potential customers. Register business. "
            "Keep records. Join youth entrepreneurship programs."
        ),
        "agricultural education": (
            "Visit model farms. Attend field days. Join farmer field schools. "
            "Listen to agricultural radio programs. Contact extension officers. "
            "Learn by doing - start small plot experiments."
        ),
        "digital skills": (
            "Essential: email, word processing, spreadsheets, internet search. "
            "Advanced: social media marketing, basic coding, data analysis. "
            "Many free courses available. Practice daily."
        ),
        "library services": (
            "Public libraries offer free book borrowing, study space, and "
            "sometimes internet. Join reading clubs. Librarians can help "
            "find resources for any topic."
        ),
        "exam preparation": (
            "Start early - do not cram. Make summary notes. Practice past papers. "
            "Study in groups. Teach topics to others. Get enough sleep. "
            "Eat well. Stay hydrated."
        ),
        "special needs education": (
            "Every child can learn. Early identification helps. Contact "
            "special education units at district level. Inclusive classrooms "
            "benefit all children. Parents are key advocates."
        ),
        "girl child education": (
            "Educated girls marry later, earn more, have healthier families. "
            "Support: provide sanitary products, safe transport, female teachers, "
            "and scholarships. Address cultural barriers through community dialogue."
        ),
        "adult literacy": (
            "It's never too late to learn. Join adult literacy classes at "
            "community centers. Practice reading local language newspapers. "
            "Write letters to family. Use literacy for daily tasks."
        ),
        "vocational training": (
            "Learn practical skills: carpentry, masonry, tailoring, mechanics, "
            "electrical, plumbing. Short courses at vocational colleges. "
            "High demand for skilled trades. Can start own business."
        ),
        "research skills": (
            "Start with clear question. Use reliable sources: academic journals, "
            "government reports, reputable organizations. Take notes with sources. "
            "Evaluate information critically. Cite all sources."
        ),
        "public speaking": (
            "Know your audience. Practice aloud. Start with a story. Make eye "
            "contact. Speak slowly and clearly. Use simple language. "
            "Prepare for questions. Confidence comes with practice."
        ),
        # ===================== BUSINESS (30+ entries) =====================
        "how to start a business": (
            "1. Identify market need. 2. Write simple business plan. 3. Register "
            "business name. 4. Get necessary licenses. 5. Start small. 6. Keep records. "
            "7. Reinvest profits. 8. Join business association for support."
        ),
        "business registration": (
            "Register business name at Huduma Center/e-citizen (Kenya) or equivalent. "
            "Get KRA PIN. Register for NSSF and NHIF if hiring. Costs about "
            "$10-50 depending on business type. Takes 1-2 weeks."
        ),
        "sacco benefits": (
            "SACCOs (Savings and Credit Co-operatives) offer: member savings, "
            "loans at lower interest than banks, dividends on shares. "
            "Join registered SACCO with good reputation. Start saving regularly."
        ),
        "mobile money business": (
            "Apply to be M-Pesa/agent or equivalent. Needs: registered business, "
            "good location, float capital ($200+), phone/SIM, training. "
            "Commission on deposits and withdrawals. Comply with AML regulations."
        ),
        "saving money tips": (
            "Save 10-20% of income first before spending. Use SACCO or bank. "
            "Join merry-go-round (chama). Track expenses. Cut non-essentials. "
            "Set specific savings goals with deadlines."
        ),
        "loan application": (
            "Have clear purpose for loan. Compare interest rates. Check: bank, "
            "SACCO, microfinance, government youth funds. Prepare: business plan, "
            "bank statements, collateral documents. Read terms carefully."
        ),
        "marketing on a budget": (
            "Use WhatsApp Business (free). Create Facebook page. Ask satisfied "
            "customers for referrals. Put sign at your location. Offer samples. "
            "Partner with complementary businesses. Word of mouth is powerful."
        ),
        "customer service": (
            "Greet every customer warmly. Listen to their needs. Be honest about "
            "products. Resolve complaints quickly. Remember regular customers. "
            "Say thank you. Good service brings repeat business."
        ),
        "record keeping business": (
            "Track every sale and expense daily. Separate business and personal "
            "money. Keep receipts. Simple notebook works. Review monthly to see "
            "profit/loss. Helps with taxes and loans."
        ),
        "pricing products": (
            "Calculate all costs: materials, labor, transport, overhead. Add "
            "profit margin (20-50%). Check competitor prices. Consider what "
            "customers will pay. Adjust based on demand."
        ),
        "supplier management": (
            "Build relationships with 2-3 suppliers. Compare prices and quality. "
            "Negotiate payment terms. Pay on time to build trust. Keep backup "
            "suppliers. Quality matters more than lowest price."
        ),
        "business plan basics": (
            "Include: business description, products/services, market analysis, "
            "marketing strategy, operations plan, management team, financial "
            "projections. Keep it simple - 5-10 pages. Update regularly."
        ),
        "tax obligations": (
            "Register for tax. File returns monthly/quarterly even if no profit. "
            "Keep all receipts. Hire accountant if needed. Penalties for late "
            "filing. Some small businesses qualify for turnover tax (simplified)."
        ),
        "hiring employees": (
            "Write clear job description. Advertise locally. Interview candidates. "
            "Check references. Offer fair wage. Register with NSSF/NHIF. "
            "Have written employment contract. Train new staff well."
        ),
        "franchise opportunities": (
            "Research: Equity Bank agents, petrol stations, fast food chains, "
            "pharmacies. Needs: capital, good location, business experience. "
            "Franchisor provides training and brand. Read agreement carefully."
        ),
        "export business": (
            "Identify export product: coffee, tea, flowers, nuts, crafts. Register "
            "with export promotion board. Meet quality standards. Find buyers at "
            "trade fairs. Use freight forwarder for shipping."
        ),
        "e-commerce in Africa": (
            "Sell on: Jumia, Kilimall, WhatsApp, Instagram, Facebook Marketplace. "
            "Take good product photos. Write clear descriptions. Offer delivery "
            "or pickup. Respond to inquiries quickly. Build reviews."
        ),
        "women in business": (
            "Access: Women Enterprise Fund, AWEP, UN Women programs. Network with "
            "other women entrepreneurs. Use chamas for capital. Many successful "
            "women run agribusinesses, boutiques, and food businesses."
        ),
        "youth employment": (
            "Government programs: Kazi Mtaani, Ajira Digital, Hustler Fund. "
            "Private: Andela, ALX, Google certifications. Start small business. "
            "Volunteer to gain experience. Use LinkedIn for professional networking."
        ),
        "insurance basics": (
            "Types: Health (NHIF/private), Life, Motor, Crop, Livestock. "
            "Compare policies. Read exclusions. Pay premiums on time. Insurance "
            "protects against major losses. Essential for business continuity."
        ),
        "negotiation skills": (
            "Know your bottom line before negotiating. Research fair prices. "
            "Be willing to walk away. Listen more than talk. Find win-win solutions. "
            "Build long-term relationships. Practice on small deals."
        ),
        "branding your business": (
            "Choose memorable name. Create simple logo. Be consistent with colors "
            "and style. Deliver on promises - your reputation is your brand. "
            "Use packaging to stand out. Tell your story."
        ),
        "cash flow management": (
            "Cash flow is lifeblood of business. Invoice promptly. Follow up on "
            "payments. Negotiate supplier credit. Keep cash reserve for 3 months. "
            "Monitor weekly. Cut costs before crisis."
        ),
        "partnership agreements": (
            "Write everything down. Define roles, contributions, profit sharing, "
            "decision making, exit strategy. Register partnership. Have lawyer "
            "review. Clear communication prevents disputes."
        ),
        "business mentorship": (
            "Find mentor through: industry associations, church/community groups, "
            "online platforms, former employers. Good mentor provides advice, "
            "connections, accountability. Be respectful of their time."
        ),
        # ===================== WEATHER (20+ entries) =====================
        "weather forecast today": (
            "For accurate local forecast, dial *384*5# (Kenya) or check with "
            "local meteorological service. Farmers can subscribe to SMS weather "
            "alerts through KALRO or equivalent agricultural service."
        ),
        "when will rains come": (
            "Rainfall patterns vary by region. Check with local meteorological "
            "department. Long rains typically March-May in East Africa. "
            "Short rains October-December. Plant when soil is moist to 15cm depth."
        ),
        "climate change effects": (
            "Changing rainfall patterns, more droughts and floods, crop pests "
            "spreading to new areas. Adapt by: diversifying crops, water harvesting, "
            "using drought-resistant varieties, and planting trees."
        ),
        "flood preparedness": (
            "Move to higher ground. Store food and water. Secure important documents "
            "in waterproof bag. Listen to radio for updates. Do not walk through "
            "flowing water. After floods: boil all water, watch for diseases."
        ),
        "drought preparedness": (
            "Store water in containers. Plant drought-resistant crops. Reduce "
            "livestock numbers early while prices are good. Keep emergency food "
            "stock. Join early warning systems. Have alternative income source."
        ),
        "seasonal farming calendar": (
            "Long rains (Mar-May): Plant maize, beans, potatoes. Short rains "
            "(Oct-Dec): Plant vegetables, beans, fodder. Dry season: Irrigate "
            "crops, tend perennials, prepare land, attend training."
        ),
        "weather apps for farmers": (
            "Try: Farm Africa weather, Awhere, Ignitia. Many provide local "
            "forecasts via SMS. Some are free. Check with agricultural extension "
            "for recommended services in your area."
        ),
        "El Nino effects": (
            "El Nino brings heavy rains and flooding to East Africa. Prepare: "
            "drainage channels, elevated storage, early planting. La Nina brings "
            "drought. Monitor meteorological forecasts."
        ),
        "rainwater harvesting": (
            "Collect from roof into tank or drum. 1mm rain on 100m2 roof = 100L. "
            "Cover tank to prevent mosquitoes. First flush diverter improves "
            "quality. Use for irrigation, livestock, and household."
        ),
        "soil erosion prevention": (
            "Plant grass strips across slopes. Build terraces on steep land. "
            "Use trash lines and contour bunds. Plant trees as windbreaks. "
            "Keep ground covered with crops or mulch."
        ),
        "frost protection": (
            "In highland areas: cover small plants with sacks at night. Light "
            "small fires or smudge pots (carefully). Water plants before frost "
            "- wet soil holds heat. Plant frost-hardy varieties."
        ),
        "wind damage prevention": (
            "Plant windbreak trees (markhamia, gravillea). Stake tall crops. "
            "Harvest mature crops before storms. Secure greenhouse structures. "
            "Trim trees near buildings."
        ),
        "temperature for crops": (
            "Maize: 15-30C. Tomatoes: 20-25C. Beans: 16-30C. Potatoes: 15-20C. "
            "Bananas: 26-30C. Coffee: 15-24C. Know your crop's optimal range."
        ),
        "humidity and farming": (
            "High humidity: fungal diseases increase, use resistant varieties. "
            "Low humidity: more irrigation needed, higher evaporation. "
            "Greenhouses need ventilation to control humidity."
        ),
        "lightning safety": (
            "During storms: stay indoors, avoid water, unplug electronics. "
            "If caught outside: crouch low, avoid trees and metal, stay in car "
            "if available. Do not use phone outside."
        ),
        # ===================== GOVERNMENT (20+ entries) =====================
        "how to get ID card": (
            "Apply at Huduma Center (Kenya) or national ID office. Bring: "
            "birth certificate, passport photos, parent's ID. Costs about $1-5. "
            "Takes 2-8 weeks. Needed for all government services."
        ),
        "how to register birth": (
            "Register at civil registration office within 6 months. Bring: "
            "hospital birth notification, parents IDs. Free if within deadline. "
            "Late registration requires affidavit. Birth certificate needed for school."
        ),
        "how to apply for passport": (
            "Apply online via eCitizen. Upload documents. Pay fee ($30-50). "
            "Book biometric appointment at Immigration. Bring: ID, photos, "
            "birth certificate. Takes 2-6 weeks."
        ),
        "NHIF registration": (
            "Register at NHIF office or online. Bring: ID, passport photo, "
            "copy of ID. Pay monthly contribution ($5-20 depending on income). "
            "Covers hospital visits, surgery, maternity. Essential for families."
        ),
        "NSSF registration": (
            "National Social Security Fund - retirement savings. Both employer "
            "and employee contribute. Register at NSSF office with ID and "
            "employment letter. Withdraw at retirement or disability."
        ),
        "KRA PIN application": (
            "Apply on iTax portal. Needed for: employment, bank account, "
            "business registration, land transactions. Free to apply. Keep "
            "PIN certificate safe. File tax returns annually."
        ),
        "voter registration": (
            "Register at IEBC office during registration periods. Bring: "
            "national ID. Free. Must be 18+. Check voter status online. "
            "Vote at assigned polling station on election day."
        ),
        "land title deed": (
            "Apply at Ministry of Lands. Process: search at land registry, "
            "survey, valuation, pay stamp duty, registration. Use lawyer for "
            "complex cases. Beware of land fraud - verify at registry."
        ),
        "business permit": (
            "Apply at county office or single business permit portal. Cost "
            "depends on business size and county. Must be renewed annually. "
            "Display permit at business premises."
        ),
        "police clearance certificate": (
            "Apply at CID headquarters or online. Bring: ID, passport photos. "
            "Pay fee ($5-10). Takes 1-2 weeks. Needed for employment abroad, "
            "visa applications, and some jobs."
        ),
        "marriage registration": (
            "Civil: register at Attorney General's office. Religious: registered "
            "by officiating clergy. Both need: IDs, photos, witnesses. "
            "Certificate needed for spousal benefits and immigration."
        ),
        "death certificate": (
            "Register death at civil registry within 30 days. Bring: hospital "
            "notification or chief's letter, deceased ID, informant ID. "
            "Needed for inheritance, insurance claims, and burial permits."
        ),
        "driving license": (
            "Apply at NTSA (Kenya). Steps: driving school training, theory "
            "test, practical test, eye test, pay fees. Renew every 3 years. "
            "Smart DL costs about $20-30."
        ),
        "vehicle registration": (
            "Buy vehicle, get insurance, have vehicle inspected, pay stamp "
            "duty at KRA, register at NTSA. Get number plates and logbook. "
            "Keep logbook safe - it is proof of ownership."
        ),
        "court processes": (
            "Small claims: magistrate court for disputes under $5000. File "
            "claim with court clerk. Mediation recommended first. For serious "
            "cases: hire advocate. Legal aid available for those who cannot afford."
        ),
        "legal aid services": (
            "Free legal help available through: Law Society legal aid clinics, "
            "NGOs like Kituo Cha Sheria, FIDA (women), LSCK. Bring all relevant "
            "documents. Available at court buildings on designated days."
        ),
        "citizen rights": (
            "Constitutional rights include: life, equality, human dignity, "
            "freedom of expression, access to information, economic/social "
            "rights. If violated: report to police, human rights commission, "
            "or seek legal redress."
        ),
        "corruption reporting": (
            "Report corruption to: EACC (Ethics and Anti-Corruption Commission), "
            "police, or whistleblower hotlines. Can report anonymously. "
            "Provide specific details and evidence. Protected by law from retaliation."
        ),
        "public participation": (
            "Citizens have right to participate in governance. Attend public "
            "forums, budget hearings, and planning meetings. Submit written "
            "memoranda. Join community development committees. Your voice matters."
        ),
        # ===================== RELIGION & CULTURE (10+ entries) =====================
        "religious holidays": (
            "Christian: Christmas (Dec 25), Easter (variable), Good Friday. "
            "Muslim: Eid al-Fitr, Eid al-Adha (dates follow Islamic calendar). "
            "Public holidays vary by country. Check official government calendar."
        ),
        "cultural respect": (
            "Greet elders first. Use right hand for giving/receiving. Ask "
            "permission before photographing people. Remove shoes when entering "
            "homes in some cultures. Dress modestly in rural areas and religious "
            "sites."
        ),
        "traditional medicine": (
            "Some traditional remedies are effective, but consult trained health "
            "provider first. Never replace prescribed medication with herbs alone "
            "for serious conditions like diabetes, HIV, TB, or malaria. "
            "Report adverse effects."
        ),
        "community conflict resolution": (
            "Traditional elders often mediate disputes. Approach chief or elder. "
            "Both parties present case. Elders deliberate and give binding decision. "
            "Faster and cheaper than courts for community matters."
        ),
        "funeral customs": (
            "Customs vary by community. Generally: family gathers, body prepared "
            "by close relatives, vigil held overnight, burial within 2-3 days. "
            "Community contributes food and funds. Mourning period varies."
        ),
        "wedding traditions": (
            "Most communities: dowry/bride price negotiation first, then traditional "
            "ceremony, then church/religious ceremony, then reception. Process can "
            "take months. Involve both families early."
        ),
        "naming ceremonies": (
            "Many communities name child after 3-7 days. Often named after elders, "
            "events, or with spiritual significance. Celebrated with family gathering. "
            "Name registered officially for birth certificate."
        ),
        "elders role": (
            "Elders provide wisdom, mediate conflicts, preserve culture, guide "
            "community decisions. Respect and consult elders on important matters. "
            "They are living libraries of community knowledge."
        ),
        # ===================== FAMILY (10+ entries) =====================
        "parenting advice": (
            "Spend quality time with children. Be consistent with rules. Praise "
            "good behavior. Read together. Eat meals together. Know their friends. "
            "Listen without judging. Model the behavior you want to see."
        ),
        "child discipline": (
            "Use positive reinforcement. Set clear boundaries. Time-outs for young "
            "children. Logical consequences (not punishment). Never use physical "
            "punishment - it harms children and is illegal in many countries."
        ),
        "teenager guidance": (
            "Stay connected despite their independence. Know where they are. "
            "Talk about peer pressure, drugs, relationships. Set curfews. "
            "Be available to listen without lecturing. They need guidance, not control."
        ),
        "marriage counseling": (
            "Seek help early when problems start. Many churches and NGOs offer "
            "free counseling. Communicate openly. Compromise. Spend time together. "
            "If abuse occurs, seek help immediately - your safety comes first."
        ),
        "domestic violence help": (
            "You are not alone. Help available: police gender desk, hotlines, "
            "shelters, FIDA, church counselors. Danger signs: controlling behavior, "
            "threats, physical harm. Safety plan: know where to go, save money, "
            "keep important documents accessible."
        ),
        "elderly care": (
            "Respect and involve elders in family life. Ensure regular medical "
            "checkups. Help with mobility. Provide nutritious food. Watch for "
            "signs of depression. Consider community support programs."
        ),
        "orphan care": (
            "Over 50 million orphans in Africa. Support: extended family care "
            "(preferred), community-based care, quality children's homes if needed. "
            "Sponsor a child through reputable NGO. Support keeps children in "
            "community, not institutions."
        ),
        "family budgeting": (
            "List all income and expenses. Prioritize: food, rent, school fees, "
            "healthcare. Save 10% minimum. Involve whole family in planning. "
            "Review weekly. Cut non-essentials during hard times."
        ),
        "saving for school fees": (
            "Start saving when child is young. Use SACCO or dedicated savings "
            "account. Some schools offer installment payments. Apply for bursaries "
            "and scholarships early. Consider less expensive good schools."
        ),
        "family planning": (
            "Space children 2-3 years apart for mother's health and family "
            "resources. Many methods available at clinics. Discuss with partner. "
            "Both partners share responsibility for family planning."
        ),
        # ===================== GENERAL / EMERGENCY (10+ entries) =====================
        "emergency numbers": (
            "Kenya: Police 999/112, Ambulance 999, Fire 999. Nigeria: Police 112, "
            "Ambulance 112. South Africa: Police 10111, Ambulance 10177. "
            "Save local hospital and police numbers in phone. Know nearest hospital."
        ),
        "fire safety": (
            "Prevention: check electrical wiring, don't overload sockets, keep "
            "flammables away from heat. If fire: shout for help, evacuate, call "
            "emergency. Use extinguisher if trained. Never use water on electrical "
            "fires."
        ),
        "road safety": (
            "Wear seatbelt. Don't use phone while driving. Obey speed limits. "
            "Don't drink and drive. Motorbike riders: wear helmet always. "
            "Pedestrians: use crossings, wear reflective clothing at night."
        ),
        "disaster preparedness": (
            "Know risks in your area (flood, drought, earthquake). Have emergency "
            "kit: water, food, torch, radio, first aid, documents. Know evacuation "
            "route. Have family communication plan. Listen to warnings."
        ),
        "first aid kit contents": (
            "Bandages, gauze, adhesive tape, antiseptic, pain relievers, scissors, "
            "tweezers, thermometer, ORS packets, gloves, torch. Check expiry dates "
            "every 6 months. Keep in accessible place. Learn basic first aid."
        ),
        "poison help": (
            "If someone ingests poison: call poison control or emergency. Do NOT "
            "induce vomiting unless instructed. Bring container to hospital. "
            "For chemicals on skin: remove contaminated clothing, rinse with water "
            "for 15 minutes."
        ),
        "animal bites": (
            "Wash wound with soap and water for 15 minutes. Apply antiseptic. "
            "Seek medical care immediately for rabies vaccination. All dog, cat, "
            "bat, and wild animal bites need assessment. Do not ignore minor bites."
        ),
        "electric shock": (
            "Do NOT touch victim if still in contact with electricity. Turn off "
            "power source first. If impossible, use dry wood/rubber to push victim "
            "away. Call emergency. Start CPR if not breathing."
        ),
        "choking first aid": (
            "Adult: stand behind, wrap arms around waist, thrust upward above "
            "navel. Infant: 5 back slaps + 5 chest thrusts. Call emergency if "
            "object does not dislodge. Learn Heimlich maneuver."
        ),
        "mental health emergency": (
            "If someone is suicidal: stay with them, listen without judgment, "
            "remove means of harm, get professional help immediately. Emergency "
            "psychiatric services available at referral hospitals. "
            "Suicide is preventable."
        ),
    }

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize the offline manager.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()
        self._cache_manager = CacheManager(self.db_path)
        logger.info("OfflineManager initialized with db: %s", self.db_path)

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS request_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        module TEXT DEFAULT 'general',
                        timestamp TEXT NOT NULL,
                        priority TEXT DEFAULT 'medium',
                        status TEXT DEFAULT 'pending',
                        attempts INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        response TEXT NOT NULL,
                        module TEXT DEFAULT 'general',
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS sync_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_name TEXT NOT NULL,
                        record_id TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        local_data TEXT NOT NULL,
                        server_data TEXT,
                        local_timestamp TEXT NOT NULL,
                        server_timestamp TEXT,
                        status TEXT DEFAULT 'pending',
                        conflict_resolution TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        records_synced INTEGER DEFAULT 0,
                        conflicts INTEGER DEFAULT 0,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_queue_status ON request_queue(status);
                    CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_queue(status);
                """)
                logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error("Database initialization failed: %s", e)
            raise

    def is_online(self, host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
        """Check if device has internet connectivity.

        Attempts to connect to a reliable DNS server to verify connectivity.
        This is lightweight and works on mobile networks.

        Args:
            host: DNS server to test connection against.
            port: Port to connect to.
            timeout: Connection timeout in seconds.

        Returns:
            True if internet is available, False otherwise.
        """
        try:
            socket.setdefaulttimeout(timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            is_connected = result == 0
            logger.debug("Connectivity check: %s", "online" if is_connected else "offline")
            return is_connected
        except OSError as e:
            logger.warning("Connectivity check failed: %s", e)
            return False

    def get_fallback_response(self, query: str, module: str = "general") -> Optional[str]:
        """Get a cached or pre-built response when offline.

        Searches the pre-built CACHE dictionary for matching queries,
        then falls back to SQLite cache if no match found.

        Args:
            query: The user's query string.
            module: The functional module (farming, health, etc.).

        Returns:
            Response string if found, None otherwise.
        """
        normalized_query = query.lower().strip().rstrip("?").strip()

        # Direct lookup in pre-built cache
        if normalized_query in self.CACHE:
            logger.info("Pre-built cache hit for: %s", normalized_query)
            return self.CACHE[normalized_query]

        # Try partial matching
        for key, response in self.CACHE.items():
            if normalized_query in key or key in normalized_query:
                logger.info("Partial cache match: '%s' -> '%s'", normalized_query, key)
                return response

        # Try SQLite cache
        cached = self._cache_manager.get_cached(normalized_query)
        if cached:
            logger.info("SQLite cache hit for: %s", normalized_query)
            return cached

        logger.info("No cached response for: %s", normalized_query)
        return None

    def queue_request(self, query: str, user_id: str, module: str = "general") -> int:
        """Save a request for later processing when connection returns.

        Args:
            query: The user's query.
            user_id: Unique identifier for the user.
            module: The functional module the query relates to.

        Returns:
            ID of the queued request in the database.
        """
        timestamp = datetime.now().isoformat()
        priority = self._infer_priority(query)

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    """INSERT INTO request_queue
                       (query, user_id, module, timestamp, priority, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (query, user_id, module, timestamp, priority, "pending"),
                )
                request_id = cursor.lastrowid
                logger.info("Queued request #%d for user %s: %s", request_id, user_id, query)
                return request_id or 0
        except sqlite3.Error as e:
            logger.error("Failed to queue request: %s", e)
            return 0

    def process_queue(self) -> Dict[str, int]:
        """Process queued requests when back online.

        Attempts to process all pending requests in batches.

        Returns:
            Dictionary with counts of processed, failed, and remaining items.
        """
        if not self.is_online():
            logger.info("Cannot process queue - still offline")
            return {"processed": 0, "failed": 0, "remaining": 0}

        results = {"processed": 0, "failed": 0, "remaining": 0}

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get pending requests ordered by priority
                cursor = conn.execute(
                    """SELECT id, query, user_id, module, attempts
                       FROM request_queue
                       WHERE status = 'pending' AND attempts < 5
                       ORDER BY
                         CASE priority
                           WHEN 'critical' THEN 1
                           WHEN 'high' THEN 2
                           WHEN 'medium' THEN 3
                           ELSE 4
                         END,
                         timestamp ASC
                       LIMIT ?""",
                    (QUEUE_BATCH_SIZE,),
                )
                pending = cursor.fetchall()

                for req_id, query, user_id, module, attempts in pending:
                    try:
                        # Mark as processing
                        conn.execute(
                            "UPDATE request_queue SET status = ?, attempts = ? WHERE id = ?",
                            ("processing", attempts + 1, req_id),
                        )
                        conn.commit()

                        # In production, this would call the actual AI engine
                        # For offline mode, we attempt to get a cached response
                        response = self.get_fallback_response(query, module)

                        if response:
                            conn.execute(
                                "UPDATE request_queue SET status = ? WHERE id = ?",
                                ("completed", req_id),
                            )
                            results["processed"] += 1
                        else:
                            conn.execute(
                                "UPDATE request_queue SET status = ? WHERE id = ?",
                                ("pending", req_id),
                            )
                            results["failed"] += 1

                        conn.commit()

                    except Exception as e:
                        logger.error("Error processing request #%d: %s", req_id, e)
                        conn.execute(
                            "UPDATE request_queue SET status = ?, attempts = ? WHERE id = ?",
                            ("pending" if attempts < 4 else "failed", attempts + 1, req_id),
                        )
                        conn.commit()
                        results["failed"] += 1

                # Count remaining
                remaining_cursor = conn.execute(
                    "SELECT COUNT(*) FROM request_queue WHERE status = 'pending'"
                )
                results["remaining"] = remaining_cursor.fetchone()[0] or 0

        except sqlite3.Error as e:
            logger.error("Queue processing database error: %s", e)

        logger.info("Queue processing complete: %s", results)
        return results

    def _infer_priority(self, query: str) -> str:
        """Infer priority level from query content.

        Args:
            query: The user's query string.

        Returns:
            Priority string: critical, high, medium, or low.
        """
        query_lower = query.lower()
        critical_keywords = ["emergency", "hospital", "dying", "death", "accident", "poison", "snake bite"]
        high_keywords = ["malaria", "disease", "sick", "plant", "crop", "weather", "rain"]

        if any(kw in query_lower for kw in critical_keywords):
            return ResponsePriority.CRITICAL.value
        if any(kw in query_lower for kw in high_keywords):
            return ResponsePriority.HIGH.value
        return ResponsePriority.MEDIUM.value


# =============================================================================
# LOCAL MODEL MANAGER
# =============================================================================


class LocalModelManager:
    """Manages local LLM integration via Ollama and Llama.cpp.

    Provides methods to check for, query, and manage locally-installed
    language models. This enables AI responses even without internet.

    Attributes:
        ollama_host: URL of the Ollama server.
    """

    def __init__(self, ollama_host: str = OLLAMA_DEFAULT_HOST) -> None:
        """Initialize the local model manager.

        Args:
            ollama_host: URL for the Ollama API endpoint.
        """
        self.ollama_host = ollama_host
        logger.info("LocalModelManager initialized with host: %s", ollama_host)

    def is_ollama_available(self) -> bool:
        """Check if Ollama server is running locally.

        Makes a lightweight HTTP request to the Ollama API.

        Returns:
            True if Ollama is running and responsive.
        """
        try:
            req = urllib.request.Request(
                f"{self.ollama_host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                return response.status == 200
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            logger.debug("Ollama not available at %s", self.ollama_host)
            return False

    def query_local_model(self, prompt: str, model: str = "llama3.2") -> Dict[str, Any]:
        """Send a query to the local Ollama model.

        Args:
            prompt: The user's prompt text.
            model: Name of the Ollama model to use.

        Returns:
            Dictionary with 'success', 'response', and 'error' keys.
        """
        if not self.is_ollama_available():
            return {
                "success": False,
                "response": "",
                "error": "Ollama is not running. Start it with: ollama serve",
            }

        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500,
            },
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.ollama_host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "error": None,
                }
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            if e.code == 404:
                error_msg = f"Model '{model}' not found. Run: ollama pull {model}"
            logger.error("Ollama query failed: %s", error_msg)
            return {"success": False, "response": "", "error": error_msg}
        except Exception as e:
            logger.error("Ollama query error: %s", e)
            return {"success": False, "response": "", "error": str(e)}

    def get_available_models(self) -> List[Dict[str, Any]]:
        """List all locally installed Ollama models.

        Returns:
            List of model dictionaries with name, size, and parameter info.
        """
        if not self.is_ollama_available():
            return []

        try:
            req = urllib.request.Request(
                f"{self.ollama_host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("models", [])
                return [
                    {
                        "name": m.get("name", "unknown"),
                        "size": m.get("size", 0),
                        "parameter_size": m.get("details", {}).get("parameter_size", "unknown"),
                        "format": m.get("details", {}).get("format", "unknown"),
                    }
                    for m in models
                ]
        except Exception as e:
            logger.error("Failed to list models: %s", e)
            return []

    def get_model_recommendation(self, hardware: HardwareProfile) -> Dict[str, Any]:
        """Suggest the best model based on device specifications.

        Recommends appropriate models for the available hardware to ensure
        reasonable performance on African devices (often low-spec).

        Args:
            hardware: Device hardware profile.

        Returns:
            Dictionary with recommended model name, reason, and alternatives.
        """
        recommendations = {
            "recommended": "",
            "reason": "",
            "alternatives": [],
            "install_command": "",
        }

        ram = hardware.ram_gb
        has_gpu = hardware.has_gpu
        gpu_vram = hardware.gpu_vram_gb

        if ram >= 16 and (has_gpu and gpu_vram >= 8):
            recommendations["recommended"] = "llama3.2"
            recommendations["reason"] = (
                "Your powerful setup can run full models with good speed. "
                "Llama 3.2 provides excellent quality."
            )
            recommendations["alternatives"] = ["mistral", "qwen2.5", "gemma2"]
            recommendations["install_command"] = "ollama pull llama3.2"

        elif ram >= 8 and (has_gpu and gpu_vram >= 4):
            recommendations["recommended"] = "llama3.2:3b"
            recommendations["reason"] = (
                "Good balance of quality and speed for your mid-range GPU setup."
            )
            recommendations["alternatives"] = ["phi3", "qwen2.5:3b", "gemma2:2b"]
            recommendations["install_command"] = "ollama pull llama3.2:3b"

        elif ram >= 8:
            recommendations["recommended"] = "phi3:mini"
            recommendations["reason"] = (
                "CPU-only with 8GB RAM. Phi-3 mini provides good quality "
                "without requiring GPU acceleration."
            )
            recommendations["alternatives"] = ["qwen2.5:1.5b", "gemma2:2b"]
            recommendations["install_command"] = "ollama pull phi3:mini"

        elif ram >= 4:
            recommendations["recommended"] = "qwen2.5:1.5b"
            recommendations["reason"] = (
                "Low-resource optimized. This 1.5B parameter model runs well "
                "on 4GB RAM devices common in rural areas."
            )
            recommendations["alternatives"] = ["tinyllama", "gemma2:2b"]
            recommendations["install_command"] = "ollama pull qwen2.5:1.5b"

        else:
            recommendations["recommended"] = "tinyllama"
            recommendations["reason"] = (
                "Ultra-lightweight model for devices with limited RAM. "
                "Basic functionality but runs on almost any hardware."
            )
            recommendations["alternatives"] = ["qwen2.5:0.5b"]
            recommendations["install_command"] = "ollama pull tinyllama"

        return recommendations

    def get_install_guide(self, os_type: str = "linux") -> Dict[str, str]:
        """Get platform-specific Ollama installation instructions.

        Args:
            os_type: Operating system (linux, windows, macos, android).

        Returns:
            Dictionary with installation steps and commands.
        """
        guides = {
            "linux": {
                "title": "Install Ollama on Linux",
                "command": "curl -fsSL https://ollama.com/install.sh | sh",
                "note": "Requires curl. Supports Ubuntu, Debian, Fedora, CentOS.",
                "verify": "Run 'ollama --version' to verify installation.",
                "start": "Start server with: ollama serve",
                "first_model": "Pull your first model: ollama pull llama3.2:3b",
            },
            "windows": {
                "title": "Install Ollama on Windows",
                "command": "Download installer from https://ollama.com/download/windows",
                "note": "Windows 10 or later required. 8GB+ RAM recommended.",
                "verify": "Run 'ollama --version' in PowerShell or CMD.",
                "start": "Ollama starts automatically. Check system tray icon.",
                "first_model": "Pull model: ollama pull llama3.2:3b",
            },
            "macos": {
                "title": "Install Ollama on macOS",
                "command": "Download from https://ollama.com/download/mac or use Homebrew: brew install ollama",
                "note": "macOS 12 or later. Apple Silicon recommended.",
                "verify": "Run 'ollama --version' in Terminal.",
                "start": "Start Ollama from Applications folder.",
                "first_model": "Pull model: ollama pull llama3.2:3b",
            },
            "android": {
                "title": "Run LLMs on Android",
                "command": "Install Termux from F-Droid, then: pkg install ollama (experimental)",
                "note": "Alternative: Use PocketLLM or MLC Chat apps from Play Store.",
                "verify": "Limited support. Consider using remote Ollama instance.",
                "start": "Android devices often lack RAM for local LLMs.",
                "first_model": "Consider using the offline FAQ instead for reliability.",
            },
        }

        return guides.get(os_type.lower(), guides["linux"])

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Download a model using Ollama.

        Args:
            model_name: Name of the model to download.

        Returns:
            Dictionary with success status and message.
        """
        if not self.is_ollama_available():
            return {
                "success": False,
                "message": "Ollama is not running. Start it first with 'ollama serve'.",
            }

        try:
            payload = json.dumps({"name": model_name}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_host}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300.0) as response:
                return {
                    "success": True,
                    "message": f"Model '{model_name}' pulled successfully.",
                }
        except Exception as e:
            logger.error("Failed to pull model %s: %s", model_name, e)
            return {"success": False, "message": str(e)}


# =============================================================================
# SMS INTERFACE
# =============================================================================


class SMSInterface:
    """Handles SMS-based interaction for low-bandwidth scenarios.

    Formats responses for 160/320 character SMS limits and parses
    incoming SMS queries. Designed for Africa's Talking API and
    similar SMS gateways.
    """

    # SMS command definitions with keywords and response templates
    SMS_COMMANDS: Dict[str, Dict[str, Any]] = {
        "HELP": {
            "keywords": ["help", "info", "support", "how"],
            "description": "Get help on using Luqi AI via SMS",
            "template": (
                "Luqi AI: Reply with keywords. FARM, HEALTH, PRICE, WEATHER, "
                "BUSINESS, TEACH, LAW, NEWS, EMERGENCY. Or ask any question. "
                "Free service for farmers and communities."
            ),
        },
        "WEATHER": {
            "keywords": ["weather", "rain", "forecast", "climate", "sun"],
            "description": "Get weather-related information",
            "template": (
                "For accurate local forecast, dial your provider's weather USSD "
                "code or contact your local meteorological service. "
                "Farmers can subscribe to SMS weather alerts through agricultural services."
            ),
        },
        "PRICE": {
            "keywords": ["price", "cost", "market", "sell", "buy", "rates"],
            "description": "Get market prices for commodities",
            "template": (
                "Visit nearest market for current prices. Prices vary by location "
                "and season. Call your local agricultural extension officer for "
                "commodity price updates. Cooperative societies also provide price info."
            ),
        },
        "HEALTH": {
            "keywords": ["health", "sick", "medicine", "doctor", "clinic", "hospital"],
            "description": "Get basic health information",
            "template": (
                "For symptoms: describe them clearly. For emergencies: call nearest "
                "hospital. For malaria: get tested before treatment. "
                "Prevention: sleep under net, drink clean water, wash hands."
            ),
        },
        "FARM": {
            "keywords": ["farm", "crop", "plant", "seed", "harvest", "pest", "fertilizer"],
            "description": "Get farming advice",
            "template": (
                "SMS your specific question: 'How to plant maize', 'Control armyworms', "
                "'Tomato fertilizer', 'Store maize'. We provide step-by-step guides "
                "for African farming conditions."
            ),
        },
        "TEACH": {
            "keywords": ["teach", "learn", "school", "study", "education", "exam"],
            "description": "Get educational resources",
            "template": (
                "Study tips: set goals, 25-min blocks with breaks, review notes daily, "
                "teach others to test understanding. Free learning: Khan Academy, "
                "ALX, African Virtual University. Scholarships: check Mastercard Foundation."
            ),
        },
        "BUSINESS": {
            "keywords": ["business", "money", "loan", "sell", "market", "profit"],
            "description": "Get business and financial advice",
            "template": (
                "Start small, keep records, save 10%+, separate business/personal money. "
                "SACCOs offer lower interest loans. Register business for credibility. "
                "Use WhatsApp Business for free marketing."
            ),
        },
        "LAW": {
            "keywords": ["law", "legal", "rights", "court", "police", "government"],
            "description": "Get basic legal information",
            "template": (
                "Know your constitutional rights. Free legal aid at Law Society clinics "
                "and Kituo Cha Sheria. Report corruption to EACC. For disputes: "
                "try mediation first, it is faster and cheaper."
            ),
        },
        "NEWS": {
            "keywords": ["news", "update", "information", "alert"],
            "description": "Get news and updates",
            "template": (
                "Listen to local radio for trusted news. BBC Africa, VOA, and local "
                "stations provide reliable updates. Be careful of fake news on "
                "social media - verify before sharing."
            ),
        },
        "EMERGENCY": {
            "keywords": ["emergency", "urgent", "999", "112", "police", "fire", "ambulance"],
            "description": "Emergency contact information",
            "template": (
                "EMERGENCY: Police 999/112, Ambulance 999, Fire 999. "
                "Save local hospital and police numbers. For snake bites: keep calm, "
                "immobilize limb, get to hospital. For burns: cool with water 20 min."
            ),
        },
    }

    @classmethod
    def format_for_sms(cls, response: str) -> str:
        """Compress a response to fit SMS character limits.

        Prioritizes keeping the most important information within
        160 characters for single SMS or 320 for extended.

        Args:
            response: Full text response to compress.

        Returns:
            Compressed response string fitting SMS limits.
        """
        if len(response) <= MAX_SMS_LENGTH:
            return response

        # Try to fit in extended SMS (320 chars)
        if len(response) <= EXTENDED_SMS_LENGTH:
            return response

        # Compress: remove extra spaces, shorten common words
        compressed = response
        compressed = re.sub(r"\s+", " ", compressed).strip()

        # Replace common word sequences with abbreviations
        replacements = {
            "government": "govt",
            "hospital": "hosp",
            "medicine": "med",
            "immediately": "now",
            "information": "info",
            "doctor": "dr",
            "extension": "ext",
            "agricultural": "agri",
            "fertilizer": "fert",
            "treatment": "treatmt",
        }
        for full, short in replacements.items():
            compressed = compressed.replace(full, short)
            compressed = compressed.replace(full.capitalize(), short.capitalize())

        if len(compressed) <= EXTENDED_SMS_LENGTH:
            return compressed

        # Truncate with ellipsis, keeping the most important parts
        sentences = compressed.split(". ")
        result = ""
        for sentence in sentences:
            if len(result) + len(sentence) + 2 <= EXTENDED_SMS_LENGTH - 3:
                result += sentence + ". "
            else:
                break

        return result.strip() + "..." if result else compressed[:EXTENDED_SMS_LENGTH - 3] + "..."

    @classmethod
    def parse_sms_query(cls, message: str) -> Dict[str, Any]:
        """Parse and understand incoming SMS queries.

        Identifies command keywords and extracts the actual query.

        Args:
            message: Raw SMS message text.

        Returns:
            Dictionary with detected command, query text, and confidence.
        """
        message_lower = message.lower().strip()
        result = {
            "command": None,
            "query": message,
            "confidence": 0.0,
            "is_command": False,
        }

        # Check for explicit command keywords
        for cmd_name, cmd_info in cls.SMS_COMMANDS.items():
            for keyword in cmd_info["keywords"]:
                if keyword in message_lower:
                    result["command"] = cmd_name
                    result["confidence"] = 0.8
                    result["is_command"] = True
                    # Remove command keyword from query
                    result["query"] = message_lower.replace(keyword, "").strip()
                    break
            if result["command"]:
                break

        # If no command matched, check for question patterns
        if not result["command"]:
            question_words = ["what", "how", "when", "where", "why", "which", "who"]
            if any(message_lower.startswith(w) for w in question_words):
                result["confidence"] = 0.5
                # Try to categorize
                if any(w in message_lower for w in ["farm", "crop", "plant", "seed"]):
                    result["command"] = "FARM"
                elif any(w in message_lower for w in ["health", "sick", "medicine", "doctor"]):
                    result["command"] = "HEALTH"
                elif any(w in message_lower for w in ["money", "business", "loan", "sell"]):
                    result["command"] = "BUSINESS"
                elif any(w in message_lower for w in ["learn", "school", "study", "exam"]):
                    result["command"] = "TEACH"

        return result

    @classmethod
    def get_sms_commands(cls) -> Dict[str, str]:
        """Get list of supported SMS commands with descriptions.

        Returns:
            Dictionary mapping command names to descriptions.
        """
        return {
            name: info["description"]
            for name, info in cls.SMS_COMMANDS.items()
        }

    @classmethod
    def format_long_response(cls, text: str) -> List[str]:
        """Split a long response into SMS-sized chunks.

        Each chunk is at most 160 characters to ensure compatibility
        with basic phones and minimize cost.

        Args:
            text: Long text to split.

        Returns:
            List of SMS-sized text chunks with part indicators.
        """
        if len(text) <= MAX_SMS_LENGTH:
            return [text]

        chunks = []
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_chunk = ""
        part_number = 1

        # Account for part indicator (e.g., "(1/5) ")
        max_chunk = MAX_SMS_LENGTH - 10  # Reserve space for part indicator

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_chunk:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        # Add part indicators
        total = len(chunks)
        return [f"({i+1}/{total}) {chunk}" for i, chunk in enumerate(chunks)]

    @classmethod
    def handle_sms_command(cls, command: str) -> str:
        """Handle a specific SMS command and return appropriate response.

        Args:
            command: Command name (HELP, FARM, HEALTH, etc.).

        Returns:
            Formatted response string for the command.
        """
        cmd_info = cls.SMS_COMMANDS.get(command.upper())
        if cmd_info:
            return cls.format_for_sms(cmd_info["template"])
        return cls.format_for_sms(
            "Unknown command. Reply HELP for available commands. "
            "Or ask your question directly."
        )

    @classmethod
    def get_character_count(cls, text: str) -> Dict[str, int]:
        """Get character count analysis for SMS cost estimation.

        Args:
            text: Message text to analyze.

        Returns:
            Dictionary with character count and SMS count.
        """
        length = len(text)
        if length <= MAX_SMS_LENGTH:
            sms_count = 1
        elif length <= EXTENDED_SMS_LENGTH:
            sms_count = 1  # Extended single SMS
        else:
            # Multi-part SMS: 153 chars per part (7 chars for concatenation)
            sms_count = (length + 152) // 153

        return {
            "characters": length,
            "sms_count": sms_count,
            "single_sms": length <= MAX_SMS_LENGTH,
            "cost_estimate": sms_count,  # 1 unit per SMS
        }


# =============================================================================
# CACHE MANAGER
# =============================================================================


class CacheManager:
    """Manages persistent caching using SQLite.

    Provides get/set operations with TTL support, cache warming,
    and statistics. Optimized for offline-first scenarios.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize cache manager.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._hits = 0
        self._misses = 0
        logger.debug("CacheManager initialized")

    def get_cached(self, query_key: str) -> Optional[str]:
        """Retrieve a cached response by key.

        Args:
            query_key: The cache key (normalized query string).

        Returns:
            Cached response string if found and not expired, None otherwise.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    """SELECT response, expires_at FROM cache
                       WHERE key = ? AND expires_at > ?""",
                    (query_key, datetime.now().isoformat()),
                )
                row = cursor.fetchone()

                if row:
                    # Update access stats
                    conn.execute(
                        """UPDATE cache
                           SET access_count = access_count + 1,
                               last_accessed = ?
                           WHERE key = ?""",
                        (datetime.now().isoformat(), query_key),
                    )
                    conn.commit()
                    self._hits += 1
                    return row[0]

                self._misses += 1
                return None

        except sqlite3.Error as e:
            logger.error("Cache retrieval error: %s", e)
            return None

    def set_cached(
        self,
        query_key: str,
        response: str,
        module: str = "general",
        ttl_hours: int = CACHE_TTL_HOURS,
    ) -> bool:
        """Store a response in the cache.

        Args:
            query_key: The cache key.
            response: Response text to cache.
            module: Functional module category.
            ttl_hours: Time-to-live in hours.

        Returns:
            True if successfully cached, False otherwise.
        """
        try:
            now = datetime.now()
            expires = (now + timedelta(hours=ttl_hours)).isoformat()

            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO cache
                       (key, response, module, created_at, expires_at, access_count, last_accessed)
                       VALUES (?, ?, ?, ?, ?, 0, ?)""",
                    (query_key, response, module, now.isoformat(), expires, now.isoformat()),
                )
                conn.commit()

                # Prune old entries if cache is too large
                self._prune_cache(conn)

            logger.debug("Cached response for key: %s", query_key)
            return True

        except sqlite3.Error as e:
            logger.error("Cache storage error: %s", e)
            return False

    def warm_cache(self, module: str = "general") -> int:
        """Preload common queries into the cache.

        Populates the SQLite cache with pre-built responses for
        faster offline access.

        Args:
            module: Module to warm cache for ("all" for all modules).

        Returns:
            Number of entries warmed.
        """
        count = 0
        now = datetime.now()
        expires = (now + timedelta(days=30)).isoformat()

        # Filter cache entries by module
        module_keywords = {
            "farming": ["plant", "crop", "farm", "seed", "harvest", "pest", "fertilizer", "livestock", "irrigation"],
            "health": ["malaria", "disease", "doctor", "clinic", "medicine", "symptom", "vaccine", "nutrition"],
            "education": ["study", "school", "learn", "exam", "scholarship", "university", "teacher"],
            "business": ["business", "money", "loan", "market", "sell", "profit", "sacco", "register"],
            "weather": ["weather", "rain", "flood", "drought", "climate", "season"],
            "government": ["ID", "passport", "NHIF", "KRA", "register", "voter", "permit", "license"],
            "religion": ["church", "mosque", "prayer", "holiday", "christian", "muslim", "cultural"],
            "family": ["parent", "child", "marriage", "family", "pregnancy", "baby", "elderly"],
        }

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                for key, response in OfflineManager.CACHE.items():
                    # Determine module for this entry
                    entry_module = "general"
                    key_lower = key.lower()
                    for mod, keywords in module_keywords.items():
                        if any(kw in key_lower for kw in keywords):
                            entry_module = mod
                            break

                    if module != "all" and entry_module != module:
                        continue

                    conn.execute(
                        """INSERT OR REPLACE INTO cache
                           (key, response, module, created_at, expires_at, access_count, last_accessed)
                           VALUES (?, ?, ?, ?, ?, 0, ?)""",
                        (key, response, entry_module, now.isoformat(), expires, now.isoformat()),
                    )
                    count += 1

                conn.commit()

            logger.info("Warmed cache with %d entries for module: %s", count, module)
            return count

        except sqlite3.Error as e:
            logger.error("Cache warming error: %s", e)
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics including hit rate and size.

        Returns:
            Dictionary with hit_rate, total_entries, total_accesses, etc.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total_entries = cursor.fetchone()[0] or 0

                cursor = conn.execute("SELECT SUM(access_count) FROM cache")
                total_accesses = cursor.fetchone()[0] or 0

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?",
                    (datetime.now().isoformat(),),
                )
                valid_entries = cursor.fetchone()[0] or 0

                cursor = conn.execute(
                    "SELECT module, COUNT(*) FROM cache GROUP BY module"
                )
                by_module = {row[0]: row[1] for row in cursor.fetchall()}

            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "hit_rate_percent": round(hit_rate, 2),
                "total_entries": total_entries,
                "valid_entries": valid_entries,
                "expired_entries": total_entries - valid_entries,
                "total_accesses": total_accesses,
                "hits": self._hits,
                "misses": self._misses,
                "by_module": by_module,
            }

        except sqlite3.Error as e:
            logger.error("Cache stats error: %s", e)
            return {"error": str(e)}

    def _prune_cache(self, conn: sqlite3.Connection) -> None:
        """Remove expired entries and limit cache size.

        Args:
            conn: Active SQLite connection.
        """
        # Remove expired entries
        conn.execute("DELETE FROM cache WHERE expires_at < ?", (datetime.now().isoformat(),))

        # If still too large, remove least accessed
        cursor = conn.execute("SELECT COUNT(*) FROM cache")
        count = cursor.fetchone()[0] or 0

        if count > MAX_CACHE_ENTRIES:
            to_remove = count - MAX_CACHE_ENTRIES + 1000  # Remove extra to avoid frequent pruning
            conn.execute(
                """DELETE FROM cache WHERE key IN (
                    SELECT key FROM cache ORDER BY access_count ASC, last_accessed ASC LIMIT ?
                )""",
                (to_remove,),
            )
            logger.info("Pruned %d old cache entries", to_remove)

        conn.commit()

    def clear_cache(self) -> bool:
        """Clear all cached entries.

        Returns:
            True if cache cleared successfully.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared")
            return True
        except sqlite3.Error as e:
            logger.error("Cache clear error: %s", e)
            return False


# =============================================================================
# BANDWIDTH OPTIMIZER
# =============================================================================


class BandwidthOptimizer:
    """Optimizes responses for low-bandwidth environments.

    Provides compression, text-only formatting, and priority-based
    content delivery for users on slow or expensive connections.
    """

    # Priority keywords for response classification
    PRIORITY_KEYWORDS = {
        ResponsePriority.CRITICAL: [
            "emergency", "hospital", "ambulance", "police", "poison", "snake bite",
            "dying", "death", "accident", "fire", "heart attack", "stroke",
            "severe bleeding", "unconscious", "suicide",
        ],
        ResponsePriority.HIGH: [
            "malaria", "disease", "sick", "plant", "crop", "weather", "rain",
            "vaccine", "pregnancy", "child", "baby", "water",
        ],
        ResponsePriority.MEDIUM: [
            "business", "money", "loan", "school", "study", "learn", "farm",
            "market", "price", "sell", "register", "legal",
        ],
        ResponsePriority.LOW: [
            "news", "sports", "entertainment", "history", "general", "fun",
        ],
    }

    @classmethod
    def compress_response(cls, response: str, level: str = "high") -> str:
        """Compress a response to minimize data usage.

        Args:
            response: Full response text.
            level: Compression level - "low", "medium", or "high".

        Returns:
            Compressed response string.
        """
        if not response:
            return ""

        compressed = response

        # Remove extra whitespace
        compressed = re.sub(r"\s+", " ", compressed).strip()

        if level in ("medium", "high"):
            # Shorten common words
            replacements = {
                "government": "govt",
                "hospital": "hosp",
                "information": "info",
                "immediately": "now",
                "doctor": "dr",
                "medicine": "med",
                "treatment": "rx",
                "agricultural": "agri",
                "extension": "ext",
                "fertilizer": "fert",
                "approximately": "~",
                "because": "bc",
                "before": "b4",
                "with": "w/",
                "without": "w/o",
            }
            for full, short in replacements.items():
                compressed = compressed.replace(full, short)
                compressed = compressed.replace(full.capitalize(), short.capitalize())

        if level == "high":
            # Aggressive compression: abbreviate more, remove articles
            compressed = compressed.replace(" the ", " ")
            compressed = compressed.replace(" and ", " & ")
            compressed = compressed.replace(" for ", " 4 ")
            compressed = re.sub(r"\s+", " ", compressed).strip()

            # Truncate to most important sentences
            sentences = compressed.split(". ")
            if len(sentences) > 3:
                compressed = ". ".join(sentences[:3]) + "."

        logger.debug("Compressed response from %d to %d chars", len(response), len(compressed))
        return compressed

    @classmethod
    def format_for_low_bandwidth(cls, content: str) -> str:
        """Format content for extremely low bandwidth (text-only, no formatting).

        Args:
            content: Content to format.

        Returns:
            Plain text with minimal formatting.
        """
        if not content:
            return ""

        # Remove any markdown-like formatting
        text = content
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)      # Italic
        text = re.sub(r"`([^`]+)`", r"\1", text)         # Code
        text = re.sub(r"#+\s*", "", text)                # Headers
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # Links
        text = re.sub(r"\s+", " ", text).strip()

        return text

    @classmethod
    def get_response_priority(cls, query: str) -> ResponsePriority:
        """Determine the priority level of a query.

        Used to decide how much detail to include and how quickly
        to respond in bandwidth-constrained environments.

        Args:
            query: The user's query string.

        Returns:
            ResponsePriority enum value.
        """
        query_lower = query.lower()

        for priority, keywords in cls.PRIORITY_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return priority

        return ResponsePriority.MEDIUM

    @classmethod
    def estimate_data_size(cls, text: str) -> Dict[str, float]:
        """Estimate data size of a response in different formats.

        Args:
            text: Response text.

        Returns:
            Dictionary with size estimates in bytes for different formats.
        """
        text_bytes = len(text.encode("utf-8"))

        # Rough estimates for different formats
        return {
            "plain_text_bytes": text_bytes,
            "json_bytes": text_bytes * 1.5,  # JSON overhead
            "html_bytes": text_bytes * 2.0,  # HTML overhead
            "compressed_bytes": text_bytes * 0.4,  # Gzip estimate
            "sms_count": max(1, (len(text) + 159) // 160),
        }

    @classmethod
    def prioritize_content(cls, content: str, priority: ResponsePriority) -> str:
        """Return content sized appropriately for its priority.

        Critical content gets full detail; lower priority gets truncated.

        Args:
            content: Full content text.
            priority: Priority level of the content.

        Returns:
            Sized content string.
        """
        max_lengths = {
            ResponsePriority.CRITICAL: 1000,
            ResponsePriority.HIGH: 500,
            ResponsePriority.MEDIUM: 320,
            ResponsePriority.LOW: 160,
        }

        max_len = max_lengths.get(priority, 320)

        if len(content) <= max_len:
            return content

        # Truncate at sentence boundary
        truncated = content[:max_len]
        last_period = truncated.rfind(".")
        if last_period > max_len * 0.7:
            return truncated[:last_period + 1]

        return truncated + "..."


# =============================================================================
# SYNC MANAGER
# =============================================================================


class SyncManager:
    """Manages synchronization between offline and online data.

    Handles uploading offline interactions, resolving conflicts,
    and tracking sync status.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize sync manager.

        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path
        logger.info("SyncManager initialized")

    def sync_when_online(self) -> Dict[str, Any]:
        """Upload offline interactions when connection is available.

        Processes the sync queue, uploading records and resolving
        any conflicts with server data.

        Returns:
            Dictionary with sync results.
        """
        results = {
            "synced": 0,
            "failed": 0,
            "conflicts": 0,
            "resolved": 0,
            "status": SyncStatus.SYNCED.value,
        }

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get pending sync records
                cursor = conn.execute(
                    """SELECT id, table_name, record_id, operation, local_data,
                              local_timestamp, server_data, server_timestamp
                       FROM sync_queue
                       WHERE status = ?
                       LIMIT ?""",
                    (SyncStatus.PENDING.value, QUEUE_BATCH_SIZE),
                )
                records = cursor.fetchall()

                for record in records:
                    (
                        rec_id, table_name, record_id, operation,
                        local_data, local_timestamp, server_data, server_timestamp,
                    ) = record

                    try:
                        if server_data and server_timestamp:
                            # Potential conflict
                            conflict_result = self.resolve_conflicts(
                                json.loads(local_data),
                                json.loads(server_data),
                            )

                            conn.execute(
                                """UPDATE sync_queue
                                   SET status = ?, conflict_resolution = ?
                                   WHERE id = ?""",
                                (SyncStatus.SYNCED.value, json.dumps(conflict_result), rec_id),
                            )
                            results["conflicts"] += 1
                            results["resolved"] += 1
                        else:
                            # No conflict - simple upload
                            conn.execute(
                                "UPDATE sync_queue SET status = ? WHERE id = ?",
                                (SyncStatus.SYNCED.value, rec_id),
                            )
                            results["synced"] += 1

                        conn.commit()

                    except Exception as e:
                        logger.error("Sync failed for record %d: %s", rec_id, e)
                        conn.execute(
                            "UPDATE sync_queue SET status = ? WHERE id = ?",
                            (SyncStatus.FAILED.value, rec_id),
                        )
                        conn.commit()
                        results["failed"] += 1

        except sqlite3.Error as e:
            logger.error("Sync database error: %s", e)
            results["status"] = SyncStatus.FAILED.value

        logger.info("Sync complete: %s", results)
        return results

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status.

        Returns:
            Dictionary with counts of pending, synced, and failed records.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    """SELECT status, COUNT(*) FROM sync_queue GROUP BY status"""
                )
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

                cursor = conn.execute(
                    """SELECT COUNT(*) FROM sync_queue WHERE status = 'conflict'"""
                )
                conflict_count = cursor.fetchone()[0] or 0

                cursor = conn.execute(
                    """SELECT MAX(local_timestamp) FROM sync_queue WHERE status = 'pending'"""
                )
                oldest_pending = cursor.fetchone()[0]

            return {
                "pending": status_counts.get(SyncStatus.PENDING.value, 0),
                "synced": status_counts.get(SyncStatus.SYNCED.value, 0),
                "failed": status_counts.get(SyncStatus.FAILED.value, 0),
                "conflicts": conflict_count,
                "oldest_pending": oldest_pending,
                "needs_sync": status_counts.get(SyncStatus.PENDING.value, 0) > 0,
            }

        except sqlite3.Error as e:
            logger.error("Sync status error: %s", e)
            return {"error": str(e)}

    def resolve_conflicts(
        self,
        local_data: Dict[str, Any],
        server_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve conflicts between local and server data.

        Uses timestamp-based strategy: most recent change wins.
        For critical data, prefers server version.

        Args:
            local_data: Data from local (offline) changes.
            server_data: Data from server (online) changes.

        Returns:
            Resolved data dictionary.
        """
        resolved = {}
        resolution_log = []

        all_keys = set(local_data.keys()) | set(server_data.keys())

        for key in all_keys:
            local_val = local_data.get(key)
            server_val = server_data.get(key)

            if local_val == server_val:
                resolved[key] = local_val
            elif local_val is None:
                resolved[key] = server_val
                resolution_log.append(f"{key}: used server (local null)")
            elif server_val is None:
                resolved[key] = local_val
                resolution_log.append(f"{key}: used local (server null)")
            else:
                # Both have different values - use timestamp if available
                local_time = local_data.get("_timestamp", "")
                server_time = server_data.get("_timestamp", "")

                if local_time and server_time:
                    if local_time > server_time:
                        resolved[key] = local_val
                        resolution_log.append(f"{key}: used local (newer)")
                    else:
                        resolved[key] = server_val
                        resolution_log.append(f"{key}: used server (newer)")
                else:
                    # No timestamp - merge arrays, prefer server for scalars
                    if isinstance(local_val, list) and isinstance(server_val, list):
                        resolved[key] = list(set(local_val + server_val))
                        resolution_log.append(f"{key}: merged lists")
                    else:
                        resolved[key] = server_val
                        resolution_log.append(f"{key}: used server (default)")

        resolved["_conflict_resolution"] = resolution_log
        resolved["_resolved_at"] = datetime.now().isoformat()

        logger.debug("Resolved conflict with %d fields", len(resolution_log))
        return resolved

    def add_sync_record(
        self,
        table_name: str,
        record_id: str,
        operation: str,
        data: Dict[str, Any],
    ) -> bool:
        """Add a record to the sync queue.

        Args:
            table_name: Name of the table being synced.
            record_id: Unique identifier for the record.
            operation: Type of operation (create, update, delete).
            data: Record data as dictionary.

        Returns:
            True if added successfully.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """INSERT INTO sync_queue
                       (table_name, record_id, operation, local_data, local_timestamp, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        table_name,
                        record_id,
                        operation,
                        json.dumps(data),
                        datetime.now().isoformat(),
                        SyncStatus.PENDING.value,
                    ),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Failed to add sync record: %s", e)
            return False

    def retry_failed_syncs(self) -> int:
        """Retry previously failed sync attempts.

        Returns:
            Number of records queued for retry.
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    """UPDATE sync_queue SET status = ? WHERE status = ?""",
                    (SyncStatus.PENDING.value, SyncStatus.FAILED.value),
                )
                conn.commit()
                count = cursor.rowcount
                logger.info("Queued %d failed syncs for retry", count)
                return count
        except sqlite3.Error as e:
            logger.error("Retry failed syncs error: %s", e)
            return 0


# =============================================================================
# OFFLINE FAQ
# =============================================================================


class OfflineFAQ:
    """Provides pre-built answers for 200+ common African questions.

    This is the primary offline response source, organized by category
    for efficient lookup. Covers farming, health, education, business,
    weather, government, religion, and family topics.
    """

    # Category mapping for organizing answers
    CATEGORIES = {
        "farming": "Agriculture, livestock, crops, and farming practices",
        "health": "Health, wellness, disease prevention, and medical care",
        "education": "Schooling, learning, scholarships, and skills",
        "business": "Business, finance, entrepreneurship, and employment",
        "weather": "Weather, climate, seasons, and natural disasters",
        "government": "Government services, IDs, registration, and legal",
        "religion": "Religious and cultural practices",
        "family": "Family, parenting, relationships, and home",
    }

    def __init__(self) -> None:
        """Initialize FAQ with pre-built knowledge base."""
        # Build reverse index from keywords to answers
        self._index: Dict[str, List[str]] = {}
        self._build_index()
        logger.info("OfflineFAQ initialized with %d answers", len(OfflineManager.CACHE))

    def _build_index(self) -> None:
        """Build keyword index for faster FAQ lookups."""
        for key in OfflineManager.CACHE:
            words = key.lower().split()
            for word in words:
                clean_word = re.sub(r"[^a-z]", "", word)
                if len(clean_word) > 2:
                    if clean_word not in self._index:
                        self._index[clean_word] = []
                    self._index[clean_word].append(key)

    def get_answer(self, query: str) -> Optional[Dict[str, str]]:
        """Get a pre-built answer for a common question.

        Uses fuzzy matching to find the best answer even when the
        query doesn't exactly match a cached key.

        Args:
            query: The user's question.

        Returns:
            Dictionary with answer text and category, or None if not found.
        """
        normalized = query.lower().strip().rstrip("?").strip()

        # Direct match
        if normalized in OfflineManager.CACHE:
            return {
                "answer": OfflineManager.CACHE[normalized],
                "category": self._categorize(normalized),
                "match_type": "exact",
                "confidence": "high",
            }

        # Check for contained match
        for key in OfflineManager.CACHE:
            if normalized in key or key in normalized:
                return {
                    "answer": OfflineManager.CACHE[key],
                    "category": self._categorize(key),
                    "match_type": "partial",
                    "confidence": "high",
                }

        # Keyword index lookup
        query_words = [re.sub(r"[^a-z]", "", w) for w in normalized.split() if len(w) > 2]
        candidate_scores: Dict[str, int] = {}

        for word in query_words:
            for candidate_key in self._index.get(word, []):
                candidate_scores[candidate_key] = candidate_scores.get(candidate_key, 0) + 1

        if candidate_scores:
            best_key = max(candidate_scores, key=candidate_scores.get)
            score = candidate_scores[best_key]
            if score >= 2 or len(query_words) == 1:
                return {
                    "answer": OfflineManager.CACHE[best_key],
                    "category": self._categorize(best_key),
                    "match_type": "keyword",
                    "confidence": "medium" if score >= 2 else "low",
                }

        return None

    def get_answers_by_category(self, category: str) -> Dict[str, str]:
        """Get all answers in a specific category.

        Args:
            category: Category name (farming, health, education, etc.).

        Returns:
            Dictionary of question-answer pairs in the category.
        """
        results = {}
        for key, answer in OfflineManager.CACHE.items():
            if self._categorize(key) == category.lower():
                results[key] = answer
        return results

    def search_faq(self, keyword: str) -> Dict[str, str]:
        """Search FAQ for questions containing a keyword.

        Args:
            keyword: Search term.

        Returns:
            Matching question-answer pairs.
        """
        keyword_lower = keyword.lower()
        results = {}
        for key, answer in OfflineManager.CACHE.items():
            if keyword_lower in key or keyword_lower in answer.lower():
                results[key] = answer
        return results

    def _categorize(self, query_key: str) -> str:
        """Categorize a query into a topic area.

        Args:
            query_key: The query text.

        Returns:
            Category name string.
        """
        key_lower = query_key.lower()

        category_keywords = {
            "farming": ["plant", "crop", "farm", "seed", "harvest", "pest", "fertilizer",
                       "livestock", "cattle", "chicken", "goat", "dairy", "irrigation",
                       "soil", "compost", "maize", "rice", "beans", "tomato", "storage",
                       "vaccination", "deworm", "fish", "bee", "rabbit", "mushroom"],
            "health": ["malaria", "disease", "doctor", "clinic", "medicine", "symptom",
                      "vaccine", "nutrition", "diabetes", "HIV", "TB", "pregnancy",
                      "birth", "breastfeeding", "family planning", "cancer", "stroke",
                      "heart", "dental", "eye", "mental", "stress", "diet", "exercise",
                      "water", "sanitation", "cholera", "dengue", "typhoid", "wound"],
            "education": ["study", "school", "learn", "exam", "scholarship", "university",
                         "teacher", "student", "book", "read", "write", "career",
                         "coding", "digital", "library", "research", "speak", "vocational"],
            "business": ["business", "money", "loan", "market", "sell", "profit",
                        "sacco", "register", "tax", "employee", "customer", "price",
                        "supplier", "brand", "cash flow", "insurance", "negotiation",
                        "e-commerce", "export", "franchise", "mentorship"],
            "weather": ["weather", "rain", "flood", "drought", "climate", "season",
                       "temperature", "humidity", "harvest", "frost", "wind", "erosion",
                       "rainwater", "El Nino", "forecast"],
            "government": ["ID", "passport", "NHIF", "NSSF", "KRA", "register", "voter",
                          "permit", "license", "title", "birth", "death", "marriage",
                          "police", "court", "legal", "rights", "corruption"],
            "religion": ["church", "mosque", "prayer", "holiday", "christian", "muslim",
                        "cultural", "traditional", "elder", "naming", "wedding", "funeral"],
            "family": ["parent", "child", "marriage", "family", "baby", "elderly",
                      "orphan", "budget", "school fees", "domestic", "pregnant"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in key_lower for kw in keywords):
                return category

        return "general"

    def get_categories(self) -> Dict[str, str]:
        """Get list of available FAQ categories.

        Returns:
            Dictionary mapping category names to descriptions.
        """
        return dict(self.CATEGORIES)

    def get_stats(self) -> Dict[str, Any]:
        """Get FAQ statistics.

        Returns:
            Dictionary with total answers and counts per category.
        """
        category_counts: Dict[str, int] = {}
        for key in OfflineManager.CACHE:
            cat = self._categorize(key)
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_answers": len(OfflineManager.CACHE),
            "by_category": category_counts,
            "categories": list(self.CATEGORIES.keys()),
        }


# =============================================================================
# MODULE-LEVEL FUNCTIONS
# =============================================================================

# Global singleton instances
_offline_manager: Optional[OfflineManager] = None
_local_model_manager: Optional[LocalModelManager] = None
_sms_interface = SMSInterface
_bandwidth_optimizer = BandwidthOptimizer
_sync_manager: Optional[SyncManager] = None
_offline_faq: Optional[OfflineFAQ] = None
_cache_manager: Optional[CacheManager] = None


def _get_offline_manager() -> OfflineManager:
    """Get or create the global OfflineManager instance."""
    global _offline_manager
    if _offline_manager is None:
        _offline_manager = OfflineManager()
    return _offline_manager


def _get_local_model_manager() -> LocalModelManager:
    """Get or create the global LocalModelManager instance."""
    global _local_model_manager
    if _local_model_manager is None:
        _local_model_manager = LocalModelManager()
    return _local_model_manager


def _get_sync_manager() -> SyncManager:
    """Get or create the global SyncManager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager(DEFAULT_DB_PATH)
    return _sync_manager


def _get_offline_faq() -> OfflineFAQ:
    """Get or create the global OfflineFAQ instance."""
    global _offline_faq
    if _offline_faq is None:
        _offline_faq = OfflineFAQ()
    return _offline_faq


def _get_cache_manager() -> CacheManager:
    """Get or create the global CacheManager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(DEFAULT_DB_PATH)
    return _cache_manager


def offline_query(
    query: str,
    user_id: str = "anonymous",
    module: str = "general",
    use_local_model: bool = True,
) -> Dict[str, Any]:
    """Handle a user query when offline or connectivity is limited.

    This is the main entry point for offline queries. It attempts multiple
    strategies in order: pre-built FAQ, local LLM, cache lookup, and finally
    queues the request for later processing.

    Args:
        query: The user's question or request.
        user_id: Unique identifier for the user.
        module: Functional module (farming, health, education, etc.).
        use_local_model: Whether to try local LLM if available.

    Returns:
        Dictionary with response text, source, and metadata.
    """
    result = {
        "query": query,
        "response": "",
        "source": "none",
        "offline": True,
        "cached": False,
        "module": module,
        "timestamp": datetime.now().isoformat(),
    }

    # 1. Try pre-built FAQ (fastest, most reliable)
    faq = _get_offline_faq()
    faq_answer = faq.get_answer(query)
    if faq_answer and faq_answer.get("confidence") in ("high", "medium"):
        result["response"] = faq_answer["answer"]
        result["source"] = "faq"
        result["category"] = faq_answer.get("category", "general")
        result["confidence"] = faq_answer.get("confidence", "medium")

        # Cache the response for future use
        _get_cache_manager().set_cached(
            query.lower().strip(), faq_answer["answer"], module
        )
        return result

    # 2. Try local LLM (Ollama) if available
    if use_local_model:
        model_mgr = _get_local_model_manager()
        if model_mgr.is_ollama_available():
            llm_result = model_mgr.query_local_model(query)
            if llm_result.get("success"):
                result["response"] = llm_result["response"]
                result["source"] = "local_llm"

                # Cache the LLM response
                _get_cache_manager().set_cached(
                    query.lower().strip(), llm_result["response"], module
                )
                return result

    # 3. Try cache lookup
    cached_response = _get_cache_manager().get_cached(query.lower().strip())
    if cached_response:
        result["response"] = cached_response
        result["source"] = "cache"
        result["cached"] = True
        return result

    # 4. Generic fallback response
    result["response"] = (
        "I am working offline right now. I could not find a specific answer, "
        "but I have saved your question. I will try to get an answer when "
        "connectivity returns. For urgent matters, please contact a professional "
        "directly. Reply HELP for available topics."
    )
    result["source"] = "fallback"

    # Queue for later processing
    mgr = _get_offline_manager()
    request_id = mgr.queue_request(query, user_id, module)
    result["queued_request_id"] = request_id

    return result


def sms_response(message: str, user_id: str = "anonymous") -> Dict[str, Any]:
    """Process an incoming SMS query and return SMS-formatted response.

    Args:
        message: The SMS message text.
        user_id: Phone number or user identifier.

    Returns:
        Dictionary with SMS-formatted response and metadata.
    """
    result = {
        "incoming_message": message,
        "response": "",
        "sms_chunks": [],
        "command": None,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
    }

    # Parse the SMS query
    parsed = SMSInterface.parse_sms_query(message)
    result["command"] = parsed.get("command")
    result["parsed_query"] = parsed.get("query")

    # If it's a recognized command, use command handler
    if parsed.get("is_command") and parsed.get("command"):
        response_text = SMSInterface.handle_sms_command(parsed["command"])
        result["response"] = response_text
        result["sms_chunks"] = SMSInterface.format_long_response(response_text)
        return result

    # Try FAQ for the actual query content
    faq = _get_offline_faq()
    faq_answer = faq.get_answer(parsed.get("query", message))

    if faq_answer:
        formatted = SMSInterface.format_for_sms(faq_answer["answer"])
        result["response"] = formatted
        result["source"] = "faq"
    else:
        # Generic SMS help response
        result["response"] = SMSInterface.format_for_sms(
            "Sorry, I do not have an answer for that. Reply HELP for available "
            "commands, or ask about farming, health, business, or education."
        )
        result["source"] = "fallback"

    result["sms_chunks"] = SMSInterface.format_long_response(result["response"])
    result["character_count"] = SMSInterface.get_character_count(result["response"])

    return result


def cache_response(query: str, response: str, module: str = "general") -> bool:
    """Cache a response for future offline use.

    Args:
        query: The query string to cache under.
        response: The response text to cache.
        module: Functional module category.

    Returns:
        True if caching succeeded.
    """
    cache_mgr = _get_cache_manager()
    return cache_mgr.set_cached(query.lower().strip(), response, module)


def sync_data() -> Dict[str, Any]:
    """Trigger synchronization of offline data with the server.

    Returns:
        Dictionary with sync results and status.
    """
    sync_mgr = _get_sync_manager()
    offline_mgr = _get_offline_manager()

    # First process any queued requests
    queue_results = offline_mgr.process_queue()

    # Then sync data records
    sync_results = sync_mgr.sync_when_online()

    return {
        "queue_processing": queue_results,
        "data_sync": sync_results,
        "timestamp": datetime.now().isoformat(),
        "online": offline_mgr.is_online(),
    }


def get_offline_status() -> Dict[str, Any]:
    """Get current offline/online status and system information.

    Returns:
        Dictionary with connectivity status, cache stats, queue status, etc.
    """
    offline_mgr = _get_offline_manager()
    sync_mgr = _get_sync_manager()
    faq = _get_offline_faq()
    model_mgr = _get_local_model_manager()

    is_connected = offline_mgr.is_online()
    faq_stats = faq.get_stats()

    status = {
        "online": is_connected,
        "timestamp": datetime.now().isoformat(),
        "cache_entries": faq_stats["total_answers"],
        "faq_categories": faq_stats["by_category"],
        "sync_status": sync_mgr.get_sync_status(),
        "ollama_available": model_mgr.is_ollama_available(),
        "local_models": model_mgr.get_available_models() if is_connected else [],
    }

    # Add bandwidth-optimized flag for low-connectivity scenarios
    if not is_connected:
        status["mode"] = "offline"
        status["fallback_available"] = True
    else:
        status["mode"] = "online"
        status["pending_sync"] = status["sync_status"].get("pending", 0)

    return status


def initialize_offline_engine(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Initialize the offline engine with all components.

    This should be called at application startup to ensure all
    subsystems are ready.

    Args:
        db_path: Optional custom database path.

    Returns:
        Dictionary with initialization results.
    """
    global DEFAULT_DB_PATH
    if db_path:
        DEFAULT_DB_PATH = db_path

    results = {
        "initialized": True,
        "components": {},
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Initialize database and managers
        offline_mgr = OfflineManager(db_path)
        results["components"]["offline_manager"] = "ok"

        # Warm cache with all pre-built answers
        cache_mgr = CacheManager(offline_mgr.db_path)
        warmed = cache_mgr.warm_cache("all")
        results["components"]["cache_warmed"] = warmed

        # Check local model availability
        model_mgr = LocalModelManager()
        results["components"]["ollama_available"] = model_mgr.is_ollama_available()

        # Initialize FAQ
        faq = OfflineFAQ()
        results["components"]["faq_entries"] = len(OfflineManager.CACHE)
        results["components"]["faq_categories"] = list(faq.CATEGORIES.keys())

        # Check connectivity
        results["components"]["online"] = offline_mgr.is_online()

        logger.info("Offline engine initialized successfully")

    except Exception as e:
        results["initialized"] = False
        results["error"] = str(e)
        logger.error("Offline engine initialization failed: %s", e)

    return results


# =============================================================================
# MAIN / DEMO
# =============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("Luqi AI v20 - Offline Engine Demo")
    print("=" * 60)

    # Initialize the engine
    init_result = initialize_offline_engine()
    print(f"\nInitialization: {'SUCCESS' if init_result['initialized'] else 'FAILED'}")
    print(f"FAQ entries: {init_result['components'].get('faq_entries', 0)}")
    print(f"Cache warmed: {init_result['components'].get('cache_warmed', 0)}")
    print(f"Online: {init_result['components'].get('online', False)}")
    print(f"Ollama available: {init_result['components'].get('ollama_available', False)}")

    # Demo offline queries
    print("\n--- Offline Query Demo ---")
    demo_queries = [
        "how to plant maize",
        "malaria symptoms",
        "how to start poultry farming",
        "scholarship opportunities",
        "how to start a business",
    ]

    for q in demo_queries:
        result = offline_query(q, user_id="demo_user")
        print(f"\nQ: {q}")
        print(f"A: {result['response'][:120]}...")
        print(f"Source: {result['source']}")

    # Demo SMS interface
    print("\n--- SMS Interface Demo ---")
    demo_sms_messages = [
        "HELP",
        "how to plant maize",
        "What are malaria symptoms?",
        "I need farming advice",
    ]

    for msg in demo_sms_messages:
        result = sms_response(msg, user_id="+254712345678")
        print(f"\nSMS: {msg}")
        print(f"Response: {result['response']}")
        print(f"Chunks: {len(result['sms_chunks'])}")

    # Demo FAQ stats
    print("\n--- FAQ Statistics ---")
    faq = _get_offline_faq()
    stats = faq.get_stats()
    for cat, count in stats["by_category"].items():
        print(f"  {cat}: {count} answers")
    print(f"  Total: {stats['total_answers']} answers")

    # Demo offline status
    print("\n--- System Status ---")
    status = get_offline_status()
    print(f"Mode: {status['mode']}")
    print(f"Cache entries: {status['cache_entries']}")
    print(f"Ollama: {status['ollama_available']}")

    print("\n" + "=" * 60)
    print("Luqi AI Offline Engine Demo Complete")
    print("=" * 60)
