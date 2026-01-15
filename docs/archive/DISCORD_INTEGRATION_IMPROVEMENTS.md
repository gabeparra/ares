# Discord Integration Improvements

## Executive Summary

The current Discord integration is functional but has several reliability, security, and maintainability concerns. This document outlines the issues found and provides actionable recommendations to make the bot stable and production-ready.

---

## Current Architecture Overview

### Components
- **Bot Core**: `api/discord_bot.py` - Main bot logic using discord.py
- **API Views**: `api/discord_views.py` - REST endpoints for OAuth2 and status
- **Management Command**: `api/management/commands/run_discord_bot.py` - Django command to run bot
- **Frontend**: `src/components/controls/DiscordStatus.jsx` and `DiscordStatusCompact.jsx`
- **Model**: `DiscordCredential` in `api/models.py` - Stores OAuth tokens

### How It Works
1. Bot runs in a daemon thread with its own asyncio event loop
2. Responds to mentions (`@Bot`) and DMs
3. Creates daily sessions per user/channel: `discord_user_{user_id}_{channel_id}_{YYYY-MM-DD}`
4. Processes messages through the ARES orchestrator
5. OAuth2 flow allows users to link Discord accounts to their Auth0 identity

---

## Critical Issues

### 1. Race Condition in Connection Status
**Location**: `discord_bot.py:494-533`

**Problem**: The `_bot_ready` flag is accessed from multiple threads without synchronization.

**Current Code**:
```python
_bot_ready = False  # Global flag, no lock

def on_ready():
    global _bot_ready
    _bot_ready = True  # Set from bot thread

def is_discord_bot_running():
    return _bot_ready  # Read from main thread
```

**Fix**:
```python
import threading

_bot_ready_lock = threading.Lock()
_bot_ready = False

def set_bot_ready(value: bool):
    global _bot_ready
    with _bot_ready_lock:
        _bot_ready = value

def is_bot_ready() -> bool:
    with _bot_ready_lock:
        return _bot_ready
```

---

### 2. No Automatic Restart on Failure
**Location**: `discord_bot.py:372-413`

**Problem**: If the bot thread crashes due to network failure or exception, it never restarts. The `start_discord_bot()` function only attempts once.

**Current Code**:
```python
def _run_bot_thread():
    try:
        _bot_loop.run_until_complete(bot.start(token))
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        _bot_loop.close()  # Thread dies here
```

**Fix**: Implement retry with exponential backoff:
```python
MAX_RETRIES = 5
BASE_DELAY = 5  # seconds

def _run_bot_thread():
    retries = 0
    while retries < MAX_RETRIES:
        try:
            _bot_loop.run_until_complete(bot.start(token))
        except Exception as e:
            retries += 1
            delay = BASE_DELAY * (2 ** retries)
            logger.error(f"Bot error (attempt {retries}): {e}. Retrying in {delay}s")
            time.sleep(delay)
        else:
            break  # Clean exit

    if retries >= MAX_RETRIES:
        logger.critical("Bot failed after max retries")
```

---

### 3. No Rate Limiting on Message Processing
**Location**: `discord_bot.py:246-364`

**Problem**: Users can spam messages and exhaust AI API quota with no protection.

**Fix**: Add per-user rate limiting:
```python
from collections import defaultdict
import time

_user_last_message = defaultdict(float)
RATE_LIMIT_SECONDS = 2.0

async def on_message(message):
    user_id = str(message.author.id)
    now = time.time()

    if now - _user_last_message[user_id] < RATE_LIMIT_SECONDS:
        await message.reply("Please wait a moment before sending another message.")
        return

    _user_last_message[user_id] = now
    # Continue processing...
```

---

### 4. Missing Intent Validation
**Location**: `discord_bot.py:200-206`

**Problem**: Bot assumes MESSAGE_CONTENT intent is enabled but can't verify at runtime. If not enabled, the bot silently fails to read message content.

**Fix**: Add validation in `on_ready()`:
```python
@bot.event
async def on_ready():
    if not bot.intents.message_content:
        logger.critical("MESSAGE_CONTENT intent not enabled! Bot cannot read messages.")
        await bot.close()
        return

    logger.info(f"Bot connected as {bot.user} with MESSAGE_CONTENT intent enabled")
```

---

### 5. Broad Exception Handling
**Location**: `discord_bot.py:84-98, 135-142`

**Problem**: Generic `except Exception` blocks hide bugs and make debugging difficult.

**Current Code**:
```python
try:
    # processing
except Exception as e:
    logger.error(f"Error: {e}")
    pass  # Silent failure
```

