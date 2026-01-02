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
        "num_gpu": 40,
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


def _get_canonical_user_id(identifier, default_user_id="default"):
    """
    Get the canonical ARES user_id from any identifier.
    
    Supports:
    - Telegram chat_id: Looks up link stored as preference "telegram_user_link_{chat_id}"
    - ARES user_id: Returns as-is
    - Returns default_user_id if no link found
    
    This allows Telegram users to be linked to ARES user_ids so memories are shared.
    """
    from .models import UserPreference
    
    # If it's already a user_id format we recognize, return it
    # (This is a simple check - you might want to add more validation)
    if identifier and identifier != "default":
        # Check if this is a Telegram chat_id format (numeric)
        if identifier.isdigit():
            # Look for link: telegram_user_link_{chat_id} -> user_id
            pref_key = f"telegram_user_link_{identifier}"
            preference = UserPreference.objects.filter(
                preference_key=pref_key
            ).first()
            if preference:
                return preference.preference_value.strip()
            # No link found for this Telegram chat_id, return default
            return default_user_id
        else:
            # Might be an ARES user_id already (e.g., Auth0 user_id like "google-oauth2|123456")
            # Check if there's a reverse link (telegram_user_link_* pointing to this identifier)
            preference = UserPreference.objects.filter(
                preference_key__startswith="telegram_user_link_",
                preference_value=identifier
            ).first()
            if preference:
                # Found a reverse link, so this identifier is the canonical user_id
                return identifier
            # No reverse link found, but identifier is likely already a valid user_id
            # (e.g., Auth0 user_id), so return it as-is
            return identifier
    
    return default_user_id


def _link_telegram_to_user_id(telegram_chat_id, user_id):
    """
    Link a Telegram chat_id to an ARES user_id.
    
    This stores a preference that maps Telegram chat_id to ARES user_id,
    allowing memories to be shared between Telegram and web interfaces.
    """
    from .models import UserPreference
    
    pref_key = f"telegram_user_link_{telegram_chat_id}"
    preference, created = UserPreference.objects.update_or_create(
        preference_key=pref_key,
        defaults={
            "preference_value": user_id,
            "user_id": user_id,  # Store with the linked user_id for easier querying
        }
    )
    return preference, created


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

## Telegram Messaging
You can send messages to Telegram users. When the user asks you to send a message to someone via Telegram, use this format in your response:
[TELEGRAM_SEND:identifier:message_text]

Where:
- identifier: The name, username, or nickname of the Telegram user (e.g., "gabu", "gabe", "@username")
- message_text: The actual message content to send

Example: If asked to "send hello to gabu", include in your response:
[TELEGRAM_SEND:gabu:Hello from ARES!]

After sending, the system will replace this marker with a confirmation. Always confirm that you've sent the message in your response.
"""

