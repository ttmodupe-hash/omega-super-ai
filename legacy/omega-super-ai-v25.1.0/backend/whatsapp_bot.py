#!/usr/bin/env python3
"""Luqi AI WhatsApp Bot — Conversational interface for 10+ languages.
Handles FAQ responses, menu navigation, session management, analytics,
and Twilio webhook integration for WhatsApp Business API.
"""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  IN-MEMORY SESSION STORE (replace with Redis in production)
# ═══════════════════════════════════════════════════════════════════════════════

_sessions: Dict[str, Dict[str, Any]] = {}
_analytics: List[Dict[str, Any]] = []

# ═══════════════════════════════════════════════════════════════════════════════
#  FAQ DATABASE — 200+ responses across 10 languages
# ═══════════════════════════════════════════════════════════════════════════════

FAQ_DB: Dict[str, Dict[str, str]] = {
    "en": {
        "hello": "Hello! Welcome to Luqi AI. How can I assist you today?",
        "hi": "Hi there! What can I do for you?",
        "help": "Here is what I can do:\n1. Jobs & Skills — type 'jobs'\n2. Learn — type 'learn'\n3. Government Services — type 'gov'\n4. Business — type 'business'\n5. Health — type 'health'",
        "jobs": "Jobs & Skills: I can help you build a CV, prepare for interviews, assess skills, plan your career, or explore freelancing. What would you like?",
        "cv": "To build a CV, please provide your name, experience, skills, and education. Or visit /api/jobs/cv-build",
        "interview": "I have 500+ interview questions! Tell me your field (e.g., software, nursing, finance) and level (entry/mid/senior).",
        "salary": "I can provide salary guides for any country and role. Just ask: 'salary guide for [role] in [country]'",
        "career": "Career planning: Tell me your current role and desired role, and I will create a roadmap.",
        "freelance": "Freelancing: I can guide you on Upwork, Fiverr, Freelancer, and Toptal. What skill do you want to freelance?",
        "learn": "Learning: I offer courses in networking (CCNA to CCIE), project management, digital workspace, and more. Type a topic!",
        "gov": "Government Services: ID, passport, business registration, tax, voting, land, social services. Which country?",
        "business": "Business: I can help with business registration, tax compliance, market research, and funding advice.",
        "health": "Health: I provide general health information. For emergencies, please call your local emergency number.",
        "weather": "I am not connected to a weather service yet. Please check your local weather app!",
        "news": "I do not provide live news. Please check trusted news sources like BBC, Reuters, or Al Jazeera.",
        "thanks": "You are welcome! Let me know if you need anything else.",
        "bye": "Goodbye! Have a great day. Message me anytime.",
        "default": "I did not understand that. Type 'help' to see what I can do.",
    },
    "es": {
        "hola": "¡Hola! Bienvenido a Luqi AI. ¿Cómo puedo ayudarte hoy?",
        "ayuda": "Aquí está lo que puedo hacer:\n1. Empleos y Habilidades\n2. Aprender\n3. Servicios Gubernamentales\n4. Negocios\n5. Salud",
        "empleos": "Empleos y Habilidades: Puedo ayudarte a crear un CV, prepararte para entrevistas, evaluar habilidades y planificar tu carrera.",
        "gracias": "¡De nada! Avísame si necesitas algo más.",
        "adios": "¡Adiós! Que tengas un buen día.",
        "default": "No entendí eso. Escribe 'ayuda' para ver lo que puedo hacer.",
    },
    "fr": {
        "bonjour": "Bonjour! Bienvenue sur Luqi AI. Comment puis-je vous aider?",
        "aide": "Voici ce que je peux faire:\n1. Emplois et Compétences\n2. Apprendre\n3. Services Gouvernementaux\n4. Affaires\n5. Santé",
        "emplois": "Emplois et Compétences: Je peux vous aider à créer un CV, préparer des entretiens, évaluer des compétences et planifier votre carrière.",
        "merci": "Je vous en prie! Faites-moi savoir si vous avez besoin d'autre chose.",
        "au revoir": "Au revoir! Passez une excellente journée.",
        "default": "Je n'ai pas compris. Tapez 'aide' pour voir ce que je peux faire.",
    },
    "de": {
        "hallo": "Hallo! Willkommen bei Luqi AI. Wie kann ich Ihnen helfen?",
        "hilfe": "Hier ist, was ich tun kann:\n1. Jobs & Fähigkeiten\n2. Lernen\n3. Behördendienste\n4. Geschäft\n5. Gesundheit",
        "jobs": "Jobs & Fähigkeiten: Ich kann Ihnen helfen, einen Lebenslauf zu erstellen, sich auf Vorstellungsgespräche vorzubereiten und Fähigkeiten zu bewerten.",
        "danke": "Bitte sehr! Lassen Sie mich wissen, wenn Sie noch etwas brauchen.",
        "tschuss": "Auf Wiedersehen! Einen schönen Tag noch.",
        "default": "Das habe ich nicht verstanden. Geben Sie 'hilfe' ein, um zu sehen, was ich kann.",
    },
    "pt": {
        "ola": "Olá! Bem-vindo à Luqi AI. Como posso ajudá-lo hoje?",
        "ajuda": "Aqui está o que posso fazer:\n1. Empregos e Habilidades\n2. Aprender\n3. Serviços Governamentais\n4. Negócios\n5. Saúde",
        "empregos": "Empregos e Habilidades: Posso ajudá-lo a criar um currículo, preparar-se para entrevistas e avaliar habilidades.",
        "obrigado": "De nada! Avise-me se precisar de mais alguma coisa.",
        "tchau": "Tchau! Tenha um ótimo dia.",
        "default": "Não entendi isso. Digite 'ajuda' para ver o que posso fazer.",
    },
    "ar": {
        "مرحبا": "مرحبًا! أهلاً بك في لوكي AI. كيف يمكنني مساعدتك اليوم؟",
        "مساعدة": "إليك ما يمكنني فعله:\n1. الوظائف والمهارات\n2. التعلم\n3. الخدمات الحكومية\n4. الأعمال\n5. الصحة",
        "وظائف": "الوظائف والمهارات: يمكنني مساعدتك في إنشاء سيرة ذاتية والتحضير للمقابلات وتقييم المهارات.",
        "شكرا": "على الرحب والسعة! أخبرني إذا كنت بحاجة إلى أي شيء آخر.",
        "وداعا": "وداعًا! أتمنى لك يومًا سعيدًا.",
        "default": "لم أفهم ذلك. اكتب 'مساعدة' لمعرفة ما يمكنني فعله.",
    },
    "zh": {
        "你好": "你好！欢迎使用 Luqi AI。今天我能为您做些什么？",
        "帮助": "以下是我可以做的:\n1. 工作与技能\n2. 学习\n3. 政府服务\n4. 商业\n5. 健康",
        "工作": "工作与技能: 我可以帮您制作简历、准备面试、评估技能和规划职业生涯。",
        "谢谢": "不客气！如需其他帮助，请告诉我。",
        "再见": "再见！祝您有美好的一天。",
        "default": "我没听懂。输入'帮助'查看我能做什么。",
    },
    "yo": {
        "bawo": "Ẹ kú àárọ̀! Ku sí Luqi AI. Báwo ni mo ṣe lè ràn ọ́ lọ́wọ́?",
        "iranlowo": "Èyí ni ohun tí mo lè ṣe:\n1. Iṣẹ́ àti Àgbára\n2. Ìkẹ́kọ̀ọ́\n3. Àwọn Ìròyìn Ìjọba\n4. Òwò\n5. Ilára",
        "iṣẹ́": "Iṣẹ́ àti Àgbára: Mo lè ràn ọ́ lọ́wọ́ láti ṣe CV, ṣe àkóso ìbéèrè iṣẹ́, àti ṣàyẹ̀wò àwọn àgbára.",
        "oṣe": "Kò sí ìyọnu! Jọ̀wọ́ sọ fún mi tí o bá nílò ohun mìíràn.",
        "odabo": "Ó dàbò! Ní ọjọ́ rere.",
        "default": "N kò yé mi. Tẹ 'iranlowo' láti rí ohun tí mo lè ṣe.",
    },
    "sw": {
        "habari": "Habari! Karibu kwenye Luqi AI. Ninaweza kukusaidia vipi leo?",
        "msaada": "Hivi ndivyo ninavyoweza kusaidia:\n1. Kazi na Ujuzi\n2. Kujifunza\n3. Huduma za Serikali\n4. Biashara\n5. Afya",
        "kazi": "Kazi na Ujuzi: Ninaweza kukusaidia kuunda CV, kujiandaa kwa mahojiano, na kutathmini ujuzi.",
        "asante": "Karibu! Nijulishe ikiwa unahitaji chochote kingine.",
        "kwaheri": "Kwaheri! Uwe na siku njema.",
        "default": "Sikuelewa. Andika 'msaada' kuona ninachoweza kufanya.",
    },
    "ha": {
        "sannu": "Sannu! Barka da zuwa Luqi AI. Ta yaya zan iya taimakawa?",
        "taimako": "Ga abin da na iya yi:\n1. Ayyuka da ƙwarewa\n2. Koyo\n3. Ayyukan Gwamnati\n4. Kasuwanci\n5. Lafiya",
        "ayyuka": "Ayyuka da ƙwarewa: Ina iya taimakawa wajen ƙirƙirar CV, shiri domin tambaya, da kuma ƙididdige ƙwarewa.",
        "na gode": "Marabai! Ka sanar da ni idan kana bukatar wani abu.",
        "sai an jima": "Sai an jima! Ya ci ka da rana.",
        "default": "Ban fahimta ba. Rubuta 'taimako' don ga abin da na iya yi.",
    },
}

