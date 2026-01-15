#!/usr/bin/env python3
"""
Test script to verify daily Telegram session ID generation logic.
This doesn't require database access, just tests the date logic.
"""

from datetime import datetime, date
from django.utils import timezone

# Simulate the functions
def _get_daily_telegram_session_id(from_id):
    """Generate a daily Telegram session ID."""
    today = timezone.now().date()
    return f"telegram_user_{from_id}_{today.isoformat()}"

def test_daily_session_logic():
    """Test that daily session IDs are generated correctly."""
    print("=" * 80)
    print("Testing Daily Telegram Session ID Generation")
    print("=" * 80)
    print()
    
    # Get today's date
    today = timezone.now().date()
    today_str = today.isoformat()
    
    print(f"Today's date: {today_str}")
    print(f"Current time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    
    # Test with a sample user ID
    test_user_id = "123456789"
    
    # Generate session ID
    session_id = _get_daily_telegram_session_id(test_user_id)
    expected_format = f"telegram_user_{test_user_id}_{today_str}"
    
    print(f"Test user ID: {test_user_id}")
    print(f"Generated session ID: {session_id}")
    print(f"Expected format: {expected_format}")
    print()
    
    # Verify format
    if session_id == expected_format:
        print("✅ Session ID format is correct!")
    else:
        print("❌ Session ID format mismatch!")
        print(f"   Expected: {expected_format}")
        print(f"   Got:      {session_id}")
    
    print()
    
    # Test prefix matching (simulating the webhook logic)
    today_prefix = f"telegram_user_{test_user_id}_{today_str}"
    
    print("Testing prefix matching logic:")
    print(f"Today's prefix: {today_prefix}")
    print()
    
    # Test cases
    test_cases = [
        (f"telegram_user_{test_user_id}_{today_str}", True, "Today's daily session"),
        (f"telegram_user_{test_user_id}_{today_str}_123456", True, "Today's /new session"),
        (f"telegram_user_{test_user_id}_2025-01-14", False, "Yesterday's session"),
        (f"telegram_user_{test_user_id}_2025-01-13_123456", False, "Day before yesterday's /new session"),
    ]
    
    for session_id_test, should_match, description in test_cases:
        matches = session_id_test.startswith(today_prefix)
        status = "✅" if matches == should_match else "❌"
        print(f"{status} {description}: {session_id_test}")
        print(f"   Matches today's prefix: {matches} (expected: {should_match})")
        if matches != should_match:
            print(f"   ⚠️  MISMATCH!")
        print()
    
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    import os
    import sys
    import django
    
    # Setup Django
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ares_project.settings")
    django.setup()
    
    test_daily_session_logic()

