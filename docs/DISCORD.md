# Discord Bot Setup - Enable Privileged Intents

## Issue: Bot Shows as Offline

The bot is failing to start because **privileged intents** need to be enabled in the Discord Developer Portal.

## Quick Fix

1. **Go to Discord Developer Portal:**
   - Visit: https://discord.com/developers/applications
   - Select your application (Client ID: 1460657376062345269)

2. **Enable Privileged Intents:**
   - Go to **Bot** section (left sidebar)
   - Scroll down to **Privileged Gateway Intents**
   - Enable these intents:
     - ✅ **MESSAGE CONTENT INTENT** (Required - allows bot to read message content)
     - ✅ **SERVER MEMBERS INTENT** (Optional - if you need member info)
     - ✅ **PRESENCE INTENT** (Optional - if you need presence info)

3. **Save Changes:**
   - Click **Save Changes** at the bottom

4. **Restart the Bot:**
   ```bash
   # If using systemd service:
   sudo systemctl restart ares-discord-bot
   
   # Or use the control script:
   ./scripts/control-discord-bot.sh restart
   
   # Or manually:
   python manage.py run_discord_bot --daemon
   ```

## Why This Is Needed

Discord requires explicit permission for bots to read message content. This is a security feature to prevent bots from accessing messages without permission.

## Verify It's Working

After enabling intents and restarting:

1. Check bot status:
   ```bash
   sudo systemctl status ares-discord-bot
   ```

2. Check logs:
   ```bash
   sudo journalctl -u ares-discord-bot -f
   ```

3. Look for this in logs:
   ```
   [DISCORD] Bot logged in as BotName (ID: 123456789)
   [DISCORD] Bot is in X guilds
   ```

4. In Discord, the bot should show as **online** (green dot)

## Troubleshooting

If the bot still shows offline after enabling intents:

1. **Verify intents are enabled:**
   - Go back to Developer Portal > Bot > Privileged Gateway Intents
   - Make sure "MESSAGE CONTENT INTENT" is checked

2. **Check bot token:**
   ```bash
   grep DISCORD_BOT_TOKEN /home/gabe/ares/.env
   ```

3. **Check logs for errors:**
   ```bash
   tail -50 /home/gabe/ares/logs/discord-bot-error.log
   ```

4. **Restart the service:**
   ```bash
   sudo systemctl restart ares-discord-bot
   ```

## Required Intents

The bot needs these intents:
- **MESSAGE CONTENT INTENT** - Required to read message content (for mentions and DMs)
- **GUILDS** - Default, always enabled
- **GUILD_MESSAGES** - Default, always enabled
- **DM_MESSAGES** - Default, always enabled



# Discord Bot Service Setup

This guide explains how to set up the Discord bot as a systemd service so it runs automatically and stays running.

## Quick Start

1. **Install the service:**
   ```bash
   sudo /home/gabe/ares/scripts/install-discord-bot-service.sh
   ```

2. **Start the service:**
   ```bash
   sudo systemctl start ares-discord-bot
   ```

3. **Check status:**
   ```bash
   sudo systemctl status ares-discord-bot
   ```

## Service Management

### Using the Control Script (Recommended)

```bash
# Start
./scripts/control-discord-bot.sh start

# Stop
./scripts/control-discord-bot.sh stop

# Restart
./scripts/control-discord-bot.sh restart

# Check status
./scripts/control-discord-bot.sh status

# View logs
./scripts/control-discord-bot.sh logs

# Follow logs in real-time
./scripts/control-discord-bot.sh follow

# Enable auto-start on boot
./scripts/control-discord-bot.sh enable

# Disable auto-start on boot
./scripts/control-discord-bot.sh disable
```

### Using systemctl Directly

```bash
# Start
sudo systemctl start ares-discord-bot

# Stop
sudo systemctl stop ares-discord-bot

# Restart
sudo systemctl restart ares-discord-bot

# Check status
sudo systemctl status ares-discord-bot

# Enable on boot
sudo systemctl enable ares-discord-bot

# Disable on boot
sudo systemctl disable ares-discord-bot

# View logs
sudo journalctl -u ares-discord-bot -f
```

### Using the Service Manager

The `manage-services.sh` script now includes Discord bot controls:

```bash
./manage-services.sh
```

Then select:
- `b` - Start Discord Bot
- `s` - Stop Discord Bot
- `r` - Restart Discord Bot
- `l` - View Discord Bot Logs

## Service Details

- **Service Name:** `ares-discord-bot`
- **Service File:** `/etc/systemd/system/ares-discord-bot.service`
- **Working Directory:** `/home/gabe/ares`
- **User:** `gabe`
- **Logs:** 
  - Standard output: `/home/gabe/ares/logs/discord-bot.log`
  - Standard error: `/home/gabe/ares/logs/discord-bot-error.log`
  - Systemd journal: `sudo journalctl -u ares-discord-bot`

## Auto-Restart

The service is configured with:
- `Restart=always` - Automatically restarts if it crashes
- `RestartSec=10` - Waits 10 seconds before restarting
- `WantedBy=multi-user.target` - Starts automatically on boot (if enabled)

## Troubleshooting

### Service won't start

1. Check if DISCORD_BOT_TOKEN is set in `.env`:
   ```bash
   grep DISCORD_BOT_TOKEN /home/gabe/ares/.env
   ```

2. Check service status:
   ```bash
   sudo systemctl status ares-discord-bot
   ```

3. Check logs:
   ```bash
   sudo journalctl -u ares-discord-bot -n 50
   ```

4. Check error logs:
   ```bash
   tail -50 /home/gabe/ares/logs/discord-bot-error.log
   ```

### Service keeps restarting

Check the logs to see why it's crashing:
```bash
sudo journalctl -u ares-discord-bot -n 100
```

Common issues:
- Missing DISCORD_BOT_TOKEN
- Database connection issues
- Python import errors

### Bot not responding

1. Verify the bot is running:
   ```bash
   sudo systemctl status ares-discord-bot
   ```

2. Check if the bot is online in Discord (should show as "ARES AI Assistant")

3. Check logs for errors:
   ```bash
   sudo journalctl -u ares-discord-bot -f
   ```

## Uninstalling

To remove the service:

```bash
sudo systemctl stop ares-discord-bot
sudo systemctl disable ares-discord-bot
sudo rm /etc/systemd/system/ares-discord-bot.service
sudo systemctl daemon-reload
```

