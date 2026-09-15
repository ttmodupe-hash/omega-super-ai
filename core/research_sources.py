"""
OMEGA-LUQI Sovereign Research Grounding Layer

Free, keyless scholarly retrieval under the reasoning layer:
  OpenAlex   250M+ works     (best for bibliometrics)
  Crossref   150M+ works     (DOIs, citation counts)
  PubMed     36M+ biomedical (E-utilities esearch -> esummary)
  arXiv      2M+ preprints   (Atom XML)

Why this wins for luqi-ai:
  - ZERO token cost for retrieval; Kimi only synthesizes over real, cited papers.
  - Students get "the answer AND the papers it comes from" - the difference
    between a tutor and a chatbot.
  - Fixed public endpoints only: SSRF-immune by construction (no user URLs).
  - Failures isolated per source: one down source degrades, never breaks.

Grounding pattern for AI engines:
    hits = search_scholarly(query, max_results=5)
    context = "\n".join(f"[{h['source']}] {h['title']} ({h['year']}) - {h['url']}" for h in hits)
    await route_chat("deep_research", DIRECTIVE + "\nCite these sources:",
                     f"{context}\n\nQuestion: {query}")
"""
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import LuqiAuthManager, UserSessionProfile

logger = logging.getLogger("LuqiResearchLayer")
router = APIRouter(prefix="/v1/research", tags=["Scholarly Grounding"])

_MAILTO = os.getenv("SCHOLAR_MAILTO", "luqi-ai@localhost")
_TIMEOUT = 15

ENDPOINTS = {
    "openalex": "https://api.openalex.org/works",
    "crossref": "https://api.crossref.org/works",
    "pubmed_esearch": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
    "pubmed_esummary": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
    "arxiv": "http://export.arxiv.org/api/query",
}


def _norm(title, authors, year, citations, url, source, doi=None) -> Dict[str, Any]:
    return {"title": title, "authors": authors, "year": year,
            "citations": citations, "url": url, "source": source, "doi": doi}


def search_openalex(query: str, limit: int) -> List[Dict[str, Any]]:
    r = requests.get(ENDPOINTS["openalex"], params={
        "search": query, "per_page": limit, "sort": "cited_by_count:desc"}, timeout=_TIMEOUT)
    r.raise_for_status()
    out = []
    for w in r.json().get("results", []):
        out.append(_norm(w.get("title", ""), [a.get("display_name", "") for a in w.get("authorships", [])][:4],
                         w.get("publication_year"), w.get("cited_by_count"),
                         w.get("doi") or w.get("id", ""), "openalex", w.get("doi")))
    return out


def search_crossref(query: str, limit: int) -> List[Dict[str, Any]]:
    r = requests.get(ENDPOINTS["crossref"], params={
        "query": query, "rows": limit, "mailto": _MAILTO}, timeout=_TIMEOUT)  # polite pool
    r.raise_for_status()
    out = []
    for it in r.json().get("message", {}).get("items", []):
        authors = [f"{a.get('family', '')} {a.get('given', '')[:1]}".strip()
                   for a in it.get("author", [])][:4]
        year = (it.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
        out.append(_norm((it.get("title") or [""])[0], authors, year,
                         it.get("is-referenced-by-count"),
                         it.get("URL", ""), "crossref", it.get("DOI")))
    return out


def search_pubmed(query: str, limit: int) -> List[Dict[str, Any]]:
    s = requests.get(ENDPOINTS["pubmed_esearch"], params={
        "db": "pubmed", "term": query, "retmax": limit, "retmode": "json"}, timeout=_TIMEOUT)
    s.raise_for_status()
    ids = s.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    d = requests.get(ENDPOINTS["pubmed_esummary"], params={
        "db": "pubmed", "id": ",".join(ids), "retmode": "json"}, timeout=_TIMEOUT)
    d.raise_for_status()
    result = d.json().get("result", {})
    out = []
    for uid in ids:
        p = result.get(uid, {})
        out.append(_norm(p.get("title", ""), p.get("authors", [])[:4],
                         (p.get("pubdate", "") or "")[:4] or None, None,
                         f"https://pubmed.ncbi.nlm.nih.gov/{uid}/", "pubmed"))
    return out


def search_arxiv(query: str, limit: int) -> List[Dict[str, Any]]:
    r = requests.get(ENDPOINTS["arxiv"], params={
        "search_query": f"all:{quote(query)}", "max_results": limit,
        "sortBy": "relevance"}, timeout=_TIMEOUT)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(r.text)
    out = []
    for e in root.findall("a:entry", ns):
        title = " ".join((e.findtext("a:title", default="", namespaces=ns) or "").split())
        authors = [a.findtext("a:name", default="", namespaces=ns)
                   for a in e.findall("a:author", ns)][:4]
        published = e.findtext("a:published", default="", namespaces=ns) or ""
        out.append(_norm(title, authors, published[:4] or None, None,
                         e.findtext("a:id", default="", namespaces=ns) or "", "arxiv"))
    return out


SOURCES = {"openalex": search_openalex, "crossref": search_crossref,
           "pubmed": search_pubmed, "arxiv": search_arxiv}


class LiteratureQuery(BaseModel):
    query: str
    sources: Optional[List[str]] = None   # default: all four
    max_results: int = 5


@router.post("/literature-search")
async def literature_search(
    q: LiteratureQuery,
    current_user: UserSessionProfile = Depends(LuqiAuthManager.verify_session_token),
):
    """Keyless scholarly search across OpenAlex/Crossref/PubMed/arXiv.

    Auth-gated (upstream rate limits are shared community resources).
    Per-source failures are isolated and reported - one down source never
    breaks the response.
    """
    if not q.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    if q.max_results < 1 or q.max_results > 25:
        raise HTTPException(status_code=400, detail="max_results must be 1-25.")
    selected = q.sources or list(SOURCES)
    unknown = [s for s in selected if s not in SOURCES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown sources: {unknown}")

    import asyncio
    results, failed = [], []

    def _run(src):
        try:
            return SOURCES[src](q.query, q.max_results), None
        except Exception as e:
            logger.warning("Research source %s failed: %s", src, e)
            return [], src

    for src in selected:
        hits, err = await asyncio.to_thread(_run, src)
        results.extend(hits)
        if err:
            failed.append(err)

    results.sort(key=lambda h: -(h.get("citations") or 0))
    return {"query": q.query, "results": results[:q.max_results * len(selected)],
            "meta": {"sources_used": [s for s in selected if s not in failed],
                     "sources_failed": failed}}
