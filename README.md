# ARES

**Local-first AI orchestration system** - A personal AI assistant that runs on your hardware, with cloud fallback when needed.

Built with Django, React, and modern AI infrastructure. Supports multiple LLM backends, persistent memory, and multi-platform clients.

---

## Architecture

```
Clients (Telegram / Discord / Web)
              ↓
      ARES Gateway (Django)
   Auth • Routing • Memory • RAG
         ↓           ↓
    Local LLM    Cloud LLM
    (Ollama)    (OpenRouter)
```

All clients connect through a unified API. The gateway handles authentication, intelligent routing, and memory injection - LLM backends are treated as stateless reasoning engines.

---

## Key Features

### LLM Integration
- **Multi-backend routing** - OpenRouter (100+ models) with Ollama fallback
- **Unified API** - Single `/api/v1/chat` endpoint abstracts backend complexity
- **Model configuration** - Temperature, context window, and parameters per-request

### Memory System
- **Four-layer memory architecture:**
  - Identity (AI self-knowledge, capabilities)
  - Factual (user preferences, stable facts)
  - Working (rebuilt per-request: time, calendar, active context)
  - Episodic (conversation summaries)
- **RAG integration** - ChromaDB for semantic search over conversation history
- **Automatic extraction** - Background processing extracts memories from conversations

### Client Integrations
- **Telegram bot** - Full chat with session management
- **Discord bot** - Server integration with mentions and DMs
- **Web dashboard** - React UI with real-time chat, memory management, settings

### Additional Services
- **Google Calendar** - OAuth integration, event sync, scheduled tasks
- **TTS/STT** - ElevenLabs voice synthesis, OpenAI Whisper transcription
- **Code indexing** - Codebase memory and semantic search

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django + Django REST Framework |
| Frontend | Vite + React + UnoCSS |
| Auth | Auth0 (OIDC + MFA) |
| Local LLM | Ollama |
| Cloud LLM | OpenRouter |
| Vector DB | ChromaDB |
| Database | SQLite (dev) / PostgreSQL (prod) |

---

## Security

- **Auth0 OIDC** with MFA for human access
- **API keys** for service-to-service auth
- **Role-based access control** with admin-only system endpoints
- **Field encryption** for sensitive data
- **Audit logging** on all requests

---

## Project Structure

```
ares/
├── api/                 # Django REST API
├── ares_core/           # Orchestrator, LLM routing, prompt assembly
├── ares_mind/           # Memory store, RAG, extraction
├── src/                 # React frontend
├── scripts/             # Service management, setup utilities
├── tests/               # Test suite
└── config/              # Nginx, Docker configs
```

---

## Why Local-First?

Modern AI tools centralize compute and data in the cloud. ARES explores the opposite:

> **Your AI, your hardware, your rules.**

Run models locally by default. Fall back to cloud when needed. Keep full ownership of your data and conversations.

---

## License

MIT
