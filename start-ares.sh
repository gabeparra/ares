#!/bin/bash
# Wrapper script to start ARES with proper environment

cd /home/gabe/ares

# Try to use uv if available
if command -v uv &> /dev/null; then
    exec uv run python manage.py runserver 0.0.0.0:8000
fi

# Fall back to venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    exec python manage.py runserver 0.0.0.0:8000
fi

# Last resort: try system python
exec python3 manage.py runserver 0.0.0.0:8000
