#!/bin/bash
# Verify Discord bot intents are enabled and bot can connect

echo "============================================================"
echo "Discord Bot Intent Verification"
echo "============================================================"
echo ""

# Check if bot token is set
if ! grep -q "DISCORD_BOT_TOKEN=" /home/gabe/ares/.env 2>/dev/null; then
    echo "❌ DISCORD_BOT_TOKEN not found in .env"
    exit 1
fi

echo "✅ DISCORD_BOT_TOKEN is configured"
echo ""

# Try to start bot and check for intent errors
echo "Testing bot connection..."
cd /home/gabe/ares

timeout 10 python3 manage.py run_discord_bot 2>&1 | head -20 > /tmp/discord_test.log

if grep -q "PrivilegedIntentsRequired" /tmp/discord_test.log; then
    echo "❌ ERROR: Privileged intents are NOT enabled"
    echo ""
    echo "You need to enable MESSAGE CONTENT INTENT in Discord Developer Portal:"
    echo "  1. Go to: https://discord.com/developers/applications"
    echo "  2. Select your app (Client ID: 1460657376062345269)"
    echo "  3. Go to Bot → Privileged Gateway Intents"
    echo "  4. Enable: MESSAGE CONTENT INTENT"
    echo "  5. Click Save Changes"
    echo "  6. Wait 1-2 minutes"
    echo "  7. Run this script again to verify"
    echo ""
    exit 1
elif grep -q "Bot logged in" /tmp/discord_test.log; then
    echo "✅ SUCCESS: Bot connected successfully!"
    echo "✅ Intents are properly enabled"
    echo ""
    echo "You can now start the service:"
    echo "  sudo systemctl start ares-discord-bot"
    exit 0
else
    echo "⚠️  Could not determine status. Check logs:"
    cat /tmp/discord_test.log
    exit 1
fi



