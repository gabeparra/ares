"""CLI entrypoint."""

import asyncio
import argparse

from caption_ai.runner import main


def cli() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Glup - Advanced Meeting Intelligence")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web UI server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web server port (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (development mode)",
    )
    
    args = parser.parse_args()
    asyncio.run(main(web_mode=args.web, web_port=args.port, reload=args.reload))


if __name__ == "__main__":
    cli()

