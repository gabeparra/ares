"""
API views for user-initiated account linking.

These endpoints allow authenticated users (admins) to link local user accounts
with Auth0 accounts for unified access and data merging.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import require_auth, Auth0Error
from .user_account_linking import (
    get_linked_user_ids,
    resolve_primary_user_id,
    link_user_accounts,
    unlink_user_accounts,
    verify_link,
    get_user_links,
    get_linked_data_stats,
    get_all_links,
)
from .models import UserAccountLink

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def list_all_links(request):
    """
    List all account links in the system (admin only).
    
    Returns all links with their status and metadata.
    """
    try:
        links = get_all_links()
        
        return JsonResponse({
            "links": links,
            "total": len(links),
        })
        
    except Exception as e:
        logger.error(f"Error listing all links: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def my_account_links(request):
    """
    Get all account links for the current authenticated user.
    
    Returns links where the current user is either the local or Auth0 account.
    """
    try:
        user_id = request.auth0_user.get("sub")
        if not user_id:
            return JsonResponse({"error": "User ID not found in token"}, status=400)
        
        links = get_user_links(user_id)
        linked_ids = get_linked_user_ids(user_id)
        
        return JsonResponse({
            "user_id": user_id,
            "links": links,
            "all_linked_ids": linked_ids,
            "total": len(links),
        })
        
    except Exception as e:
        logger.error(f"Error getting user links: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def create_account_link(request):
    """
    Create a link between a local user account and an Auth0 account.
    
    Body:
    {
        "local_user_id": "telegram_user_123",
        "auth0_user_id": "google-oauth2|123456",  // optional, defaults to current user
        "notes": "Linked from Telegram",  // optional
        "auto_verify": true  // optional, defaults to true for admins
    }
    """
    try:
        data = json.loads(request.body)
        local_user_id = data.get("local_user_id", "").strip()
        
        if not local_user_id:
            return JsonResponse({"error": "local_user_id is required"}, status=400)
        
        # Get the current user as the linker and default auth0_user_id
        current_user_id = request.auth0_user.get("sub")
        if not current_user_id:
            return JsonResponse({"error": "User ID not found in token"}, status=400)
        
        # Allow specifying a different auth0_user_id (admin feature)
        auth0_user_id = data.get("auth0_user_id", "").strip() or current_user_id
        notes = data.get("notes", "").strip()
        auto_verify = data.get("auto_verify", True)  # Default to verified for admins
        
        # Create the link
        link = link_user_accounts(
            local_user_id=local_user_id,
            auth0_user_id=auth0_user_id,
            linked_by=current_user_id,
            notes=notes,
            auto_verify=auto_verify,
        )
        
        logger.info(f"Account link created: {local_user_id} -> {auth0_user_id} by {current_user_id}")
        
        return JsonResponse({
            "success": True,
            "link": {
                "id": link.id,
                "local_user_id": link.local_user_id,
                "auth0_user_id": link.auth0_user_id,
                "linked_by": link.linked_by,
                "verified": link.verified,
                "notes": link.notes,
                "created_at": link.created_at.isoformat(),
            }
        })
        
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error creating account link: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
@require_auth
def delete_account_link(request):
    """
    Remove a link between a local user account and an Auth0 account.
    
    Body:
    {
        "local_user_id": "telegram_user_123",
        "auth0_user_id": "google-oauth2|123456"
    }
    
    Or by link ID:
    {
        "link_id": 123
    }
    """
    try:
        data = json.loads(request.body)
        
        # Option 1: Delete by link ID
        link_id = data.get("link_id")
        if link_id:
            try:
                link = UserAccountLink.objects.get(id=link_id)
                local_user_id = link.local_user_id
                auth0_user_id = link.auth0_user_id
                link.delete()
                
                logger.info(f"Account link deleted by ID {link_id}: {local_user_id} -> {auth0_user_id}")
                
                return JsonResponse({
                    "success": True,
                    "deleted": True,
                    "local_user_id": local_user_id,
                    "auth0_user_id": auth0_user_id,
                })
            except UserAccountLink.DoesNotExist:
                return JsonResponse({"error": "Link not found"}, status=404)
        
        # Option 2: Delete by user_ids
        local_user_id = data.get("local_user_id", "").strip()
        auth0_user_id = data.get("auth0_user_id", "").strip()
        
        if not local_user_id or not auth0_user_id:
            return JsonResponse({
                "error": "Either link_id or both local_user_id and auth0_user_id are required"
            }, status=400)
        
        deleted = unlink_user_accounts(local_user_id, auth0_user_id)
        
        if deleted:
            logger.info(f"Account link deleted: {local_user_id} -> {auth0_user_id}")
        
        return JsonResponse({
            "success": True,
            "deleted": deleted,
            "local_user_id": local_user_id,
            "auth0_user_id": auth0_user_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error deleting account link: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def verify_account_link(request):
    """
    Mark an account link as verified.
    
    Body:
    {
        "local_user_id": "telegram_user_123",
        "auth0_user_id": "google-oauth2|123456"
    }
    
    Or by link ID:
    {
        "link_id": 123
    }
    """
    try:
        data = json.loads(request.body)
        
        # Option 1: Verify by link ID
        link_id = data.get("link_id")
        if link_id:
            try:
                link = UserAccountLink.objects.get(id=link_id)
                verified = verify_link(link.local_user_id, link.auth0_user_id)
                
                return JsonResponse({
                    "success": True,
                    "verified": verified,
                    "local_user_id": link.local_user_id,
                    "auth0_user_id": link.auth0_user_id,
                })
            except UserAccountLink.DoesNotExist:
                return JsonResponse({"error": "Link not found"}, status=404)
        
        # Option 2: Verify by user_ids
        local_user_id = data.get("local_user_id", "").strip()
        auth0_user_id = data.get("auth0_user_id", "").strip()
        
        if not local_user_id or not auth0_user_id:
            return JsonResponse({
                "error": "Either link_id or both local_user_id and auth0_user_id are required"
            }, status=400)
        
        verified = verify_link(local_user_id, auth0_user_id)
        
        return JsonResponse({
            "success": True,
            "verified": verified,
            "local_user_id": local_user_id,
            "auth0_user_id": auth0_user_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error verifying account link: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def get_linked_accounts(request):
    """
    Get all linked user_ids for a given user_id.
    
    Query params:
    - user_id: The user_id to look up (optional, defaults to current user)
    """
    try:
        user_id = request.GET.get("user_id")
        
        if not user_id:
            user_id = request.auth0_user.get("sub")
        
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)
        
        linked_ids = get_linked_user_ids(user_id)
        primary_id = resolve_primary_user_id(user_id)
        
        return JsonResponse({
            "user_id": user_id,
            "primary_user_id": primary_id,
            "linked_user_ids": linked_ids,
            "is_primary": user_id == primary_id,
        })
        
    except Exception as e:
        logger.error(f"Error getting linked accounts: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def get_link_data_stats(request):
    """
    Get statistics about data that would be merged for a user's linked accounts.
    
    Query params:
    - user_id: The user_id to check (optional, defaults to current user)
    """
    try:
        user_id = request.GET.get("user_id")
        
        if not user_id:
            user_id = request.auth0_user.get("sub")
        
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)
        
        stats = get_linked_data_stats(user_id)
        
        return JsonResponse({
            "user_id": user_id,
            "stats": stats,
        })
        
    except Exception as e:
        logger.error(f"Error getting link data stats: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def get_link_by_id(request, link_id):
    """
    Get details of a specific account link by ID.
    """
    try:
        link = UserAccountLink.objects.get(id=link_id)
        
        return JsonResponse({
            "id": link.id,
            "local_user_id": link.local_user_id,
            "auth0_user_id": link.auth0_user_id,
            "linked_by": link.linked_by,
            "verified": link.verified,
            "notes": link.notes,
            "created_at": link.created_at.isoformat(),
            "verified_at": link.verified_at.isoformat() if link.verified_at else None,
        })
        
    except UserAccountLink.DoesNotExist:
        return JsonResponse({"error": "Link not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting link by ID: {e}")
        return JsonResponse({"error": str(e)}, status=500)
