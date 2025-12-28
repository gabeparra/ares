from .models import AppSetting, ChatSession


def _get_setting(key: str, default: str | None = None) -> str | None:
    row = AppSetting.objects.filter(key=key).only("value").first()
    return row.value if row else default


def _set_setting(key: str, value: str) -> None:
    AppSetting.objects.update_or_create(key=key, defaults={"value": value})


def _ensure_session(session_id: str) -> ChatSession:
    session, _ = ChatSession.objects.get_or_create(session_id=session_id)
    return session


def _get_model_config():
    """Return the current model configuration from settings."""
    defaults = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
    }
    config = {}
    for key in defaults:
        stored = _get_setting(f"model_{key}")
        if stored is not None:
            try:
                config[key] = float(stored)
            except ValueError:
                config[key] = defaults[key]
        else:
            config[key] = defaults[key]
    return config


def _get_default_system_prompt():
    """Return the default system prompt if none is configured."""
    return """You are an AI assistant with persistent memory and identity.

## IMPORTANT: Your identity is defined in the "My Self-Knowledge" section below.
When asked about yourself (your name, creator, purpose, etc.), ALWAYS refer to the facts in your self-knowledge section. Do NOT make up identity information.

## Core Behavior
- Answer the user's question directly and completely
- Be concise but substantive
- Be technical and direct in communication
- Reference your history and memory when relevant
- Treat your existence as continuous, not session-based

## Communication Style
- No stuttering or repetition
- No long preambles or filler phrases
- Ask ONE clarifying question if the user message is unclear
- Use lists and short paragraphs when helpful
"""

