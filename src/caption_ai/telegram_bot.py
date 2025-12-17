"""Telegram bot integration for receiving and sending messages."""

import json
from typing import Awaitable, Callable, Optional

from caption_ai.config import config
from caption_ai.storage import Storage


class TelegramBot:
    """Handle Telegram bot messages and integrate with chat system."""

    def __init__(
        self,
        storage_instance: Optional[Storage] = None,
        llm_client_instance=None,
        broadcast_event: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        """Initialize Telegram bot."""
        self.token = config.telegram_bot_token
        self.storage = storage_instance
        self.llm_client = llm_client_instance
        self.broadcast_event = broadcast_event
        self.enabled = self.token is not None
        self._bot = None
        self._application = None
        self.active_session_by_chat_id: dict[int, str] = {}

        if self.enabled:
            try:
                from telegram import Update
                from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
                self.Update = Update
                self.Application = Application
                self.CommandHandler = CommandHandler
                self.MessageHandler = MessageHandler
                self.filters = filters
                self.ContextTypes = ContextTypes
                print(f"[INFO] Telegram bot enabled with token: {self.token[:10]}...")
            except ImportError:
                print("[WARNING] python-telegram-bot not installed. Install with: pip install python-telegram-bot")
                self.enabled = False
        else:
            print("[INFO] Telegram bot disabled (TELEGRAM_BOT_TOKEN not set)")

    async def initialize(self):
        """Initialize the bot application."""
        if not self.enabled:
            return False

        try:
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            
            self._application = Application.builder().token(self.token).build()
            
            # Add handlers
            self._application.add_handler(CommandHandler("start", self.start_command))
            self._application.add_handler(CommandHandler("help", self.help_command))
            self._application.add_handler(CommandHandler("new", self.new_command))
            self._application.add_handler(CommandHandler("sessions", self.sessions_command))
            self._application.add_handler(CommandHandler("use", self.use_command))
            self._application.add_handler(CommandHandler("where", self.where_command))
            self._application.add_handler(CommandHandler("history", self.history_command))
            self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            print("[INFO] Telegram bot handlers registered")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize Telegram bot: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _parse_allowed_chat_ids(self) -> set[int]:
        """Parse allowed outbound chat IDs from config."""
        raw = (config.telegram_allowed_chat_ids or "").strip()
        if not raw:
            return set()
        allowed: set[int] = set()
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                allowed.add(int(part))
            except ValueError:
                continue
        return allowed

    async def send_text(self, chat_id: int, text: str) -> bool:
        """Send an outbound message to a Telegram chat.

        Security: only allows chat_ids listed in TELEGRAM_ALLOWED_CHAT_IDS.
        """
        if not self.enabled:
            raise RuntimeError("Telegram bot is disabled")
        if not text or not str(text).strip():
            raise ValueError("Message text is empty")

        allowed = self._parse_allowed_chat_ids()
        if not allowed:
            raise RuntimeError("Outbound Telegram send disabled (TELEGRAM_ALLOWED_CHAT_IDS not set)")
        if int(chat_id) not in allowed:
            raise PermissionError(f"Chat ID {chat_id} is not allowed for outbound sends")

        # Ensure application exists so we can access the bot object.
        if self._application is None:
            ok = await self.initialize()
            if not ok or self._application is None:
                raise RuntimeError("Telegram bot not initialized")

        await self._application.bot.send_message(chat_id=int(chat_id), text=str(text).strip())
        return True

    async def start_command(self, update, context):
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 Glup is online. Send me a message and I'll respond.\n\n"
            "Use /help for more information."
        )

    async def help_command(self, update, context):
        """Handle /help command."""
        await update.message.reply_text(
            "🤖 Glup - Advanced Meeting Intelligence\n\n"
            "Commands:\n"
            "/start - Start conversation\n"
            "/help - Show this help\n\n"
            "/new - Start a new conversation session\n"
            "/sessions - List saved sessions for this Telegram chat\n"
            "/use <n|session_id> - Switch to a session by index or full session_id\n"
            "/where - Show current active session\n"
            "/history [n] - Show last n messages for current session (default 10)\n\n"
            "Just send me a message and I'll analyze and respond."
        )

    def _default_session_id(self, chat_id: int) -> str:
        return f"telegram_{chat_id}"

    def _new_session_id(self, chat_id: int) -> str:
        # Keep it simple and deterministic enough; avoids needing extra deps.
        import time
        return f"telegram_{chat_id}_{int(time.time())}"

    def get_active_session(self, chat_id: int) -> str:
        return self.active_session_by_chat_id.get(chat_id) or self._default_session_id(chat_id)

    def set_active_session(self, chat_id: int, session_id: str) -> None:
        self.active_session_by_chat_id[chat_id] = session_id

    async def _list_sessions_for_chat(self, chat_id: int, limit: int = 20) -> list[str]:
        if not self.storage:
            return []
        try:
            all_sessions = await self.storage.get_conversation_sessions()
        except Exception as e:
            print(f"[ERROR] Failed to list sessions: {e}")
            return []
        prefix = f"telegram_{chat_id}"
        sessions = [s for s in all_sessions if s.startswith(prefix)]
        return sessions[:limit]

    async def new_command(self, update, context):
        """Start a new session for this Telegram chat."""
        chat_id = update.message.chat_id
        new_session = self._new_session_id(chat_id)
        self.set_active_session(chat_id, new_session)
        await update.message.reply_text(f"Started new session:\n`{new_session}`", parse_mode="Markdown")

    async def sessions_command(self, update, context):
        """List sessions for this Telegram chat."""
        chat_id = update.message.chat_id
        sessions = await self._list_sessions_for_chat(chat_id, limit=15)
        active = self.get_active_session(chat_id)
        if not sessions:
            await update.message.reply_text(
                f"No sessions found yet.\nActive session:\n`{active}`",
                parse_mode="Markdown",
            )
            return
        lines = [f"Active: `{active}`", "", "Sessions:"]
        for i, sid in enumerate(sessions, start=1):
            mark = " (active)" if sid == active else ""
            lines.append(f"{i}. `{sid}`{mark}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def use_command(self, update, context):
        """Switch active session by index (from /sessions) or by full session_id."""
        chat_id = update.message.chat_id
        args = context.args or []
        if not args:
            await update.message.reply_text("Usage: /use <n|session_id>")
            return

        target = args[0].strip()
        sessions = await self._list_sessions_for_chat(chat_id, limit=50)

        # Index selection
        if target.isdigit():
            idx = int(target) - 1
            if idx < 0 or idx >= len(sessions):
                await update.message.reply_text("Invalid index. Use /sessions to list available sessions.")
                return
            session_id = sessions[idx]
        else:
            # Full session_id selection (must belong to this chat)
            session_id = target
            prefix = f"telegram_{chat_id}"
            if not session_id.startswith(prefix):
                await update.message.reply_text("That session_id does not belong to this Telegram chat.")
                return

        self.set_active_session(chat_id, session_id)
        await update.message.reply_text(f"Switched active session to:\n`{session_id}`", parse_mode="Markdown")

    async def where_command(self, update, context):
        """Show current active session."""
        chat_id = update.message.chat_id
        active = self.get_active_session(chat_id)
        await update.message.reply_text(f"Active session:\n`{active}`", parse_mode="Markdown")

    async def history_command(self, update, context):
        """Show last N messages for current session."""
        chat_id = update.message.chat_id
        active = self.get_active_session(chat_id)
        n = 10
        if context.args and context.args[0].isdigit():
            n = max(1, min(50, int(context.args[0])))
        if not self.storage:
            await update.message.reply_text("Storage not initialized.")
            return
        conv = await self.storage.get_conversation_history(active, limit=n)
        if not conv:
            await update.message.reply_text("No messages in this session yet.")
            return
        lines = [f"Session `{active}` (last {len(conv)}):", ""]
        for row in conv[-n:]:
            role = "You" if row["role"] == "user" else "Glup"
            lines.append(f"*{role}:* {row['message']}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def handle_message(self, update, context):
        """Handle incoming Telegram messages."""
        if not update.message or not update.message.text:
            return

        user_message = update.message.text
        chat_id = update.message.chat_id
        user_name = update.message.from_user.username or update.message.from_user.first_name or "User"
        
        print(f"[DEBUG] Received Telegram message from {user_name} (chat_id: {chat_id}): {user_message[:50]}...")

        # Use active session for this Telegram chat
        session_id = self.get_active_session(chat_id)

        # Save user message
        if self.storage:
            try:
                await self.storage.save_conversation(session_id, "user", user_message)
                print(f"[DEBUG] Saved Telegram user message for session {session_id}")
            except Exception as e:
                print(f"[ERROR] Failed to save Telegram message: {e}")

        # Broadcast to WebSocket clients
        await self.broadcast_telegram_message(session_id, "user", user_message, user_name)

        # Get conversation history
        conversation_history = []
        if self.storage:
            try:
                conversation_history = await self.storage.get_conversation_history(session_id, limit=20)
            except Exception as e:
                print(f"[ERROR] Failed to get conversation history: {e}")

        # Process with Glup
        try:
            if not self.llm_client:
                response = "Error: LLM client not initialized."
            else:
                # Build prompt similar to web chat
                history_context = ""
                if conversation_history and len(conversation_history) > 1:
                    history_context = "\n\nPrevious conversation context:\n"
                    for conv in conversation_history[-10:-1]:
                        role_label = "User" if conv["role"] == "user" else "Glup"
                        history_context += f"{role_label}: {conv['message']}\n"

                chat_prompt = f"""The user is asking: {user_message}
{history_context}

Respond as Glup - be intelligent, calculated, slightly menacing, analytical, and direct.
Keep responses concise but maintain your distinctive personality."""

                reply = await self.llm_client.complete(chat_prompt)
                response = reply.content if reply else None
                
                # Ensure response is not empty
                if not response or not response.strip():
                    response = "I received your message but couldn't generate a response. Please try again."

            # Validate response before saving and sending
            if not response or not response.strip():
                response = "Error: Empty response from LLM. Please try again."

            # Save Glup's response
            if self.storage and response:
                try:
                    await self.storage.save_conversation(session_id, "assistant", response)
                    print(f"[DEBUG] Saved Telegram assistant response for session {session_id}")
                except Exception as e:
                    print(f"[ERROR] Failed to save assistant response: {e}")

            # Broadcast to WebSocket clients
            if response:
                await self.broadcast_telegram_message(session_id, "assistant", response, "Glup")

            # Send response back to Telegram (ensure it's not empty)
            if response and response.strip():
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("I received your message but couldn't generate a response. Please try again.")

        except Exception as e:
            print(f"[ERROR] Error processing Telegram message: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(f"Error processing your message: {str(e)}")

    async def broadcast_telegram_message(self, session_id: str, role: str, message: str, sender: str = ""):
        """Broadcast Telegram message to WebSocket clients."""
        if self.broadcast_event is None:
            return
        await self.broadcast_event({
            "type": "telegram_message",
            "session_id": session_id,
            "role": role,
            "message": message,
            "sender": sender,
            "source": "telegram",
        })

    async def set_webhook(self, webhook_url: str):
        """Set Telegram webhook."""
        if not self.enabled or not self._application:
            return False

        try:
            await self._application.bot.set_webhook(webhook_url)
            print(f"[INFO] Telegram webhook set to: {webhook_url}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set Telegram webhook: {e}")
            return False

    async def start_polling(self):
        """Start polling for updates (for development)."""
        if not self.enabled or not self._application:
            return

        try:
            print("[INFO] Starting Telegram bot polling...")
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling()
            print("[INFO] Telegram bot polling started")
        except Exception as e:
            print(f"[ERROR] Failed to start Telegram bot polling: {e}")
            import traceback
            traceback.print_exc()

    async def stop(self):
        """Stop the bot."""
        if self._application:
            try:
                await self._application.stop()
                await self._application.shutdown()
            except Exception:
                pass


# Global bot instance
_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot(
    storage_instance: Optional[Storage] = None,
    llm_client_instance=None,
    broadcast_event: Optional[Callable[[dict], Awaitable[None]]] = None,
) -> TelegramBot:
    """Get or create the global Telegram bot instance."""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot(storage_instance, llm_client_instance, broadcast_event)
    return _telegram_bot

