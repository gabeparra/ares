"""Main orchestration logic for running the application."""

import asyncio
from threading import Thread

import uvicorn
from rich.console import Console

from caption_ai.bus import SegmentBus
from caption_ai.config import config
from caption_ai.storage import Storage
from caption_ai.summarizer import Summarizer
from caption_ai.web import app, broadcast_summary, set_storage, set_summarizer
from caption_ai.web_summarizer import WebSummarizer

console = Console()


async def main(web_mode: bool = False, web_port: int = 8000, reload: bool = False) -> None:
    """Main entrypoint."""
    console.print("[bold red]╔════════════════════════════════════════╗[/bold red]")
    console.print("[bold red]║[/bold red] [bold white]Glup - Advanced Meeting Intelligence[/bold white] [bold red]║[/bold red]")
    console.print("[bold red]╚════════════════════════════════════════╝[/bold red]")
    console.print("[dim]Initializing neural pathways...[/dim]")
    console.print(f"[dim]LLM Provider: {config.llm_provider}[/dim]")
    console.print(f"[dim]Model: {config.ollama_model if config.llm_provider == 'local' else 'API'}[/dim]")
    
    if web_mode:
        console.print(f"[dim]Web UI: http://127.0.0.1:{web_port}[/dim]")
    
    console.print("[dim]Analyzing conversation patterns...[/dim]\n")

    # Initialize components
    bus = SegmentBus()
    storage = Storage()
    await storage.init()

    # Setup web server if in web mode
    if web_mode:
        set_storage(storage)
        
        def run_server():
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=web_port,
                log_level="warning",
                reload=reload,
            )
        
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        console.print(f"[green]✓ Web server started on http://127.0.0.1:{web_port}[/green]\n")

    # Use WebSummarizer in web mode, regular Summarizer otherwise
    if web_mode:
        summarizer = WebSummarizer(bus, storage, summary_interval_seconds=15)
        set_summarizer(summarizer)
    else:
        summarizer = Summarizer(bus, storage, summary_interval_seconds=15)

    # Start summarizer in background
    summarizer_task = asyncio.create_task(summarizer.run())

    if web_mode:
        console.print("[green]✓ Glup is running. Open http://127.0.0.1:{web_port} in your browser.[/green]")
        console.print("[dim]Press Ctrl+C to stop...[/dim]\n")
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            summarizer_task.cancel()
            try:
                await summarizer_task
            except asyncio.CancelledError:
                pass
            console.print("[green]Done![/green]")
    else:
        # Wait a bit for final summary
        await asyncio.sleep(5)

        # Stop summarizer
        summarizer_task.cancel()
        try:
            await summarizer_task
        except asyncio.CancelledError:
            pass

        console.print("[green]Done![/green]")