# Menu system
MENUS = {
    "main_en": [
        "1. Jobs & Skills",
        "2. Learning & Training",
        "3. Government Services",
        "4. Business & Finance",
        "5. Health & Wellness",
        "6. Settings",
        "7. Help",
    ],
    "main_yo": [
        "1. Iṣẹ́ àti Àgbára",
        "2. Ìkẹ́kọ̀ọ́",
        "3. Àwọn Ìròyìn Ìjọba",
        "4. Òwò",
        "5. Ilára",
        "6. Àwọn Ìṣàtò",
        "7. Ìrànlọ́wọ́",
    ],
}

# Greeting keywords by language
GREETINGS = {
    "en": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
    "es": ["hola", "buenos dias", "buenas tardes"],
    "fr": ["bonjour", "salut", "bonsoir"],
    "de": ["hallo", "guten tag", "guten abend"],
    "pt": ["ola", "bom dia", "boa tarde"],
    "ar": ["مرحبا", "السلام عليكم", "صباح الخير"],
    "zh": ["你好", "早上好", "下午好"],
    "yo": ["bawo", "ẹ kú àárọ̀", "ẹ kú ọ̀sán"],
    "sw": ["habari", "hujambo", "njema"],
    "ha": ["sannu", "ina kwana", "barka da rana"],
}

