#!/bin/bash

# Send Daily Briefing Email
# This script generates a briefing and sends it via email
# To be run daily via cron at 6am

set -e

# Change to script directory
cd "$(dirname "$0")"

DATE=${1:-$(date +%Y-%m-%d)}
RECIPIENT_EMAIL=${RECIPIENT_EMAIL:-$(grep RECIPIENT_EMAIL backend/.env | cut -d '=' -f2)}

echo "Generating briefing for ${DATE}..."

# Generate briefing and capture JSON response
RESPONSE=$(curl -s -X POST http://localhost:8000/api/briefing/generate \
  -H "Content-Type: application/json" \
  -d "{\"target_date\": \"${DATE}\"}")

# Check if request was successful
if [ $? -ne 0 ]; then
  echo "Error: Failed to connect to backend server"
  echo "Make sure the server is running: cd backend && python main.py"
  exit 1
fi

# Extract briefing markdown
MARKDOWN=$(echo "$RESPONSE" | python3 -c "
import json
import sys

try:
    data = json.load(sys.stdin)
    briefing = data['briefing']

    # Build markdown (compact layout)
    md = f\"# Daily Briefing - {briefing['date']}\\n\\n\"

    # Sort sections by priority
    sections = sorted(briefing['sections'], key=lambda x: x['priority'])

    for section in sections:
        md += f\"## {section['title']}\\n\\n\"

        # Add metadata if present
        if 'metadata' in section and section['metadata']:
            metadata = section['metadata']
            metadata_lines = []

            if 'total_emails' in metadata:
                metadata_lines.append(f\"📧 Total emails: {metadata['total_emails']}\")
            if 'meeting_invites' in metadata:
                metadata_lines.append(f\"📅 Meeting invites: {metadata['meeting_invites']}\")
            if 'total_events' in metadata:
                metadata_lines.append(f\"📅 Total events: {metadata['total_events']}\")
            if 'total_messages' in metadata:
                metadata_lines.append(f\"💬 Total messages: {metadata['total_messages']}\")
            if 'unanswered_dms' in metadata:
                metadata_lines.append(f\"✉️ Unanswered DMs: {metadata['unanswered_dms']}\")
            if 'mentions' in metadata:
                metadata_lines.append(f\"@️ Mentions: {metadata['mentions']}\")
            if 'total_calls' in metadata:
                metadata_lines.append(f\"📞 Total calls: {metadata['total_calls']}\")
            if 'new_customers' in metadata:
                metadata_lines.append(f\"🆕 New customers: {metadata['new_customers']}\")
            if 'total_articles' in metadata:
                metadata_lines.append(f\"📰 Articles: {metadata['total_articles']}\")

            if metadata_lines:
                md += ' | '.join(metadata_lines) + \"\\n\\n\"

        md += section['content'] + \"\\n\\n\"

    # Data sources
    md += \"## 🔌 Data Sources\\n\\n\"
    for source in briefing['data_sources']:
        status_icon = '✅' if source['status'] == 'success' else '❌'
        md += f\"{status_icon} **{source['source_name'].title()}**: {source['items_collected']} items\"
        if source['error_message']:
            md += f\" (Error: {source['error_message']})\"
        md += \"\\n\"

    print(md)

except Exception as e:
    print(f\"Error: {e}\", file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ]; then
    echo "❌ Failed to parse briefing"
    exit 1
fi

# Send email using Python (with venv)
source backend/venv/bin/activate
python3 -c "
import sys
sys.path.insert(0, 'backend')
from utils.email_sender import send_briefing_email
from datetime import datetime

markdown = '''${MARKDOWN}'''
recipient = '${RECIPIENT_EMAIL}'

if not recipient or recipient == '':
    print('❌ RECIPIENT_EMAIL not set. Add it to backend/.env')
    sys.exit(1)

subject = f'Daily Briefing - {datetime.now().strftime(\"%B %d, %Y\")}'
success = send_briefing_email(markdown, recipient, subject)

if not success:
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Daily briefing sent to ${RECIPIENT_EMAIL}"
else
    echo "❌ Failed to send email"
    exit 1
fi
