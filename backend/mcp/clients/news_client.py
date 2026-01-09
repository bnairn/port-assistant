from typing import Any, Dict, List, Optional
from datetime import date, datetime
import httpx
from ..base_client import BaseMCPClient, MCPClientError


class NewsMCPClient(BaseMCPClient):
    """
    MCP Client for NewsAPI.org
    Fetches tech news, AI news, and competitor news with comprehensive filtering
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("NEWSAPI_API_KEY")
        self.base_url = "https://newsapi.org/v2"
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            self.logger.info("NewsAPI client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to NewsAPI: {str(e)}")

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
        Fetch news articles from multiple categories

        Returns:
            Dictionary with 'news_articles', 'ai_news_articles', 'competitor_news_articles' keys
        """
        # Fetch all news types in parallel
        import asyncio

        tech_news_task = self.fetch_top_news(max_results=5)
        ai_news_task = self.fetch_ai_news(max_results=10)
        competitor_news_task = self.fetch_competitor_news(max_results=10)

        tech_articles, ai_articles, competitor_articles = await asyncio.gather(
            tech_news_task,
            ai_news_task,
            competitor_news_task,
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(tech_articles, Exception):
            self.logger.error(f"Error fetching tech news: {tech_articles}")
            tech_articles = []
        if isinstance(ai_articles, Exception):
            self.logger.error(f"Error fetching AI news: {ai_articles}")
            ai_articles = []
        if isinstance(competitor_articles, Exception):
            self.logger.error(f"Error fetching competitor news: {competitor_articles}")
            competitor_articles = []

        return {
            "news_articles": tech_articles,
            "ai_news_articles": ai_articles,
            "competitor_news_articles": competitor_articles
        }

    async def fetch_top_news(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch top tech news headlines using NewsAPI
        This is kept for backwards compatibility but returns general tech news
        """
        try:
            url = f"{self.base_url}/everything"

            params = {
                "apiKey": self.api_key,
                "q": "technology OR tech",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_results,
                "domains": "techcrunch.com,theverge.com,arstechnica.com,wired.com,venturebeat.com,zdnet.com"
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for article in data.get("articles", [])[:max_results]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "content": article.get("description", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_date": article.get("publishedAt")
                })

            self.logger.info(f"Fetched {len(articles)} tech news articles")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching news: {str(e)}")
            raise MCPClientError(f"Failed to fetch news: {str(e)}")

    async def fetch_ai_news(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch AI/ML news from top tech publications

        Args:
            max_results: Maximum number of articles to return

        Returns:
            List of articles with title, url, content, source, published_date
        """
        try:
            url = f"{self.base_url}/everything"

            # Query for AI/ML news from reputable tech sources
            params = {
                "apiKey": self.api_key,
                "q": "\"artificial intelligence\" OR \"machine learning\" OR \"AI\" OR \"LLM\" OR \"GPT\" OR \"Claude\" OR \"ChatGPT\" OR \"deep learning\"",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_results,
                "domains": "techcrunch.com,theverge.com,arstechnica.com,wired.com,venturebeat.com,zdnet.com,artificialintelligence-news.com,simonwillison.net"
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for article in data.get("articles", [])[:max_results]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "content": article.get("description", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_date": article.get("publishedAt")
                })

            self.logger.info(f"Fetched {len(articles)} AI news articles")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching AI news: {str(e)}")
            raise MCPClientError(f"Failed to fetch AI news: {str(e)}")

    async def fetch_competitor_news(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch news about internal developer platforms and Port competitors

        Args:
            max_results: Maximum number of articles to return

        Returns:
            List of articles with title, url, content, source, published_date
        """
        try:
            url = f"{self.base_url}/everything"

            # Query for competitor and IDP news
            params = {
                "apiKey": self.api_key,
                "q": "\"backstage\" OR \"cortex\" OR \"opslevel\" OR \"roadie\" OR \"internal developer portal\" OR \"IDP\" OR \"platform engineering\" OR \"developer experience\"",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": max_results,
                "domains": "techcrunch.com,theverge.com,infoq.com,thenewstack.io,devops.com,venturebeat.com,zdnet.com"
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for article in data.get("articles", [])[:max_results]:
                articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "content": article.get("description", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_date": article.get("publishedAt")
                })

            self.logger.info(f"Fetched {len(articles)} competitor news articles")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching competitor news: {str(e)}")
            raise MCPClientError(f"Failed to fetch competitor news: {str(e)}")

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to NewsAPI"""
        try:
            # Try to fetch one article as a test
            url = f"{self.base_url}/everything"
            params = {
                "apiKey": self.api_key,
                "q": "test",
                "pageSize": 1
            }

            response = await self.http_client.get(url, params=params)
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
