# Luqi AI v24.0.0

<p align="center">
  <img src="web/icons/icon-192x192.png" alt="Luqi AI Logo" width="120">
</p>

<p align="center">
  <strong>World-Class AI SaaS Platform — Serving Africa and the World</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#api">API</a> &bull;
  <a href="#deployment">Deploy</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-24.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/endpoints-300%2B-green" alt="Endpoints">
  <img src="https://img.shields.io/badge/lines-115K%2B-orange" alt="Code Size">
</p>

---

## What's New in v24

| Feature | Description |
|---------|-------------|
| **Global Knowledge Academy** | 11 disciplines, 55 schools of thought with debate simulator and ELI5 explainer |
| **Network & AI Engineering Training** | 3-phase curriculum (CCNA→CCNP→CCIE) with virtual device simulation |
| **Workspace Collaboration** | Real-time workspaces with messaging, video conferencing, and AI-powered assistance |
| **Project Management Training** | 8 methodologies, 22 templates, Gantt charts, sprint simulator |
| **Digital Workspace Training** | 51 tools, 10 productivity methods, phishing simulator |

---

## Quick Start

### Option 1: Using Make (Recommended)

```bash
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai
make install-dev
make dev
```

### Option 2: Using Docker Compose

```bash
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

### Option 3: Manual Setup

```bash
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[all]"
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
uvicorn backend.router:app --reload --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in your browser.

---

## Complete Feature Catalog

### v13 — Multi-Agent Core (Foundation)

| Feature | Description |
|---------|-------------|
| **AI Chat** | Conversational AI with GPT-4o/Claude/Gemini, streaming responses |
| **Deep Research** | Multi-agent swarm research with parallel search and synthesis |
| **Critical Thinking** | Chain-of-thought reasoning, bias detection, fact verification |
| **Companion Mentor** | Personalized learning paths, goal coaching, study guides |
| **Domain Experts** | 13+ professional domains: engineering, medical, legal, IT, finance |
| **Financial Advisor** | Investment analysis, budget planning, scam detection |
| **Scam Guard** | 15-pattern fraud detection with URL analysis |
| **File Upload** | PDF, DOCX, TXT, PNG, JPG analysis with extraction |
| **Vector Memory** | Persistent ChromaDB-based memory for conversations |
| **Web Search** | Live web search via Serper API with source citations |
| **PWA Support** | Install as standalone app on desktop and mobile |
| **REST API** | Full-featured FastAPI backend with auto-generated docs |

### v14 — SaaS Platform

| Feature | Description |
|---------|-------------|
| **Subscription Management** | Stripe-powered billing, plans, invoices |
| **Developer Portal** | API key management, usage analytics, webhooks |
| **Website Builder** | AI-powered site generation with templates |
| **Dashboard Analytics** | Usage metrics, revenue tracking, user insights |

### v15 — ASI Cognitive Engine

| Feature | Description |
|---------|-------------|
| **Autonomous Reasoning** | Multi-step cognitive reasoning with planning |
| **Education System** | Adaptive curriculum with mastery tracking |
| **Voice Synthesis** | Text-to-speech with multi-language support |
| **Safety Guardrails** | Content moderation, toxicity detection |
| **Physics Engine** | Computational physics simulations |

### v16 — Production Features

| Feature | Description |
|---------|-------------|
| **GitHub Integration** | Code analysis, PR review, repository insights |
| **Notifications** | Multi-channel alerts (email, SMS, push) |
| **Data Portability** | GDPR-compliant data export/delete |

### v17 — Captainship & Companionship

| Feature | Description |
|---------|-------------|
| **AI Captainship** | Strategic planning with AI-assisted decision making |
| **Companionship** | Long-term relationship building with memory |

### v18 — Automotive & Writing

| Feature | Description |
|---------|-------------|
| **Automotive Advisor** | Vehicle diagnostics, maintenance scheduling |
| **Writing Assistant** | Creative writing, editing, plagiarism check |

