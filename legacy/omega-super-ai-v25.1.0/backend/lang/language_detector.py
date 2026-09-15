#!/usr/bin/env python3
"""
Luqi AI — Language Detection Engine

Multi-strategy language detection optimized for African languages.
Uses a cascading approach: greeting matching, unicode script analysis,
pattern matching, n-gram analysis, and heuristic fallback.

Usage:
    detector = LanguageDetector()
    lang_code = detector.detect("Jambo! Habari yako?")  # Returns "sw"
    greeting = detector.format_greeting("sw")  # "Habari"
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple


# =============================================================================
# LANGUAGE GREETING DATABASE
# =============================================================================

LANGUAGE_GREETINGS: Dict[str, Dict[str, str]] = {
    # ---- East Africa ----
    "sw": {"hello": "Habari", "goodbye": "Kwa heri", "thank_you": "Asante", "help": "Msaada", "welcome": "Karibu"},
    "rw": {"hello": "Muraho", "goodbye": "Muraho neza", "thank_you": "Murakoze", "help": "Ubufasha", "welcome": "Ikaze"},
    "rn": {"hello": "Amahoro", "goodbye": "Gira neza", "thank_you": "Murakoze", "help": "Ubufasha", "welcome": "Ikaze"},
    "so": {"hello": "Ma nabad baa", "goodbye": "Ma nabad baa", "thank_you": "Mahadsanid", "help": "Caawimo", "welcome": "Soo dhowow"},
    "am": {"hello": "Selam", "goodbye": "Dehna hun", "thank_you": "Ameseginalehu", "help": "Ede", "welcome": "Enkuan desta"},
    "ti": {"hello": "Selam", "goodbye": "Dehan hun", "thank_you": "Yekeniyeley", "help": "Ede", "welcome": "Tikuala"},
    "om": {"hello": "Akkam", "goodbye": "Nagaa dhuftu", "thank_you": "Galatoomi", "help": "Gargaarsa", "welcome": "Baga nagaan dhuftan"},
    "lg": {"hello": "Wasuze otya", "goodbye": "Weraba", "thank_you": "Webale", "help": "Obuyambi", "welcome": "Tukusanyukidde"},
    "mg": {"hello": "Manao ahoana", "goodbye": "Veloma", "thank_you": "Misaotra", "help": "Fanampiana", "welcome": "Tonga soa"},
    # ---- West Africa ----
    "yo": {"hello": "Bawo ni", "goodbye": "O dabọ", "thank_you": "O ṣeun", "help": "Irannlọwọ", "welcome": "Ẹ ku abọ"},
    "ig": {"hello": "Nnọọ", "goodbye": "Ka chi fo", "thank_you": "Daalụ", "help": "Enyemaka", "welcome": "Nno"},
    "ha": {"hello": "Sannu", "goodbye": "Sai an jima", "thank_you": "Na gode", "help": "Taimako", "welcome": "Barka da zuwa"},
    "ff": {"hello": "A jaaraama", "goodbye": "A jaaraama", "thank_you": "A jaaraama", "help": "Ballal", "welcome": "A jaaraama"},
    "ak": {"hello": "Mahama", "goodbye": "Nantee yie", "thank_you": "Medaase", "help": "Mmoa", "welcome": "Akwaaba"},
    "ee": {"hello": "Woezon", "goodbye": "De mafia wo", "thank_you": "Madu", "help": "Kpekpe", "welcome": "Woezon"},
    "wo": {"hello": "Asalaam malekum", "goodbye": "Ba beneen", "thank_you": "Jërëjëf", "help": "Walla", "welcome": "Ci yab na"},
    "bm": {"hello": "I ni ce", "goodbye": "Ka ben", "thank_you": "I ni ce", "help": "Dɛmɛ", "welcome": "I ni ce"},
    "mos": {"hello": "Lafi barka", "goodbye": "Lalle wende", "thank_you": "M wend naore", "help": "Yaaba", "welcome": "Lafikat"},
    "fon": {"hello": "Alafia", "goodbye": "Hwedō", "thank_you": "Ahouanu", "help": "Alōdō", "welcome": "Kpɛnɛ"},
    # ---- Southern Africa ----
    "zu": {"hello": "Sawubona", "goodbye": "Hamba kahle", "thank_you": "Ngiyabonga", "help": "Usizo", "welcome": "Siyakwamukela"},
    "xh": {"hello": "Molo", "goodbye": "Hamba kakuhle", "thank_you": "Enkosi", "help": "Uncedo", "welcome": "Wamkelekile"},
    "af": {"hello": "Hallo", "goodbye": "Totsiens", "thank_you": "Dankie", "help": "Hulp", "welcome": "Welkom"},
    "st": {"hello": "Dumela", "goodbye": "Sala hantle", "thank_you": "Ke a leboha", "help": "Thuso", "welcome": "O amohetswe"},
    "tn": {"hello": "Dumela", "goodbye": "Tswang ditlela", "thank_you": "Ke a leboga", "help": "Thuso", "welcome": "O amogetswe"},
    "sn": {"hello": "Mhoroi", "goodbye": "Chisarai zvakanaka", "thank_you": "Ndinotenda", "help": "Rubatsiro", "welcome": "Mauya"},
    "nd": {"hello": "Salibonani", "goodbye": "Lihambe kahle", "thank_you": "Ngiyabonga", "help": "Usizo", "welcome": "Wamukelekile"},
    "ny": {"hello": "Moni", "goodbye": "Pitani bwino", "thank_you": "Zikomo", "help": "Thandizo", "welcome": "Takulandirani"},
    # ---- North Africa ----
    "ar-eg": {"hello": "As-salamu alaykum", "goodbye": "Ma'a salama", "thank_you": "Shukran", "help": "Musaa'da", "welcome": "Ahlan wa sahlan"},
    "ary": {"hello": "As-salamu alaykum", "goodbye": "Bslama", "thank_you": "Shukran", "help": "Musaada", "welcome": "Marhaba"},
    "kab": {"hello": "Azul fell-awen", "goodbye": "Ttεelleme", "thank_you": "Tanmirt", "help": "Tallelt", "welcome": "Azul"},
    "shi": {"hello": "Manzak", "goodbye": "Ar ttili", "thank_you": "Tanmirt", "help": "Tallalt", "welcome": "Bark"},
    # ---- Central Africa ----
    "ln": {"hello": "Mbote", "goodbye": "Kenam", "thank_you": "Matondo", "help": "Lisalisi", "welcome": "Boyei bolamu"},
    "kg": {"hello": "Kiao", "goodbye": "Kiele", "thank_you": "Ntondo", "help": "Lusadisu", "welcome": "Kwiza"},
    "sg": {"hello": "Baraa", "goodbye": "Baraa na", "thank_you": "Singila", "help": "Ga na", "welcome": "Baraa"},
    "lu": {"hello": "Twasakidila", "goodbye": "Nkongenu", "thank_you": "Tatubula", "help": "Tusadi", "welcome": "Tukusanyine"},
    "fan": {"hello": "Mbolo", "goodbye": "Akiba", "thank_you": "Akiba", "help": "Yeege", "welcome": "Woro"},
    # ---- Global ----
    "en": {"hello": "Hello", "goodbye": "Goodbye", "thank_you": "Thank you", "help": "Help", "welcome": "Welcome"},
    "es": {"hello": "Hola", "goodbye": "Adiós", "thank_you": "Gracias", "help": "Ayuda", "welcome": "Bienvenido"},
    "fr": {"hello": "Bonjour", "goodbye": "Au revoir", "thank_you": "Merci", "help": "Aide", "welcome": "Bienvenue"},
    "pt": {"hello": "Olá", "goodbye": "Adeus", "thank_you": "Obrigado", "help": "Ajuda", "welcome": "Bem-vindo"},
    "zh": {"hello": "你好", "goodbye": "再见", "thank_you": "谢谢", "help": "帮助", "welcome": "欢迎"},
    "hi": {"hello": "नमस्ते", "goodbye": "अलविदा", "thank_you": "धन्यवाद", "help": "मदद", "welcome": "स्वागत"},
    "ar": {"hello": "As-salamu alaykum", "goodbye": "Ma'a salama", "thank_you": "Shukran", "help": "Musaa'da", "welcome": "Ahlan wa sahlan"},
    "de": {"hello": "Hallo", "goodbye": "Auf Wiedersehen", "thank_you": "Danke", "help": "Hilfe", "welcome": "Willkommen"},
    "ja": {"hello": "こんにちは", "goodbye": "さようなら", "thank_you": "ありがとう", "help": "助け", "welcome": "ようこそ"},
    "ko": {"hello": "안녕하세요", "goodbye": "안녕히 가세요", "thank_you": "감사합니다", "help": "도움", "welcome": "환영합니다"},
    "ru": {"hello": "Привет", "goodbye": "До свидания", "thank_you": "Спасибо", "help": "Помощь", "welcome": "Добро пожаловать"},
    "tr": {"hello": "Merhaba", "goodbye": "Hoşçakal", "thank_you": "Teşekkürler", "help": "Yardım", "welcome": "Hoş geldiniz"},
    "vi": {"hello": "Xin chào", "goodbye": "Tạm biệt", "thank_you": "Cảm ơn", "help": "Giúp đỡ", "welcome": "Chào mừng"},
    "th": {"hello": "สวัสดี", "goodbye": "ลาก่อน", "thank_you": "ขอบคุณ", "help": "ความช่วยเหลือ", "welcome": "ยินดีต้อนรับ"},
    "fa": {"hello": "سلام", "goodbye": "خداحافظ", "thank_you": "متشکرم", "help": "کمک", "welcome": "خوش آمدید"},
    "ur": {"hello": "As-salamu alaykum", "goodbye": "Allah hafiz", "thank_you": "Shukriya", "help": "Madad", "welcome": "Khush amdeed"},
    "id": {"hello": "Halo", "goodbye": "Selamat tinggal", "thank_you": "Terima kasih", "help": "Bantuan", "welcome": "Selamat datang"},
    "he": {"hello": "שלום", "goodbye": "להתראות", "thank_you": "תודה", "help": "עזרה", "welcome": "ברוך הבא"},
    "ta": {"hello": "வணக்கம்", "goodbye": "விடைபெறுகிறேன்", "thank_you": "நன்றி", "help": "உதவி", "welcome": "வரவேற்கிறேன்"},
    "te": {"hello": "నమస్కారం", "goodbye": "వీడ్కోలు", "thank_you": "ధన్యవాదాలు", "help": "సహాయం", "welcome": "స్వాగతం"},
    "bn": {"hello": "হ্যালো", "goodbye": "বিদায়", "thank_you": "ধন্যবাদ", "help": "সাহায্য", "welcome": "স্বাগতম"},
    "pa": {"hello": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "goodbye": "ਰੱਖਿਆ", "thank_you": "ਧੰਨਵਾਦ", "help": "ਮਦਦ", "welcome": "ਜੀ ਆਇਆ ਨੂੰ"},
}


# =============================================================================
# UNICODE SCRIPT RANGES
# =============================================================================

SCRIPT_RANGES: Dict[str, Tuple[int, int]] = {
    "ethiopic": (0x1200, 0x137F),
    "tifinagh": (0x2D30, 0x2D7F),
    "arabic": (0x0600, 0x06FF),
    "devanagari": (0x0900, 0x097F),
    "cyrillic": (0x0400, 0x04FF),
    "cjk": (0x4E00, 0x9FFF),
    "hiragana": (0x3040, 0x309F),
    "katakana": (0x30A0, 0x30FF),
    "hangul": (0xAC00, 0xD7AF),
    "hebrew": (0x0590, 0x05FF),
    "thai": (0x0E00, 0x0E7F),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "bengali": (0x0980, 0x09FF),
    "gurmukhi": (0x0A00, 0x0A7F),
}


# =============================================================================
# LANGUAGE PATTERNS
# =============================================================================

LANGUAGE_PATTERNS: Dict[str, List[str]] = {
    # East African
    "sw": ["habari", "jambo", "asante", "karibu", "rafiki", "mzuri", "sijui"],
    "rw": ["muraho", "amakuru", "murakoze", "yego", "oya"],
    "rn": ["amahoro", "waraye", "urakaza"],
    "so": ["walaal", "mahadsanid", "waan ku fahmay", "ma nabad baa"],
    "am": ["selam", "ameseginalehu", "ende", "tinish"],
    "ti": ["selam", "yekeniyeley", "dehan", "tinish"],
    "om": ["akkam", "galatoomi", "nagaa", "jirta"],
    "lg": ["wasuze", "webale", "gyebaleko", "ssebo", "nyabo"],
    "mg": ["manaona", "misaotra", "salama", "tsara"],
    # West African
    "yo": ["bawo", "oṣeun", "ẹ kú", "ọ̀wọ̀", "mo ṣe"],
    "ig": ["nnọọ", "daalụ", "kedu", "ọ dị", "imela"],
    "ha": ["sannu", "na gode", "lafiya", "sai", "ina kwana"],
    "ff": ["jaaraama", "on jaaraama", "yeddu"],
    "ak": ["mahama", "medaase", "wo ho te", "ɛte"],
    "ee": ["woezon", "maduu", "meɖekuku"],
    "wo": ["jërëjëf", "nanga def", "man deh"],
    "bm": ["i ni ce", "a ni ce", "tɔgɔ"],
    "mos": ["lafi barka", "yamb na"],
    "fon": ["alafia", "ahouanu", "kêdenu"],
    # Southern African
    "zu": ["sawubona", "ngiyabonga", "kunjani", "yebo", "cha"],
    "xh": ["molo", "enkosi", "unjani", "ewe", "hayi"],
    "af": ["hallo", "dankie", "totsiens", "ja", "nee"],
    "st": ["dumela", "ke a leboha", "o kae", "e", "tjhe"],
    "tn": ["dumela", "ke a leboga", "o tsogile", "e", "nyaa"],
    "sn": ["mhoroi", "ndatenda", "makadii", "ehe", "kwete"],
    "nd": ["salibonani", "siyabonga", "unjani"],
    "ny": ["moni", "zikomo", "muli bwanji", "inde", "ayi"],
    # North African
    "ar-eg": ["مرحبا", "شكرا", "السلام", "كيف", "نعم"],
    "ary": ["سلام", "شكرا", "بسلامة", "واخا", "لّا"],
    "kab": ["azul", "tanmirt", "lla", "ih", "ala"],
    "shi": ["manzak", "tanmirt", "yah", "oho"],
    # Central African
    "ln": ["mbote", "matondo", "malamu", "ee", "te"],
    "kg": ["kiao", "ntondu", "malamu", "ee", "vé"],
    "sg": ["baraa", "singila", "nzoni", "ango"],
    "lu": ["twasakidila", "tatubula", "bua musakidila"],
    "fan": ["mbolo", "y'akiba", "papa"],
    # Global
    "en": ["hello", "thank", "please", "sorry", "good"],
    "es": ["hola", "gracias", "por favor", "buenos", "sí"],
    "fr": ["bonjour", "merci", "s'il vous plaît", "au revoir", "oui"],
    "pt": ["olá", "obrigado", "por favor", "sim", "não"],
    "de": ["hallo", "danke", "bitte", "guten", "ja"],
    "ru": ["привет", "спасибо", "пожалуйста", "да", "нет"],
    "zh": ["你好", "谢谢", "请", "对不起", "是的"],
    "ja": ["こんにちは", "ありがとう", "すみません", "はい"],
    "ko": ["안녕하세요", "감사합니다", "죄송합니다", "네"],
    "hi": ["नमस्ते", "धन्यवाद", "कृपया", "हाँ"],
    "ar": ["مرحبا", "شكرا", "من فضلك", "نعم"],
    "tr": ["merhaba", "teşekkürler", "lütfen", "evet"],
    "vi": ["xin chào", "cảm ơn", "làm ơn", "vâng"],
    "th": ["สวัสดี", "ขอบคุณ", "กรุณา", "ใช่"],
    "he": ["שלום", "תודה", "בבקשה", "כן"],
}


# =============================================================================
# N-GRAM LANGUAGE MARKERS
# =============================================================================

NGRAM_MARKERS: Dict[str, Set[str]] = {
    # African click languages
    "xh": {"xho", "pho", "bha", "nya", "ci", "qa", "gq", "ngq"},
    "zu": {"zul", "ngu", "ngi", "siy", "uku", "uma", "kwa", "ezi"},
    "nd": {"nde", "nga", "siy", "uku", "kwa"},
    # Bantu languages
    "sw": {"swa", "hili", "zuri", "moja", "mbili", "nne", "tano"},
    "rw": {"kir", "rwand", "mwari", "mugabo", "yego"},
    "lg": {"lug", "gamba", "mukwano", "ssebo", "nyabo"},
    "yo": {"yor", "ọmọ", "ilẹ̀", "tí", "ní", "sí"},
    "ig": {"igb", "chukwu", "biko", "kedu", "nne", "nna"},
    "ha": {"hau", "alla", "ina", "lafiya", "sannu", "yau"},
    "ak": {"akan", "abusi", "obaatan", "agya", "mmr"},
    "ln": {"ling", "bato", "mokili", "mingi", "mbala"},
    # Semitic
    "am": {"amha", "bet", "alem", "selam", "and", "yeh"},
    "ti": {"tigr", "selam", "ab", "te", "ti"},
    "ar-eg": {"masr", "ahl", "balad", "kida", "basha"},
    # Global
    "en": {"the", "and", "ing", "tion", "that"},
    "es": {"ción", "ando", "iento", " está", "para"},
    "fr": {"tion", "ement", "pour", "dans", "avec"},
    "pt": {"ção", "ando", "ento", "para", "como"},
    "de": {"ung", "lich", "keit", "für", "und"},
    "ru": {"tion", "stv", "kat", "для", "что"},
}


# =============================================================================
# CHARACTER FREQUENCY MARKERS
# =============================================================================

CHAR_MARKERS: Dict[str, Set[str]] = {
    "xh": {"q", "x", "c"},  # click consonants
    "zu": {"q", "x"},
    "yo": {"ọ", "ẹ", "ṣ", "à", "á", "è", "é", "ì", "í", "ò", "ó", "ù", "ú"},
    "ig": {"ị", "ụ", "ḅ", "ṅ", "ṣ"},
    "ha": {"ɗ", "ƙ", "ts", "sh"},
    "ak": {"ɛ", "ɔ", "ng", "ny"},
    "ee": {"ɛ", "ɔ", "ɖ", "ƒ", "gb", "ŋ"},
    "wo": {"ñ", "ë", "à", "é", "ó"},
    "kab": {"ɛ", "ɣ", "ε", "ɣ", "ṭ", "ḍ"},
    "shi": {"ε", "ɣ", "ṭ", "č", "ǧ"},
    "mg": {"ñ", "ô", "ts", "ao"},
    "pt": {"ão", "ções", "lh", "nh"},
    "es": {"ñ", "ll", "rr", "ció", "ado"},
    "fr": {"ç", "œ", "î", "ê", "à", "ù"},
    "de": {"ß", "ä", "ö", "ü", "sch", "ch"},
}


# =============================================================================
# LANGUAGE DETECTOR CLASS
# =============================================================================

class LanguageDetector:
    """
    Multi-strategy language detector optimized for African languages.

    Uses a cascading detection pipeline:
    1. Greeting matching (fastest, most reliable)
    2. Unicode script analysis (script-based languages)
    3. Pattern matching (language-specific word patterns)
    4. N-gram analysis (statistical frequency)
    5. Character markers (unique characters)
    6. Default to English

    Attributes:
        supported_languages: Set of language codes that can be detected.
    """

    def __init__(self) -> None:
        """Initialize the language detector with all language data."""
        self.supported_languages: Set[str] = set(LANGUAGE_GREETINGS.keys())
        self._build_greeting_index()

    def _build_greeting_index(self) -> None:
        """Build a reverse index from greeting words to language codes."""
        self._greeting_index: Dict[str, str] = {}
        for lang_code, greetings in LANGUAGE_GREETINGS.items():
            for greeting_type, greeting_text in greetings.items():
                # Index by lowercase greeting
                self._greeting_index[greeting_text.lower()] = lang_code
                # Also index first word
                first_word = greeting_text.split()[0].lower()
                if len(first_word) > 2:
                    self._greeting_index[first_word] = lang_code

    def detect(self, text: str) -> str:
        """
        Detect the language of the given text.

        Uses cascading detection strategies for maximum accuracy.

        Args:
            text: Input text to analyze.

        Returns:
            ISO language code (e.g., 'sw', 'en', 'zu').
        """
        if not text or not text.strip():
            return "en"

        normalized = text.lower().strip()

        # 1. Fast greeting detection
        greeting_lang = self._detect_by_greeting(normalized)
        if greeting_lang:
            return greeting_lang

        # 2. Unicode script analysis
        script_lang = self._detect_by_script(normalized)
        if script_lang:
            return script_lang

        # 3. Language-specific n-gram patterns
        pattern_lang = self._detect_by_patterns(normalized)
        if pattern_lang:
            return pattern_lang

        # 4. Check for common language markers
        marker_lang = self._detect_by_markers(normalized)
        if marker_lang:
            return marker_lang

        # 5. Default to English
        return "en"

    def detect_greeting(self, text: str) -> str:
        """
        Detect if text is a greeting and return the language code.

        Args:
            text: Input text to analyze.

        Returns:
            Language code if greeting detected, empty string otherwise.
        """
        if not text:
            return ""

        normalized = text.lower().strip()

        # Check for common greeting patterns
        greeting_patterns = {
            "sw": ["jambo", "habari", "hujambo", "sijambo", "shikamoo", "vipi", "mambo"],
            "rw": ["muraho", "mwiriwe", "bite", "amakuru", "yego"],
            "rn": ["amahoro", "waraye", "bite", "urakaza"],
            "so": ["ma nabad baa", "iska waran", "galab wanaagsan"],
            "am": ["selam", "tena yistilign", "dena weter"],
            "ti": ["selam", "kemey alika", "teweli alika"],
            "om": ["akkam", "nagaa", "akkam bultan", "akkam ooltan"],
            "lg": ["oli otya", "wasuze otya", "webale", "sula bulungi"],
            "mg": ["manaona", "manaona ahoana", "akory", "salama"],
            "yo": ["bawo ni", "ẹ kú àárọ", "ẹ kú irọlẹ", "nnkan sowapo"],
            "ig": ["nnọọ", "kedụ", "ị salụ", "kedụ ụzọ"],
            "ha": ["sannu", "ina kwana", "ina wuni", "ina yini", "barka da rana"],
            "ff": ["jaaraama", "on jaaraama", "jaabama"],
            "ak": ["mahama", "agoo", "me ma wo akye", "me ma wo hye"],
            "ee": ["woezon", "yoo", "neka", "nde"],
            "wo": ["nanga def", "jàmm nga", "jaam rek"],
            "bm": ["i ni ce", "i ni sogoma", "i ni tilebaw", "a ni ce"],
            "mos": ["lafi barka", "lafi zabre"],
            "fon": ["alafia", "alafia le", "kêdenu"],
            "zu": ["sawubona", "sanibonani", "yebo sawubona", "unjani"],
            "xh": ["molo", "molweni", "unjani", "encode", "uxolo"],
            "af": ["hallo", "goeie more", "goeie naand", "haai"],
            "st": ["dumela", "lumela", "o kae", "dumelang"],
            "tn": ["dumela", "o tsogile jang", "dumelang"],
            "sn": ["mhoroi", "mhoro", "mamukasei", "masikati"],
            "nd": ["salibonani", "livukile", "lotjhani"],
            "ny": ["moni", "muli bwanji", "mukuwelu"],
            "ar-eg": ["مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", "أهلا"],
            "ary": ["سلام", "صباح", "msa l-khir", "ahlan"],
            "kab": ["azul", "azul fell-awen", "seggem"],
            "shi": ["manzak", "bazar", "tifawt"],
            "ln": ["mbote", "mbote na bino", "bondjo"],
            "kg": ["kiao", "ku me kio", "malafu"],
            "sg": ["baraa", "bara ti mo"],
            "lu": ["twasakidila", "wa mukelenu"],
            "fan": ["mbolo", "mbolo mimb"],
            "en": ["hello", "hi", "good morning", "good afternoon", "good evening", "hey"],
            "es": ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal"],
            "fr": ["bonjour", "salut", "bonsoir", "bonne nuit", "allô"],
            "pt": ["olá", "bom dia", "boa tarde", "boa noite", "oi"],
            "de": ["hallo", "guten morgen", "guten tag", "guten abend", "grüß dich"],
            "ru": ["привет", "здравствуйте", "доброе утро", "добрый день"],
            "zh": ["你好", "早上好", "下午好", "晚上好", "您好"],
            "ja": ["こんにちは", "おはよう", "こんばんは", "やあ"],
            "ko": ["안녕하세요", "안녕", "좋은 아침"],
            "hi": ["नमस्ते", "नमस्कार", "सुप्रभात", "शुभ संध्या"],
            "ar": ["مرحبا", "السلام عليكم", "صباح الخير", "أهلا وسهلا"],
            "tr": ["merhaba", "selam", "günaydın", "iyi akşamlar"],
            "vi": ["xin chào", "chào", "chào buổi sáng", "chào buổi tối"],
            "th": ["สวัสดี", "สวัสดีครับ", "สวัสดีค่ะ", "หวัดดี"],
            "he": ["שלום", "בוקר טוב", "ערב טוב", "היי"],
        }

        for lang_code, patterns in greeting_patterns.items():
            for pattern in patterns:
                if pattern in normalized:
                    return lang_code
        return ""

    def _detect_by_greeting(self, text: str) -> str:
        """Detect language by matching greeting words."""
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            if word in self._greeting_index:
                return self._greeting_index[word]
        return ""

    def _detect_by_script(self, text: str) -> str:
        """Detect language by unicode script analysis."""
        for char in text:
            cp = ord(char)
            for script, (start, end) in SCRIPT_RANGES.items():
                if start <= cp <= end:
                    if script == "ethiopic":
                        return "am"
                    elif script == "tifinagh":
                        return "kab"
                    elif script == "arabic":
                        return "ar-eg"
                    elif script == "devanagari":
                        return "hi"
                    elif script == "cyrillic":
                        return "ru"
                    elif script == "cjk":
                        return "zh"
                    elif script == "hiragana":
                        return "ja"
                    elif script == "katakana":
                        return "ja"
                    elif script == "hangul":
                        return "ko"
                    elif script == "hebrew":
                        return "he"
                    elif script == "thai":
                        return "th"
                    elif script == "tamil":
                        return "ta"
                    elif script == "telugu":
                        return "te"
                    elif script == "bengali":
                        return "bn"
        return ""

    def _detect_by_patterns(self, text: str) -> str:
        """Detect language by word pattern matching."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for lang_code, patterns in LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern in text_lower:
                    score += 1
            if score > 0:
                scores[lang_code] = score

        if scores:
            # Return the language with the highest score
            return max(scores, key=scores.get)
        return ""

    def _detect_by_markers(self, text: str) -> str:
        """Detect language by unique character markers."""
        scores: Dict[str, int] = {}

        for lang_code, markers in CHAR_MARKERS.items():
            score = 0
            for marker in markers:
                if marker in text.lower():
                    score += 1
            if score > 0:
                scores[lang_code] = score

        if scores:
            return max(scores, key=scores.get)
        return ""

    def format_greeting(self, lang_code: str) -> str:
        """
        Get a greeting in the specified language.

        Args:
            lang_code: ISO language code.

        Returns:
            Greeting string in the target language.
        """
        greetings = LANGUAGE_GREETINGS.get(lang_code, LANGUAGE_GREETINGS["en"])
        return greetings.get("hello", "Hello")

    def is_african(self, lang_code: str) -> bool:
        """
        Check if a language is African.

        Args:
            lang_code: ISO language code.

        Returns:
            True if African language.
        """
        african_codes = {
            "sw", "rw", "rn", "so", "am", "ti", "om", "lg", "mg",
            "yo", "ig", "ha", "ff", "ak", "ee", "wo", "bm", "mos", "fon",
            "zu", "xh", "af", "st", "tn", "sn", "nd", "ny",
            "ar-eg", "ary", "kab", "shi",
            "ln", "kg", "sg", "lu", "fan",
        }
        return lang_code in african_codes

    def get_fallback_chain(self, lang_code: str) -> List[str]:
        """
        Get a fallback chain for a language.

        When a language has limited AI support, this provides
        alternative languages that the user might understand.

        Args:
            lang_code: ISO language code.

        Returns:
            List of fallback language codes.
        """
        fallback_map = {
            # East Africa
            "rw": ["rw", "sw", "fr", "en"],
            "rn": ["rn", "sw", "fr", "en"],
            "so": ["so", "ar", "sw", "en"],
            "ti": ["ti", "am", "en"],
            "om": ["om", "am", "sw", "en"],
            "lg": ["lg", "sw", "en"],
            "mg": ["mg", "fr", "en"],
            # West Africa
            "ff": ["ff", "ha", "fr", "en"],
            "ee": ["ee", "ak", "en"],
            "wo": ["wo", "fr", "en"],
            "bm": ["bm", "fr", "en"],
            "mos": ["mos", "fr", "en"],
            "fon": ["fon", "fr", "en"],
            # Southern Africa
            "af": ["af", "en", "zu"],
            "st": ["st", "zu", "en"],
            "tn": ["tn", "zu", "en"],
            "sn": ["sn", "zu", "en"],
            "nd": ["nd", "zu", "en"],
            "ny": ["ny", "sw", "en"],
            # North Africa
            "ar-eg": ["ar-eg", "ar", "en"],
            "ary": ["ary", "ar", "fr", "en"],
            "kab": ["kab", "ary", "fr", "ar", "en"],
            "shi": ["shi", "ary", "fr", "ar", "en"],
            # Central Africa
            "ln": ["ln", "fr", "sw", "en"],
            "kg": ["kg", "pt", "fr", "en"],
            "sg": ["sg", "fr", "en"],
            "lu": ["lu", "fr", "sw", "en"],
            "fan": ["fan", "fr", "es", "en"],
            # Default
            "default": [lang_code, "en"],
        }
        return fallback_map.get(lang_code, [lang_code, "en"])

    def get_response_language(self, lang_code: str) -> str:
        """
        Determine the best language to respond in.

        For languages with good GPT support, respond directly.
        For others, provide a fallback suggestion.

        Args:
            lang_code: Detected language code.

        Returns:
            Recommended response language code.
        """
        # Languages with good direct support
        direct_support = {
            "en", "sw", "yo", "ig", "ha", "zu", "xh", "am", "so",
            "ar", "ar-eg", "fr", "es", "pt", "zh", "hi", "ja", "ko",
            "de", "ru", "tr", "vi", "th", "he", "id", "ta", "te", "bn", "pa",
        }

        if lang_code in direct_support:
            return lang_code

        # Use fallback chain
        fallback = self.get_fallback_chain(lang_code)
        for fc in fallback:
            if fc in direct_support:
                return fc

        return "en"

    def get_language_name(self, lang_code: str, english: bool = False) -> str:
        """
        Get the name of a language.

        Args:
            lang_code: ISO language code.
            english: If True, return English name.

        Returns:
            Language name string.
        """
        names = {
            "sw": ("Kiswahili", "Swahili"),
            "rw": ("Ikinyarwanda", "Kinyarwanda"),
            "rn": ("Ikirundi", "Kirundi"),
            "so": ("Af-Soomaali", "Somali"),
            "am": ("አማርኛ", "Amharic"),
            "ti": ("ትግርኛ", "Tigrinya"),
            "om": ("Afaan Oromoo", "Oromo"),
            "lg": ("Luganda", "Luganda"),
            "mg": ("Malagasy", "Malagasy"),
            "yo": ("Yorùbá", "Yoruba"),
            "ig": ("Igbo", "Igbo"),
            "ha": ("Hausa", "Hausa"),
            "ff": ("Fulfulde", "Fulfulde"),
            "ak": ("Akan", "Akan"),
            "ee": ("Eʋegbe", "Ewe"),
            "wo": ("Wolof", "Wolof"),
            "bm": ("Bamanankan", "Bambara"),
            "mos": ("Mooré", "Mossi"),
            "fon": ("Fon", "Fon"),
            "zu": ("isiZulu", "Zulu"),
            "xh": ("isiXhosa", "Xhosa"),
            "af": ("Afrikaans", "Afrikaans"),
            "st": ("Sesotho", "Sesotho"),
            "tn": ("Setswana", "Tswana"),
            "sn": ("chiShona", "Shona"),
            "nd": ("isiNdebele", "Ndebele"),
            "ny": ("Chichewa", "Chewa"),
            "ar-eg": ("العربية المصرية", "Egyptian Arabic"),
            "ary": ("الدارجة", "Moroccan Arabic"),
            "kab": ("Taqbaylit", "Kabyle"),
            "shi": ("Tashelhit", "Tashelhit"),
            "ln": ("Lingála", "Lingala"),
            "kg": ("Kikongo", "Kikongo"),
            "sg": ("Sängö", "Sango"),
            "lu": ("Tshiluba", "Luba"),
            "fan": ("Faŋ", "Fang"),
            "en": ("English", "English"),
            "es": ("Español", "Spanish"),
            "fr": ("Français", "French"),
            "pt": ("Português", "Portuguese"),
            "zh": ("中文", "Chinese"),
            "hi": ("हिन्दी", "Hindi"),
            "ar": ("العربية", "Arabic"),
            "de": ("Deutsch", "German"),
            "ja": ("日本語", "Japanese"),
            "ko": ("한국어", "Korean"),
            "ru": ("Русский", "Russian"),
            "tr": ("Türkçe", "Turkish"),
            "vi": ("Tiếng Việt", "Vietnamese"),
            "th": ("ไทย", "Thai"),
            "he": ("עברית", "Hebrew"),
            "fa": ("فارسی", "Persian"),
            "ur": ("اردو", "Urdu"),
            "id": ("Bahasa Indonesia", "Indonesian"),
            "ta": ("தமிழ்", "Tamil"),
            "te": ("తెలుగు", "Telugu"),
            "bn": ("বাংলা", "Bengali"),
            "pa": ("ਪੰਜਾਬੀ", "Punjabi"),
        }

        native, eng = names.get(lang_code, (lang_code, lang_code))
        return eng if english else native

    def detect_with_confidence(self, text: str) -> Tuple[str, float]:
        """
        Detect language and return confidence score.

        Args:
            text: Input text to analyze.

        Returns:
            Tuple of (language_code, confidence_score).
        """
        lang = self.detect(text)

        # Estimate confidence based on detection method
        normalized = text.lower().strip()

        # High confidence: greeting match
        if self._detect_by_greeting(normalized):
            return lang, 0.95

        # High confidence: script match
        if self._detect_by_script(normalized):
            return lang, 0.90

        # Medium confidence: pattern match
        if self._detect_by_patterns(normalized):
            return lang, 0.75

        # Lower confidence: marker match
        if self._detect_by_markers(normalized):
            return lang, 0.60

        # Lowest: default
        return lang, 0.30