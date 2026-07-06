# Luqi AI v12

<p align="center">
  <img src="web/icons/icon-192x192.png" alt="Luqi AI Logo" width="120">
</p>

<p align="center">
  <strong>Your Intelligent Assistant</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#api">API</a> &bull;
  <a href="#deployment">Deploy</a>
</p>

---

## Quick Start

Get Luqi AI running in three commands:

```bash
# 1. Install dependencies
py -3.11 -m pip install -r requirements.txt

# 2. Configure your API key
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start the server
py -3.11 start_server.py
```

Then open **http://localhost:8000** in your browser.

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Chat** | Conversational assistant powered by GPT-4o with streaming responses |
| **Deep Research** | Multi-angle web research with parallel search and synthesis |
| **Critical Thinking** | Chain-of-thought reasoning, bias detection, and fact verification |
| **Companion Mentor** | Personalized learning paths, goal coaching, and study guides |
| **Domain Experts** | 13+ professional domains: engineering, medical, legal, IT, finance, and more |
| **Financial Advisor** | Investment analysis, budget planning, and scam detection |
| **Scam Guard** | 15-pattern fraud detection with URL analysis and protection tips |
| **File Upload** | PDF, DOCX, and image analysis with extraction capabilities |
| **Vector Memory** | Persistent ChromaDB-based memory for conversations and context |
| **Web Search** | Live web search via Serper API with source citations |
| **PWA Support** | Install as a standalone app on desktop and mobile |
| **REST API** | Full-featured FastAPI backend with auto-generated docs |

---

## Architecture

```
User (Browser/CLI)
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
         +-----> File Uploads (PDF/DOCX/Images)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla JS, CSS3, PWA |
| Backend | FastAPI, Uvicorn |
| AI Engine | OpenAI GPT-4o / GPT-4o-mini |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB |
| Structured DB | SQLite |
| Search | Serper API (Google Search) |
| File Parsing | PyPDF2, python-docx, Pillow |

---

## API Documentation

Luqi AI exposes a REST API powered by FastAPI. Interactive docs are available at `/docs` when the server is running.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message to the AI |
| `POST` | `/api/chat/stream` | Stream a response (SSE) |
| `POST` | `/api/research` | Run deep research |
| `POST` | `/api/think` | Critical thinking analysis |
| `POST` | `/api/upload` | Upload a file for analysis |
| `GET`  | `/api/history` | Get conversation history |
| `POST` | `/api/clear` | Clear conversation history |
| `GET`  | `/api/health` | Health check |
| `GET`  | `/docs` | Interactive API docs (Swagger UI) |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Explain quantum computing in simple terms"}'
```

### Example: File Upload

```bash
curl -X POST http://localhost:8000/api/upload \\
  -F "file=@document.pdf"
```

---

## Installation Guide

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Step-by-Step

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/luqi-ai.git
   cd luqi-ai
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   py -3.11 -m venv .venv
   .venv\\Scripts\\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   py -3.11 -m pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=sk-your-openai-key-here
   SERPER_API_KEY=your-serper-key-here  # optional, for web search
   ```

5. **Start the server**
   ```bash
   py -3.11 start_server.py
   ```

6. **Open in browser**
   Navigate to `http://localhost:8000`

---

## Development Setup

### Running with Auto-Reload

```bash
py -3.11 start_server.py --reload
```

### Running on a Custom Port

```bash
py -3.11 start_server.py --port 8080
```

### Running with Custom Host

```bash
py -3.11 start_server.py --host 0.0.0.0 --port 8000
```

### Skip Dependency Check

```bash
py -3.11 start_server.py --skip-deps
```

### Running the CLI Version

Luqi AI also includes a terminal-based interface:

```bash
py -3.11 omega.py
```

---

## Deployment to GitHub Pages

### Frontend (Static Site)

1. Push the `web/` directory to a GitHub repository
2. Go to **Settings > Pages** in your repository
3. Select the branch containing the `web/` folder
4. Your site will be available at `https://yourusername.github.io/luqi-ai/`

### Backend (Self-Hosted)

For the full backend with AI capabilities, deploy the Python server:

**Option A: Self-hosted VPS**
```bash
# On your server
git clone https://github.com/yourusername/luqi-ai.git
cd luqi-ai
py -3.11 -m pip install -r requirements.txt
copy .env.example .env
# Edit .env with your API keys
py -3.11 start_server.py --host 0.0.0.0 --port 80
```

**Option B: Docker (coming soon)**
```bash
docker build -t luqi-ai .
docker run -p 8000:8000 --env-file .env luqi-ai
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `SERPER_API_KEY` | No | - | Serper.dev search API key |
| `OMEGA_MODEL` | No | `gpt-4o-mini` | Default chat model |
| `OMEGA_VISION_MODEL` | No | `gpt-4o` | Vision-capable model |
| `OMEGA_EMBED_MODEL` | No | `text-embedding-3-small` | Embedding model |
| `OMEGA_DB_PATH` | No | `luqi_memory.db` | SQLite database file |
| `CHROMA_PATH` | No | `./chroma_db` | ChromaDB directory |
| `UPLOAD_DIR` | No | `./uploads` | File upload directory |
| `OMEGA_DEBUG` | No | `false` | Enable debug mode |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |

---

## Project Structure

```
luqi-ai/
 start_server.py       # Server launcher (run this)
 omega.py              # CLI launcher
 requirements.txt      # Python dependencies
 .env.example          # Environment variable template
 README.md             # This file
 DEPLOY.md             # Deployment guide
 omega/
   __init__.py         # Package init
   config.py           # Configuration
   server.py           # FastAPI app
   database.py         # SQLite persistence
   memory.py           # ChromaDB vector memory
   utils.py            # Utility functions
   search_engines.py   # Web search
   content_extractor.py # Web content extraction
   research_swarm.py   # Multi-agent deep research
   critical_thinker.py # Reasoning engine
   companion.py        # Mentoring mode
   domain_experts.py   # Professional domains
   financial_advisor.py # Financial literacy
   scam_guard.py       # Fraud protection
 web/
   index.html          # Main UI
   styles.css          # Styles
   app.js              # Frontend logic
   manifest.json       # PWA manifest
   sw.js               # Service worker
   icons/              # App icons
```

---

## Screenshots

### Chat Interface
A modern, dark-themed chat UI with streaming responses, file upload, and conversation history.

### Deep Research
Multi-angle research with synthesized reports and source citations.

### File Analysis
Upload PDFs, Word documents, or images for AI-powered analysis and extraction.

### API Docs
Auto-generated Swagger UI documentation at `/docs`.

---

## Safety & Disclaimers

- **Financial Advice**: All financial guidance is educational only. Consult a licensed financial advisor for professional advice.
- **Medical/Legal**: Domain expert outputs are informational and do not constitute professional advice.
- **Scam Detection**: Analysis is probabilistic. Always verify independently and report fraud to authorities.
- **AI Generated Content**: Responses are generated by AI and may occasionally contain errors. Verify critical information.

---

## License

MIT License. Use, modify, and distribute freely.

See [LICENSE](LICENSE) for full terms.

---

<p align="center">
  Built with passion for intelligent assistance.
</p>
