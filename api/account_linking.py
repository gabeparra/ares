"""
Auth0 Account Linking utilities.

This module provides functions to link multiple Auth0 identities
(e.g., Google + email/password) that share the same email address.
"""

import logging
import requests
from django.conf import settings
from .auth import get_management_api_token, Auth0Error

logger = logging.getLogger(__name__)


def get_users_by_email(email):
    """
    Get all Auth0 users with a specific email address.
    
    Returns list of user objects, each potentially from a different connection
    (e.g., google-oauth2, auth0, etc.)
    """
    if not email:
        return []
    
    try:
        token = get_management_api_token()
        domain = settings.AUTH0_DOMAIN
        
        # Search for users by email
        url = f"https://{domain}/api/v2/users-by-email"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        params = {"email": email}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        users = response.json()
        logger.info(f"Found {len(users)} user(s) with email {email}")
        return users
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error getting users by email: {e.response.status_code} - {e.response.text}")
        raise Auth0Error(f"Failed to get users: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting users by email: {e}")
        raise Auth0Error(str(e))


def link_accounts(primary_user_id, secondary_user_id, secondary_provider, secondary_connection_id=None):
    """
    Link a secondary account to a primary account.
    
    After linking, the secondary user's identity will be merged into the primary.
    The secondary user will effectively cease to exist as a separate entity.
    
    Args:
        primary_user_id: The user_id to keep (e.g., "google-oauth2|123")
        secondary_user_id: The user_id to merge (e.g., "auth0|456")
        secondary_provider: The provider of the secondary (e.g., "auth0")
        secondary_connection_id: Optional connection-specific user_id
    """
    try:
        token = get_management_api_token()
        domain = settings.AUTH0_DOMAIN
        
        # Extract the numeric part of the secondary user_id
        # e.g., "auth0|12345" -> "12345"
        if "|" in secondary_user_id:
            user_id_part = secondary_user_id.split("|")[1]
        else:
            user_id_part = secondary_user_id
        
        from urllib.parse import quote
        encoded_primary_id = quote(primary_user_id, safe='')
        
        url = f"https://{domain}/api/v2/users/{encoded_primary_id}/identities"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "provider": secondary_provider,
            "user_id": user_id_part,
        }
        
        if secondary_connection_id:
            payload["connection_id"] = secondary_connection_id
        
        logger.info(f"Linking {secondary_user_id} to {primary_user_id}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 201:
            logger.info(f"Successfully linked accounts")
            return response.json()
        else:
            error_text = response.text
            logger.error(f"Failed to link accounts: {response.status_code} - {error_text}")
            raise Auth0Error(f"Failed to link accounts: {error_text}")
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error linking accounts: {e.response.status_code} - {e.response.text}")
        raise Auth0Error(f"Failed to link accounts: {e.response.text}")
    except Exception as e:
        logger.error(f"Error linking accounts: {e}")
        raise Auth0Error(str(e))


def auto_link_by_email(email, preferred_provider="google-oauth2"):
    """
    Automatically link all accounts with the same email.
    
    Finds all users with the given email and links them together,
    using the preferred provider's account as primary.
    
    Args:
        email: Email address to search for
        preferred_provider: Provider to use as primary (default: google-oauth2)
        
    Returns:
        dict with linking results
    """
    users = get_users_by_email(email)
    
    if len(users) <= 1:
        return {
            "status": "no_action",
            "message": f"Only {len(users)} user(s) found with email {email}",
            "users": [u.get("user_id") for u in users]
        }
    
    # Find primary user (prefer the specified provider)
    primary_user = None
    secondary_users = []
    
    for user in users:
        user_id = user.get("user_id", "")
        provider = user_id.split("|")[0] if "|" in user_id else "unknown"
        
        if provider == preferred_provider:
            primary_user = user
        else:
            secondary_users.append(user)
    
    # If no preferred provider found, use the first one as primary
    if not primary_user:
        primary_user = users[0]
        secondary_users = users[1:]
    
    primary_id = primary_user.get("user_id")
    results = {
        "status": "linked",
        "primary_user": primary_id,
        "linked_accounts": [],
        "errors": []
    }
    
    for secondary in secondary_users:
        secondary_id = secondary.get("user_id")
        
        if secondary_id == primary_id:
            continue
            
        provider = secondary_id.split("|")[0] if "|" in secondary_id else "unknown"
        
        try:
            link_accounts(primary_id, secondary_id, provider)
            results["linked_accounts"].append(secondary_id)
            logger.info(f"Linked {secondary_id} to {primary_id}")
        except Auth0Error as e:
            error_msg = f"Failed to link {secondary_id}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
    
    return results


def get_user_identities(user_id):
    """
    Get all linked identities for a user.
    
    Returns the user object with the 'identities' array showing
    all linked accounts.
    """
    try:
        token = get_management_api_token()
        domain = settings.AUTH0_DOMAIN
        
        from urllib.parse import quote
        encoded_user_id = quote(user_id, safe='')
        
        url = f"https://{domain}/api/v2/users/{encoded_user_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        user = response.json()
        return {
            "user_id": user.get("user_id"),
            "email": user.get("email"),
            "identities": user.get("identities", []),
            "identity_count": len(user.get("identities", []))
        }
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error getting user identities: {e.response.status_code} - {e.response.text}")
        raise Auth0Error(f"Failed to get user: {e.response.text}")
    except Exception as e:
        logger.error(f"Error getting user identities: {e}")
        raise Auth0Error(str(e))

