from typing import Dict, List, Optional
from datetime import date, datetime
import asyncio
import logging
from .base import BaseCollector, CollectionResult
from models.data_sources import CollectedData
from models.briefing import DataSourceStatus
from mcp.clients import (
    GoogleMCPClient,
    SlackMCPClient,
    GongMCPClient,
    MondayMCPClient,
    NotionMCPClient,
    MiroMCPClient,
    WeatherMCPClient,
    NewsMCPClient,
)

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Main data collector that orchestrates all MCP clients
    to gather data from all sources in parallel.
    """

    def __init__(self, config: Dict[str, any]):
        """
        Initialize the main data collector

        Args:
            config: Dictionary containing all API keys and configuration
        """
        self.config = config
        self.logger = logger

        # Initialize all MCP clients
        self.clients = {
            "google": GoogleMCPClient(config),
            "slack": SlackMCPClient(config),
            "gong": GongMCPClient(config),
            "monday": MondayMCPClient(config),
            "notion": NotionMCPClient(config),
            "miro": MiroMCPClient(config),
            "weather": WeatherMCPClient(config),
            "news": NewsMCPClient(config),
        }

    async def collect_all(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        sources: Optional[List[str]] = None,
    ) -> tuple[CollectedData, List[DataSourceStatus]]:
        """
        Collect data from all (or specified) sources in parallel

        Args:
            start_date: Start date for data collection
            end_date: End date (defaults to start_date)
            sources: List of source names to collect from (None = all sources)

        Returns:
            Tuple of (CollectedData, List of DataSourceStatus)
        """
        if end_date is None:
            end_date = start_date

        if sources is None:
            sources = list(self.clients.keys())

        self.logger.info(f"Starting data collection for {start_date} to {end_date}")
        self.logger.info(f"Sources: {', '.join(sources)}")

        # Collect from all sources in parallel
        tasks = []
        for source_name in sources:
            if source_name in self.clients:
                task = self._collect_from_source(
                    source_name,
                    self.clients[source_name],
                    start_date,
                    end_date
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        collected_data = CollectedData()
        source_statuses = []

        for i, result in enumerate(results):
            source_name = sources[i] if i < len(sources) else "unknown"

            if isinstance(result, Exception):
                self.logger.error(f"Error collecting from {source_name}: {str(result)}")
                source_statuses.append(
                    DataSourceStatus(
                        source_name=source_name,
                        status="failed",
                        items_collected=0,
                        error_message=str(result),
                        collected_at=datetime.utcnow(),
                    )
                )
            elif isinstance(result, CollectionResult):
                source_statuses.append(
                    DataSourceStatus(
                        source_name=result.source_name,
                        status="success" if result.success else "failed",
                        items_collected=result.items_collected,
                        error_message=result.error_message,
                        collected_at=result.collected_at,
                    )
                )

                # Add collected data to appropriate lists
                if result.success and result.data:
                    self._add_data_to_collection(collected_data, result.source_name, result.data)

        total_items = collected_data.get_total_items()
        self.logger.info(f"Collection complete. Total items: {total_items}")
        self.logger.info(f"Source counts: {collected_data.get_source_counts()}")

        return collected_data, source_statuses

    async def _collect_from_source(
        self,
        source_name: str,
        client,
        start_date: date,
        end_date: date
    ) -> CollectionResult:
        """Collect data from a single source"""
        self.logger.info(f"Collecting from {source_name}...")

        try:
            async with client:
                data = await client.fetch_data(start_date, end_date)

                # Count items based on source type
                items_count = self._count_items(source_name, data)

                self.logger.info(f"Successfully collected {items_count} items from {source_name}")

                return CollectionResult(
                    source_name=source_name,
                    success=True,
                    items_collected=items_count,
                    collected_at=datetime.utcnow(),
                    data=data,
                )

        except Exception as e:
            self.logger.error(f"Failed to collect from {source_name}: {str(e)}")
            return CollectionResult(
                source_name=source_name,
                success=False,
                items_collected=0,
                error_message=str(e),
                collected_at=datetime.utcnow(),
            )

    def _count_items(self, source_name: str, data) -> int:
        """Count items in collected data"""
        if source_name == "google":
            if isinstance(data, dict):
                return len(data.get("emails", [])) + len(data.get("calendar_events", []))
        elif source_name == "weather":
            return 1  # Weather is a single data point
        elif source_name == "news":
            if isinstance(data, dict):
                return (
                    len(data.get("news_articles", []))
                    + len(data.get("ai_news_articles", []))
                    + len(data.get("competitor_news_articles", []))
                )
        elif isinstance(data, list):
            return len(data)
        return 0

    def _add_data_to_collection(
        self,
        collected_data: CollectedData,
        source_name: str,
        data
    ):
        """Add collected data to the CollectedData object"""
        try:
            if source_name == "google" and isinstance(data, dict):
                collected_data.emails.extend(data.get("emails", []))
                collected_data.calendar_events.extend(data.get("calendar_events", []))
            elif source_name == "slack":
                collected_data.slack_messages.extend(data)
            elif source_name == "gong":
                collected_data.gong_calls.extend(data)
            elif source_name == "monday":
                collected_data.monday_items.extend(data)
            elif source_name == "notion":
                collected_data.notion_pages.extend(data)
            elif source_name == "miro":
                collected_data.miro_boards.extend(data)
            elif source_name == "weather" and isinstance(data, dict):
                from models.data_sources import WeatherData
                # Convert weather dict to WeatherData model
                weather_data = WeatherData(
                    location=data.get("location", {}),
                    current_temperature=data.get("current", {}).get("temperature", 0),
                    feels_like=data.get("current", {}).get("feels_like", 0),
                    humidity=data.get("current", {}).get("humidity", 0),
                    description=data.get("current", {}).get("description", ""),
                    wind_speed=data.get("current", {}).get("wind_speed", 0),
                    visibility=data.get("current", {}).get("visibility", 0),
                    forecast=data.get("forecast", [])
                )
                collected_data.weather = weather_data
            elif source_name == "news" and isinstance(data, dict):
                from models.data_sources import NewsArticle

                # Convert general tech news articles
                articles = data.get("news_articles", [])
                for article in articles:
                    news_article = NewsArticle(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        content=article.get("content", ""),
                        source=article.get("source", ""),
                        published_date=article.get("published_date")
                    )
                    collected_data.news_articles.append(news_article)

                # Convert AI news articles
                ai_articles = data.get("ai_news_articles", [])
                for article in ai_articles:
                    news_article = NewsArticle(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        content=article.get("content", ""),
                        source=article.get("source", ""),
                        published_date=article.get("published_date")
                    )
                    collected_data.ai_news_articles.append(news_article)

                # Convert competitor news articles
                competitor_articles = data.get("competitor_news_articles", [])
                for article in competitor_articles:
                    news_article = NewsArticle(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        content=article.get("content", ""),
                        source=article.get("source", ""),
                        published_date=article.get("published_date")
                    )
                    collected_data.competitor_news_articles.append(news_article)

        except Exception as e:
            self.logger.warning(f"Failed to add data from {source_name}: {str(e)}")

    async def test_all_connections(self) -> Dict[str, any]:
        """Test connections to all data sources"""
        self.logger.info("Testing all connections...")

        results = {}
        for source_name, client in self.clients.items():
            try:
                async with client:
                    test_result = await client.test_connection()
                    results[source_name] = test_result
            except Exception as e:
                results[source_name] = {
                    "connected": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return results
