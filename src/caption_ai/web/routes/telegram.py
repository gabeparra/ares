"""Telegram outbound messaging API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from caption_ai.web.state import get_telegram_bot_instance

router = APIRouter()


class TelegramSendRequest(BaseModel):
    chat_id: int = Field(..., description="Target Telegram chat_id")
    message: str = Field(..., description="Message text to send")


@router.post("/api/telegram/send")
async def telegram_send(request: TelegramSendRequest) -> JSONResponse:
    """Send an outbound Telegram message to an allowed chat_id."""
    bot = get_telegram_bot_instance()
    if not bot or not getattr(bot, "enabled", False):
        return JSONResponse({"error": "Telegram bot is not enabled"}, status_code=503)

    try:
        await bot.send_text(chat_id=request.chat_id, text=request.message)
        return JSONResponse({"success": True})
    except PermissionError as e:
        return JSONResponse({"error": str(e)}, status_code=403)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


