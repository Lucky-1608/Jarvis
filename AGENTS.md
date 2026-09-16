# Repository Guidelines

## Project Structure & Module Organization

- `jarvis/` contains the Python backend: `brain/` and `router/` coordinate AI requests, `providers/` wraps model APIs, `server/` exposes FastAPI routes, and `cli/` defines terminal commands.
- `tools/`, `plugins/`, and `automation/` implement capabilities; `memory/` and `database/` handle persistence.
- `jarvis/frontend/src/` contains React/TypeScript pages, components, hooks, and services. Frontend assets live in `public/` and `assets/`; `electron/` and `android/` contain desktop and mobile integrations.
- `jarvis/whatsapp-bridge/` and `jarvis/telegram-bridge/` are Node.js services. `docs/` holds documentation; `data/` holds local runtime data; `graphify-out/` contains generated architecture artifacts.

## Build, Test, and Development Commands

Use Python 3.11+ and an activated virtual environment. Run backend commands from the repository root:

- `pip install -e ".[dev]"`: install the backend and development tools.
- `jarvis serve --reload`: start the development API server.
- `ruff check jarvis/`: check Python style, imports, and common errors.
- `python -m pytest`: run Python tests when present.
- `docker build -f Dockerfile.backend -t jarvis-backend:test .`: build the backend container, matching CI.

From `jarvis/frontend/`:

- `npm ci`: install locked dependencies.
- `npm run dev`: start Vite.
- `npm run typecheck`: check TypeScript types.
- `npm run build`: type-check and create the production build.

## Coding Style & Naming Conventions

Use four-space Python indentation, type annotations, `snake_case` functions/modules, and `PascalCase` classes. Ruff targets Python 3.11 with a 100-character line limit. Match surrounding TypeScript formatting, typically two spaces; use `PascalCase` React components and `use...` hook names. Keep changes within the relevant module.

## Testing Guidelines

Pytest and pytest-asyncio are configured with automatic asyncio mode and `tests/` discovery, but no Python test suite currently exists. Add tests as `tests/test_<feature>.py`; mock external providers and messaging services. No coverage threshold is configured. The frontend has no test script; run type-check/build checks and manually verify affected screens. CI builds both applications but currently treats Ruff failures as nonblocking and does not run pytest.

## Commit & Pull Request Guidelines

Recent commits generally use `feat:`, `fix:`, and `chore:` prefixes. Write concise, action-oriented subjects. PRs should describe behavior changes, link relevant issues, list validation performed, and include screenshots for UI changes. Document configuration changes and remaining limitations.

## Security & Configuration

Copy `.env.example` to `.env` for local configuration. Never commit credentials, OAuth tokens, bridge sessions, or private runtime data. Update example configuration when adding environment variables.
