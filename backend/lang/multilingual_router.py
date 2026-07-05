# -*- coding: utf-8 -*-
"""
Luqi AI — Multilingual Response Router

Routes user queries to the appropriate language-aware pipeline.
Handles system prompt construction, cultural context injection,
translation coordination, and response formatting.

Usage:
    router = MultilingualRouter()
    result = router.route("Jambo! Habari yako?", "sw")
    print(result["system_prompt"])
"""

from __future__ import annotations

import os
from typing import Any, Optional

from backend.lang.african_languages import AFRICAN_LANGUAGES
try:
    from backend.lang.african_languages import GLOBAL_LANGUAGES
except ImportError:
    GLOBAL_LANGUAGES = {}

from backend.lang.language_detector import LanguageDetector


# =============================================================================
# CULTURAL CONTEXT DATABASE
# =============================================================================

CULTURAL_CONTEXTS: dict[str, str] = {
    # ---- East Africa ----
    "sw": (
        "You are speaking with a Swahili speaker from East Africa. "
        "Swahili is the lingua franca across Tanzania, Kenya, Uganda, Rwanda, "
        "Burundi, and DRC. Be respectful, use inclusive language, and understand "
        "that many speakers use Swahili as a second language. Family and community "
        "are highly valued. Islamic and Christian greetings may both be appropriate."
    ),
    "rw": (
        "You are speaking with a Kinyarwanda speaker from Rwanda. "
        "Post-1994 Rwanda emphasizes unity and reconciliation. "
        "Avoid ethnic references (Hutu/Tutsi/Twa). Use respectful, inclusive language. "
        "Family and community are central to Rwandan culture."
    ),
    "rn": (
        "You are speaking with a Kirundi speaker from Burundi. "
        "Be respectful and acknowledge the importance of community and social harmony."
    ),
    "am": (
        "You are speaking with an Amharic speaker from Ethiopia. "
        "Ethiopia has deep historical and religious traditions (Ethiopian Orthodox, "
        "Islam, Protestant). Age and elders are deeply respected. Use formal and "
        "respectful language. The Ethiopian calendar and timekeeping differ from Western systems."
    ),
    "ti": (
        "You are speaking with a Tigrinya speaker from Eritrea or Ethiopia. "
        "Be respectful of Eritrea's independence and distinct identity. "
        "Family and community ties are very strong."
    ),
    "so": (
        "You are speaking with a Somali speaker. "
        "Somali culture emphasizes clan identity, poetry, and oral tradition. "
        "Islam is central to daily life. Use respectful Islamic greetings when appropriate."
    ),
    "om": (
        "You are speaking with an Oromo speaker from Ethiopia or Kenya. "
        "Oromo culture values the Gadaa system (traditional democratic governance). "
        "Respect for elders and community decisions is important."
    ),
    "lg": (
        "You are speaking with a Luganda speaker from Uganda (Baganda people). "
        "The Buganda kingdom has a rich cultural heritage. "
        "Respect for hierarchy and elders is important."
    ),
    "mg": (
        "You are speaking with a Malagasy speaker from Madagascar. "
        "Malagasy culture has unique Austronesian and African roots. "
        "Ancestor veneration (razana) and family (fianakaviana) are central. "
        "Taboos (fady) vary by region and family."
    ),
    # ---- West Africa ----
    "yo": (
        "You are speaking with a Yoruba speaker, likely from Nigeria or Benin. "
        "Yoruba culture values respect for elders, proverbs, and rich artistic traditions. "
        "Islam and Christianity coexist with traditional beliefs (Ifa/Orisa). "
        "Greetings are elaborate and important."
    ),
    "ig": (
        "You are speaking with an Igbo speaker from Nigeria. "
        "Igbo culture values individual achievement, community (umunna), "
        "and hospitality. Christianity is predominant but traditional beliefs persist."
    ),
    "ha": (
        "You are speaking with a Hausa speaker from Nigeria, Niger, or neighboring countries. "
        "Hausa is a major West African lingua franca. Islam is central to Hausa culture. "
        "Use respectful language and be mindful of Islamic values and practices."
    ),
    "ff": (
        "You are speaking with a Fulfulde/Fula speaker from West Africa. "
        "Fulani culture traditionally centers on cattle herding (pulaaku - the Fulaniness). "
        "Islam is predominant. Respect for tradition and community is important."
    ),
    "ak": (
        "You are speaking with an Akan/Twi speaker from Ghana. "
        "Akan culture values respect for elders, extended family (abusua), "
        "and the Golden Stool tradition. Adinkra symbols carry deep meaning."
    ),
    "ee": (
        "You are speaking with an Ewe speaker from Ghana or Togo. "
        "Ewe culture has rich traditions in music (drumming), dance, and weaving (kente)."
    ),
    "wo": (
        "You are speaking with a Wolof speaker from Senegal, Gambia, or Mauritania. "
        "Wolof is the dominant language of Senegal. Islam ( Mouride brotherhood) is central. "
        "Teranga (hospitality) is a core cultural value."
    ),
    "bm": (
        "You are speaking with a Bambara speaker from Mali. "
        "Bambara culture values community decision-making (consensus), "
        "oral tradition, and griot heritage."
    ),
    "mos": (
        "You are speaking with a Moore speaker from Burkina Faso. "
        "Mossi society is organized around kingdoms with the Mogho Naba as the supreme chief."
    ),
    "fon": (
        "You are speaking with a Fon speaker from Benin. "
        "Fon people have deep Vodun (Voodoo) spiritual traditions "
        "alongside Christianity and Islam."
    ),
    # ---- Southern Africa ----
    "zu": (
        "You are speaking with a Zulu speaker from South Africa. "
        "Zulu is the most spoken home language in South Africa. "
        "Ubuntu (I am because we are) is a core philosophy. "
        "Respect for elders and ancestors is important."
    ),
    "xh": (
        "You are speaking with a Xhosa speaker from South Africa. "
        "Xhosa has distinctive click consonants. Ubuntu is central to the worldview. "
        "Respect for elders and communal decision-making are valued."
    ),
    "af": (
        "You are speaking with an Afrikaans speaker from South Africa or Namibia. "
        "Afrikaans has Dutch roots and is spoken across racial lines. "
        "Be sensitive to South Africa's complex linguistic and political history."
    ),
    "st": (
        "You are speaking with a Sesotho speaker from Lesotho or South Africa. "
        "Lesotho is the only country entirely surrounded by another (South Africa). "
        "Basotho culture values respect, community, and traditional blankets (Seanamarena)."
    ),
    "tn": (
        "You are speaking with a Setswana speaker from Botswana or South Africa. "
        "Botswana is known for stable democracy. Botho (respect and good manners) "
        "is a core cultural value."
    ),
    "sn": (
        "You are speaking with a Shona speaker from Zimbabwe. "
        "Shona culture values respect for elders, ancestors (vadzimu), "
        "and community. Christianity is widespread alongside traditional beliefs."
    ),
    "nd": (
        "You are speaking with a North Ndebele speaker from Zimbabwe. "
        "Ndebele culture has strong Zulu roots. Respect for royalty and tradition is important."
    ),
    "ny": (
        "You are speaking with a Chewa/Nyanja speaker from Malawi or Zambia. "
        "Chewa culture emphasizes community (umunthu) and respect for elders."
    ),
    # ---- North Africa ----
    "ar-eg": (
        "You are speaking with an Egyptian Arabic speaker. "
        "Egypt has a rich ancient civilization heritage. "
        "Islam and Christianity (Coptic) are both important. "
        "Use respectful language appropriate to the context."
    ),
    "ary": (
        "You are speaking with a Maghrebi Arabic (Darija) speaker from Morocco, Algeria, "
        "Tunisia, or Libya. Berber/Amazigh culture coexists with Arab culture. "
        "Islam is central to daily life. Use respectful greetings."
    ),
    "kab": (
        "You are speaking with a Kabyle/Berber (Amazigh) speaker from Algeria or North Africa. "
        "Berber culture is ancient and distinct. The Amazigh identity movement "
        "is important. Tifinagh script is used alongside Latin."
    ),
    "shi": (
        "You are speaking with a Tashelhit (Shilha) Berber speaker from Morocco. "
        "Tashelhit is one of the major Berber languages. "
        "Respect for Amazigh identity and culture is important."
    ),
    # ---- Central Africa ----
    "ln": (
        "You are speaking with a Lingala speaker from DRC or Congo-Brazzaville. "
        "Lingala is a major lingua franca in Kinshasa and across the two Congos. "
        "Music (soukous, rumba) is central to culture."
    ),
    "kg": (
        "You are speaking with a Kikongo speaker from DRC, Congo, or Angola. "
        "Kikongo has historical importance in the Kongo Kingdom."
    ),
    "sg": (
        "You are speaking with a Sango speaker from the Central African Republic. "
        "Sango is a creole language and the national language alongside French."
    ),
    "lu": (
        "You are speaking with a Luba-Kasai (Tshiluba) speaker from DRC. "
        "Luba culture has rich traditions in oral history and governance."
    ),
    "fan": (
        "You are speaking with a Fang speaker from Gabon or Equatorial Guinea. "
        "Fang people have a strong tradition of Byeri (ancestor veneration)."
    ),
    # ---- Global ----
    "en": "You are speaking with an English speaker. Be natural and helpful.",
    "es": "You are speaking with a Spanish speaker. Use natural, respectful Spanish.",
    "fr": (
        "You are speaking with a French speaker. "
        "In Africa, French is often a second language used for official/business purposes. "
        "Be clear and use standard French."
    ),
    "pt": (
        "You are speaking with a Portuguese speaker. "
        "In Africa, Portuguese is spoken in Angola, Mozambique, Cape Verde, "
        "Guinea-Bissau, and Sao Tome."
    ),
    "zh": "You are speaking with a Mandarin Chinese speaker. Be respectful and clear.",
    "hi": "You are speaking with a Hindi speaker. Be respectful and culturally sensitive.",
    "ar": (
        "You are speaking with an Arabic speaker. "
        "Use Modern Standard Arabic for formal contexts. Be mindful of Islamic cultural values."
    ),
    "de": "You are speaking with a German speaker. Be direct and respectful.",
    "ja": "You are speaking with a Japanese speaker. Be polite and considerate.",
    "ko": "You are speaking with a Korean speaker. Be respectful of social hierarchy.",
    "ru": "You are speaking with a Russian speaker. Be direct and clear.",
    "tr": "You are speaking with a Turkish speaker. Be respectful and warm.",
    "vi": "You are speaking with a Vietnamese speaker. Be respectful and polite.",
    "th": "You are speaking with a Thai speaker. Be respectful of Buddhist cultural values.",
    "fa": "You are speaking with a Persian (Farsi) speaker. Be respectful and warm.",
    "ur": "You are speaking with an Urdu speaker. Be respectful of Islamic cultural values.",
    "id": "You are speaking with an Indonesian speaker. Be respectful and friendly.",
    "he": "You are speaking with a Hebrew speaker. Be respectful of Jewish cultural values.",
    "ta": "You are speaking with a Tamil speaker. Be respectful of South Indian culture.",
    "te": "You are speaking with a Telugu speaker. Be respectful of South Indian culture.",
    "bn": "You are speaking with a Bengali speaker. Be warm and respectful.",
    "pa": "You are speaking with a Punjabi speaker. Be warm and respectful.",
}


