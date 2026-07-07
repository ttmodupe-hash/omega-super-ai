#!/usr/bin/env python3
"""
Luqi AI v20 -- Server Launcher
Starts the FastAPI backend server with auto-setup.

Usage:
    py -3.11 start_server.py
    py -3.11 start_server.py --port 8080
    py -3.11 start_server.py --host 0.0.0.0 --port 8000
"""

import argparse
import importlib
import os
import socket
import subprocess
import sys
from pathlib import Path


def print_banner():
    """Display the Luqi AI startup banner."""
    banner = r"""
    ██░     ██░   ██░ ██████░ ██░     ███████░
    ██░     ██░   ██░██╔═══██░██░     ██╔════╝
    ██░     ██░   ██░██░   ██░██░     ███████░
    ██░     ██░   ██░██░▄▄ ██░██░     ╚════██░
    ███████░╚██████░▄▄██████▄▄███████░███████░
    ╚══════╝ ╚═════╝  ╚══▄▄╔▄═╝ ╚═════╝╚══════╝
         Luqi AI v20 -- World-class AI for Africa & Beyond
    """
    print(banner)


def check_env_file():
    """Ensure .env file exists; prompt to create from template if missing."""
    env_path = Path(".env")
    example_path = Path(".env.example")

    if env_path.exists():
        return True

    print("[setup] .env file not found.")
    if example_path.exists():
        print(f"[setup] Creating .env from {example_path} ...")
        env_path.write_text(example_path.read_text(), encoding="utf-8")
        print("[setup] .env created. Please edit it and add your API keys.")
    else:
        print("[setup] .env.example also missing. Creating a minimal .env ...")
        env_path.write_text(
            'OPENAI_API_KEY=sk-your-openai-key-here\n'
            'STRIPE_SECRET_KEY=sk-test-your-key-here\n'
            'STRIPE_PUBLISHABLE_KEY=pk-test-your-key-here\n',
            encoding="utf-8"
        )
        print("[setup] Minimal .env created. Please edit it and add your API keys.")

    print("\n>>> IMPORTANT: Edit .env and set your OPENAI_API_KEY before restarting. <<<")
    return False


def check_api_key():
    """Verify that the OpenAI API key is configured."""
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key or api_key.strip() in (
        "sk-your-openai-key-here",
        "your_openai_api_key_here",
        "",
    ):
        print("[setup] OPENAI_API_KEY is not configured in .env")
        print("[setup] Get your key at: https://platform.openai.com/api-keys")
        return False

    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"[setup] API key configured: {masked}")
    return True


def ensure_directory(path):
    """Create a directory if it does not already exist."""
    dir_path = Path(path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"[setup] Created directory: {dir_path}")
    else:
        print(f"[setup] Directory exists: {dir_path}")


def init_chromadb(chroma_path):
    """Initialize the ChromaDB vector store."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=chroma_path)
        client.get_or_create_collection("luqi_memory")
        print(f"[setup] ChromaDB initialized at: {chroma_path}")
        return True
    except ImportError:
        print("[setup] chromadb not installed. Will be installed with dependencies.")
        return False
    except Exception as e:
        print(f"[setup] ChromaDB init warning: {e}")
        return False


def check_dependencies():
    """Check that required packages are importable; install any that are missing."""
    required = {
        "openai": "openai>=1.35.0",
        "fastapi": "fastapi>=0.111.0",
        "uvicorn": "uvicorn[standard]>=0.30.0",
        "dotenv": "python-dotenv>=1.0.0",
        "chromadb": "chromadb>=0.5.0",
        "numpy": "numpy>=1.26.0",
        "pydantic": "pydantic>=2.7.0",
        "PIL": "Pillow>=10.0.0",
        "requests": "requests>=2.31.0",
        "python_multipart": "python-multipart>=0.0.9",
        "stripe": "stripe>=9.0.0",
    }

    missing = []
    for module, package in required.items():
        try:
            importlib.import_module(module)
            print(f"[deps]  OK  {package}")
        except ImportError:
            print(f"[deps]  MISSING  {package}")
            missing.append(package)

    if missing:
        print(f"\n[setup] Installing {len(missing)} missing package(s) ...")
        cmd = [sys.executable, "-m", "pip", "install", *missing]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print("[setup] pip install failed. Please install manually:")
            print(f"        {' '.join(missing)}")
            return False
        print("[setup] Dependencies installed successfully.")
    else:
        print("[deps] All dependencies satisfied.")

    return True


def get_local_ip():
    """Retrieve the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("8.8.8.8", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_urls(host, port):
    """Print clickable local and network URLs."""
    local_url = f"http://localhost:{port}"
    network_ip = get_local_ip()
    network_url = f"http://{network_ip}:{port}"
    docs_url = f"http://localhost:{port}/docs"

    print("\n" + "=" * 60)
    print("  Luqi AI v20 Server is running!")
    print("=" * 60)
    print(f"  Local:    {local_url}")
    print(f"  Network:  {network_url}")
    print(f"  API Docs: {docs_url}")
    print("=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")


def graceful_shutdown(server):
    """Handle graceful shutdown on interrupt signals."""
    print("\n[server] Shutting down gracefully ...")
    server.should_exit = True


def main():
    parser = argparse.ArgumentParser(
        description="Luqi AI v20 Server Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start on default port 8000
  %(prog)s --port 8080              # Start on port 8080
  %(prog)s --host 0.0.0.0 --port 8000   # Bind to all interfaces
        """,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency check/install",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    args = parser.parse_args()

    print_banner()

    # Step 1: Check .env
    if not check_env_file():
        print("\n[setup] Please configure .env and restart.")
        sys.exit(1)

    # Step 2: Check API key
    if not check_api_key():
        print("\n[setup] Please set your OPENAI_API_KEY in .env and restart.")
        sys.exit(1)

    # Step 3: Check dependencies
    if not args.skip_deps:
        if not check_dependencies():
            print("\n[setup] Dependency installation failed.")
            sys.exit(1)
    else:
        print("[setup] Skipping dependency check.")

    # Step 4: Ensure directories
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    chroma_path = os.getenv("CHROMA_PATH", "./chroma_db")
    ensure_directory(upload_dir)
    ensure_directory(chroma_path)

    # Step 5: Init ChromaDB
    init_chromadb(chroma_path)

    # Step 6: Print startup info
    print(f"\n[start] Starting Luqi AI v20 Server ...")
    print(f"[start] Host: {args.host}")
    print(f"[start] Port: {args.port}")
    print(f"[start] Reload: {'on' if args.reload else 'off'}")

    # Step 7: Start uvicorn
    import uvicorn

    print_urls(args.host, args.port)

    config = uvicorn.Config(
        "backend.router:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)

    try:
        server.run()
    except KeyboardInterrupt:
        graceful_shutdown(server)
        print("[server] Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
