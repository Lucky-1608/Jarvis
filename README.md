<div align="center">

# 🌊 Jarvis OS

**A self-hosted autonomous AI assistant that runs 24/7 — and proves what it did.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kotlin](https://img.shields.io/badge/Android-Kotlin-3DDC84?style=flat-square&logo=android&logoColor=white)](https://kotlinlang.org)
[![Postgres](https://img.shields.io/badge/Database-PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![pgvector](https://img.shields.io/badge/Vector_DB-pgvector-FF6F00?style=flat-square)](https://github.com/pgvector/pgvector)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

<samp>

**$0 inference spend** · **~2s typical reply** · **5-provider failover** · **solo build**

</samp>

*Most AI assistants just talk; Jarvis acts and proves it. It operates not as a simple chatbot, but as a persistent, self-hosted digital secretary running continuously in the background. Driven by a resilient 5-provider LLM cascade, it manages your communications, routes critical alerts to your phone via native WhatsApp and Telegram bridges, and proactively filters out scams. Crucially, Jarvis features true autonomy—scheduling its own tasks and generating cryptographic Truth Seals to mathematically verify every real-world action it executes on your behalf.*

</div>

---

## 📖 Table of Contents
1. [Why this exists](#-why-this-exists)
2. [Core Architecture](#-core-architecture)
3. [Deep Dive: Capabilities & Features](#-deep-dive-capabilities--features)
   - [AI Router & Multi-Provider Cascade](#ai-router--multi-provider-cascade)
   - [Semantic Memory & Vector DB](#semantic-memory--vector-db)
   - [Verified Missions & Truth Seals](#verified-missions--truth-seals)
   - [Messaging & Voice Integrations](#messaging--voice-integrations)
4. [Prerequisites](#-prerequisites)
5. [Installation & Setup (Local)](#-installation--setup-local)
6. [Installation & Setup (Docker)](#-installation--setup-docker)
7. [Environment Configuration (`.env`)](#-environment-configuration-env)
8. [CLI Reference](#-cli-reference)
9. [Project Structure](#-project-structure)
10. [Development & AI Workflows](#-development--ai-workflows)
11. [License](#-license)

---

## ❓ Why this exists

Every AI assistant you can rent is **request–response**: it helps for three minutes when prompted,
then stops existing. Its memory of you belongs to the vendor. It has no hands. And you cannot audit
whether it actually did what it said.

Jarvis OS is the opposite of all four. It owns its data, runs on hardware you control, holds intentions
across days, acts through real devices — and every consequential action leaves a ground-truth record
that can be diffed against what it claimed.

Language models lie about their own actions — not maliciously, but because pattern-matching a plausible confirmation is easier than doing the work. Mine once reported *"Task scheduled successfully"* with no row in the database. Everything below is downstream of taking that seriously.

---

## 🏗️ Core Architecture

```
                            ┌──────────────────────────────────┐
                            │           CLOUD BRAIN            │
                            │    FastAPI · WebSocket :8000     │
                            │                                  │
   WhatsApp  ◄──Baileys───► │  router ───► 5-provider cascade  │ ◄──WS──► React UI /
   (loop-proof              │      │         opencode →        │          Dashboard
    secretary)              │      │         gemini →          │        
                            │      │         ollama →          │
   Telegram  ◄──Bot API───► │      │         groq → nvidia     │
                            │      │                           │ ◄──WS──► Device nodes
   Gmail  ◄────poll───────► │      │                           │      laptop ✓  phone ✓
   (+ Guardian scan)        │      │                           │      (AccessibilityService)
                            │  memory tree      scheduler      │
   Calendar ◄──OAuth──────► │  (episodic →                     │
                            │   summary)                       │
                            │                                  │
                            │  pgvector      [TOOL RESULTS]    │
                            │  semantic       truth seals      │
                            │  recall         (the lie detector│
                            └──────────────────────────────────┘
```

**One brain, multiple entry points**. A single `/ws` WebSocket carries chat, status, streamed UI state, and device-node registration.

---

## ✨ Capabilities

| Capability | How it works |
|---|---|
| **Messaging secretary** | Native WhatsApp (Baileys) and Telegram Bot. Implements rate limiting, 5s debounce. Echo-loop-proof by design. |
| **Verified missions** | A goal is decomposed into steps, each with an *objectively checkable* verification. It's done because evidence proved it. |
| **Automated Briefings** | Scheduled daemon performs periodic email analysis and pushes intelligent summaries directly to WhatsApp and Telegram via local bridge endpoints. |
| **Device hands** | Lightweight agents connect *outbound* from laptop and phone and register capabilities. The Android client drives arbitrary apps via a native Kotlin `AccessibilityService`. |
| **Guardian fraud shield** | Rule-first scam detection on inbound mail and messages. Warn-only — never auto-deletes, auto-replies, or clicks. |
| **Truth seals** | Every side-effecting tool call generates a cryptographic `seal_id` (currently stored in-memory). Claims are auditable against seals; when words and seals disagree, **seals win**. |
| **Vector memory** | Deep semantic recall on every message via `pgvector` or ChromaDB, allowing meaning-based retrieval across thousands of past interactions. |
| **GraphRAG** | Uses Graphify to understand codebase architecture and concept relationships contextually, not just textually. |

---

## 🔍 Deep Dive: Advanced Features

### AI Router & Multi-Provider Cascade
Jarvis never goes offline due to a single API failure. It uses a **5-tier provider failover cascade**:
1. **OpenCode** (Primary focus)
2. **Ollama Cloud** (Remote Llama/Minimax)
3. **Nvidia NIM** (High-performance fallback for heavy lifting)
4. **Groq** (Cloud fallback)
5. **Google Gemini** (Cloud fallback)
6. **Local Ollama** (Offline capability for absolute privacy)

### Semantic Memory & Vector DB
Jarvis remembers you across sessions using an advanced two-tier memory system:
- **Episodic Memory:** Short-term conversational context.
- **Semantic Vector Recall:** Powered by `pgvector` (PostgreSQL) or ChromaDB, utilizing local embeddings (`BAAI/bge-small-en-v1.5`) or Jina API to retrieve context from thousands of past interactions.

### Voice Integrations
- **Voice Capabilities:** Supports Wake-word, Push-to-Talk, and Continuous listening modes using Azure Cognitive Services (STT) and ElevenLabs (TTS).

---

## 🛠️ Prerequisites

Before you start, ensure you have the following installed on your machine:
- **Python:** version 3.11 or higher
- **Node.js:** version 18+ (for frontend and n8n)
- **Database:** PostgreSQL with the `pgvector` extension (or use Docker)
- **Package Manager:** `pip` and `npm`

---

## 🚀 Installation & Setup (Local)

**1. Clone the repository**
```bash
git clone https://github.com/your-username/Jarvis.git
cd Jarvis
```

**2. Setup Backend Environment**
Install dependencies and activate the virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[all]"
```
*(Optional: Omit `[all]` and use `[dev]`, `[voice]`, `[vision]`, or `[automation]` depending on required modules).*

**3. Initialize Database**
Make sure PostgreSQL is running, then run migrations (or initialization scripts):
```bash
python create_db.py
```

**4. Start the Backend Server and Bridges**
You can use the provided startup script which installs Node.js dependencies and starts the FastAPI backend:
```bash
bash startup.sh
```
Alternatively, you can manually start the backend using `jarvis serve --reload` and start the WhatsApp/Telegram bridges using `node index.js` inside `jarvis/whatsapp-bridge` and `jarvis/telegram-bridge`.

**5. Start the Frontend**
Open a new terminal window:
```bash
cd jarvis/frontend
npm install
npm run dev
```
The React frontend will be accessible via `http://localhost:5173`.

---



## ⚙️ Environment Configuration (`.env`)

Copy `.env.example` to `.env` and fill out your keys. Key sections include:

- **LLM Configuration:** `AI_PRIMARY_PROVIDER` and `AI_FALLBACK_PROVIDERS` control the cascade. You must supply API keys for your chosen providers (e.g., `OPENCODE_API_KEY`, `NVIDIA_API_KEY`).
- **Database:** `JARVIS_DATABASE_URL` for PostgreSQL (`postgresql+asyncpg://user:pass@host:5432/db`).
- **Integrations:** 
  - `WHATSAPP_OWNER_NUMBER` to link your personal number.
  - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_OWNER_ID` to restrict the bot to you.
  - `GOOGLE_CLIENT_ID`, `NOTION_CLIENT_ID`, `GITHUB_CLIENT_ID` for OAuth integrations.
- **Voice:** `AZURE_SPEECH_KEY` for STT and `ELEVENLABS_API_KEY` for high-quality TTS.

---

## 💻 CLI Reference

The `jarvis` CLI acts as your control center for managing the OS.

| Command | Description |
|---------|-------------|
| `jarvis serve` | Starts the API server (use `--reload` for development, `--host` and `--port` to configure) |
| `jarvis chat` | Starts an interactive, terminal-based chat session with Jarvis |
| `jarvis voice` | Starts voice assistant (`--mode` can be `push-to-talk`, `wake-word`, or `continuous`) |
| `jarvis status` | Displays system health, tool registration status, memory stats, and provider latency |
| `jarvis tools` | Lists all registered tools and their capabilities |

---

## 📂 Project Structure

```text
Jarvis/
├── jarvis/                     # 🐍 Core Python Backend
│   ├── analytics/              # Performance and telemetry
│   ├── automation/             # Automated tasks (e.g., Email Briefings) and desktop/browser scripts
│   ├── brain/                  # Core LLM processing and routing logic
│   ├── cli/                    # CLI command definitions
│   ├── database/               # SQLAlchemy models and migrations
│   ├── frontend/               # ⚛️ React/Vite Frontend
│   ├── integrations/           # Third-party service API wrappers
│   ├── memory/                 # Vector DB and episodic memory modules
│   ├── providers/              # API wrappers for LLMs (OpenCode, Nvidia, Gemini, etc.)
│   ├── server/                 # FastAPI configuration and endpoints
│   ├── tools/                  # Extensible tool functions the AI can execute
│   ├── voice/                  # Voice assistance components (TTS, STT, Wake-word)
│   ├── whatsapp-bridge/        # WhatsApp Baileys integration
│   └── telegram-bridge/        # Telegram Bot integration
├── data/                       # Local data storage (ChromaDB, local files)
├── docs/                       # Additional documentation
├── Dockerfile.backend          # Backend container specification
├── pyproject.toml              # Python project metadata and dependencies
└── README.md                   # This file
```

---

## 🤖 Development & AI Workflows

This project utilizes advanced AI swarm workflows (`claude-flow`) and code comprehension (`graphify`).

- **GraphRAG (`graphify-out/`)**: This repository contains a generated knowledge graph. Use `graphify query "..."` to quickly explore cross-file relationships or architecture details instead of using standard text searches.
- **Swarm Operations**: Use `ruflo` / `claude-flow` via the `.claude/` definitions for orchestrated multi-agent development tasks. See `CLAUDE.md` for our internal AI collaboration rules.
- **Adding Tools:** To add a new capability to Jarvis, create a new module in `jarvis/tools/` and register it using the internal decorator system. The AI will automatically discover and utilize it when appropriate.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