**Fix**: Catch specific exceptions:
```python
try:
    # processing
except discord.errors.Forbidden as e:
    logger.error(f"Permission denied: {e}")
    await message.reply("I don't have permission to do that.")
except discord.errors.HTTPException as e:
    logger.error(f"Discord API error: {e}")
    await message.reply("Discord API error. Please try again.")
except OrchestratorError as e:
    logger.error(f"Processing error: {e}")
    await message.reply("I couldn't process your message. Please try again.")
```

---

## High Severity Issues

### 6. Status Check Doesn't Verify Actual Connection
**Location**: `discord_bot.py:521-532`

**Problem**: Status relies on internal flags, not actual Discord connection state.

**Fix**: Add comprehensive status checking:
```python
def get_discord_bot_status() -> dict:
    """Return detailed bot status."""
    global _bot_instance, _bot_ready, _bot_ready_timestamp

    status = {
        "running": False,
        "connected": False,
        "ready": False,
        "uptime_seconds": None,
        "guilds": 0,
        "latency_ms": None,
        "last_error": None
    }

    if _bot_instance is None:
        return status

    status["running"] = _bot_ready

    try:
        status["connected"] = not _bot_instance.is_closed()
        status["ready"] = _bot_instance.is_ready()
        status["guilds"] = len(_bot_instance.guilds)
        status["latency_ms"] = round(_bot_instance.latency * 1000, 2)

        if _bot_ready_timestamp:
            status["uptime_seconds"] = int(time.time() - _bot_ready_timestamp)
    except Exception as e:
        status["last_error"] = str(e)

    return status
```

---

### 7. Frontend Polling Too Slow
**Location**: `DiscordStatus.jsx:16-17`, `DiscordStatusCompact.jsx:16-17`

**Problem**: Status polls every 60 seconds - too slow for real-time feedback.

**Fix**: Reduce interval and add refresh on user action:
```javascript
// Change from 60000 to 10000 (10 seconds)
const STATUS_POLL_INTERVAL = 10000;

// Add manual refresh capability
const refreshStatus = useCallback(() => {
  fetchStatus();
}, []);
```

---

### 8. Duplicate Frontend Components
**Location**: `DiscordStatus.jsx` and `DiscordStatusCompact.jsx`

**Problem**: ~95% identical code duplicated across two components.

**Fix**: Create shared hook:
```javascript
// hooks/useDiscordStatus.js
export function useDiscordStatus(pollInterval = 10000) {
  const [status, setStatus] = useState({ running: false, loading: true });

  useEffect(() => {
    const fetchStatus = async () => {
      const response = await api.get('/discord/status/');
      setStatus({ ...response.data, loading: false });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  return status;
}
```

---

## Status Checker Implementation

### Backend Health Check Endpoint

Add a dedicated health check that verifies actual Discord connectivity:

```python
# api/discord_views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def discord_health_check(request):
    """Comprehensive health check for Discord bot."""
    from api.discord_bot import get_discord_bot_status

    status = get_discord_bot_status()

    # Determine overall health
    if status["running"] and status["connected"] and status["ready"]:
        health = "healthy"
        http_status = 200
    elif status["running"]:
        health = "degraded"
        http_status = 200
    else:
        health = "unhealthy"
        http_status = 503

    return Response({
        "health": health,
        "details": status,
        "timestamp": timezone.now().isoformat()
    }, status=http_status)
```

### Background Health Monitor

Add a background task that monitors bot health and restarts if needed:

```python
# api/discord_bot.py

import threading
import time

_health_monitor_thread = None
_health_monitor_running = False

def start_health_monitor():
    """Start background health monitoring."""
    global _health_monitor_thread, _health_monitor_running

    if _health_monitor_thread and _health_monitor_thread.is_alive():
        return

    _health_monitor_running = True
    _health_monitor_thread = threading.Thread(target=_health_monitor_loop, daemon=True)
    _health_monitor_thread.start()
    logger.info("Discord health monitor started")

def stop_health_monitor():
    global _health_monitor_running
    _health_monitor_running = False

def _health_monitor_loop():
    """Monitor bot health and restart if needed."""
    consecutive_failures = 0
    MAX_FAILURES = 3
    CHECK_INTERVAL = 30  # seconds

    while _health_monitor_running:
        time.sleep(CHECK_INTERVAL)

        status = get_discord_bot_status()

        if not status["running"] or not status["connected"]:
            consecutive_failures += 1
            logger.warning(f"Bot health check failed ({consecutive_failures}/{MAX_FAILURES})")

            if consecutive_failures >= MAX_FAILURES:
                logger.error("Bot unhealthy, attempting restart...")
                stop_discord_bot()
                time.sleep(5)
                start_discord_bot()
                consecutive_failures = 0
        else:
            consecutive_failures = 0
            logger.debug(f"Bot healthy: latency={status['latency_ms']}ms, guilds={status['guilds']}")
```

