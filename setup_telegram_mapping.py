#!/usr/bin/env python3
"""
Quick script to set up Telegram chat ID mappings.

"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

from api.models import UserPreference

def setup_telegram_mapping(identifier, chat_id, user_id="default"):
    """Set up a mapping from identifier to Telegram chat_id."""
    pref_key = f"telegram_chat_id_{identifier.lower().strip().lstrip('@')}"
    
    pref, created = UserPreference.objects.update_or_create(
        user_id=user_id,
        preference_key=pref_key,
        defaults={
            "preference_value": str(chat_id).strip(),
        }
    )
    
    action = "Created" if created else "Updated"
    print(f"{action} mapping: '{identifier}' -> Telegram chat_id '{chat_id}'")
    print(f"  Preference key: {pref_key}")
    print(f"  User ID: {user_id}")
    
    return pref

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 setup_telegram_mapping.py <identifier> <chat_id> [user_id]")
        sys.exit(1)
    
    identifier = sys.argv[1]
    chat_id = sys.argv[2]
    user_id = sys.argv[3] if len(sys.argv) > 3 else "default"
    
    setup_telegram_mapping(identifier, chat_id, user_id)
    print("\n✓ Mapping set up successfully!")
    print(f"  You can now ask ARES to 'send a message to {identifier}' and it will work.")

