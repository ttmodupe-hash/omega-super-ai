# Omega Super AI v10

> A terminal-based super AI assistant with multi-agent deep research, critical thinking, companion mentoring, professional domain expertise, financial literacy, and scam protection.

## Capabilities

| Module | Description |
|--------|-------------|
| **Deep Research Swarm** | Multi-angle web research with parallel search, content extraction, and synthesis |
| **Critical Thinking** | Chain-of-thought reasoning, bias detection, fact verification, fallacy detection |
| **Companion Mentor** | Personalized learning paths, goal coaching, quizzes, study guides |
| **Domain Experts** | 13 professional domains: engineering, architecture, plumbing, medical, legal, IT, agriculture, automotive, culinary, finance, construction, beauty, education |
| **Financial Advisor** | Investment analysis, budget planning, financial education, scam detection |
| **Scam Guard** | 15-pattern fraud detection, URL analysis, protection tips, scam reporting |

## Quick Start

```bash
py -3.11 -m pip install -r requirements.txt
copy .env.example .env
# Edit .env with your API keys
py -3.11 omega.py
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `[any question]` | Intelligent auto-routing | `What is quantum computing?` |
| `/research <query>` | Deep multi-angle research | `/research renewable energy trends 2025` |
| `/think <query>` | Critical thinking analysis | `/think Is AI a threat to jobs?` |
| `/mentor <topic>` | Personalized learning path | `/mentor Python programming` |
| `/expert <domain>` | Professional consultation | `/expert plumbing How to fix a leaky faucet?` |
| `/finance <query>` | Financial advice & analysis | `/finance How does compound interest work?` |
| `/scam <description>` | Scam/fraud detection | `/scam I got an email saying I won $1M` |
| `/learn <topic>` | Interactive learning mode | `/learn machine learning basics` |
| `/history` | Show conversation history | |
| `/memory` | Show saved memories | |
| `/clear` | Clear the screen | |
| `/help` | Show all commands | |
| `/quit` | Exit | |

## Project Structure

```
omega-super-ai/
 omega.py              # Launcher script (run this)
 requirements.txt      # Python dependencies
 .env.example          # API key template
 README.md             # This file
 omega/
   __init__.py         # Package init
   config.py           # Configuration & API keys
   database.py         # SQLite persistence
   utils.py            # Terminal UI utilities
   omega.py            # Main CLI & REPL
   search_engines.py   # Multi-engine search
   content_extractor.py # Web content extraction
   research_swarm.py   # Multi-agent deep research
   critical_thinker.py # Reasoning engine
   companion.py        # Mentoring mode
   domain_experts.py   # Professional domains
   financial_advisor.py # Financial literacy
   scam_guard.py       # Fraud protection
```

## Safety & Disclaimers

- **Financial Advice**: All financial guidance is educational only. Consult a licensed financial advisor.
- **Medical/Legal**: Domain expert outputs are informational, not professional advice.
- **Scam Detection**: Analysis is probabilistic — always verify independently and report to authorities.

## License

MIT License
