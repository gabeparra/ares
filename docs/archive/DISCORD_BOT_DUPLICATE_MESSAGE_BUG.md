# Discord Bot Duplicate Message Bug

## Problem Description
The Discord bot sends **two different responses** to a single user message. The responses are different (from different LLM calls), arriving approximately 1 second apart.

Example:
```
User: @ARES AI test
Bot: Your message appears to be a test. How can I assist you today?
Bot: I'm ready! How can I assist you today? If you need any help with questions, information, or tasks, feel free to let me know.
```

## Key Findings from Logs

The backend log shows the orchestrator being called **twice** for a single message:

```
[DISCORD] Processing message via ORCHESTRATOR for user_id=discord:1408308379339853975
ares_core.orchestrator: Processing chat request...
[DISCORD] Processing message via ORCHESTRATOR for user_id=discord:1408308379339853975  <-- SECOND CALL
ares_core.orchestrator: Processing chat request...
```

And two different providers respond:
```
Successfully processed via orchestrator: provider=local, model=ares
Successfully processed via orchestrator: provider=openrouter, model=openai/gpt-4o-mini-2024-07-18
```

Also suspicious - two different database errors for the same lookup:
```
Error looking up Discord user: no such table: api_discordcredential  (SQLite)
Error looking up Discord user: relation "api_discordcredential" does not exist  (PostgreSQL)
```

## Confirmed Facts
- Only ONE Discord bot process running (`ps aux` shows single `run_discord_bot` process)
- Only ONE `on_message` event being triggered (single trace_id in logs)
- Only ONE `_process_discord_message` call logged
- But TWO orchestrator calls happening somehow
- No webhooks configured
- No other ARES instances on other machines
- Bot is only added to Discord server once
- Both messages come from the same bot name

## Attempted Fixes (None worked)

### 1. Message ID Deduplication
Added tracking of processed message IDs to prevent duplicate processing:
```python
_processed_messages = set()
if _is_message_processed(message.id):
    return  # Skip duplicate
```
**Result:** Did not fix - the issue happens before this check or bypasses it

### 2. Disabled Default Help Command
Changed from `commands.Bot` to include `help_command=None`:
```python
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
```
**Result:** Did not fix

### 3. Removed `bot.process_commands()` Calls
Removed all three calls to `bot.process_commands(message)` since commands are handled manually.
**Result:** Did not fix

### 4. Switched from `commands.Bot` to `discord.Client`
```python
bot = discord.Client(intents=intents)
```
**Result:** Did not fix

### 5. Added "Currently Processing" Check
Track messages that are currently being processed (not just completed):
```python
_processing_messages = set()
if message_id in _processing_messages:
    return  # Already being processed
```
**Result:** Did not fix

### 6. Added `thread_sensitive=False` to `@sync_to_async`
```python
@sync_to_async(thread_sensitive=False)
def _process_message_sync(...):
```
**Result:** Did not fix

### 7. Added Session-Level Locking
Added a lock per session to prevent concurrent orchestrator calls:
```python
_session_locks = {}
session_lock = _get_session_lock(session_id)
if not session_lock.acquire(blocking=False):
    return None, "Session already being processed"
```
**Result:** Did not fix (lock not being triggered, suggesting calls may be sequential not concurrent)

## Current State of Code
File: `/home/gabe/ares/api/discord_bot.py`

The code now has extensive logging with:
- Trace IDs for each message processing
- Thread ID and name logging
- Call IDs for each `_process_message_sync` invocation
- Session lock acquisition logging

## Theories to Investigate

### 1. Django `@sync_to_async` Issue
The `@sync_to_async` decorator might be somehow executing the function twice. The fact that we see SQLite and PostgreSQL errors suggests multiple database connections or contexts.

### 2. Multiple Database Connections
The gunicorn workers use PostgreSQL, while the Discord bot might be using SQLite. If there's some shared state or signal being triggered, both could be responding.

### 3. Django ORM Thread Safety
The Django ORM isn't fully thread-safe. The `sync_to_async` wrapper runs code in a thread pool, which might cause issues with database connections.

### 4. Event Loop / Thread Pool Interaction
The Discord bot runs in its own event loop inside a thread. The `sync_to_async` decorator creates additional threads. There might be some interaction causing duplicate execution.

### 5. Import Side Effects
When `from ares_core.orchestrator import orchestrator` is called inside the function, it might trigger some initialization code that causes duplicate behavior.

## Next Steps to Try

1. **Remove `@sync_to_async` entirely** - Run the orchestrator call in the main thread using `asyncio.to_thread()` instead

2. **Check if gunicorn is involved** - Stop gunicorn and test if duplicates still occur

3. **Add logging to orchestrator** - Add entry/exit logging to `process_chat_request` to see if it's being called twice

4. **Check for Django signals** - Look for any `post_save` or other signals that might trigger additional processing

5. **Simplify the Discord bot** - Create a minimal test bot that just echoes messages to isolate the issue

6. **Check environment variables** - Verify DATABASE_URL is set correctly for the Discord bot service

## Relevant Files
- `/home/gabe/ares/api/discord_bot.py` - Main Discord bot code
- `/home/gabe/ares/ares_core/orchestrator.py` - AI orchestrator
- `/home/gabe/ares/ares_project/settings.py` - Django settings (database config)
- `/etc/systemd/system/ares-discord-bot.service` - Systemd service file
- `/home/gabe/ares/.env` - Environment variables

## Commands for Debugging
```bash
# Restart the Discord bot
sudo systemctl restart ares-discord-bot

# Watch logs in real-time
sudo journalctl -u ares-discord-bot -f

# Check backend logs
tail -f /home/gabe/ares/logs/backend.log | grep -i discord

# Check for multiple processes
ps aux | grep discord
```
