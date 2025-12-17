"""Broadcasting utilities for WebSocket connections."""

import json

from caption_ai.bus import Segment
from caption_ai.web.state import get_websocket_connections


async def broadcast_event(event: dict):
    """Generic event broadcaster for external integrations."""
    websocket_connections = get_websocket_connections()
    if not websocket_connections:
        return
    
    message = json.dumps(event)
    disconnected = []
    for connection in websocket_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)
    
    for conn in disconnected:
        if conn in websocket_connections:
            websocket_connections.remove(conn)


async def broadcast_summary(summary: str) -> None:
    """Broadcast new summary to all WebSocket connections."""
    websocket_connections = get_websocket_connections()
    if not websocket_connections:
        return

    message = json.dumps({"type": "summary", "summary": summary})
    disconnected = []

    for connection in websocket_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        if conn in websocket_connections:
            websocket_connections.remove(conn)


async def broadcast_segment(segment: Segment) -> None:
    """Broadcast new segment to all WebSocket connections."""
    websocket_connections = get_websocket_connections()
    if not websocket_connections:
        return

    message = json.dumps({
        "type": "segment",
        "segment": {
            "timestamp": segment.timestamp.isoformat(),
            "text": segment.text,
            "speaker": segment.speaker,
        },
    })
    disconnected = []

    for connection in websocket_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        if conn in websocket_connections:
            websocket_connections.remove(conn)

