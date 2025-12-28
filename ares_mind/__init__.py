"""
ARES Mind - Memory and context management for ARES AI system.

This module provides:
- RAG store (semantic search over conversation history using ChromaDB)

Note: Context building functions for memory injection are in:
- api/memory_views.py::get_self_memory_context()
- api/user_memory_views.py::get_user_memory_context()
"""

from .rag import RAGStore, rag_store

__all__ = ["RAGStore", "rag_store"]
