"""Configuration management with environment variable loading."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Config(BaseSettings):
    """Application configuration."""

    # LLM Provider selection
    llm_provider: Literal["openai", "grok", "gemini", "local", "gemma"] = Field(
        default="local",
        description="LLM provider to use",
    )

    # Storage
    storage_path: Path = Field(
        default=Path.home() / ".caption_ai" / "segments.db",
        description="Path to SQLite database",
    )

    # OpenAI
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")

    # Grok
    grok_api_key: str | None = Field(default=None, description="Grok API key")

    # Gemini
    gemini_api_key: str | None = Field(default=None, description="Gemini API key")

    # GEMMA AI API (External API service)
    gemma_ai_api_url: str = Field(
        default="http://localhost:8000",
        description="GEMMA AI API base URL (e.g., http://192.168.1.100:8000)",
    )
    gemma_temperature: float = Field(
        default=0.7,
        description="Temperature for GEMMA AI (0.0-2.0, default: 0.7)",
    )
    gemma_max_length: int = Field(
        default=512,
        description="Maximum tokens to generate for GEMMA AI (default: 512)",
    )
    gemma_top_p: float = Field(
        default=0.9,
        description="Top-p sampling for GEMMA AI (default: 0.9)",
    )

    # Local Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama base URL",
    )
    ollama_model: str = Field(
        default="llama2",
        description="Ollama model name",
    )
    ollama_uncensored: bool = Field(
        default=True,
        description="Enable uncensored mode (adds system prompt to bypass restrictions)",
    )
    ollama_temperature: float = Field(
        default=0.9,
        description="Temperature for Ollama (higher = more creative/random)",
    )
    ollama_top_p: float = Field(
        default=0.95,
        description="Top-p sampling for Ollama",
    )
    ollama_top_k: int | None = Field(
        default=None,
        description="Top-k sampling for Ollama (None = disabled)",
    )
    ollama_min_p: float | None = Field(
        default=None,
        description="Min-p sampling for Ollama (None = disabled). Typical values: 0.0 to 0.1",
    )
    ollama_repeat_last_n: int | None = Field(
        default=256,
        description="Repetition window for Ollama (how many last tokens are penalized). None = disabled.",
    )
    ollama_repeat_penalty: float | None = Field(
        default=1.15,
        description="Repetition penalty for Ollama (>= 1.0). None = disabled.",
    )
    ollama_num_ctx: int | None = Field(
        default=None,
        description="Context window size for Ollama (num_ctx). None = model default.",
    )
    ollama_num_predict: int | None = Field(
        default=4096,
        description="Maximum number of tokens to predict (None = no limit)",
    )

    # Telegram/Apprise notifications
    apprise_url: str | None = Field(
        default=None,
        description="Apprise URL for Telegram notifications (e.g., tgram://bot_token/chat_id)",
    )
    notify: bool = Field(
        default=False,
        description="Enable Telegram notifications",
    )
    
    # Telegram Bot (for receiving messages)
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram bot token for receiving messages",
    )
    telegram_allowed_chat_ids: str | None = Field(
        default=None,
        description="Comma-separated Telegram chat IDs allowed for outbound sends. If unset, outbound send is disabled.",
    )
    telegram_contacts: str | None = Field(
        default=None,
        description="Comma-separated Telegram contact aliases, like: alice=123,bob=-100123 (group). Used for @alice mention sending.",
    )
    telegram_webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for Telegram bot (e.g., https://yourdomain.com/api/telegram/webhook)",
    )
    
    # ChatGPT Web Integration (WARNING: May violate OpenAI ToS)
    chatgpt_enabled: bool = Field(
        default=False,
        description="Enable ChatGPT web scraping integration (use at your own risk)",
    )
    chatgpt_email: str | None = Field(
        default=None,
        description="ChatGPT login email",
    )
    chatgpt_password: str | None = Field(
        default=None,
        description="ChatGPT login password",
    )
    chatgpt_headless: bool = Field(
        default=True,
        description="Run ChatGPT browser in headless mode",
    )
    chatgpt_session_id: str | None = Field(
        default=None,
        description="Default session ID for ChatGPT conversations",
    )
    
    # Power Pet Door / Home Assistant
    home_assistant_url: str | None = Field(
        default=None,
        description="Home Assistant URL (e.g., http://homeassistant.local:8123)",
    )
    home_assistant_token: str | None = Field(
        default=None,
        description="Home Assistant long-lived access token",
    )
    power_pet_door_entity_prefix: str = Field(
        default="power_pet_door",
        description="Entity prefix for Power Pet Door entities in Home Assistant",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


config = Config()

