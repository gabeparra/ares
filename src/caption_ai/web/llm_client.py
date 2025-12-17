"""LLM client management."""

from caption_ai.config import config
from caption_ai.llm.router import get_llm_client as _get_llm_client_from_router
from caption_ai.web.state import set_llm_client_instance


def set_llm_client(client=None, model: str | None = None):
    """Set the LLM client for chat."""
    if client is None:
        client = _get_llm_client_from_router(config.llm_provider)
        # If it's a LocalOllamaClient and we have a model, set it
        if model and hasattr(client, 'set_model'):
            client.set_model(model)
        elif model and hasattr(client, '__class__'):
            # Recreate with new model if it's LocalOllamaClient
            from caption_ai.llm.local_ollama import LocalOllamaClient
            if isinstance(client, LocalOllamaClient):
                client = LocalOllamaClient(model=model)
    set_llm_client_instance(client)

