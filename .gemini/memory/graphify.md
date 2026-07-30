# Graphify — Knowledge Graph for Codebases

## Overview
**Graphify** turns any codebase (including docs, SQL schemas, configs, PDFs, images, videos) into a queryable knowledge graph. It's an AI coding assistant skill (slash command `/graphify`) that works with Claude Code, Cursor, Codex, Gemini CLI, GitHub Copilot, and 15+ more platforms.

- **GitHub**: https://github.com/Graphify-Labs/graphify
- **Website**: https://graphify.com (waitlist for always-on background service)
- **PyPI Package**: `graphifyy` (double-y — the CLI command is still `graphify`)
- **License**: Apache-2.0 / MIT dual-licensed
- **Stars**: ~98.3k ⭐
- **Language**: Python

## Key Features
- **Local & Deterministic**: Code is parsed with **tree-sitter AST** — no LLM, nothing leaves your machine (docs/PDFs/images use your assistant's model or a configured API key)
- **Every Edge Explained**: Connections tagged as `EXTRACTED` (explicit in source) or `INFERRED` (resolved by graphify)
- **Not a Vector Index**: Real graph you traverse — no embeddings, no vector store
- **Edge types**: `calls`, `imports`, `inherits`, `mixes_in`, and more

## Installation
```bash
# Step 1 — Install the CLI
uv tool install graphifyy          # recommended
# or: pipx install graphifyy
# or: pip install graphifyy

# Step 2 — Register skill with AI assistant
graphify install                   # global (user profile)
graphify install --project         # project-scoped
graphify install --project --platform codex  # specific platform
```

## Usage
```bash
# In your AI assistant
/graphify .

# CLI commands
graphify explain "APIRouter"       # Explain a node
graphify path "FastAPI" "ModelField"  # Trace connection path
graphify query "<question>"        # Query with plain language
```

## Output Files
```
graphify-out/
├── graph.html          # Interactive browser visualization
├── GRAPH_REPORT.md     # Key concepts, connections, suggested questions
└── graph.json          # Full graph for querying without re-reading files
```

## Why Remember This
- Useful for understanding complex codebases quickly
- Can map the Jarvis project into a navigable knowledge graph
- Helps AI assistants reason about code relationships
- Pairs well with multi-agent workflows (ruflo) for codebase analysis
