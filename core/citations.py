"""
Citation layer — UNIFY-11 (luqi-ai #58)

Response-schema-level citation contract for the unified engine. The standing
user requirement: every factual answer must show its sources — "show we do
not hallucinate" — and anything without sources must SAY so.

The contract (law for every research/factual response):
  CitedAnswer {
    answer: str
    citations: [Citation]          # real, retrieved sources only
    verification: "verified"       # >= 1 verifiable citation attached
                | "unverified"     # no verifiable source — LABELLED, never hidden
    label: str                     # human-readable honesty banner
  }

A citation is VERIFIABLE iff it carries a resolvable locator:
  - an http(s) URL, or
  - a DOI (resolvable via doi.org), or
  - a PubMed ID (resolvable via pubmed.ncbi.nlm.nih.gov)
A citation with none of these is UNVERIFIABLE and is labelled as such —
it is still shown (transparency), but it cannot make an answer "verified".

Deterministic only: no LLM, no network calls, fully offline.
"""
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/citations", tags=["citation-layer"])

VERIFIED_LABEL = "VERIFIED — sources attached; check them yourself."
UNVERIFIED_LABEL = "UNVERIFIED — this answer carries no verifiable sources. Treat as unconfirmed."

_HTTPS_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_PMID_RE = re.compile(r"^\d{6,9}$")


class Citation(BaseModel):
    """One source reference. Produced by retrieval layers, never by the LLM."""
    title: str = Field(min_length=1, max_length=600)
    source: str = Field(default="unknown", max_length=60)   # openalex | crossref | pubmed | arxiv | ...
    url: Optional[str] = Field(default=None, max_length=1000)
    doi: Optional[str] = Field(default=None, max_length=200)
    pmid: Optional[str] = Field(default=None, max_length=12)
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    excerpt: Optional[str] = Field(default=None, max_length=2000)


class CitationVerdict(BaseModel):
    citation: Citation
    verifiable: bool
    locator: Optional[str]  # the canonical resolvable link, if any
    reason: str


class CitedAnswer(BaseModel):
    """The engine's response contract for factual/research answers."""
    answer: str
    citations: List[Citation]
    verification: str  # "verified" | "unverified"
    label: str
    verifiable_count: int
    unverifiable_count: int


def resolve_locator(c: Citation) -> Optional[str]:
    """Canonical resolvable link for a citation, or None."""
    if c.doi and _DOI_RE.match(c.doi):
        return f"https://doi.org/{c.doi}"
    if c.pmid and _PMID_RE.match(c.pmid):
        return f"https://pubmed.ncbi.nlm.nih.gov/{c.pmid}/"
    if c.url and _HTTPS_RE.match(c.url):
        return c.url
    return None


def verify_citation(c: Citation) -> CitationVerdict:
    locator = resolve_locator(c)
    if locator:
        via = "doi" if c.doi and locator.endswith(c.doi) else ("pmid" if "pubmed" in locator else "url")
        return CitationVerdict(citation=c, verifiable=True, locator=locator,
                               reason=f"resolvable via {via}")
    return CitationVerdict(citation=c, verifiable=False, locator=None,
                           reason="no resolvable locator (needs url, doi, or pmid)")


def wrap_answer(answer: str, citations: List[Citation]) -> CitedAnswer:
    """The response-schema enforcement: answers WITHOUT verifiable sources
    are explicitly labelled UNVERIFIED — the anti-hallucination guarantee
    is the label, not the omission."""
    verdicts = [verify_citation(c) for c in citations]
    verifiable = sum(1 for v in verdicts if v.verifiable)
    verified = verifiable > 0
    return CitedAnswer(
        answer=answer,
        citations=citations,
        verification="verified" if verified else "unverified",
        label=VERIFIED_LABEL if verified else UNVERIFIED_LABEL,
        verifiable_count=verifiable,
        unverifiable_count=len(citations) - verifiable,
    )


# ── Schemas ──────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    citations: List[Citation] = Field(min_length=1, max_length=100)


class WrapRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=50_000)
    citations: List[Citation] = Field(default_factory=list, max_length=100)


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/verify")
async def verify_batch(req: VerifyRequest) -> Dict[str, Any]:
    """Batch-verify citations: which carry a resolvable locator, and the
    canonical link for each."""
    verdicts = [verify_citation(c) for c in req.citations]
    return {
        "verdicts": [v.model_dump() for v in verdicts],
        "verifiable_count": sum(1 for v in verdicts if v.verifiable),
        "total": len(verdicts),
    }


@router.post("/wrap")
async def wrap(req: WrapRequest) -> CitedAnswer:
    """Wrap an answer in the citation contract. Zero verifiable citations
    does NOT hide the answer — it labels it UNVERIFIED, loudly."""
    return wrap_answer(req.answer, req.citations)


@router.get("/contract")
async def contract() -> Dict[str, Any]:
    """The citation contract — inspectable law for engine responses."""
    return {
        "rule": "factual/research answers MUST ship as CitedAnswer; no verifiable source => UNVERIFIED label",
        "verified_label": VERIFIED_LABEL,
        "unverified_label": UNVERIFIED_LABEL,
        "verifiable_locators": ["https?:// URL", "DOI (10.xxxx/...)", "PubMed ID"],
        "citation_schema": Citation.model_json_schema(),
        "cited_answer_schema": CitedAnswer.model_json_schema(),
    }
