# ARES Service Management

This directory contains scripts and configurations to manage ARES services without password prompts.

## Quick Start

1. **Install the sudoers configuration** (one-time setup):
   ```bash
   sudo ./scripts/install-service-sudoers.sh
   ```

2. **Restart services** (no password required):
   ```bash
   # Using the shell script
   ./scripts/restart-service.sh ares-backend
   
   # Using the Python script
   ./scripts/restart_service.py ares-backend
   
   # Or directly with sudo (no password needed)
   sudo systemctl restart ares-backend
   ```

## Available Services

- `ares-backend` - Django backend service
- `ares-discord-bot` - Discord bot service
- `ares-frontend-dev` - Frontend development server

## Security

The sudoers configuration (`/etc/sudoers.d/ares-services`) is restricted to:
- Only specific systemctl commands (restart, start, stop, status, reload)
- Only for the three ARES services listed above
- No wildcards or general systemctl access
- No ability to modify the sudoers file itself

This follows the principle of least privilege - only the minimum necessary permissions are granted.

## Files

- `sudoers-ares-services` - Sudoers configuration file
- `install-service-sudoers.sh` - Installation script
- `restart-service.sh` - Shell script wrapper
- `restart_service.py` - Python script wrapper

## Troubleshooting

If you get a password prompt:
1. Verify the sudoers file is installed: `ls -l /etc/sudoers.d/ares-services`
2. Check permissions: should be `0440` (read-only for root and group)
3. Verify syntax: `sudo visudo -c -f /etc/sudoers.d/ares-services`
4. Reinstall if needed: `sudo ./scripts/install-service-sudoers.sh`

## Adding New Services

To add a new service to the allowed list:

1. Edit `scripts/sudoers-ares-services` and add the new service commands
2. Update `ALLOWED_SERVICES` in `scripts/restart_service.py`
3. Update the case statement in `scripts/restart-service.sh`
4. Reinstall: `sudo ./scripts/install-service-sudoers.sh`