### v19 — Law Studies

| Feature | Description |
|---------|-------------|
| **Legal Education** | Complete law curriculum with case studies |
| **Legal AI Assistant** | Contract analysis, legal research, document drafting |
| **African Law Coverage** | Jurisdiction-specific legal guidance for 54 countries |

### v20 — Africa-First Capabilities

| Feature | Description |
|---------|-------------|
| **Agricultural Advisor** | Smart farming, crop management, weather integration |
| **Healthcare Assistant** | Telemedicine guidance, symptom checker, health education |
| **Teacher Assistant** | Lesson planning, quiz generation, grading support |
| **Business Advisor** | SME support, market analysis, business planning |
| **Offline Engine** | Works without internet via local LLM fallback |

### v21 — Jobs, WhatsApp & Government

| Feature | Description |
|---------|-------------|
| **Jobs & Skills** | CV builder, interview prep (500+ questions), salary guides, career planning |
| **WhatsApp Bot** | 200+ FAQ responses, 10 languages, Twilio integration, menu system |
| **Government Services** | ID, passport, business registration, tax, voting, land — 50+ countries |

### v22 — Workspace Collaboration

| Feature | Description |
|---------|-------------|
| **Real-time Workspaces** | Create/join collaborative workspaces with role-based access |
| **Socket.io Messaging** | Instant messaging with Redis Pub/Sub for scalability |
| **File Sharing** | Upload, version, and share files within workspaces |
| **Video Conferencing** | WebRTC-powered meetings via LiveKit |
| **Presence Indicators** | Typing indicators, online status, read receipts |
| **@ai Mentions** | Tag AI for contextual assistance in conversations |
| **AI Agent Worker** | Background AI processing for mentioned queries |

### v23 — Network & AI Engineering Training

| Feature | Description |
|---------|-------------|
| **3-Phase Curriculum** | CCNA → CCNP → CCIE progressive learning paths |
| **Virtual Devices** | Simulated routers, switches, firewalls |
| **Protocol Simulation** | OSPF, BGP, STP state machines with packet tracing |
| **Topology Generator** | Auto-generate network topologies for labs |
| **Scenario Injection** | Break/fix scenarios for hands-on learning |
| **Grading Engine** | Automated lab assessment with detailed feedback |
| **Quiz Engine** | Adaptive quizzes with difficulty scaling |
| **Certificate Generator** | Completion certificates with verification |

### v24 — Global Knowledge Academy

| Feature | Description |
|---------|-------------|
| **Knowledge Academy** | 11 disciplines with 55 schools of thought |
| **Debate Simulator** | Structured, Socratic, and Battle debate formats |
| **ELI5 Explainer** | Complex concepts explained simply |
| **Project Management Training** | Agile, Scrum, Kanban, Waterfall, Hybrid, Lean, Six Sigma, PRINCE2 |
| **Digital Workspace Training** | 51 tools, 10 productivity methods, security awareness |

### v24.1 — Infrastructure & DevOps

| Feature | Description |
|---------|-------------|
| **Enhanced Middleware** | Rate limiting, structured logging, 11 security headers |
| **Multi-tier Cache** | Redis L1 + in-memory L2 with TTL and invalidation |
| **Background Tasks** | RQ production + threading dev fallback with retry logic |
| **Health Check System** | 12-subsystem deep health probes with degradation alerts |
| **Config Validator** | Pydantic-based env validation with sensible defaults |
| **Lifecycle Manager** | Ordered startup/shutdown with graceful cleanup |
| **Secrets Manager** | Encrypted API key storage with rotation and audit logging |
| **CI/CD Pipeline** | GitHub Actions with lint, test, security scan, Docker build |

---

## Knowledge Academy Disciplines

