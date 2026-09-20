"""UNIFY-11 + UNIFY-10 verification — citation layer contract + unified deep
research pipeline (mocked retrieval, deterministic offline)."""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.deep_research as dr
from core.citations import router as cit_router, Citation, wrap_answer, verify_citation
from core.deep_research import router as dr_router

app = FastAPI()
app.include_router(cit_router)
app.include_router(dr_router)
c = TestClient(app)

def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        sys.exit(1)

# ── Citation layer unit checks ────────────────────────────────────────────
v = verify_citation(Citation(title="Paper A", source="crossref", doi="10.1234/abc"))
check("doi citation verifiable", v.verifiable and v.locator == "https://doi.org/10.1234/abc")
v = verify_citation(Citation(title="Paper B", source="pubmed", pmid="12345678"))
check("pmid citation verifiable", v.verifiable and "pubmed.ncbi.nlm.nih.gov/12345678" in v.locator)
v = verify_citation(Citation(title="Paper C", source="openalex", url="https://openalex.org/W123"))
check("url citation verifiable", v.verifiable)
v = verify_citation(Citation(title="Paper D", source="memory"))
check("locatorless citation NOT verifiable", not v.verifiable)
v = verify_citation(Citation(title="Bad", source="x", url="javascript:alert(1)"))
check("non-http url rejected", not v.verifiable)

w = wrap_answer("Some answer", [Citation(title="P", source="crossref", doi="10.1234/x")])
check("wrap: verified with verifiable source", w.verification == "verified" and "VERIFIED" in w.label)
w = wrap_answer("Some answer", [])
check("wrap: zero sources -> UNVERIFIED label", w.verification == "unverified" and "UNVERIFIED" in w.label)
w = wrap_answer("Some answer", [Citation(title="P", source="memory")])
check("wrap: unverifiable sources -> UNVERIFIED", w.verification == "unverified")

# ── Citation endpoints ────────────────────────────────────────────────────
r = c.post("/v1/citations/verify", json={"citations": [
    {"title": "A", "source": "crossref", "doi": "10.1234/abc"},
    {"title": "B", "source": "memory"}]})
b = r.json()
check("verify endpoint 200", r.status_code == 200)
check("verify counts", b["verifiable_count"] == 1 and b["total"] == 2)
r = c.post("/v1/citations/wrap", json={"answer": "X", "citations": []})
check("wrap endpoint labels unverified", r.json()["verification"] == "unverified")
r = c.get("/v1/citations/contract")
check("contract documented", "UNVERIFIED" in r.json()["unverified_label"])

# ── Deep research: mocked retrieval ──────────────────────────────────────
HITS = {
    "openalex": lambda q, n: [
        {"title": "Attention Is All You Need", "authors": ["Vaswani"], "year": 2017,
         "citations": 90000, "url": "https://arxiv.org/abs/1706.03762", "source": "openalex", "doi": None}],
    "crossref": lambda q, n: [
        {"title": "Attention Is All You Need", "authors": ["Vaswani A"], "year": 2017,
         "citations": 88000, "url": "https://doi.org/10.5555/3295222.3295349",
         "source": "crossref", "doi": "10.5555/3295222.3295349"},
        {"title": "BERT: Pre-training of Deep Bidirectional Transformers", "authors": ["Devlin"],
         "year": 2019, "citations": 70000, "url": "https://doi.org/10.18653/v1/N19-1423",
         "source": "crossref", "doi": "10.18653/v1/N19-1423"}],
    "pubmed": lambda q, n: (_ for _ in ()).throw(ConnectionError("pubmed down")),  # forced failure
    "arxiv": lambda q, n: [
        {"title": "Attention Is All You Need", "authors": ["Vaswani"], "year": 2017,
         "citations": None, "url": "https://arxiv.org/abs/1706.03762", "source": "arxiv", "doi": None}],
}
dr.SOURCES.clear()
dr.SOURCES.update(HITS)

