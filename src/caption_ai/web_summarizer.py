"""Web-aware summarizer that broadcasts summaries to web clients."""

from caption_ai.bus import Segment
from caption_ai.summarizer import Summarizer
from caption_ai.web import broadcast_summary


class WebSummarizer(Summarizer):
    """Summarizer that broadcasts summaries to web clients."""

    async def _summarize(self, segments: list[Segment]) -> None:
        """Summarize segments and broadcast to web clients."""
        await super()._summarize(segments)
        if self.current_summary:
            await broadcast_summary(self.current_summary)