| Discipline | Schools of Thought |
|-----------|-------------------|
| Epistemology | Empiricism, Rationalism, Constructivism, Pragmatism |
| Ethics | Utilitarianism, Deontology, Virtue Ethics, Care Ethics |
| Metaphysics | Materialism, Idealism, Dualism, Process Philosophy |
| Political Philosophy | Liberalism, Conservatism, Socialism, Anarchism, Libertarianism |
| Philosophy of Mind | Functionalism, Identity Theory, Eliminativism, Panpsychism |
| Philosophy of Science | Positivism, Falsificationism, Kuhnian Paradigms, Scientific Realism |
| Aesthetics | Formalism, Expressionism, Institutional Theory |
| Philosophy of Religion | Theism, Deism, Natural Theology, Philosophy of Atheism |
| Logic | Classical, Modal, Fuzzy, Non-monotonic |
| Philosophy of Language | Logical Atomism, Speech Act Theory, Structuralism |
| Existentialism | Sartrean, Kierkegaardian, Camusian Absurdism, Heideggerian |

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Python 3.10+ | Core language |
| FastAPI | Web framework (300+ endpoints) |
| Uvicorn | ASGI server |
| SQLAlchemy + Alembic | ORM and migrations |
| Redis | Caching, Pub/Sub, rate limiting |
| RQ | Background task queue |
| SQLite | Structured data storage |
| ChromaDB | Vector embeddings storage |

### AI / ML
| Technology | Purpose |
|-----------|---------|
| OpenAI GPT-4o | Primary language model |
| Claude / Gemini | Fallback models |
| text-embedding-3-small | Vector embeddings |
| LiveKit | WebRTC video conferencing |

### Frontend
| Technology | Purpose |
|-----------|---------|
| Vanilla JS | Core frontend (24 pages) |
| Tailwind CSS | Styling |
| Socket.io Client | Real-time messaging |
| WebRTC | Video conferencing |
| PWA | Installable app support |

### DevOps
| Technology | Purpose |
|-----------|---------|
| Docker + Docker Compose | Containerization |
| Nginx | Reverse proxy |
| GitHub Actions | CI/CD pipeline |
| Ruff + MyPy + Bandit | Linting and security |
| pytest + coverage | Testing |

### Third-Party APIs
| Service | Purpose |
|---------|---------|
| OpenAI API | AI chat and embeddings |
| Serper API | Web search |
| Stripe | Payments and billing |
| Twilio | WhatsApp and SMS |
| LiveKit | Video conferencing |

---

## Project Structure

