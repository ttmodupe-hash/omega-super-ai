# Luqi AI v25.0.0 "Prometheus"

<p align="center">
  <img src="web/icons/icon-192x192.png" alt="Luqi AI Logo" width="120">
</p>

<p align="center">
  <strong>World-Class AI SaaS Platform — Now with Omega AI Prometheus Engines</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#v25-prometheus">v25 Prometheus</a> &bull;
  <a href="#api">API</a> &bull;
  <a href="#deployment">Deploy</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-25.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/endpoints-400%2B-green" alt="Endpoints">
  <img src="https://img.shields.io/badge/engines-20-orange" alt="Engines">
  <img src="https://img.shields.io/badge/modules-90%2B-purple" alt="Modules">
</p>

---

## What's New in v25 "Prometheus"

v25 merges the full **Omega AI v3.7.0 Prometheus** engine suite into Luqi AI's FastAPI backend, adding 50+ endpoints across 20 specialized modules:

| Engine | Description | Endpoints |
|--------|-------------|-----------|
| **Error Repair** | Self-healing with circuit breakers, retry logic, health monitoring | 3 |
| **Memory Manager** | 3-agent memory (Archivist, Curator, Steward) with user-consent cleanup | 7 |
| **Pedagogical Engine** | Socrates + Bjork + Bloom — Socratic tutoring, spaced repetition, Bloom's Taxonomy | 4 |
| **Wisdom Engine** | 17 traditions, 165+ proverbs and quotes | 2 |
| **Crypto Utils** | AES-256-GCM encryption, SHA-256/512, BLAKE2 hashing | 3 |
| **Rate Limiter** | Token bucket algorithm with status reporting | 1 |
| **Vector DB** | Semantic document search and storage | 2 |
| **Multi-Tenant** | Isolated tenant statistics | 1 |
| **Plugin Marketplace** | Plugin discovery and installation | 2 |
| **Realtime Prices** | Cryptocurrency and financial price feeds | 1 |
| **Metrics Exporter** | Prometheus-compatible system metrics | 1 |
| **Email Notifier** | SMTP email notifications | 1 |
| **Telegram Bot** | Telegram messaging integration | 1 |
| **PDF Generator** | Report generation from content | 1 |
| **Auto Backup** | System backup creation, restore, and listing | 3 |
| **Local LLM** | Ollama-based local language model querying | 2 |
| **Agent Mesh** | Distributed agent coordination and task management | 2 |
| **Blockchain Audit** | Tamper-proof audit logging | 1 |
| **Federated Learning** | Privacy-preserving distributed ML | 1 |
| **v25 Status** | Reports which Prometheus modules are loaded | 1 |

**Total: 50+ new endpoints under `/api/v25/*`**

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
| **3-Phase Curriculum** | CCNA -> CCNP -> CCIE progressive learning paths |
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

### v24.2 — Animated Practical Learning
| Feature | Description |
|---------|-------------|
| **Animated Learning** | Step-by-step animated practical learning system |

### v24.3 — Accessibility for Deaf Users
| Feature | Description |
|---------|-------------|
| **Sign Language** | Sign language video library, visual alerts, vibration patterns |

### v25 — Omega AI Prometheus Engines
| Feature | Description |
|---------|-------------|
| **Error Repair** | Self-healing engine with circuit breakers, retry decorators, health monitoring |
| **Memory Manager** | 3-agent memory management (Archivist, Curator, Steward) with user-consent cleanup |
| **Pedagogical Engine** | Tri-agent learning: Socratic method, Cognitive Ledger (spaced repetition), Bloom's Taxonomy |
| **Wisdom Engine** | 165+ proverbs/quotes from 17 global traditions |
| **Crypto Utils** | AES-256-GCM encryption, SHA-256/512, BLAKE2 hashing |
| **Rate Limiter** | Token bucket rate limiting |
| **Vector DB** | Semantic document search and storage |
| **Multi-Tenant** | Isolated tenant management |
| **Plugin Marketplace** | Plugin discovery and installation |
| **Realtime Prices** | Cryptocurrency/financial price feeds |
| **Metrics Exporter** | Prometheus-compatible metrics |
| **Email Notifier** | SMTP email notifications |
| **Telegram Bot** | Telegram messaging |
| **PDF Generator** | PDF report generation |
| **Auto Backup** | System backup/restore management |
| **Local LLM** | Ollama local LLM integration |
| **Agent Mesh** | Distributed agent coordination |
| **Blockchain Audit** | Tamper-proof audit logging |
| **Federated Learning** | Privacy-preserving distributed machine learning |

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Python 3.10+ | Core language |
| FastAPI | Web framework (400+ endpoints) |
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
| Ollama | Local LLM inference |

