#!/usr/bin/env python3
"""Luqi AI CLI Client — Terminal chat with streaming, colors, and commands.

Usage:
    py -3.11 cli.py                    # Interactive mode
    py -3.11 cli.py "Hello"            # Single query
    py -3.11 cli.py --server http://localhost:8000
    py -3.11 cli.py /research "AI in Africa"
    py -3.11 cli.py key YOUR_API_KEY

Commands:
    /r, /research <query>   Deep research mode
    /f, /finance <symbol>   Stock/crypto quote
    /t, /tax <country>      Tax information
    /o, /opps               Opportunities
    /s, /scam <text>        Scam detection
    /think <question>       Multi-step reasoning
    /m, /mentor <topic>     Learning mentor
    /x, /expert <question>  Expert consultant
    /l, /learn <topic>      Educational mode
    key <api_key>           Set API key
    clear                   Clear screen
    exit, quit              Exit

Environment:
    LUQI_API_KEY            API key (or set via 'key' command)
    LUQI_SERVER             Server URL (default: http://localhost:8000)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────

API_BASE = os.environ.get("LUQI_SERVER", "http://localhost:8000")
API_KEY = os.environ.get("LUQI_API_KEY", "")

# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"

# ── HTTP Helpers ───────────────────────────────────────────────────────

def http_post(path: str, payload: dict) -> dict:
    """POST JSON to the API and return parsed JSON."""
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err = json.loads(body)
            return {"error": err.get("detail", err.get("error", str(e)))}
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def http_get(path: str) -> dict:
    """GET from the API and return parsed JSON."""
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-API-Key": API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err = json.loads(body)
            return {"error": err.get("detail", err.get("error", str(e)))}
        except json.JSONDecodeError:
            return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


# ── Streaming Chat ─────────────────────────────────────────────────────

def stream_chat(message: str, mode: str = "default") -> str:
    """Stream a chat response and print tokens as they arrive."""
    payload = {
        "message": message,
        "stream": True,
        "mode": mode,
    }
    url = f"{API_BASE}/api/chat/stream"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-API-Key": API_KEY,
        },
        method="POST",
    )

    full_text = ""
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "delta":
                    token = event.get("token", "")
                    full_text += token
                    sys.stdout.write(token)
                    sys.stdout.flush()
                elif event.get("type") == "done":
                    break
    except Exception as e:
        print(f"{Colors.RED}Stream error: {e}{Colors.END}")
    print()  # newline after stream
    return full_text


# ── Command Handlers ───────────────────────────────────────────────────

def handle_research(query: str) -> str:
    """Run deep research on a query."""
    print(f"{Colors.YELLOW}Researching: {query}...{Colors.END}")
    result = http_post("/api/search", {"query": query, "max_results": 10})
    if "error" in result:
        return f"Research error: {result['error']}"

    sources = result.get("results", [])
    print(f"\n{Colors.CYAN}Found {len(sources)} sources:{Colors.END}")
    for i, src in enumerate(sources[:5], 1):
        print(f"  {i}. {src.get('title', 'N/A')}")
        print(f"     {Colors.DIM}{src.get('url', '')}{Colors.END}")

    # Now get AI analysis
    analysis = stream_chat(
        f"Analyze these sources and provide a comprehensive research summary about: {query}\n\n"
        f"Sources: {json.dumps(sources[:5])}",
        mode="research",
    )
    return analysis


def handle_finance(symbol: str) -> str:
    """Get financial quote for a stock or crypto symbol."""
    # Try stock first
    result = http_get(f"/api/finance/stock/{symbol.upper()}")
    if "error" in result:
        # Try crypto
        result = http_get(f"/api/finance/crypto/{symbol.upper()}")
    if "error" in result:
        return f"Finance error: {result['error']}"

    print(f"\n{Colors.GREEN}═══ {result.get('symbol', symbol).upper()} ═══{Colors.END}")
    for key, value in result.items():
        if key != "symbol":
            print(f"  {Colors.CYAN}{key}:{Colors.END} {value}")
    return ""


def handle_tax(country: str) -> str:
    """Get tax information for a country."""
    result = http_get(f"/api/taxes/{country.upper()}")
    if "error" in result:
        return f"Tax error: {result['error']}"
    print(f"\n{Colors.GREEN}═══ Tax Info: {country.upper()} ═══{Colors.END}")
    print(json.dumps(result, indent=2))
    return ""


def handle_opportunities() -> str:
    """Get opportunities list."""
    result = http_get("/api/opportunities")
    if "error" in result:
        return f"Error: {result['error']}"
    print(f"\n{Colors.GREEN}═══ Opportunities ═══{Colors.END}")
    items = result.get("opportunities", result.get("results", []))
    for i, item in enumerate(items[:10], 1):
        title = item.get("title", item.get("name", "N/A"))
        desc = item.get("description", item.get("desc", ""))
        print(f"\n  {Colors.YELLOW}{i}. {title}{Colors.END}")
        if desc:
            print(f"     {Colors.DIM}{desc[:120]}{Colors.END}")
    return ""


def handle_scam(text: str) -> str:
    """Analyze text for scam indicators."""
    return stream_chat(
        f"Analyze this message for scam/fraud indicators. List red flags and provide a safety assessment:\n\n{text}",
        mode="scam",
    )


def handle_think(question: str) -> str:
    """Multi-step reasoning mode."""
    return stream_chat(question, mode="think")


def handle_mentor(topic: str) -> str:
    """Learning mentor mode."""
    return stream_chat(
        f"Teach me about: {topic}. Start with fundamentals, use examples, and check my understanding.",
        mode="mentor",
    )


def handle_expert(question: str) -> str:
    """Expert consultant mode."""
    return stream_chat(question, mode="expert")


def handle_learn(topic: str) -> str:
    """Educational mode with structured lesson."""
    return stream_chat(
        f"Create a structured lesson plan about: {topic}. Include objectives, key concepts, examples, and practice questions.",
        mode="learn",
    )


# ── Interactive Mode ───────────────────────────────────────────────────

def print_banner():
    """Print the Luqi AI CLI banner."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
  _                _     _ 
 | |    _   _ _ __| | __| |
 | |   | | | | '__| |/ _` |
 | |___| |_| | |  | | (_| |
 |_____|\__,_|_|  |_|\__,_|
{Colors.END}
  {Colors.GREEN}Luqi AI v13 — Africa's AI{Colors.END}
  {Colors.DIM}Type 'help' for commands, 'exit' to quit{Colors.END}
""")


def print_help():
    """Print available commands."""
    print(f"""
{Colors.BOLD}Commands:{Colors.END}
  /r, /research <query>    Deep research with sources
  /f, /finance <symbol>    Stock/crypto quote
  /t, /tax <country>       Tax information
  /o, /opps                Business opportunities
  /s, /scam <text>         Scam detection analysis
  /think <question>        Multi-step reasoning
  /m, /mentor <topic>      Learning mentor
  /x, /expert <question>   Expert consultant
  /l, /learn <topic>       Educational mode
  key <api_key>            Set your API key
  clear                    Clear screen
  exit, quit               Exit

{Colors.BOLD}Modes:{Colors.END} default, research, think, mentor, expert, finance, scam, learn, opps
""")


def interactive_mode():
    """Run the interactive chat loop."""
    print_banner()

    # Check server health
    health = http_get("/api/health")
    if "error" in health:
        print(f"{Colors.YELLOW}Warning: Server not responding at {API_BASE}{Colors.END}")
        print(f"{Colors.DIM}Start server: py -3.11 start_server.py{Colors.END}\n")
    else:
        ver = health.get("version", "unknown")
        langs = health.get("languages_supported", "?")
        print(f"{Colors.GREEN}Server: v{ver} | {langs} languages | Status: OK{Colors.END}\n")

    while True:
        try:
            prompt_text = f"{Colors.CYAN}You{Colors.END}{Colors.DIM}>{Colors.END} "
            user_input = input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.YELLOW}Goodbye!{Colors.END}")
            break

        if not user_input:
            continue

        # Exit commands
        if user_input.lower() in ("exit", "quit", "q"):
            print(f"{Colors.YELLOW}Goodbye!{Colors.END}")
            break

        # Clear screen
        if user_input.lower() == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            print_banner()
            continue

        # Help
        if user_input.lower() in ("help", "h", "?"):
            print_help()
            continue

        # API Key
        if user_input.lower().startswith("key "):
            global API_KEY
            API_KEY = user_input[4:].strip()
            print(f"{Colors.GREEN}API key set.{Colors.END}")
            continue

        # Server URL
        if user_input.lower().startswith("server "):
            global API_BASE
            API_BASE = user_input[7:].strip().rstrip("/")
            print(f"{Colors.GREEN}Server set to: {API_BASE}{Colors.END}")
            continue

        # Route commands
        cmd = user_input.split()[0].lower()
        rest = user_input[len(cmd):].strip()

        if cmd in ("/r", "/research"):
            handle_research(rest or input(f"{Colors.YELLOW}Research topic: {Colors.END}"))
        elif cmd in ("/f", "/finance"):
            handle_finance(rest or input(f"{Colors.YELLOW}Symbol (e.g., AAPL, BTC): {Colors.END}"))
        elif cmd in ("/t", "/tax"):
            handle_tax(rest or input(f"{Colors.YELLOW}Country code (e.g., NG, ZA, KE): {Colors.END}"))
        elif cmd in ("/o", "/opps"):
            handle_opportunities()
        elif cmd in ("/s", "/scam"):
            handle_scam(rest or input(f"{Colors.YELLOW}Paste suspicious text: {Colors.END}"))
        elif cmd == "/think":
            handle_think(rest or input(f"{Colors.YELLOW}Question to reason through: {Colors.END}"))
        elif cmd in ("/m", "/mentor"):
            handle_mentor(rest or input(f"{Colors.YELLOW}Topic to learn: {Colors.END}"))
        elif cmd in ("/x", "/expert"):
            handle_expert(rest or input(f"{Colors.YELLOW}Expert question: {Colors.END}"))
        elif cmd in ("/l", "/learn"):
            handle_learn(rest or input(f"{Colors.YELLOW}Educational topic: {Colors.END}"))
        else:
            # Regular chat
            print(f"{Colors.GREEN}Luqi{Colors.END}{Colors.DIM}>{Colors.END} ", end="", flush=True)
            stream_chat(user_input)


# ── Main Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Luqi AI CLI — Terminal chat client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py -3.11 cli.py                          # Interactive mode
  py -3.11 cli.py "Hello, how are you?"    # Single query
  py -3.11 cli.py /research "AI in Africa" # Research mode
  py -3.11 cli.py /finance AAPL            # Stock quote
  py -3.11 cli.py --server http://luqi-ai.com
        """,
    )
    parser.add_argument("query", nargs="?", help="Single query to send")
    parser.add_argument("--server", default=None, help="API server URL")
    parser.add_argument("--mode", default="default", help="Chat mode")
    parser.add_argument("--key", default=None, help="API key")
    args = parser.parse_args()

    # Override config from args
    if args.server:
        global API_BASE
        API_BASE = args.server.rstrip("/")
    if args.key:
        global API_KEY
        API_KEY = args.key

    # Single query mode
    if args.query:
        print(f"{Colors.GREEN}Luqi{Colors.END}{Colors.DIM}>{Colors.END} ", end="", flush=True)
        stream_chat(args.query, mode=args.mode)
        return

    # Interactive mode
    interactive_mode()


if __name__ == "__main__":
    main()
