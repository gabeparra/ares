#!/usr/bin/env python3
"""
Check Telegram Sessions Script

Verifies if daily Telegram chat creation is working by:
1. Listing all Telegram sessions
2. Checking if there are sessions with today's date
3. Showing the most recent sessions
"""

import sys
import os
from datetime import datetime

# Add Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ares_project.settings")

import django
django.setup()

from django.utils import timezone
from api.models import ChatSession, ConversationMessage
from api.telegram_views import _get_daily_telegram_session_id, _extract_chat_id_from_session_id


def check_telegram_sessions():
    """Check Telegram sessions and verify daily creation is working."""
    print("=" * 80)
    print("Telegram Sessions Check")
    print("=" * 80)
    print()
    
    # Get today's date
    today = timezone.now().date()
    today_str = today.isoformat()
    print(f"Today's date: {today_str}")
    print()
    
    # Find all Telegram sessions
    telegram_sessions = ChatSession.objects.filter(
        session_id__startswith="telegram_user_"
    ).order_by("-updated_at")
    
    total_sessions = telegram_sessions.count()
    print(f"Total Telegram sessions found: {total_sessions}")
    print()
    
    if total_sessions == 0:
        print("⚠️  No Telegram sessions found in database.")
        print("   This could mean:")
        print("   - No messages have been sent via Telegram yet")
        print("   - Telegram integration is not working")
        return
    
    # Group sessions by chat_id and date
    sessions_by_chat = {}
    today_sessions = []
    
    for session in telegram_sessions:
        chat_id = _extract_chat_id_from_session_id(session.session_id)
        if not chat_id:
            continue
        
        if chat_id not in sessions_by_chat:
            sessions_by_chat[chat_id] = []
        
        sessions_by_chat[chat_id].append(session)
        
        # Check if this session is from today
        if today_str in session.session_id:
            today_sessions.append(session)
    
    print(f"Sessions from today ({today_str}): {len(today_sessions)}")
    print()
    
    if today_sessions:
        print("✅ Today's sessions:")
        for session in today_sessions:
            message_count = ConversationMessage.objects.filter(session=session).count()
            print(f"  - {session.session_id}")
            print(f"    Title: {session.title or '(no title)'}")
            print(f"    Messages: {message_count}")
            print(f"    Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    else:
        print("⚠️  No sessions found for today!")
        print("   This suggests daily chat creation is NOT working.")
        print()
    
    # Show recent sessions (last 10)
    print("Recent Telegram sessions (last 10):")
    print("-" * 80)
    for session in telegram_sessions[:10]:
        chat_id = _extract_chat_id_from_session_id(session.session_id)
        message_count = ConversationMessage.objects.filter(session=session).count()
        is_today = today_str in session.session_id
        
        date_part = ""
        if "_" in session.session_id:
            parts = session.session_id.split("_")
            if len(parts) >= 3:
                # Try to extract date
                for part in parts:
                    if len(part) == 10 and part.count("-") == 2:
                        date_part = part
                        break
        
        status = "✅ TODAY" if is_today else "📅"
        print(f"{status} {session.session_id}")
        print(f"   Chat ID: {chat_id or 'unknown'}")
        print(f"   Title: {session.title or '(no title)'}")
        print(f"   Date: {date_part or 'unknown'}")
        print(f"   Messages: {message_count}")
        print(f"   Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # Check what the expected session ID would be for a test user
    print("=" * 80)
    print("Expected Session ID Format")
    print("=" * 80)
    print()
    print("For a Telegram user with ID '123456789', today's session should be:")
    test_id = "123456789"
    expected_session_id = _get_daily_telegram_session_id(test_id)
    print(f"  {expected_session_id}")
    print()
    
    # Check if any active session preferences exist
    from api.models import UserPreference
    active_prefs = UserPreference.objects.filter(
        preference_key__startswith="telegram_active_session_"
    )
    
    if active_prefs.exists():
        print(f"Active session preferences found: {active_prefs.count()}")
        for pref in active_prefs:
            user_id = pref.preference_key.replace("telegram_active_session_", "")
            session_id = pref.preference_value
            is_today_session = today_str in session_id
            status = "✅ TODAY" if is_today_session else "⚠️  STALE"
            print(f"  {status} User {user_id}: {session_id}")
    else:
        print("No active session preferences found (this is normal if using daily sessions)")
    print()


if __name__ == "__main__":
    check_telegram_sessions()

