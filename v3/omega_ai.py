#!/usr/bin/env python3
"""Omega AI v3.2 — Luqi-AI
The main entry point for the Luqi-AI intelligent assistant.
Run with: python omega_ai.py          # Interactive CLI mode
         python omega_ai.py --server  # HTTP API server mode
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure local modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONFIG, validate_config, get_memory_dir
from utils import colorize, Colors, print_header, print_success, print_error, print_info, print_warning, Spinner, sanitize_input
from core_brain import OmegaBrain
from memory_store import MemoryStore
from preferences import UserPreferences


def start_server(port: int = 8080) -> None:
    """Start the HTTP API server."""
    from api_server import start_api_server
    print_success(f"Starting Luqi-AI API server on port {port}...")
    start_api_server(port=port)


def main() -> None:
    """Main CLI loop for Luqi-AI."""
    prefs = UserPreferences()
    brain = OmegaBrain(max_history=prefs.get("max_history", 6))
    memory = MemoryStore()

    # Handle --server flag
    if "--server" in sys.argv:
        port = 8080
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        start_server(port)
        return

    # Track last interaction for /save command
    last_query = ""
    last_response = ""
    last_category = "general"

    # Print startup banner
    print(colorize(OmegaBrain.startup_banner(), Colors.CYAN))

    # Validate config
    missing = validate_config()
    if missing:
        print_warning(f"Missing config (running in mock mode): {', '.join(missing)}")
    else:
        print_success("Configuration loaded")

    print_info(f"Memory directory: {get_memory_dir()}")
    print_info("Type /menu for capabilities, /quit to exit\n")

    # Check for due reminders on startup
    try:
        from reminders import ReminderManager
        rm = ReminderManager()
        due = rm.check_due()
        if due:
            print_warning(f"📌 {len(due)} reminder(s) due!")
            for d in due[:3]:
                print(f"   • {d['text']}")
            print()
    except Exception:
        pass

    # Show menu on first run
    print(OmegaBrain.show_menu())

    # Main interaction loop
    while True:
        try:
            # Prompt
            prompt_text = colorize("\nΩ", Colors.BOLD + Colors.CYAN) + colorize(" >>", Colors.CYAN) + " "
            user_input = input(prompt_text).strip()
            user_input = sanitize_input(user_input)

            if not user_input:
                continue

            # Command handling
            if user_input.lower() in ("/quit", "quit", "exit", "bye"):
                print(colorize("\nThank you for using Luqi-AI. Stay brilliant! ✨\n", Colors.CYAN))
                break

            if user_input.lower() in ("/menu", "/help", "menu", "help"):
                print(OmegaBrain.show_menu())
                continue

            if user_input.lower() in ("/status", "/health"):
                from self_improve import SelfImprovementLab
                lab = SelfImprovementLab()
                print(lab.lab_report())
                continue

            if user_input.lower() == "/train":
                from companion_trainer import CompanionTrainer
                trainer = CompanionTrainer()
                trainer.enter_training_mode()
                continue

            if user_input.lower().startswith("/prefs"):
                prefs = UserPreferences()
                parts = user_input[6:].strip().split(None, 1)
                if not parts:
                    # Show current preferences
                    print(f"\nCurrent Preferences:")
                    for k, v in prefs.all().items():
                        print(f"  {k}: {v}")
                    print("\nUse /prefs set <key> <value> to change")
                elif parts[0] == "set" and len(parts) > 1:
                    kv = parts[1].split(None, 1)
                    if len(kv) == 2:
                        key, val = kv[0], kv[1]
                        # Auto-convert types
                        if val.lower() in ("true", "false"):
                            val = val.lower() == "true"
                        elif val.replace(".", "").isdigit():
                            val = float(val) if "." in val else int(val)
                        prefs.set(key, val)
                        print_success(f"Set {key} = {val}")
                    else:
                        print_error("Usage: /prefs set <key> <value>")
                continue

            if user_input.lower().startswith("/save"):
                filename = user_input[5:].strip() or f"luqi_export_{datetime.now():%Y%m%d_%H%M%S}.md"
                if not filename.endswith(".md"):
                    filename += ".md"
                export_content = f"""# Luqi-AI Export

