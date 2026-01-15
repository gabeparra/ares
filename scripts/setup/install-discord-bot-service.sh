#!/bin/bash
# Install Discord Bot as a systemd service

set -e

SERVICE_NAME="ares-discord-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="/home/gabe/ares"
USER="gabe"

echo "Installing Discord Bot systemd service..."

# Create systemd service file
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=ARES Discord Bot Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=/usr/bin/python3 ${PROJECT_DIR}/manage.py run_discord_bot --daemon
Restart=always
RestartSec=30
StandardOutput=append:${PROJECT_DIR}/logs/discord-bot.log
StandardError=append:${PROJECT_DIR}/logs/discord-bot-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create logs directory if it doesn't exist
mkdir -p "${PROJECT_DIR}/logs"
touch "${PROJECT_DIR}/logs/discord-bot.log"
touch "${PROJECT_DIR}/logs/discord-bot-error.log"
chown ${USER}:${USER} "${PROJECT_DIR}/logs/discord-bot.log"
chown ${USER}:${USER} "${PROJECT_DIR}/logs/discord-bot-error.log"

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ${SERVICE_NAME}

echo ""
echo "✓ Discord Bot service installed successfully!"
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "The service will start automatically on boot."
echo "To start it now, run: sudo systemctl start ${SERVICE_NAME}"

