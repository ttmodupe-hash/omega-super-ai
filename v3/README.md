# Luqi-AI v3.2 — Omega AI

**Intelligence Without Limits**

Luqi-AI (Omega AI v3.2) is a comprehensive, multi-capability AI assistant designed for terminal/CLI use. It features deep research, investment guidance, tax support, companion learning, African language support, financial literacy, professional assistance, conversation memory, user preferences, streaming responses, a plugin architecture, crypto price tracking, calculators, reminders, learning progress, history search, guided wizards, capability pipelines, and an HTTP API server.

![Version](https://img.shields.io/badge/version-3.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Quick Start

```bash
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai/v3
pip install -r requirements.txt      # only needs requests>=2.31.0
python omega_ai.py                   # runs in full mock mode, zero API keys needed
```

To unlock LLM power, add API keys to a `.env` file (see `.env.example`).

## Capabilities (25 Total)

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **Deep Research** | Multi-source research with citations, 3 depth levels |
| 2 | **Investment & Mining** | Crypto/BTC mining guidance, profitability calculator |
| 3 | **Tax Engine** | Global tax support (60+ countries), African focus |
| 4 | **Financial Literacy** | 36 lessons, scam detection, budget planner |
| 5 | **African Languages** | 22 languages, phrases, cultural context |
| 6 | **Professional Assist** | 25 domains: engineering, medical, legal, trades |
| 7 | **Opportunity Engine** | African market opportunities, trend analysis |
| 8 | **Email Assistant** | Grammar check, 7 templates, tone analysis |
| 9 | **Companion Trainer** | Rate responses, submit corrections |
| 10 | **Self-Improvement Lab** | Performance analytics, real benchmarks |
| 11 | **Conversation Memory** | Context-aware responses |
| 12 | **User Preferences** | Persistent settings |
| 13 | **Export/Save** | Save to Markdown |
| 14 | **Streaming** | Real-time LLM streaming |
| 15 | **Plugin Architecture** | Self-registering capabilities |
| 16 | **Crypto Price Ticker** | Live prices + alerts (v3.2) |
| 17 | **Calculators** | Currency, mining, tax, compound, loans (v3.2) |
| 18 | **Reminders** | Deadline tracking (v3.2) |
| 19 | **Learning Tracker** | Lesson progress (v3.2) |
| 20 | **History Search** | Search conversations (v3.2) |
| 21 | **Guided Wizards** | Multi-step workflows (v3.2) |
| 22 | **Capability Pipelines** | Chain commands (v3.2) |
| 23 | **Bilingual Mode** | African language responses (v3.2) |
| 24 | **Multi-Format Export** | CSV, JSON, Markdown (v3.2) |
| 25 | **HTTP API Server** | REST API mode (v3.2) |

## CLI Commands

| Command | Description |
|---------|-------------|
| `/menu` | Show capability menu |
| `/price [symbols]` | Crypto price table |
| `/alert <sym> <above/below> <price>` | Set price alert |
| `/calc <args>` | Quick calculator |
| `/search <query>` | Search conversation history |
| `/history` | List recent conversations |
| `/clear` | Clear all history |
| `/learn` | Financial literacy progress |
| `/wizard <name>` | Guided workflow |
| `/pipeline <preset>` | Capability chaining |
| `/remind <text> [on <date>]` | Set reminder |
| `/reminders` | List reminders |
| `/train` | Enter training mode |
| `/status` | System health + benchmark |
| `/save [filename]` | Export to Markdown |
| `/prefs` | View preferences |
| `/prefs set <key> <val>` | Change preference |
| `/research <query>` | Deep research |
| `/invest <asset>` | Investment analysis |
| `/tax <type> in <country>` | Tax guidance |
| `/lang <text> to <lang>` | Translation |
| `/scam <description>` | Scam check |
| `/email <draft>` | Email improvement |
| `/opportunity [country]` | Business opportunities |
| `/prof <domain> <query>` | Professional help |
| `/quit` | Exit |

## API Server Mode

```bash
python omega_ai.py --server --port 8080
```

Endpoints: `/api/health`, `/api/chat`, `/api/research`, `/api/invest/*`, `/api/tax/*`, `/api/price/*`, `/api/calc`, `/api/scam/*`, `/api/email/*`, `/api/lang/*`, `/api/opportunities/*`

## Architecture

32 Python modules, 11,800+ lines, zero required external dependencies (LLMs optional).

## License

MIT License — Luqi AI Labs
