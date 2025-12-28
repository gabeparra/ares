"""
ARES Core Configuration

Environment variables for ARES components.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# OpenRouter configuration (primary LLM provider)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Local Ollama configuration (fallback)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

# ChromaDB configuration (for RAG)
CHROMADB_PATH = os.environ.get("CHROMADB_PATH", str(DATA_DIR / "chromadb"))

# Memory database
MEMORY_DB_PATH = os.environ.get("MEMORY_DB_PATH", str(DATA_DIR / "memory.db"))

# Server configuration
ENGRAM_PORT = int(os.environ.get("ENGRAM_PORT", "60006"))
ENGRAM_HOST = os.environ.get("ENGRAM_HOST", "0.0.0.0")

