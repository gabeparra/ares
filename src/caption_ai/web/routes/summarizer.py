"""Summarizer control API endpoints."""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caption_ai.web.state import (
    get_summarizer_running,
    set_summarizer_running,
    get_websocket_connections,
)

router = APIRouter()


@router.get("/api/summarizer/status")
async def get_summarizer_status() -> JSONResponse:
    """Get summarizer running status."""
    return JSONResponse({
        "running": get_summarizer_running(),
    })


class SummarizerToggleRequest(BaseModel):
    running: bool


@router.post("/api/summarizer/toggle")
async def toggle_summarizer(request: SummarizerToggleRequest) -> JSONResponse:
    """Toggle summarizer on/off."""
    try:
        new_state = request.running
        set_summarizer_running(new_state)
        
        # Broadcast to all WebSocket connections
        message = json.dumps({
            "type": "summarizer_state",
            "running": new_state,
        })
        disconnected = []
        websocket_connections = get_websocket_connections()
        for connection in websocket_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in websocket_connections:
                websocket_connections.remove(conn)
        
        return JSONResponse({
            "success": True,
            "running": new_state,
            "message": f"Summarizer {'started' if new_state else 'paused'}",
        })
    except Exception as e:
        return JSONResponse({
            "error": f"Failed to toggle summarizer: {str(e)}"
        }, status_code=500)

