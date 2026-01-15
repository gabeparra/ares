#!/usr/bin/env python3
"""
Link a Telegram chat_id to an ARES user_id so memories are shared.

Usage:
    python3 link_telegram_user.py <telegram_chat_id> <ares_user_id>
    
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

from api.utils import _link_telegram_to_user_id

def link_telegram_user(telegram_chat_id, ares_user_id):
    """Link a Telegram chat_id to an ARES user_id."""
    pref, created = _link_telegram_to_user_id(telegram_chat_id, ares_user_id)
    
    action = "Created" if created else "Updated"
    print(f"{action} link: Telegram chat_id '{telegram_chat_id}' -> ARES user_id '{ares_user_id}'")
    print(f"\n✓ Linking complete!")
    print(f"  Telegram messages from chat_id {telegram_chat_id} will now use user_id '{ares_user_id}'")
    print(f"  This means memories, facts, and preferences will be shared between Telegram and ARES web interface.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 link_telegram_user.py <telegram_chat_id> <ares_user_id>")
        print("\nThis links your Telegram identity to your ARES user_id so memories are shared.")
        sys.exit(1)
    
    telegram_chat_id = sys.argv[1]
    ares_user_id = sys.argv[2]
    
    link_telegram_user(telegram_chat_id, ares_user_id)

