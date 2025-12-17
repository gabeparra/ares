"""Storage initialization and management."""

import asyncio

from caption_ai.config import config
from caption_ai.storage import Storage
from caption_ai.telegram_bot import get_telegram_bot
from caption_ai.chatgpt_bridge import get_chatgpt_bridge
from caption_ai.web.state import (
    get_llm_client,
    set_storage_instance,
    set_telegram_bot_instance,
    set_chatgpt_bridge_instance,
)
from caption_ai.web.llm_client import set_llm_client
from caption_ai.web.broadcast import broadcast_event


async def _init_storage_async(storage_instance: Storage) -> None:
    """Async helper to initialize storage."""
    try:
        await storage_instance.init()
    except Exception as e:
        print(f"[WARNING] Failed to ensure storage init: {e}")
        import traceback
        traceback.print_exc()


def set_storage(storage_instance: Storage) -> None:
    """Set the storage instance."""
    set_storage_instance(storage_instance)
    
    # Ensure database is initialized
    # Since we're in a sync context but need async, schedule it
    try:
        loop = asyncio.get_running_loop()
        # Event loop is running, schedule as task
        asyncio.create_task(_init_storage_async(storage_instance))
    except RuntimeError:
        # No running event loop, try to get/create one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_init_storage_async(storage_instance))
            else:
                # Event loop exists but not running, run until complete
                loop.run_until_complete(_init_storage_async(storage_instance))
        except RuntimeError:
            # No event loop exists, try to create one
            try:
                asyncio.run(_init_storage_async(storage_instance))
            except RuntimeError:
                # Cannot create new event loop (likely already running in another thread)
                # Storage will be initialized on first use via the storage methods
                pass
    
    # Initialize LLM client when storage is set
    llm_client = get_llm_client()
    if llm_client is None:
        set_llm_client()
        llm_client = get_llm_client()
    
    # Initialize Telegram bot if enabled
    if config.telegram_bot_token:
        telegram_bot = get_telegram_bot(storage_instance, llm_client, broadcast_event)
        set_telegram_bot_instance(telegram_bot)
        try:
            loop = asyncio.get_running_loop()
            # Event loop is running, schedule tasks
            asyncio.create_task(telegram_bot.initialize())
            # Start polling if webhook URL not set (for development)
            if not config.telegram_webhook_url:
                asyncio.create_task(telegram_bot.start_polling())
        except RuntimeError:
            # No running event loop, try to get one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(telegram_bot.initialize())
                    if not config.telegram_webhook_url:
                        asyncio.create_task(telegram_bot.start_polling())
                else:
                    # Event loop not running, run initialization synchronously
                    loop.run_until_complete(telegram_bot.initialize())
                    if not config.telegram_webhook_url:
                        asyncio.create_task(telegram_bot.start_polling())
            except RuntimeError:
                # No event loop available, will be initialized later
                pass
    
    # Initialize ChatGPT bridge if enabled
    if config.chatgpt_enabled:
        chatgpt_bridge = get_chatgpt_bridge(storage_instance, llm_client, broadcast_event)
        set_chatgpt_bridge_instance(chatgpt_bridge)
        try:
            loop = asyncio.get_running_loop()
            # Event loop is running, schedule tasks
            asyncio.create_task(chatgpt_bridge.initialize())
            asyncio.create_task(chatgpt_bridge.start_monitoring())
        except RuntimeError:
            # No running event loop, try to get one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(chatgpt_bridge.initialize())
                    asyncio.create_task(chatgpt_bridge.start_monitoring())
                else:
                    # Event loop not running, run initialization synchronously
                    loop.run_until_complete(chatgpt_bridge.initialize())
                    asyncio.create_task(chatgpt_bridge.start_monitoring())
            except RuntimeError:
                # No event loop available, will be initialized later
                pass

