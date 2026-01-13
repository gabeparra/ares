"""
User Account Linking utilities.

This module provides functions to manage links between local user accounts
and Auth0 accounts, enabling data merging and unified access.
"""

import logging
from typing import List, Set, Optional, Dict, Any
from django.db.models import Q

from .models import (
    UserAccountLink,
    UserFact,
    UserPreference,
    ConversationSummary,
    MemorySpot,
    GoogleCalendarCredential,
    ScheduledTask,
)

logger = logging.getLogger(__name__)


def get_linked_user_ids(user_id: str, include_self: bool = True) -> List[str]:
    """
    Get all user_ids linked to a given user_id.
    
    This performs a bidirectional lookup - if the given user_id is either
    the local_user_id or auth0_user_id in a link, returns all connected IDs.
    
    Args:
        user_id: The user_id to look up
        include_self: Whether to include the input user_id in the result
        
    Returns:
        List of all linked user_ids
    """
    linked_ids: Set[str] = set()
    
    if include_self:
        linked_ids.add(user_id)
    
    # Find links where this user_id is the local_user_id
    links_as_local = UserAccountLink.objects.filter(local_user_id=user_id)
    for link in links_as_local:
        linked_ids.add(link.auth0_user_id)
    
    # Find links where this user_id is the auth0_user_id
    links_as_auth0 = UserAccountLink.objects.filter(auth0_user_id=user_id)
    for link in links_as_auth0:
        linked_ids.add(link.local_user_id)
    
    return list(linked_ids)


def resolve_primary_user_id(user_id: str) -> str:
    """
    Resolve a user_id to its primary (Auth0) user_id.
    
    If the given user_id is a local_user_id that's linked to an Auth0 account,
    returns the Auth0 user_id. Otherwise, returns the input user_id.
    
    Args:
        user_id: The user_id to resolve
        
    Returns:
        The primary (Auth0) user_id, or the input if not linked
    """
    # Check if this is a local_user_id linked to an Auth0 account
    link = UserAccountLink.objects.filter(local_user_id=user_id).first()
    if link:
        return link.auth0_user_id
    
    # If not found as local, return as-is (may already be Auth0 or unlinked)
    return user_id


def is_auth0_user_id(user_id: str) -> bool:
    """
    Check if a user_id appears to be an Auth0 user_id.
    
    Auth0 user_ids typically have the format "provider|id" (e.g., "google-oauth2|123").
    
    Args:
        user_id: The user_id to check
        
    Returns:
        True if it appears to be an Auth0 user_id
    """
    return "|" in user_id


def link_user_accounts(
    local_user_id: str,
    auth0_user_id: str,
    linked_by: str,
    notes: str = "",
    auto_verify: bool = False,
) -> UserAccountLink:
    """
    Create a link between a local user account and an Auth0 account.
    
    Args:
        local_user_id: The local user_id to link
        auth0_user_id: The Auth0 user_id to link to
        linked_by: The Auth0 user_id of the user creating the link
        notes: Optional notes about the link
        auto_verify: Whether to automatically verify the link
        
    Returns:
        The created UserAccountLink instance
        
    Raises:
        ValueError: If either user_id is invalid or link already exists
    """
    if not local_user_id or not auth0_user_id:
        raise ValueError("Both local_user_id and auth0_user_id are required")
    
    if local_user_id == auth0_user_id:
        raise ValueError("Cannot link a user_id to itself")
    
    # Check if link already exists
    existing = UserAccountLink.objects.filter(
        local_user_id=local_user_id,
        auth0_user_id=auth0_user_id
    ).first()
    
    if existing:
        raise ValueError(f"Link already exists between {local_user_id} and {auth0_user_id}")
    
    from django.utils import timezone
    
    link = UserAccountLink.objects.create(
        local_user_id=local_user_id,
        auth0_user_id=auth0_user_id,
        linked_by=linked_by,
        notes=notes,
        verified=auto_verify,
        verified_at=timezone.now() if auto_verify else None,
    )
    
    logger.info(f"Created account link: {local_user_id} -> {auth0_user_id} (by {linked_by})")
    return link


