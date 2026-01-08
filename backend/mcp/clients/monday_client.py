from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import MondayData


class MondayMCPClient(BaseMCPClient):
    """MCP Client for Monday.com"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("MONDAY_API_KEY")
        self.api_url = "https://api.monday.com/v2"
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection to Monday.com"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": self.api_key,
                    "Content-Type": "application/json"
                }
            )
            self.logger.info("Monday MCP client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Monday: {str(e)}")

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        board_ids: Optional[List[int]] = None,
        **kwargs
    ) -> List[MondayData]:
        """
        Fetch Monday.com items from specified date range

        Args:
            start_date: Start date for items
            end_date: End date (defaults to start_date)
            board_ids: List of board IDs to fetch from (None = all boards)
        """
        if end_date is None:
            end_date = start_date

        try:
            # If no board IDs specified, get all boards
            if board_ids is None:
                board_ids = await self._get_board_ids()

            items = []
            for board_id in board_ids:
                board_items = await self._fetch_board_items(board_id, start_date, end_date)
                items.extend(board_items)

            self.logger.info(f"Fetched {len(items)} Monday.com items")
            return items

        except Exception as e:
            self.logger.error(f"Error fetching Monday items: {str(e)}")
            raise MCPClientError(f"Failed to fetch Monday items: {str(e)}")

    async def _get_board_ids(self) -> List[int]:
        """Get list of all board IDs"""
        query = """
        query {
            boards {
                id
            }
        }
        """

        try:
            response = await self.http_client.post(
                self.api_url,
                json={"query": query}
            )
            data = response.json()

            boards = data.get("data", {}).get("boards", [])
            return [int(board["id"]) for board in boards]

        except Exception as e:
            self.logger.warning(f"Failed to get board IDs: {str(e)}")
            return []

    async def _fetch_board_items(
        self,
        board_id: int,
        start_date: date,
        end_date: date
    ) -> List[MondayData]:
        """Fetch items from a specific board"""
        query = """
        query ($boardId: ID!) {
            boards(ids: [$boardId]) {
                id
                name
                items_page {
                    items {
                        id
                        name
                        created_at
                        updated_at
                        column_values {
                            id
                            text
                            value
                        }
                        updates {
                            id
                            body
                            created_at
                        }
                    }
                }
            }
        }
        """

        try:
            response = await self.http_client.post(
                self.api_url,
                json={"query": query, "variables": {"boardId": str(board_id)}}
            )
            data = response.json()

            boards = data.get("data", {}).get("boards", [])
            if not boards:
                return []

            board = boards[0]
            board_name = board.get("name", "")
            items_data = board.get("items_page", {}).get("items", [])

            items = []
            for item in items_data:
                monday_item = self._parse_item(item, board_id, board_name, start_date, end_date)
                if monday_item:
                    items.append(monday_item)

            return items

        except Exception as e:
            self.logger.warning(f"Failed to fetch board {board_id}: {str(e)}")
            return []

    def _parse_item(
        self,
        item: Dict[str, Any],
        board_id: int,
        board_name: str,
        start_date: date,
        end_date: date
    ) -> Optional[MondayData]:
        """Parse Monday item into MondayData model"""
        try:
            # Parse dates
            created_at = datetime.fromisoformat(item.get("created_at", "").replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00"))

            # Filter by date range
            if created_at.date() < start_date or created_at.date() > end_date:
                if updated_at.date() < start_date or updated_at.date() > end_date:
                    return None

            # Parse column values
            column_values = {}
            status = None
            owner = None
            due_date = None
            priority = None

            for col in item.get("column_values", []):
                col_id = col.get("id", "")
                col_text = col.get("text", "")
                column_values[col_id] = col_text

                # Extract common columns
                if col_id == "status":
                    status = col_text
                elif col_id == "person":
                    owner = col_text
                elif col_id in ["date", "due_date"]:
                    if col_text:
                        try:
                            due_date = datetime.fromisoformat(col_text)
                        except:
                            pass
                elif col_id == "priority":
                    priority = col_text

            # Parse updates
            updates = []
            for update in item.get("updates", [])[:5]:  # Limit to 5 recent updates
                updates.append({
                    "id": update.get("id"),
                    "body": update.get("body"),
                    "created_at": update.get("created_at"),
                })

            return MondayData(
                item_id=item.get("id", ""),
                board_id=str(board_id),
                board_name=board_name,
                item_name=item.get("name", ""),
                status=status,
                owner=owner,
                created_at=created_at,
                updated_at=updated_at,
                due_date=due_date,
                priority=priority,
                column_values=column_values,
                updates=updates,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse item: {str(e)}")
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Monday.com"""
        query = "query { me { name } }"

        try:
            response = await self.http_client.post(
                self.api_url,
                json={"query": query}
            )
            data = response.json()

            return {
                "connected": "data" in data and "me" in data["data"],
                "user": data.get("data", {}).get("me", {}).get("name"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
