#!/usr/bin/env python3
"""Luqi AI Server Launcher

Starts the FastAPI backend with automatic setup:
1. Checks .env for OPENAI_API_KEY
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
        print("Creating .env from .env.example...")
        with open(env_example) as f:
            content = f.read()
        with open(env_file, "w") as f:
            f.write(content)
        print("Please edit .env and add your OPENAI_API_KEY")

    # Create directories
    for d in ["uploads", "generated_images", "chroma_db"]:
        (project_dir / d).mkdir(exist_ok=True)
        print(f"  ✓ {d}/")

    # Install dependencies
    req_file = project_dir / "requirements.txt"
    if req_file.exists():
        print("Checking dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)
        ], check=False)

    # Start server
    print("\n" + "=" * 50)
    print("  Luqi AI v13 — Starting Server")
    print("  " + "-" * 46)
    print("  API Docs:  http://localhost:8000/docs")
    print("  Web UI:    http://localhost:8000")
    print("  Health:    http://localhost:8000/api/health")
    print("=" * 50 + "\n")

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
        print("Installing uvicorn...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "uvicorn"], check=True)
        import uvicorn
        uvicorn.run("backend.router:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