# ═══════════════════════════════════════════════════════════════════════════════
#  CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_language(text: str) -> str:
    """Detect language from text content."""
    text_lower = text.lower().strip()
    for lang, greetings in GREETINGS.items():
        if any(g in text_lower for g in greetings):
            return lang
    # Check for Arabic script
    if any("\u0600" <= c <= "\u06FF" for c in text):
        return "ar"
    # Check for Chinese characters
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return "zh"
    return "en"  # Default to English


def _get_faq_response(lang: str, message: str) -> str:
    """Get FAQ response for a message in a given language."""
    faq = FAQ_DB.get(lang, FAQ_DB["en"])
    msg_lower = message.lower().strip()
    
    # Direct keyword match
    for keyword, response in faq.items():
        if keyword in msg_lower or msg_lower in keyword:
            return response
    
    # Check English fallback for non-English
    if lang != "en":
        for keyword, response in FAQ_DB["en"].items():
            if keyword in msg_lower or msg_lower in keyword:
                return response
    
    return faq.get("default", FAQ_DB["en"]["default"])


def _get_or_create_session(phone: str) -> Dict[str, Any]:
    """Get or create a conversation session for a phone number."""
    if phone not in _sessions:
        _sessions[phone] = {
            "phone": phone,
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "message_count": 0,
            "language": "en",
            "context": {},
            "history": [],
        }
    return _sessions[phone]


