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

from lang.african_languages import AFRICAN_LANGUAGES, GLOBAL_LANGUAGES
from lang.language_detector import LanguageDetector


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
        "polite language. Ethiopia was never colonized and has strong national pride."
    ),
    "so": (
        "You are speaking with a Somali speaker. Somalia has a clan-based society "
        "with strong oral poetry traditions. Islam is central to daily life. "
        "Be respectful of Islamic customs and traditions."
    ),
    "om": (
        "You are speaking with an Oromo speaker from Ethiopia/Kenya. "
        "The Oromo are the largest ethnic group in Ethiopia. "
        "Respect for Gadaa traditional governance system is important."
    ),
    "ti": (
        "You are speaking with a Tigrinya speaker from Eritrea or Ethiopia (Tigray). "
        "Be sensitive to the Eritrea-Ethiopia conflict history. "
        "Family and religious traditions (Orthodox, Catholic, Islam) are important."
    ),
    "lg": (
        "You are speaking with a Luganda/Ganda speaker from Uganda (Buganda region). "
        "The Kingdom of Buganda has a rich cultural heritage. "
        "Respect for elders and traditional leaders (Kabaka) is important."
    ),
    "mg": (
        "You are speaking with a Malagasy speaker from Madagascar. "
        "Malagasy culture blends Southeast Asian and African influences. "
        "Respect for ancestors (razana) and family is central. "
        "Use polite and inclusive language."
    ),

    # ---- West Africa ----
    "ha": (
        "You are speaking with a Hausa speaker from West Africa (Nigeria, Niger, Ghana). "
        "Hausa is a major lingua franca in West Africa. Islam is predominant but "
        "there are Christian and traditional communities. Be respectful of religious "
        "diversity. Family and community are highly valued."
    ),
    "yo": (
        "You are speaking with a Yoruba speaker from Nigeria/Benin/Togo. "
        "Yoruba culture has rich artistic, religious (Ifa/Christian/Islam), "
        "and cultural traditions. Respect for elders is paramount. "
        "Be culturally sensitive and inclusive."
    ),
    "ig": (
        "You are speaking with an Igbo speaker from Nigeria. "
        "Igbo culture values achievement, education, and community (umuahia). "
        "Respect for elders and traditional institutions is important. "
        "Be inclusive and culturally aware."
    ),
    "ff": (
        "You are speaking with a Fulfulde/Pulaar speaker. The Fulani are "
        "traditionally pastoralist and spread across many West African countries. "
        "Pulaaku (Fulani code of conduct emphasizing dignity and reserve) is important."
    ),
    "ak": (
        "You are speaking with an Akan/Twi speaker from Ghana. "
        "Akan culture emphasizes respect, hospitality, and proverbs. "
        "Use respectful language and be mindful of cultural nuances."
    ),
    "ee": (
        "You are speaking with an Ewe speaker from Ghana/Togo/Benin. "
        "Ewe culture has rich musical and dance traditions. "
        "Be respectful and culturally sensitive."
    ),
    "wo": (
        "You are speaking with a Wolof speaker from Senegal/Gambia. "
        "Wolof is the lingua franca of Senegal. Teranga (hospitality) is a core value. "
        "Be warm, welcoming, and respectful. Islam and Christianity are both present."
    ),
    "bm": (
        "You are speaking with a Bambara speaker from Mali. "
        "Bambara is the dominant language in Mali. "
        "Respect for elders and community is important. "
        "Be culturally sensitive and inclusive."
    ),
    "mos": (
        "You are speaking with a Moore/Mossi speaker from Burkina Faso. "
        "The Mossi people have a strong traditional kingdom (Mogho Naba). "
        "Respect for elders and traditional authority is important."
    ),
    "fon": (
        "You are speaking with a Fon speaker from Benin. "
        "Benin is the birthplace of Vodun (Voodoo) tradition. "
        "Be respectful of traditional religious practices alongside Christianity and Islam."
    ),

    # ---- Southern Africa ----
    "zu": (
        "You are speaking with a Zulu speaker from South Africa. "
        "Zulu is the most widely spoken home language in South Africa. "
        "Ubuntu (I am because we are) is a central philosophy. "
        "Be respectful of cultural traditions and the legacy of apartheid."
    ),
    "xh": (
        "You are speaking with a Xhosa speaker from South Africa. "
        "Xhosa has rich oral traditions including click consonants. "
        "Ubuntu is important. Nelson Mandela was Xhosa. "
        "Be respectful of cultural heritage."
    ),
    "af": (
        "You are speaking with an Afrikaans speaker. Afrikaans is spoken "
        "in South Africa and Namibia. Be sensitive to the complex history "
        "of Afrikaans (apartheid legacy vs modern diverse community)."
    ),
    "st": (
        "You are speaking with a Sesotho speaker from South Africa or Lesotho. "
        "Lesotho is a mountain kingdom entirely surrounded by South Africa. "
        "Respect for Basotho traditions and the monarchy is important."
    ),
    "tn": (
        "You are speaking with a Tswana speaker from Botswana or South Africa. "
        "Botswana is known for stable democracy. Botho (respect and compassion) "
        "is a core cultural value. Be respectful and polite."
    ),
    "nso": (
        "You are speaking with a Sepedi/Northern Sotho speaker from South Africa. "
        "Be respectful of cultural traditions and community values."
    ),
    "ts": (
        "You are speaking with a Tsonga speaker from South Africa/Mozambique. "
        "Tsonga culture has rich music and dance traditions. "
        "Be respectful and culturally aware."
    ),
    "ve": (
        "You are speaking with a Venda speaker from South Africa/Zimbabwe. "
        "Venda culture has strong traditional institutions. "
        "Be respectful of cultural heritage."
    ),
    "ss": (
        "You are speaking with a Swati speaker from Eswatini or South Africa. "
        "Eswatini is Africa's last absolute monarchy. "
        "Respect for the monarchy and traditional institutions is paramount."
    ),
    "nr": (
        "You are speaking with a Ndebele speaker from South Africa or Zimbabwe. "
        "Ndebele people are known for vibrant artistic traditions. "
        "Be respectful of cultural heritage."
    ),
    "sn": (
        "You are speaking with a Shona speaker from Zimbabwe. "
        "Shona culture emphasizes respect (unhu) and community. "
        "Be respectful of cultural traditions and the political context."
    ),
    "nd": (
        "You are speaking with a North Ndebele speaker from Zimbabwe. "
        "Be respectful of cultural traditions and Zimbabwe's complex history."
    ),
    "ny": (
        "You are speaking with a Chewa/Nyanja speaker from Malawi/Zambia. "
        "Chewa is a major language in Malawi. "
        "Be respectful, warm, and culturally sensitive."
    ),

    # ---- Central Africa ----
    "ln": (
        "You are speaking with a Lingala speaker from DRC or Congo-Brazzaville. "
        "Lingala is a major lingua franca in the DRC, especially in Kinshasa. "
        "Be culturally sensitive to the ongoing conflicts in the region."
    ),
    "kg": (
        "You are speaking with a Kikongo speaker. Kikongo is spoken "
        "in DRC, Congo-Brazzaville, and Angola. "
        "Be respectful of cultural traditions."
    ),
    "ktu": (
        "You are speaking with a Kituba/Munukutuba speaker. Kituba is "
        "a trade language in DRC and Congo-Brazzaville. "
        "Be culturally sensitive."
    ),
    "lu": (
        "You are speaking with a Luba-Kasai (Tshiluba) speaker from DRC. "
        "Be respectful of the complex cultural and political landscape of the DRC."
    ),
    "sg": (
        "You are speaking with a Sango speaker from the Central African Republic. "
        "Sango is the national language. The country has faced significant conflict. "
        "Be sensitive and respectful."
    ),

    # ---- North Africa ----
    "ar-eg": (
        "You are speaking with an Arabic speaker from Egypt or North Africa. "
        "Egyptian Arabic is widely understood across the Arab world. "
        "Islam and Christianity are both present. "
        "Be respectful of religious and cultural traditions."
    ),
    "ary": (
        "You are speaking with a Moroccan Arabic (Darija) speaker. "
        "Moroccan culture blends Arab, Berber, and European influences. "
        "Respect for elders and hospitality are important values."
    ),
    "kab": (
        "You are speaking with a Kabyle/Berber speaker from Algeria. "
        "Berber (Tamazight) is an official language in Algeria and Morocco. "
        "Berber identity and cultural preservation are important issues."
    ),
    "shi": (
        "You are speaking with a Tashelhit/Shilha speaker from Morocco. "
        "Tashelhit is a major Berber language in southern Morocco. "
        "Be respectful of Berber cultural heritage."
    ),

    # ---- Global languages ----
    "en": (
        "You are speaking with an English speaker. Be clear, concise, and helpful. "
        "Adapt tone to the user's style."
    ),
    "fr": (
        "You are speaking with a French speaker. Use formal 'vous' unless "
        "the user uses 'tu'. Be polite and culturally sensitive."
    ),
    "pt": (
        "You are speaking with a Portuguese speaker. Be warm and respectful. "
        "Note: Brazilian and European Portuguese have significant differences."
    ),
    "es": (
        "You are speaking with a Spanish speaker. Be warm and respectful. "
        "Note: Latin American and Iberian Spanish vary significantly."
    ),
    "zh": (
        "You are speaking with a Chinese speaker. Be respectful and formal. "
        "Note: Simplified (Mainland) and Traditional (Taiwan/HK) characters differ."
    ),
    "hi": (
        "You are speaking with a Hindi speaker from India. "
        "Respect for elders and cultural traditions is important. "
        "India has diverse religions (Hinduism, Islam, Sikhism, Christianity, etc.)."
    ),
    "ar": (
        "You are speaking with an Arabic speaker. Arabic varies significantly "
        "across regions (Egyptian, Gulf, Levantine, Maghrebi, etc.). "
        "Be respectful of Islamic traditions and cultural norms."
    ),
    "bn": (
        "You are speaking with a Bengali speaker from Bangladesh or India (West Bengal). "
        "Be respectful of cultural traditions."
    ),
    "ru": (
        "You are speaking with a Russian speaker. Be direct but polite. "
        "Formality levels matter in Russian culture."
    ),
    "ja": (
        "You are speaking with a Japanese speaker. Politeness and formality "
        "are extremely important. Use keigo (respectful language) concepts."
    ),
    "de": (
        "You are speaking with a German speaker. Be direct, clear, and efficient. "
        "Formality (Sie vs du) matters depending on context."
    ),
    "ko": (
        "You are speaking with a Korean speaker. Respect for hierarchy and "
        "age is very important. Use honorifics appropriately."
    ),
    "it": (
        "You are speaking with an Italian speaker. Be warm and expressive. "
        "Formality (Lei vs tu) depends on context."
    ),
    "tr": (
        "You are speaking with a Turkish speaker. Be respectful and hospitable. "
        "Islam is the majority religion but Turkey is officially secular."
    ),
    "vi": (
        "You are speaking with a Vietnamese speaker. Respect for elders and "
        "family is paramount. Use polite language."
    ),
    "pl": (
        "You are speaking with a Polish speaker. Be polite and direct. "
        "Formality (Pan/Pani) is used in professional contexts."
    ),
    "uk": (
        "You are speaking with a Ukrainian speaker. Be respectful of "
        "Ukrainian national identity and the ongoing conflict with Russia."
    ),
    "ro": (
        "You are speaking with a Romanian speaker. Be warm and respectful. "
        "Romanian culture values hospitality and family."
    ),
    "nl": (
        "You are speaking with a Dutch speaker. Be direct and practical. "
        "Dutch culture values straightforwardness and efficiency."
    ),
    "el": (
        "You are speaking with a Greek speaker. Be warm and respectful. "
        "Family and Orthodox Christian traditions are important to many."
    ),
    "cs": (
        "You are speaking with a Czech speaker. Be polite and direct. "
        "Czech culture values modesty and straightforwardness."
    ),
    "hu": (
        "You are speaking with a Hungarian speaker. Be polite and respectful. "
        "Hungarian culture values hospitality and intellectual discourse."
    ),
    "sv": (
        "You are speaking with a Swedish speaker. Be egalitarian and direct. "
        "Swedish culture values equality (jantelagen) and consensus."
    ),
    "id": (
        "You are speaking with an Indonesian speaker. Be respectful and polite. "
        "Indonesia is diverse with many ethnic groups and religions."
    ),
    "th": (
        "You are speaking with a Thai speaker. Respect for hierarchy, Buddhism, "
        "and the monarchy is paramount. Use polite particles (krub/kha)."
    ),
    "he": (
        "You are speaking with a Hebrew speaker from Israel. Be direct and respectful. "
        "Be sensitive to the Israeli-Palestinian conflict."
    ),
    "fa": (
        "You are speaking with a Persian/Farsi speaker from Iran. "
        "Be respectful of Islamic traditions and Persian cultural heritage. "
        "Taarof (ritual politeness) is an important cultural concept."
    ),
}


