#!/bin/bash

# Generate Daily Briefing and save as Markdown
# Usage: ./generate-briefing.sh [YYYY-MM-DD]
# If no date provided, uses today's date

DATE=${1:-$(date +%Y-%m-%d)}
OUTPUT_FILE="briefing-${DATE}.md"

echo "Generating briefing for ${DATE}..."

# Generate briefing
RESPONSE=$(curl -s -X POST http://localhost:8000/api/briefing/generate \
  -H "Content-Type: application/json" \
  -d "{\"target_date\": \"${DATE}\"}")

# Check if request was successful
if [ $? -ne 0 ]; then
  echo "Error: Failed to connect to backend server"
  echo "Make sure the server is running: cd backend && python main.py"
  exit 1
fi

# Extract briefing data
echo "$RESPONSE" | python3 -c "
import json
import sys
import os
from datetime import datetime

OUTPUT_FILE = '${OUTPUT_FILE}'

try:
    data = json.load(sys.stdin)
    briefing = data['briefing']

    # Write markdown file (compact layout)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(f\"# Daily Briefing - {briefing['date']}\n\n\")

        # Sort sections by priority (lowest number = highest priority, 1 is first)
        sections = sorted(briefing['sections'], key=lambda x: x['priority'])

        for section in sections:
            f.write(f\"## {section['title']}\n\n\")

            if 'metadata' in section and section['metadata']:
                metadata = section['metadata']
                metadata_lines = []

                # Email metadata
                if 'total_emails' in metadata:
                    metadata_lines.append(f\"📧 Total emails: {metadata['total_emails']}\")
                if 'meeting_invites' in metadata:
                    metadata_lines.append(f\"📅 Meeting invites: {metadata['meeting_invites']}\")

                # Calendar metadata
                if 'total_events' in metadata:
                    metadata_lines.append(f\"📅 Total events: {metadata['total_events']}\")

                # Slack metadata
                if 'total_messages' in metadata:
                    metadata_lines.append(f\"💬 Total messages: {metadata['total_messages']}\")
                if 'unanswered_dms' in metadata:
                    metadata_lines.append(f\"✉️ Unanswered DMs: {metadata['unanswered_dms']}\")
                if 'mentions' in metadata:
                    metadata_lines.append(f\"@️ Mentions: {metadata['mentions']}\")

                # Gong metadata
                if 'total_calls' in metadata:
                    metadata_lines.append(f\"📞 Total calls: {metadata['total_calls']}\")
                if 'new_customers' in metadata:
                    metadata_lines.append(f\"🆕 New customers: {metadata['new_customers']}\")
                if 'existing_customers' in metadata:
                    metadata_lines.append(f\"🔄 Existing customers: {metadata['existing_customers']}\")

                # News metadata
                if 'total_articles' in metadata:
                    metadata_lines.append(f\"📰 Articles: {metadata['total_articles']}\")

                # Critical items metadata
                if 'total_items' in metadata:
                    metadata_lines.append(f\"⚠️ Critical items: {metadata['total_items']}\")
                if 'total_requests' in metadata:
                    metadata_lines.append(f\"📬 New requests: {metadata['total_requests']}\")

                if metadata_lines:
                    f.write(\" | \".join(metadata_lines) + \"\n\n\")

            f.write(section['content'])
            f.write(\"\n\n\")

        # Data sources status
        f.write(\"## 🔌 Data Sources\n\n\")
        for source in briefing['data_sources']:
            status_icon = '✅' if source['status'] == 'success' else '❌'
            f.write(f\"{status_icon} **{source['source_name'].title()}**: \")
            f.write(f\"{source['items_collected']} items\")
            if source['error_message']:
                f.write(f\" (Error: {source['error_message']})\")
            f.write(\"\n\")

    print(f\"✅ Briefing saved to {OUTPUT_FILE}\")
    print(f\"📄 Open in VS Code: code {OUTPUT_FILE}\")

except Exception as e:
    print(f\"Error: {e}\", file=sys.stderr)
    sys.exit(1)
"

if [ $? -eq 0 ]; then
  # Automatically open in VS Code if available
  if command -v code &> /dev/null; then
    code "${OUTPUT_FILE}"
    echo "✨ Opened in VS Code"
  fi
else
  echo "❌ Failed to generate briefing"
  exit 1
fi
