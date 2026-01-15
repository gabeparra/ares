"""
Discord integration views for ARES.

Handles OAuth authentication, connecting multiple Discord accounts, and managing Discord connections.
"""

from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
import json
import logging
import os
import requests
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs

from .models import DiscordCredential
from .auth import require_auth

logger = logging.getLogger(__name__)

# Discord OAuth 2.0 scopes
# See: https://discord.com/developers/docs/topics/oauth2#shared-resources-oauth2-scopes
DISCORD_SCOPES = [
    'identify',  # Get user info (username, avatar, etc.)
    'guilds',   # Get list of servers/guilds user is in
    'email',    # Get user email (optional, but useful)
]

# Discord OAuth endpoints
DISCORD_AUTHORIZE_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_USER_INFO_URL = 'https://discord.com/api/users/@me'
DISCORD_GUILDS_URL = 'https://discord.com/api/users/@me/guilds'

# OAuth redirect URI (should match what's configured in Discord Developer Portal)
REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:8000/api/v1/discord/oauth/callback')


def _refresh_discord_token(credential):
    """
    Refresh a Discord OAuth token if it's expired.
    
    Returns True if token was refreshed, False otherwise.
    """
    if not credential.refresh_token:
        return False
    
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("Discord OAuth credentials not configured")
        return False
    
    try:
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': credential.refresh_token,
        }
        
        response = requests.post(DISCORD_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update credential with new token
        credential.access_token = token_data['access_token']
        if 'refresh_token' in token_data:
            credential.refresh_token = token_data['refresh_token']
        
        expires_in = token_data.get('expires_in', 604800)  # Default 7 days
        credential.expires_at = timezone.now() + timedelta(seconds=expires_in)
        credential.save()
        
        logger.info(f"Refreshed Discord token for user {credential.user_id}, Discord user {credential.discord_user_id}")
        return True
    except Exception as e:
        logger.error(f"Error refreshing Discord token: {e}")
        return False


def _get_discord_user_info(access_token):
    """
    Get Discord user information using an access token.
    
    Returns dict with user info or None on error.
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        response = requests.get(DISCORD_USER_INFO_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Discord user info: {e}")
        return None


@require_http_methods(["GET"])
@require_auth
def discord_status(request):
    """
    Check Discord integration status for the current user.
    
    Returns list of all connected Discord accounts.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    try:
        credentials = DiscordCredential.objects.filter(user_id=user_id, enabled=True)
        
        connected_accounts = []
        for cred in credentials:
            # Check if token needs refresh
            if cred.expires_at and cred.expires_at <= timezone.now():
                _refresh_discord_token(cred)
            
            connected_accounts.append({
                "discord_user_id": cred.discord_user_id,
                "discord_username": cred.discord_username,
                "discord_discriminator": cred.discord_discriminator,
                "discord_avatar": cred.discord_avatar,
                "enabled": cred.enabled,
                "created_at": cred.created_at.isoformat() if cred.created_at else None,
                "last_sync_at": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
            })
        
        return JsonResponse({
            "connected": len(connected_accounts) > 0,
            "accounts": connected_accounts,
            "count": len(connected_accounts),
        })
    except Exception as e:
        logger.error(f"Error checking Discord status: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@require_auth
def discord_connect(request):
    """
    Initiate Discord OAuth flow.
    
    Redirects user to Discord OAuth consent screen.
    Returns authorization URL that the frontend should redirect to.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    # Get OAuth client credentials from environment
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return JsonResponse({
            "error": "Discord OAuth credentials not configured. Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET environment variables."
        }, status=400)
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state and user_id in session for callback
    request.session['discord_oauth_state'] = state
    request.session['discord_oauth_user_id'] = user_id
    
    # Build authorization URL
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(DISCORD_SCOPES),
        'state': state,
    }
    
    authorization_url = f"{DISCORD_AUTHORIZE_URL}?{urlencode(params)}"
    
    return JsonResponse({
        "authorization_url": authorization_url,
        "state": state,
    })


@require_http_methods(["GET"])
@csrf_exempt
def discord_oauth_callback(request):
    """
    Handle Discord OAuth callback.
    
    This endpoint should be accessible without authentication (csrf_exempt)
    as it's called by Discord's servers.
    """
    # Get state and user_id from session
    state = request.session.get('discord_oauth_state')
    user_id = request.session.get('discord_oauth_user_id', 'default')
    
    # Verify state
    if request.GET.get('state') != state:
        return JsonResponse({"error": "Invalid state parameter"}, status=400)
    
    # Check for error from Discord
    error = request.GET.get('error')
    if error:
        error_description = request.GET.get('error_description', 'Unknown error')
        return JsonResponse({
            "error": f"Discord OAuth error: {error}",
            "error_description": error_description
        }, status=400)
    
    # Get authorization code
    code = request.GET.get('code')
    if not code:
        return JsonResponse({"error": "No authorization code provided"}, status=400)
    
    # Get OAuth client credentials
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return JsonResponse({"error": "OAuth credentials not configured"}, status=500)
    
    # Exchange authorization code for token
    try:
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
        }
        
        response = requests.post(DISCORD_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 604800)  # Default 7 days
        token_type = token_data.get('token_type', 'Bearer')
        scopes = token_data.get('scope', '').split()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error exchanging Discord authorization code: {e}")
        return JsonResponse({"error": f"Failed to exchange authorization code: {str(e)}"}, status=400)
    
    # Get Discord user information
    user_info = _get_discord_user_info(access_token)
    if not user_info:
        return JsonResponse({"error": "Failed to fetch Discord user information"}, status=500)
    
    discord_user_id = str(user_info.get('id'))
    discord_username = user_info.get('username', '')
    discord_discriminator = user_info.get('discriminator', '')
    discord_avatar = user_info.get('avatar', '')
    
    # Calculate expiration time
    expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    
    # Store credentials (supporting multiple Discord accounts per user)
    credential, created = DiscordCredential.objects.update_or_create(
        user_id=user_id,
        discord_user_id=discord_user_id,
        defaults={
            'discord_username': discord_username,
            'discord_discriminator': discord_discriminator,
            'discord_avatar': discord_avatar,
            'access_token': access_token,
            'refresh_token': refresh_token or '',
            'token_type': token_type,
            'expires_at': expires_at,
            'scopes': scopes,
            'enabled': True,
        }
    )
    
    # Clean up session
    request.session.pop('discord_oauth_state', None)
    request.session.pop('discord_oauth_user_id', None)
    
    return JsonResponse({
        "success": True,
        "message": "Discord account connected successfully",
        "discord_user_id": discord_user_id,
        "discord_username": discord_username,
        "created": created,
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def discord_disconnect(request):
    """
    Disconnect a Discord account.
    
    Body:
    {
        "discord_user_id": "123456789012345678"  // Optional, if not provided, disconnects all
    }
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    try:
        data = json.loads(request.body) if request.body else {}
        discord_user_id = data.get('discord_user_id')
        
        if discord_user_id:
            # Disconnect specific Discord account
            try:
                cred = DiscordCredential.objects.get(user_id=user_id, discord_user_id=discord_user_id)
                cred.enabled = False
                cred.save()
                return JsonResponse({
                    "success": True,
                    "message": f"Discord account {discord_user_id} disconnected",
                    "discord_user_id": discord_user_id,
                })
            except DiscordCredential.DoesNotExist:
                return JsonResponse({"error": "Discord account not found"}, status=404)
        else:
            # Disconnect all Discord accounts for this user
            count = DiscordCredential.objects.filter(user_id=user_id, enabled=True).update(enabled=False)
            return JsonResponse({
                "success": True,
                "message": f"Disconnected {count} Discord account(s)",
                "count": count,
            })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error disconnecting Discord account: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@require_auth
def discord_accounts(request):
    """
    List all connected Discord accounts for the current user.
    
    Returns detailed information about each connected Discord account.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    try:
        credentials = DiscordCredential.objects.filter(user_id=user_id, enabled=True).order_by('-created_at')
        
        accounts = []
        for cred in credentials:
            # Check if token needs refresh
            if cred.expires_at and cred.expires_at <= timezone.now():
                _refresh_discord_token(cred)
            
            accounts.append({
                "discord_user_id": cred.discord_user_id,
                "discord_username": cred.discord_username,
                "discord_discriminator": cred.discord_discriminator,
                "discord_avatar": cred.discord_avatar,
                "enabled": cred.enabled,
                "scopes": cred.scopes,
                "created_at": cred.created_at.isoformat() if cred.created_at else None,
                "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
                "last_sync_at": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
                "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
            })
        
        return JsonResponse({
            "accounts": accounts,
            "count": len(accounts),
        })
    except Exception as e:
        logger.error(f"Error listing Discord accounts: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@require_auth
def discord_guilds(request):
    """
    Get list of Discord servers/guilds for a connected Discord account.
    
    Query parameters:
    - discord_user_id: Discord user ID (optional, uses first connected account if not provided)
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    discord_user_id = request.GET.get('discord_user_id')
    
    try:
        # Get credential
        if discord_user_id:
            try:
                cred = DiscordCredential.objects.get(user_id=user_id, discord_user_id=discord_user_id, enabled=True)
            except DiscordCredential.DoesNotExist:
                return JsonResponse({"error": "Discord account not found"}, status=404)
        else:
            # Use first connected account
            cred = DiscordCredential.objects.filter(user_id=user_id, enabled=True).first()
            if not cred:
                return JsonResponse({"error": "No Discord account connected"}, status=404)
        
        # Check if token needs refresh
        if cred.expires_at and cred.expires_at <= timezone.now():
            if not _refresh_discord_token(cred):
                return JsonResponse({"error": "Failed to refresh Discord token"}, status=500)
        
        # Fetch guilds
        headers = {
            'Authorization': f'{cred.token_type} {cred.access_token}',
        }
        
        response = requests.get(DISCORD_GUILDS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        guilds = response.json()
        
        return JsonResponse({
            "discord_user_id": cred.discord_user_id,
            "discord_username": cred.discord_username,
            "guilds": guilds,
            "count": len(guilds),
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Discord guilds: {e}")
        return JsonResponse({"error": f"Discord API error: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Error getting Discord guilds: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@require_auth
def discord_bot_status(request):
    """
    Check Discord bot status with detailed information.

    Returns:
    - running: bool - whether bot is considered running
    - connected: bool - whether bot is connected to Discord
    - ready: bool - whether bot has received on_ready event
    - configured: bool - whether bot token is configured
    - uptime_seconds: int or None - seconds since bot became ready
    - guilds: int - number of guilds bot is in
    - latency_ms: float or None - WebSocket latency to Discord
    - last_error: str or None - last error message
    - restart_count: int - number of times bot has been restarted
    - health_monitor_running: bool - whether health monitor is active
    """
    from .discord_bot import get_discord_bot_status, is_health_monitor_running

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    configured = bool(bot_token)

    if not configured:
        return JsonResponse({
            "running": False,
            "connected": False,
            "ready": False,
            "configured": False,
            "error": "DISCORD_BOT_TOKEN not configured"
        })

    status = get_discord_bot_status()
    status['configured'] = True
    status['health_monitor_running'] = is_health_monitor_running()

    return JsonResponse(status)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def discord_bot_start(request):
    """
    Start the Discord bot with optional health monitor.

    Body (optional):
    {
        "with_monitor": true  // Start with health monitor (default: true)
    }
    """
    from .discord_bot import (
        start_discord_bot,
        start_discord_bot_with_monitor,
        is_discord_bot_running,
        is_health_monitor_running,
    )

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        return JsonResponse({"error": "DISCORD_BOT_TOKEN not configured"}, status=400)

    if is_discord_bot_running():
        return JsonResponse({
            "success": True,
            "message": "Bot is already running",
            "running": True,
            "health_monitor_running": is_health_monitor_running(),
        })

    # Parse request body for options
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    with_monitor = data.get('with_monitor', True)

    if with_monitor:
        success = start_discord_bot_with_monitor()
        message = "Discord bot started with health monitor"
    else:
        success = start_discord_bot()
        message = "Discord bot started"

    if success:
        return JsonResponse({
            "success": True,
            "message": message,
            "running": True,
            "health_monitor_running": is_health_monitor_running(),
        })
    else:
        return JsonResponse({
            "success": False,
            "error": "Failed to start Discord bot",
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def discord_bot_stop(request):
    """
    Stop the Discord bot and health monitor.
    """
    from .discord_bot import stop_discord_bot_with_monitor

    success = stop_discord_bot_with_monitor()
    if success:
        return JsonResponse({
            "success": True,
            "message": "Discord bot and health monitor stopped",
            "running": False,
            "health_monitor_running": False,
        })
    else:
        return JsonResponse({
            "success": False,
            "error": "Bot was not running",
        }, status=400)


@require_http_methods(["GET"])
def discord_bot_health(request):
    """
    Health check endpoint for Discord bot.

    This endpoint is unauthenticated so it can be used by monitoring systems.

    Returns:
    - HTTP 200 if bot is healthy (running, connected, ready)
    - HTTP 503 if bot is unhealthy
    - HTTP 500 if bot is not configured
    """
    from .discord_bot import get_discord_bot_status

    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        return JsonResponse({
            "health": "unconfigured",
            "message": "DISCORD_BOT_TOKEN not configured",
        }, status=500)

    status = get_discord_bot_status()

    # Determine overall health
    if status['running'] and status['connected'] and status['ready']:
        health = "healthy"
        http_status = 200
    elif status['running']:
        health = "degraded"
        http_status = 200
    else:
        health = "unhealthy"
        http_status = 503

    return JsonResponse({
        "health": health,
        "details": status,
        "timestamp": timezone.now().isoformat(),
    }, status=http_status)


@require_http_methods(["GET"])
@require_auth
def discord_bot_invite(request):
    """
    Get Discord bot invite URL.
    
    Returns a URL that can be used to invite the bot to a Discord server.
    """
    client_id = os.getenv('DISCORD_CLIENT_ID')
    if not client_id:
        return JsonResponse({"error": "DISCORD_CLIENT_ID not configured"}, status=400)
    
    # Required permissions for the bot:
    # - Send Messages (2048)
    # - Read Message History (65536)
    # - View Channels (1024)
    # - Use External Emojis (262144)
    # - Add Reactions (64)
    # Total: 2048 + 65536 + 1024 + 262144 + 64 = 330816
    # But we'll use a simpler set: Send Messages + Read History + View Channels
    permissions = 2048 + 65536 + 1024  # Send Messages + Read History + View Channels
    
    # Discord OAuth2 authorize URL (correct format)
    # Note: Use /oauth2/authorize not /api/oauth2/authorize
    invite_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=bot%20applications.commands"
    
    return JsonResponse({
        "invite_url": invite_url,
        "client_id": client_id,
        "permissions": permissions,
        "permissions_hex": hex(permissions),
        "instructions": "Use this URL to invite the bot to your Discord server. You need 'Manage Server' permission on the server.",
        "permissions_breakdown": {
            "send_messages": 2048,
            "read_message_history": 65536,
            "view_channels": 1024,
            "total": permissions
        }
    })