**Date:** {datetime.now().isoformat()}
**Module:** {last_category}

## Query
{last_query}

## Response
{last_response}

---
*Generated by Luqi-AI v3.2*
"""
                Path(filename).write_text(export_content, encoding="utf-8")
                print_success(f"Saved to {filename}")
                continue

            # ── v3.2 NEW COMMANDS ──

            if user_input.lower().startswith("/price") or user_input.lower().startswith("/crypto"):
                from price_ticker import PriceTicker
                pt = PriceTicker()
                args = user_input.split(None, 1)[1] if " " in user_input else ""
                if not args.strip():
                    args = "btc eth sol"
                result = pt.handle_command(args.split())
                print(f"\n{result}")
                last_query = user_input
                last_response = result
                last_category = "price_ticker"
                continue

            if user_input.lower().startswith("/alert "):
                from price_ticker import PriceTicker
                pt = PriceTicker()
                parts = user_input[7:].strip().split()
                result = pt.handle_command(["alert"] + parts)
                print(f"\n{result}")
                continue

            if user_input.lower().startswith("/calc "):
                from calc_engine import CalcEngine
                ce = CalcEngine()
                args = user_input[6:].strip().split()
                result = ce.handle_command(args)
                print(f"\n{result}")
                last_query = user_input
                last_response = result
                last_category = "calc"
                continue

            if user_input.lower().startswith("/search "):
                from history_search import HistoryManager
                hm = HistoryManager()
                query = user_input[8:].strip()
                results = hm.search(query, limit=10)
                formatted = hm.format_results(results)
                print(f"\n{formatted}")
                continue

            if user_input.lower() == "/history":
                from history_search import HistoryManager
                hm = HistoryManager()
                results = hm.list_recent(limit=20)
                formatted = hm.format_results(results)
                print(f"\n{formatted}")
                continue

            if user_input.lower() == "/clear":
                confirm = input(colorize("Clear all conversation history? Type 'yes' to confirm: ", Colors.YELLOW)).strip()
                if confirm.lower() == "yes":
                    from history_search import HistoryManager
                    hm = HistoryManager()
                    hm.clear_all()
                    print_success("Conversation history cleared.")
                else:
                    print("Cancelled.")
                continue

            if user_input.lower() == "/learn":
                from learning_tracker import LearningTracker
                lt = LearningTracker()
                print(f"\n{lt.format_progress()}")
                next_lesson = lt.get_next_lesson()
                if next_lesson:
                    prompt = colorize(f"\nNext lesson: {next_lesson['topic']} ({next_lesson['level']}) — Start? [Y/n]: ", Colors.CYAN)
                    start_lesson = input(prompt).strip().lower()
                    if start_lesson in ("", "y", "yes"):
                        content = lt.get_lesson_content(next_lesson['topic'], next_lesson['level'])
                        print(f"\n{content}")
                        lt.mark_completed(next_lesson['topic'], next_lesson['level'])
                        print_success(f"Marked {next_lesson['topic']} ({next_lesson['level']}) as completed!")
                continue

            if user_input.lower().startswith("/remind "):
                from reminders import ReminderManager
                rm = ReminderManager()
                text = user_input[8:].strip()
                date_str = ""
                recurring = ""
                if " on " in text.lower():
                    parts = text.lower().split(" on ", 1)
                    text = parts[0].strip()
                    date_str = parts[1].strip()
                if " every " in text.lower():
                    parts = text.lower().split(" every ", 1)
                    text = parts[0].strip()
                    recurring = parts[1].strip()
                reminder = rm.add(text, date_str=date_str, recurring=recurring)
                print_success(f"Reminder set: '{reminder['text']}' (ID: {reminder['id']})")
                continue

            if user_input.lower() == "/reminders":
                from reminders import ReminderManager
                rm = ReminderManager()
                reminders = rm.list(show_all=False)
                if not reminders:
                    print("No upcoming reminders.")
                else:
                    print(f"\n{rm.format_list(reminders)}")
                # Also show any due reminders
                due = rm.check_due()
                if due:
                    print_warning(f"\n⚠ {len(due)} reminder(s) due now!")
                    for d in due:
                        print(f"  • {d['text']} (set {d['created'][:10]})")
                continue

            if user_input.lower().startswith("/wizard "):
                from wizard import WizardEngine
                we = WizardEngine()
                wizard_name = user_input[8:].strip()
                if wizard_name == "list" or wizard_name == "":
                    print(f"\nAvailable wizards: {', '.join(we.list_wizards())}")
                    print("Usage: /wizard <name>")
                else:
                    try:
                        result = we.run(wizard_name)
                        print(f"\n{result}")
                    except Exception as e:
                        print_error(f"Wizard error: {e}")
                continue

            if user_input.lower().startswith("/pipeline "):
                from pipeline import PipelineRunner
                pr = PipelineRunner()
                preset = user_input[10:].strip()
                if preset == "list" or preset == "":
                    print(f"\nAvailable presets: {', '.join(pr.list_presets())}")
                    print("Usage: /pipeline <preset_name>")
                else:
                    try:
                        results = pr.run_preset(preset)
                        formatted = pr.format_results(results)
                        print(f"\n{formatted}")
                    except Exception as e:
                        print_error(f"Pipeline error: {e}")
                continue

            # ── v3.1 COMMANDS ──

            if user_input.lower().startswith("/research "):
                from deep_research import DeepResearch
                query = user_input[10:]
                dr = DeepResearch()
                with Spinner(f"Researching: {query[:40]}..."):
                    result = dr.research(query, depth="deep")
                print(f"\n{result.get('cited_response', result.get('summary', str(result)))}")
                memory.save_interaction(query, result.get('cited_response', str(result)), "deep_research")
                last_query = query
                last_response = result.get("cited_response", "")
                last_category = "deep_research"
                continue

            if user_input.lower().startswith("/invest "):
                from investment_mining import InvestmentMining
                im = InvestmentMining()
                query = user_input[8:]
                result = im.investment_analysis(query)
                print(f"\n{result['outlook']}")
                print(im.disclaimer())
                memory.save_interaction(query, "Investment analysis provided", "investment")
                last_query = query
                last_response = result.get("outlook", "")
                last_category = "investment"
                continue

            if user_input.lower().startswith("/tax "):
                from tax_engine import TaxEngine
                te = TaxEngine()
                parts = user_input[5:].split(" in ", 1)
                query_type = parts[0].strip() if parts else "personal_income"
                country = parts[1].strip() if len(parts) > 1 else "south africa"
                response_text = te.tax_query(country, query_type)
                print(f"\n{response_text}")
                memory.save_interaction(user_input, "Tax guidance provided", "tax")
                last_query = user_input
                last_response = response_text
                last_category = "tax"
                continue

            if user_input.lower().startswith("/lang "):
                from african_languages import AfricanLanguages
                al = AfricanLanguages()
                parts = user_input[6:].split(" to ", 1)
                text = parts[0].strip()
                lang = parts[1].strip() if len(parts) > 1 else "zu"
                translation = al.translate(text, lang)
                print(f"\n{translation}")
                memory.save_interaction(user_input, "Translation provided", "language")
                last_query = user_input
                last_response = translation
                last_category = "language"
                continue

            if user_input.lower().startswith("/scam "):
                from financial_literacy import FinancialLiteracy
                fl = FinancialLiteracy()
                result = fl.scam_check(user_input[6:])
                print(f"\n🛡️ Scam Check Result:\n{result['risk_level']}\nScore: {result['risk_score']}/100")
                if result['red_flags']:
                    print("\nRed Flags:")
                    for flag in result['red_flags']:
                        print(f"  {flag}")
                print(f"\n{result['advice']}")
                memory.save_interaction(user_input, f"Scam check: {result['risk_score']}/100", "financial_lit")
                last_query = user_input
                last_response = f"Risk: {result['risk_level']} | Score: {result['risk_score']}/100 | Advice: {result['advice']}"
                last_category = "financial_lit"
                continue

            if user_input.lower().startswith("/email "):
                from email_assistant import EmailAssistant
                ea = EmailAssistant()
                draft = user_input[7:]
                improved = ea.improve_email(draft)
                print(f"\n{improved}")
                memory.save_interaction(user_input, "Email assistance provided", "email")
                last_query = user_input
                last_response = improved
                last_category = "email"
                continue

            if user_input.lower().startswith("/opportunity"):
                from opportunity_engine import OpportunityEngine
                oe = OpportunityEngine()
                country = user_input[13:].strip() or ""
                ops = oe.african_opportunities(country)
                print(f"\n## Opportunities in {country or 'Africa'}\n")
                response_lines = []
                for op in ops[:5]:
                    line = f"• {op['title']}"
                    desc_line = f"  {op['description'][:120]}..."
                    print(line)
                    print(desc_line)
                    response_lines.append(line)
                    response_lines.append(desc_line)
                    if op.get('source'):
                        src_line = f"  Source: {op['source']}"
                        print(src_line)
                        response_lines.append(src_line)
                memory.save_interaction(user_input, f"Opportunities in {country or 'Africa'}", "opportunity")
                last_query = user_input
                last_response = "\n".join(response_lines)
                last_category = "opportunity"
                continue

            if user_input.lower().startswith("/prof "):
                from professional_assist import ProfessionalAssist
                pa = ProfessionalAssist()
                domain_query = user_input[6:]
                domain, _, query = domain_query.partition(" ")
                response_text = pa.get_help(domain, query)
                print(f"\n{response_text}")
                memory.save_interaction(user_input, "Professional assistance provided", "professional")
                last_query = user_input
                last_response = response_text
                last_category = "professional"
                continue

            # Default: route through brain
            start_time = time.time()
            with Spinner("Thinking"):
                result = brain.orchestrate_response(user_input)

            response_time = time.time() - start_time

            # Track last interaction for /save command
            last_query = user_input
            last_response = result.get("response", "")
            last_category = result.get("module", "general")

            # Print response
            print(f"\n{result['response']}")

            # Add citations if sources exist
            if result.get('sources'):
                from citation_engine import format_citations
                print(format_citations(result['sources']))

            # Save interaction
            memory.save_interaction(user_input, result['response'], result.get('module', 'general'))

            # Show category info
            cat_color = {
                "deep_research": Colors.CYAN, "investment": Colors.YELLOW,
                "tax": Colors.GREEN, "financial_lit": Colors.MAGENTA,
                "language": Colors.BLUE, "professional": Colors.WHITE,
                "opportunity": Colors.YELLOW, "email": Colors.CYAN,
                "price_ticker": Colors.GREEN, "calc": Colors.CYAN,
            }.get(result.get('module', ''), Colors.DIM)

            cat_label = result.get("module", "general")
            meta_line = f"[{cat_label}] • {response_time:.1f}s"
            print(f"\n{colorize(meta_line, Colors.DIM + cat_color)}")

            # Prompt for rating
            rating_input = input(colorize("Rate this response (1-5, Enter=skip): ", Colors.DIM)).strip()
            if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
                memory.record_feedback(user_input, result['response'], int(rating_input), module=result.get('module', 'general'))
                print(colorize("  ✓ Thank you for your feedback!", Colors.GREEN))

        except KeyboardInterrupt:
            print(colorize("\n\nInterrupted. Use /quit to exit properly.", Colors.YELLOW))
        except EOFError:
            break
        except Exception as e:
            print_error(f"Error: {e}")
            if CONFIG.get("DEBUG"):
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
