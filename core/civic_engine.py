"""
Consumer Shield for the ballot box — Civic & Voter Education (CIVIC-1) — 2026-09-30

Origin: an external paste proposed a "self-improving political science agent"
on LangGraph with five nodes and an autonomous web-scraping loop.

House verdicts (REJECT-6 precedent + anti-hallucination law):
  * LangGraph: REJECTED. The proposed graph is a linear five-node chain with
    no branching, no cycles and no heavy compute — plain functions behind
    FastAPI deliver the identical contract with zero new dependencies and
    zero added image weight (cost law: founder-funded, no revenue yet).
  * "Self-improving learning loop": REJECTED HARD. The paste's learning node
    incremented a float and then claimed the knowledge base was "validated
    and synchronized with latest public manifesto records" — a fabricated
    verification claim. This engine never does that. KNOWLEDGE_VERSION is a
    real constant bound to this curated file; update_status says plainly
    that this is a curated snapshot, not a live sync.
  * Party data: HARVESTED under the neutrality law. Six parties, alphabetical
    order (no ranking, no endorsement), identical fields and depth for every
    party, each entry attributed to the party's own published 2024 election
    manifesto, each carrying the honest caveat to confirm against the current
    official document.
  * Voter education: HARVESTED. Balanced, non-partisan: why participation
    matters AND what disengagement risks — plus the official IEC channels.

Laws honoured:
  * Non-partisan by construction: alphabetical ordering, equal field depth,
    no evaluative language, no recommendations. Education, never campaigning.
  * Every response carries the disclaimer: civic education, not political
    advice; confirm with the IEC and the parties' official manifestos.
  * Deterministic only — same request, same answer. No LLM, no scraping.
  * Kill switch: DISABLED_ENGINES containing "civic_engine" -> 503, honestly.
"""
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/civic", tags=["Civic & Voter Education (CIVIC-1)"])

# Real version of THIS curated file — not an auto-incremented pretend metric.
KNOWLEDGE_VERSION = "2024-manifesto-snapshot.1"

DISCLAIMER = (
    "Non-partisan civic education only — this is NOT political advice and "
    "Luqi-ai does not endorse, rank or oppose any party. Party summaries are "
    "a curated snapshot of published 2024 election manifestos; confirm against "
    "each party's current official manifesto and the IEC (iec.org.za) before "
    "quoting or deciding."
)
NEUTRALITY_NOTE = (
    "Parties are listed alphabetically with identical depth. Ordering carries "
    "no meaning. No party is endorsed, ranked or omitted for editorial reasons."
)
MANIFESTO_CAVEAT = (
    "Curated from the party's published 2024 national election manifesto — "
    "confirm against the current official manifesto before quoting."
)

# ── Curated knowledge (snapshot; sources named; caveat attached) ─────────

POLITICAL_PARTIES: List[Dict[str, Any]] = [
    {"id": "actionsa", "party_name": "ActionSA",
     "core_ideology": "Classical liberalism / pragmatism (self-described)",
     "key_pillars": ["Rule of law and anti-corruption", "Economic deregulation",
                     "Strict border management"],
     "source": "ActionSA 2024 Election Manifesto (party's official publication)"},
    {"id": "anc", "party_name": "African National Congress (ANC)",
     "core_ideology": "Social democracy / liberation-movement legacy (self-described)",
     "key_pillars": ["Socio-economic transformation", "Public infrastructure",
                     "Social welfare safety nets"],
     "source": "ANC 2024 Election Manifesto (party's official publication)"},
    {"id": "da", "party_name": "Democratic Alliance (DA)",
     "core_ideology": "Liberalism / constitutionalism (self-described)",
     "key_pillars": ["Free-market growth", "Non-racialism",
                     "Service delivery efficiency"],
     "source": "DA 2024 Election Manifesto (party's official publication)"},
    {"id": "eff", "party_name": "Economic Freedom Fighters (EFF)",
     "core_ideology": "Marxist-Leninist / Pan-Africanism (self-described)",
     "key_pillars": ["Land redistribution without compensation",
                     "Nationalisation of key economic sectors", "Pan-African unity"],
     "source": "EFF 2024 Election Manifesto (party's official publication)"},
    {"id": "ifp", "party_name": "Inkatha Freedom Party (IFP)",
     "core_ideology": "African social conservatism / federalism (self-described)",
     "key_pillars": ["Devolution of power",
                     "Institutional role for traditional authorities",
                     "Community development"],
     "source": "IFP 2024 Election Manifesto (party's official publication)"},
    {"id": "mkp", "party_name": "uMkhonto weSizwe Party (MKP)",
     "core_ideology": "Left-wing nationalism / radical economic transformation (self-described)",
     "key_pillars": ["Constitutional overhaul", "State-led industrialisation",
                     "Traditional leadership integration"],
     "source": "MKP 2024 Election Manifesto (party's official publication)"},
]

LIBERATION_HISTORY: List[Dict[str, Any]] = [
    {"figure_or_movement": "Anti-apartheid & Pan-African liberation movements",
     "historical_impact": "Fought colonial oppression, disenfranchisement and racial segregation.",
     "civic_relevance": "Secured universal suffrage and foundational human rights — the constitutional right to vote exercised today.",
     "sources_via": "African History Archive: GET /v1/history/entries?q=liberation"},
    {"figure_or_movement": "1976 youth & student movements",
     "historical_impact": "Resisted systemic educational and socio-economic inequality.",
     "civic_relevance": "Demonstrated the decisive role of youth participation in shaping the country's political destiny.",
     "sources_via": "African History Archive: GET /v1/history/entries?q=1976"},
]

