"""
OMEGA-LUQI Academic Literature Grounding Layer

REAL, free, key-less scholarly sources to ground the research engines with
verifiable citations (the antidote to LLM-invented references):
  Crossref  - api.crossref.org         (DOIs, citation counts)
  OpenAlex  - api.openalex.org         (bibliometrics, 250M works)
  PubMed    - NCBI E-utilities         (biomedical gold standard)
  arXiv     - export.arxiv.org         (AI/physics/math preprints)

Design:
  - Fixed hosts only: no user-supplied URLs, so no SSRF surface.
  - One source failing does not break the aggregate (per-source try/except).
  - Parsers are pure functions: fully unit-testable without network.
  - Etiquette: NCBI email param (polite pool), arXiv rate guidance in docs.
  - CORE (300M full-text): env-gated on CORE_API_KEY (free key from
    core.ac.uk/services/api); aggregate skips it cleanly when unset.
"""
import asyncio
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, Query

router = APIRouter(prefix="/v1/research", tags=["Academic Literature Grounding"])

CONTACT_EMAIL = "luqi-ai@localhost"  # override via ACADEMIC_CONTACT_EMAIL env


# ---------------- pure parsers (unit-tested offline) ----------------

def _parse_crossref(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for item in payload.get("message", {}).get("items", []):
        title = (item.get("title") or ["(untitled)"])[0]
        out.append({
            "title": title,
            "doi": item.get("DOI", ""),
            "cited_by": item.get("is-referenced-by-count", 0),
            "year": (item.get("issued", {}).get("date-parts", [[None]])[0][0]),
            "url": item.get("URL", ""),
            "source": "crossref",
        })
    return out


def _parse_openalex(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{
        "title": w.get("title", "(untitled)"),
        "doi": w.get("doi", ""),
        "cited_by": w.get("cited_by_count", 0),
        "year": w.get("publication_year"),
        "open_access": bool((w.get("open_access") or {}).get("is_oa")),
        "source": "openalex",
    } for w in payload.get("results", [])]


def _parse_pubmed_ids(payload: Dict[str, Any]) -> List[str]:
    return payload.get("esearchresult", {}).get("idlist", [])


def _parse_pubmed_summary(payload: Dict[str, Any], ids: List[str]) -> List[Dict[str, Any]]:
    result = payload.get("result", {})
    out = []
    for uid in ids:
        p = result.get(uid, {})
        if p:
            out.append({"title": p.get("title", "(untitled)"), "pmid": uid,
                        "year": p.get("pubdate", "")[:4], "source": "pubmed"})
    return out


_ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_arxiv(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)
    out = []
    for entry in root.findall("atom:entry", _ARXIV_NS):
        title = (entry.findtext("atom:title", default="(untitled)", namespaces=_ARXIV_NS) or "").strip()
        link = entry.find("atom:id", _ARXIV_NS)
        out.append({"title": " ".join(title.split()),
                    "url": link.text if link is not None else "",
                    "published": entry.findtext("atom:published", default="", namespaces=_ARXIV_NS)[:10],
                    "source": "arxiv"})
    return out


def _parse_core(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{
        "title": w.get("title", "(untitled)"),
        "doi": w.get("doi", ""),
        "full_text": bool(w.get("fullText")),
        "download_url": (w.get("downloadUrl") or ""),
        "source": "core",
    } for w in payload.get("results", [])]


# ---------------- live fetchers (blocking; offloaded) ----------------

def _email() -> str:
    import os
    return os.getenv("ACADEMIC_CONTACT_EMAIL", CONTACT_EMAIL)


def fetch_crossref(query: str, rows: int = 5) -> List[Dict[str, Any]]:
    r = requests.get("https://api.crossref.org/works",
                     params={"query": query, "rows": rows, "mailto": _email()},
                     timeout=15)
    r.raise_for_status()
    return _parse_crossref(r.json())


def fetch_openalex(query: str, per_page: int = 5) -> List[Dict[str, Any]]:
    r = requests.get("https://api.openalex.org/works",
                     params={"search": query, "per_page": per_page,
                             "sort": "cited_by_count:desc"}, timeout=15)
    r.raise_for_status()
    return _parse_openalex(r.json())


def fetch_pubmed(term: str, retmax: int = 5) -> List[Dict[str, Any]]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    s = requests.get(f"{base}/esearch.fcgi",
                     params={"db": "pubmed", "term": term, "retmax": retmax,
                             "retmode": "json", "email": _email()}, timeout=15)
    s.raise_for_status()
    ids = _parse_pubmed_ids(s.json())
    if not ids:
        return []
    d = requests.get(f"{base}/esummary.fcgi",
                     params={"db": "pubmed", "id": ",".join(ids),
                             "retmode": "json"}, timeout=15)
    d.raise_for_status()
    return _parse_pubmed_summary(d.json(), ids)


def fetch_arxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(f"all:{query}")
    r = requests.get(f"https://export.arxiv.org/api/query?search_query={q}"
                     f"&max_results={max_results}", timeout=15)
    r.raise_for_status()
    return _parse_arxiv(r.text)


_CORE_GATE = {"last": 0.0}
_CORE_GATE_LOCK = threading.Lock()
_CORE_DAILY = {"date": "", "used": 0}


def _core_rate_wait() -> None:
    """Shared client-side gate (CORE free tier is quota-limited; be polite).
    Default 1 call/sec, env-tunable via CORE_RATE_LIMIT_SECONDS."""
    import os as _os
    interval = float(_os.getenv("CORE_RATE_LIMIT_SECONDS", "1.0"))
    from .geocoding import compute_delay
    with _CORE_GATE_LOCK:
        delay = compute_delay(_CORE_GATE["last"], time.time(), interval)
        if delay > 0:
            time.sleep(delay)
        _CORE_GATE["last"] = time.time()


def core_daily_quota_ok() -> bool:
    """Daily cap (env CORE_DAILY_QUOTA, default 1000) - refuse politely."""
    import os as _os
    cap = int(_os.getenv("CORE_DAILY_QUOTA", "1000"))
    today = time.strftime("%Y-%m-%d")
    with _CORE_GATE_LOCK:
        if _CORE_DAILY["date"] != today:
            _CORE_DAILY.update(date=today, used=0)
        if _CORE_DAILY["used"] >= cap:
            return False
        _CORE_DAILY["used"] += 1
        return True


def fetch_core(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    import os as _os
    key = _os.getenv("CORE_API_KEY")
    if not key:
        raise RuntimeError("CORE_API_KEY not set - get a free key at core.ac.uk/services/api")
    if not core_daily_quota_ok():
        raise RuntimeError("CORE daily quota reached (CORE_DAILY_QUOTA) - try tomorrow")
    _core_rate_wait()
    r = requests.get("https://api.core.ac.uk/v3/search/works",
                     params={"q": query, "limit": limit},
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    if r.status_code == 429:
        remaining = r.headers.get("X-RateLimit-Remaining", "unknown")
        raise RuntimeError(f"CORE rate limit hit (429) - remaining quota: {remaining}. "
                           "Increase CORE_RATE_LIMIT_SECONDS or wait for the window.")
    r.raise_for_status()
    return _parse_core(r.json())


FETCHERS = {"crossref": fetch_crossref, "openalex": fetch_openalex,
            "pubmed": fetch_pubmed, "arxiv": fetch_arxiv, "core": fetch_core}


async def aggregate_literature(query: str, sources=None) -> Dict[str, Any]:
    """Query selected sources; a failure in one never breaks the rest."""
    import logging
    log = logging.getLogger("LuqiAcademicSources")
    sources = sources or list(FETCHERS)
    results: Dict[str, Any] = {}
    async def one(name):
        try:
            results[name] = await asyncio.to_thread(FETCHERS[name], query)
        except Exception as e:
            log.warning("Literature source %s failed (non-fatal): %s", name, e)
            results[name] = {"error": str(e)[:200]}
    await asyncio.gather(*(one(s) for s in sources if s in FETCHERS))
    return {"query": query, "sources": results}


@router.get("/literature")
async def search_literature(q: str = Query(..., min_length=2), source: str = "all"):
    """Public read-only scholarly search across free academic APIs."""
    sources = list(FETCHERS) if source == "all" else [s.strip() for s in source.split(",")]
    return await aggregate_literature(q, sources)
