# Slack Bot Setup for Workspace-Wide @Mention Detection

## Current Issue
Your Slack bot can only see messages in channels where it's been explicitly invited. This means:
- ❌ @mentions in other channels are missed
- ❌ Need to manually add bot to every channel
- ❌ Can't anticipate where you'll be mentioned

## Solution: Configure Proper OAuth Scopes

### Step 1: Update Slack App Scopes

Go to [Slack API Apps](https://api.slack.com/apps) and select your app, then:

1. Navigate to **OAuth & Permissions** in the left sidebar
2. Scroll to **Scopes** > **Bot Token Scopes**
3. Add these scopes (if not already present):

#### Required Scopes for @Mention Detection:
- `channels:history` - Read messages in public channels (even ones bot isn't in)
- `channels:read` - View basic channel information
- `im:history` - Read direct message history
- `mpim:history` - Read group DM history
- `users:read` - Get user information
- `app_mentions:read` - See @mentions of your bot

#### Optional (but recommended):
- `groups:history` - Read private channel messages (if bot is added)
- `reactions:read` - Read emoji reactions

### Step 2: Reinstall App to Workspace

After adding scopes:
1. Scroll to top of **OAuth & Permissions** page
2. Click **Reinstall to Workspace**
3. Review new permissions and approve
4. Copy the new **Bot User OAuth Token**
5. Update `SLACK_BOT_TOKEN` in `backend/.env`

### Step 3: Enable Event Subscriptions (Recommended)

Instead of polling, receive real-time events:

1. Navigate to **Event Subscriptions** in left sidebar
2. Toggle **Enable Events** to ON
3. Set **Request URL** to: `https://your-domain.com/api/slack/events`
   - You'll need to expose your backend with a public URL (use ngrok for testing)
4. Subscribe to **Bot Events**:
   - `app_mention` - When someone @mentions your bot
   - `message.im` - DMs to your bot
   - `message.channels` - Messages in channels (for context)

### Step 4: Test the Setup

Run the test script to verify scopes:

```bash
source backend/venv/bin/activate
python3 test-slack-scopes.py
```

You should see:
- ✅ Connected to Slack
- ✅ Can list conversations
- ✅ Can read messages from channels

### Alternative: Search API Method

If you can't get workspace-wide access, use Slack's Search API:

1. Add `search:read` scope
2. Update the Slack client to use `search.messages` API
3. Search for: `@your-username` in the last 24 hours

This requires less permissions but is limited to 10 requests/minute.

## Current Bot Info

**Team:** Port
**Bot Name:** bnairnassistant
**Bot ID:** U0A6Z8A9ZKP
**Conversations Accessible:** 51

## Troubleshooting

### "Bot not seeing @mentions"
- Verify `app_mentions:read` scope is enabled
- Reinstall app after adding scopes
- Check bot is in workspace (not just channel)

### "Only seeing invited channels"
- Add `channels:history` scope
- This allows reading public channels without being invited

### "Missing DMs"
- Ensure `im:history` scope is present
- Users may need to start a DM with the bot first

## Security Note

The `channels:history` scope allows reading **all public channel messages**. This is necessary for detecting @mentions but means the bot has broad access. If this is a concern, use the Event Subscriptions method instead, which only sends events when the bot is explicitly mentioned.