### Frontend
| Technology | Purpose |
|-----------|---------|
| Vanilla JS | Core frontend |
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

---

## Project Structure

```
omega-super-ai/
├── backend/                        # FastAPI backend (80+ modules)
│   ├── __init__.py                 # Package init, version 25.0.0
│   ├── router.py                   # Main FastAPI app with all endpoint imports
│   ├── v25_endpoints.py            # Omega AI Prometheus integration (50+ endpoints)
│   ├── middleware_enhanced.py      # Production middleware (v24.1)
│   ├── cache_manager.py            # Multi-tier caching (v24.1)
│   ├── health_system.py            # Health check probes (v24.1)
│   ├── [80+ more modules...]
│   ├── v14_endpoints.py            # SaaS platform endpoints
│   ├── v15_endpoints.py            # ASI cognitive engine
│   ├── ...
│   └── v25_endpoints.py            # Prometheus engine integration
│
├── web/                            # Frontend
│   ├── index.html                  # Main SPA
│   ├── admin.html                  # Admin dashboard
│   ├── wellness.html               # Digital wellness
│   ├── manifest.json               # PWA manifest
│   ├── sw.js                       # Service worker
│   └── icons/                      # App icons
│
├── collab-service/                 # TypeScript collaboration microservice
│   ├── src/
│   │   ├── index.ts                # Socket.io + Redis + LiveKit
│   │   └── [10 more files...]
│   ├── Dockerfile
│   └── package.json
│
├── Omega AI (root-level)           # Standalone Omega AI modules
│   ├── api_server.py               # HTTP API server (60+ endpoints)
│   ├── omega_ai.py                 # Main CLI entry point
│   ├── core_brain.py               # Central brain with intent routing
│   ├── error_repair.py             # Error Repair & Self-Healing Engine
│   ├── memory_manager.py           # 3-Agent Memory Management
│   ├── pedagogical_engine.py       # Tri-Agent Pedagogical Engine
│   ├── wisdom_engine.py            # Wisdom Engine (17 traditions)
│   ├── [40+ more modules...]
│
├── .github/workflows/ci.yml        # CI/CD pipeline
├── docker-compose.yml              # Multi-service orchestration
├── Dockerfile                      # Backend container
├── nginx.conf                      # Reverse proxy config
├── pyproject.toml                  # Project config
├── Makefile                        # Development commands
├── README.md                       # This file
└── LICENSE                         # MIT License
```

---

## v25 Prometheus API Endpoints

All v25 endpoints are prefixed with `/api/v25/`:

### Status
- `GET /api/v25/status` — Prometheus engine status (reports all 20 modules)

### Error Repair
- `GET /api/v25/error-repair/stats` — Error repair statistics
- `POST /api/v25/error-repair/heal` — Trigger self-healing for a module
- `POST /api/v25/error-repair/clear` — Clear error history

### Memory Manager
- `GET /api/v25/memory-manager/stats` — Memory manager statistics
- `GET /api/v25/memory-manager/entries` — List all memory entries
- `POST /api/v25/memory-manager/cleanup` — Propose memory cleanup
- `GET /api/v25/memory-manager/purge-proposals` — Get pending purge proposals
- `POST /api/v25/memory-manager/approve-purge` — Approve a purge proposal
- `POST /api/v25/memory-manager/reject-purge` — Reject a purge proposal
- `POST /api/v25/memory-manager/recover` — Recover a soft-deleted entry

### Pedagogical Engine
- `POST /api/v25/pedagogical/diagnostic` — Run diagnostic assessment
- `GET /api/v25/pedagogical/progress/{student_id}` — Get student progress
- `POST /api/v25/pedagogical/tutor` — Socratic tutoring session
- `POST /api/v25/pedagogical/assess-bloom` — Assess Bloom's Taxonomy level

