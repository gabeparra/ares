"""
LLM Router - Routes requests to OpenRouter (primary) or Ollama (fallback).

OpenRouter provides access to Claude, GPT-4, and other models through a single API.
Local Ollama serves as a fallback when OpenRouter is unavailable.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import httpx

from .config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_BASE_URL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None


class LLMRouter:
    """
    Routes LLM requests to OpenRouter (primary) or Ollama (fallback).
    
    Usage:
        router = LLMRouter()
        response = router.chat([{"role": "user", "content": "Hello"}])
    """
    
    def __init__(self):
        self.openrouter_available = bool(OPENROUTER_API_KEY)
        self.ollama_available = bool(OLLAMA_BASE_URL)
        self._client = httpx.Client(timeout=120.0)
    
    def chat(
        self,
        messages: List[Dict],
        prefer_local: bool = False,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send chat request to LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            prefer_local: If True, try Ollama first
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with content, provider, and model info
        """
        # Try local Ollama first if preferred
        if prefer_local and self.ollama_available:
            try:
                result = self._call_ollama(messages, model, temperature)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Ollama failed, falling back to OpenRouter: {e}")
        
        # Use OpenRouter (primary)
        if self.openrouter_available:
            try:
                return self._call_openrouter(messages, model, temperature, max_tokens)
            except Exception as e:
                logger.error(f"OpenRouter failed: {e}")
                if self.ollama_available:
                    logger.info("Falling back to Ollama")
                    return self._call_ollama(messages, model, temperature)
                raise
        
        # Fallback to Ollama if OpenRouter not configured
        if self.ollama_available:
            return self._call_ollama(messages, model, temperature)
        
        raise RuntimeError("No LLM provider available. Configure OPENROUTER_API_KEY or OLLAMA_BASE_URL.")
    
    def _call_openrouter(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call OpenRouter API."""
        used_model = model or OPENROUTER_MODEL
        
        payload = {
            "model": used_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        response = self._client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "ARES",
                "HTTP-Referer": "https://aresai.space",
            },
            json=payload,
        )
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")
        
        return LLMResponse(
            content=content,
            provider="openrouter",
            model=used_model,
            tokens_used=tokens,
        )
    
    def _call_ollama(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Call local Ollama API."""
        used_model = model or OLLAMA_MODEL
        
        response = self._client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": used_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            },
        )
        response.raise_for_status()
        
        data = response.json()
        content = data["message"]["content"]
        
        return LLMResponse(
            content=content,
            provider="ollama",
            model=used_model,
        )
    
    def get_status(self) -> Dict:
        """Get status of all LLM providers."""
        status = {
            "openrouter": {
                "configured": self.openrouter_available,
                "model": OPENROUTER_MODEL if self.openrouter_available else None,
            },
            "ollama": {
                "configured": self.ollama_available,
                "model": OLLAMA_MODEL if self.ollama_available else None,
            },
        }
        
        # Check OpenRouter connectivity
        if self.openrouter_available:
            try:
                resp = self._client.get(
                    f"{OPENROUTER_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                    timeout=5.0,
                )
                status["openrouter"]["status"] = "online" if resp.status_code == 200 else "error"
            except Exception:
                status["openrouter"]["status"] = "offline"
        
        # Check Ollama connectivity
        if self.ollama_available:
            try:
                resp = self._client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
                status["ollama"]["status"] = "online" if resp.status_code == 200 else "error"
            except Exception:
                status["ollama"]["status"] = "offline"
        
        return status
    
    def list_openrouter_models(self) -> List[Dict]:
        """List available OpenRouter models."""
        if not self.openrouter_available:
            return []
        
        try:
            response = self._client.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to list OpenRouter models: {e}")
            return []


# Singleton instance
llm_router = LLMRouter()

