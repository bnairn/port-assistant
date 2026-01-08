from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime
from typing import Optional, Dict
import logging
from config.settings import settings
from collectors.data_collector import DataCollector
from agents.briefing_agent import BriefingAgent
from models.briefing import Briefing, BriefingResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage for briefings (replace with database later)
briefings_cache: Dict[str, Briefing] = {}


@router.post("/generate", response_model=BriefingResponse)
async def generate_briefing(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    include_raw_data: bool = Query(False, description="Include raw collected data"),
    force_regenerate: bool = Query(False, description="Force regeneration if already exists"),
):
    """
    Generate daily briefing for the specified date (default: today)

    This endpoint:
    1. Collects data from all connected sources (Google, Slack, Gong, etc.)
    2. Processes the data through the AI agent
    3. Generates an intelligent briefing with key insights

    Args:
        target_date: Date in YYYY-MM-DD format (optional, defaults to today)
        include_raw_data: Include raw collected data in response
        force_regenerate: Force regeneration even if briefing exists

    Returns:
        Complete Briefing object with sections and summary
    """
    try:
        # Parse date
        if target_date is None:
            briefing_date = date.today()
        else:
            briefing_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        briefing_id = f"briefing-{briefing_date.isoformat()}"

        # Check if briefing already exists
        if briefing_id in briefings_cache and not force_regenerate:
            logger.info(f"Returning cached briefing for {briefing_date}")
            return BriefingResponse(
                briefing=briefings_cache[briefing_id],
                message="Briefing retrieved from cache"
            )

        logger.info(f"Generating new briefing for {briefing_date}")

        # Step 1: Collect data from all sources
        logger.info("Step 1: Collecting data from all sources...")
        collector = DataCollector(settings.model_dump())

        collected_data, source_statuses = await collector.collect_all(
            start_date=briefing_date,
            end_date=briefing_date,
        )

        total_items = collected_data.get_total_items()
        logger.info(f"Collected {total_items} total items")

        if total_items == 0:
            logger.warning("No data collected from any source")
            return BriefingResponse(
                briefing=Briefing(
                    id=briefing_id,
                    date=briefing_date,
                    status="completed",
                    data_sources=source_statuses,
                ),
                message="No data available for this date"
            )

        # Step 2: Process with AI agent
        logger.info("Step 2: Processing data with AI agent...")
        agent = BriefingAgent(settings.ANTHROPIC_API_KEY)

        briefing = await agent.generate_briefing(
            collected_data=collected_data,
            target_date=briefing_date,
            source_statuses=source_statuses,
            include_raw_data=include_raw_data,
        )

        # Cache the briefing
        briefings_cache[briefing_id] = briefing

        logger.info(f"Briefing generation complete for {briefing_date}")

        return BriefingResponse(
            briefing=briefing,
            message="Briefing generated successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating briefing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate briefing: {str(e)}"
        )


@router.get("/{briefing_date}", response_model=BriefingResponse)
async def get_briefing(briefing_date: str):
    """
    Retrieve briefing for a specific date

    Args:
        briefing_date: Date in YYYY-MM-DD format

    Returns:
        Briefing data if available
    """
    try:
        # Validate date format
        parsed_date = datetime.strptime(briefing_date, "%Y-%m-%d").date()
        briefing_id = f"briefing-{parsed_date.isoformat()}"

        # Check cache
        if briefing_id in briefings_cache:
            return BriefingResponse(
                briefing=briefings_cache[briefing_id],
                message="Briefing retrieved successfully"
            )

        # Not found
        raise HTTPException(
            status_code=404,
            detail=f"No briefing found for {briefing_date}. Generate one first using POST /api/briefing/generate"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )


@router.get("/test/connections")
async def test_connections():
    """
    Test connections to all data sources

    Returns:
        Status of each data source connection
    """
    try:
        logger.info("Testing all data source connections...")
        collector = DataCollector(settings.model_dump())
        results = await collector.test_all_connections()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "sources": results,
            "summary": {
                "total": len(results),
                "connected": sum(1 for r in results.values() if r.get("connected")),
                "failed": sum(1 for r in results.values() if not r.get("connected")),
            }
        }

    except Exception as e:
        logger.error(f"Error testing connections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test connections: {str(e)}"
        )
