"""Conversation-related API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from caption_ai.web.state import get_storage

router = APIRouter()


@router.get("/api/conversations")
async def get_conversations(session_id: str | None = None, limit: int = 50) -> JSONResponse:
    """Get conversation history."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        # Ensure storage is initialized
        await storage.init()
        
        if session_id:
            conversations = await storage.get_conversation_history(session_id, limit=limit)
        else:
            conversations = await storage.get_all_conversations(limit=limit)
        
        return JSONResponse({
            "conversations": conversations,
            "count": len(conversations),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/conversations/sessions")
async def get_conversation_sessions() -> JSONResponse:
    """Get list of conversation sessions (legacy endpoint - returns just session IDs)."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        sessions = await storage.get_conversation_sessions()
        return JSONResponse({"sessions": sessions, "count": len(sessions)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


class ConversationSearchRequest(BaseModel):
    query: str
    limit: int = 20


@router.post("/api/conversations/search")
async def search_conversations(request: ConversationSearchRequest) -> JSONResponse:
    """Search conversations."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)
    
    try:
        query = request.query.lower()
        limit = request.limit
        
        all_conversations = await storage.get_all_conversations(limit=200)
        results = []
        
        for conv in all_conversations:
            if query in conv["message"].lower():
                results.append(conv)
                if len(results) >= limit:
                    break
        
        return JSONResponse({
            "results": results,
            "count": len(results),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

