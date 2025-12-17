"""Global state management for the web server."""

from fastapi import WebSocket

from caption_ai.storage import Storage


# Global state
storage: Storage | None = None
llm_client = None
websocket_connections: list[WebSocket] = []
summary_callbacks: list[callable] = []
summarizer_running: bool = True  # Controls whether summarizer processes segments
summarizer_instance = None  # Reference to the summarizer instance
telegram_bot_instance = None  # Telegram bot instance
chatgpt_bridge_instance = None  # ChatGPT bridge instance
power_pet_door_client = None  # Power Pet Door client instance


def get_storage() -> Storage | None:
    """Get the storage instance."""
    return storage


def set_storage_instance(instance: Storage) -> None:
    """Set the storage instance."""
    global storage
    storage = instance


def get_llm_client():
    """Get the LLM client."""
    return llm_client


def set_llm_client_instance(client) -> None:
    """Set the LLM client instance."""
    global llm_client
    llm_client = client


def get_websocket_connections() -> list[WebSocket]:
    """Get all active WebSocket connections."""
    return websocket_connections


def get_summarizer_running() -> bool:
    """Get whether summarizer should be running."""
    return summarizer_running


def set_summarizer_running(value: bool) -> None:
    """Set whether summarizer should be running."""
    global summarizer_running
    summarizer_running = value


def get_summarizer_instance():
    """Get the summarizer instance."""
    return summarizer_instance


def set_summarizer_instance(instance) -> None:
    """Set the summarizer instance reference."""
    global summarizer_instance
    summarizer_instance = instance


def get_telegram_bot_instance():
    """Get the Telegram bot instance."""
    return telegram_bot_instance


def set_telegram_bot_instance(instance) -> None:
    """Set the Telegram bot instance."""
    global telegram_bot_instance
    telegram_bot_instance = instance


def get_chatgpt_bridge_instance():
    """Get the ChatGPT bridge instance."""
    return chatgpt_bridge_instance


def set_chatgpt_bridge_instance(instance) -> None:
    """Set the ChatGPT bridge instance."""
    global chatgpt_bridge_instance
    chatgpt_bridge_instance = instance


def get_power_pet_door_client():
    """Get the Power Pet Door client instance."""
    return power_pet_door_client


def set_power_pet_door_client(client) -> None:
    """Set the Power Pet Door client instance."""
    global power_pet_door_client
    power_pet_door_client = client

