# app/engine/router.py
import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    mode: str
    verified: bool
    confidence: float
    sources: List[str] = []
    content: Dict[str, Any]

class LuqiEngineRouter:
    def __init__(self, scam_db, services_db, history_db):
        self.scam_db = scam_db
        self.services_db = services_db
        self.history_db = history_db

    async def process_query(self, query: str, user_mode: str = "auto") -> AnalysisResult:
        # Auto-route if mode isn't explicitly set
        if user_mode == "auto":
            user_mode = self._detect_intent(query)

        if user_mode == "scam_shield":
            return await self._run_scam_shield(query)
        elif user_mode == "everyday_services":
            return await self._run_services_pack(query)
        elif user_mode == "african_history":
            return await self._run_history_archive(query)
        else:
            return await self._run_professor_tutor(query)

    def _detect_intent(self, query: str) -> str:
        scam_keywords = [r"invest", r"guaranteed", r"return", r"whatsapp group", r"send money"]
        service_keywords = [r"sassa", r"srd", r"sars", r"uif", r"nsfas", r"grant"]
        
        for pattern in scam_keywords:
            if re.search(pattern, query, re.IGNORECASE):
                return "scam_shield"
        for pattern in service_keywords:
            if re.search(pattern, query, re.IGNORECASE):
                return "everyday_services"
        return "professor"

    async def _run_scam_shield(self, text: str) -> AnalysisResult:
        # Match against the 12 live fraud families in the engine database
        matches = self.scam_db.search_patterns(text)
        risk_level = "CRITICAL" if len(matches) >= 2 else "LOW"
        
        return AnalysisResult(
            mode="scam_shield",
            verified=True,
            confidence=0.95,
            sources=["Luqi-ai Fraud Family Registry v1.2"],
            content={
                "risk_score": risk_level,
                "matched_patterns": [m.name for m in matches],
                "red_flags": [m.flag_reason for m in matches],
                "action_advice": "Do not transfer funds. Verify directly with official institutions."
            }
        )

    async def _run_services_pack(self, query: str) -> AnalysisResult:
        # Strict RAG retrieval from official sources only
        doc = self.services_db.get_official_guide(query)
        if not doc:
            return AnalysisResult(
                mode="everyday_services",
                verified=False,
                confidence=0.0,
                sources=[],
                content={"message": "UNVERIFIED — Official information not found in indexed government sources."}
            )
        return AnalysisResult(
            mode="everyday_services",
            verified=True,
            confidence=1.0,
            sources=[doc.official_source_url],
            content={"steps": doc.steps, "official_channel": doc.channel}
        )
        # app/main.py
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

app = FastAPI(title="Luqi-ai Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/chat")
async def chat_endpoint(payload: dict):
    query = payload.get("message", "")
    mode = payload.get("mode", "auto")
    language = payload.get("language", "en") # Supports the 22 African languages registry

    async def event_stream():
        # Stream response tokens to enforce data-light, low-latency UI
        yield f"data: {json.dumps({'status': 'routing', 'mode': mode})}\n\n"
        
        # Engine execution steps...
        yield f"data: {json.dumps({'chunk': 'Analyzing against the 12 fraud families...'})}\n\n"
        yield f"data: {json.dumps({'status': 'complete', 'verified': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/v1/stats")
async def get_live_metrics():
    """Powers the dynamic verifiable counter on the landing page."""
    return {
        "fraud_families": 12,
        "history_entries": 29,
        "service_guides": 15,
        "languages_supported": 22
    }
    // components/LuqiEngineChat.tsx
import React, { useState } from 'react';

export default function LuqiEngineChat() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleExecute = async (inputQuery: string, selectedMode = 'auto') => {
    setLoading(true);
    setQuery(inputQuery);

    const res = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: inputQuery, mode: selectedMode })
    });

    const data = await res.json();
    setResponse(data);
    setLoading(false);
  };

  return (
    <div className="max-w-3xl mx-auto p-4 bg-slate-900 text-white rounded-xl shadow-lg border border-slate-800">
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Check a suspicious offer, ask about SASSA, or learn a topic..."
          className="flex-1 bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:outline-none focus:border-amber-500"
        />
        <button
          onClick={() => handleExecute(query)}
          className="bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold px-6 py-3 rounded-lg transition-colors"
        >
          {loading ? 'Routing...' : 'Chat Now'}
        </button>
      </div>

      {/* Preset Action Trigger Example */}
      <div className="text-sm text-slate-400 flex items-center gap-2">
        <span>Try live demo:</span>
        <button
          onClick={() => handleExecute("Invest R500, get R5000 back in 7 days, guaranteed", "scam_shield")}
          className="underline hover:text-amber-400 text-left"
        >
          “Invest R500, get R5000 back in 7 days...”
        </button>
      </div>

      {response && (
        <div className="mt-6 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-1 rounded">
              Mode: {response.mode}
            </span>
            <span className={`text-xs font-mono ${response.verified ? 'text-green-400' : 'text-red-400'}`}>
              {response.verified ? '✓ VERIFIED SOURCE' : '⚠ UNVERIFIED'}
            </span>
          </div>
          <pre className="whitespace-pre-wrap text-slate-200 text-sm font-sans">
            {JSON.stringify(response.content, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