VOTING_IMPORTANCE = [
    "Direct accountability: voting forces elected officials to answer to public demands.",
    "Policy direction: ballots determine budget priorities for services, jobs and education.",
    "Honouring the liberation struggle: exercising rights secured at great cost.",
]
APATHY_RISKS = [
    "Abstaining lets a minority of active voters decide the country's direction for the majority.",
    "Low turnout reduces competitive pressure on whoever governs.",
    "Public complaints carry less leverage without participation in formal electoral mechanisms.",
]

VOTER_EDUCATION = {
    "registration": [
        "You must be a South African citizen, 16+ to register (18+ to vote), with a valid ID.",
        "Register at your local IEC office or online via the IEC voter portal.",
        "Check and update your registration status and voting station on the IEC site before election day.",
    ],
    "official_channels": {
        "iec": "https://www.elections.org.za (IEC — verify current registration steps and dates there; they can change)",
    },
    "honest_note": ("Election dates, registration weekends and procedures are set by the IEC "
                    "and change per cycle — always confirm on the official IEC channel above."),
}


def _party_view(p: Dict[str, Any]) -> Dict[str, Any]:
    """Identical shape for every party — neutrality enforced by construction."""
    return {"id": p["id"], "party_name": p["party_name"],
            "core_ideology": p["core_ideology"], "key_pillars": list(p["key_pillars"]),
            "source": p["source"], "verification": MANIFESTO_CAVEAT}


class CivicQueryRequest(BaseModel):
    user_query: str = Field(min_length=1, max_length=2_000)
    include_learning_loop: bool = Field(
        default=True,
        description="Accepted for paste-contract compatibility; the honest status is always returned.")


# ── Endpoints ─────────────────────────────────────────────────────────────

def _kill_switch() -> None:
    if "civic_engine" in os.getenv("DISABLED_ENGINES", ""):
        raise HTTPException(status_code=503, detail={
            "error": "civic engine offline (kill switch)", "fail_closed": True})


@router.get("/parties")
async def list_parties() -> Dict[str, Any]:
    """The neutral party landscape — alphabetical, equal depth, sourced."""
    _kill_switch()
    return {"knowledge_version": KNOWLEDGE_VERSION,
            "party_count": len(POLITICAL_PARTIES),
            "ordering": "alphabetical — no ranking, no endorsement",
            "parties": [_party_view(p) for p in POLITICAL_PARTIES],
            "neutrality": NEUTRALITY_NOTE, "disclaimer": DISCLAIMER}


@router.get("/parties/{party_id}")
async def party_detail(party_id: str) -> Dict[str, Any]:
    _kill_switch()
    for p in POLITICAL_PARTIES:
        if p["id"] == party_id:
            return {"knowledge_version": KNOWLEDGE_VERSION, "party": _party_view(p),
                    "neutrality": NEUTRALITY_NOTE, "disclaimer": DISCLAIMER}
    raise HTTPException(status_code=404, detail={
        "error": f"party '{party_id}' not in the curated snapshot",
        "honest_note": "six parties are curated so far; absence is a curation gap, not a judgement",
        "available": [p["id"] for p in POLITICAL_PARTIES]})


@router.get("/history")
async def liberation_history() -> Dict[str, Any]:
    """Why the vote exists at all — sourced context, deeper archive linked."""
    _kill_switch()
    return {"knowledge_version": KNOWLEDGE_VERSION, "entries": LIBERATION_HISTORY,
            "deeper_archive": "GET /v1/history (African History Archive — sourced entries)",
            "disclaimer": DISCLAIMER}


@router.get("/voter-education")
async def voter_education() -> Dict[str, Any]:
    """Balanced participation education + the official IEC channels."""
    _kill_switch()
    return {"knowledge_version": KNOWLEDGE_VERSION,
            "why_voting_matters": VOTING_IMPORTANCE,
            "risks_of_disengagement": APATHY_RISKS,
            "how_to_register": VOTER_EDUCATION["registration"],
            "official_channels": VOTER_EDUCATION["official_channels"],
            "honest_note": VOTER_EDUCATION["honest_note"],
            "disclaimer": DISCLAIMER}


@router.post("/empowerment-guidance")
async def empowerment_guidance(req: CivicQueryRequest) -> Dict[str, Any]:
    """The paste's endpoint — honoured in shape, honest in substance.

    Returns historical context, balanced participation analysis and the
    neutral party landscape. The 'learning loop' field is answered with the
    truth: this is a curated snapshot with a real version constant, not a
    live-syncing agent — no validation is claimed that did not happen."""
    _kill_switch()
    return {"status": "success",
            "knowledge_version": KNOWLEDGE_VERSION,
            "update_status": ("Curated snapshot served as-is. No live sync or "
                              "re-validation was performed for this answer — the "
                              "sources and caveat on each entry are the verification path."),
            "learning_loop_requested": req.include_learning_loop,
            "learning_loop_honest_status": ("not a live agent — deterministic curated "
                                            "knowledge, updated by reviewed commits only"),
            "historical_context": LIBERATION_HISTORY,
            "history_summary": ("Civic rights and the power to vote were secured through "
                                "historical struggle; voting honours those who sacrificed "
                                "for full constitutional representation."),
            "voting_importance": VOTING_IMPORTANCE,
            "apathy_risks": APATHY_RISKS,
            "party_landscape": [_party_view(p) for p in POLITICAL_PARTIES],
            "query_received": req.user_query,
            "query_note": ("The landscape is shown in full rather than filtered by the "
                           "query — filtering would editorialize. Compare on the sourced "
                           "pillars themselves."),
            "neutrality": NEUTRALITY_NOTE,
            "disclaimer": DISCLAIMER}
