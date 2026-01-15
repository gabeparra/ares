#!/bin/bash
# Install sudoers configuration for ARES service management
# This allows restarting services without password prompts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUDOERS_FILE="$SCRIPT_DIR/sudoers-ares-services"
TARGET_FILE="/etc/sudoers.d/ares-services"

echo "Installing ARES service sudoers configuration..."
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    exit 1
fi

# Check if source file exists
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "Error: Source file not found: $SUDOERS_FILE"
    exit 1
fi

# Copy the sudoers file
echo "Copying sudoers configuration..."
cp "$SUDOERS_FILE" "$TARGET_FILE"

# Set correct permissions (sudoers files must be 0440)
chmod 0440 "$TARGET_FILE"

# Verify syntax
echo "Verifying sudoers syntax..."
if visudo -c -f "$TARGET_FILE"; then
    echo ""
    echo "✓ Sudoers configuration installed successfully!"
    echo ""
    echo "You can now restart services without password:"
    echo "  sudo systemctl restart ares-backend"
    echo "  sudo systemctl restart ares-discord-bot"
    echo "  sudo systemctl restart ares-frontend-dev"
    echo ""
    echo "Or use the helper script:"
    echo "  ./scripts/restart-service.sh ares-backend"
else
    echo ""
    echo "✗ Error: Sudoers syntax validation failed!"
    echo "Removing invalid configuration..."
    rm -f "$TARGET_FILE"
    exit 1
fi

