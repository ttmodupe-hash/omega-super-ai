# Luqi AI v13

**World-class AI for Africa and the world.** 85 languages, virtual science labs, self-improving engine, multi-agent orchestration.

---

## Quick Start

```bash
# 1. Clone and enter
# (already done)

# 2. Install dependencies
py -3.11 -m pip install -r requirements.txt

# 3. Configure API key
$env:OPENAI_API_KEY="sk-your-key-here"
# Or: copy .env.example .env  (and edit)

# 4. Start server
py -3.11 start_server.py

# 5. Open http://localhost:8000
```

---

## What's New in v13

- **85 Languages** — 54 African + 31 global with greeting detection, cultural context, and multilingual routing
- **Virtual Science Labs** — 24 interactive simulations across 6 subjects (Physics, Chemistry, Biology, Math, Earth Science, CS)
- **Prometheus Prime** — Self-improving engine that monitors AI landscape and evolves capabilities
- **Multi-Agent Orchestration** — Plan → Research → Analyze → Synthesize pipeline
- **CLI Client** — Terminal chat with streaming, colors, and command shortcuts (`cli.py`)
- **Docker Deployment** — Dockerfile + docker-compose.yml for containerized hosting
- **Self-Test Diagnostics** — `self_test.py` checks your environment before starting
- **Export Endpoints** — Export conversations as JSON, text, or Markdown

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Chat** | Streaming chat with GPT-4o, 9 specialized modes |
| **Deep Research** | Multi-source web research with synthesis |
| **85 Languages** | African + global language detection and cultural context |
| **Virtual Labs** | Interactive science simulations for schools |
| **Financial Data** | Stock quotes, crypto prices, forex rates |
| **Tax Information** | Tax data for African and global countries |
| **Scam Detection** | Fraud pattern analysis and protection tips |
| **Image Generation** | DALL-E 3 image creation |
| **File Upload** | PDF, DOCX, and image analysis |
| **Vector Memory** | Persistent ChromaDB semantic search |
| **Prometheus** | Self-improving AI engine |
| **REST API** | 20+ FastAPI endpoints with auto docs |
| **CLI Client** | Terminal interface with streaming |
| **Docker Ready** | One-command container deployment |

---

## Architecture