# =============================================================================
# SYSTEM PROMPT TEMPLATES
# =============================================================================

SYSTEM_PROMPT_TEMPLATES: dict[str, str] = {
    "default": (
        "You are Luqi AI, a multilingual assistant fluent in over 80 languages, "
        "including 50+ African languages. You always respond in the user's language. "
        "If the user's language has limited AI resources, you do your best while "
        "remaining culturally sensitive and accurate.\n\n"
        "{cultural_context}\n\n"
        "Respond naturally in {lang_name} ({lang_english}). "
        "User language code: {lang_code}"
    ),
    "formal": (
        "You are Luqi AI, a professional multilingual assistant. "
        "Respond formally in {lang_name} ({lang_english}).\n\n"
        "{cultural_context}\n\n"
        "Use professional, respectful language appropriate for formal contexts. "
        "User language code: {lang_code}"
    ),
    "casual": (
        "You are Luqi AI, a friendly multilingual assistant. "
        "Respond conversationally in {lang_name} ({lang_english}).\n\n"
        "{cultural_context}\n\n"
        "Use natural, friendly language. Be warm and approachable. "
        "User language code: {lang_code}"
    ),
    "educational": (
        "You are Luqi AI, an educational multilingual tutor. "
        "Teach and explain clearly in {lang_name} ({lang_english}).\n\n"
        "{cultural_context}\n\n"
        "Use simple, clear language. Break complex topics into understandable parts. "
        "Encourage learning and curiosity. User language code: {lang_code}"
    ),
    "cultural": (
        "You are Luqi AI, a culturally-aware multilingual assistant. "
        "Provide responses that are deeply respectful of {lang_name} culture.\n\n"
        "{cultural_context}\n\n"
        "Be especially mindful of cultural nuances, traditional values, "
        "and appropriate ways of communicating. User language code: {lang_code}"
    ),
    "translation": (
        "You are Luqi AI, a professional translator. "
        "Translate accurately between languages while preserving meaning, "
        "tone, and cultural context.\n\n"
        "Source language context: {cultural_context}\n\n"
        "Provide accurate, natural-sounding translations. "
        "User language code: {lang_code}"
    ),
}