### Wisdom Engine
- `GET /api/v25/wisdom` — Get a wisdom proverb (optional `?tradition=`)
- `GET /api/v25/wisdom/traditions` — List available traditions

### Crypto Utils
- `POST /api/v25/crypto/encrypt` — Encrypt with AES-256-GCM
- `POST /api/v25/crypto/decrypt` — Decrypt ciphertext
- `POST /api/v25/crypto/hash` — Hash data (SHA-256/512, BLAKE2)

### Infrastructure
- `GET /api/v25/rate-limit/status` — Rate limiter status
- `POST /api/v25/vector/search` — Semantic vector search
- `POST /api/v25/vector/store` — Store document in vector DB
- `GET /api/v25/tenant/stats` — Multi-tenant statistics
- `GET /api/v25/marketplace/plugins` — List marketplace plugins
- `POST /api/v25/marketplace/install` — Install a plugin
- `POST /api/v25/prices/realtime` — Get realtime prices
- `GET /api/v25/metrics` — Prometheus-compatible metrics
- `POST /api/v25/notify/email` — Send email notification
- `POST /api/v25/telegram/send` — Send Telegram message
- `POST /api/v25/pdf/generate` — Generate PDF report
- `POST /api/v25/backup/create` — Create system backup
- `POST /api/v25/backup/restore` — Restore from backup
- `GET /api/v25/backup/list` — List available backups
- `GET /api/v25/llm/status` — Local LLM status
- `POST /api/v25/llm/query` — Query local LLM
- `GET /api/v25/mesh/agents` — List mesh agents
- `GET /api/v25/mesh/tasks` — List mesh tasks
- `GET /api/v25/blockchain/audit` — Blockchain audit log
- `GET /api/v25/federated/status` — Federated learning status

---

## Known Issues

### Missing Files (Sandbox Lost)
The following files were lost when the sandbox environment was cleaned. They exist in the Git history and can be recovered from previous commits:

| File | Size | Description |
|------|------|-------------|
| `backend/whatsapp_bot.py` | 146 KB | WhatsApp Bot with 200+ FAQs, 10 languages |
| `backend/jobs_skills.py` | 197 KB | CV builder, interview prep, skills assessor |
| `backend/netai_training.py` | 244 KB | 3-phase Network/AI training curriculum |
| `backend/project_management.py` | 204 KB | 8 PM methodologies, 22 templates, PMP exam |
| `backend/digital_workspace.py` | 293 KB | 51 tool guides, phishing simulator |
| `backend/government_services.py` | 337 KB | Gov services for 50+ countries |

**Recovery:** These files exist in earlier Git commits. To recover:
```bash
git log --all --full-history -- "backend/whatsapp_bot.py"
git show <commit>:backend/whatsapp_bot.py > backend/whatsapp_bot.py
```

### Broken Files
| File | Status | Fix |
|------|--------|-----|
| `backend/physics_simulator.py` | 2 bytes (empty) | Fixed in v25 |
| `backend/safety_alignment.py` | 11 bytes (empty) | Fixed in v25 |

---

## Deployment

### Docker Compose (Recommended)
```bash
docker-compose up -d
```
Services: Redis, Backend API, Collaboration Service, Nginx

### VPS / Self-Hosted
```bash
make install && make run
```

### Cloud
```bash
# Build and push Docker image
make docker-build
docker tag luqi-ai:latest your-registry/luqi-ai:v25
docker push your-registry/luqi-ai:v25
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
| `TEMPERATURE` | `0.7` | Model creativity |

### Server
| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

### Security
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (auto) | JWT signing key |
| `JWT_EXPIRY_HOURS` | `24` | JWT token lifetime |
| `RATE_LIMIT_GENERAL` | `100` | General API rate limit (req/min) |

---

## Safety & Disclaimers

- **Financial Advice**: Educational only. Consult a licensed financial advisor.
- **Medical/Legal**: Informational only. Not professional advice.
- **Scam Detection**: Probabilistic. Always verify independently.
- **AI Generated Content**: May occasionally contain errors. Verify critical information.

---

## License

MIT License. See [LICENSE](LICENSE) for full terms.

---

<p align="center">
  <strong>Luqi AI v25.0.0 "Prometheus"</strong> — 400+ endpoints | 90+ modules | 20 AI engines | 25 versions
</p>

<p align="center">
  Built with passion for Africa and the world.
</p>
