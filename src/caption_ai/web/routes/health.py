"""Health check API endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from caption_ai.config import config
from caption_ai.web.state import (
    get_storage,
    get_llm_client,
    get_telegram_bot_instance,
)

router = APIRouter()


@router.get("/api/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    storage = get_storage()
    llm_client = get_llm_client()
    telegram_bot_instance = get_telegram_bot_instance()
    
    # Check Telegram bot status
    telegram_status = "disabled"
    if telegram_bot_instance:
        # Check if bot is enabled and application is initialized (actually running)
        if telegram_bot_instance.enabled and hasattr(telegram_bot_instance, '_application') and telegram_bot_instance._application:
            telegram_status = "enabled"
        elif telegram_bot_instance.enabled:
            telegram_status = "enabled"  # Enabled but may still be initializing
        else:
            telegram_status = "disabled"
    elif config.telegram_bot_token:
        telegram_status = "enabled"  # Token configured but instance not yet created
    else:
        telegram_status = "disabled"
    
    return JSONResponse({
        "status": "ok",
        "backend": "running",
        "storage": "initialized" if storage else "not initialized",
        "llm_client": "ready" if llm_client else "not ready",
        "telegram_notifications": telegram_status,
    })

