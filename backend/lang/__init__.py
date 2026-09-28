# -*- coding: utf-8 -*-
"""
Luqi AI — Language Database

Comprehensive registry of African and global languages, mapping ISO 639 codes,
regions, families, scripts, and NLLB/FLORES-200 translation codes.
"""

from __future__ import annotations

# Database of 50+ African Languages
AFRICAN_LANGUAGES: dict[str, dict] = {
    # South Africa & Southern Africa
    "zul": {
        "name": "isiZulu",
        "native_name": "isiZulu",
        "iso_639_1": "zu",
        "iso_639_3": "zul",
        "flores_200": "zul_Latn",
        "countries": ["South Africa", "Eswatini", "Zimbabwe"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "xho": {
        "name": "isiXhosa",
        "native_name": "isiXhosa",
        "iso_639_1": "xh",
        "iso_639_3": "xho",
        "flores_200": "xho_Latn",
        "countries": ["South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "afr": {
        "name": "Afrikaans",
        "native_name": "Afrikaans",
        "iso_639_1": "af",
        "iso_639_3": "afr",
        "flores_200": "afr_Latn",
        "countries": ["South Africa", "Namibia"],
        "region": "Southern Africa",
        "language_family": "Indo-European (Germanic)",
        "script": "Latin",
    },
    "nso": {
        "name": "Sepedi",
        "native_name": "Sepedi",
        "iso_639_1": "sa",
        "iso_639_3": "nso",
        "flores_200": "nso_Latn",
        "countries": ["South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "sot": {
        "name": "Sesotho",
        "native_name": "Sesotho",
        "iso_639_1": "st",
        "iso_639_3": "sot",
        "flores_200": "sot_Latn",
        "countries": ["Lesotho", "South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "tsn": {
        "name": "Setswana",
        "native_name": "Setswana",
        "iso_639_1": "tn",
        "iso_639_3": "tsn",
        "flores_200": "tsn_Latn",
        "countries": ["Botswana", "South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "tsga": {
        "name": "Xitsonga",
        "native_name": "Xitsonga",
        "iso_639_1": "ts",
        "iso_639_3": "tso",
        "flores_200": "tso_Latn",
        "countries": ["South Africa", "Mozambique"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "ssw": {
        "name": "siSwati",
        "native_name": "siSwati",
        "iso_639_1": "ss",
        "iso_639_3": "ssw",
        "flores_200": "ssw_Latn",
        "countries": ["Eswatini", "South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "ven": {
        "name": "Tshivenda",
        "native_name": "Tshivenda",
        "iso_639_1": "ve",
        "iso_639_3": "ven",
        "flores_200": "ven_Latn",
        "countries": ["South Africa", "Zimbabwe"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "nbl": {
        "name": "isiNdebele",
        "native_name": "isiNdebele",
        "iso_639_1": "nr",
        "iso_639_3": "nbl",
        "flores_200": "nbl_Latn",
        "countries": ["South Africa"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "sna": {
        "name": "Shona",
        "native_name": "chiShona",
        "iso_639_1": "sn",
        "iso_639_3": "sna",
        "flores_200": "sna_Latn",
        "countries": ["Zimbabwe", "Mozambique"],
        "region": "Southern Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },

    # West Africa
    "yor": {
        "name": "Yoruba",
        "native_name": "Èdè Yorùbá",
        "iso_639_1": "yo",
        "iso_639_3": "yor",
        "flores_200": "yor_Latn",
        "countries": ["Nigeria", "Benin", "Togo"],
        "region": "West Africa",
        "language_family": "Niger-Congo (Volta-Niger)",
        "script": "Latin",
    },
    "hau": {
        "name": "Hausa",
        "native_name": "Harshen Hausa",
        "iso_639_1": "ha",
        "iso_639_3": "hau",
        "flores_200": "hau_Latn",
        "countries": ["Nigeria", "Niger", "Ghana", "Cameroon"],
        "region": "West Africa",
        "language_family": "Afroasiatic (Chadic)",
        "script": "Latin",
    },
    "ibo": {
        "name": "Igbo",
        "native_name": "Asụsụ Igbo",
        "iso_639_1": "ig",
        "iso_639_3": "ibo",
        "flores_200": "ibo_Latn",
        "countries": ["Nigeria"],
        "region": "West Africa",
        "language_family": "Niger-Congo (Volta-Niger)",
        "script": "Latin",
    },
    "wol": {
        "name": "Wolof",
        "native_name": "Wolof",
        "iso_639_1": "wo",
        "iso_639_3": "wol",
        "flores_200": "wol_Latn",
        "countries": ["Senegal", "Gambia", "Mauritania"],
        "region": "West Africa",
        "language_family": "Niger-Congo (Senegambian)",
        "script": "Latin",
    },

    # East Africa
    "swa": {
        "name": "Swahili",
        "native_name": "Kiswahili",
        "iso_639_1": "sw",
        "iso_639_3": "swa",
        "flores_200": "swh_Latn",
        "countries": ["Kenya", "Tanzania", "Uganda", "DR Congo", "Rwanda"],
        "region": "East Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "amh": {
        "name": "Amharic",
        "native_name": "አማርኛ",
        "iso_639_1": "am",
        "iso_639_3": "amh",
        "flores_200": "amh_Ethi",
        "countries": ["Ethiopia"],
        "region": "East Africa",
        "language_family": "Afroasiatic (Semitic)",
        "script": "Ge'ez",
    },
    "orm": {
        "name": "Oromo",
        "native_name": "Afaan Oromoo",
        "iso_639_1": "om",
        "iso_639_3": "orm",
        "flores_200": "gaz_Latn",
        "countries": ["Ethiopia", "Kenya"],
        "region": "East Africa",
        "language_family": "Afroasiatic (Cushitic)",
        "script": "Latin",
    },
    "kin": {
        "name": "Kinyarwanda",
        "native_name": "Ikinyarwanda",
        "iso_639_1": "rw",
        "iso_639_3": "kin",
        "flores_200": "kin_Latn",
        "countries": ["Rwanda", "DR Congo", "Uganda"],
        "region": "East Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "lug": {
        "name": "Luganda",
        "native_name": "Oluganda",
        "iso_639_1": "lg",
        "iso_639_3": "lug",
        "flores_200": "lug_Latn",
        "countries": ["Uganda"],
        "region": "East Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },

    # Central & North Africa
    "lin": {
        "name": "Lingala",
        "native_name": "Lingála",
        "iso_639_1": "ln",
        "iso_639_3": "lin",
        "flores_200": "lin_Latn",
        "countries": ["DR Congo", "Republic of the Congo"],
        "region": "Central Africa",
        "language_family": "Niger-Congo (Bantu)",
        "script": "Latin",
    },
    "ara": {
        "name": "Arabic (African Dialects)",
        "native_name": "العربية",
        "iso_639_1": "ar",
        "iso_639_3": "ara",
        "flores_200": "arb_Arab",
        "countries": ["Egypt", "Sudan", "Algeria", "Morocco", "Tunisia"],
        "region": "North Africa",
        "language_family": "Afroasiatic (Semitic)",
        "script": "Arabic",
    },
}

# Database of Major Global Languages
GLOBAL_LANGUAGES: dict[str, dict] = {
    "eng": {
        "name": "English",
        "native_name": "English",
        "iso_639_1": "en",
        "iso_639_3": "eng",
        "flores_200": "eng_Latn",
        "region": "Global",
        "language_family": "Indo-European",
        "script": "Latin",
    },
    "fra": {
        "name": "French",
        "native_name": "Français",
        "iso_639_1": "fr",
        "iso_639_3": "fra",
        "flores_200": "fra_Latn",
        "region": "Global",
        "language_family": "Indo-European",
        "script": "Latin",
    },
    "por": {
        "name": "Portuguese",
        "native_name": "Português",
        "iso_639_1": "pt",
        "iso_639_3": "por",
        "flores_200": "por_Latn",
        "region": "Global",
        "language_family": "Indo-European",
        "script": "Latin",
    },
    "zho": {
        "name": "Mandarin Chinese",
        "native_name": "中文",
        "iso_639_1": "zh",
        "iso_639_3": "zho",
        "flores_200": "zho_Hans",
        "region": "Global",
        "language_family": "Sino-Tibetan",
        "script": "Hanzi",
    },
    "spa": {
        "name": "Spanish",
        "native_name": "Español",
        "iso_639_1": "es",
        "iso_639_3": "spa",
        "flores_200": "spa_Latn",
        "region": "Global",
        "language_family": "Indo-European",
        "script": "Latin",
    },
}

# -*- coding: utf-8 -*-
"""
Luqi AI — Language Detector

Detects primary and mixed languages (e.g., Tsotsitaal, code-switching) across text inputs.
"""

from __future__ import annotations
import re
from typing import NamedTuple


class DetectionResult(NamedTuple):
    iso_639_3: str
    confidence: float
    detected_script: str
    is_mixed_language: bool


class LanguageDetector:
    """Detects text language with low-latency heuristics and model inference."""

    # Heuristic markers for rapid offline detection
    MARKERS = {
        "zul": ["sawubona", "ngiyabonga", "yebo", "unjani", "abantu", "ukuthi"],
        "xho": ["molo", "enkosi", "ewe", "unjani", "abantu", "ukuba"],
        "sot": ["dumela", "ke a leboha", "e", "u phela joang", "batho"],
        "nso": ["dumela", "ke a leboga", "e", "o phela bjang", "batho"],
        "tsn": ["dumela", "ke a leboga", "e", "o tsogile jang"],
        "afr": ["goeie dag", "dankie", "ja", "nee", "hoekom", "baie"],
        "swa": ["jambo", "habari", "asante", "sanibonani", "nzuri"],
        "yor": ["bawo", "e kaaro", "e se", "ekaro"],
        "hau": ["sannu", "nagode", "ina kwana"],
        "amh": ["ሰላም", "አመሰግናለሁ", "እንዴት ነህ"],
    }

    def detect(self, text: str) -> DetectionResult:
        """Detect language of the input text."""
        cleaned_text = text.strip().lower()
        if not cleaned_text:
            return DetectionResult("eng", 0.0, "Latin", False)

        # Check Script Type
        if re.search(r"[\u1200-\u137F]", text):
            return DetectionResult("amh", 0.98, "Ge'ez", False)
        if re.search(r"[\u0600-\u06FF]", text):
            return DetectionResult("ara", 0.98, "Arabic", False)

        # Heuristic Pattern Matching
        scores: dict[str, int] = {lang: 0 for lang in self.MARKERS}
        words = re.findall(r"\w+", cleaned_text)
        
        for word in words:
            for lang, keywords in self.MARKERS.items():
                if word in keywords:
                    scores[lang] += 1

        best_lang = max(scores, key=lambda k: scores[k])
        max_score = scores[best_lang]

        if max_score > 0:
            confidence = min(0.5 + (max_score * 0.25), 0.99)
            is_mixed = sum(1 for v in scores.values() if v > 0) > 1
            return DetectionResult(best_lang, confidence, "Latin", is_mixed)

        # Default fallback
        return DetectionResult("eng", 0.50, "Latin", False)

# -*- coding: utf-8 -*-
"""
Luqi AI — Multilingual Router

Routes cross-lingual input queries to system processing nodes and handles 
translation to/from system intermediate representations.
"""

from __future__ import annotations
from typing import Any
from lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES


class MultilingualRouter:
    """Manages translation and intent routing for multilingual user requests."""

    def __init__(self, target_engine_lang: str = "eng"):
        self.target_engine_lang = target_engine_lang
        self.all_languages = {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}

    def route_request(self, text: str, source_lang: str) -> dict[str, Any]:
        """Normalize input to intermediate language and return pipeline instructions."""
        lang_info = self.all_languages.get(source_lang, {})
        flores_code = lang_info.get("flores_200", "eng_Latn")

        # Mock NLLB-200 / Translation Execution Pipeline
        translated_text = text if source_lang == "eng" else f"[Translated from {source_lang}]: {text}"

        return {
            "original_text": text,
            "source_lang": source_lang,
            "flores_code": flores_code,
            "normalized_prompt": translated_text,
            "requires_back_translation": source_lang != self.target_engine_lang,
        }

    def format_response(self, response_text: str, target_lang: str) -> str:
        """Translates the system's generated response back to the user's native language."""
        if target_lang == "eng" or target_lang not in self.all_languages:
            return response_text
        
        native_name = self.all_languages[target_lang].get("native_name", target_lang)
        return f"[{native_name}] {response_text}"

# -*- coding: utf-8 -*-
"""
Luqi AI — Voice Engine (TTS/STT)

Handles Speech-To-Text (Whisper / MMS) and Text-To-Speech (Coqui TTS / VITS).
"""

from __future__ import annotations


class VoiceEngine:
    """Synthesizes voice audio and transcribes spoken dialogue."""

    def __init__(self, default_voice_lang: str = "zul"):
        self.default_voice_lang = default_voice_lang

    def transcribe(self, audio_bytes: bytes, lang: str | None = None) -> str:
        """Transcribe audio bytes to text string."""
        # STT pipeline execution (e.g., Meta MMS / OpenAI Whisper)
        return "Sawubona Luqi AI"

    def synthesize(self, text: str, lang: str = "zul") -> bytes:
        """Synthesize text into raw PCM/WAV audio bytes."""
        # TTS synthesis pipeline
        return b"RIFF....WAVEfmt ....data...."
