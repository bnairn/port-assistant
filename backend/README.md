# Port Assistant Backend

Product Marketing Productivity Assistant for Port.io - Backend Service

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the server:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── config/
│   └── settings.py         # Application configuration
├── api/
│   ├── health.py           # Health check endpoints
│   └── briefing.py         # Briefing generation endpoints
├── mcp/
│   └── clients/            # MCP client implementations
├── collectors/
│   ├── base.py             # Base collector class
│   └── implementations/    # Data source collectors
├── models/
│   ├── briefing.py         # Briefing data models
│   └── data_sources.py     # Data source models
└── agents/
    └── ...                 # AI agent implementations (LangGraph)
```

## Development

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Test all data source connections
curl http://localhost:8000/api/briefing/test/connections

# Generate briefing for today
curl -X POST http://localhost:8000/api/briefing/generate

# Generate briefing for specific date
curl -X POST "http://localhost:8000/api/briefing/generate?target_date=2026-01-07"

# Generate briefing with raw data
curl -X POST "http://localhost:8000/api/briefing/generate?include_raw_data=true"

# Get briefing
curl http://localhost:8000/api/briefing/2026-01-07
```

## Features Implemented

1. ✅ Basic FastAPI setup with health check and briefing endpoints
2. ✅ MCP clients for all data sources (Google, Slack, Gong, Monday, Notion, Miro)
3. ✅ Data collectors that gather information in parallel from all sources
4. ✅ AI agent (Claude) for intelligent briefing generation
5. ✅ Complete data models for briefings and all data sources
6. ✅ Connection testing endpoint

## Data Sources

The system integrates with:
- **Google Workspace**: Gmail + Google Calendar
- **Slack**: Channel messages and threads
- **Gong**: Customer call recordings and transcripts
- **Monday.com**: Project boards and tasks
- **Notion**: Pages and documentation
- **Miro**: Collaborative boards

## Next Steps

1. ⏳ Add database storage for briefings (PostgreSQL + SQLAlchemy)
2. ⏳ Implement cron job for daily generation
3. ⏳ Add authentication and user management
4. ⏳ Build frontend interface (Next.js)
5. ⏳ Add email delivery of daily briefings
6. ⏳ Implement vector database (Pinecone) for semantic search

## License

Proprietary - Port.io Internal Tool
