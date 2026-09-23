"""
Unified i18n engine layer — UNIFY-14 (luqi-ai #63)

One engine-level i18n owner serving web/ and cli/ over the same contract:

  - Language negotiation (RFC 7231 Accept-Language, q-values, prefix match)
  - UI string catalogue resolved per locale with EXPLICIT per-key fallback —
    English fallback is always flagged, never silent (acceptance law)
  - Translation memory in Postgres (i18n_strings, migration 007): seeded UI
    catalogue + cached machine translations, one lookup path for all clients

The 22-language registry backs the platform's 22-language claim honestly:
coverage stats per language show exactly how much is translated (seeded)
vs what falls back — no inflated claims.
"""
import asyncio
import hashlib
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/i18n", tags=["i18n"])

DEFAULT_LOCALE = "en"

# ── The 22-language registry (11 official SA spoken + 11 African/global) ──
LANGUAGES: Dict[str, Dict[str, str]] = {
    "en":  {"name": "English",     "native": "English",     "region": "ZA"},
    "zu":  {"name": "Zulu",        "native": "isiZulu",     "region": "ZA"},
    "xh":  {"name": "Xhosa",       "native": "isiXhosa",    "region": "ZA"},
    "af":  {"name": "Afrikaans",   "native": "Afrikaans",   "region": "ZA"},
    "st":  {"name": "Sesotho",     "native": "Sesotho",     "region": "ZA"},
    "tn":  {"name": "Setswana",    "native": "Setswana",    "region": "ZA"},
    "nso": {"name": "Sepedi",      "native": "Sepedi",      "region": "ZA"},
    "ts":  {"name": "Xitsonga",    "native": "Xitsonga",    "region": "ZA"},
    "ss":  {"name": "Siswati",     "native": "siSwati",     "region": "ZA"},
    "ve":  {"name": "Tshivenda",   "native": "Tshivenda",   "region": "ZA"},
    "nr":  {"name": "Ndebele",     "native": "isiNdebele",  "region": "ZA"},
    "sw":  {"name": "Swahili",     "native": "Kiswahili",   "region": "EA"},
    "pt":  {"name": "Portuguese",  "native": "Português",   "region": "MZ/AO"},
    "fr":  {"name": "French",      "native": "Français",    "region": "WA/CA"},
    "ar":  {"name": "Arabic",      "native": "العربية",      "region": "NA"},
    "yo":  {"name": "Yoruba",      "native": "Yorùbá",      "region": "NG"},
    "ig":  {"name": "Igbo",        "native": "Igbo",        "region": "NG"},
    "ha":  {"name": "Hausa",       "native": "Hausa",       "region": "NG"},
    "am":  {"name": "Amharic",     "native": "አማርኛ",         "region": "ET"},
    "so":  {"name": "Somali",      "native": "Soomaali",    "region": "SO"},
    "lg":  {"name": "Luganda",     "native": "Luganda",     "region": "UG"},
    "sn":  {"name": "Shona",       "native": "chiShona",    "region": "ZW"},
}

