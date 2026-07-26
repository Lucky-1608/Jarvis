# 🤖 Jarvis OS

> AI Operating System — Think. Remember. Plan. Execute. Automate.

Jarvis OS is a production-grade AI Operating System that can understand, plan, execute, learn, remember, and automate anything on your computer and cloud. Built with Python, FastAPI, ChromaDB, and multi-provider AI routing.

## ⚡ Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install Jarvis OS
pip install -e ".[dev]"
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# At minimum, set your OPENCODE_API_KEY
```

### 3. Run

```bash
# Interactive chat mode
jarvis chat

# Start the API server
jarvis serve

# Check system health
jarvis status

# List available tools
jarvis tools

# Start voice assistant
jarvis voice                    # Push-to-talk mode
jarvis voice --mode wake-word   # Say "Jarvis" to activate
jarvis voice --mode continuous  # Always listening
```

## 🏗️ Architecture

```
Input → Intent Analysis → AI Router → Planner → Executor →
Verification → Memory Update → Response
```

### Core Modules

| Module | Description |
|--------|-------------|
| **Brain** | Central orchestrator — ties everything together |
| **AI Router** | Selects best AI provider with automatic fallback |
| **Memory** | Multi-tier memory with ChromaDB vector search |
| **Planner** | Breaks complex tasks into executable steps |
| **Executor** | Runs tools and collects results |
| **Verifier** | Validates every action before completion |
| **Tools** | Extensible capability system (23 built-in) |
| **Voice** | Wake word, STT (faster-whisper), TTS (Edge-TTS) |
| **Vision** | Screenshot capture + AI-powered screen analysis |
| **Automation**| Browser (Playwright) & Desktop (PyAutoGUI) control |
| **Plugins** | SDK for third-party extensions |
| **Events** | Async pub/sub for inter-module communication |

### AI Providers

| Provider | Type | Use Case |
|----------|------|----------|
| **OpenCode** | Cloud (Primary) | Complex reasoning, coding |
| **Ollama** | Local (Fallback) | Free, offline, privacy-first |
| **OpenRouter** | Cloud | 200+ models, advanced tasks |

## 🛠️ Built-in Tools

| Tool | Category | Description |
|------|----------|-------------|
| `system_info` | System | CPU, RAM, disk, OS info |
| `open_app` | System | Launch desktop applications |
| `run_command` | System | Execute shell commands |
| `list_files` | File | List directory contents |
| `read_file` | File | Read text files |
| `write_file` | File | Create/write files |
| `search_files` | File | Search files by pattern |
| `get_datetime` | System | Current date/time |
| `web_search` | Web | Search via DuckDuckGo |
| `fetch_url` | Web | Fetch URL content |

## 📡 API Endpoints

Start the server with `jarvis serve`, then visit `http://localhost:8000/docs` for full API docs.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message, get response |
| WS | `/api/chat/stream` | Streaming chat |
| GET | `/api/memory/search` | Search memories |
| POST | `/api/memory` | Store a memory |
| GET | `/api/memory/stats` | Memory statistics |
| GET | `/api/tools` | List tools |
| POST | `/api/tools/execute` | Execute a tool |
| GET | `/api/health` | System health check |

## 📁 Project Structure

```
jarvis/
├── brain/              # Core orchestrator
│   └── jarvis_brain.py
├── router/             # AI model routing
│   └── ai_router.py
├── providers/          # AI provider implementations
│   ├── base.py         # Abstract interface
│   ├── opencode.py     # OpenCode (primary)
│   ├── ollama.py       # Ollama (local)
│   └── openrouter.py   # OpenRouter (cloud)
├── memory/             # Memory system
│   ├── memory_manager.py
│   ├── embeddings.py
│   └── context_manager.py
├── planner/            # Task decomposition
│   └── planner.py
├── executor/           # Plan execution
│   └── executor.py
├── verification/       # Result verification
│   └── verifier.py
├── tools/              # Tool system
│   ├── base.py
│   ├── registry.py
│   └── builtin/
│       ├── system_tools.py
│       └── web_tools.py
├── events/             # Event bus
│   └── bus.py
├── plugins/            # Plugin SDK
│   └── sdk.py
├── server/             # FastAPI backend
│   ├── app.py
│   └── routes/
│       ├── chat.py
│       ├── memory.py
│       ├── tools.py
│       └── health.py
├── cli/                # Terminal interface
│   └── cli.py
└── config/             # Settings
    └── settings.py
```

## 🔮 Roadmap

- **Phase 2**: Voice (Whisper STT, Edge-TTS) & Vision (NVIDIA NIM)
- **Phase 3**: Automation (Playwright, PyAutoGUI, desktop control)
- **Phase 4**: Knowledge Graph, RAG pipeline, preference learning
- **Phase 5**: Plugin ecosystem, background agents
- **Phase 6**: Iron Man HUD (Three.js dashboard)
- **Phase 7**: Multi-agent team collaboration
- **Phase 8**: Docker, CI/CD, auth, security audit

## 📄 License

MIT
