"""Base LLM client interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMReply:
    """Response from LLM."""

    content: str
    model: str | None = None
    tokens_used: int | None = None


class LLMClient(ABC):
    """Base interface for LLM clients."""

    @abstractmethod
    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete a prompt and return response.
        
        Args:
            prompt: The user's message/prompt
            conversation_history: Optional list of previous messages in format:
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        pass

