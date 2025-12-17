"""Segment-related API endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from caption_ai.web.state import get_storage

router = APIRouter()


@router.get("/api/segments")
async def get_segments(limit: int = 50) -> JSONResponse:
    """Get recent segments."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)

    segments = []
    async for segment in storage.fetch_recent(limit=limit):
        segments.append({
            "timestamp": segment.timestamp.isoformat(),
            "text": segment.text,
            "speaker": segment.speaker,
        })

    return JSONResponse({"segments": list(reversed(segments))})


@router.get("/api/summary")
async def get_summary() -> JSONResponse:
    """Get latest summary."""
    storage = get_storage()
    if not storage:
        return JSONResponse({"error": "Storage not initialized"}, status_code=500)

    summary = await storage.get_latest_summary()
    return JSONResponse({"summary": summary})