# ── Seed UI catalogue (real translations; source="seed") ─────────────────
# 12 keys covering one full page flow (landing/status/actions/footer).
SEED_STRINGS: Dict[str, Dict[str, str]] = {
    "app.name": {l: "Luqi-ai" for l in LANGUAGES},
    "app.tagline": {
        "en": "Sovereign intelligence for South Africa",
        "zu": "Ubuhlakani bezwe laseNingizimu Afrika",
        "xh": "Ubulumko belizwe laseMzantsi Afrika",
        "af": "Souvereine intelligensie vir Suid-Afrika",
        "st": "Bohlale ba naha bakeng sa Afrika Borwa",
        "sw": "Akili huru kwa ajili ya Afrika Kusini",
        "fr": "Intelligence souveraine pour l'Afrique du Sud",
        "pt": "Inteligência soberana para a África do Sul",
    },
    "status.operational": {
        "en": "operational", "zu": "lusebenza", "xh": "lusebenza",
        "af": "operasioneel", "st": "e sebetsa", "sw": "inafanya kazi",
        "fr": "opérationnel", "pt": "operacional",
    },
    "status.degraded": {
        "en": "degraded", "zu": "lunciphile", "xh": "luncuthekile",
        "af": "verswak", "st": "e fokotsehile", "sw": "imezorota",
        "fr": "dégradé", "pt": "degradado",
    },
    "nav.health": {
        "en": "Health", "zu": "Impilo", "xh": "Mpilo", "af": "Gesondheid",
        "st": "Bophelo", "sw": "Afya", "fr": "Santé", "pt": "Saúde",
    },
    "nav.companion": {
        "en": "Companion", "zu": "Umlingani", "xh": "Umlingani",
        "af": "Metgesel", "st": "Molekane", "sw": "Msahaba",
        "fr": "Compagnon", "pt": "Companheiro",
    },
    "nav.research": {
        "en": "Research", "zu": "Ucwaningo", "xh": "Uphando",
        "af": "Navorsing", "st": "Dinyakisiso", "sw": "Utafiti",
        "fr": "Recherche", "pt": "Pesquisa",
    },
    "cta.ask_luqi": {
        "en": "Ask Luqi", "zu": "Buza uLuqi", "xh": "Buza uLuqi",
        "af": "Vra Luqi", "st": "Botsa Luqi", "sw": "Muulize Luqi",
        "fr": "Demander à Luqi", "pt": "Perguntar à Luqi",
    },
    "cta.check_scam": {
        "en": "Check a scam", "zu": "Hlola inkohliso", "xh": "Jonga inkohliso",
        "af": "Kontroleer bedrog", "st": "Tlhola tshenyehetso",
        "sw": "Kagua ulaghai", "fr": "Vérifier une arnaque", "pt": "Verificar um golpe",
    },
    "cta.deep_research": {
        "en": "Deep research", "zu": "Ucwaningo olujulile", "xh": "Uphando oluthe nzulu",
        "af": "Diep navorsing", "st": "Dinyakisiso tse tebileng", "sw": "Utafiti wa kina",
        "fr": "Recherche approfondie", "pt": "Pesquisa aprofundada",
    },
    "companion.greeting": {
        "en": "Sawubona! I'm Luqi — how can I help today?",
        "zu": "Sawubona! NginguLuqi — ngingakusiza ngani namuhla?",
        "xh": "Molo! NdinguLuqi — ndikuncede ngantoni namhlanje?",
        "af": "Hallo! Ek is Luqi — hoe kan ek vandag help?",
        "st": "Dumela! Ke Luqi — nka thusa jwang kajeno?",
        "sw": "Habari! Mimi ni Luqi — nikusaidie vipi leo?",
        "fr": "Bonjour ! Je suis Luqi — comment puis-je aider aujourd'hui ?",
        "pt": "Olá! Sou a Luqi — como posso ajudar hoje?",
    },
    "msg.english_fallback": {
        "en": "This text has not been translated yet — showing English.",
        "zu": "Lombhalo awukahunyushwa okwamanje — sikukhombisa ngesiNgisi.",
        "xh": "Eli bhalo alikaguqulwa okwangoku — sikubonisa ngesiNgesi.",
        "af": "Hierdie teks is nog nie vertaal nie — Engels word gewys.",
        "st": "Sengwalwa sena ha se eso fetolelwe — re bontsha Senyesemane.",
        "sw": "Maandishi haya bado hayajatafsiriwa — tunaonyesha Kiingereza.",
        "fr": "Ce texte n'est pas encore traduit — affichage en anglais.",
        "pt": "Este texto ainda não foi traduzido — a mostrar em inglês.",
    },
    "footer.sovereignty": {
        "en": "Your data stays in your country.",
        "zu": "Idatha yakho ihlala ezweni lakho.",
        "xh": "Idatha yakho ihlala elizweni lakho.",
        "af": "Jou data bly in jou land.",
        "st": "Data ya hao e dula naheng ya hao.",
        "sw": "Data yako hubaki nchini kwako.",
        "fr": "Vos données restent dans votre pays.",
        "pt": "Os seus dados ficam no seu país.",
    },
}


