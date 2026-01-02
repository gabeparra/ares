"""
ARES Mind - Memory and context management for ARES AI system.

This module provides:
- RAG store (semantic search over conversation history using ChromaDB)
- Memory extraction from conversations using OpenRouter AI
- Automated hourly memory revision process

Note: Context building functions for memory injection are in:
- api/memory_views.py::get_self_memory_context()
- api/user_memory_views.py::get_user_memory_context()
"""

from .rag import RAGStore, rag_store
from .memory_extraction import (
    extract_memories_from_conversation,
    revise_memories_hourly,
    apply_memory_spot,
    auto_apply_high_confidence_memories,
)

__all__ = [
    "RAGStore",
    "rag_store",
    "extract_memories_from_conversation",
    "revise_memories_hourly",
    "apply_memory_spot",
    "auto_apply_high_confidence_memories",
]
