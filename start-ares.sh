#!/bin/bash
# Wrapper script to start ARES with proper environment

cd /home/gabe/ares

# Try to use uv if available
if command -v uv &> /dev/null; then
    exec uv run python -m caption_ai --web --port 8000
fi

# Fall back to venv if it exists
if [ -d ".venv" ]; then
    export PYTHONPATH=/home/gabe/ares/src
    exec .venv/bin/python -m caption_ai --web --port 8000
fi

# Last resort: try system python (will likely fail without deps)
export PYTHONPATH=/home/gabe/ares/src
exec python3 -m caption_ai --web --port 8000