```
omega-super-ai/
├── backend/                        # FastAPI backend (70+ modules)
│   ├── __init__.py                 # Package init, version 24.0.0
│   ├── router.py                   # Main FastAPI app with all endpoint imports
│   ├── middleware_enhanced.py      # Production middleware (v24.1)
│   ├── cache_manager.py            # Multi-tier caching (v24.1)
│   ├── background_tasks.py         # Async task queue (v24.1)
│   ├── health_system.py            # Health check probes (v24.1)
│   ├── config_validator.py         # Env config validation (v24.1)
│   ├── lifecycle_manager.py        # Startup/shutdown (v24.1)
│   ├── secrets_manager.py          # API key management (v24.1)
│   ├── chat.py                     # AI chat engine
│   ├── memory.py                   # ChromaDB vector memory
│   ├── financial.py                # Financial advisor
│   ├── search.py                   # Web search
│   ├── companion.py                # Companion/mentor
│   ├── v14_endpoints.py            # SaaS platform endpoints
│   ├── v15_endpoints.py            # ASI cognitive engine
│   ├── v16_endpoints.py            # Production features
│   ├── v17_endpoints.py            # Captainship & companionship
│   ├── v18_endpoints.py            # Automotive & writing
│   ├── law_studies.py              # Legal education system
│   ├── v19_endpoints.py            # Law studies endpoints
│   ├── agricultural_advisor.py     # Smart farming (Africa)
│   ├── healthcare_assistant.py     # Telemedicine (Africa)
│   ├── teacher_assistant.py        # Education support (Africa)
│   ├── business_advisor.py         # SME advisor (Africa)
│   ├── offline_engine.py           # Offline capability
│   ├── v20_endpoints.py            # Africa-first endpoints
│   ├── jobs_skills.py              # Jobs & skills advisor
│   ├── whatsapp_bot.py             # WhatsApp bot
│   ├── government_services.py      # Government services guide
│   ├── v21_endpoints.py            # Jobs, WhatsApp, government endpoints
│   ├── workspace_collab.py         # Workspace collaboration
│   ├── workspace_agent.py          # AI agent for workspaces
│   ├── v22_endpoints.py            # Workspace endpoints
│   ├── netai_training.py           # Network training curriculum
│   ├── netai_simulator.py          # Network device simulation
│   ├── v23_endpoints.py            # Network training endpoints
│   ├── knowledge_academy.py        # Knowledge graph (11 disciplines)
│   ├── project_management.py       # PM training system
│   ├── digital_workspace.py        # Digital workspace training
│   ├── v24_endpoints.py            # Knowledge academy endpoints
│   └── [50+ more modules...]
├── collab-service/                 # TypeScript collaboration microservice
│   ├── src/
│   │   ├── index.ts                # Socket.io + Redis + LiveKit
│   │   ├── health.ts               # Health checks
│   │   └── [10 more files...]
│   ├── Dockerfile
│   └── package.json
├── web/                            # Frontend (24 pages)
│   ├── index.html                  # Main SPA with all pages
│   ├── styles.css                  # Tailwind + custom styles
│   ├── app.js                      # Frontend logic
│   ├── manifest.json               # PWA manifest
│   ├── sw.js                       # Service worker
│   └── icons/                      # App icons
├── .github/workflows/ci.yml        # CI/CD pipeline
├── docker-compose.yml              # Multi-service orchestration
├── Dockerfile                      # Backend container
├── nginx.conf                      # Reverse proxy config
├── pyproject.toml                  # Project config + tool settings
├── Makefile                        # Development commands
├── .gitignore                      # Comprehensive ignore rules
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── start-all.sh                    # Startup script
└── README.md                       # This file
```

---

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (starts with `sk-`) |

### AI Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `OMEGA_MODEL` | `gpt-4o-mini` | Default chat model |
| `OMEGA_VISION_MODEL` | `gpt-4o` | Vision-capable model |
| `OMEGA_EMBED_MODEL` | `text-embedding-3-small` | Embedding model |
| `MAX_TOKENS` | `4096` | Maximum response tokens |
| `TEMPERATURE` | `0.7` | Model creativity (0.0-2.0) |

### Server
| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `ALLOWED_HOSTS` | `*` | Allowed host headers |

### Database & Storage
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/luqi.db` | Database connection |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB directory |
| `UPLOAD_DIR` | `./uploads` | File upload directory |
| `MAX_UPLOAD_SIZE` | `52428800` | Max upload size (50MB) |

### Redis (optional, enables caching & tasks)
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `` | Redis connection URL |

### External APIs (optional)
| Variable | Description |
|----------|-------------|
| `SERPER_API_KEY` | Serper.dev web search API |
| `STRIPE_SECRET_KEY` | Stripe payments (`sk_test_*` or `sk_live_*`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification |
| `TWILIO_ACCOUNT_SID` | Twilio account (`AC*`) |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Twilio phone number |
| `LIVEKIT_API_KEY` | LiveKit video API key |
| `LIVEKIT_API_SECRET` | LiveKit video API secret |
| `LIVEKIT_URL` | LiveKit server URL |

### Security
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (auto) | JWT signing key (required in production) |
| `JWT_EXPIRY_HOURS` | `24` | JWT token lifetime |
| `RATE_LIMIT_GENERAL` | `100` | General API rate limit (req/min) |
| `RATE_LIMIT_AUTH` | `10` | Auth endpoint rate limit (req/min) |

### Feature Flags
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WORKSPACE_COLLAB` | `true` | Enable workspace collaboration |
| `ENABLE_NETAI_TRAINING` | `true` | Enable network training |
| `ENABLE_KNOWLEDGE_ACADEMY` | `true` | Enable knowledge academy |
| `ENABLE_WHATSAPP_BOT` | `true` | Enable WhatsApp bot |
| `ENABLE_GOV_SERVICES` | `true` | Enable government services |

