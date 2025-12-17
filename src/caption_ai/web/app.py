"""FastAPI application setup."""

from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from caption_ai.web.templates import get_default_html
from caption_ai.web.routes import (
    segments,
    health,
    code,
    conversations,
    sessions,
    models,
    summarizer,
    power_pet_door,
    telegram,
)
from caption_ai.web.websocket import websocket_endpoint


app = FastAPI(title="Glup - Advanced Meeting Intelligence")

# CORS middleware for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(segments.router)
app.include_router(health.router)
app.include_router(code.router)
app.include_router(conversations.router)
app.include_router(sessions.router)
app.include_router(models.router)
app.include_router(summarizer.router)
app.include_router(power_pet_door.router)
app.include_router(telegram.router)

# Serve static files from React build
static_path = Path(__file__).parent.parent.parent.parent / "web" / "dist"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=str(static_path / "assets")), name="assets")


@app.get("/", response_class=HTMLResponse)
async def get_index() -> str:
    """Serve the main UI."""
    # Check for built React app first
    built_html = Path(__file__).parent.parent.parent.parent / "web" / "dist" / "index.html"
    if built_html.exists():
        return built_html.read_text()
    
    # Fallback to default HTML
    html_path = Path(__file__).parent.parent.parent.parent / "web" / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return get_default_html()


@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket) -> None:
    """WebSocket endpoint handler."""
    await websocket_endpoint(websocket)

