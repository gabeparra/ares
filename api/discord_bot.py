"""
Discord bot service for ARES.

Handles Discord bot functionality, message processing, and integration with ARES orchestrator.
"""

import os
import logging
import threading
import asyncio
import time
from django.utils import timezone
from asgiref.sync import sync_to_async

# Ensure Django is set up
import django
if not hasattr(django, 'apps') or not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
    django.setup()

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Discord API limits
DISCORD_MESSAGE_LIMIT = 2000
DISCORD_CHUNK_DELAY = 0.5  # seconds between message chunks

# Bot stability thresholds
BOT_READY_STABILITY_WINDOW = 2.0  # seconds before reporting as ready
BOT_DISCONNECT_TIMEOUT = 3.0  # seconds before considering disconnected

# Auto-restart configuration
MAX_RESTART_RETRIES = 5
BASE_RETRY_DELAY = 5  # seconds
MAX_RETRY_DELAY = 300  # 5 minutes max

# Health monitor configuration
HEALTH_CHECK_INTERVAL = 30  # seconds between health checks
MAX_CONSECUTIVE_FAILURES = 3  # failures before auto-restart
RESTART_COOLDOWN = 60  # seconds between restart attempts

# =============================================================================
# PID file for cross-process coordination
# =============================================================================

PID_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'discord_bot.pid')


def _is_another_bot_running() -> bool:
    """
    Check if another Discord bot process is already running.
    Uses a PID file to coordinate across processes (management command vs gunicorn).
    """
    if not os.path.exists(PID_FILE_PATH):
        return False

    try:
        with open(PID_FILE_PATH, 'r') as f:
            pid = int(f.read().strip())

        # Check if process is still running
        os.kill(pid, 0)  # Doesn't kill, just checks if process exists

        # Process exists - but is it actually a Discord bot?
        # Check if it's not our own process
        if pid == os.getpid():
            return False

        logger.warning(f"[DISCORD] Another bot process is running (PID {pid})")
        return True

    except (ValueError, FileNotFoundError):
        # Invalid or missing PID file
        return False
    except ProcessLookupError:
        # Process doesn't exist anymore, clean up stale PID file
        logger.info(f"[DISCORD] Removing stale PID file")
        try:
            os.remove(PID_FILE_PATH)
        except OSError:
            pass
        return False
    except PermissionError:
        # Can't check process, assume it might be running
        return True


def _write_pid_file():
    """Write our PID to the PID file."""
    try:
        os.makedirs(os.path.dirname(PID_FILE_PATH), exist_ok=True)
        with open(PID_FILE_PATH, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"[DISCORD] Wrote PID file: {PID_FILE_PATH} (PID {os.getpid()})")
    except Exception as e:
        logger.error(f"[DISCORD] Failed to write PID file: {e}")


def _remove_pid_file():
    """Remove the PID file."""
    try:
        if os.path.exists(PID_FILE_PATH):
            # Only remove if it's our PID
            with open(PID_FILE_PATH, 'r') as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(PID_FILE_PATH)
                logger.info(f"[DISCORD] Removed PID file")
    except Exception as e:
        logger.debug(f"[DISCORD] Error removing PID file: {e}")


# =============================================================================
# Thread-safe state management
# =============================================================================

_state_lock = threading.Lock()

# Bot state (protected by _state_lock)
_bot_instance = None
_bot_thread = None
_bot_loop = None
_bot_ready = False
_bot_ready_timestamp = None
_bot_disconnect_timestamp = None
_bot_last_error = None
_bot_restart_count = 0

# Message deduplication to prevent processing the same message twice
_processed_messages = set()
_processed_messages_lock = threading.Lock()
_processing_messages = set()  # Messages currently being processed (to catch concurrent processing)
MAX_PROCESSED_MESSAGES = 1000  # Keep track of last N messages to prevent memory leak

# Session-level locks to prevent concurrent orchestrator calls for the same session
_session_locks = {}
_session_locks_lock = threading.Lock()

# Health monitor state
_health_monitor_thread = None
_health_monitor_running = False


