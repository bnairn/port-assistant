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

    # Write markdown file
    with open(OUTPUT_FILE, 'w') as f:
        f.write(f\"# Daily Briefing - {briefing['date']}\n\n\")
        f.write(f\"**Generated at:** {briefing['generated_at']}\n\n\")
        f.write(f\"**Processing time:** {briefing['processing_time_seconds']:.2f} seconds\n\n\")

        # Summary section
        f.write(\"---\n\n\")
        f.write(\"## 📋 Executive Summary\n\n\")

        summary = briefing['summary']

        if summary['key_highlights']:
            f.write(\"### 🎯 Key Highlights\n\n\")
            for highlight in summary['key_highlights']:
                f.write(f\"- {highlight}\n\")
            f.write(\"\n\")

        if summary['action_items']:
            f.write(\"### ✅ Action Items\n\n\")
            for item in summary['action_items']:
                f.write(f\"- [ ] {item}\n\")
            f.write(\"\n\")

        f.write(f\"**Overall Sentiment:** {summary['overall_sentiment'].title()}\n\n\")

        # Detailed sections
        f.write(\"---\n\n\")

        # Sort sections by priority (highest first)
        sections = sorted(briefing['sections'], key=lambda x: x['priority'], reverse=True)

        for section in sections:
            f.write(f\"## {section['title']}\n\n\")
            f.write(f\"**Priority:** {section['priority']} | **Sources:** {section['source_count']}\n\n\")

            if 'metadata' in section and section['metadata']:
                metadata = section['metadata']
                if 'total_emails' in metadata:
                    f.write(f\"📧 Total emails analyzed: {metadata['total_emails']}\n\n\")
                if 'total_events' in metadata:
                    f.write(f\"📅 Total events: {metadata['total_events']}\n\n\")

            f.write(section['content'])
            f.write(\"\n\n---\n\n\")

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
