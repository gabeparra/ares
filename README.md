# ARES

**ARES** is a **local-first AI orchestration and control system** designed to act as a powerful personal assistant while keeping ownership of compute, data, and decisions in the user’s hands.

ARES prioritizes **running on your own hardware**, falls back to cloud or external LLMs only when needed, and exposes all capabilities through a **secure, authenticated control plane**.

> Inspired by early power-user software of the 2000s and modern AI infrastructure principles.

---

## What ARES Is (and Is Not)

**ARES is:**

* A **gateway** between clients (Telegram, Discord, web) and AI backends
* A **router** for local models, cloud GPUs, and external LLM APIs
* A **secure control plane** for system-level actions
* A long-term personal assistant that improves via tooling and memory

**ARES is not:**

* A simple chatbot
* A wrapper around a single AI API
* An autonomous agent with unrestricted system access

---

## Core Principles

* **Local-first**
  Run models on your own GPU by default.

* **Explicit control**
  No hidden autonomy. Sensitive actions require approval.

* **Fail gracefully**
  Local → cloud → external LLM fallback.

* **Security by design**
  MFA, scoped permissions, audit logs.

* **Modular architecture**
  Swap inference engines without touching clients.

---

## High-Level Architecture

```
Clients (Telegram / Web / Discord*)
                ↓
        ARES Gateway (Django)
   Auth • Routing • Memory • Logs
        ↓        ↓        ↓
   Local LLM   External LLM   Additional Services
   (Ollama)    (OpenRouter)   (Calendar, TTS, STT, SD)
   (fallback)  (Claude, GPT-4, etc.)
        ↓
   System Tools (Agent control, OS control*)
   
* Discord and OS control features are planned
```

All clients communicate **only** with the ARES Gateway.
Inference backends and system tools are never exposed directly.

---

## Features

### Core Infrastructure

* Unified `/api/v1/chat` API
* LLM routing (OpenRouter primary, Ollama fallback)
* Auth0 authentication (OIDC + MFA)
* Web dashboard (Vite + React)
* Request logging and audit trails

### LLM Integration

* Local LLM inference (Ollama)
* External LLM via OpenRouter (Claude, GPT-4, and 100+ models)
* Automatic fallback routing (OpenRouter → Ollama)
* Model selection and configuration

### Client Integrations

* Telegram bot integration
* Web dashboard with real-time chat
* Account linking system

### Memory & Context

* AI self-memory system (identity, milestones, observations)
* User memory (facts, preferences)
* Memory extraction from conversations
* Conversation summaries
* Retrieval-augmented generation (RAG) with ChromaDB
* Code indexing and codebase memory
* Memory revision and auto-apply system

### Additional Features

* Google Calendar integration (OAuth, event sync, scheduled tasks)
* Text-to-Speech (ElevenLabs)
* Speech-to-Text (OpenAI Whisper)
* Agent control (4090 rig management)
* Stable Diffusion API integration
* Image upscaling
* Training data export
* Ollama management API
* Code browser and revision system

### Planned Features

* Discord bot integration
* Cloud GPU fallback (vLLM) - alternative to OpenRouter
* OS-level control (Wake-on-LAN, reboot, next-boot selection)
* Agent Zero integration (proposal → approval → execution)

---

## Security Model

ARES separates **human control** from **service automation**.

### Authentication

* **Auth0 (OIDC + MFA)** for human access
* **API keys** for bots and services

### Authorization

* Role- and scope-based access
* Admin-only endpoints for system actions
* Explicit approval required for dangerous operations

### Safety

* No direct model access to system tools
* No autonomous execution
* Full audit logging

---

## MVP Status

ARES MVP milestones:

* ✅ Local LLM works via `/api/v1/chat`
* ✅ Telegram and web dashboard both function
* ✅ Auth0 + API key auth enforced
* ✅ Local ↔ external LLM routing works (OpenRouter + Ollama)
* ✅ Logs record every request and routing decision
* ⏳ Wake / shutdown / next-boot commands (partial - service restart exists)

**Status:** MVP core features are complete. The project has moved well beyond MVP with extensive memory, RAG, and integration features.

---

## Technology Stack

* **Backend:** Django + Django REST Framework
* **Frontend:** Vite + React
* **Auth:** Auth0 (OIDC, MFA)
* **Local LLM:** Ollama
* **External LLM:** OpenRouter (Claude, GPT-4, and 100+ models)
* **RAG:** ChromaDB
* **TTS:** ElevenLabs
* **STT:** OpenAI Whisper
* **Calendar:** Google Calendar API
* **Bots:** Telegram Bot API
* **Database:** SQLite (dev), Postgres (planned)
* **OS Control (planned):** GRUB, Wake-on-LAN, Agent Zero

---

## Project Status

This repository is the **canonical implementation** of ARES.

A previous experimental prototype is archived here:

* [https://github.com/gabeparra/AiListener](https://github.com/gabeparra/AiListener)

---

## Motivation

Modern AI tools increasingly centralize compute and decision-making in the cloud.
ARES explores the opposite approach:

> **What if your AI worked for you, on your machine, under your rules?**

---

## Documentation

All documentation is organized in the [`internaldocuments/`](internaldocuments/) folder.

### Quick Start
* **[Setup Guide](internaldocuments/SETUP.md)** - Installation and setup
* **[Docker Guide](internaldocuments/docker/DOCKER.md)** - Container deployment (reference)
* **[Documentation Index](internaldocuments/INDEX.md)** - Complete documentation guide

### Security & Deployment
* **[Deployment Status](internaldocuments/security/DEPLOYMENT_STATUS_AND_NEXT_STEPS.md)** - Current status and next steps
* [`internaldocuments/security/`](internaldocuments/security/) - Security audit, fixes, and guides

### Features
* [Google Calendar Integration](internaldocuments/GOOGLE_CALENDAR_SETUP.md)
* [Memory System](internaldocuments/MEMORY_EXTRACTION.md)
* [Code Memory](internaldocuments/CODE_MEMORY_SYSTEM.md)
* [Authentication Testing](internaldocuments/TEST_AUTH.md)

For a complete list, see **[internaldocuments/INDEX.md](internaldocuments/INDEX.md)**

---

## License

MIT (subject to change)
