# Nexus — Universal AI Chat Platform

**Nexus** is an open-source, privacy-first, universal AI chat platform that unifies multiple Large Language Models (LLMs) into a single, modern interface. Instead of switching between different AI services, Nexus allows you to connect cloud-based LLM providers and local models through **Ollama**, giving you complete freedom to choose the AI that best fits your workflow.

Designed for developers, researchers, students, and AI enthusiasts, Nexus aims to become a complete AI workspace where every model, provider, and AI tool can be accessed from one platform.

> 🚧 **Project Status:** Active Development (v1.0 Preview)
>
> Nexus is currently under active development. Version **1.0** is an early preview release focused on establishing the core architecture and multi-provider AI integration. Features, APIs, and the user interface may change as development progresses.

---

## ✨ Features (Currently Implemented)

### Core Chat & Multi-Provider
- 🌐 **Connect multiple LLM providers** from one application
- 🤖 **Support for local AI models** using **Ollama** (manual `ollama serve` required)
- ⚡ **Fast, responsive chat interface** with streaming responses
- 🔄 **Switch between AI providers instantly** mid-conversation
- 💬 **Streaming AI responses** with real-time tokens

### Document Processing
- 📂 **Upload and chat with documents** (PDF, DOCX, XLSX, PPTX, CSV, code, text, and more)
- 🔍 **Full-text extraction** from all supported formats
- ⚠️ **Current limitation:** Documents are concatenated into the prompt context (no RAG/vector search yet — large documents may exceed context windows)

### Settings & Configuration
- 🔑 **Runtime API key management** — add/remove provider keys in Settings → Providers without restarting the server
- 📝 **Persistent conversation history** with date-bucketed sidebar
- 🎨 **Theme system** (dark/light/system) with 6 accent color options
- 🛡️ **Privacy-focused local architecture** (single-user, password-hashed auth)

### Technical Foundation
- ⚙️ **REST API** powered by FastAPI with auto-generated Swagger docs
- 🧪 **GitHub Actions CI** support
- 📚 **Extensible Skills system** — parameterized prompt templates with dependency resolution and auto-suggest
- 🔐 **Local authentication** (scrypt hashing, Bearer tokens, HTTP-only cookies, CSRF protection)

---

## 🤖 Supported AI Providers

| Provider | ID | Type | API Key Required | LiteLLM Prefix |
|----------|-----|------|------------------|----------------|
| Anthropic | `anthropic` | Cloud | Yes | `anthropic/` |
| OpenAI | `openai` | Cloud | Yes | `openai/` |
| NVIDIA NIM | `nvidia` | Cloud | Yes | `nvidia_nim/` |
| Together AI | `together` | Cloud | Yes | (none) |
| Groq | `groq` | Cloud | Yes | (none) |
| OpenRouter | `openrouter` | Cloud | Yes | (none) |
| DeepSeek | `deepseek` | Cloud | Yes | `deepseek/` |
| Mistral AI | `mistral` | Cloud | Yes | (none) |
| Gemini | `gemini` | Cloud | Yes | `gemini/` |
| Ollama | `ollama` | Local | No | `ollama/` |

> **Note:** Additional providers can be added by extending the provider registry in `backend/providers/__init__.py`.

---

## 🚀 Quick Start

### Windows (Recommended)

**Option 1:** Double-click `run.bat` (easiest)
- Opens a command window that stays visible
- Shows server logs in real-time
- Press Ctrl+C to stop

**Option 2:** Run from Command Prompt
```powershell
cd "D:\chat apps\Universal-Ai-Chat-Platform--main"
run.bat
```

**Option 3:** Run start.py directly (window stays open)
```powershell
cd "D:\chat apps\Universal-Ai-Chat-Platform--main"
python start.py
```

### Linux / macOS
```bash
./start.sh
```

### Manual Start (Advanced)
```bash
# Backend (API Server)
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001

# Frontend (Web Server) - in a separate terminal
cd frontend
python -m http.server 5500
```