### Frontend Status Component

Improved status component with real-time updates:

```javascript
// components/controls/DiscordStatusPanel.jsx

import React, { useState, useEffect, useCallback } from 'react';
import { useDiscordStatus } from '../../hooks/useDiscordStatus';
import api from '../../services/api';

export function DiscordStatusPanel() {
  const status = useDiscordStatus(10000); // Poll every 10 seconds
  const [actionLoading, setActionLoading] = useState(false);

  const handleToggle = async () => {
    setActionLoading(true);
    try {
      if (status.running) {
        await api.post('/discord/stop/');
      } else {
        await api.post('/discord/start/');
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = () => {
    if (status.loading) return 'gray';
    if (status.running && status.connected) return 'green';
    if (status.running) return 'yellow';
    return 'red';
  };

  return (
    <div className="discord-status-panel">
      <div className="status-indicator" style={{ color: getStatusColor() }}>
        <span className="status-dot" />
        {status.loading ? 'Checking...' :
         status.running ? (status.connected ? 'Connected' : 'Connecting...') : 'Offline'}
      </div>

      {status.running && (
        <div className="status-details">
          <span>Guilds: {status.guilds}</span>
          <span>Latency: {status.latency_ms}ms</span>
          <span>Uptime: {formatUptime(status.uptime_seconds)}</span>
        </div>
      )}

      <button
        onClick={handleToggle}
        disabled={actionLoading || status.loading}
      >
        {status.running ? 'Stop Bot' : 'Start Bot'}
      </button>
    </div>
  );
}
```

---

## Implementation Priority

### Phase 1: Critical Fixes (Do First)
1. Add thread-safe state management with locks
2. Implement automatic restart with exponential backoff
3. Add rate limiting on message processing
4. Validate MESSAGE_CONTENT intent on startup
5. Replace broad exception handlers with specific ones

### Phase 2: Reliability Improvements
6. Implement comprehensive status endpoint
7. Add background health monitor with auto-restart
8. Reduce frontend polling interval to 10 seconds
9. Add connection latency monitoring
10. Implement graceful shutdown

### Phase 3: User Experience
11. Add informative error messages to users
12. Implement activity logging/metrics
13. Add new commands (`!status`, `!clear`, `!help`)
14. Create unified frontend status component

### Phase 4: Code Quality
15. Define constants for magic numbers
16. Consolidate duplicate frontend components
17. Add type hints throughout
18. Improve logging with structured context
19. Add unit tests for bot logic

---

## Configuration Constants

Add these to a constants file or settings:

```python
# api/discord_constants.py

# Discord API limits
DISCORD_MESSAGE_LIMIT = 2000
DISCORD_EMBED_LIMIT = 4096

# Bot behavior
BOT_READY_STABILITY_WINDOW = 2.0  # seconds
BOT_DISCONNECT_TIMEOUT = 3.0  # seconds
MESSAGE_PROCESSING_TIMEOUT = 30.0  # seconds

# Rate limiting
RATE_LIMIT_MESSAGES_PER_USER = 1
RATE_LIMIT_WINDOW_SECONDS = 2.0

# Health monitoring
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_CONSECUTIVE_FAILURES = 3
RESTART_DELAY_SECONDS = 5

# Retry configuration
MAX_START_RETRIES = 5
BASE_RETRY_DELAY = 5  # seconds
```

---

## Monitoring Recommendations

### Metrics to Track
- Bot uptime percentage
- Message processing latency (p50, p95, p99)
- Messages processed per hour
- Error rate by type
- Active users per day
- API quota usage

### Alerts to Set Up
- Bot disconnected for > 5 minutes
- Message processing latency > 10 seconds
- Error rate > 5% in 15 minutes
- API quota > 80% of daily limit

---

## Conclusion

The Discord integration needs reliability improvements before it can be considered production-ready. The most critical issues are:

1. **Thread safety** - Race conditions can cause inconsistent state
2. **No auto-restart** - Single failure kills the bot permanently
3. **No rate limiting** - Users can exhaust API quota
4. **Silent failures** - Missing intents cause silent message drops

Addressing Phase 1 items will significantly improve stability. The health monitor and improved status checking in Phase 2 will provide visibility into bot health and automatic recovery from failures.
