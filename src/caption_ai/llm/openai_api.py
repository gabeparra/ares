"""OpenAI API client."""

import httpx

from caption_ai.config import config
from caption_ai.llm.base import LLMClient, LLMReply


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""

    def __init__(self) -> None:
        """Initialize OpenAI client."""
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")

    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete prompt using OpenAI API."""
        # TODO: Implement OpenAI API call
        return LLMReply(
            content="[OpenAI] Summary generation not yet implemented",
            model="gpt-4",
        )

