# Port Assistant Setup Guide

## Quick Start

### 1. Create and Activate Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

**Required:**
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for AI processing)

**Optional (configure only the services you want to use):**
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`: For Gmail/Calendar
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`: For Slack integration
- `GONG_API_KEY`: For Gong call recordings
- `MONDAY_API_KEY`: For Monday.com boards
- `NOTION_API_TOKEN`: For Notion pages
- `MIRO_ACCESS_TOKEN`: For Miro boards

### 4. Run the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

### 5. Test the API

Visit http://localhost:8000/docs for interactive API documentation.

Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Test connections
curl http://localhost:8000/api/briefing/test/connections

# Generate briefing (requires at least ANTHROPIC_API_KEY)
curl -X POST http://localhost:8000/api/briefing/generate
```

## Getting API Keys

### Anthropic (Required)
1. Visit https://console.anthropic.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key

### Google Workspace (Optional)
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable Gmail API and Google Calendar API
4. Create OAuth 2.0 credentials
5. Generate refresh token using OAuth playground

### Slack (Optional)
1. Visit https://api.slack.com/apps
2. Create a new app
3. Add Bot Token Scopes: `channels:history`, `channels:read`, `users:read`
4. Install app to workspace
5. Copy Bot User OAuth Token

### Gong (Optional)
1. Log in to Gong at https://app.gong.io/
2. Go to Settings > API
3. Generate API key

### Monday.com (Optional)
1. Log in to Monday.com
2. Click profile picture > Admin > API
3. Generate API token

### Notion (Optional)
1. Visit https://www.notion.so/my-integrations
2. Create new integration
3. Copy Internal Integration Token

### Miro (Optional)
1. Go to https://miro.com/app/settings/user-profile/apps
2. Create new app
3. Generate access token

## Architecture Overview

The system consists of:

1. **MCP Clients** (`mcp/clients/`): Connect to external APIs (Google, Slack, etc.)
2. **Data Collectors** (`collectors/`): Orchestrate data collection from all sources in parallel
3. **AI Agent** (`agents/`): Process collected data using Claude to generate intelligent briefings
4. **API Endpoints** (`api/`): FastAPI routes for generating and retrieving briefings
5. **Data Models** (`models/`): Pydantic models for briefings and data sources

## Troubleshooting

### Import Errors
Make sure you've activated the virtual environment:
```bash
source venv/bin/activate
```

### API Key Errors
Check that your `.env` file exists and contains valid API keys. The only required key is `ANTHROPIC_API_KEY`.

### Connection Timeouts
Some data sources may take time to respond. Increase timeout settings in the MCP client if needed.

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black .

# Type checking
mypy .

# Linting
ruff check .
```

## Production Deployment

For production deployment, consider:

1. Use environment variables instead of `.env` file
2. Add database for persistent storage (PostgreSQL recommended)
3. Implement authentication and authorization
4. Set up monitoring and logging
5. Use a production ASGI server (Gunicorn + Uvicorn)
6. Add rate limiting and caching
7. Set up HTTPS with SSL certificates

Example production command:
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
