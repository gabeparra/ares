"""Google Gemini API client."""

from caption_ai.config import config
from caption_ai.llm.base import LLMClient, LLMReply


class GeminiClient(LLMClient):
    """Gemini API client implementation."""

    def __init__(self) -> None:
        """Initialize Gemini client."""
        if not config.gemini_api_key:
            raise ValueError("Gemini API key not configured")

    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete prompt using Gemini API."""
        # TODO: Implement Gemini API call
        return LLMReply(
            content="[Gemini] Summary generation not yet implemented",
            model="gemini-pro",
        )