---

## API Endpoints

### Core (v13)
- `POST /api/chat` — AI chat
- `POST /api/chat/stream` — Streaming chat (SSE)
- `POST /api/upload` — File upload and analysis
- `POST /api/search` — Web search
- `POST /api/image/generate` — Image generation
- `POST /api/memory/save` — Save to memory
- `POST /api/memory/search` — Search memory
- `GET /api/health` — Health check
- `GET /api/health/detailed` — Detailed health diagnostics
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc documentation

### SaaS (v14)
- `POST /api/subscriptions/create` — Create subscription
- `GET /api/subscriptions/status` — Subscription status
- `POST /api/developer/keys` — Generate API key
- `GET /api/developer/usage` — Usage analytics
- `POST /api/website/build` — Build website

### ASI (v15)
- `POST /api/cognitive/reason` — Autonomous reasoning
- `GET /api/education/curriculum` — Get curriculum
- `POST /api/voice/synthesize` — Text-to-speech

### Law (v19)
- `GET /api/law/studies` — Law study modules
- `POST /api/law/analyze` — Legal document analysis
- `GET /api/law/jurisdictions` — Supported jurisdictions

### Africa-First (v20)
- `GET /api/agriculture/advise` — Farming advice
- `GET /api/healthcare/assist` — Health guidance
- `GET /api/education/assist` — Teaching support
- `GET /api/business/advise` — Business advice
- `GET /api/offline/status` — Offline capability status

### Jobs & Skills (v21)
- `POST /api/jobs/cv-build` — Build CV
- `POST /api/jobs/interview` — Interview questions
- `POST /api/jobs/assess` — Skills assessment
- `GET /api/jobs/market` — Job market overview
- `POST /api/jobs/career-plan` — Career planning
- `POST /api/jobs/freelance` — Freelance guide
- `POST /api/jobs/coverletter` — Cover letter generator
- `POST /api/jobs/salary-guide` — Salary guide

### WhatsApp (v21)
- `POST /api/whatsapp/webhook` — Webhook handler
- `POST /api/whatsapp/send` — Send message
- `GET /api/whatsapp/sessions` — List sessions
- `GET /api/whatsapp/session/{phone}` — Get session
- `DELETE /api/whatsapp/session/{phone}` — Delete session

### Government (v21)
- `GET /api/government/id-guide` — ID application guide
- `GET /api/government/business-reg` — Business registration
- `GET /api/government/tax-guide` — Tax guide
- `GET /api/government/voting` — Voting information
- `GET /api/government/passport` — Passport guide
- `GET /api/government/land` — Land transaction guide
- `GET /api/government/social-services` — Social services
- `POST /api/government/document-checklist` — Document checklist
- `GET /api/government/agencies` — Find government agencies

### Workspace (v22)
- `POST /api/workspaces` — Create workspace
- `GET /api/workspaces` — List workspaces
- `GET /api/workspaces/{id}` — Get workspace
- `POST /api/workspaces/{id}/messages` — Send message
- `GET /api/workspaces/{id}/messages` — Get messages
- `POST /api/workspaces/{id}/files` — Upload file
- `GET /api/workspaces/{id}/files` — List files
- `POST /api/video/token` — Get video token (LiveKit)
- `GET /api/workspaces/{id}/presence` — Get presence