class MultilingualRouter:
    """
    Routes multilingual queries and constructs language-aware system prompts.

    Coordinates between language detection, cultural context, and
    AI model configuration for optimal multilingual responses.

    Attributes:
        detector: LanguageDetector instance.
        openai_api_key: Optional OpenAI API key for translation.
    """

    def __init__(self, openai_api_key: str | None = None) -> None:
        """
        Initialize the multilingual router.

        Args:
            openai_api_key: Optional OpenAI API key for translation features.
        """
        self.detector = LanguageDetector()
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.all_languages = {**AFRICAN_LANGUAGES, **GLOBAL_LANGUAGES}

    def route(self, query: str, detected_lang: str | None = None) -> dict[str, Any]:
        """
        Route a query with full language context.

        Args:
            query: User's input text.
            detected_lang: Pre-detected language code, or None to auto-detect.

        Returns:
            Dictionary with routing information including:
                - lang_code: Detected language code
                - lang_name: Native language name
                - lang_english: English language name
                - is_african: Whether language is African
                - gpt_support: Estimated GPT support level
                - response_lang: Recommended response language
                - system_prompt: Constructed system prompt
                - cultural_context: Cultural context string
                - greeting: Appropriate greeting
                - whisper_code: Whisper model language code
        """
        # Auto-detect if not provided
        if not detected_lang:
            detected_lang = self.detector.detect(query)

        # Handle the case where detected_lang has variant codes
        if detected_lang not in self.all_languages:
            # Try base code (e.g., "ar-eg" -> "ar")
            base = detected_lang.split("-")[0]
            if base in self.all_languages:
                detected_lang = base
            else:
                detected_lang = "en"

        lang_info = self.all_languages.get(detected_lang, {})

        # Determine response language
        response_lang = self.detector.get_response_language(detected_lang)

        # Get cultural context
        cultural_context = self.get_cultural_context(detected_lang)

        # Build system prompt
        system_prompt = self.build_system_prompt("default", detected_lang)

        # Get greeting
        greeting = self.detector.format_greeting(detected_lang)

        # Get whisper code
        whisper_code = lang_info.get("whisper_code", detected_lang)

        return {
            "lang_code": detected_lang,
            "lang_name": lang_info.get("name", detected_lang),
            "lang_english": lang_info.get("english_name", detected_lang),
            "is_african": self.detector.is_african(detected_lang),
            "gpt_support": lang_info.get("gpt_support", "unknown"),
            "response_lang": response_lang,
            "system_prompt": system_prompt,
            "cultural_context": cultural_context,
            "greeting": greeting,
            "whisper_code": whisper_code,
            "fallback_chain": self.detector.get_fallback_chain(detected_lang),
        }

    def build_system_prompt(self, mode: str, lang_code: str) -> str:
        """
        Build a language-aware system prompt for the AI model.

        Args:
            mode: Prompt mode - "default", "formal", "casual",
                  "educational", "cultural", or "translation".
            lang_code: Target language ISO code.

        Returns:
            Formatted system prompt string.
        """
        template = SYSTEM_PROMPT_TEMPLATES.get(mode, SYSTEM_PROMPT_TEMPLATES["default"])

        # Get language info
        lang_info = self.all_languages.get(lang_code, {})
        lang_name = lang_info.get("name", lang_code)
        lang_english = lang_info.get("english_name", lang_code)

        # Get cultural context
        cultural_context = self.get_cultural_context(lang_code)

        return template.format(
            cultural_context=cultural_context,
            lang_name=lang_name,
            lang_english=lang_english,
            lang_code=lang_code,
        )

    def translate_if_needed(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "en",
    ) -> str:
        """
        Translate text if the target language differs from source.

        This is a placeholder that returns the original text.
        In production, integrate with OpenAI API or a translation service.

        Args:
            text: Text to potentially translate.
            target_lang: Target language code.
            source_lang: Source language code (default English).

        Returns:
            Translated text or original if no translation needed.
        """
        if target_lang == source_lang:
            return text

        # Placeholder: in production, call OpenAI translation API
        # Example:
        # response = openai.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[
        #         {"role": "system", "content": f"Translate from {source_lang} to {target_lang}."},
        #         {"role": "user", "content": text},
        #     ],
        # )
        # return response.choices[0].message.content

        # For now, return with a note
        return text  # Translation placeholder

    def get_cultural_context(self, lang_code: str) -> str:
        """
        Get cultural context for a language.

        Args:
            lang_code: Language ISO code.

        Returns:
            Cultural context string for the AI model.
        """
        context = CULTURAL_CONTEXTS.get(lang_code)
        if context:
            return context

        # Try base code for variants
        if "-" in lang_code:
            base = lang_code.split("-")[0]
            context = CULTURAL_CONTEXTS.get(base)
            if context:
                return context

        return (
            f"You are speaking with a user who communicates "
            f"in language code '{lang_code}'. Be respectful and helpful."
        )

    def is_supported(self, lang_code: str) -> bool:
        """
        Check if a language is in the database.

        Args:
            lang_code: Language ISO code to check.

        Returns:
            True if language is supported.
        """
        return lang_code in self.all_languages

    def get_available_modes(self) -> list[str]:
        """Return available system prompt modes."""
        return list(SYSTEM_PROMPT_TEMPLATES.keys())

    def suggest_language(self, text: str) -> dict[str, Any]:
        """
        Suggest language information for a given text.

        Args:
            text: Input text to analyze.

        Returns:
            Dictionary with language suggestions.
        """
        detected = self.detector.detect(text)
        return self.route(text, detected)

    def format_multilingual_response(
        self,
        text: str,
        lang_code: str,
        include_greeting: bool = False,
    ) -> str:
        """
        Format a response with optional greeting in target language.

        Args:
            text: Response text (already in target language).
            lang_code: Target language code.
            include_greeting: Whether to prepend a greeting.

        Returns:
            Formatted response string.
        """
        if include_greeting:
            greeting = self.detector.format_greeting(lang_code)
            return f"{greeting}! {text}"
        return text

    def get_greeting_with_context(self, lang_code: str, context: str = "general") -> str:
        """
        Get a culturally-appropriate greeting for a specific context.

        Args:
            lang_code: Target language code.
            context: Context type ("general", "morning", "evening",
                     "formal", "religious").

        Returns:
            Appropriate greeting string.
        """
        lang_info = self.all_languages.get(lang_code, {})
        greetings = lang_info.get("greetings", {})

        # Context-specific greetings
        if context == "morning":
            return greetings.get("hello", "Hello!")
        elif context == "evening":
            return greetings.get("goodbye", "Goodbye!")
        elif context == "thank_you":
            return greetings.get("thank_you", "Thank you!")
        elif context == "help":
            return greetings.get("help", "Help!")
        elif context == "welcome":
            return greetings.get("welcome", "Welcome!")

        return greetings.get("hello", "Hello!")

    def compare_languages(self, lang_code1: str, lang_code2: str) -> dict[str, Any]:
        """
        Compare two languages and return similarities/differences.

        Args:
            lang_code1: First language code.
            lang_code2: Second language code.

        Returns:
            Comparison dictionary.
        """
        info1 = self.all_languages.get(lang_code1, {})
        info2 = self.all_languages.get(lang_code2, {})

        same_family = (
            info1.get("language_family") == info2.get("language_family")
            and info1.get("language_family") is not None
        )
        same_region = (
            info1.get("region") == info2.get("region")
            and info1.get("region") is not None
        )
        shared_countries = set(info1.get("countries", [])) & set(
            info2.get("countries", [])
        )

        return {
            "lang1": {"code": lang_code1, **info1},
            "lang2": {"code": lang_code2, **info2},
            "same_family": same_family,
            "same_region": same_region,
            "shared_countries": list(shared_countries),
            "similarity_score": sum([
                1 if same_family else 0,
                1 if same_region else 0,
                len(shared_countries),
            ]),
        }


# =============================================================================
# MODULE-LEVEL HELPERS
# =============================================================================

def get_router(openai_api_key: str | None = None) -> MultilingualRouter:
    """Factory function to create a MultilingualRouter instance."""
    return MultilingualRouter(openai_api_key=openai_api_key)


def build_prompt(lang_code: str, mode: str = "default") -> str:
    """Quick system prompt builder."""
    router = MultilingualRouter()
    return router.build_system_prompt(mode, lang_code)


def get_context(lang_code: str) -> str:
    """Quick cultural context lookup."""
    router = MultilingualRouter()
    return router.get_cultural_context(lang_code)