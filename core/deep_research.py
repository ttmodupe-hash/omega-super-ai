"""
Unified deep research skill — UNIFY-10 (luqi-ai #59)

One coherent pipeline replacing the fragmented deep_research.py /
history_search.py / news_factcheck.py lineage:

    query planning -> real retrieval -> synthesis WITH citations

House guardrails (binding):
  - NO FAKE CITATIONS. Every citation in the output is a real hit from the
    retrieval layer (research_sources: OpenAlex / Crossref / PubMed / arXiv),
    passed through the citation layer (UNIFY-11). The LLM synthesizes over
    retrieved sources; it never invents them.
  - Zero retrieved sources => the brief is labelled UNVERIFIED via the
    citation contract — never silently "answered anyway".
  - Per-source isolation: one provider failing degrades, never breaks.
  - Synthesis modes: "llm" (Kimi, when key present), "extractive"
    (deterministic offline brief), "auto" (llm if key else extractive).
  - Guided refinement (KNOWLEDGE_GAP_POLICY v1.0.0, 2026-09-20): an optional
    context_hint is folded back into retrieval - no static dead ends.
"""
import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import kimi_client
from .citations import Citation, wrap_answer
from .research_sources import SOURCES

router = APIRouter(prefix="/v1/deep-research", tags=["deep-research"])

_MAX_SOURCES_PER_PROVIDER = 5
_MAX_TOTAL_SOURCES = 12
_SYNTHESIS_TIMEOUT_S = 60


# ── Query planning (deterministic) ───────────────────────────────────────

def plan_query(query: str, context_hint: Optional[str] = None) -> Dict[str, Any]:
    """Decompose the question into retrieval sub-queries. Deterministic —
    planning must be inspectable and cheap.

    KNOWLEDGE_GAP_POLICY v1.0.0 (2026-09-20) step 3: a user-supplied
    context_hint folds into retrieval as its own sub-query, so guided
    refinement actually changes what gets retrieved - never decorative."""
    sub_queries = [query.strip()]
    # Multi-part questions: each clause becomes its own retrieval target
    parts = [p.strip() for p in re.split(r"[?;]\s*", query) if len(p.strip()) > 25]
    for p in parts[1:3]:  # at most 2 extra sub-queries
        if p not in sub_queries:
            sub_queries.append(p)
    # A condensed variant: strip filler to sharpen provider recall
    condensed = re.sub(
        r"\b(please|can you|could you|tell me|explain|what is|what are|how does|how do|why is|why does)\b",
        "", query, flags=re.I)
    condensed = " ".join(condensed.replace("?", " ").split())
    if 10 < len(condensed) < len(query) and condensed not in sub_queries:
        sub_queries.append(condensed)
    if context_hint and context_hint.strip():
        hint_q = f"{query.strip()} {context_hint.strip()}"[:300]
        if hint_q not in sub_queries:
            sub_queries.append(hint_q)
    return {"original": query, "sub_queries": sub_queries[:5],
            "guided": bool(context_hint and context_hint.strip())}


# ── Retrieval (real providers, per-source isolation) ─────────────────────

def _hit_to_citation(hit: Dict[str, Any]) -> Optional[Citation]:
    title = (hit.get("title") or "").strip()
    if not title:
        return None
    year = hit.get("year")
    try:
        year = int(str(year)[:4]) if year else None
    except ValueError:
        year = None
    doi = hit.get("doi") or None
    if doi and doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    pmid = None
    url = hit.get("url") or None
    if hit.get("source") == "pubmed" and url:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
        if m:
            pmid = m.group(1)
    authors = [a if isinstance(a, str) else a.get("name", "") for a in (hit.get("authors") or [])][:4]
    return Citation(title=title[:600], source=hit.get("source", "unknown"),
                    url=url, doi=doi, pmid=pmid,
                    authors=[a for a in authors if a], year=year)


def _dedupe(citations: List[Citation]) -> List[Citation]:
    """Dedupe by DOI, then PMID, then normalized title."""
    seen = set()
    out = []
    for c in citations:
        keys = [k for k in (
            f"doi:{c.doi.lower()}" if c.doi else None,
            f"pmid:{c.pmid}" if c.pmid else None,
            "t:" + re.sub(r"\W+", "", c.title.lower())[:80],
        ) if k]
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        out.append(c)
    return out


async def retrieve(sub_queries: List[str], max_per_provider: int) -> Dict[str, Any]:
    """Fan out sub-queries over the scholarly providers. One provider down
    degrades the result set, never the request."""
    per_source: Dict[str, int] = {}
    failures: Dict[str, str] = {}
    all_hits: List[Citation] = []

    async def _one(name, fn, q):
        try:
            return name, await asyncio.to_thread(fn, q, max_per_provider), None
        except Exception as e:  # network/parse/HTTP — isolated per source
            return name, [], str(e)[:200]

    tasks = [_one(name, fn, q) for q in sub_queries for name, fn in SOURCES.items()]
    for name, hits, err in await asyncio.gather(*tasks):
        if err:
            failures[name] = err
        for h in hits:
            c = _hit_to_citation(h)
            if c:
                all_hits.append(c)
        per_source[name] = per_source.get(name, 0) + len(hits)

    return {
        "citations": _dedupe(all_hits)[:_MAX_TOTAL_SOURCES],
        "per_source_hits": per_source,
        "source_failures": failures,
    }


