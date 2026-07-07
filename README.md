# Luqi AI v20

```
 ██░     ██░   ██░ ██████░ ██░     ███████░
 ██░     ██░   ██░██╔═══██░██░     ██╔════╝
 ██░     ██░   ██░██░   ██░██░     ███████░
 ██░     ██░   ██░██░▄▄ ██░██░     ╚════██░
 ███████░╚██████░▄▄██████▄▄███████░███████░
 ╚══════╝ ╚═════╝  ╚══▄▄╔▄═╝ ╚═════╝╚══════╝
          v20 — World-class AI for Africa & Beyond
```

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38bdf8.svg)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v20.0.0-blue.svg)](https://github.com/ttmodupe-hash/omega-super-ai)
[![Endpoints](https://img.shields.io/badge/endpoints-195+-brightgreen.svg)]()
[![Lines of Code](https://img.shields.io/badge/loc-82k+-blueviolet.svg)]()

> **World-class AI serving Africa and the world.** Built for limited resources, works offline, supports 85 languages, and never puts capability behind a paywall.

---

## What Makes Luqi AI Different

| Feature | Typical AI Platform | Luqi AI |
|---------|-------------------|---------|
| Internet required | Yes | **No** — offline mode + SMS |
| Languages | 5-10 | **85** including 54 African |
| Subscription cost | $20-100/month | **Free tier + affordable Pro** |
| African agriculture | Not available | **16 crops, 6 regions** |
| Legal studies | Western only | **US + UK + Nigeria + SA + Kenya + Ghana** |
| Works on feature phone | No | **Yes — via SMS** |
| Open source | No | **Yes — MIT License** |

---

## Capabilities (v13 — v20)

Luqi AI is organized into 8 capability versions, each adding major new features:

| Version | Module | Endpoints | What It Does |
|---------|--------|-----------|-------------|
| **v13** | Core Engine | 15 | Chat, memory, search, financial analysis |
| **v14** | SaaS Platform | 41 | Subscriptions, developer tools, website builder, dashboard |
| **v15** | ASI Engine | 31 | Cognitive engine, education system, voice, safety, physics |
| **v16** | Production | 21 | GitHub integration, notifications, data portability |
| **v17** | Leadership | 25 | Project captainship, emotional companionship |
| **v18** | Specialist | 17 | Automotive diagnostics, writing assistant |
| **v19** | **Law Studies** | 20 | Legal research, case briefing, bar exam, citation |
| **v20** | **Africa-First** | 38 | Agriculture, healthcare, education, business, offline |

**Total: 195+ endpoints across 41 modules, 82,000+ lines of Python**

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (React 18 + Tailwind CSS) — 20 pages, PWA           │
├──────────────────────────────────────────────────────────┤
│  FastAPI Backend — 195+ endpoints, async, streaming            │
├──────────────────────────────────────────────────────────┤
│  ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │v13   │ │v14-v16│ │v17-v18  │ │v19      │ │v20      │    │
│  │Core  │ │SaaS    │ │Specialist│ │Law     │ │Africa  │    │
│  └──────┘ └────────┘ └──────────┘ └──────────┘ └──────────┘    │
├──────────────────────────────────────────────────────────┤
│  AI: OpenAI GPT-4o • Vector DB: ChromaDB • Cache: SQLite       │
└──────────────────────────────────────────────────────────┘
```

---

## v20 Africa-First Capabilities

Designed specifically for areas with limited internet, limited power, and limited resources.

### Agriculture Advisor (335KB, 6,819 lines)
- **16 crops**: maize, rice, cassava, yam, sorghum, millet, beans, groundnut, and more
- **6 African regions**: West Africa, East Africa, Southern Africa, Central Africa, North Africa, Sahel
- **Pest diagnosis** with organic treatments (neem, wood ash, chili spray)
- **Market prices** for major African commodity markets
- **Farm planning** with budget-aware crop rotation schedules

### Healthcare Assistant (229KB, 5,744 lines)
- **First aid**: burns, bleeding, choking, poisoning, fracture, snakebite, heatstroke
- **Maternal health**: pregnancy guidance, warning signs, nutrition
- **Child health**: milestones, vaccinations, fever/diarrhea management
- **Nutrition**: local food recommendations, hydration guidelines
- **Emergency numbers** by country
- **DISCLAIMER**: All health info is educational only — consult a professional

### Teacher Assistant (241KB, 4,920 lines)
- **20 subjects**: mathematics, science, English, social studies, ICT, agriculture, and more
- **12 grade levels**: Primary 1-6, JSS 1-3, SSS 1-3
- **Lesson plan generator** with objectives, materials, activities, assessment
- **Worksheet generator** with answer keys
- **Teaching tips** for large classes, low resources, mixed abilities
- **STEM experiments** using household materials

### Business Advisor (163KB, 3,596 lines)
- **13 business plan templates**: retail, agriculture, tech, food, fashion, services
- **Market research**: demand analysis, competition assessment, pricing
- **Financial planning**: budget calculator, breakeven analysis
- **Business registration** guides for 8 African countries

### Offline Engine (141KB, 3,336 lines)
- **Works without internet**: cached responses for common questions
- **SMS interface**: query by text message, receive answers by SMS
- **200+ FAQ entries** across agriculture, health, education, business, weather, emergency
- **Sync manager**: automatically updates when connection returns
- **Bandwidth optimizer**: compresses responses for low-speed connections

---

## Quick Start

### Prerequisites
- Python 3.11+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# Validate installation
python3 startup_check.py

# Start the server
python3 start_server.py
```

Visit [http://localhost:8000](http://localhost:8000) — the web UI loads automatically.

API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Environment Variables

### Required

| Variable | Description | Format |
|----------|-------------|--------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` or `sk_live_...` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `pk_test_...` or `pk_live_...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook endpoint secret | — |
| `SENDGRID_API_KEY` | SendGrid email API key | — |
| `SERPER_API_KEY` | Serper.dev search API key | — |
| `DATABASE_URL` | SQLite database path | `./luqi.db` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `VAPID_PUBLIC_KEY` | Web Push VAPID public key | — |
| `VAPID_PRIVATE_KEY` | Web Push VAPID private key | — |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI Engine** | OpenAI GPT-4o (with streaming) |
| **Vector DB** | ChromaDB |
| **Database** | SQLite |
| **Payments** | Stripe |
| **Email** | SendGrid (with SMTP fallback) |
| **Voice** | gTTS + pyttsx3 |
| **Frontend** | React 18, Tailwind CSS, single-file SPA |
| **PWA** | Service Worker, Web Manifest |
| **Security** | Rate limiting, security headers, request ID tracing |

---

## Deployment

### Docker

```bash
docker-compose up --build
```

### Railway (Recommended for 72-Hour Launch)

1. Connect your GitHub repo to [Railway](https://railway.app)
2. Add environment variables in Railway dashboard
3. Deploy automatically on every push

### Manual Production

```bash
python3 start_server.py --prod
# or
uvicorn backend.router:app --host 0.0.0.0 --port 8000
```

**System Requirements:**
- RAM: 512MB minimum, 1GB recommended
- Disk: 500MB for code + data
- Network: Port 8000 (or $PORT for cloud)

---

## Production Hardening (v20)

Luqi AI v20 includes enterprise-grade production middleware:

- **Rate limiting**: 30/min default, 10/min auth, 5/min upload (via slowapi)
- **Security headers**: X-Frame-Options, HSTS, CSP, Referrer-Policy
- **Request logging**: Every request logged with timing, method, path, request ID
- **Error handling**: Safe JSON responses, no traceback leakage
- **Health monitoring**: `/api/health` returns module-by-module status
- **Startup validation**: `startup_check.py` validates all 53 imports before launch

---

## Project Structure

```
omega-super-ai/
│
├── backend/                     # Backend Python modules
│   ├── __init__.py              # Package init (v20.0.0)
│   ├── router.py                # FastAPI app + core endpoints
│   ├── middleware.py            # Production hardening layer
│   ├── config.py                # Configuration management
│   ├── chat.py                  # AI chat engine
│   ├── ai_engine.py             # Core AI engine
│   ├── memory.py                # Vector memory (ChromaDB)
│   ├── search.py                # Web search
│   ├── financial.py             # Financial analysis
│   ├── taxes.py                 # Tax computation
│   ├── files.py                 # File processing
│   ├── images.py                # Image generation
│   ├── agents.py                # Agent orchestration
│   ├── subscriptions.py         # SaaS billing (Stripe)
│   ├── developer.py             # Code generation (25 languages)
│   ├── website_builder.py       # Website generation
│   ├── dashboard.py             # Analytics dashboard
│   ├── cognitive_engine.py      # ASI multi-agent engine
│   ├── education_system.py      # K-PhD digital tutor
│   ├── voice_system.py          # TTS/STT (92 languages)
│   ├── safety_alignment.py      # Red-teaming & safety
│   ├── physics_simulator.py     # Science simulations
│   ├── github_integration.py    # GitHub API integration
│   ├── notifications.py         # Web push notifications
│   ├── data_portability.py      # GDPR export/import
│   ├── captainship.py           # Project management
│   ├── companionship.py         # Emotional AI companion
│   ├── automotive.py            # Vehicle diagnostics
│   ├── writing_assistant.py     # Grammar & style checker
│   ├── law_studies.py           # v19: Legal AI
│   ├── agricultural_advisor.py  # v20: Farming guidance
│   ├── healthcare_assistant.py  # v20: Health information
│   ├── teacher_assistant.py     # v20: Teaching tools
│   ├── business_advisor.py      # v20: Business planning
│   ├── offline_engine.py        # v20: Offline/SMS access
│   ├── stripe_integration.py    # Stripe payments
│   ├── email_system.py          # Email templates
│   ├── v14_endpoints.py         # v14 API routes
│   ├── v15_endpoints.py         # v15 API routes
│   ├── v16_endpoints.py         # v16 API routes
│   ├── v17_endpoints.py         # v17 API routes
│   ├── v18_endpoints.py         # v18 API routes
│   ├── v19_endpoints.py         # v19 API routes
│   └── v20_endpoints.py         # v20 API routes
│
├── web/                         # Frontend
│   ├── index.html               # Main SPA (20 pages)
│   ├── admin.html               # Admin dashboard
│   ├── sw.js                    # Service worker (PWA)
│   └── manifest.json            # PWA manifest
│
├── uploads/                     # Uploaded files
├── chroma_db/                   # Vector database
├── generated_images/            # AI-generated images
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── Dockerfile                   # Container image
├── docker-compose.yml           # Docker orchestration
├── start_server.py              # Server launcher
├── startup_check.py             # Pre-flight validation
├── push_to_github.py            # Git sync utility
├── 72_HOUR_LAUNCH_PLAN.md       # Launch guide
└── README.md                    # This file
```

---

## Contributing

Contributions are welcome! Luqi AI is open source forever.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- **Formatter**: `black backend/`
- **Import sorter**: `isort backend/`
- **Type checker**: `mypy backend/`
- **Tests**: `pytest tests/`

---

## Changelog

| Version | Date | Highlights |
|---------|------|-----------|
| v13 | 2024 | Core AI engine: chat, memory, search, financial |
| v14 | 2024 | SaaS platform: subscriptions, developer, website builder |
| v15 | 2024 | ASI engine: cognitive, education, voice, safety, physics |
| v16 | 2024 | Production: GitHub integration, notifications, GDPR |
| v17 | 2025 | Leadership: captainship, emotional companionship |
| v18 | 2025 | Specialist: automotive diagnostics, writing assistant |
| **v19** | 2025 | **Law Studies**: IRAC/CREAC briefing, 51 landmark cases, bar exam |
| **v20** | 2025 | **Africa-First**: agriculture, health, education, business, offline |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Luqi AI is **free forever** for personal and educational use. Commercial use requires a Pro license.

---

## Acknowledgments

Built with love for Africa and the world. Designed to work everywhere — from fiber-connected offices in Lagos to offline villages in rural Kenya.

**Special thanks** to everyone who believes AI should serve all of humanity, not just the privileged few.

---

<p align="center">
  <strong>Luqi AI v20</strong> — World-class AI for Africa & Beyond<br>
  <a href="https://github.com/ttmodupe-hash/omega-super-ai">GitHub</a> ·
  <a href="https://github.com/ttmodupe-hash/omega-super-ai/issues">Issues</a> ·
  <a href="https://github.com/ttmodupe-hash/omega-super-ai/discussions">Discussions</a>
</p>
