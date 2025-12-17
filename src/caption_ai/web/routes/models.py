"""Model management API endpoints."""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caption_ai.config import config
from caption_ai.web.llm_client import set_llm_client
from caption_ai.web.state import get_websocket_connections

router = APIRouter()


class ModelChangeRequest(BaseModel):
    model: str


@router.get("/api/models")
async def get_models() -> JSONResponse:
    """Get current model and list available models from Ollama."""
    try:
        import httpx
        
        # Get current model
        current_model = config.ollama_model
        
        # Fetch available models from Ollama
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config.ollama_base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                available_models = [model.get("name", "") for model in data.get("models", [])]
            else:
                available_models = []
        
        return JSONResponse({
            "current_model": current_model,
            "available_models": available_models,
            "models": available_models,
        })
    except Exception as e:
        return JSONResponse({
            "current_model": config.ollama_model,
            "available_models": [],
            "models": [],
            "error": str(e),
        }, status_code=500)


@router.post("/api/models")
async def set_model(request: ModelChangeRequest) -> JSONResponse:
    """Change the Ollama model."""
    try:
        import httpx
        
        new_model = request.model
        
        # Verify model exists in Ollama
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{config.ollama_base_url}/api/tags")
            if response.status_code != 200:
                return JSONResponse({
                    "error": "Cannot connect to Ollama. Make sure it's running."
                }, status_code=503)
            
            data = response.json()
            available_models = [model.get("name", "") for model in data.get("models", [])]
            
            if new_model not in available_models:
                return JSONResponse({
                    "error": f"Model '{new_model}' not found. Available models: {', '.join(available_models[:5])}"
                }, status_code=404)
        
        # Update config
        config.ollama_model = new_model
        
        # Reinitialize LLM client with new model
        set_llm_client(model=new_model)
        
        # Broadcast model change to all WebSocket connections
        message = json.dumps({"type": "model_changed", "model": new_model})
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
            "model": new_model,
            "message": f"Model changed to {new_model}",
        })
    except Exception as e:
        return JSONResponse({
            "error": f"Failed to change model: {str(e)}"
        }, status_code=500)