# ── Synthesis ────────────────────────────────────────────────────────────

_SYNTH_SYSTEM = (
    "You are Luqi's research synthesizer. Write a concise research brief that "
    "answers the question using ONLY the numbered sources below. Rules:\n"
    "- Cite claims inline as [1], [2], ... matching the source numbers.\n"
    "- Never introduce a fact that is not in the sources.\n"
    "- If the sources do not answer part of the question, say so explicitly.\n"
    "- End with a one-line 'Bottom line:' summary."
)


def _source_listing(citations: List[Citation]) -> str:
    lines = []
    for i, c in enumerate(citations, 1):
        ref = c.doi or c.url or (f"PMID {c.pmid}" if c.pmid else "")
        lines.append(f"[{i}] {c.title} ({c.source}{', ' + str(c.year) if c.year else ''}) {ref}")
    return "\n".join(lines)


def _extractive_brief(query: str, citations: List[Citation]) -> str:
    """Deterministic offline brief: the retrieved landscape, honestly framed.
    Used when no LLM key is available — no invented prose, just the sources
    and what they are."""
    lines = [
        f"Research brief (extractive mode — no LLM synthesis available): {query}",
        "",
        f"Retrieved {len(citations)} relevant sources across the scholarly providers:",
    ]
    for i, c in enumerate(citations, 1):
        byline = f" — {', '.join(c.authors[:3])}" if c.authors else ""
        lines.append(f"[{i}] {c.title}{byline} ({c.source}{', ' + str(c.year) if c.year else ''})")
    lines += [
        "",
        "Bottom line: these are the real sources the engine retrieved for your "
        "question — read them via the attached links. For a synthesized narrative "
        "answer, the engine needs its LLM key configured.",
    ]
    return "\n".join(lines)


async def synthesize(query: str, citations: List[Citation], mode: str) -> Dict[str, Any]:
    has_key = bool(os.getenv("KIMI_API_KEY"))
    effective = mode
    if mode == "auto":
        effective = "llm" if has_key else "extractive"
    if effective == "llm":
        if not has_key:
            raise HTTPException(status_code=500, detail="mode=llm requires KIMI_API_KEY (fail-closed).")
        try:
            import requests as _rq
            brief = await asyncio.to_thread(
                kimi_client.chat_completion,
                _SYNTH_SYSTEM,
                f"QUESTION: {query}\n\nSOURCES:\n{_source_listing(citations)}",
                timeout=_SYNTHESIS_TIMEOUT_S,
            )
            return {"brief": brief, "synthesis_mode": "llm"}
        except _rq.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Upstream AI unreachable: {e}")
    return {"brief": _extractive_brief(query, citations), "synthesis_mode": "extractive"}


# ── Endpoint ─────────────────────────────────────────────────────────────

class DeepResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    max_per_provider: int = Field(default=3, ge=1, le=_MAX_SOURCES_PER_PROVIDER)
    mode: str = Field(default="auto", pattern="^(auto|llm|extractive)$")
    # KNOWLEDGE_GAP_POLICY v1.0.0 step 3: user-guided context. When the first
    # retrieval misses, the user's own hint (synonyms, the local or technical
    # name, a document title, a spelling variant) becomes a retrieval sub-query.
    context_hint: Optional[str] = Field(None, max_length=1000)


@router.post("")
async def deep_research(req: DeepResearchRequest) -> Dict[str, Any]:
    """End-to-end: plan -> retrieve -> synthesize -> citation-contract wrap."""
    t0 = time.perf_counter()
    plan = plan_query(req.query, req.context_hint)
    retrieval = await retrieve(plan["sub_queries"], req.max_per_provider)
    citations = retrieval["citations"]

    if not citations:
        # Anti-hallucination law: no sources => no synthesized answer at all.
        wrapped = wrap_answer(
            "No verifiable sources could be retrieved for this query from the "
            "scholarly providers. I will not answer from memory alone — that is "
            "how hallucinations happen. This is not a dead end: call this "
            "endpoint again with a context_hint (synonyms, the local or "
            "technical name, a document title, a spelling variant) and your "
            "hint is routed straight back into retrieval.",
            [],
        )
        return {
            "plan": plan,
            "retrieval": retrieval,
            "synthesis_mode": "none",
            "result": wrapped.model_dump(),
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    synth = await synthesize(req.query, citations, req.mode)
    wrapped = wrap_answer(synth["brief"], citations)
    return {
        "plan": plan,
        "retrieval": retrieval,
        "synthesis_mode": synth["synthesis_mode"],
        "result": wrapped.model_dump(),
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }
