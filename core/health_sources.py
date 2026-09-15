"""
OMEGA-LUQI Keyless Health Data Layer - the review's five strongest sources.

DailyMed (NLM)  - drug labels + version history
RxNorm/RxNav    - concept status; LESSON APPLIED: properties.json returns {}
                  for obsolete/remapped/nonexistent alike - ALWAYS pair with
                  historystatus.json, which answers all four distinctly.
ClinicalTrials  - trial status via the history endpoint
PubChem PUG     - compound properties
openFDA         - drug label search

MEDICAL SAFETY: every response is labeled educational research data, not
clinical advice - same policy as universal_learning. HAPI FHIR test server is
deliberately EXCLUDED (public write-test data, per the review). disease.sh,
WHO GHO, NPI Registry: reserved (no version signal / single-purpose).

Every fetch is snapshot-recorded (core/snapshots.py): rewrites provable.
Polite shared rate gate for NLM hosts (review measured no limits; be polite).
"""
import asyncio
import threading
import time
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Query

from .geocoding import compute_delay
from .snapshots import record_snapshot, versions_held, rewrites_detected

router = APIRouter(prefix="/v1/health-data", tags=["Keyless Health Data"])

MEDICAL_DISCLAIMER = ("Educational research data from public registries "
                      "(NIH/FDA). Not medical advice, not a clinical reference. "
                      "Always consult a qualified health professional.")

_nlm_gate = {"last": 0.0}
_nlm_lock = threading.Lock()


def _polite_nlm() -> None:
    with _nlm_lock:
        delay = compute_delay(_nlm_gate["last"], time.time(), 1.0)
        if delay > 0:
            time.sleep(delay)
        _nlm_gate["last"] = time.time()


def _get(url: str, params: Dict[str, Any]) -> requests.Response:
    from .geocoding import _headers
    r = requests.get(url, headers=_headers(), params=params, timeout=20)
    r.raise_for_status()
    return r


