# ARES Service Setup

## Prerequisites

Before setting up the systemd service, ensure you have the required packages:

```bash
sudo apt install python3.10-venv
```

Or install `uv` (recommended):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup Steps

1. **Install system dependencies (if using venv):**
   ```bash
   sudo apt install python3.10-venv
   ```

2. **Setup the service environment:**
   ```bash
   ./setup-service-env.sh
   ```
   This will either:
   - Use `uv` if available (preferred)
   - Create a `.venv` virtual environment and install dependencies

3. **Install the systemd service:**
   ```bash
   sudo ./install-service.sh
   ```

4. **Start the service:**
   ```bash
   sudo systemctl start ares
   ```

5. **Check status:**
   ```bash
   sudo systemctl status ares
   ```

## Service Management

- **Start:** `sudo systemctl start ares`
- **Stop:** `sudo systemctl stop ares`
- **Restart:** `sudo systemctl restart ares`
- **Status:** `sudo systemctl status ares`
- **Logs:** `sudo journalctl -u ares -f`
- **Enable on boot:** `sudo systemctl enable ares` (done automatically by install script)
- **Disable on boot:** `sudo systemctl disable ares`

## Troubleshooting

If the service fails to start:

1. Check the logs:
   ```bash
   sudo journalctl -u ares -n 50
   ```

2. Verify dependencies are installed:
   ```bash
   ./setup-service-env.sh
   ```

3. Test the start script manually:
   ```bash
   ./start-ares.sh
   ```

