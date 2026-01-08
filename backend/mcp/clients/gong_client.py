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
        Fetch Gong call recordings from specified date range

        Args:
            start_date: Start date for calls
            end_date: End date (defaults to start_date)
        """
        if end_date is None:
            end_date = start_date

        try:
            # Fetch calls using GET with query parameters
            from_datetime = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
            to_datetime = datetime.combine(end_date, datetime.max.time()).isoformat() + "Z"

            url = f"{self.base_url}/calls"
            params = {
                "fromDateTime": from_datetime,
                "toDateTime": to_datetime
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            calls = []
            for call_item in data.get("calls", []):
                call_data = await self._parse_call(call_item)
                if call_data:
                    calls.append(call_data)

            self.logger.info(f"Fetched {len(calls)} Gong calls")
            return calls

        except Exception as e:
            self.logger.error(f"Error fetching Gong calls: {str(e)}")
            raise MCPClientError(f"Failed to fetch Gong calls: {str(e)}")

    async def _parse_call(self, call_item: Dict[str, Any]) -> Optional[GongData]:
        """Parse call data into GongData model"""
        try:
            call_id = call_item.get("id", "")

            # Fetch detailed call info
            detailed_data = await self._fetch_call_details(call_id)

            # Parse started time
            started = call_item.get("started")
            call_date = datetime.fromisoformat(started.replace("Z", "+00:00")) if started else datetime.utcnow()

            # Extract participants
            participants = []
            for party in call_item.get("parties", []):
                name = party.get("name", "")
                if name:
                    participants.append(name)

            return GongData(
                call_id=call_id,
                title=call_item.get("title", ""),
                date=call_date,
                duration_minutes=call_item.get("duration", 0) // 60,
                participants=participants,
                customer_name=detailed_data.get("customer_name"),
                summary=detailed_data.get("summary"),
                key_topics=detailed_data.get("key_topics", []),
                action_items=detailed_data.get("action_items", []),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse call: {str(e)}")
            return None

    async def _fetch_call_details(self, call_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific call"""
        try:
            url = f"{self.base_url}/calls/{call_id}"
            response = await self.http_client.get(url)

            if response.status_code == 200:
                return response.json()

            return {}

        except Exception as e:
            self.logger.warning(f"Failed to fetch call details for {call_id}: {str(e)}")
            return {}

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
