"""
User Manager API views for admin user management.

This module provides endpoints for:
- Listing all Auth0 users with admin access
- Viewing user details and linked identities
- Linking Telegram accounts to Auth0 users
- Managing Telegram chat connections
"""

import json
import logging
import requests
from urllib.parse import quote

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .auth import require_auth, get_management_api_token, Auth0Error
from .models import UserPreference, UserFact, ChatSession


logger = logging.getLogger(__name__)


def _get_auth0_users(page=0, per_page=50, search=None):
    """
    Get users from Auth0 Management API with pagination.
    
    Args:
        page: Page number (0-indexed)
        per_page: Number of users per page
        search: Optional search query (searches name, email)
    
    Returns:
        dict with users list and pagination info
    """
    try:
        token = get_management_api_token()
        domain = settings.AUTH0_DOMAIN
        
        url = f"https://{domain}/api/v2/users"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "page": page,
            "per_page": per_page,
            "include_totals": "true",
            "fields": "user_id,email,name,picture,created_at,last_login,logins_count,identities",
        }
        
        if search:
            # Search in name or email
            params["q"] = f'name:*{search}* OR email:*{search}*'
            params["search_engine"] = "v3"
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "users": data.get("users", []),
            "total": data.get("total", 0),
            "page": page,
            "per_page": per_page,
        }
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error getting Auth0 users: {e.response.status_code} - {e.response.text}")
        raise Auth0Error(f"Failed to get users: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting Auth0 users: {e}")
        raise Auth0Error(str(e))


def _get_telegram_links():
    """
    Get all Telegram-to-user links from preferences.
    
    Returns:
        dict mapping telegram_chat_id to user_id
    """
    links = UserPreference.objects.filter(
        preference_key__startswith="telegram_user_link_"
    ).values("preference_key", "preference_value")
    
    result = {}
    for link in links:
        # Extract telegram_chat_id from preference_key
        chat_id = link["preference_key"].replace("telegram_user_link_", "")
        result[chat_id] = link["preference_value"]
    
    return result


