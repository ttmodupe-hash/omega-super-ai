"""Omega AI v3 — Bilingual Response Wrapper
Adds African language translations to English responses.
"""
from __future__ import annotations

from typing import Dict


# Common phrases in major African languages
_PHRASES: Dict[str, Dict[str, str]] = {
    "zu": {
        "hello": "Sawubona", "goodbye": "Hamba kahle", "thank_you": "Ngiyabonga",
        "note": "Qaphela", "warning": "Isixwayiso", "disclaimer": "Chaza",
        "price": "Intengo", "alert": "Isaziso", "success": "Impumelelo",
        "error": "Iphutha", "yes": "Yebo", "no": "Cha", "loading": "Iyaloda", "done": "Kwenziwe",
    },
    "sw": {
        "hello": "Jambo", "goodbye": "Kwaheri", "thank_you": "Asante",
        "note": "Kumbuka", "warning": "Onyo", "disclaimer": "Tangazo",
        "price": "Bei", "alert": "Tahadhari", "success": "Mafanikio",
        "error": "Hitilafu", "yes": "Ndiyo", "no": "Hapana", "loading": "Inapakia", "done": "Imekamilika",
    },
    "yo": {
        "hello": "Bawo", "goodbye": "O dabọ", "thank_you": "O ṣeun",
        "note": "Akiyesi", "warning": "Ikilo", "disclaimer": "Aṣẹ",
        "price": "Iye", "alert": "Kilọ", "success": "Aṣeyọri",
        "error": "Aṣiṣe", "yes": "Bẹẹni", "no": "Rara", "loading": "Nṣiṣe", "done": "Ti ṣe",
    },
    "am": {
        "hello": "ሰላም", "goodbye": "ቻው", "thank_you": "አመሰግናለሁ",
        "note": "ማስታወሻ", "warning": "ማስጠንቀቂያ", "disclaimer": "ማብራሪያ",
        "price": "ዋጋ", "alert": "ማስጠንቀቂያ", "success": "ተሳክቷል",
        "error": "ስህተት", "yes": "አዎ", "no": "አይ", "loading": "በመጫን ላይ", "done": "ተከናውኗል",
    },
    "ha": {
        "hello": "Sannu", "goodbye": "Sai an jima", "thank_you": "Na gode",
        "note": "Lura", "warning": "Gargadi", "disclaimer": "Bayani",
        "price": "Farashi", "alert": "Faɗakarwa", "success": "Nasara",
        "error": "Kuskure", "yes": "Eh", "no": "A'a", "loading": "Ana loda", "done": "Anyi",
    },
    "ig": {
        "hello": "Nnọọ", "goodbye": "Ka ọ dị", "thank_you": "Daalụ",
        "note": "Mara", "warning": "Ịdọrọ ndụ", "disclaimer": "Nkọwa",
        "price": "Ọnụahịa", "alert": "Ịdọrọ ndụ", "success": "Ihe meziiri ọma",
        "error": "Njehie", "yes": "Ee", "no": "Mba", "loading": "Na-ebugo", "done": "Emela",
    },
}


class BilingualResponder:
    """Wrap English responses with African language translations."""

    def __init__(self, preferred_language: str = "en") -> None:
        self.lang = preferred_language.lower().strip()

    def is_bilingual_capable(self) -> bool:
        """Check if the set language has translation support."""
        return self.lang in _PHRASES

    def supported_languages(self) -> list[str]:
        """Return list of supported language codes."""
        return list(_PHRASES.keys())

    def wrap_response(self, english_text: str, module: str = "") -> str:
        """Add translation footer if language is supported."""
        if self.lang == "en" or self.lang not in _PHRASES:
            return english_text

        phrases = _PHRASES[self.lang]
        found = []
        text_lower = english_text.lower()

        for key, translation in phrases.items():
            if key.replace("_", " ") in text_lower or key.split("_")[0] in text_lower:
                found.append(f"  {key}: {translation}")

        if not found:
            return english_text

        lang_name = {"zu": "isiZulu", "sw": "Kiswahili", "yo": "Yoruba",
                     "am": "Amharic", "ha": "Hausa", "ig": "Igbo"}.get(self.lang, self.lang)

        footer = f"\n\n[{lang_name} quick reference:]\n" + "\n".join(found[:6])
        return english_text + footer

    def get_greeting(self) -> str:
        """Return greeting in target language."""
        if self.lang in _PHRASES:
            return _PHRASES[self.lang]["hello"]
        return "Hello"

    def get_farewell(self) -> str:
        if self.lang in _PHRASES:
            return _PHRASES[self.lang]["goodbye"]
        return "Goodbye"

    def get_thanks(self) -> str:
        if self.lang in _PHRASES:
            return _PHRASES[self.lang]["thank_you"]
        return "Thank you"

    def format_bilingual(self, english: str, translation: str, lang_name: str) -> str:
        """Format with English and translation block."""
        return f"{english}\n\n[{lang_name}]: {translation}"
