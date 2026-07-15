"""Omega AI v3 — African Languages Support
Translation and cultural context for African languages.
"""
from __future__ import annotations

from typing import Any


class AfricanLanguages:
    """African language support with phrases and cultural context."""

    LANGUAGES: dict[str, dict[str, Any]] = {
        "zu": {"name": "Zulu", "native": "isiZulu", "region": "South Africa", "speakers": "12M+", "family": "Bantu", "code": "zu"},
        "xh": {"name": "Xhosa", "native": "isiXhosa", "region": "South Africa", "speakers": "8M+", "family": "Bantu", "code": "xh"},
        "sw": {"name": "Swahili", "native": "Kiswahili", "region": "East Africa", "speakers": "200M+", "family": "Bantu", "code": "sw"},
        "yo": {"name": "Yoruba", "native": "Yorùbá", "region": "Nigeria, Benin", "speakers": "45M+", "family": "Niger-Congo", "code": "yo"},
        "am": {"name": "Amharic", "native": "አማርኛ", "region": "Ethiopia", "speakers": "32M+", "family": "Semitic", "code": "am"},
        "ha": {"name": "Hausa", "native": "Hausa / هَوُسَ", "region": "Nigeria, Niger, West Africa", "speakers": "80M+", "family": "Afro-Asiatic", "code": "ha"},
        "ig": {"name": "Igbo", "native": "Igbo", "region": "Nigeria", "speakers": "27M+", "family": "Niger-Congo", "code": "ig"},
        "sn": {"name": "Shona", "native": "chiShona", "region": "Zimbabwe, Mozambique", "speakers": "13M+", "family": "Bantu", "code": "sn"},
        "af": {"name": "Afrikaans", "native": "Afrikaans", "region": "South Africa, Namibia", "speakers": "7M+", "family": "Germanic", "code": "af"},
        "st": {"name": "Sesotho", "native": "Sesotho", "region": "Lesotho, South Africa", "speakers": "5M+", "family": "Bantu", "code": "st"},
        "tn": {"name": "Setswana", "native": "Setswana", "region": "Botswana, South Africa", "speakers": "4M+", "family": "Bantu", "code": "tn"},
        "nr": {"name": "isiNdebele", "native": "isiNdebele", "region": "South Africa, Zimbabwe", "speakers": "1M+", "family": "Bantu", "code": "nr"},
        "ss": {"name": "Siswati", "native": "siSwati", "region": "Eswatini, South Africa", "speakers": "2M+", "family": "Bantu", "code": "ss"},
        "ve": {"name": "Tshivenda", "native": "Tshivenḓa", "region": "South Africa, Zimbabwe", "speakers": "1M+", "family": "Bantu", "code": "ve"},
        "ts": {"name": "Xitsonga", "native": "Xitsonga", "region": "South Africa, Mozambique", "speakers": "3M+", "family": "Bantu", "code": "ts"},
        "rw": {"name": "Kinyarwanda", "native": "Kinyarwanda", "region": "Rwanda", "speakers": "12M+", "family": "Bantu", "code": "rw"},
        "lg": {"name": "Luganda", "native": "Luganda", "region": "Uganda", "speakers": "6M+", "family": "Bantu", "code": "lg"},
        "wo": {"name": "Wolof", "native": "Wolof", "region": "Senegal, Gambia", "speakers": "12M+", "family": "Niger-Congo", "code": "wo"},
        "so": {"name": "Somali", "native": "Soomaali", "region": "Somalia, Ethiopia, Kenya", "speakers": "20M+", "family": "Cushitic", "code": "so"},
        "ar": {"name": "Arabic (North African)", "native": "العربية", "region": "North Africa", "speakers": "170M+", "family": "Semitic", "code": "ar"},
        "fr": {"name": "French (African)", "native": "Français", "region": "Francophone Africa", "speakers": "120M+", "family": "Romance", "code": "fr"},
        "pt": {"name": "Portuguese (African)", "native": "Português", "region": "Lusophone Africa", "speakers": "30M+", "family": "Romance", "code": "pt"},
    }

    PHRASES: dict[str, dict[str, str]] = {
        "hello": {
            "zu": "Sawubona", "xh": "Molo", "sw": "Jambo / Hujambo", "yo": "Báwo",
            "am": "ሰላም (Salam)", "ha": "Sannu", "ig": "Ndewo", "sn": "Mhoroi",
            "af": "Hallo / Goeie dag", "st": "Dumela", "tn": "Dumela",
            "nr": "Lotjhani", "ss": "Sawubona", "ve": "Ndaa / Aa",
            "ts": "Avuxeni", "rw": "Muraho", "lg": "Oli otya?",
            "wo": "Asalaam maleekum / Naka nga def?", "so": "Iska waran",
            "ar": "السلام عليكم (As-salamu alaykum)", "fr": "Bonjour", "pt": "Olá",
        },
        "thank_you": {
            "zu": "Ngiyabonga", "xh": "Enkosi", "sw": "Asante", "yo": "O ṣeun",
            "am": "አመሰግናለሁ (Ameseginalehu)", "ha": "Na gode", "ig": "Daalụ", "sn": "Ndatenda",
            "af": "Dankie", "st": "Ke a leboha", "tn": "Ke a leboga",
            "nr": "Ngiyabonga", "ss": "Ngiyabonga", "ve": "Ndo livhuwa",
            "ts": "Ndza nkhensa", "rw": "Murakoze", "lg": "Webale",
            "wo": "Jërëjëf", "so": "Mahadsanid", "ar": "شكراً (Shukran)",
            "fr": "Merci", "pt": "Obrigado/Obrigada",
        },
        "how_are_you": {
            "zu": "Unjani?", "xh": "Unjani?", "sw": "Habari gani?", "yo": "Ṣé àlàáfíà ni?",
            "am": "እንዴት ነህ? (Indet neh?)", "ha": "Yaya lafiya?", "ig": "Kedu?", "sn": "Makadii?",
            "af": "Hoe gaan dit?", "st": "O kae?", "tn": "O tsogile jang?",
            "nr": "Unjani?", "ss": "Unjani?", "ve": "Vho vuwa hani?",
            "ts": "Ku njhani?", "rw": "Amakuru?", "lg": "Oli otya?",
            "wo": "Naka nga def?", "so": "Iska waran?", "ar": "كيف حالك؟ (Kayfa halak?)",
            "fr": "Comment allez-vous?", "pt": "Como está?",
        },
        "goodbye": {
            "zu": "Hamba kahle / Sala kahle", "xh": "Hamba kakuhle", "sw": "Kwaheri", "yo": "Ó dàbò",
            "am": "ቻው (Chau) / ደህና ሁን (Dehna hun)", "ha": "Sai an jima", "ig": "Ka ọ dị", "sn": "Chisarai",
            "af": "Totsiens", "st": "Sala hantle", "tn": "Tsamaya sentle",
            "nr": "Hamba kahle", "ss": "Hamba kahle", "ve": "Vha vhe na vhudi",
            "ts": "Vaha helini", "rw": "Murabeho", "lg": "Weeraba",
            "wo": "Ba beneen", "so": "Nabad gelyo", "ar": "مع السلامة (Ma'a as-salama)",
            "fr": "Au revoir", "pt": "Adeus",
        },
        "yes": {
            "zu": "Yebo", "xh": "Ewe", "sw": "Ndiyo / Ndio", "yo": "Bẹ́ẹ̀ni",
            "am": "አዎ (Awo)", "ha": "Eh", "ig": "Ee", "sn": "Hongu",
            "af": "Ja", "st": "Ee", "tn": "Ee", "nr": "Yebo", "ss": "Yebo",
            "ve": "Ii", "ts": "Ina", "rw": "Yego", "lg": "Yee",
            "wo": "Waaw", "so": "Haa", "ar": "نعم (Na'am)", "fr": "Oui", "pt": "Sim",
        },
        "no": {
            "zu": "Cha", "xh": "Hayi", "sw": "Hapana", "yo": "Rárá",
            "am": "አይ (Ay)", "ha": "A'a", "ig": "Mba", "sn": "Kwete",
            "af": "Nee", "st": "Tjhee", "tn": "Nnyaa", "nr": "Cha", "ss": "Cha",
            "ve": "Aha", "ts": "E-e", "rw": "Oya", "lg": "Nedda",
            "wo": "Déet", "so": "Maya", "ar": "لا (La)", "fr": "Non", "pt": "Não",
        },
        "please": {
            "zu": "Ngiyacela", "xh": "Ndiyacela", "sw": "Tafadhali", "yo": "Ẹ jọ̀ọ́",
            "am": "በልኳ (Belekwa)", "ha": "Don Allah", "ig": "Biko", "sn": "Ndapota",
            "af": "Asseblief", "st": "Ka kopo", "tn": "Tswêê-tswêê", "nr": "Ngiyacela",
            "ss": "Ngiyacela", "ve": "Ndi khou humbela", "ts": "Ndza kombela",
            "rw": "Mbabarira", "lg": "Mukama gw'omukwano", "wo": "Ladaayaal",
            "so": "Fadlan", "ar": "من فضلك (Min fadlik)", "fr": "S'il vous plaît", "pt": "Por favor",
        },
        "welcome": {
            "zu": "Siyakwamukela", "xh": "Wamkelekile", "sw": "Karibu", "yo": "Ẹ kú àbọ̀",
            "am": "እንኳን ደህና መጣህ (Inkwuan dehna metah)", "ha": "Barka da zuwa", "ig": "Nnọọ", "sn": "Mauya",
            "af": "Welkom", "st": "O amohetswe", "tn": "O amogetswe", "nr": "Siyamukela",
            "ss": "Siyakwamukela", "ve": "Vha khou itelwa", "ts": "Mi amukeriwile",
            "rw": "Murakaza neza", "lg": "Tukusanyukidde", "wo": "Dalal jamm",
            "so": "Soo dhawoow", "ar": "أهلاً وسهلاً (Ahlan wa sahlan)", "fr": "Bienvenue", "pt": "Bem-vindo",
        },
    }

    NUMBERS: dict[str, dict[int, str]] = {
        "zu": {1: "kunye", 2: "kubili", 3: "kuthathu", 4: "kune", 5: "kuhlanu", 6: "yisithupha", 7: "yisikhombisa", 8: "yisishiyagalombili", 9: "yisishiyagalolunye", 10: "yishumi"},
        "xh": {1: "nye", 2: "bini", 3: "thathu", 4: "ne", 5: "hlanu", 6: "thandathu", 7: "xhenxe", 8: "sibhozo", 9: "ithoba", 10: "lishumi"},
        "sw": {1: "moja", 2: "mbili", 3: "tatu", 4: "nne", 5: "tano", 6: "sita", 7: "saba", 8: "nane", 9: "tisa", 10: "kumi"},
        "yo": {1: "ọ̀kan", 2: "méjì", 3: "mẹ́ta", 4: "mẹ́rin", 5: "márùn-ún", 6: "mẹ́fà", 7: "méje", 8: "mẹ́jọ", 9: "mẹ́sàn-án", 10: "mọ́kànlá"},
        "af": {1: "een", 2: "twee", 3: "drie", 4: "vier", 5: "vyf", 6: "ses", 7: "sewe", 8: "agt", 9: "nege", 10: "tien"},
        "rw": {1: "rimwe", 2: "kabiri", 3: "gatatu", 4: "kane", 5: "gatanu", 6: "gatandatu", 7: "karindwi", 8: "umunani", 9: "icyenda", 10: "icumi"},
        "so": {1: "kow", 2: "laba", 3: "sadex", 4: "afar", 5: "shan", 6: "lix", 7: "toddoba", 8: "siddeed", 9: "sagaal", 10: "toban"},
    }

    CULTURAL_NOTES: dict[str, str] = {
        "zu": "Zulu culture emphasizes respect for elders ('ubudoda'). Use 'Sawubona' for greetings. The left hand should not be used alone when giving/receiving.",
        "xh": "Xhosa culture values ubuntu ('I am because we are'). Greetings are important and often include asking about family.",
        "sw": "Swahili is a lingua franca across East Africa. 'Jambo' is common for tourists; locals often use 'Habari' instead.",
        "yo": "Yoruba culture values respect and greeting rituals. Elders are greeted first. Proverbs are commonly used in speech.",
        "am": "Amharic uses its own script (Ge'ez). Ethiopian culture values communal eating (injera). Elders are highly respected.",
        "ha": "Hausa culture is heavily influenced by Islam. Greetings are elaborate and involve asking about family, work, and health.",
        "ig": "Igbo culture values hospitality (òbì). The kola nut ceremony is significant for welcoming guests.",
        "sn": "Shona culture emphasizes respect ('kunzwa'). Greeting elders with both hands together is a sign of respect.",
        "af": "Afrikaans culture blends Dutch, African, and other influences. Directness in communication is valued.",
        "rw": "Rwanda has a unified cultural identity. Greetings are important and often ask about cattle (a sign of wealth).",
    }

    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        """Translate common phrases or provide guidance."""
        target = target_lang.lower()[:2]
        text_lower = text.lower().strip()

        for phrase_key, translations in self.PHRASES.items():
            if text_lower in phrase_key or phrase_key in text_lower:
                if target in translations:
                    lang_name = self.LANGUAGES.get(target, {}).get("name", target)
                    return f"'{text}' in {lang_name}: {translations[target]}"

        lang_name = self.LANGUAGES.get(target, {}).get("name", target)
        return f"Translation guidance: '{text}' → {lang_name}\n\nFor accurate translation, consider:\n- Google Translate (basic)\n- Professional translator (important documents)\n- Community language resources\n\nI can teach common phrases in {lang_name}. Try: 'greetings in {lang_name}'"

    def detect_language(self, text: str) -> str:
        """Identify African language from sample text."""
        text_lower = text.lower()
        for lang_code, lang_info in self.LANGUAGES.items():
            if lang_info["native"].lower() in text_lower:
                return f"Detected: {lang_info['name']} ({lang_info['native']}) — {lang_info['region']}"
        indicators = {
            "sawubona": "Zulu/Siswati/Ndebele", "molo": "Xhosa", "jambo": "Swahili",
            "báwo": "Yoruba", "salam": "Amharic/Arabic", "sannu": "Hausa",
            "ndewo": "Igbo", "mhoroi": "Shona", "hallo": "Afrikaans",
            "dumela": "Sesotho/Setswana", "muraho": "Kinyarwanda", "avuxeni": "Xitsonga",
        }
        for word, lang in indicators.items():
            if word in text_lower:
                return f"Detected: {lang} (keyword: '{word}')"
        return "Could not identify language. Please provide more text or specify the language."

    def list_languages(self) -> list[dict[str, Any]]:
        """List all supported languages."""
        return list(self.LANGUAGES.values())

    def cultural_context(self, phrase: str, language: str) -> str:
        """Get cultural notes for a language."""
        code = language.lower()[:2]
        note = self.CULTURAL_NOTES.get(code, f"Cultural notes for {language} not yet available.")
        lang_name = self.LANGUAGES.get(code, {}).get("name", language)
        return f"## Cultural Context: {lang_name}\n\n{note}"

    def learn_mode(self, language: str) -> str:
        """Interactive language lesson."""
        code = language.lower()[:2]
        lang = self.LANGUAGES.get(code)
        if not lang:
            return f"Language '{language}' not found. Use list_languages() to see available languages."

        lines = [f"# {lang['name']} ({lang['native']}) — Quick Lesson"]
        lines.append(f"Region: {lang['region']} | Speakers: {lang['speakers']} | Family: {lang['family']}")
        lines.append("")

        lines.append("## Greetings")
        for key in ["hello", "thank_you", "how_are_you", "goodbye", "welcome"]:
            phrase = self.PHRASES.get(key, {}).get(code, "—")
            lines.append(f"  {key.replace('_', ' ').title():<15} {phrase}")

        lines.append(f"\n## Numbers 1-10")
        nums = self.NUMBERS.get(code, {})
        if nums:
            for i in range(1, 11):
                lines.append(f"  {i:<3} {nums.get(i, '—')}")
        else:
            lines.append("  Numbers not yet available for this language.")

        if code in self.CULTURAL_NOTES:
            lines.append(f"\n## Cultural Note")
            lines.append(f"  {self.CULTURAL_NOTES[code]}")

        return "\n".join(lines)

    def greetings(self, language: str) -> str:
        """Get greetings for a language."""
        return self.learn_mode(language)

    def common_phrases(self, language: str) -> list[dict[str, str]]:
        """Get essential phrases for a language."""
        code = language.lower()[:2]
        return [{"phrase": k.replace("_", " ").title(), "translation": v.get(code, "—")}
                for k, v in self.PHRASES.items()]


if __name__ == "__main__":
    al = AfricanLanguages()
    print(al.learn_mode("zu"))
    print("\n---\n", al.translate("hello", "xh"))
    print("\n---\n", al.detect_language("Sawubona baba"))
