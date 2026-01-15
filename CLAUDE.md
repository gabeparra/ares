# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARES is a local-first AI orchestration and control system. It acts as a gateway between clients (Telegram, Discord, web) and AI backends (Ollama for local inference, OpenRouter for cloud LLMs). All state, memory, and tools are owned by the backend—LLMs are treated as stateless reasoning engines.

## Development Commands

### Backend (Django)
```bash
source .venv/bin/activate
python3 manage.py runserver              # Dev server on :8000
python3 manage.py migrate                # Run migrations
python3 manage.py makemigrations api     # Create new migrations
ruff check .                             # Lint Python code
ruff format .                            # Format Python code
```

### Frontend (Vite + React)
```bash
npm run dev                              # Dev server on :3000 with HMR
npm run build                            # Build to web/dist/
```

### Service Management (Production)
```bash
./manage-services.sh                     # Interactive service manager
sudo systemctl restart ares-backend      # Restart Django/Gunicorn
sudo systemctl restart ares-frontend-dev # Restart Vite dev server
```

### Database
SQLite for development (db.sqlite3), PostgreSQL planned for production.

### Django Management Commands
```bash
python3 manage.py process_memories       # Process pending memory extractions
python3 manage.py revise_memories        # Revise extracted memories
python3 manage.py process_scheduled_tasks # Process calendar scheduled tasks
python3 manage.py run_discord_bot        # Run Discord bot
```

## Architecture

### Core Python Packages

- **`ares_project/`** - Django project settings and configuration
- **`ares_core/`** - Core orchestration logic
  - `orchestrator.py` - Central coordinator between frontend and LLMs, manages memory and routing
  - `llm_router.py` - Routes requests to OpenRouter (primary) or Ollama (fallback)
  - `prompt_assembler.py` - Single source of truth for prompt structure (identical prompts to all LLMs)
  - `config.py` - Configuration loading from environment
- **`ares_mind/`** - Memory and RAG systems
  - `memory_store.py` - Four-layer memory system (identity, factual, working, episodic)
  - `memory_extraction.py` - Extract memories from conversations
  - `rag.py` - ChromaDB-based semantic search over conversation history
- **`api/`** - Django REST API views and models

### Key Design Principle

**LLMs are stateless reasoning engines.** All memory, personality, and context live in the orchestrator. The `prompt_assembler.py` ensures identical prompts are sent to both local and cloud LLMs—any behavioral difference comes only from routing decisions, not prompt shape.

### Four-Layer Memory System (ares_mind/memory_store.py)

1. **Identity Memory** - Long-term, slow-changing (communication style, habits)
2. **Factual Memory** - Stable facts (timezone, location, projects)
3. **Working Memory** - Rebuilt each request (date/time, calendar, active task)
4. **Episodic Memory** - Recent conversational context (summarized)

### Frontend Structure (src/)

React + Vite with UnoCSS for styling, Auth0 for authentication, Zustand for state management.

- `App.jsx` - Main application with tabbed interface
- `components/` - Feature-organized components (chat, memory, calendar, agent, code, etc.)
- `services/api.js` - API client
- `services/auth.js` - Auth0 integration

### API Endpoints

All endpoints under `/api/v1/`. Key endpoint groups:
- `/api/v1/chat` - Main chat interface
- `/api/v1/memory/*` - Memory extraction and management
- `/api/v1/self-memory/*` - AI self-memory (identity)
- `/api/v1/user-memory/*` - User facts and preferences
- `/api/v1/calendar/*` - Google Calendar integration
- `/api/v1/ollama/*` - Local LLM management
- `/api/v1/rag/*` - RAG/semantic search
- `/api/v1/telegram/*`, `/api/v1/discord/*` - Bot integrations

### OpenRouter Service (openrouter-service/)

Separate Node.js/TypeScript service for OpenRouter SDK integration. Not typically run directly—the Django backend handles LLM routing.

## Environment Configuration

Copy `.env.example` to `.env`. Key variables:
- `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY` - Security (required in production)
- `AUTH0_*` - Authentication configuration
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` - Local LLM
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` - Cloud LLM fallback
- `TELEGRAM_BOT_TOKEN`, `DISCORD_*` - Bot integrations
- `GOOGLE_CALENDAR_*` - Calendar OAuth
- `ELEVENLABS_API_KEY`, `OPENAI_API_KEY` - TTS/STT

## Testing

```bash
pytest                                   # Run all tests
pytest tests/test_specific.py            # Run specific test file
pytest -k "test_name"                    # Run tests matching pattern
```

Test files are in the `tests/` directory.
