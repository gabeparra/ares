"""
API views for Auth0 account linking.

These endpoints allow administrators to link multiple Auth0 identities
that share the same email address.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .auth import require_auth, Auth0Error
from .account_linking import (
    get_users_by_email,
    link_accounts,
    auto_link_by_email,
    get_user_identities,
)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def check_duplicate_accounts(request):
    """
    Check if there are multiple Auth0 accounts with the same email.
    
    Query params:
    - email: Email address to check
    """
    email = request.GET.get("email")
    
    if not email:
        # Use the current user's email
        email = request.auth0_user.get("email")
    
    if not email:
        return JsonResponse({"error": "Email required"}, status=400)
    
    try:
        users = get_users_by_email(email)
        
        return JsonResponse({
            "email": email,
            "user_count": len(users),
            "has_duplicates": len(users) > 1,
            "users": [
                {
                    "user_id": u.get("user_id"),
                    "provider": u.get("user_id", "").split("|")[0] if "|" in u.get("user_id", "") else "unknown",
                    "name": u.get("name"),
                    "created_at": u.get("created_at"),
                    "last_login": u.get("last_login"),
                    "logins_count": u.get("logins_count", 0),
                }
                for u in users
            ]
        })
        
    except Auth0Error as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def link_user_accounts(request):
    """
    Link multiple Auth0 accounts with the same email.
    
    Body:
    {
        "email": "user@example.com",
        "preferred_provider": "google-oauth2"  // optional
    }
    
    Or for manual linking:
    {
        "primary_user_id": "google-oauth2|123",
        "secondary_user_id": "auth0|456",
        "secondary_provider": "auth0"
    }
    """
    try:
        data = json.loads(request.body)
        
        # Check if this is an auto-link request or manual link
        if "email" in data:
            email = data.get("email")
            preferred_provider = data.get("preferred_provider", "google-oauth2")
            
            result = auto_link_by_email(email, preferred_provider)
            return JsonResponse(result)
            
        elif "primary_user_id" in data and "secondary_user_id" in data:
            primary_id = data.get("primary_user_id")
            secondary_id = data.get("secondary_user_id")
            secondary_provider = data.get("secondary_provider")
            
            if not secondary_provider:
                secondary_provider = secondary_id.split("|")[0] if "|" in secondary_id else "auth0"
            
            result = link_accounts(primary_id, secondary_id, secondary_provider)
            return JsonResponse({
                "status": "linked",
                "primary_user": primary_id,
                "linked_account": secondary_id,
                "identities": result
            })
            
        else:
            return JsonResponse({
                "error": "Provide either 'email' for auto-linking or 'primary_user_id' and 'secondary_user_id' for manual linking"
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Auth0Error as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def my_identities(request):
    """
    Get all linked identities for the current user.
    """
    user_id = request.auth0_user.get("sub")
    
    if not user_id:
        return JsonResponse({"error": "User ID not found in token"}, status=400)
    
    try:
        result = get_user_identities(user_id)
        return JsonResponse(result)
        
    except Auth0Error as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

