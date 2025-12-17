"""Testing utilities for generating fake segments."""

import asyncio
from datetime import datetime, timedelta

from rich.console import Console

from caption_ai.bus import Segment, SegmentBus

console = Console()

# Try to import web broadcast function if available
try:
    from caption_ai.web import broadcast_segment
    _web_available = True
except ImportError:
    _web_available = False


async def generate_fake_segments(bus: SegmentBus, count: int = 20, web_mode: bool = False) -> None:
    """Generate fake transcript segments for testing."""
    base_time = datetime.now()
    fake_segments = [
        ("Alice", "Let's start by reviewing the Q4 results."),
        ("Bob", "I've prepared the financial overview."),
        ("Alice", "Great, can you walk us through the key metrics?"),
        ("Bob", "Revenue is up 15% compared to last quarter."),
        ("Charlie", "That's excellent news. What about expenses?"),
        ("Bob", "Expenses are well controlled, only up 3%."),
        ("Alice", "So we're looking at a strong profit margin."),
        ("Charlie", "Yes, this positions us well for next year."),
        ("Alice", "Let's discuss the roadmap for Q1."),
        ("Bob", "I think we should focus on the new product launch."),
        ("Charlie", "Agreed, but we also need to address technical debt."),
        ("Alice", "Let's prioritize both. Bob, can you draft a plan?"),
        ("Bob", "I'll have something ready by Friday."),
        ("Alice", "Perfect. Any other items to discuss?"),
        ("Charlie", "I think we're good. Let's wrap up."),
        ("Alice", "Sounds good. Meeting adjourned."),
    ]

    for i, (speaker, text) in enumerate(fake_segments[:count]):
        segment = Segment(
            timestamp=base_time + timedelta(seconds=i * 3),
            text=text,
            speaker=speaker,
        )
        await bus.put(segment)
        if not web_mode:
            console.print(
                f"[dim][{segment.timestamp.strftime('%H:%M:%S')}] "
                f"{speaker}: {text}[/dim]"
            )
        if web_mode and _web_available:
            await broadcast_segment(segment)
        await asyncio.sleep(0.5)  # Simulate real-time arrival

