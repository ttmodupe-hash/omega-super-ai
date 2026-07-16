"""Omega AI v3.2 — HTTP API Server
Standard-library-only REST API. Start with: python omega_ai.py --server [--port 8080]
"""
from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


# ── Request Handler ──
class APIHandler(BaseHTTPRequestHandler):
    _start_time = time.time()

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # Suppress default logging

    def _send_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_error(self, msg: str, status: int = 400) -> None:
        self._send_json({"error": msg}, status)

    def _read_body(self) -> dict:
        cl = int(self.headers.get("Content-Length", 0))
        if cl == 0:
            return {}
        return json.loads(self.rfile.read(cl).decode())

    def do_GET(self) -> None:
        p = urlparse(self.path)
        path = p.path
        qs = parse_qs(p.query)

        if path == "/api/health":
            self._send_json({
                "status": "ok", "version": "3.2.0", "name": "Luqi-AI",
                "uptime_seconds": round(time.time() - self._start_time),
                "capabilities": [
                    "research", "invest", "tax", "lang", "scam", "email",
                    "price", "calc", "opportunities", "learn", "wizard"
                ],
            })
        elif path == "/api/price/btc" or path == "/api/price/bitcoin":
            self._price("btc")
        elif path == "/api/price/eth" or path == "/api/price/ethereum":
            self._price("eth")
        elif path == "/api/price/sol" or path == "/api/price/solana":
            self._price("sol")
        elif path.startswith("/api/opportunities/"):
            country = path.split("/")[-1]
            self._opportunities(country)
        elif path == "/api/opportunities":
            self._opportunities("")
        elif path == "/":
            self._send_json({"message": "Luqi-AI API v3.2", "docs": "/api/health"})
        else:
            self._send_error(f"Not found: {path}", 404)

    def do_POST(self) -> None:
        p = urlparse(self.path)
        path = p.path
        body = self._read_body()

        routes = {
            "/api/chat": self._chat, "/api/research": self._research,
            "/api/invest/analyze": self._invest_analyze, "/api/invest/mining": self._invest_mining,
            "/api/tax/calculate": self._tax_calc, "/api/lang/translate": self._translate,
            "/api/scam/check": self._scam_check, "/api/email/improve": self._email_improve,
            "/api/calc": self._calc, "/api/learn/next": self._learn_next,
        }
        handler = routes.get(path)
        if handler:
            handler(body)
        else:
            self._send_error(f"Not found: {path}", 404)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Endpoint Handlers ──
    def _chat(self, body: dict) -> None:
        q = body.get("query", "")
        if not q:
            self._send_error("Missing 'query' field"); return
        from core_brain import OmegaBrain
        r = OmegaBrain().orchestrate_response(q)
        self._send_json({"query": q, "response": r.get("response"), "module": r.get("module"), "response_time_ms": r.get("response_time_ms")})

    def _research(self, body: dict) -> None:
        q = body.get("query", "")
        d = body.get("depth", "deep")
        if not q:
            self._send_error("Missing 'query'"); return
        from deep_research import DeepResearch
        r = DeepResearch().research(q, depth=d)
        self._send_json({"query": q, "depth": d, "cited_response": r.get("cited_response"), "sources": r.get("sources", [])})

    def _invest_analyze(self, body: dict) -> None:
        a = body.get("asset", "bitcoin")
        from investment_mining import InvestmentMining
        im = InvestmentMining()
        r = im.investment_analysis(a)
        self._send_json({"asset": a, "trend": r.get("trend"), "outlook": r.get("outlook"), "risk_level": r.get("risk_level"), "disclaimer": im.disclaimer()})

    def _invest_mining(self, body: dict) -> None:
        hr = body.get("hashrate_ths", 100)
        pc = body.get("power_cost", 0.08)
        pw = body.get("power_watts", 3000)
        from investment_mining import InvestmentMining
        r = InvestmentMining().mining_profitability(hr, pc, pw)
        self._send_json({"hashrate_ths": hr, "power_cost": pc, **{k: v for k, v in r.items() if k in ("daily", "monthly", "yearly")}})

    def _tax_calc(self, body: dict) -> None:
        c = body.get("country", "south africa")
        i = body.get("income", 0)
        from tax_engine import TaxEngine
        r = TaxEngine().calculate_estimate(c, i)
        self._send_json({"country": c, "income": i, "estimated_tax": r.get("estimated_tax", r.get("tax", 0)), "effective_rate": r.get("effective_rate", 0)})

    def _translate(self, body: dict) -> None:
        t = body.get("text", "")
        l = body.get("language", "zulu")
        from african_languages import AfricanLanguages
        r = AfricanLanguages().translate(t, l)
        self._send_json({"text": t, "language": l, "translation": r})

    def _scam_check(self, body: dict) -> None:
        d = body.get("description", "")
        if not d:
            self._send_error("Missing 'description'"); return
        from financial_literacy import FinancialLiteracy
        r = FinancialLiteracy().scam_check(d)
        self._send_json({"risk_score": r["risk_score"], "risk_level": r["risk_level"], "red_flags": r["red_flags"], "advice": r["advice"]})

    def _email_improve(self, body: dict) -> None:
        d = body.get("draft", "")
        if not d:
            self._send_error("Missing 'draft'"); return
        from email_assistant import EmailAssistant
        ea = EmailAssistant()
        improved = ea.improve_email(d)
        tone = ea.analyze_tone(d)
        self._send_json({"original": d, "improved": improved, "tone_analysis": tone})

    def _price(self, symbol: str) -> None:
        from price_ticker import PriceTicker
        p = PriceTicker().get_price(symbol)
        self._send_json(p)

    def _calc(self, body: dict) -> None:
        args = body.get("args", [])
        if not args:
            self._send_error("Missing 'args' array"); return
        from calc_engine import CalcEngine
        r = CalcEngine().handle_command(args)
        self._send_json({"result": r, "type": body.get("type", "auto")})

    def _opportunities(self, country: str) -> None:
        from opportunity_engine import OpportunityEngine
        ops = OpportunityEngine().african_opportunities(country)
        self._send_json({"country": country or "Africa", "opportunities": ops[:10]})

    def _learn_next(self, body: dict) -> None:
        from learning_tracker import LearningTracker
        lt = LearningTracker()
        nl = lt.get_next_lesson()
        p = lt.get_progress()
        self._send_json({"next_lesson": nl, "progress": p})


# ── Server Entry Point ──
def start_api_server(port: int = 8080) -> None:
    server = HTTPServer(("", port), APIHandler)
    print(f"Luqi-AI API server running on http://localhost:{port}")
    print(f"Health check: curl http://localhost:{port}/api/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_api_server(port)