# ── Negotiation (RFC 7231) ───────────────────────────────────────────────

def parse_accept_language(header: str) -> List[Tuple[str, float]]:
    """Parse an Accept-Language header into [(tag, q)] sorted by preference."""
    out = []
    for part in (header or "").split(","):
        part = part.strip()
        if not part:
            continue
        if ";" in part:
            tag, _, params = part.partition(";")
            q = 1.0
            for p in params.split(";"):
                p = p.strip()
                if p.startswith("q="):
                    try:
                        q = float(p[2:])
                    except ValueError:
                        q = 0.0
            out.append((tag.strip().lower(), q))
        else:
            out.append((part.lower(), 1.0))
    out.sort(key=lambda t: -t[1])
    return [(t, q) for t, q in out if q > 0 and t != "*"]


def negotiate(header: str) -> Dict[str, Any]:
    """Match the header against the registry. Fallback to English is always
    EXPLICIT — the response says so, with the reason."""
    candidates = parse_accept_language(header)
    for tag, q in candidates:
        if tag in LANGUAGES:
            return {"requested_header": header, "candidates": [{"tag": t, "q": q2} for t, q2 in candidates],
                    "served": tag, "fallback": False,
                    "reason": f"exact match '{tag}' (q={q})"}
        base = tag.split("-", 1)[0]
        if base in LANGUAGES:
            return {"requested_header": header, "candidates": [{"tag": t, "q": q2} for t, q2 in candidates],
                    "served": base, "fallback": False,
                    "reason": f"prefix match '{tag}' -> '{base}' (q={q})"}
    return {"requested_header": header, "candidates": [{"tag": t, "q": q2} for t, q2 in candidates],
            "served": DEFAULT_LOCALE, "fallback": True,
            "reason": "no supported language in request — explicit English fallback"}


# ── Translation memory (Postgres; lazy seed) ─────────────────────────────

_seeded_engines: set = set()


def _seed(engine) -> None:
    """Idempotently seed the UI catalogue into i18n_strings."""
    if id(engine) in _seeded_engines:
        return
    from sqlalchemy.orm import Session
    from .i18n_models import I18nString

    with Session(engine) as s:
        existing = s.query(I18nString).filter_by(source="seed").first()
        if existing is None:
            for key, per_locale in SEED_STRINGS.items():
                for locale, text in per_locale.items():
                    s.merge(I18nString(key=key, locale=locale, text=text, source="seed"))
            s.commit()
    _seeded_engines.add(id(engine))


def _tm_get(engine, key: str, locale: str) -> Optional[str]:
    from sqlalchemy.orm import Session
    from .i18n_models import I18nString

    with Session(engine) as s:
        row = s.get(I18nString, (key, locale))
        return row.text if row else None


def _tm_put(engine, key: str, locale: str, text: str, source: str) -> None:
    from sqlalchemy.orm import Session
    from .i18n_models import I18nString

    with Session(engine) as s:
        s.merge(I18nString(key=key, locale=locale, text=text,
                           source=source, updated_at=datetime.utcnow()))
        s.commit()


def _resolve_catalogue(engine, locale: str) -> Dict[str, Any]:
    """Resolve every catalogue key for a locale with PER-KEY fallback flags —
    the never-silent guarantee made inspectable."""
    strings = {}
    translated = 0
    for key, per_locale in SEED_STRINGS.items():
        text = _tm_get(engine, key, locale) if engine else None
        if text is None:
            text = per_locale.get(locale)
        if text is None:
            strings[key] = {"text": per_locale[DEFAULT_LOCALE], "translated": False, "fallback": True}
        else:
            translated += 1
            strings[key] = {"text": text, "translated": True, "fallback": False}
    return {
        "locale": locale,
        "strings": strings,
        "coverage": {"keys_total": len(SEED_STRINGS), "keys_translated": translated,
                     "keys_on_english_fallback": len(SEED_STRINGS) - translated},
        "fallback_notice": SEED_STRINGS["msg.english_fallback"].get(
            locale, SEED_STRINGS["msg.english_fallback"]["en"]) if translated < len(SEED_STRINGS) else None,
    }


