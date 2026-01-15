#!/bin/bash
# Helper script to restart ARES services without password
# Usage: ./scripts/restart-service.sh <service-name>
# Example: ./scripts/restart-service.sh ares-backend

set -e

SERVICE_NAME="$1"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name>"
    echo ""
    echo "Available services:"
    echo "  - ares-backend"
    echo "  - ares-discord-bot"
    echo "  - ares-frontend-dev"
    exit 1
fi

# Validate service name to prevent command injection
case "$SERVICE_NAME" in
    ares-backend|ares-discord-bot|ares-frontend-dev)
        echo "Restarting $SERVICE_NAME..."
        sudo systemctl restart "$SERVICE_NAME.service"
        echo "✓ $SERVICE_NAME restarted successfully"
        ;;
    *)
        echo "Error: Invalid service name '$SERVICE_NAME'"
        echo ""
        echo "Allowed services:"
        echo "  - ares-backend"
        echo "  - ares-discord-bot"
        echo "  - ares-frontend-dev"
        exit 1
        ;;
esac