def _get_state():
    """Get current bot state in a thread-safe manner."""
    with _state_lock:
        return {
            'ready': _bot_ready,
            'ready_timestamp': _bot_ready_timestamp,
            'disconnect_timestamp': _bot_disconnect_timestamp,
            'last_error': _bot_last_error,
            'restart_count': _bot_restart_count,
        }


def _set_ready(value: bool, timestamp: float = None):
    """Set bot ready state in a thread-safe manner."""
    global _bot_ready, _bot_ready_timestamp, _bot_disconnect_timestamp
    with _state_lock:
        _bot_ready = value
        if value:
            _bot_ready_timestamp = timestamp or time.time()
            _bot_disconnect_timestamp = None
        else:
            _bot_ready_timestamp = None


def _set_disconnected():
    """Mark bot as disconnected in a thread-safe manner."""
    global _bot_disconnect_timestamp
    with _state_lock:
        _bot_disconnect_timestamp = time.time()


def _set_error(error: str):
    """Set last error in a thread-safe manner."""
    global _bot_last_error
    with _state_lock:
        _bot_last_error = error


def _increment_restart_count():
    """Increment restart count in a thread-safe manner."""
    global _bot_restart_count
    with _state_lock:
        _bot_restart_count += 1
        return _bot_restart_count


def _reset_state():
    """Reset all state in a thread-safe manner."""
    global _bot_ready, _bot_ready_timestamp, _bot_disconnect_timestamp, _bot_last_error
    with _state_lock:
        _bot_ready = False
        _bot_ready_timestamp = None
        _bot_disconnect_timestamp = None
        _bot_last_error = None


def _is_message_processed(message_id: int) -> bool:
    """
    Check if a message has already been processed OR is currently being processed.
    If not processed, marks it as being processed and returns False.
    If already processed or currently processing, returns True.
    """
    global _processed_messages, _processing_messages
    with _processed_messages_lock:
        # Check if already fully processed
        if message_id in _processed_messages:
            logger.warning(f"[DISCORD] Message {message_id} already in _processed_messages")
            return True

        # Check if currently being processed (concurrent request)
        if message_id in _processing_messages:
            logger.warning(f"[DISCORD] Message {message_id} currently being processed (concurrent)")
            return True

        # Mark as currently processing
        _processing_messages.add(message_id)
        logger.info(f"[DISCORD] Message {message_id} marked as processing")

        return False


