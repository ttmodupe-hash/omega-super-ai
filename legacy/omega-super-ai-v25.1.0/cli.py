#!/usr/bin/env python3
"""
Luqi AI v13 — Terminal Chat Client

A beautiful CLI for chatting with Luqi AI from the terminal.
Supports streaming responses, command modes, file upload, and history.

Usage:
    py -3.11 cli.py                    # Interactive chat
    py -3.11 cli.py "Hello"            # Single query
    py -3.11 cli.py --mode research    # Research mode
    py -3.11 cli.py --stream           # Streaming mode
    py -3.11 cli.py --key YOUR_KEY     # Set API key
"""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# ── Configuration ──────────────────────────────────────────────────────

API_BASE = os.environ.get("LUQI_API_URL", "http://localhost:8000")
API_KEY_FILE = Path.home() / ".luqi_ai_key"

# ── Colors ─────────────────────────────────────────────────────────────

class Colors:
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def color(text: str, color_code: str) -> str:
    return f"{color_code}{text}{Colors.RESET}"


# ── HTTP Helpers ───────────────────────────────────────────────────────

def http_post(endpoint: str, data: dict) -> dict:
    """Make a POST request to the API."""
    import urllib.request
    url = f"{API_BASE}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            err = json.loads(error_body)
            raise SystemExit(color(f"Error: {err.get('detail', error_body)}", Colors.RED))
        except json.JSONDecodeError:
            raise SystemExit(color(f"HTTP Error {e.code}: {error_body}", Colors.RED))
    except urllib.error.URLError as e:
        raise SystemExit(color(
            f"Cannot connect to {API_BASE}\n"
            f"Make sure the server is running: py -3.11 start_server.py\n"
            f"Or set LUQI_API_URL env var.",
            Colors.RED
        ))


def http_get(endpoint: str) -> dict:
    """Make a GET request to the API."""
    import urllib.request
    url = f"{API_BASE}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise SystemExit(color(f"Error: {e}", Colors.RED))


# ── Streaming ──────────────────────────────────────────────────────────

def stream_chat(message: str, mode: str = "default") -> None:
    """Stream a chat response from the API."""
    import urllib.request
    url = f"{API_BASE}/api/chat/stream"
    data = json.dumps({"message": message, "mode": mode}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )

    print(color("Luqi AI: ", Colors.CYAN) + color("", Colors.BOLD), end="", flush=True)
    
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1)
                if not chunk:
                    break
                buffer += chunk
                if b"\n\n" in buffer:
                    lines = buffer.split(b"\n\n")
                    for line in lines[:-1]:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            try:
                                event = json.loads(line_str[6:])
                                if event.get("type") == "delta":
                                    print(event.get("token", ""), end="", flush=True)
                                elif event.get("type") == "done":
                                    print()  # New line after completion
                                    return
                            except json.JSONDecodeError:
                                pass
                    buffer = lines[-1]
    except Exception as e:
        print(color(f"\n[Stream error: {e}]", Colors.RED))


# ── Commands ───────────────────────────────────────────────────────────

COMMANDS_HELP = """
Available commands:
  /help          Show this help
  /modes         List available AI modes
  /history       Show conversation history (last 10)
  /clear         Clear screen
  /upload PATH   Upload a file
  /image PROMPT  Generate an image
  /search QUERY  Web search
  /labs          List virtual labs
  /languages     List supported languages
  /health        Server health check
  /quit, /exit   Exit CLI

Mode shortcuts:
  /r, /research  Research mode
  /f, /finance   Finance mode
  /t, /tax       Tax mode
  /th, /think    Deep Think mode
  /m, /mentor    Mentor mode
  /e, /expert    Expert mode
  /l, /learn     Learning mode
  /o, /opps      Opportunities mode
  /sc, /scam     Scam Guard mode
"""


