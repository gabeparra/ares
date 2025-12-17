"""Telegram notification integration using Apprise."""

import asyncio
from typing import Optional

from caption_ai.config import config


class Notifier:
    """Handle Telegram notifications via Apprise."""

    def __init__(self):
        """Initialize notifier."""
        try:
            self.enabled = config.notify and config.apprise_url is not None
            self.apprise_url = config.apprise_url
            self._apprise = None

            if self.enabled:
                try:
                    import apprise
                    self._apprise = apprise.Apprise()
                    self._apprise.add(self.apprise_url)
                    print(f"[INFO] Telegram notifications enabled: {self.apprise_url[:20]}...")
                except ImportError:
                    print("[WARNING] Apprise not installed. Install with: pip install apprise")
                    self.enabled = False
                except Exception as e:
                    print(f"[WARNING] Failed to initialize Telegram notifications: {e}")
                    import traceback
                    traceback.print_exc()
                    self.enabled = False
            else:
                if config.notify and not config.apprise_url:
                    print("[WARNING] NOTIFY=true but APPRISE_URL not set. Telegram notifications disabled.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Notifier: {e}")
            import traceback
            traceback.print_exc()
            self.enabled = False
            self._apprise = None

    async def send_message(self, title: str, body: str) -> bool:
        """Send a notification message to Telegram."""
        if not self.enabled or not self._apprise:
            return False

        try:
            # Run apprise notification in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._apprise.notify(
                    body=body,
                    title=title,
                )
            )
            return result
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram notification: {e}")
            return False

    async def send_chat_message(self, role: str, message: str, session_id: Optional[str] = None) -> bool:
        """Send a chat message notification to Telegram."""
        if not self.enabled:
            return False

        role_emoji = "👤" if role == "user" else "🤖"
        title = f"{role_emoji} Glup Chat"
        
        # Truncate long messages for Telegram
        max_length = 1000
        if len(message) > max_length:
            message = message[:max_length] + "..."
        
        body = f"{role_emoji} {role.capitalize()}: {message}"
        
        if session_id:
            body += f"\n\nSession: {session_id[:20]}..."

        return await self.send_message(title, body)

    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.enabled


# Global notifier instance
_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Get or create the global notifier instance."""
    global _notifier
    if _notifier is None:
        try:
            _notifier = Notifier()
        except Exception as e:
            print(f"[ERROR] Failed to create Notifier instance: {e}")
            import traceback
            traceback.print_exc()
            # Return a disabled notifier to prevent blocking
            _notifier = Notifier.__new__(Notifier)
            _notifier.enabled = False
            _notifier._apprise = None
    return _notifier

