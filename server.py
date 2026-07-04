"""Luqi AI v12 — FastAPI Backend Server

Entry point for the Luqi AI backend API server.

Run:
    py -3.11 server.py

Or with uvicorn directly:
    uvicorn backend.router:app --host 0.0.0.0 --port 8000 --reload
"""

import uvicorn
from backend.router import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("backend.router:app", host="0.0.0.0", port=8000, reload=True)
