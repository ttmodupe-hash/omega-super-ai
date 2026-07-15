#!/usr/bin/env python3
"""Omega AI v3 — Luqi-AI
The main entry point for the Luqi-AI intelligent assistant.
Run with: python omega_ai.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure local modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONFIG, validate_config, get_memory_dir
from utils import colorize, Colors, print_header, print_success, print_error, print_info, print_warning, Spinner, sanitize_input
from core_brain import OmegaBrain
from memory_store import MemoryStore


def main() -> None:
    """Main CLI loop for Luqi-AI."""
    brain = OmegaBrain()
    memory = MemoryStore()

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

            if user_input.lower().startswith("/research "):
                from deep_research import deep_research
                query = user_input[10:]
                with Spinner(f"Researching: {query[:40]}..."):
                    result = deep_research(query, depth="deep")
                print(f"\n{result['cited_response']}")
                memory.save_interaction(query, result['cited_response'], "deep_research")
                continue

            if user_input.lower().startswith("/invest "):
                from investment_mining import InvestmentMining
                im = InvestmentMining()
                query = user_input[8:]
                print(f"\n{im.investment_analysis(query)['outlook']}")
                print(im.disclaimer())
                memory.save_interaction(query, "Investment analysis provided", "investment")
                continue

            if user_input.lower().startswith("/tax "):
                from tax_engine import TaxEngine
                te = TaxEngine()
                parts = user_input[5:].split(" in ", 1)
                query_type = parts[0].strip() if parts else "personal_income"
                country = parts[1].strip() if len(parts) > 1 else "south africa"
                print(f"\n{te.tax_query(country, query_type)}")
                memory.save_interaction(user_input, "Tax guidance provided", "tax")
                continue

            if user_input.lower().startswith("/lang "):
                from african_languages import AfricanLanguages
                al = AfricanLanguages()
                parts = user_input[6:].split(" to ", 1)
                text = parts[0].strip()
                lang = parts[1].strip() if len(parts) > 1 else "zu"
                print(f"\n{al.translate(text, lang)}")
                memory.save_interaction(user_input, "Translation provided", "language")
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
                continue

            if user_input.lower().startswith("/email "):
                from email_assistant import EmailAssistant
                ea = EmailAssistant()
                draft = user_input[7:]
                print(f"\n{ea.improve_email(draft)}")
                memory.save_interaction(user_input, "Email assistance provided", "email")
                continue

            if user_input.lower().startswith("/opportunity"):
                from opportunity_engine import OpportunityEngine
                oe = OpportunityEngine()
                country = user_input[13:].strip() or ""
                ops = oe.african_opportunities(country)
                print(f"\n## Opportunities in {country or 'Africa'}\n")
                for op in ops[:5]:
                    print(f"• {op['title']}")
                    print(f"  {op['description'][:120]}...")
                    if op.get('source'):
                        print(f"  Source: {op['source']}")
                memory.save_interaction(user_input, f"Opportunities in {country or 'Africa'}", "opportunity")
                continue

            if user_input.lower().startswith("/prof "):
                from professional_assist import ProfessionalAssist
                pa = ProfessionalAssist()
                domain_query = user_input[6:]
                domain, _, query = domain_query.partition(" ")
                print(f"\n{pa.get_help(domain, query)}")
                memory.save_interaction(user_input, "Professional assistance provided", "professional")
                continue

            # Default: route through brain
            start_time = time.time()
            with Spinner("Thinking"):
                result = brain.orchestrate_response(user_input)

            response_time = time.time() - start_time

            # Print response
            print(f"\n{result['response']}")

            # Add citations if sources exist
            if result.get('sources'):
                from citation_engine import format_citations
                print(format_citations(result['sources']))

            # Save interaction
            memory.save_interaction(user_input, result['response'], result.get('category', 'general'))

            # Show category info
            cat_color = {
                "deep_research": Colors.CYAN, "investment": Colors.YELLOW,
                "tax": Colors.GREEN, "financial_lit": Colors.MAGENTA,
                "language": Colors.BLUE, "professional": Colors.WHITE,
                "opportunity": Colors.YELLOW, "email": Colors.CYAN,
            }.get(result.get('category', ''), Colors.DIM)

            cat_label = result.get("category", "general")
            meta_line = f"[{cat_label}] • {response_time:.1f}s"
            print(f"\n{colorize(meta_line, Colors.DIM + cat_color)}")

            # Prompt for rating
            rating_input = input(colorize("Rate this response (1-5, Enter=skip): ", Colors.DIM)).strip()
            if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
                memory.record_feedback(user_input, result['response'], int(rating_input), module=result.get('category', 'general'))
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
