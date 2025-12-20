"""Settings management API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caption_ai.prompts import get_chat_system_prompt
from caption_ai.web.state import get_storage

router = APIRouter()


class PromptUpdateRequest(BaseModel):
    prompt: str


@router.get("/api/settings/prompt")
async def get_prompt() -> JSONResponse:
    """Get the current chat system prompt."""
    try:
        storage = get_storage()
        if storage:
            stored_prompt = await storage.get_setting("chat_system_prompt")
            if stored_prompt:
                return JSONResponse({"prompt": stored_prompt})
        
        # Fallback to default prompt
        default_prompt = get_chat_system_prompt()
        return JSONResponse({"prompt": default_prompt})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/settings/prompt")
async def set_prompt(request: PromptUpdateRequest) -> JSONResponse:
    """Update the chat system prompt."""
    try:
        storage = get_storage()
        if not storage:
            return JSONResponse({"error": "Storage not initialized"}, status_code=500)
        
        await storage.set_setting("chat_system_prompt", request.prompt)
        
        # Reload prompt on LLM client if it's a LocalOllamaClient
        from caption_ai.web.state import get_llm_client
        llm_client = get_llm_client()
        if llm_client and hasattr(llm_client, 'reload_prompt'):
            llm_client.reload_prompt(request.prompt)
        
        # Broadcast prompt change to all WebSocket connections
        import json
        from caption_ai.web.state import get_websocket_connections
        
        message = json.dumps({"type": "prompt_changed"})
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
            "message": "Prompt updated successfully",
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

