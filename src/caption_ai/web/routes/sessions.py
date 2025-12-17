"""Session management API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caption_ai.web.state import get_storage

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions(limit: int = 200) -> JSONResponse:
    """List all sessions with metadata (title, pinned, model, etc.)."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        # Ensure storage is initialized
        await storage.init()
        
        sessions = await storage.list_sessions(limit=limit)
        return JSONResponse({"sessions": sessions, "count": len(sessions)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """Get session metadata by ID."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        session = await storage.get_session(session_id)
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        return JSONResponse(session)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    pinned: bool | None = None
    model: str | None = None


@router.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdateRequest) -> JSONResponse:
    """Update session metadata (title, pinned status, model)."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        updates = {}
        if request.title is not None:
            updates["title"] = request.title
        if request.pinned is not None:
            updates["pinned"] = 1 if request.pinned else 0
        if request.model is not None:
            updates["model"] = request.model
        
        if not updates:
            return JSONResponse({"error": "No updates provided"}, status_code=400)
        
        await storage.update_session(session_id, **updates)
        session = await storage.get_session(session_id)
        return JSONResponse(session)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> JSONResponse:
    """Delete a session and all its messages."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        await storage.delete_session(session_id)
        return JSONResponse({"success": True, "message": f"Session {session_id} deleted"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/sessions/{session_id}/export")
async def export_session(session_id: str, format: str = "md") -> JSONResponse:
    """Export a session as Markdown or JSON."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        if format == "md":
            content = await storage.export_session_markdown(session_id)
            return JSONResponse({"content": content, "format": "markdown"})
        else:
            # JSON export
            session = await storage.get_session(session_id)
            conversations = await storage.get_conversation_history(session_id, limit=1000)
            export_data = {
                "session": session,
                "conversations": conversations,
            }
            import json
            return JSONResponse({
                "content": json.dumps(export_data, indent=2),
                "format": "json"
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

