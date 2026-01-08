#!/usr/bin/env python3
"""Test Slack connection and show current scopes"""
import os
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env") if os.path.exists(".env") else load_dotenv("backend/.env")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

if not SLACK_BOT_TOKEN:
    print("❌ SLACK_BOT_TOKEN not found in backend/.env")
    exit(1)

print("Testing Slack Bot Token...")
print("=" * 70)

with httpx.Client() as client:
    # Test auth
    response = client.get(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    )

    data = response.json()

    if not data.get("ok"):
        print(f"❌ Auth failed: {data.get('error')}")
        exit(1)

    print(f"✅ Connected to Slack!")
    print(f"   Team: {data.get('team')}")
    print(f"   User: {data.get('user')}")
    print(f"   Bot ID: {data.get('user_id')}")
    print()

    # Try to list conversations to see what scopes are missing
    print("Testing conversations.list...")
    response = client.get(
        "https://slack.com/api/conversations.list",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        params={"types": "public_channel,private_channel,im"}
    )

    data = response.json()

    if not data.get("ok"):
        error = data.get('error')
        print(f"❌ Failed: {error}")
        print()

        if error == "missing_scope":
            print("Your Slack app is missing required OAuth scopes!")
            print()
            print("Required Bot Token Scopes:")
            print("  • channels:history - Read messages in public channels")
            print("  • channels:read - View basic channel info")
            print("  • groups:history - Read messages in private channels")
            print("  • groups:read - View private channel info")
            print("  • im:history - Read direct messages")
            print("  • im:read - View direct message info")
            print("  • users:read - View user information")
            print()
            print("How to fix:")
            print("1. Go to https://api.slack.com/apps")
            print("2. Select your app")
            print("3. Go to 'OAuth & Permissions'")
            print("4. Add the scopes listed above to 'Bot Token Scopes'")
            print("5. Click 'Reinstall to Workspace'")
            print("6. Copy the new Bot Token and update your .env file")

        print()
        print(f"Response needed: {data.get('needed')}")
        print(f"Response provided: {data.get('provided')}")
    else:
        channels = data.get("channels", [])
        print(f"✅ Successfully listed {len(channels)} conversations")
        print()
        print("Your Slack integration is working correctly!")