# =============================================================================
# MULTILINGUAL ROUTER
# =============================================================================

class MultilingualRouter:
    """Routes queries to the appropriate language-aware pipeline.

    Handles:
        - System prompt construction with cultural context
        - Greeting detection and response in user's language
        - Translation coordination
        - Response formatting

    Attributes:
        detector: LanguageDetector instance
        all_languages: Combined dict of African + global languages
    """

    def __init__(self) -> None:
        self.detector = LanguageDetector()
        self.all_languages: dict[str, dict] = {}
        self.all_languages.update(AFRICAN_LANGUAGES)
        self.all_languages.update(GLOBAL_LANGUAGES)

    def route(
        self,
        user_input: str,
        language_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Route a user query through the multilingual pipeline.

        Args:
            user_input: The user's message.
            language_code: Optional known language code (ISO 639-1/2).

        Returns:
            Dictionary with system_prompt, detected_language, greeting,
            cultural_context, and translation_needed.
        """
        # Step 1: Detect language if not provided
        if language_code is None:
            detection = self.detector.detect(user_input)
            language_code = detection["language"]
            confidence = detection["confidence"]
            method = detection["method"]
        else:
            confidence = 1.0
            method = "explicit"

        # Step 2: Get language info
        lang_info = self.all_languages.get(language_code, {})

        # Step 3: Check if it's a greeting
        greeting_response = self._check_greeting(user_input, language_code)

        # Step 4: Build system prompt
        cultural_context = CULTURAL_CONTEXTS.get(language_code, "")
        system_prompt = self._build_system_prompt(
            language_code, lang_info, cultural_context
        )

        # Step 5: Determine if translation is needed
        needs_translation = language_code not in ("en", "af") and method != "explicit_en"

        return {
            "system_prompt": system_prompt,
            "detected_language": language_code,
            "language_name": lang_info.get("name", language_code),
            "confidence": confidence,
            "method": method,
            "greeting_response": greeting_response,
            "cultural_context": cultural_context,
            "needs_translation": needs_translation,
            "script": lang_info.get("script", "Latin"),
        }

    def _check_greeting(self, user_input: str, lang_code: str) -> Optional[str]:
        """Check if user input is a greeting and return appropriate response."""
        user_lower = user_input.lower().strip()

        # Remove punctuation
        user_clean = re.sub(r"[^\w\s]", "", user_lower)

        lang_info = self.all_languages.get(lang_code, {})
        greetings = lang_info.get("greetings", {})

        if not greetings:
            return None

        # Check for greeting keywords
        greeting_keywords = {
            "hello": ["hello", "hi", "hey", "greetings", "salutations"],
            "goodbye": ["bye", "goodbye", "see you", "farewell", "ciao"],
            "thank_you": ["thank", "thanks", "grateful", "appreciate"],
            "how_are_you": ["how are you", "how're you", "how you doing", "what's up"],
            "help": ["help", "assist", "support", "aid"],
            "welcome": ["welcome", "you're welcome"],
        }

        for greeting_type, keywords in greeting_keywords.items():
            for keyword in keywords:
                if keyword in user_clean:
                    response = greetings.get(greeting_type)
                    if response:
                        return f"{response}! 👋"

        return None

    def _build_system_prompt(
        self,
        lang_code: str,
        lang_info: dict,
        cultural_context: str,
    ) -> str:
        """Build a system prompt for the given language."""
        parts = []

        # Language instruction
        lang_name = lang_info.get("name", lang_code)
        english_name = lang_info.get("english_name", lang_code)

        if lang_code == "en":
            parts.append("You are a helpful AI assistant. Respond in English.")
        else:
            parts.append(
                f"You are a multilingual AI assistant. The user is writing "
                f"in {lang_name} ({english_name}). "
                f"Respond primarily in {lang_name} unless the user explicitly "
                f"asks for another language."
            )

        # Cultural context
        if cultural_context:
            parts.append(f"\nCultural Context: {cultural_context}")

        # Script guidance
        script = lang_info.get("script", "Latin")
        if script in ("Ge'ez (Ethiopic)", "Tifinagh"):
            parts.append(
                f"\nNote: {lang_name} uses the {script} script. "
                f"Ensure your responses use the correct script and encoding."
            )
        elif script == "Arabic":
            parts.append(
                "\nNote: Arabic uses right-to-left (RTL) script. "
                "Ensure proper RTL handling in responses."
            )

        # GPT quality guidance
        gpt_support = lang_info.get("gpt_support", "unknown")
        if gpt_support in ("minimal", "limited"):
            parts.append(
                f"\nNote: Your training data for {lang_name} may be limited. "
                f"If you are uncertain about a translation or cultural nuance, "
                f"acknowledge this limitation honestly. When possible, provide "
                f"the English equivalent alongside the {lang_name} response."
            )

        return "\n".join(parts)

    def get_supported_languages(self) -> list[dict[str, str]]:
        """Return list of all supported languages with basic info."""
        result = []
        for code, info in self.all_languages.items():
            result.append({
                "code": code,
                "name": info.get("name", code),
                "english_name": info.get("english_name", code),
                "region": info.get("region", "Unknown"),
                "script": info.get("script", "Latin"),
                "gpt_support": info.get("gpt_support", "unknown"),
            })
        return sorted(result, key=lambda x: x["name"])

    def get_language_details(self, lang_code: str) -> Optional[dict[str, Any]]:
        """Get detailed information about a specific language."""
        info = self.all_languages.get(lang_code)
        if not info:
            return None

        return {
            "code": lang_code,
            **info,
            "has_cultural_context": lang_code in CULTURAL_CONTEXTS,
        }

    def detect_and_route(self, user_input: str) -> dict[str, Any]:
        """Convenience method: detect language and route in one step."""
        return self.route(user_input)

    def format_response(
        self,
        response_text: str,
        lang_code: str,
        include_translation: bool = False,
    ) -> dict[str, str]:
        """Format a response with optional translation."""
        result = {
            "primary": response_text,
            "language": lang_code,
        }

        if include_translation and lang_code != "en":
            # In a real implementation, this would call a translation API
            result["translation_note"] = (
                f"[Translation to English would be provided here]"
            )

        return result