def handle_command(cmd: str, current_mode: list) -> bool:
    """Handle CLI commands. Returns True if should continue, False to exit."""
    cmd = cmd.strip().lower()
    
    if cmd in ("/quit", "/exit", "/q"):
        print(color("Goodbye! 👋", Colors.GREEN))
        return False
    
    if cmd == "/help":
        print(color(COMMANDS_HELP, Colors.DIM))
        return True
    
    if cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()
        return True
    
    if cmd == "/modes":
        modes = [
            ("default", "General chat"),
            ("research", "Deep research with citations"),
            ("finance", "Financial analysis & advice"),
            ("tax", "Global tax guidance"),
            ("opps", "Find opportunities"),
            ("scam", "Scam & fraud detection"),
            ("think", "Critical thinking mode"),
            ("mentor", "Learn any topic"),
            ("expert", "Technical deep-dive"),
            ("learn", "Structured learning"),
        ]
        print(color("Available modes:", Colors.CYAN))
        for m, desc in modes:
            print(f"  {color(m, Colors.YELLOW):12} {desc}")
        return True
    
    if cmd in ("/r", "/research"):
        current_mode[0] = "research"
        print(color("Switched to Research mode 🔬", Colors.CYAN))
        return True
    if cmd in ("/f", "/finance"):
        current_mode[0] = "finance"
        print(color("Switched to Finance mode 💰", Colors.CYAN))
        return True
    if cmd in ("/t", "/tax"):
        current_mode[0] = "tax"
        print(color("Switched to Tax mode 📋", Colors.CYAN))
        return True
    if cmd in ("/th", "/think"):
        current_mode[0] = "think"
        print(color("Switched to Deep Think mode 🧠", Colors.CYAN))
        return True
    if cmd in ("/m", "/mentor"):
        current_mode[0] = "mentor"
        print(color("Switched to Mentor mode 👨‍🏫", Colors.CYAN))
        return True
    if cmd in ("/e", "/expert"):
        current_mode[0] = "expert"
        print(color("Switched to Expert mode ⚡", Colors.CYAN))
        return True
    if cmd in ("/l", "/learn"):
        current_mode[0] = "learn"
        print(color("Switched to Learn mode 📚", Colors.CYAN))
        return True
    if cmd in ("/o", "/opps"):
        current_mode[0] = "opps"
        print(color("Switched to Opportunities mode 🚀", Colors.CYAN))
        return True
    if cmd in ("/sc", "/scam"):
        current_mode[0] = "scam"
        print(color("Switched to Scam Guard mode 🛡️", Colors.CYAN))
        return True
    
    if cmd == "/health":
        try:
            health = http_get("/api/health")
            print(color("Server Status:", Colors.CYAN))
            for k, v in health.items():
                print(f"  {k}: {color(str(v), Colors.GREEN)}")
        except Exception as e:
            print(color(f"Health check failed: {e}", Colors.RED))
        return True
    
    if cmd == "/labs":
        try:
            labs = http_get("/api/labs")
            print(color(f"Virtual Labs ({labs.get('count', 0)} available):", Colors.CYAN))
            for lab in labs.get("labs", [])[:10]:
                emoji = {"physics": "⚛️", "chemistry": "🧪", "biology": "🧬", "math": "📐", "earth": "🌍", "cs": "💻"}.get(lab["subject"], "🔬")
                diff_color = {"beginner": Colors.GREEN, "intermediate": Colors.YELLOW, "advanced": Colors.RED}.get(lab["difficulty"], Colors.DIM)
                print(f"  {emoji} {color(lab['name'], Colors.BOLD):20} {color(lab['subject'], Colors.DIM):10} {color(lab['difficulty'], diff_color)}")
        except Exception as e:
            print(color(f"Error: {e}", Colors.RED))
        return True
    
    if cmd == "/languages":
        try:
            langs = http_get("/api/languages")
            african = langs.get("african", {})
            global_langs = langs.get("global", {})
            print(color(f"Languages: {langs.get('total', 0)} total", Colors.CYAN))
            print(f"  African: {color(str(african.get('count', 0)), Colors.GREEN)}")
            print(f"  Global:  {color(str(global_langs.get('count', 0)), Colors.GREEN)}")
        except Exception as e:
            print(color(f"Error: {e}", Colors.RED))
        return True
    
    if cmd.startswith("/search "):
        query = cmd[8:].strip()
        if query:
            print(color(f"Searching: {query}...", Colors.DIM))
            try:
                result = http_post("/api/search", {"query": query})
                print(color(f"Found {result.get('count', 0)} results:", Colors.CYAN))
                print(result.get("markdown", "No results"))
            except Exception as e:
                print(color(f"Error: {e}", Colors.RED))
        return True
    
    print(color(f"Unknown command: {cmd}. Type /help for commands.", Colors.YELLOW))
    return True


