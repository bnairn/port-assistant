from typing import Any, Dict, List, Optional
from datetime import date, datetime
import httpx
from ..base_client import BaseMCPClient, MCPClientError


class NewsMCPClient(BaseMCPClient):
    """
    MCP Client for Tavily News API
    Fetches top world news headlines
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("TAVILY_API_KEY")
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            self.logger.info("News client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Tavily API: {str(e)}")

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> Dict[str, List[Any]]:
        """
        Fetch top world news headlines

        Returns:
            Dictionary with 'news_articles' key
        """
        articles = await self.fetch_top_news()

        return {
            "news_articles": articles
        }

    async def fetch_top_news(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """Fetch top world news headlines using Tavily"""
        try:
            url = "https://api.tavily.com/search"

            payload = {
                "api_key": self.api_key,
                "query": "top world news headlines today",
                "search_depth": "basic",
                "include_answer": False,
                "include_images": False,
                "include_raw_content": False,
                "max_results": max_results,
                "include_domains": [],
                "exclude_domains": [],
                "topic": "news"  # Focus on news content
            }

            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            articles = []
            for result in data.get("results", [])[:max_results]:
                articles.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                    "published_date": result.get("published_date")
                })

            self.logger.info(f"Fetched {len(articles)} news articles")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching news: {str(e)}")
            raise MCPClientError(f"Failed to fetch news: {str(e)}")

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Tavily API"""
        try:
            # Try to fetch one article as a test
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": "test",
                "max_results": 1
            }

            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()

            return {
                "connected": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