r = c.post("/v1/deep-research", json={"query": "What is the transformer architecture?", "mode": "extractive"})
check("deep-research 200", r.status_code == 200, str(r.status_code))
b = r.json()
res = b["result"]
check("brief produced", len(res["answer"]) > 100)
check("sourced brief VERIFIED", res["verification"] == "verified")
cits = res["citations"]
check("dedupe collapsed 3x Attention to 1", sum(1 for x in cits if "Attention" in x["title"]) == 1,
      str([x["title"] for x in cits]))
check("BERT retained", any("BERT" in x["title"] for x in cits))
check("every citation verifiable", res["verifiable_count"] == len(cits) and res["unverifiable_count"] == 0)
check("pubmed failure isolated", "pubmed" in b["retrieval"]["source_failures"],
      str(b["retrieval"]["source_failures"]))
check("per-source hit counts", b["retrieval"]["per_source_hits"]["crossref"] >= 2)
check("extractive mode reported", b["synthesis_mode"] == "extractive")
check("plan has sub-queries", len(b["plan"]["sub_queries"]) >= 1)
check("crossref doi preserved", any(x.get("doi") == "10.18653/v1/N19-1423" for x in cits))

# ── Zero sources -> no synthesis, UNVERIFIED (anti-hallucination law) ────
dr.SOURCES.clear()
dr.SOURCES.update({k: (lambda q, n: []) for k in HITS})
r = c.post("/v1/deep-research", json={"query": "something obscure with no results", "mode": "extractive"})
b = r.json()
check("zero hits -> synthesis none", b["synthesis_mode"] == "none")
check("zero hits -> UNVERIFIED", b["result"]["verification"] == "unverified")
check("zero hits -> refusal mentions sources", "will not answer from memory" in b["result"]["answer"])

# ── LLM mode: mocked kimi, citation-grounded prompt ──────────────────────
dr.SOURCES.clear()
dr.SOURCES.update(HITS)
captured = {}
def fake_chat(system, user, **kw):
    captured["system"], captured["user"] = system, user
    return "Transformers use self-attention [1]. BERT extends this [2]. Bottom line: sourced."
import os
os.environ["KIMI_API_KEY"] = "test-key-not-real"
dr.kimi_client.chat_completion = fake_chat
r = c.post("/v1/deep-research", json={"query": "What is the transformer architecture?", "mode": "llm"})
b = r.json()
check("llm mode brief", b["synthesis_mode"] == "llm")
check("llm answer ships with citations", b["result"]["verification"] == "verified")
check("llm prompt contains ONLY real sources", "Attention Is All You Need" in captured["user"]
      and "10.18653/v1/N19-1423" in captured["user"])
check("llm prompt forbids invention", "Never introduce a fact" in captured["system"])
del os.environ["KIMI_API_KEY"]

# ── llm mode without key -> fail-closed 500 ──────────────────────────────
r = c.post("/v1/deep-research", json={"query": "transformers", "mode": "llm"})
check("llm without key -> 500", r.status_code == 500)

# ── Query planning determinism ────────────────────────────────────────────
p1 = dr.plan_query("What is photosynthesis? How does it work?")
p2 = dr.plan_query("What is photosynthesis? How does it work?")
check("planning deterministic", p1 == p2)
check("multi-part produces sub-queries", len(p1["sub_queries"]) >= 2, str(p1["sub_queries"]))

# ── main.py mounts both ───────────────────────────────────────────────────
import importlib, core.main as m
importlib.reload(m)
paths = [getattr(r_, "path", "") for r_ in m.app.routes]
check("main mounts /v1/citations", any(p.startswith("/v1/citations") for p in paths))
check("main mounts /v1/deep-research", any(p.startswith("/v1/deep-research") for p in paths))

print("\nALL CITATION + DEEP-RESEARCH CHECKS PASSED")
