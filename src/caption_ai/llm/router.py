"""LLM client router."""

from typing import Literal

from caption_ai.config import config
from caption_ai.llm.base import LLMClient
from caption_ai.llm.local_ollama import LocalOllamaClient
from caption_ai.llm.openai_api import OpenAIClient
from caption_ai.llm.gemini_api import GeminiClient
from caption_ai.llm.grok_api import GrokClient
from caption_ai.llm.gemma_api import GemmaAIClient


def get_llm_client(provider: Literal["openai", "grok", "gemini", "local", "gemma"]) -> LLMClient:
    """Get LLM client for specified provider."""
    if provider == "openai":
        return OpenAIClient()
    elif provider == "grok":
        return GrokClient()
    elif provider == "gemini":
        return GeminiClient()
    elif provider == "local":
        return LocalOllamaClient()
    elif provider == "gemma":
        return GemmaAIClient()
    else:
        raise ValueError(f"Unknown provider: {provider}")