def _finish(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload["medical_disclaimer"] = MEDICAL_DISCLAIMER
    return payload


# ---------------- verification primitives (the full article's lessons) ----------

_VERSION_RE = __import__("re").compile(rb'<versionNumber\s+value="([^"]+)"')


def extract_version_number(doc: bytes) -> str:
    """Parse the SERVED version out of a returned document - never trust the
    request echo. The article: ?spl_version=1 served version 8, HTTP 200."""
    m = _VERSION_RE.search(doc[:4000])
    return m.group(1).decode() if m else "<<ABSENT>>"


def is_html_response(body: bytes) -> bool:
    """HTTP 200 can be an HTML homepage, not a document (article: /{setid}/3.xml
    returned 75KB of DailyMed homepage with 200). Detect before indexing."""
    return b"<!DOCTYPE html" in body[:200] or b"<html" in body[:200]


def verify_version_request(wanted: str, body: bytes) -> Dict[str, Any]:
    served = extract_version_number(body)
    ok = served == wanted
    return {"wanted": wanted, "served": served, "served_as_asked": ok,
            "warning": None if ok else
            f"asked for v{wanted}, source served v{served} - old versions are not "
            "obtainable; the only copy of an old version is one taken while current"}


# ---------------- DailyMed ----------------

def dailymed_search(query: str, pagesize: int = 5) -> Dict[str, Any]:
    _polite_nlm()
    r = _get("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json",
             {"drug_name": query, "pagesize": pagesize})
    data = r.json().get("data", [])
    out = []
    for d in data:
        setid = d.get("setid", "")
        title = d.get("title", "")
        if not setid or not title:
            # all-zeros/empty setid -> HTTP 200 with an empty envelope:
            # "never existed" and "no history" arrive identically (article 2.1)
            out.append({"setid": setid or "(empty)", "title": title or "(empty)",
                        "empty_history": True,
                        "note": "empty envelope - record never existed OR has no history; indistinguishable by design"})
            continue
        versions = dailymed_versions(setid)
        out.append({"setid": setid, "title": title[:120],
                    "published_date": d.get("published_date", ""),
                    "versions_listed": versions,        # HISTORY entries, never spl_version
                    "rewrites_witnessed": rewrites_detected("dailymed", setid)})
    return _finish({"source": "dailmed", "query": query, "results": out})


def dailymed_versions(setid: str) -> int:
    _polite_nlm()
    r = _get(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}/history.json", {})
    body = r.content
    # Snapshot the history listing itself - key insight: the LIST is stable
    record_snapshot("dailymed", setid, "history-index", body)
    return int(r.json().get("metadata", {}).get("total_elements", 0))


# ---------------- RxNorm (the review's core lesson, applied) ----------------

def rxnorm_status(rxcui: str) -> Dict[str, Any]:
    """NEVER read properties.json alone: {} means obsolete OR remapped OR
    unknown. historystatus.json answers all four distinctly - so we always
    call it, exactly as the review demonstrated."""
    _polite_nlm()
    _get(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json", {})
    h = _get(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/historystatus.json", {})
    record_snapshot("rxnorm", rxcui, "historystatus", h.content)
    status = h.json().get("rxcuiStatusHistory", {}).get("metaData", {}).get("status", "UNKNOWN")
    return _finish({"source": "rxnorm", "rxcui": rxcui, "status": status,
                    "lesson": "properties.json alone collapses obsolete/remapped/unknown; "
                              "historystatus distinguishes them."})


# ---------------- ClinicalTrials.gov ----------------

def ctgov_status(nct: str) -> Dict[str, Any]:
    nct = nct.upper().strip()
    if not nct.startswith("NCT"):
        nct = "NCT" + nct
    r = _get(f"https://clinicaltrials.gov/api/int/studies/{nct}/history", {})
    record_snapshot("ctgov", nct, "history-index", r.content)
    data = r.json().get("data", {})
    versions = data.get("versions", [])
    latest_status = versions[-1].get("study", {}).get("status", "UNKNOWN") if versions else "UNKNOWN"
    return _finish({"source": "clinicaltrials", "nct": nct,
                    "versions": len(versions), "latest_status": latest_status})


# ---------------- PubChem ----------------

def pubchem_compound(name: str) -> Dict[str, Any]:
    r = _get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/"
             "MolecularFormula,MolecularWeight,XLogP,CanonicalSMILES/JSON", {})
    props = r.json().get("PropertyTable", {}).get("Properties", [{}])[0]
    return _finish({"source": "pubchem", "name": name,
                    "formula": props.get("MolecularFormula", ""),
                    "weight": props.get("MolecularWeight", ""),
                    "xlogp": props.get("XLogP"), "smiles": props.get("CanonicalSMILES", "")})


# ---------------- openFDA ----------------

def openfda_label(query: str, limit: int = 3) -> Dict[str, Any]:
    r = _get("https://api.fda.gov/drug/label.json",
             {"search": f'openfda.generic_name:"{query}"', "limit": limit})
    results = r.json().get("results", [])
    out = [{"brand": (x.get("openfda", {}).get("brand_name") or ["?"])[0],
            "manufacturer": (x.get("openfda", {}).get("manufacturer_name") or ["?"])[0],
            "purpose": (x.get("purpose") or [""])[0][:200]}
           for x in results]
    return _finish({"source": "openfda", "query": query, "results": out})


def _wrap(func):
    async def handler(*a, **k):
        try:
            return await asyncio.to_thread(func, *a, **k)
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503,
                                detail=f"Health registry unreachable: {e.__class__.__name__}")
    return handler


@router.get("/drug")
async def drug(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    return await _wrap(dailymed_search)(q)


@router.get("/drug/{rxcui}/status")
async def drug_status(rxcui: str) -> Dict[str, Any]:
    return await _wrap(rxnorm_status)(rxcui)


@router.get("/trial/{nct}")
async def trial(nct: str) -> Dict[str, Any]:
    return await _wrap(ctgov_status)(nct)


@router.get("/compound/{name}")
async def compound(name: str) -> Dict[str, Any]:
    return await _wrap(pubchem_compound)(name)


@router.get("/fda-label")
async def fda_label(q: str = Query(..., min_length=2)) -> Dict[str, Any]:
    return await _wrap(openfda_label)(q)
