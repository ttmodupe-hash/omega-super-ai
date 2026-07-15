# Luqi-AI v3 — Omega AI

**Intelligence Without Limits**

Luqi-AI (Omega AI v3) is a comprehensive, multi-capability AI assistant designed for terminal/CLI use. It features deep research, investment guidance, tax support, companion learning, African language support, financial literacy, and professional assistance across all domains.

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## Features

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **Deep Research** | Multi-source research with citations, 3 depth levels (quick/deep/comprehensive) |
| 2 | **Investment & Mining** | Crypto/BTC mining guidance, profitability calculator, portfolio advice |
| 3 | **Tax Engine** | Global tax support (60+ countries), African focus (SA, Nigeria, Kenya, Ghana, Egypt, Morocco) |
| 4 | **Financial Literacy** | 18 topics, scam detection (80+ indicators), budget planner |
| 5 | **African Languages** | 22 languages, phrases, cultural context, learn mode |
| 6 | **Professional Assist** | 25 domains: engineering, medical, legal, trades, culinary, nursing |
| 7 | **Opportunity Engine** | African market opportunities, trend analysis, market gap detection |
| 8 | **Email Assistant** | Grammar check (30+ rules), 7 templates, tone analysis |
| 9 | **Companion Trainer** | Rate responses, submit corrections, training mode |
| 10 | **Self-Improvement Lab** | Performance analytics, health checks, benchmarks |

---

## Quick Start

### 1. Clone or Download

```bash
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai/v3
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run

```bash
python omega_ai.py
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Required: At least one of these
OPENAI_API_KEY=sk-your-key          # OpenAI fallback
SERPER_API_KEY=your-serper-key      # Web search

# Optional: Local LLM (recommended)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

# Optional
DEBUG=false
DEFAULT_DEPTH=deep
```

**Note:** The system works in "mock mode" without any API keys, using built-in knowledge and keyword-based responses.

---

## Usage

### Interactive Mode
```bash
python omega_ai.py
```

### Quick Commands

| Command | Description |
|---------|-------------|
| `/menu` | Show capability menu |
| `/train` | Enter companion training mode |
| `/status` | System health report |
| `/research <query>` | Deep research |
| `/invest <asset>` | Investment analysis |
| `/tax <type> in <country>` | Tax guidance |
| `/lang <text> to <language>` | Translation |
| `/scam <description>` | Scam check |
| `/email <draft>` | Email improvement |
| `/opportunity <country>` | Business opportunities |
| `/quit` | Exit |

### Example Queries

```
How do I start Bitcoin mining in South Africa?
What are the tax brackets in Nigeria?
Translate hello to Zulu
Is this a scam? Guaranteed 100% daily returns
Write a professional email to request a meeting
What business opportunities exist in Kenya?
```

---

## Architecture

```
v3/
├── omega_ai.py           # Main entry point
├── config.py             # Configuration & env
├── core_brain.py         # Intent routing & orchestration
├── utils.py              # Colors, formatting, helpers
├── local_llm.py          # Ollama + OpenAI integration
├── web_search.py         # Serper API search
├── citation_engine.py    # Source verification & citations
├── memory_store.py       # Persistent memory & feedback
├── deep_research.py      # Multi-agent research swarm
├── opportunity_engine.py # Opportunity detection
├── investment_mining.py  # Crypto investment & mining
├── tax_engine.py         # Global tax support
├── financial_literacy.py # Financial education & scam protection
├── companion_trainer.py  # User training & feedback
├── self_improve.py       # Performance analytics
├── african_languages.py  # African language support
├── professional_assist.py # Multi-domain professional help
├── email_assistant.py    # Email composition & grammar
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

---

## Capabilities Detail

### Deep Research
- Automatic sub-query generation
- Cross-source verification
- 3 depth levels: quick (1-2 sources), deep (3-5 sub-queries), comprehensive (full swarm)
- Historical context detection
- Every claim cited

### Investment & Mining
- Mining profitability calculator (hash rate, power cost, hardware)
- ASIC comparison catalog (8 models)
- Portfolio analysis & risk assessment
- Live crypto prices (CoinGecko API)
- **Disclaimer:** Not financial advice

### Tax Engine
- Personal income, corporate, VAT, capital gains, crypto tax
- 9 detailed country profiles + generic template for 190+ countries
- African focus: SARS, FIRS, KRA, GRA, ETA, DGI
- Step-by-step filing guides
- **Disclaimer:** General guidance only

### African Languages
- 22 languages: Zulu, Xhosa, Swahili, Yoruba, Amharic, Hausa, Igbo, Shona, Afrikaans, and more
- Common phrases: greetings, thanks, numbers 1-10
- Cultural context notes
- Language detection

### Financial Literacy
- 18 topics × 3 levels = 54 lessons
- Scam detection: 80+ weighted indicators, 0-100 risk score
- 17 scam types covered
- Budget planner with 50/30/20 analysis
- Savings roadmap generator

### Professional Assist
- 25 professional domains
- Code assistance (Python, JS, Java, C++, SQL)
- Engineering calculations (mechanical, electrical, civil)
- Safety notes for trades
- Medical/legal disclaimers

### Self-Improvement Lab
- Performance metrics & analytics
- System health monitoring
- Capability benchmarking
- Improvement suggestions
- Uptime & error tracking

---

## Requirements

- Python 3.11+
- `requests` library (`pip install requests`)
- Optional: Ollama for local LLM
- Optional: API keys for enhanced features

---

## African Focus

Luqi-AI is built with Africa in mind:
- **Tax:** Detailed coverage of SARS, FIRS, KRA, GRA
- **Languages:** 22 African languages with cultural context
- **Financial:** Stokvels, mobile money, African scam patterns
- **Opportunities:** African market analysis
- **Professional:** Covers trades and professions common across Africa

---

## Safety & Disclaimers

- **Financial:** All investment advice includes risk warnings. Not financial advice.
- **Tax:** General guidance only. Consult a qualified tax professional.
- **Medical/Legal:** General information only. Consult licensed professionals.
- **Scam Detection:** Automated analysis, not a guarantee. Always verify independently.

---

## License

MIT License — see LICENSE file for details.

---

## Brand

- **Name:** Luqi-AI
- **Domain:** luqi-ai.com
- **Motto:** Intelligence Without Limits

---

Built with ❤️ by Luqi AI Labs
