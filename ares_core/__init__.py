"""
ARES Core - Infrastructure components for ARES AI system.

This module provides:
- LLM routing (OpenRouter primary, Ollama fallback)
- Configuration management
"""

from .llm_router import LLMRouter, llm_router

__all__ = ["LLMRouter", "llm_router"]

