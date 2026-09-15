"""
OMEGA-LUQI Knowledge Base - grounded answers from Luqi-AI's OWN documents.

Students/admins asking about the platform should get answers from the real
docs (EULA, deployment, manuals), not an LLM improvising. Excerpt-first
retrieval: returns the most relevant passages WITH source paths, so answers
are checkable - the same anti-hallucination principle as the literature layer.

Zero-dependency token-IDF scoring (sklearn optional upgrade later, same
philosophy as the hybrid engine: the safe layer never requires the heavy one).
"""
import math
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/v1/knowledge", tags=["Platform Knowledge Base"])

_DOC_DIRS = ["docs", "deploy"]
_DOC_FILES = ["README.md", "static/terms.html"]  # EULA: the platform's own policy doc
_MAX_DOCS = 60
_TOP_K = 3
_EXCERPT = 240


def _scan_docs(root: str) -> Dict[str, str]:
    docs: Dict[str, str] = {}
    for d in _DOC_DIRS:
        path = os.path.join(root, d)
        if os.path.isdir(path):
            for fn in sorted(os.listdir(path)):
                if fn.endswith(".md") and len(docs) < _MAX_DOCS:
                    try:
                        docs[f"{d}/{fn}"] = open(os.path.join(path, fn)).read()
                    except OSError:
                        pass
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text)


def _load_doc(path: str) -> str:
    raw = open(path).read()
    return _strip_html(raw) if path.endswith(".html") else raw


def _scan_docs(root: str) -> Dict[str, str]:
    docs: Dict[str, str] = {}
    for d in _DOC_DIRS:
        path = os.path.join(root, d)
        if os.path.isdir(path):
            for fn in sorted(os.listdir(path)):
                if fn.endswith(".md") and len(docs) < _MAX_DOCS:
                    try:
                        docs[f"{d}/{fn}"] = _load_doc(os.path.join(path, fn))
                    except OSError:
                        pass
    for fn in _DOC_FILES:
        p = os.path.join(root, fn)
        if os.path.exists(p):
            docs[fn] = _load_doc(p)
    return docs


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{3,}", text.lower())


class KnowledgeBase:
    """Tiny TF-IDF index over the repo's markdown. Lazy-built, rebuildable."""

    def __init__(self, root: str):
        self.root = root
        self.docs: Dict[str, str] = {}
        self.df: Dict[str, int] = {}
        self._built = False

    def build(self) -> None:
        self.docs = _scan_docs(self.root)
        self.df = {}
        for text in self.docs.values():
            for tok in set(_tokenize(text)):
                self.df[tok] = self.df.get(tok, 0) + 1
        self._built = True

    def search(self, query: str, top_k: int = _TOP_K) -> List[Dict[str, Any]]:
        if not self._built:
            self.build()
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        n = max(1, len(self.docs))
        scores: Dict[str, float] = {}
        for path, text in self.docs.items():
            tokens = _tokenize(text)
            if not tokens:
                continue
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            score = 0.0
            for qt in q_tokens:
                if qt in tf:
                    idf = math.log(1 + n / (1 + self.df.get(qt, 0)))
                    score += (tf[qt] / len(tokens)) * idf
            if score > 0:
                scores[path] = score
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [{"source": p, "score": round(s, 4), "excerpt": _excerpt_for(self.docs[p], q_tokens)}
                for p, s in ranked]

    def reload(self) -> None:
        self._built = False
        self.build()


def _excerpt_for(text: str, q_tokens: List[str]) -> str:
    low = text.lower()
    pos = min((low.find(t) for t in q_tokens if low.find(t) >= 0), default=0)
    start = max(0, pos - _EXCERPT // 3)
    snippet = text[start:start + _EXCERPT].replace("\n", " ").strip()
    return ("... " if start > 0 else "") + snippet + (" ..." if start + _EXCERPT < len(text) else "")


import os  # noqa: E402
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_kb = KnowledgeBase(_ROOT)


@router.get("/ask")
async def ask(q: str = Query(..., min_length=3)) -> Dict[str, Any]:
    """Public, grounded excerpts from Luqi-AI's own documents, with sources."""
    return {"query": q, "matches": _kb.search(q)}


from .admin_auth import verify_admin  # state-mutating endpoint - admin only


@router.post("/reload")
async def reload(is_authenticated: bool = Depends(verify_admin)) -> Dict[str, Any]:
    """Re-scan docs (after adding new documentation). Admin: mutates server state."""
    _kb.reload()
    return {"reloaded": True, "docs_indexed": len(_kb.docs)}
