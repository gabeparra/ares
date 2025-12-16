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
Clients (Telegram / Discord / Web)
                ↓
        ARES Gateway (Django)
   Auth • Routing • Memory • Logs
        ↓        ↓        ↓
   Local LLM   Cloud LLM   External APIs
   (Ollama)    (vLLM)     (OpenAI / Grok)
        ↓
   System Tools (Agent Zero, OS control)
```

All clients communicate **only** with the ARES Gateway.
Inference backends and system tools are never exposed directly.

---

## Features (Current + Planned)

### Implemented / In Progress

* Unified `/v1/chat` API
* Local LLM inference (Ollama)
* Telegram integration
* Web dashboard (Vite + React)
* Auth0 authentication (MFA)
* API keys for bots
* Request logging

### Planned

* Discord bot
* Cloud GPU fallback (vLLM)
* External LLM escalation (ChatGPT / Grok)
* OS-level control (Wake-on-LAN, reboot, next-boot selection)
* Agent Zero integration (proposal → approval → execution)
* Conversation memory + summaries
* Retrieval-augmented generation (docs, notes, optional news)

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

## MVP Scope (Hard Line)

ARES is considered **MVP-complete** when:

* Local LLM works via `/v1/chat`
* Telegram and web dashboard both function
* Auth0 + API key auth enforced
* Local ↔ external LLM routing works
* Wake / shutdown / next-boot commands work with approval
* Logs record every request and routing decision

Everything else is **post-MVP**.

---

## Technology Stack

* **Backend:** Django + Django REST Framework
* **Frontend:** Vite + React
* **Auth:** Auth0 (OIDC, MFA)
* **Local LLM:** Ollama
* **Cloud LLM (planned):** vLLM
* **Bots:** Telegram Bot API, Discord.js
* **OS Control:** GRUB, Wake-on-LAN, Agent Zero
* **Database:** SQLite (dev), Postgres (planned)

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

## License

MIT (subject to change)
