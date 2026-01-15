#!/usr/bin/env python
"""
Quick test script to verify Discord bot setup.

Run this to check if the bot can be initialized properly.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')
django.setup()

def test_bot_setup():
    """Test if Discord bot can be set up."""
    print("Testing Discord bot setup...")
    
    # Check environment variables
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    client_id = os.getenv('DISCORD_CLIENT_ID')
    
    if not bot_token:
        print("❌ DISCORD_BOT_TOKEN not set in environment")
        return False
    else:
        print(f"✅ DISCORD_BOT_TOKEN is set (length: {len(bot_token)})")
    
    if not client_id:
        print("❌ DISCORD_CLIENT_ID not set in environment")
        return False
    else:
        print(f"✅ DISCORD_CLIENT_ID is set: {client_id}")
    
    # Check if discord.py is installed
    try:
        import discord
        print(f"✅ discord.py is installed (version: {discord.__version__})")
    except ImportError:
        print("❌ discord.py is not installed. Run: pip install discord.py")
        return False
    
    # Check if bot module can be imported
    try:
        from api.discord_bot import start_discord_bot, is_discord_bot_running, stop_discord_bot
        print("✅ Discord bot module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import Discord bot module: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test bot functions
    try:
        if is_discord_bot_running():
            print("⚠️  Bot is already running")
        else:
            print("✅ Bot status check works")
    except Exception as e:
        print(f"❌ Error checking bot status: {e}")
        return False
    
    print("\n✅ All checks passed! Bot should be ready to start.")
    print("\nTo start the bot, run:")
    print("  python manage.py run_discord_bot --daemon")
    print("\nOr use the API endpoint:")
    print("  POST /api/v1/discord/bot/start")
    
    return True

if __name__ == '__main__':
    success = test_bot_setup()
    sys.exit(0 if success else 1)