The launcher automatically:
1. Creates a Python virtual environment (`venv/`)
2. Installs dependencies from `requirements.txt` (with SHA-256 caching)
3. Creates `.env` from `.env.example` if missing
4. Frees stale ports (8001 backend, 5500 frontend)
5. Starts both backend and frontend servers
6. Monitors both processes; Ctrl+C terminates both

### Default URLs

| Service | URL |
|---------|-----|
| Frontend | http://127.0.0.1:5500 |
| Backend API | http://127.0.0.1:8001 |
| API Documentation (Swagger) | http://127.0.0.1:8001/docs |
| Ollama (if installed) | http://localhost:11434 |

---

## ⚙️ Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Add only the providers you want to use:

```dotenv
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
NVIDIA_NIM_API_KEY=nvapi-...
GOOGLE_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
# ... etc
```

**API keys can also be managed directly inside the app:**

**Settings → Provider API Keys** — add, update, or remove keys without server restarts. Keys are encrypted at rest (Fernet/AES-128-GCM) and resolved at runtime (DB → `.env` fallback).

Models are automatically grouped and filtered according to available providers.

---

## 🦙 Ollama Support

Nexus automatically detects local Ollama installations.

```bash
ollama pull llama3.2
ollama serve
```

All downloaded models automatically appear inside the model selector.

To use another Ollama server, change in `.env`:
```dotenv
OLLAMA_BASE_URL=http://your-ollama-host:11434
```

> **Known limitation:** The "auto-start Ollama" feature is currently a stub — you must run `ollama serve` manually. See `backend/llm.py` `_try_start_ollama()`.

---

## 👤 Local Authentication

On first launch, Nexus asks you to create a local account.

Requirements:
- Username: minimum 3 characters
- Password: minimum 10 characters

No default credentials are provided. Passwords are hashed with **scrypt** (N=16384, r=8, p=1).

**Forgot credentials?** Use the included reset script:
```bash
python -m backend.reset_password testusr Reset@5fd19beb0f5b
```

---

## 📂 Supported Document Formats

| Format | Library | Extraction Method |
|--------|---------|-------------------|
| `.txt`, `.md` | — | Direct text read |
| `.json`, `.html`, `.xml` | — | Direct text read |
| `.py`, `.java`, `.js`, `.c`, ... | — | Direct text read (source code) |
| `.pdf` | pypdf | `PdfReader().pages` |
| `.docx` | python-docx | Paragraph text extraction |
| `.csv` | pandas | `read_csv()` → `to_string()` |
| `.xlsx` | openpyxl | Cell-by-cell iteration |
| `.pptx` | python-pptx | Slide + shape text extraction |

> **Important:** Currently, **full extracted text is concatenated into the prompt** (context stuffing). There is no chunking, embedding, or vector retrieval (RAG). Large documents may exceed model context windows.

---

## 🧪 Extensible Skills System

Nexus includes a **Skills** subsystem — parameterized prompt templates with dependency resolution and auto-suggest.

### Built-in Skills (v1.0)
| Skill | Category | Invocation | Description |
|-------|----------|------------|-------------|
| API Design Assistant | engineering | `both` | Design REST/GraphQL APIs |
| Coding Standards Review | engineering | `both` | Review code against style guides |
| Debugging Assistant | engineering | `both` | Systematic debugging workflow |
| Web Search Assistant | productivity | `auto` | Augment responses with live search |

Skills are defined as `SKILL.md` files in `config/skills/<skill-name>/` with YAML front matter.

### Skill Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/skills/` | GET | List all skills (filterable) |
| `/api/skills/categories` | GET | List categories |
| `/api/skills/{id}` | GET | Skill detail with params |
| `/api/skills/execute` | POST | Execute a skill |
| `/api/skills/chain` | POST | Chain multiple skills |
| `/api/skills/auto-suggest` | POST | Suggest skills from context |

---

## 🔍 Web Search Augmentation

Enable **Web Search** in the composer toolbar to augment responses with live results.