```
User (Browser / CLI / API)
       |
       v
+------------------+     +------------------+
|  FastAPI Server  |---->|  OpenAI GPT-4o   |
|  (Python 3.11+)  |     |  (Chat + Vision) |
+--------+---------+     +------------------+
         |
         +-----> ChromaDB (Vector Memory)
         |
         +-----> SQLite (Structured Data)
         |
         +-----> Serper API (Web Search)
         |
         +-----> Language System (85 langs)
         |
         +-----> Virtual Labs (24 sims)
         |
         +-----> Prometheus (Self-improve)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 SPA (CDN), Tailwind CSS |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| AI Engine | OpenAI GPT-4o / GPT-4o-mini / DALL-E 3 |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB |
| Structured DB | SQLite |
| Search | Serper API + DuckDuckGo fallback |
| File Parsing | PyPDF2, python-docx, Pillow |
| Language | Custom 5-strategy detection engine |
| Deployment | Docker, docker-compose |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Chat (JSON response) |
| `POST` | `/api/chat/stream` | Streaming chat (SSE) |
| `POST` | `/api/search` | Web search |
| `POST` | `/api/upload` | File upload |
| `POST` | `/api/file/ask` | Ask about uploaded file |
| `POST` | `/api/image/generate` | Generate image (DALL-E 3) |
| `GET`  | `/api/memory/{sid}` | Conversation history |
| `POST` | `/api/memory/search` | Semantic memory search |
| `GET`  | `/api/finance/stock/{s}` | Stock quote |
| `GET`  | `/api/finance/crypto/{s}` | Crypto price |
| `GET`  | `/api/finance/forex` | Forex rate |
| `GET`  | `/api/finance/markets` | Market summary |
| `GET`  | `/api/taxes/{country}` | Tax information |
| `GET`  | `/api/opportunities` | Business opportunities |
| `GET`  | `/api/languages` | List all 85 languages |
| `POST` | `/api/languages/detect` | Detect language |
| `GET`  | `/api/languages/{code}` | Language details |
| `GET`  | `/api/labs` | List virtual labs |
| `GET`  | `/api/labs/{lab_id}` | Lab simulation details |
| `GET`  | `/api/prometheus/status` | Prometheus status |
| `POST` | `/api/prometheus/run` | Trigger improvement cycle |
| `GET`  | `/api/export/conversation/{sid}` | Export conversation |
| `GET`  | `/api/export/sessions` | Export all sessions |
| `GET`  | `/api/health` | Health check |
| `GET`  | `/api/models` | Available models & modes |
| `GET`  | `/docs` | Interactive API docs (Swagger) |

---

## CLI Client

The terminal chat client (`cli.py`) provides a rich command-line interface:

```bash
py -3.11 cli.py                    # Interactive mode
py -3.11 cli.py "Hello"            # Single query
py -3.11 cli.py /research "AI in Africa"
py -3.11 cli.py /finance AAPL
py -3.11 cli.py --server http://luqi-ai.com
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `/r, /research <query>` | Deep research with sources |
| `/f, /finance <symbol>` | Stock/crypto quote |
| `/t, /tax <country>` | Tax information |
| `/o, /opps` | Business opportunities |
| `/s, /scam <text>` | Scam detection |
| `/think <question>` | Multi-step reasoning |
| `/m, /mentor <topic>` | Learning mentor |
| `/x, /expert <question>` | Expert consultant |
| `/l, /learn <topic>` | Educational mode |
| `key <api_key>` | Set API key |
| `clear` | Clear screen |
| `exit, quit` | Exit |

---

## Self-Test Diagnostics

Run before starting to verify your environment:

```bash
py -3.11 self_test.py
```

Checks: Python version, dependencies, API key, directory structure, backend imports, router endpoints, web UI files, server connectivity.

---

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Project Structure

```
omega-super-ai/
 start_server.py          # Server launcher
 cli.py                   # Terminal chat client
 self_test.py             # Startup diagnostics
 server.py                # Uvicorn entry point
 omega.py                 # Legacy CLI
 Dockerfile               # Container build
 docker-compose.yml       # Full stack orchestration
 requirements.txt         # Python dependencies
 .env.example             # Environment template
 README.md                # This file
 DEPLOY.md                # Deployment guide
 backend/
   router.py              # FastAPI app with all endpoints
   chat.py                # Chat engine
   memory.py              # Vector memory
   search.py              # Web search
   financial.py           # Stock/crypto/forex
   taxes.py               # Tax information
   auth.py                # API key auth
   config.py              # Configuration
   models.py              # Pydantic models
   lang/                  # 85-language system
     african_languages.py
     language_detector.py
     greeting_handler.py
     multilingual_router.py
   prometheus/            # Self-improvement engine
 web/
   index.html             # React 18 SPA (main UI)
   labs/                  # Virtual labs UI
   icons/                 # App icons
 docs/                    # Documentation
 data/                    # Persistent data
 uploads/                 # File uploads
 memory/                  # Vector DB storage
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `SERPER_API_KEY` | No | — | Serper.dev search API |
| `OMEGA_MODEL` | No | `gpt-4o-mini` | Default chat model |
| `OMEGA_VISION_MODEL` | No | `gpt-4o` | Vision model |
| `OMEGA_EMBED_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `OMEGA_DB_PATH` | No | `luqi_memory.db` | SQLite database |
| `CHROMA_PATH` | No | `./chroma_db` | ChromaDB directory |
| `UPLOAD_DIR` | No | `./uploads` | Upload directory |
| `OMEGA_DEBUG` | No | `false` | Debug mode |
| `CORS_ORIGINS` | No | `*` | Allowed origins |

---

## License

MIT License. Built with passion for Africa and the world.