def unlink_user_accounts(local_user_id: str, auth0_user_id: str) -> bool:
    """
    Remove a link between a local user account and an Auth0 account.
    
    Args:
        local_user_id: The local user_id
        auth0_user_id: The Auth0 user_id
        
    Returns:
        True if a link was removed, False if no link existed
    """
    deleted_count, _ = UserAccountLink.objects.filter(
        local_user_id=local_user_id,
        auth0_user_id=auth0_user_id
    ).delete()
    
    if deleted_count > 0:
        logger.info(f"Removed account link: {local_user_id} -> {auth0_user_id}")
        return True
    
    return False


def verify_link(local_user_id: str, auth0_user_id: str) -> bool:
    """
    Mark a link as verified.
    
    Args:
        local_user_id: The local user_id
        auth0_user_id: The Auth0 user_id
        
    Returns:
        True if the link was verified, False if not found
    """
    from django.utils import timezone
    
    updated = UserAccountLink.objects.filter(
        local_user_id=local_user_id,
        auth0_user_id=auth0_user_id
    ).update(verified=True, verified_at=timezone.now())
    
    if updated > 0:
        logger.info(f"Verified account link: {local_user_id} -> {auth0_user_id}")
        return True
    
    return False


def get_user_links(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all account links for a user (as either local or Auth0 user).
    
    Args:
        user_id: The user_id to look up
        
    Returns:
        List of link information dictionaries
    """
    links = []
    
    # Links where this user is the local user
    for link in UserAccountLink.objects.filter(local_user_id=user_id):
        links.append({
            "id": link.id,
            "local_user_id": link.local_user_id,
            "auth0_user_id": link.auth0_user_id,
            "linked_by": link.linked_by,
            "verified": link.verified,
            "notes": link.notes,
            "created_at": link.created_at.isoformat(),
            "verified_at": link.verified_at.isoformat() if link.verified_at else None,
            "role": "local",  # This user is the local account
        })
    
    # Links where this user is the Auth0 user
    for link in UserAccountLink.objects.filter(auth0_user_id=user_id):
        links.append({
            "id": link.id,
            "local_user_id": link.local_user_id,
            "auth0_user_id": link.auth0_user_id,
            "linked_by": link.linked_by,
            "verified": link.verified,
            "notes": link.notes,
            "created_at": link.created_at.isoformat(),
            "verified_at": link.verified_at.isoformat() if link.verified_at else None,
            "role": "auth0",  # This user is the Auth0 account
        })
    
    return links


def get_linked_data_stats(user_id: str) -> Dict[str, Any]:
    """
    Get statistics about data that would be merged for linked accounts.
    
    Args:
        user_id: The user_id to check
        
    Returns:
        Dictionary with counts of data across linked accounts
    """
    linked_ids = get_linked_user_ids(user_id)
    
    stats = {
        "linked_user_ids": linked_ids,
        "user_facts": UserFact.objects.filter(user_id__in=linked_ids).count(),
        "user_preferences": UserPreference.objects.filter(user_id__in=linked_ids).count(),
        "conversation_summaries": ConversationSummary.objects.filter(user_id__in=linked_ids).count(),
        "memory_spots": MemorySpot.objects.filter(user_id__in=linked_ids).count(),
        "calendar_credentials": GoogleCalendarCredential.objects.filter(user_id__in=linked_ids).count(),
        "scheduled_tasks": ScheduledTask.objects.filter(user_id__in=linked_ids).count(),
    }
    
    # Calculate per-user breakdown
    stats["breakdown"] = {}
    for uid in linked_ids:
        stats["breakdown"][uid] = {
            "user_facts": UserFact.objects.filter(user_id=uid).count(),
            "user_preferences": UserPreference.objects.filter(user_id=uid).count(),
            "conversation_summaries": ConversationSummary.objects.filter(user_id=uid).count(),
            "memory_spots": MemorySpot.objects.filter(user_id=uid).count(),
        }
    
    return stats


def get_all_links() -> List[Dict[str, Any]]:
    """
    Get all account links in the system (admin function).
    
    Returns:
        List of all link information dictionaries
    """
    links = []
    
    for link in UserAccountLink.objects.all().order_by("-created_at"):
        links.append({
            "id": link.id,
            "local_user_id": link.local_user_id,
            "auth0_user_id": link.auth0_user_id,
            "linked_by": link.linked_by,
            "verified": link.verified,
            "notes": link.notes,
            "created_at": link.created_at.isoformat(),
            "verified_at": link.verified_at.isoformat() if link.verified_at else None,
        })
    
    return links