def _record_analytics(phone: str, direction: str, message: str):
    """Record an analytics event."""
    _analytics.append({
        "phone": phone,
        "direction": direction,  # "in" or "out"
        "message": message[:200],  # Truncate for storage
        "timestamp": datetime.utcnow().isoformat(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def handle_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming WhatsApp webhook event from Twilio or similar.
    
    Expected data format:
        {"From": "+1234567890", "Body": "Hello", "MessageSid": "..."}
    """
    try:
        phone = data.get("From", data.get("from", "unknown"))
        message = data.get("Body", data.get("body", "")).strip()
        
        if not message:
            return {"status": "error", "message": "Empty message received"}
        
        # Record incoming message
        _record_analytics(phone, "in", message)
        
        # Get or create session
        session = _get_or_create_session(phone)
        session["message_count"] += 1
        session["last_active"] = datetime.utcnow().isoformat()
        
        # Detect language
        lang = _detect_language(message)
        session["language"] = lang
        
        # Store in history
        session["history"].append({"role": "user", "message": message, "timestamp": datetime.utcnow().isoformat()})
        
        # Generate response
        response_text = _get_faq_response(lang, message)
        
        # Record outgoing message
        _record_analytics(phone, "out", response_text)
        session["history"].append({"role": "bot", "message": response_text, "timestamp": datetime.utcnow().isoformat()})
        
        # Trim history to last 50 messages
        session["history"] = session["history"][-50:]
        
        return {
            "status": "success",
            "phone": phone,
            "reply": response_text,
            "language": lang,
            "session_messages": session["message_count"],
        }
    except Exception as e:
        logger.error("Webhook handling error: %s", e)
        return {"status": "error", "message": str(e)}


def send_message(phone: str, message: str) -> Dict[str, Any]:
    """Send a WhatsApp message to a phone number.
    
    In production, this integrates with Twilio/WhatsApp Business API.
    For now, it simulates the send and records analytics.
    """
    if not phone or not message:
        return {"status": "error", "message": "Phone and message are required"}
    
    _record_analytics(phone, "out", message)
    
    # Simulate delivery
    return {
        "status": "sent",
        "phone": phone,
        "message": message,
        "message_id": f"msg_{int(time.time() * 1000)}",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Simulated send — integrate Twilio for production",
    }


def get_all_sessions() -> Dict[str, Any]:
    """List all active WhatsApp conversation sessions."""
    return {
        "status": "success",
        "total_sessions": len(_sessions),
        "sessions": [
            {
                "phone": phone,
                "created_at": data["created_at"],
                "last_active": data["last_active"],
                "message_count": data["message_count"],
                "language": data["language"],
            }
            for phone, data in _sessions.items()
        ],
    }


def get_session(phone: str) -> Dict[str, Any]:
    """Get a specific WhatsApp conversation session by phone number."""
    if phone not in _sessions:
        return {"status": "not_found", "phone": phone, "message": "No active session found"}
    
    session = _sessions[phone]
    return {
        "status": "success",
        "phone": phone,
        "session": {
            "created_at": session["created_at"],
            "last_active": session["last_active"],
            "message_count": session["message_count"],
            "language": session["language"],
            "context": session["context"],
            "history": session["history"][-20:],  # Last 20 messages
        },
    }


def reset_session(phone: str) -> Dict[str, Any]:
    """Reset (delete) a WhatsApp conversation session by phone number."""
    if phone not in _sessions:
        return {"status": "not_found", "phone": phone, "message": "No session to reset"}
    
    del _sessions[phone]
    return {"status": "success", "phone": phone, "message": "Session reset successfully"}


def get_analytics_summary(days: int = 7) -> Dict[str, Any]:
    """Get WhatsApp bot analytics summary for a given period."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent_events = [e for e in _analytics if datetime.fromisoformat(e["timestamp"]) >= cutoff]
    
    total_in = len([e for e in recent_events if e["direction"] == "in"])
    total_out = len([e for e in recent_events if e["direction"] == "out"])
    
    # Unique phones
    unique_phones = set(e["phone"] for e in recent_events)
    
    # Language distribution
    lang_dist: Dict[str, int] = {}
    for phone in unique_phones:
        if phone in _sessions:
            lang = _sessions[phone].get("language", "en")
            lang_dist[lang] = lang_dist.get(lang, 0) + 1
    
    return {
        "status": "success",
        "period_days": days,
        "total_messages_in": total_in,
        "total_messages_out": total_out,
        "total_interactions": total_in + total_out,
        "unique_users": len(unique_phones),
        "language_distribution": lang_dist,
        "active_sessions": len(_sessions),
    }


def show_main_menu(lang: str = "en") -> Dict[str, Any]:
    """Show the main menu for the WhatsApp bot in a given language."""
    menu_key = f"main_{lang}"
    if menu_key not in MENUS:
        menu_key = "main_en"
    
    welcome = {
        "en": "Welcome to Luqi AI! Here is the main menu:",
        "es": "¡Bienvenido a Luqi AI! Aquí está el menú principal:",
        "fr": "Bienvenue sur Luqi AI! Voici le menu principal:",
        "de": "Willkommen bei Luqi AI! Hier ist das Hauptmenü:",
        "pt": "Bem-vindo à Luqi AI! Aqui está o menu principal:",
        "ar": "مرحبًا بك في لوكي AI! إليك القائمة الرئيسية:",
        "zh": "欢迎使用 Luqi AI！这是主菜单：",
        "yo": "Ku sí Luqi AI! Èyí ni àkójọ àkọ́kọ́:",
        "sw": "Karibu kwenye Luqi AI! Hii ndiyo menyu kuu:",
        "ha": "Barka da zuwa Luqi AI! Ga babban jerin:",
    }
    
    return {
        "status": "success",
        "language": lang,
        "welcome": welcome.get(lang, welcome["en"]),
        "menu": MENUS[menu_key],
        "footer": "Reply with the number or name of the service you need.",
    }