def _get_telegram_sessions():
    """
    Get all Telegram chat sessions.
    
    Returns:
        list of Telegram session info dicts
    """
    sessions = ChatSession.objects.filter(
        session_id__startswith="telegram_user_"
    ).order_by("-updated_at")
    
    result = []
    for session in sessions:
        # Extract chat_id from session_id
        # Format: telegram_user_{chat_id} or telegram_user_{chat_id}_{YYYY-MM-DD}
        session_id = session.session_id
        remainder = session_id.replace("telegram_user_", "", 1)
        
        # Check for date suffix
        parts = remainder.rsplit("_", 1)
        if len(parts) == 2 and len(parts[1]) == 10 and parts[1].count("-") == 2:
            chat_id = parts[0]
        else:
            chat_id = remainder
        
        # Check if already added (same chat_id, different date sessions)
        existing = next((r for r in result if r["chat_id"] == chat_id), None)
        if existing:
            # Update with more recent info if this session is newer
            if session.updated_at and (not existing.get("last_active") or 
                session.updated_at.isoformat() > existing["last_active"]):
                existing["last_active"] = session.updated_at.isoformat()
                existing["title"] = session.title or existing["title"]
            continue
        
        result.append({
            "chat_id": chat_id,
            "title": session.title or f"Telegram User {chat_id}",
            "session_id": session.session_id,
            "last_active": session.updated_at.isoformat() if session.updated_at else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        })
    
    return result


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def list_users(request):
    """
    List all Auth0 users with their Telegram links and activity.
    
    Query params:
    - page: Page number (default: 0)
    - per_page: Users per page (default: 50, max: 100)
    - search: Search query (optional)
    """
    try:
        page = int(request.GET.get("page", 0))
        per_page = min(int(request.GET.get("per_page", 50)), 100)
        search = request.GET.get("search", "").strip() or None
        
        # Get Auth0 users
        auth0_data = _get_auth0_users(page=page, per_page=per_page, search=search)
        
        # Get Telegram links
        telegram_links = _get_telegram_links()
        
        # Reverse lookup: user_id -> telegram_chat_ids
        user_telegram_map = {}
        for chat_id, user_id in telegram_links.items():
            if user_id not in user_telegram_map:
                user_telegram_map[user_id] = []
            user_telegram_map[user_id].append(chat_id)
        
        # Enrich user data with Telegram info
        users = []
        for user in auth0_data.get("users", []):
            user_id = user.get("user_id", "")
            
            # Get linked Telegram accounts
            linked_telegram_ids = user_telegram_map.get(user_id, [])
            
            # Get identity providers
            identities = user.get("identities", [])
            providers = [i.get("provider", "unknown") for i in identities]
            
            users.append({
                "user_id": user_id,
                "email": user.get("email"),
                "name": user.get("name"),
                "picture": user.get("picture"),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login"),
                "logins_count": user.get("logins_count", 0),
                "providers": providers,
                "identity_count": len(identities),
                "telegram_chat_ids": linked_telegram_ids,
            })
        
        return JsonResponse({
            "users": users,
            "total": auth0_data.get("total", 0),
            "page": page,
            "per_page": per_page,
        })
        
    except Auth0Error as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def list_telegram_users(request):
    """
    List all Telegram users (from chat sessions) with their links.
    
    Returns Telegram users that have chatted with ARES, along with
    their linked Auth0 accounts if any.
    """
    try:
        # Get all Telegram sessions
        telegram_sessions = _get_telegram_sessions()
        
        # Get Telegram links
        telegram_links = _get_telegram_links()
        
        # Enrich with link info
        result = []
        for session in telegram_sessions:
            chat_id = session["chat_id"]
            linked_user_id = telegram_links.get(chat_id)
            
            result.append({
                **session,
                "linked_user_id": linked_user_id,
                "is_linked": linked_user_id is not None,
            })
        
        return JsonResponse({
            "telegram_users": result,
            "total": len(result),
        })
        
    except Exception as e:
        logger.error(f"Error listing Telegram users: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def link_telegram_account(request):
    """
    Link a Telegram chat_id to an Auth0 user_id.
    
    Body:
    {
        "telegram_chat_id": "123456789",
        "user_id": "google-oauth2|123456"
    }
    """
    try:
        data = json.loads(request.body)
        telegram_chat_id = data.get("telegram_chat_id", "").strip()
        user_id = data.get("user_id", "").strip()
        
        if not telegram_chat_id:
            return JsonResponse({"error": "telegram_chat_id is required"}, status=400)
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)
        
        # Create/update the link
        pref_key = f"telegram_user_link_{telegram_chat_id}"
        preference, created = UserPreference.objects.update_or_create(
            preference_key=pref_key,
            defaults={
                "preference_value": user_id,
                "user_id": user_id,
            }
        )
        
        logger.info(f"Linked Telegram {telegram_chat_id} to user {user_id}")
        
        return JsonResponse({
            "success": True,
            "created": created,
            "telegram_chat_id": telegram_chat_id,
            "user_id": user_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error linking Telegram account: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def unlink_telegram_account(request):
    """
    Unlink a Telegram chat_id from its Auth0 user.
    
    Body:
    {
        "telegram_chat_id": "123456789"
    }
    """
    try:
        data = json.loads(request.body)
        telegram_chat_id = data.get("telegram_chat_id", "").strip()
        
        if not telegram_chat_id:
            return JsonResponse({"error": "telegram_chat_id is required"}, status=400)
        
        # Delete the link
        pref_key = f"telegram_user_link_{telegram_chat_id}"
        deleted_count, _ = UserPreference.objects.filter(preference_key=pref_key).delete()
        
        logger.info(f"Unlinked Telegram {telegram_chat_id}")
        
        return JsonResponse({
            "success": True,
            "deleted": deleted_count > 0,
            "telegram_chat_id": telegram_chat_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error unlinking Telegram account: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def get_user_details(request, user_id):
    """
    Get detailed information about a specific user.
    
    Includes:
    - Auth0 user info
    - Linked identities
    - Linked Telegram accounts
    - User facts and preferences stored in ARES
    """
    try:
        token = get_management_api_token()
        domain = settings.AUTH0_DOMAIN
        
        # Get user from Auth0
        encoded_user_id = quote(user_id, safe='')
        url = f"https://{domain}/api/v2/users/{encoded_user_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        auth0_user = response.json()
        
        # Get Telegram links for this user
        telegram_links = []
        links = UserPreference.objects.filter(
            preference_key__startswith="telegram_user_link_",
            preference_value=user_id
        )
        for link in links:
            chat_id = link.preference_key.replace("telegram_user_link_", "")
            telegram_links.append(chat_id)
        
        # Get ARES user facts
        facts = list(UserFact.objects.filter(user_id=user_id).values(
            "id", "fact_type", "fact_key", "fact_value", "source", "confidence", "updated_at"
        ))
        
        # Get ARES user preferences
        preferences = list(UserPreference.objects.filter(user_id=user_id).values(
            "id", "preference_key", "preference_value", "updated_at"
        ))
        
        return JsonResponse({
            "user_id": auth0_user.get("user_id"),
            "email": auth0_user.get("email"),
            "name": auth0_user.get("name"),
            "picture": auth0_user.get("picture"),
            "created_at": auth0_user.get("created_at"),
            "last_login": auth0_user.get("last_login"),
            "logins_count": auth0_user.get("logins_count", 0),
            "identities": auth0_user.get("identities", []),
            "telegram_chat_ids": telegram_links,
            "ares_facts": facts,
            "ares_preferences": preferences,
        })
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return JsonResponse({"error": "User not found"}, status=404)
        logger.error(f"HTTP error getting user details: {e.response.status_code} - {e.response.text}")
        return JsonResponse({"error": f"Failed to get user: {e.response.text}"}, status=500)
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def set_telegram_nickname(request):
    """
    Set a nickname for a Telegram user for easier identification.
    
    This stores a preference that maps a nickname to a Telegram chat_id,
    allowing ARES to send messages using the nickname.
    
    Body:
    {
        "telegram_chat_id": "123456789",
        "nickname": "gabu"
    }
    """
    try:
        data = json.loads(request.body)
        telegram_chat_id = data.get("telegram_chat_id", "").strip()
        nickname = data.get("nickname", "").strip().lower()
        
        if not telegram_chat_id:
            return JsonResponse({"error": "telegram_chat_id is required"}, status=400)
        if not nickname:
            return JsonResponse({"error": "nickname is required"}, status=400)
        
        # Store nickname -> chat_id mapping
        pref_key = f"telegram_chat_id_{nickname}"
        preference, created = UserPreference.objects.update_or_create(
            user_id="default",
            preference_key=pref_key,
            defaults={"preference_value": telegram_chat_id}
        )
        
        logger.info(f"Set Telegram nickname '{nickname}' for chat_id {telegram_chat_id}")
        
        return JsonResponse({
            "success": True,
            "created": created,
            "nickname": nickname,
            "telegram_chat_id": telegram_chat_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error setting Telegram nickname: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def get_telegram_nicknames(request):
    """
    Get all Telegram nicknames and their chat_ids.
    """
    try:
        nicknames = UserPreference.objects.filter(
            preference_key__startswith="telegram_chat_id_"
        ).values("preference_key", "preference_value")
        
        result = []
        for pref in nicknames:
            nickname = pref["preference_key"].replace("telegram_chat_id_", "")
            result.append({
                "nickname": nickname,
                "chat_id": pref["preference_value"],
            })
        
        return JsonResponse({"nicknames": result})
        
    except Exception as e:
        logger.error(f"Error getting Telegram nicknames: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth
def delete_telegram_nickname(request, nickname):
    """
    Delete a Telegram nickname.
    """
    try:
        pref_key = f"telegram_chat_id_{nickname.lower()}"
        deleted_count, _ = UserPreference.objects.filter(
            user_id="default",
            preference_key=pref_key
        ).delete()
        
        return JsonResponse({
            "success": True,
            "deleted": deleted_count > 0,
            "nickname": nickname,
        })
        
    except Exception as e:
        logger.error(f"Error deleting Telegram nickname: {e}")
        return JsonResponse({"error": str(e)}, status=500)

