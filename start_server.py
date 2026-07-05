#!/usr/bin/env python3
"""Luqi AI Server Launcher v13

Starts the FastAPI backend with automatic setup:
1. Checks .env for OPENAI_API_KEY (warns if missing, but continues)
2. Installs dependencies if needed
3. Creates required directories
4. Initializes ChromaDB
5. Starts uvicorn server

Usage:
    py -3.11 start_server.py
    python start_server.py
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    # Change to project root
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Add project to path
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    # Check .env
    env_file = project_dir / ".env"
    env_example = project_dir / ".env.example"

    if not env_file.exists() and env_example.exists():
        print("[setup] Creating .env from .env.example...")
        with open(env_example) as f:
            content = f.read()
        with open(env_file, "w") as f:
            f.write(content)
        print("[setup] Please edit .env and add your OPENAI_API_KEY")

    # Read .env for key check
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    if line.strip().startswith("OPENAI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass

    # Also check PowerShell env
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")

    # Banner
    print(r""")
    ____        __       _
   |  _ \ ___ / _| __ _| |_
   | |_) / _ \ |_ / _` |_  |
   |  _ <  __/  _| (_| |/ /
   |_| \_\___|_|  \__,_/___|
        Luqi AI v13 — World-class AI for Africa & Beyond
""")

    if not api_key or api_key == "your_openai_api_key_here":
        print("[WARN] OPENAI_API_KEY not configured in .env")
        print("[WARN] Get your key at: https://platform.openai.com/api-keys")
        print("[WARN] AI chat features will be unavailable until key is set")
        print("[WARN] You can still browse API docs at http://localhost:8000/docs")
        print()
        # Continue anyway — let the server start so user can browse docs
    else:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"[OK] API Key configured: {masked}")

    # Create directories
    print("[setup] Creating directories...")
    for d in ["uploads", "generated_images", "chroma_db"]:
        (project_dir / d).mkdir(exist_ok=True)
        print(f"  + {d}/")

    # Install dependencies
    req_file = project_dir / "requirements.txt"
    if req_file.exists():
        print("[setup] Checking dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)
        ], check=False)

    # Start server
    print()
    print("=" * 56)
    print("  Luqi AI v13 — Starting Server")
    print("  " + "-" * 52)
    print("  API Docs:  http://localhost:8000/docs")
    print("  Web UI:    http://localhost:8000")
    print("  Health:    http://localhost:8000/api/health")
    print("=" * 56)
    print()

    try:
        import uvicorn
        uvicorn.run(
            "backend.router:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[str(project_dir / "backend")],
        )
    except ImportError:
        print("[setup] Installing uvicorn...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "uvicorn"], check=True)
        import uvicorn
        uvicorn.run("backend.router:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
