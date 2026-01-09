# Setting Up Daily Briefing Emails

This guide will help you set up automatic daily briefing emails sent to your inbox at 6am.

## Step 1: Get Gmail App Password

Since you're using Gmail with Google OAuth already, you need to create an **App Password** for sending emails:

1. Go to https://myaccount.google.com/apppasswords
2. Sign in with your Google account
3. Select "Mail" and "Mac" (or Other)
4. Click "Generate"
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

> **Note**: If you don't see "App passwords", you may need to enable 2-Step Verification first: https://myaccount.google.com/security

## Step 2: Add Email Configuration to .env

Add these lines to `backend/.env`:

```bash
# Email Configuration
SENDER_EMAIL=your-email@gmail.com           # Your Gmail address
SENDER_APP_PASSWORD=abcdefghijklmnop        # App password (remove spaces)
RECIPIENT_EMAIL=your-email@gmail.com        # Where to send briefing (can be same)
```

Replace with your actual email and app password.

## Step 3: Test Email Sending

Test that email sending works:

```bash
cd /Users/bryannairn/Documents/port-assistant
source backend/venv/bin/activate
python backend/utils/email_sender.py
```

You should receive a test email. If not, check:
- App password is correct (no spaces)
- Sender email is correct
- No firewall blocking port 465

## Step 4: Test Full Briefing Email

Make sure the backend is running:

```bash
cd backend
source venv/bin/activate
python main.py
```

Then in another terminal, test sending a full briefing:

```bash
./send-daily-briefing.sh
```

Check your inbox for the briefing email!

## Step 5: Set Up Daily Cron Job (6am)

To automatically send the briefing every day at 6am:

1. Open crontab editor:
```bash
crontab -e
```

2. Add this line (adjust path if needed):
```bash
# Send daily briefing at 6:00 AM
0 6 * * * cd /Users/bryannairn/Documents/port-assistant && ./send-daily-briefing.sh >> /tmp/briefing-cron.log 2>&1
```

3. Save and exit (`:wq` in vim, or `Ctrl+X` then `Y` in nano)

4. Verify cron job is set:
```bash
crontab -l
```

## Step 6: Keep Backend Running

For the cron job to work, the backend needs to be running 24/7. Options:

### Option A: Run in Background (Simple)
```bash
cd /Users/bryannairn/Documents/port-assistant/backend
source venv/bin/activate
nohup python main.py > backend.log 2>&1 &
```

### Option B: Use launchd (macOS recommended)

Create `/Users/bryannairn/Library/LaunchAgents/com.port-assistant.backend.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.port-assistant.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/bryannairn/Documents/port-assistant/backend/venv/bin/python</string>
        <string>/Users/bryannairn/Documents/port-assistant/backend/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/bryannairn/Documents/port-assistant/backend</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/port-assistant.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/port-assistant.error.log</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.port-assistant.backend.plist
```

### Option C: Use Docker (Production recommended)
See Docker setup in main README if you want a containerized solution.

## Troubleshooting

### Email not sending
- Check `SENDER_EMAIL` and `SENDER_APP_PASSWORD` in `.env`
- Verify app password has no spaces
- Test with: `python backend/utils/email_sender.py`

### Cron job not running
- Check cron logs: `tail -f /tmp/briefing-cron.log`
- Verify backend is running: `curl http://localhost:8000/health`
- Check crontab: `crontab -l`

### Backend not running
- Check if process is running: `ps aux | grep "python main.py"`
- Check logs: `tail -f /tmp/port-assistant.log`
- Restart: `launchctl unload ~/Library/LaunchAgents/com.port-assistant.backend.plist && launchctl load ~/Library/LaunchAgents/com.port-assistant.backend.plist`

## Alternative: Different Email Provider

If you want to use SendGrid, Mailgun, or another provider instead of Gmail:

1. Install the provider's SDK:
```bash
pip install sendgrid
```

2. Update `backend/utils/email_sender.py` to use that provider's API
3. Add API keys to `.env`

## Testing Different Times

To test the email at different times, you can manually run:

```bash
./send-daily-briefing.sh
```

Or for a specific date:
```bash
./send-daily-briefing.sh 2026-01-07
```

---

**That's it!** You'll now receive your daily briefing at 6am every morning. 📧✨
