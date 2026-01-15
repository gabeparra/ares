#!/usr/bin/env python3
"""
Helper script to restart ARES services without password.
Can be called directly or imported by other scripts.
"""
import subprocess
import sys
from pathlib import Path

ALLOWED_SERVICES = {
    'ares-backend',
    'ares-discord-bot',
    'ares-frontend-dev',
}

def restart_service(service_name: str) -> bool:
    """
    Restart a systemd service using sudo (without password prompt).
    
    Args:
        service_name: Name of the service (without .service suffix)
    
    Returns:
        True if successful, False otherwise
    """
    if service_name not in ALLOWED_SERVICES:
        print(f"Error: Invalid service name '{service_name}'", file=sys.stderr)
        print(f"Allowed services: {', '.join(sorted(ALLOWED_SERVICES))}", file=sys.stderr)
        return False
    
    try:
        # Use sudo with the specific systemctl command
        # The sudoers file allows this without password
        cmd = ['sudo', 'systemctl', 'restart', f'{service_name}.service']
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {service_name} restarted successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error restarting {service_name}: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return False

def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: restart_service.py <service-name>", file=sys.stderr)
        print(f"Available services: {', '.join(sorted(ALLOWED_SERVICES))}", file=sys.stderr)
        sys.exit(1)
    
    service_name = sys.argv[1]
    success = restart_service(service_name)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