### Network Training (v23)
- `GET /api/netai/curriculum` — Get curriculum
- `GET /api/netai/modules/{id}` — Get module
- `POST /api/netai/labs/{id}/start` — Start lab
- `GET /api/netai/labs/{id}/status` — Lab status
- `POST /api/netai/labs/{id}/submit` — Submit lab
- `POST /api/netai/topology/generate` — Generate topology
- `POST /api/netai/scenario/inject` — Inject scenario
- `POST /api/netai/grade` — Grade submission
- `POST /api/netai/telemetry` — Get telemetry
- `GET /api/netai/quiz/{id}` — Get quiz
- `POST /api/netai/quiz/{id}/submit` — Submit quiz
- `GET /api/netai/progress` — Get progress
- `GET /api/netai/leaderboard` — Get leaderboard
- `GET /api/netai/certificate/{student_id}` — Get certificate

### Knowledge Academy (v24)
- `GET /api/academy/disciplines` — List disciplines
- `GET /api/academy/disciplines/{id}` — Get discipline
- `GET /api/academy/schools` — List schools
- `GET /api/academy/schools/{id}` — Get school details
- `POST /api/academy/debate` — Start debate
- `POST /api/academy/explain` — ELI5 explanation
- `GET /api/academy/compare` — Compare schools
- `POST /api/academy/quiz` — Take quiz
- `GET /api/academy/progress` — Get progress

### Project Management (v24)
- `GET /api/pm/methodologies` — List methodologies
- `GET /api/pm/templates` — List templates
- `POST /api/pm/gantt` — Generate Gantt chart
- `POST /api/pm/sprint/simulate` — Simulate sprint
- `GET /api/pm/pmp/exam` — Get PMP exam
- `POST /api/pm/pmp/submit` — Submit PMP exam

### Digital Workspace (v24)
- `GET /api/dw/tools` — List tools
- `GET /api/dw/tools/{id}` — Tool guide
- `GET /api/dw/productivity` — Productivity methods
- `POST /api/dw/phishing` — Phishing simulation
- `GET /api/dw/security` — Security training

---

## Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

Services: Redis, Backend API, Collaboration Service, Nginx

### VPS / Self-Hosted

```bash
# Install
make install

# Run with Gunicorn
make run

# Or with Uvicorn (dev)
make dev
```

### Cloud Platforms

**Railway / Render:**
```bash
# Connect GitHub repo, set environment variables, deploy
```

**AWS / GCP / Azure:**
```bash
# Build and push Docker image
make docker-build
docker tag luqi-ai:latest your-registry/luqi-ai:v24
docker push your-registry/luqi-ai:v24
# Deploy to container service with env vars
```

### SSL / HTTPS

Use Nginx reverse proxy with Let's Encrypt:
```nginx
# Included in nginx.conf
server {
    listen 443 ssl;
    server_name luqi-ai.com;
    ssl_certificate /etc/letsencrypt/live/luqi-ai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/luqi-ai.com/privkey.pem;
    location / {
        proxy_pass http://backend:8000;
    }
}
```

---

## Development Commands

```bash
make help           # Show all commands
make install        # Install production deps
make install-dev    # Install dev deps
make dev            # Run with hot reload
make lint           # Run linters
make lint-fix       # Fix linting issues
make format         # Format code
make test           # Run unit tests
make test-cov       # Run tests with coverage
make test-integration # Run integration tests
make docker-build   # Build Docker images
make docker-run     # Run with Docker
make clean          # Clean generated files
make version        # Show version
```

---

## Safety & Disclaimers

- **Financial Advice**: All financial guidance is educational only. Consult a licensed financial advisor.
- **Medical/Legal**: Domain expert outputs are informational and do not constitute professional advice.
- **Scam Detection**: Analysis is probabilistic. Always verify independently.
- **AI Generated Content**: Responses may occasionally contain errors. Verify critical information.

---

## License

MIT License. Use, modify, and distribute freely.

See [LICENSE](LICENSE) for full terms.

---

<p align="center">
  <strong>Luqi AI v24.0.0</strong> — 115,000+ lines | 108 files | 300+ endpoints | 24 pages | 70+ modules
</p>

<p align="center">
  Built with passion for Africa and the world.
</p>
