"""Grok API client."""

from caption_ai.config import config
from caption_ai.llm.base import LLMClient, LLMReply


class GrokClient(LLMClient):
    """Grok API client implementation."""

    def __init__(self) -> None:
        """Initialize Grok client."""
        if not config.grok_api_key:
            raise ValueError("Grok API key not configured")

    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete prompt using Grok API."""
        # TODO: Implement Grok API call
        return LLMReply(
            content="[Grok] Summary generation not yet implemented",
            model="grok-beta",
        )

