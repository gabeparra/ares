"""Web server module for Glup UI."""

from caption_ai.web.app import app
from caption_ai.web.broadcast import broadcast_summary, broadcast_segment
from caption_ai.web.storage import set_storage
from caption_ai.web.state import set_summarizer_instance, get_summarizer_running

# Backward compatibility alias
set_summarizer = set_summarizer_instance

__all__ = [
    "app",
    "broadcast_summary",
    "broadcast_segment",
    "set_storage",
    "set_summarizer",
    "set_summarizer_instance",
    "get_summarizer_running",
]

