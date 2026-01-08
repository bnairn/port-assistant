from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import GongData


class GongMCPClient(BaseMCPClient):
    """MCP Client for Gong.io"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_key = config.get("GONG_ACCESS_KEY")
        self.access_key_secret = config.get("GONG_ACCESS_KEY_SECRET")
        self.base_url = config.get("GONG_BASE_URL", "https://api.gong.io/v2")
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection to Gong"""
        try:
            # Gong uses Basic Auth with access key and secret
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                auth=(self.access_key, self.access_key_secret),
                headers={
                    "Content-Type": "application/json"
                }
            )
            self.logger.info("Gong MCP client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Gong: {str(e)}")

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
    ) -> List[GongData]:
        """
        Fetch Gong call recordings with AI-extracted content from specified date range

        Args:
            start_date: Start date for calls
            end_date: End date (defaults to start_date)
        """
        if end_date is None:
            end_date = start_date

        try:
            # Use /v2/calls/extensive to get AI-extracted content
            from_datetime = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
            to_datetime = datetime.combine(end_date, datetime.max.time()).isoformat() + "Z"

            url = f"{self.base_url}/calls/extensive"

            # Request AI-extracted content fields
            payload = {
                "filter": {
                    "fromDateTime": from_datetime,
                    "toDateTime": to_datetime
                },
                "contentSelector": {
                    "context": "Extended",
                    "exposedFields": {
                        "content": {
                            "topics": True,
                            "brief": True,
                            "outline": True,
                            "highlights": True,
                            "keyPoints": True,
                            "callOutcome": True
                        },
                        "parties": True
                    }
                }
            }

            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            calls = []
            for call_item in data.get("calls", []):
                call_data = await self._parse_extensive_call(call_item)
                if call_data:
                    calls.append(call_data)

            self.logger.info(f"Fetched {len(calls)} Gong calls with AI content")
            return calls

        except Exception as e:
            self.logger.error(f"Error fetching Gong calls: {str(e)}")
            raise MCPClientError(f"Failed to fetch Gong calls: {str(e)}")

    async def _parse_extensive_call(self, call_item: Dict[str, Any]) -> Optional[GongData]:
        """Parse extensive call data with AI content into GongData model"""
        try:
            metadata = call_item.get("metaData", {})
            content = call_item.get("content", {})
            parties = call_item.get("parties", [])

            call_id = metadata.get("id", "")

            # Parse started time
            started = metadata.get("started")
            call_date = datetime.fromisoformat(started.replace("Z", "+00:00")) if started else datetime.utcnow()

            # Extract participants from parties
            participants = []
            customer_name = None

            for party in parties:
                name = party.get("name", "")
                if name:
                    participants.append(name)
                    # Try to identify customer (external party)
                    if party.get("context") == "External" or party.get("affiliation") != "Internal":
                        if not customer_name:
                            customer_name = name

            # Extract AI content
            brief = content.get("brief", "")
            topics = content.get("topics", [])
            key_points = content.get("keyPoints", [])
            highlights = content.get("highlights", [])
            call_outcome = content.get("callOutcome", {})

            # Format topics into strings
            topic_names = [topic.get("name", "") for topic in topics if isinstance(topic, dict)]

            # Format key points into action items
            action_items = []
            if isinstance(key_points, list):
                for kp in key_points:
                    if isinstance(kp, dict):
                        action_items.append(kp.get("text", ""))
                    elif isinstance(kp, str):
                        action_items.append(kp)

            # Extract highlights as additional context
            highlight_texts = []
            if isinstance(highlights, list):
                for highlight in highlights[:3]:  # Top 3 highlights
                    if isinstance(highlight, dict):
                        highlight_texts.append(highlight.get("text", ""))
                    elif isinstance(highlight, str):
                        highlight_texts.append(highlight)

            return GongData(
                call_id=call_id,
                title=metadata.get("title", ""),
                date=call_date,
                duration_minutes=metadata.get("duration", 0) // 60,
                participants=participants,
                customer_name=customer_name,
                summary=brief,  # AI-generated brief
                key_topics=topic_names,  # AI-extracted topics
                action_items=action_items,  # AI-extracted key points
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse extensive call: {str(e)}")
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Gong"""
        try:
            # Try to fetch users as a simple test
            url = f"{self.base_url}/users"
            response = await self.http_client.get(url)

            return {
                "connected": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