- **Default:** DuckDuckGo Lite (no API key required)
- **Optional upgrades:** Tavily, Brave (set `WEB_SEARCH_PROVIDER` + `WEB_SEARCH_API_KEY` in `.env`)

Search results are injected as a system message so the model can cite sources.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (port 5500)                          │
│  Vanilla JS SPA — feature modules: auth, chat, models, settings, skills │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ apiFetch() / streamChat()
┌────────────────────────────┴────────────────────────────────────────────┐
│                    BACKEND (port 8001)                                   │
│  FastAPI + SQLAlchemy + LiteLLM                                          │
│  ├── /api/auth/*     → auth.py (register, login, session, CSRF)         │
│  ├── /api/*          → api.py (chat, models, files, providers)          │
│  └── /api/skills/*   → skills/api_skills.py (skills CRUD + execute)     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────┴─────┐      ┌──────┴──────┐    ┌─────┴─────┐
    │ SQLite    │      │ Document    │    │ Web Search│
    │ (history/ │      │ Extraction  │    │(DuckDuckGo│
    │ nexus.db) │      │ (document.py)│    │ Tavily/   │
    │           │      │             │    │ Brave)    │
    └───────────┘      └─────────────┘    └───────────┘
```

---

## 🧪 Testing

```bash
# From project root (with venv activated)
venv\Scripts\python.exe -m unittest discover -s tests -v
```

Test coverage includes:
- Authentication (hashing, tokens, security properties)
- Document extraction (all formats, error handling, preview truncation)
- Schema validation
- Model discovery (live fetch, Ollama, fallback logic)
- Skill registry (SKILL.md loading, parameter validation)
- Streaming (SSE event formatting)
- Web search (parser, format_context, live search)

---

## 📋 Requirements

- Python 3.11+
- Ollama (optional, for local models)
- Git (for cloning)

**Key Python dependencies:** FastAPI 0.115, Uvicorn 0.34, LiteLLM 1.56, SQLAlchemy 2.0, Pydantic 2.11, cryptography, python-magic-bin.

See `requirements.txt` for complete list.

---

## 🔒 Security Considerations

Nexus v1.0 is a **local, single-user application**:
- Provider API keys added via Settings are **encrypted at rest** (Fernet with `MASTER_KEY` from `.env`)
- Local account passwords use **scrypt** (memory-hard KDF)
- Sessions use **Bearer tokens** + **HTTP-only cookies** with **CSRF double-submit protection**
- Debug mode is **OFF by default** (`APP_DEBUG=false`)

> ⚠️ **Do not expose this instance to the public internet** without:
> - Changing `ENV=production`
> - Setting strong `ALLOWED_ORIGINS`
> - Using a reverse proxy with TLS
> - Rotating `MASTER_KEY` periodically
> - Reviewing rate limits for your threat model

See `SECURITY.md` for vulnerability reporting.

---


### Development Setup
```bash
git clone https://github.com/your-org/nexus-chat.git
cd nexus-chat
cp .env.example .env
# Edit .env with your MASTER_KEY and any API keys
python start.py
```

### Code Style
- Python: `ruff` + `mypy` (config in `pyproject.toml`)
- JavaScript: ES modules, no build step
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)

---

## 📄 License

MIT License — see `LICENSE` for details.

---

## 🗺️ Roadmap (Post v1.0)

| Area | Planned |
|------|---------|
| **RAG / Vector Search** | Chunking, embeddings, hybrid retrieval for large documents |
| **Ollama Auto-Start** | Actually spawn `ollama serve` on demand |
| **Docker / Compose** | Production-ready containerization |
| **Multi-User Workspaces** | Teams, shared chats, role-based access |
| **Function Calling / Tools** | Model tool use with approval UI |
| **Vision Models** | Image upload + analysis |
| **MCP (Model Context Protocol)** | Standard tool integration |
| **Desktop Apps** | Tauri/Electron packaging |
| **Plugin Marketplace** | Community skills & providers |


---

**Built with ❤️ for the open-source AI community.**