def _mark_message_completed(message_id: int):
    """Mark a message as fully processed."""
    global _processed_messages, _processing_messages
    with _processed_messages_lock:
        # Move from processing to processed
        _processing_messages.discard(message_id)
        _processed_messages.add(message_id)

        # Prune old messages if set is too large
        if len(_processed_messages) > MAX_PROCESSED_MESSAGES:
            # Remove oldest entries (roughly half)
            to_remove = len(_processed_messages) - (MAX_PROCESSED_MESSAGES // 2)
            _processed_messages = set(list(_processed_messages)[to_remove:])


def _get_session_lock(session_id):
    """Get or create a lock for a specific session."""
    with _session_locks_lock:
        if session_id not in _session_locks:
            _session_locks[session_id] = threading.Lock()
        return _session_locks[session_id]


@sync_to_async(thread_sensitive=False)
def _process_message_sync(canonical_user_id, message_content, session_id):
    """
    Synchronous wrapper for orchestrator processing.

    Matches Telegram's exact flow: saves user message, processes via orchestrator,
    saves assistant response. Uses cloud APIs since local machine is down.

    Note: thread_sensitive=False ensures this runs in a thread pool, not the main thread.
    """
    import uuid
    import threading
    call_id = str(uuid.uuid4())[:8]
    thread_id = threading.current_thread().ident
    thread_name = threading.current_thread().name
    logger.info(f"[DISCORD] [{call_id}] _process_message_sync ENTRY thread={thread_id}/{thread_name} user={canonical_user_id} session={session_id}")

    # Get session-specific lock to prevent concurrent processing
    session_lock = _get_session_lock(session_id)

    # Try to acquire lock - if already held, another thread is processing this session
    if not session_lock.acquire(blocking=False):
        logger.warning(f"[DISCORD] [{call_id}] Session {session_id} is already being processed by another thread - SKIPPING")
        return None, "Session already being processed"

    try:
        logger.info(f"[DISCORD] [{call_id}] Acquired session lock for {session_id}")

        from ares_core.orchestrator import orchestrator
        from .models import ConversationMessage, ChatSession
        from .utils import _ensure_session

        session = _ensure_session(session_id)

        # Save user message first (same as Telegram)
        ConversationMessage.objects.create(
            session=session,
            role=ConversationMessage.ROLE_USER,
            message=message_content,
        )

        logger.info(f"[DISCORD] [{call_id}] Processing message via ORCHESTRATOR for user_id={canonical_user_id}")

        # Process message through orchestrator
        response = orchestrator.process_chat_request(
            user_id=canonical_user_id,
            message=message_content,
            session_id=session_id,
            system_prompt_override=None,
            prefer_local=False,
        )

        assistant_text = response.content
        model_name = response.model
        logger.info(f"[DISCORD] [{call_id}] Successfully processed via orchestrator: provider={response.provider}, model={model_name}")

        # Save assistant response (same as Telegram)
        ConversationMessage.objects.create(
            session=session,
            role=ConversationMessage.ROLE_ASSISTANT,
            message=assistant_text,
        )
        ChatSession.objects.filter(session_id=session_id).update(updated_at=timezone.now())

        logger.info(f"[DISCORD] [{call_id}] _process_message_sync EXIT success")
        return assistant_text, None

    except Exception as e:
        # If orchestrator fails, provide a fallback message (same as Telegram)
        logger.error(f"[DISCORD] [{call_id}] Orchestrator failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Try to log error to session
        try:
            from .models import ConversationMessage
            from .utils import _ensure_session
            session = _ensure_session(session_id)
            ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ERROR,
                message=f"Orchestrator error: {str(e)}",
            )
        except Exception:
            pass

        assistant_text = "⚠️ I received your message, but I'm currently unable to process it. Your message has been saved, and I'll be back shortly."
        return assistant_text, str(e)

    finally:
        # Always release the session lock
        session_lock.release()
        logger.info(f"[DISCORD] [{call_id}] Released session lock for {session_id}")


async def _process_discord_message(channel, user_id, username, message_content, session_id, canonical_user_id):
    """
    Process a Discord message and send a reply.

    Uses the orchestrator for consistent memory management and prompts.
    """
    logger.info(f'[DISCORD] _process_discord_message called for user={user_id}, session={session_id}')
    try:
        # Process message (this runs in sync context via sync_to_async)
        assistant_text, error = await _process_message_sync(canonical_user_id, message_content, session_id)
        logger.info(f'[DISCORD] Got response from orchestrator, length={len(assistant_text) if assistant_text else 0}')
        
        if assistant_text:
            # Send reply to Discord channel
            try:
                # Split long messages (Discord has 2000 character limit)
                if len(assistant_text) <= DISCORD_MESSAGE_LIMIT:
                    logger.info(f'[DISCORD] Sending single message to channel {channel.id}, content_hash={hash(assistant_text)}')
                    sent_msg = await channel.send(assistant_text)
                    logger.info(f"[DISCORD] Message sent successfully, discord_msg_id={sent_msg.id}")
                else:
                    # Split into chunks
                    chunks = [assistant_text[i:i+DISCORD_MESSAGE_LIMIT] for i in range(0, len(assistant_text), DISCORD_MESSAGE_LIMIT)]
                    for i, chunk in enumerate(chunks):
                        logger.info(f'[DISCORD] Sending chunk {i+1}/{len(chunks)} to channel {channel.id}')
                        sent_msg = await channel.send(chunk)
                        logger.info(f"[DISCORD] Chunk {i+1} sent, discord_msg_id={sent_msg.id}")
                        await asyncio.sleep(DISCORD_CHUNK_DELAY)

                logger.info(f"[DISCORD] Finished sending reply to channel {channel.id}")
            except Exception as e:
                logger.error(f"[DISCORD] Exception sending message: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"[DISCORD] No assistant_text generated for message from user {user_id}")
            fallback = "⚠️ I received your message, but I'm currently unable to process it. Please try again in a moment."
            await channel.send(fallback)
            
    except Exception as e:
        logger.error(f"[DISCORD] Error processing message: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await channel.send("⚠️ An error occurred while processing your message. Please try again later.")
        except:
            pass


@sync_to_async
def _get_canonical_user_id_from_discord(discord_user_id):
    """
    Get the canonical ARES user_id from a Discord user_id.
    
    Checks if there's a linked Discord account, otherwise uses discord_user_id as the identifier.
    """
    from .models import DiscordCredential
    
    try:
        # Try to find linked Discord account
        cred = DiscordCredential.objects.filter(discord_user_id=str(discord_user_id), enabled=True).first()
        if cred:
            return cred.user_id
    except Exception as e:
        logger.warning(f"Error looking up Discord user: {e}")
    
    # Fallback: use Discord user ID as identifier
    return f"discord:{discord_user_id}"


def _get_daily_discord_session_id(channel_id, user_id):
    """
    Generate a daily Discord session ID (similar to Telegram).
    
    Format: discord_user_{user_id}_{channel_id}_{YYYY-MM-DD}
    Creates a new session each day for the same user/channel.
    """
    from django.utils import timezone
    today = timezone.now().date()
    return f"discord_user_{user_id}_{channel_id}_{today.isoformat()}"


def _get_or_create_session_id(channel_id, user_id):
    """
    Get or create a session ID for a Discord channel/user combination.
    Uses daily sessions like Telegram.
    """
    return _get_daily_discord_session_id(channel_id, user_id)


async def _run_discord_bot():
    """
    Run the Discord bot in an async event loop.
    """
    global _bot_instance
    
    import discord

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN not configured")
        return

    # Set up intents
    intents = discord.Intents.default()
    intents.message_content = True  # Required to read message content
    intents.guilds = True
    intents.guild_messages = True
    intents.dm_messages = True

    # Use discord.Client instead of commands.Bot to avoid any command framework interference
    bot = discord.Client(intents=intents)
    _bot_instance = bot
    
    logger.info('[DISCORD] Bot instance created, registering event handlers...')
    
    @bot.event
    async def on_ready():
        logger.info('[DISCORD] on_ready() event fired!')

        # Validate MESSAGE_CONTENT intent
        if not bot.intents.message_content:
            logger.critical('[DISCORD] MESSAGE_CONTENT intent not enabled! Bot cannot read messages.')
            _set_error('MESSAGE_CONTENT intent not enabled')
            await bot.close()
            return

        _set_ready(True)
        logger.info(f'[DISCORD] Bot logged in as {bot.user} (ID: {bot.user.id})')
        logger.info(f'[DISCORD] Bot is in {len(bot.guilds)} guilds')
        logger.info(f'[DISCORD] MESSAGE_CONTENT intent enabled: {bot.intents.message_content}')

        # Set bot status
        try:
            await bot.change_presence(activity=discord.Game(name="ARES AI Assistant"))
            logger.info('[DISCORD] Bot presence updated')
        except Exception as e:
            logger.error(f'[DISCORD] Error setting presence: {e}')

    @bot.event
    async def on_disconnect():
        # Don't immediately mark as not ready - wait a moment in case it's a temporary disconnect
        # The status check will handle this with a stability window
        _set_disconnected()
        logger.warning('[DISCORD] Bot disconnected')

    @bot.event
    async def on_resume():
        _set_ready(True)
        logger.info('[DISCORD] Bot reconnected')
    
    @bot.event
    async def on_message(message):
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return

        # Ignore empty messages
        if not message.content or not message.content.strip():
            return

        # Deduplication check - prevent processing the same message twice
        # This can happen during reconnection or due to race conditions
        if _is_message_processed(message.id):
            logger.warning(f'[DISCORD] Skipping duplicate message {message.id} - already processed')
            return

        import uuid
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f'[DISCORD] [{trace_id}] Processing message {message.id} from {message.author.name}: {message.content[:50]}...')

        # Check if bot is mentioned/tagged
        bot_mentioned = bot.user in message.mentions
        
        # Handle commands
        if message.content.startswith('!'):
            # Process commands
            if message.content.startswith('!new'):
                # Start new conversation (similar to Telegram /new)
                from django.utils import timezone
                now = timezone.now()
                user_id = str(message.author.id)
                channel_id = str(message.channel.id)
                session_id = f"discord_user_{user_id}_{channel_id}_{now.strftime('%Y-%m-%d_%H%M%S')}"
                
                @sync_to_async
                def create_new_session():
                    from .models import ChatSession
                    # Create new session with timestamp
                    session = ChatSession.objects.create(
                        session_id=session_id,
                        title=f"Discord {message.author.name} ({now.strftime('%b %d %H:%M')})"
                    )
                    return session
                
                await create_new_session()
                await message.channel.send(f"✨ Started a new conversation!\n\nSession: {now.strftime('%b %d, %H:%M')}\n\nYour previous conversations are saved and can be viewed in the ARES web interface.")
                return
            elif message.content.startswith('!help'):
                help_text = """
**ARES Discord Bot Commands:**
- `!new` - Start a new conversation
- `!help` - Show this help message

**Mention the bot** (`@ARES`) or send a direct message to chat with ARES AI!
                """
                await message.channel.send(help_text)
                return
        
        # Process messages if:
        # 1. Bot is mentioned/tagged, OR
        # 2. It's a direct message (DM)
        should_process = bot_mentioned or isinstance(message.channel, discord.DMChannel)
        
        if not should_process:
            # Bot not mentioned and not a DM, ignore
            return
        
        # Clean message content - remove bot mentions
        message_content = message.content.strip()
        if bot_mentioned:
            # Remove all mentions of the bot from the message
            # Replace @bot mentions with empty string
            import re
            # Remove <@!BOT_ID> or <@BOT_ID> mentions
            bot_id = bot.user.id
            message_content = re.sub(rf'<@!?{bot_id}>', '', message_content)
            # Also remove plain @bot mentions if any
            message_content = message_content.replace(f'@{bot.user.name}', '')
            message_content = message_content.replace(f'@{bot.user.display_name}', '')
            message_content = message_content.strip()
        
        # If message is empty after removing mentions, don't process
        if not message_content:
            return
        
        # Process the message
        user_id = str(message.author.id)
        username = message.author.name
        channel = message.channel
        
        # Use daily session (same pattern as Telegram)
        session_id = _get_or_create_session_id(str(channel.id), user_id)
        canonical_user_id = await _get_canonical_user_id_from_discord(user_id)
        
        # Ensure session exists and set title (same as Telegram)
        @sync_to_async
        def ensure_session_with_title():
            from .models import ChatSession
            from django.utils import timezone
            from .utils import _ensure_session
            
            session = _ensure_session(session_id)
            
            # Set friendly title on first sight (includes date for daily sessions)
            if not session.title:
                today = timezone.now().date()
                display = username or str(user_id)
                session.title = f"Discord {display} ({today.strftime('%b %d')})"
                session.save(update_fields=["title", "updated_at"])
            
            return session
        
        await ensure_session_with_title()

        logger.info(f'[DISCORD] [{trace_id}] About to call _process_discord_message for message {message.id}')

        try:
            # Show typing indicator
            async with channel.typing():
                # Process message (uses same orchestrator as Telegram)
                await _process_discord_message(
                    channel=channel,
                    user_id=user_id,
                    username=username,
                    message_content=message_content,
                    session_id=session_id,
                    canonical_user_id=canonical_user_id
                )
        finally:
            # Always mark as completed to prevent blocking future messages
            _mark_message_completed(message.id)
            logger.info(f'[DISCORD] [{trace_id}] Finished processing message {message.id}')
    
    @bot.event
    async def on_error(event, *args, **kwargs):
        logger.error(f'[DISCORD] Error in event {event}: {args}, {kwargs}')
        import traceback
        logger.error(traceback.format_exc())
    
    try:
        logger.info(f'[DISCORD] Attempting to connect to Discord with token (length: {len(bot_token) if bot_token else 0})...')
        await bot.start(bot_token)
        # Note: bot.start() is blocking and only returns when bot closes
        # So this line will only be reached if the bot disconnects
        logger.info(f'[DISCORD] Bot.start() returned (bot disconnected)')
    except Exception as e:
        _reset_state()
        error_msg = str(e)
        _set_error(error_msg)
        logger.error(f'[DISCORD] Error starting bot: {e}')
        import traceback
        logger.error(traceback.format_exc())
        # Re-raise to ensure the thread knows it failed
        raise


def _run_bot_in_thread():
    """
    Run the Discord bot in a separate thread with its own event loop.
    Implements auto-restart with exponential backoff on failure.
    """
    global _bot_loop

    retries = 0

    while retries < MAX_RESTART_RETRIES:
        # Create new event loop for this thread
        _bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_bot_loop)

        try:
            _bot_loop.run_until_complete(_run_discord_bot())
            # If we get here, bot exited cleanly (e.g., stop was called)
            logger.info('[DISCORD] Bot exited cleanly')
            break

        except Exception as e:
            retries += 1
            _reset_state()
            error_msg = str(e)
            _set_error(error_msg)

            # Calculate delay with exponential backoff
            delay = min(BASE_RETRY_DELAY * (2 ** (retries - 1)), MAX_RETRY_DELAY)

            logger.error(f'[DISCORD] Bot thread error (attempt {retries}/{MAX_RESTART_RETRIES}): {e}')
            logger.info(f'[DISCORD] Will retry in {delay} seconds...')

            import traceback
            logger.error(traceback.format_exc())

            # Close the event loop before sleeping
            try:
                _bot_loop.close()
            except Exception:
                pass

            # Sleep before retry (unless we've exhausted retries)
            if retries < MAX_RESTART_RETRIES:
                time.sleep(delay)
                _increment_restart_count()
                logger.info(f'[DISCORD] Attempting restart #{retries}...')

        finally:
            # Clean up event loop if still open
            try:
                if _bot_loop and not _bot_loop.is_closed():
                    _bot_loop.close()
            except Exception:
                pass

    if retries >= MAX_RESTART_RETRIES:
        logger.critical(f'[DISCORD] Bot failed after {MAX_RESTART_RETRIES} restart attempts. Giving up.')
        _set_error(f'Failed after {MAX_RESTART_RETRIES} restart attempts')

    # Final cleanup
    _reset_state()
    _remove_pid_file()


def start_discord_bot():
    """
    Start the Discord bot in a background thread.
    """
    global _bot_thread, _bot_instance

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN not configured")
        return False

    # Check if another process is already running a bot
    if _is_another_bot_running():
        logger.error("[DISCORD] Another Discord bot process is already running! Not starting duplicate.")
        return False

    with _state_lock:
        if _bot_thread and _bot_thread.is_alive():
            logger.warning("[DISCORD] Bot is already running in this process")
            return True

    logger.info("[DISCORD] Starting bot...")
    _reset_state()

    # Write PID file to prevent other processes from starting bots
    _write_pid_file()

    _bot_thread = threading.Thread(target=_run_bot_in_thread, daemon=True, name="DiscordBotThread")
    _bot_thread.start()

    return True


def stop_discord_bot():
    """
    Stop the Discord bot gracefully.
    """
    global _bot_loop, _bot_thread, _bot_instance

    with _state_lock:
        bot = _bot_instance
        loop = _bot_loop
        thread = _bot_thread

    if bot is not None:
        logger.info("[DISCORD] Stopping bot...")
        _reset_state()

        try:
            # Schedule bot close in the event loop
            if loop and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(bot.close(), loop)
                # Wait for close to complete (with timeout)
                try:
                    future.result(timeout=5.0)
                except Exception as e:
                    logger.warning(f"[DISCORD] Timeout waiting for bot close: {e}")
        except Exception as e:
            logger.error(f"[DISCORD] Error closing bot: {e}")

        with _state_lock:
            _bot_instance = None

        if thread:
            thread.join(timeout=10)

        # Remove PID file
        _remove_pid_file()

        logger.info("[DISCORD] Bot stopped")
        return True

    # Remove PID file even if bot wasn't running (cleanup)
    _remove_pid_file()
    return False


def is_discord_bot_running():
    """
    Check if the Discord bot is currently running and connected.

    Returns True only if:
    1. The bot thread is alive
    2. The bot instance exists
    3. The bot has signaled it's ready (via on_ready event)
    4. The bot has been ready for at least 2 seconds (stability check)
    5. If disconnected, it hasn't been disconnected for more than 3 seconds

    This stability check prevents flickering when the bot is reconnecting.
    """
    global _bot_thread, _bot_instance

    # Get thread-safe copies of state
    with _state_lock:
        thread = _bot_thread
        bot = _bot_instance
        ready = _bot_ready
        ready_timestamp = _bot_ready_timestamp
        disconnect_timestamp = _bot_disconnect_timestamp

    # Check if thread exists and is alive
    if thread is None or not thread.is_alive():
        return False

    # Check if bot instance exists
    if bot is None:
        return False

    current_time = time.time()

    # Check if bot has been disconnected for too long
    if disconnect_timestamp is not None:
        time_since_disconnect = current_time - disconnect_timestamp
        # If disconnected for more than threshold, consider it not running
        if time_since_disconnect > BOT_DISCONNECT_TIMEOUT:
            return False
        # If recently disconnected (less than threshold), still consider it running
        # This prevents flickering during brief reconnection attempts

    # Check if bot has signaled it's ready
    if not ready:
        return False

    # Stability check: bot must have been ready for at least threshold
    # This prevents flickering during reconnection attempts
    if ready_timestamp is None:
        return False

    time_since_ready = current_time - ready_timestamp

    # Require stability before reporting as running
    # This smooths out brief disconnects/reconnects
    if time_since_ready < BOT_READY_STABILITY_WINDOW:
        return False

    # Also check if bot is actually connected (if available)
    try:
        if hasattr(bot, 'is_closed') and bot.is_closed():
            return False
        if hasattr(bot, 'is_ready') and not bot.is_ready():
            # If not ready but our flag is set, check disconnect time
            if disconnect_timestamp is None:
                return time_since_ready >= 1.0
            return False
    except Exception:
        # If we can't check connection state, rely on the ready flag
        pass

    return True


def get_discord_bot_status():
    """
    Get detailed bot status for monitoring and health checks.

    Returns a dict with:
    - running: bool - whether bot is considered running
    - connected: bool - whether bot is connected to Discord
    - ready: bool - whether bot has received on_ready event
    - uptime_seconds: int or None - seconds since bot became ready
    - guilds: int - number of guilds bot is in
    - latency_ms: float or None - WebSocket latency to Discord
    - last_error: str or None - last error message
    - restart_count: int - number of times bot has been restarted
    """
    global _bot_thread, _bot_instance

    # Get thread-safe copies of state
    with _state_lock:
        thread = _bot_thread
        bot = _bot_instance
        ready = _bot_ready
        ready_timestamp = _bot_ready_timestamp
        last_error = _bot_last_error
        restart_count = _bot_restart_count

    status = {
        'running': False,
        'connected': False,
        'ready': False,
        'uptime_seconds': None,
        'guilds': 0,
        'latency_ms': None,
        'last_error': last_error,
        'restart_count': restart_count,
    }

    # Check thread status
    if thread is None or not thread.is_alive():
        return status

    status['running'] = True

    # Check bot instance
    if bot is None:
        return status

    try:
        status['connected'] = not bot.is_closed()
        status['ready'] = bot.is_ready() if hasattr(bot, 'is_ready') else ready
        status['guilds'] = len(bot.guilds) if hasattr(bot, 'guilds') else 0

        if hasattr(bot, 'latency') and bot.latency:
            status['latency_ms'] = round(bot.latency * 1000, 2)

        if ready_timestamp:
            status['uptime_seconds'] = int(time.time() - ready_timestamp)

    except Exception as e:
        logger.debug(f"[DISCORD] Error getting bot status details: {e}")

    return status


# =============================================================================
# Health Monitor
# =============================================================================

_last_restart_time = 0


def _health_monitor_loop():
    """
    Background loop that monitors bot health and triggers restart if needed.

    Checks bot status every HEALTH_CHECK_INTERVAL seconds.
    If bot is unhealthy for MAX_CONSECUTIVE_FAILURES checks, triggers restart.
    """
    global _health_monitor_running, _last_restart_time

    consecutive_failures = 0

    logger.info("[DISCORD] Health monitor started")

    while _health_monitor_running:
        time.sleep(HEALTH_CHECK_INTERVAL)

        if not _health_monitor_running:
            break

        status = get_discord_bot_status()

        # Check if bot is healthy (running, connected, and ready)
        is_healthy = status['running'] and status['connected'] and status['ready']

        if is_healthy:
            if consecutive_failures > 0:
                logger.info(f"[DISCORD] Health check passed after {consecutive_failures} failures")
            consecutive_failures = 0
            logger.debug(
                f"[DISCORD] Health OK: latency={status['latency_ms']}ms, "
                f"guilds={status['guilds']}, uptime={status['uptime_seconds']}s"
            )
        else:
            consecutive_failures += 1
            logger.warning(
                f"[DISCORD] Health check failed ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): "
                f"running={status['running']}, connected={status['connected']}, ready={status['ready']}"
            )

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                current_time = time.time()

                # Check restart cooldown
                if current_time - _last_restart_time < RESTART_COOLDOWN:
                    logger.warning(
                        f"[DISCORD] Restart cooldown active. "
                        f"Waiting {RESTART_COOLDOWN - (current_time - _last_restart_time):.0f}s"
                    )
                    continue

                logger.error("[DISCORD] Bot unhealthy, triggering restart...")
                _last_restart_time = current_time

                # Stop the bot
                try:
                    stop_discord_bot()
                except Exception as e:
                    logger.error(f"[DISCORD] Error stopping bot during health restart: {e}")

                # Wait a moment for cleanup
                time.sleep(5)

                # Start the bot
                try:
                    start_discord_bot()
                    logger.info("[DISCORD] Bot restart triggered by health monitor")
                except Exception as e:
                    logger.error(f"[DISCORD] Error starting bot during health restart: {e}")

                consecutive_failures = 0

    logger.info("[DISCORD] Health monitor stopped")


def start_health_monitor():
    """
    Start the background health monitor.

    The health monitor checks bot status periodically and automatically
    restarts the bot if it becomes unhealthy.
    """
    global _health_monitor_thread, _health_monitor_running

    if _health_monitor_thread and _health_monitor_thread.is_alive():
        logger.warning("[DISCORD] Health monitor is already running")
        return True

    _health_monitor_running = True
    _health_monitor_thread = threading.Thread(
        target=_health_monitor_loop,
        daemon=True,
        name="DiscordHealthMonitor"
    )
    _health_monitor_thread.start()

    logger.info("[DISCORD] Health monitor started")
    return True


def stop_health_monitor():
    """
    Stop the background health monitor.
    """
    global _health_monitor_running, _health_monitor_thread

    if not _health_monitor_running:
        return False

    logger.info("[DISCORD] Stopping health monitor...")
    _health_monitor_running = False

    if _health_monitor_thread:
        _health_monitor_thread.join(timeout=HEALTH_CHECK_INTERVAL + 5)

    logger.info("[DISCORD] Health monitor stopped")
    return True


def is_health_monitor_running():
    """
    Check if the health monitor is currently running.
    """
    return _health_monitor_running and _health_monitor_thread and _health_monitor_thread.is_alive()


def start_discord_bot_with_monitor():
    """
    Start the Discord bot along with the health monitor.

    This is the recommended way to start the bot in production,
    as it ensures automatic recovery from failures.
    """
    success = start_discord_bot()
    if success:
        start_health_monitor()
    return success


def stop_discord_bot_with_monitor():
    """
    Stop the Discord bot and the health monitor.
    """
    stop_health_monitor()
    return stop_discord_bot()

