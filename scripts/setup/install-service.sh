#!/bin/bash
# Script to install the ARES systemd service

set -e

SERVICE_FILE="ares.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "Installing ARES systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Setup service environment as the user
echo "Setting up service environment..."
sudo -u gabe /home/gabe/ares/setup-service-env.sh

# Copy service file
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
echo "Service file copied to $SYSTEMD_DIR/$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload
echo "Systemd daemon reloaded"

# Enable service to start on boot
systemctl enable ares.service
echo "Service enabled to start on boot"

echo ""
echo "Service installed successfully!"
echo ""
echo "To start the service now: sudo systemctl start ares"
echo "To check status: sudo systemctl status ares"
echo "To view logs: sudo journalctl -u ares -f"
echo "To stop: sudo systemctl stop ares"
echo "To disable auto-start: sudo systemctl disable ares"

