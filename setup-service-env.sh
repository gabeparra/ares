#!/bin/bash
# Setup script to ensure ARES service dependencies are available

set -e

cd /home/gabe/ares

echo "Setting up ARES service environment..."

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Found uv, syncing dependencies..."
    uv sync
    echo "Dependencies synced with uv"
    exit 0
fi

# Clean up failed venv if it exists but is broken
if [ -d ".venv" ] && [ ! -f ".venv/bin/python" ]; then
    echo "Removing broken .venv directory..."
    rm -rf .venv
fi

# Otherwise, create venv and install from requirements
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if ! python3 -m venv .venv 2>&1; then
        echo ""
        echo "ERROR: Failed to create virtual environment."
        echo "python3-venv is not installed."
        echo ""
        echo "Please install it with:"
        echo "  sudo apt install python3.10-venv"
        echo ""
        echo "Then run this script again."
        echo ""
        echo "Alternative: If you have uv installed, it will be used automatically."
        exit 1
    fi
fi

echo "Installing dependencies from requirements.txt..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# Also install dependencies from pyproject.toml (Django web server dependencies)
if [ -f "pyproject.toml" ]; then
    echo "Installing Django web server dependencies..."
    .venv/bin/pip install -q pydantic pydantic-settings python-dotenv httpx rich aiosqlite websockets
fi

echo "Service environment setup complete!"

