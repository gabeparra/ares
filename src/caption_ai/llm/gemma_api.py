"""GEMMA AI API client."""

import httpx

from caption_ai.config import config
from caption_ai.llm.base import LLMClient, LLMReply


class GemmaAIClient(LLMClient):
    """GEMMA AI API client implementation."""

    def __init__(self) -> None:
        """Initialize GEMMA AI client."""
        self.base_url = config.gemma_ai_api_url.rstrip("/")
        self.temperature = config.gemma_temperature
        self.max_length = config.gemma_max_length
        self.top_p = config.gemma_top_p

    def _build_prompt_with_history(self, prompt: str, conversation_history: list[dict] | None = None) -> str:
        """Build a prompt that includes conversation history."""
        if not conversation_history:
            return prompt

        # Build conversation context from history
        context_parts = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content") or msg.get("message", "")
            if content:
                role_label = "User" if role == "user" else "Assistant"
                context_parts.append(f"{role_label}: {content}")

        if context_parts:
            context = "\n".join(context_parts)
            return f"{context}\n\nUser: {prompt}\nAssistant:"
        
        return prompt

    async def complete(self, prompt: str, conversation_history: list[dict] | None = None) -> LLMReply:
        """Complete prompt using GEMMA AI API."""
        # Build prompt with conversation history if provided
        full_prompt = self._build_prompt_with_history(prompt, conversation_history)

        # Prepare request payload
        payload = {
            "prompt": full_prompt,
            "temperature": self.temperature,
            "max_length": self.max_length,
            "top_p": self.top_p,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                response_text = data.get("response", "")
                if not response_text:
                    return LLMReply(
                        content="Error: Empty response from GEMMA AI API",
                        model=data.get("model", "gemma"),
                    )

                return LLMReply(
                    content=response_text,
                    model=data.get("model", "gemma"),
                )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                return LLMReply(
                    content="Error: GEMMA AI model is still loading. Please try again in a moment.",
                    model="gemma",
                )
            error_msg = f"HTTP error {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass
            return LLMReply(
                content=f"Error calling GEMMA AI API: {error_msg}",
                model="gemma",
            )
        except httpx.TimeoutException:
            return LLMReply(
                content="Error: GEMMA AI API request timed out",
                model="gemma",
            )
        except Exception as e:
            return LLMReply(
                content=f"Error calling GEMMA AI API: {str(e)}",
                model="gemma",
            )