# ── Schemas ──────────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    target: str = Field(min_length=2, max_length=10)
    source_locale: str = Field(default="en", max_length=10)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/languages")
async def list_languages(request: Request) -> Dict[str, Any]:
    """The 22-language registry with HONEST coverage stats."""
    engine = getattr(request.app.state, "db_engine", None)
    out = []
    for code, meta in LANGUAGES.items():
        translated = sum(1 for k in SEED_STRINGS if code in SEED_STRINGS[k])
        out.append({**meta, "code": code, "catalogue_keys_translated": translated,
                    "catalogue_keys_total": len(SEED_STRINGS)})
    return {"default_locale": DEFAULT_LOCALE, "count": len(LANGUAGES), "languages": out}


@router.get("/negotiate")
async def negotiate_endpoint(request: Request) -> Dict[str, Any]:
    """Negotiate the request's Accept-Language against the registry.
    This is the contract both web/ (browser header) and cli/ (LUQI_LANG ->
    header) call — one negotiation path for every client."""
    return negotiate(request.headers.get("accept-language", ""))


@router.get("/strings")
async def strings(request: Request, lang: Optional[str] = None) -> Dict[str, Any]:
    """Resolved UI catalogue for a locale (?lang= or Accept-Language).
    Every key carries translated/fallback flags — English fallback is
    explicit, never silent."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        await asyncio.to_thread(_seed, engine)
    neg = negotiate(lang or request.headers.get("accept-language", ""))
    return {"negotiation": neg, **_resolve_catalogue(engine, neg["served"])}


@router.post("/translate")
async def translate(req: TranslateRequest, request: Request) -> Dict[str, Any]:
    """Translate text into a supported language with Postgres translation
    memory: TM hit -> instant, no LLM; miss -> machine translate, then cache.
    Fail-closed without an LLM key on a TM miss."""
    target = req.target.lower().split("-", 1)[0]
    if target not in LANGUAGES:
        raise HTTPException(status_code=400, detail={
            "error": f"unsupported target '{req.target}'",
            "supported": sorted(LANGUAGES), "fallback": DEFAULT_LOCALE,
            "note": "no silent fallback — choose explicitly"})
    if target == req.source_locale:
        return {"text": req.text, "translated": req.text, "target": target,
                "from_memory": False, "machine_translated": False, "fallback": False}

    engine = getattr(request.app.state, "db_engine", None)
    tm_key = "tm:" + hashlib.sha256(f"{req.source_locale}>{target}:{req.text}".encode()).hexdigest()[:24]

    if engine is not None:
        await asyncio.to_thread(_seed, engine)
        cached = await asyncio.to_thread(_tm_get, engine, tm_key, target)
        if cached is not None:
            return {"text": req.text, "translated": cached, "target": target,
                    "from_memory": True, "machine_translated": True, "fallback": False}

    if not os.getenv("KIMI_API_KEY"):
        raise HTTPException(status_code=500, detail={
            "error": "translation unavailable: not in translation memory and no LLM key",
            "fail_closed": True})

    from . import kimi_client
    try:
        import requests as _rq
        translated = await asyncio.to_thread(
            kimi_client.chat_completion,
            f"You are a professional translator. Translate the user's text into "
            f"{LANGUAGES[target]['name']} ({LANGUAGES[target]['native']}). "
            f"Return ONLY the translation, no commentary.",
            req.text, timeout=45)
    except _rq.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Upstream AI unreachable: {e}")

    if engine is not None:
        await asyncio.to_thread(_tm_put, engine, tm_key, target, translated, "machine")
    return {"text": req.text, "translated": translated, "target": target,
            "from_memory": False, "machine_translated": True, "fallback": False}