# ── UI ─────────────────────────────────────────────────────────────────

def print_banner():
    banner = r"""
  _             _      
 | |   _  _    (_)  ___
 | |  | +| |   | | (_-<
 |_|   \_,_|  _|_| /__/
             |___/     
"""
    print(color(banner, Colors.CYAN))
    print(color("  Luqi AI v13 — Terminal Chat Client\n", Colors.BOLD))
    print(color("  Type /help for commands, /quit to exit\n", Colors.DIM))


def print_mode_indicator(mode: str):
    mode_emojis = {
        "default": "💎", "research": "🔬", "finance": "💰", "tax": "📋",
        "opps": "🚀", "scam": "🛡️", "think": "🧠", "mentor": "👨‍🏫",
        "expert": "⚡", "learn": "📚",
    }
    emoji = mode_emojis.get(mode, "💎")
    if mode != "default":
        print(color(f"  {emoji} {mode.upper()} MODE", Colors.MAGENTA))


# ── Main ───────────────────────────────────────────────────────────────

def interactive_chat():
    """Run interactive chat session."""
    print_banner()
    
    # Check server health
    try:
        health = http_get("/api/health")
        print(color(f"  Connected — v{health.get('version', '?')}", Colors.GREEN))
        print()
    except SystemExit:
        print(color("  Server not running. Start it with: py -3.11 start_server.py", Colors.RED))
        print()
        return
    
    current_mode = ["default"]
    
    while True:
        try:
            prompt = color("You", Colors.GREEN) + color("> ", Colors.DIM)
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                if not handle_command(user_input, current_mode):
                    break
                continue
            
            # Print mode indicator
            print_mode_indicator(current_mode[0])
            
            # Send message
            stream_chat(user_input, current_mode[0])
            
        except KeyboardInterrupt:
            print(color("\nUse /quit to exit", Colors.DIM))
            continue
        except EOFError:
            break


def single_query(query: str, mode: str = "default", stream: bool = True):
    """Send a single query and print response."""
    if stream:
        stream_chat(query, mode)
    else:
        result = http_post("/api/chat", {"message": query, "mode": mode})
        print(color("Luqi AI: ", Colors.CYAN) + result.get("response", ""))


def main():
    global API_BASE
    
    parser = argparse.ArgumentParser(description="Luqi AI Terminal Chat Client")
    parser.add_argument("query", nargs="?", help="Single query (optional)")
    parser.add_argument("--mode", "-m", default="default", help="AI mode (default, research, think, etc.)")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    parser.add_argument("--api-url", default=None, help="API base URL")
    parser.add_argument("--version", "-v", action="store_true", help="Show version")
    
    args = parser.parse_args()
    
    if args.api_url:
        API_BASE = args.api_url
    
    if args.version:
        print(color("Luqi AI CLI v13.0.0", Colors.CYAN))
        return
    
    if args.query:
        single_query(args.query, args.mode, not args.no_stream)
    else:
        interactive_chat()


if __name__ == "__main__":
    main()
