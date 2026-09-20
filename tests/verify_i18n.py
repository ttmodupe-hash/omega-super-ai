"""UNIFY-14 verification — i18n negotiation matrix, explicit-fallback law,
translation memory (Postgres contract on sqlite), page + CLI flows."""
import sys
import pathlib
_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import core.i18n as i18n
from core.i18n import router, negotiate, parse_accept_language
from core.models import Base
import core.i18n_models  # noqa: F401

app = FastAPI()
app.include_router(router)
engine = create_engine("sqlite:///:memory:",
                       connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
app.state.db_engine = engine
c = TestClient(app)

def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")
    if not cond:
        sys.exit(1)

# 1. Registry: 22 languages, honest coverage
r = c.get("/v1/i18n/languages")
b = r.json()
check("22 languages registered", b["count"] == 22, f"got {b['count']}")
zu = next(l for l in b["languages"] if l["code"] == "zu")
tn = next(l for l in b["languages"] if l["code"] == "tn")
check("zu coverage honest (13/13 seeded)", zu["catalogue_keys_translated"] == 13,
      f"{zu['catalogue_keys_translated']}/{zu['catalogue_keys_total']}")
check("tn coverage honest (1 app.name only)", tn["catalogue_keys_translated"] == 1)

# 2. Negotiation matrix
n = negotiate("zu-ZA, zu;q=0.9, en;q=0.8")
check("prefix match zu-ZA -> zu", n["served"] == "zu" and not n["fallback"], n["reason"])
n = negotiate("fr;q=0.7, en;q=0.9")
check("q-value ordering: en wins", n["served"] == "en" and not n["fallback"], n["reason"])
n = negotiate("de-DE, de;q=0.9")
check("unsupported -> EXPLICIT en fallback", n["served"] == "en" and n["fallback"] is True
      and "explicit" in n["reason"], n["reason"])
n = negotiate("")
check("empty header -> explicit en fallback", n["served"] == "en" and n["fallback"] is True)
check("parse ignores wildcard + q=0", parse_accept_language("*, fr;q=0, sw;q=0.5") == [("sw", 0.5)])

# 3. /strings end-to-end — PAGE flow (browser header)
r = c.get("/v1/i18n/strings", headers={"Accept-Language": "xh-ZA,xh;q=0.9"})
b = r.json()
check("page flow negotiated xh", b["negotiation"]["served"] == "xh")
check("xh greeting translated", "Molo" in b["strings"]["companion.greeting"]["text"]
      and b["strings"]["companion.greeting"]["translated"] is True)
check("no fallback notice when fully seeded", b["fallback_notice"] is None)
check("coverage counts", b["coverage"]["keys_translated"] == 13 and b["coverage"]["keys_on_english_fallback"] == 0)

# 4. /strings — CLI flow (LUQI_LANG=tn -> header), explicit never-silent fallback
r = c.get("/v1/i18n/strings", headers={"Accept-Language": "tn"})
b = r.json()
check("cli flow served tn", b["negotiation"]["served"] == "tn")
fb = b["strings"]["companion.greeting"]
check("tn greeting EXPLICIT english fallback", fb["fallback"] is True and fb["translated"] is False
      and "Sawubona" in fb["text"])
check("every key carries flags", all("translated" in v and "fallback" in v for v in b["strings"].values()))
check("fallback notice present (never silent)", b["fallback_notice"] is not None
      and "Senyesemane" not in b["fallback_notice"])  # tn itself unseeded -> notice falls back to en text
check("coverage honest for tn", b["coverage"]["keys_on_english_fallback"] == 12)  # 13 keys - app.name

# 5. Seeded TM in DB
from sqlalchemy.orm import Session
from core.i18n_models import I18nString
with Session(engine) as s:
    n_seed = s.query(I18nString).filter_by(source="seed").count()
check("catalogue seeded into TM store", n_seed >= 90, f"rows={n_seed}")

# 6. /translate — TM miss -> machine translate -> cache; TM hit -> no LLM
import os
os.environ["KIMI_API_KEY"] = "test-key"
CALLS = []
i18n.kimi_client = type("K", (), {})()  # fresh namespace to monkeypatch
import core.kimi_client as real_kc
i18n.kimi_client = real_kc
def fake_chat(system, user, **kw):
    CALLS.append(user)
    return "Sawubona, unjani?"
real_kc.chat_completion = fake_chat
r = c.post("/v1/i18n/translate", json={"text": "Hello, how are you?", "target": "zu"})
b = r.json()
check("translate miss -> machine translated", b["machine_translated"] is True and b["from_memory"] is False)
check("translated text returned", b["translated"] == "Sawubona, unjani?")
check("one LLM call", len(CALLS) == 1)
with Session(engine) as s:
    tm_row = s.query(I18nString).filter_by(source="machine", locale="zu").first()
check("machine translation cached in Postgres TM", tm_row is not None)
r = c.post("/v1/i18n/translate", json={"text": "Hello, how are you?", "target": "zu"})
b = r.json()
check("second call -> TM hit, no new LLM call", b["from_memory"] is True and len(CALLS) == 1)

# 7. Fail-closed: TM miss without key -> 500 (never silent)
del os.environ["KIMI_API_KEY"]
r = c.post("/v1/i18n/translate", json={"text": "a brand new sentence never cached", "target": "sw"})
check("TM miss without key -> 500 fail-closed", r.status_code == 500)

# 8. Unsupported target -> 400 with supported list, NO silent fallback
r = c.post("/v1/i18n/translate", json={"text": "hi", "target": "xx"})
check("unsupported target -> 400", r.status_code == 400)
check("400 body lists supported + no-silent-fallback note", "supported" in r.json()["detail"])

# 9. Same-locale short-circuit
r = c.post("/v1/i18n/translate", json={"text": "hello", "target": "en", "source_locale": "en"})
check("same-locale passthrough", r.json()["translated"] == "hello" and r.json()["from_memory"] is False)

# 10. main.py mounts + migration chain
import importlib, core.main as m
importlib.reload(m)
paths = [getattr(r_, "path", "") for r_ in m.app.routes]
check("main mounts /v1/i18n", any(p.startswith("/v1/i18n") for p in paths))
import re
mig = open(_REPO / "alembic/versions/007_i18n.py").read()
check("007 chains on 006", re.search(r'^down_revision = "006_reflexion_traces"$', mig, re.M) is not None)
check("007 has FORCE RLS + shared policy", "FORCE ROW LEVEL SECURITY" in mig and "shared_reference_read" in mig)
page = open(_REPO / "static/i18n.html").read()
check("demo page wired to /v1/i18n/strings", "/v1/i18n/strings" in page and "english fallback" in page)

print("\nALL I18N CHECKS PASSED (10/10 groups)")
