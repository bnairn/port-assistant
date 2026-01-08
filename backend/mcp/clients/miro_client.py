from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import MiroData


class MiroMCPClient(BaseMCPClient):
    """MCP Client for Miro"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get("MIRO_ACCESS_TOKEN")
        self.api_url = "https://api.miro.com/v2"
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection to Miro"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            self.logger.info("Miro MCP client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Miro: {str(e)}")

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
    ) -> List[MiroData]:
        """
        Fetch Miro boards modified in specified date range

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
        """
        if end_date is None:
            end_date = start_date

        try:
            # Get all boards
            boards = await self._get_boards()

            # Filter by modification date
            filtered_boards = []
            for board in boards:
                modified_at = board.get("modifiedAt")
                if modified_at:
                    modified_dt = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
                    if start_date <= modified_dt.date() <= end_date:
                        miro_board = await self._parse_board(board)
                        if miro_board:
                            filtered_boards.append(miro_board)

            self.logger.info(f"Fetched {len(filtered_boards)} Miro boards")
            return filtered_boards

        except Exception as e:
            self.logger.error(f"Error fetching Miro boards: {str(e)}")
            raise MCPClientError(f"Failed to fetch Miro boards: {str(e)}")

    async def _get_boards(self) -> List[Dict[str, Any]]:
        """Get all accessible boards"""
        try:
            url = f"{self.api_url}/boards"
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()

            return data.get("data", [])

        except Exception as e:
            self.logger.warning(f"Failed to get boards: {str(e)}")
            return []

    async def _parse_board(self, board: Dict[str, Any]) -> Optional[MiroData]:
        """Parse Miro board into MiroData model"""
        try:
            board_id = board.get("id", "")

            # Parse timestamps
            created_at = datetime.fromisoformat(
                board.get("createdAt", "").replace("Z", "+00:00")
            )
            modified_at = datetime.fromisoformat(
                board.get("modifiedAt", "").replace("Z", "+00:00")
            )

            # Get owner info
            owner_info = board.get("owner", {})
            owner = owner_info.get("name") or owner_info.get("id")

            # Get board statistics
            stats = await self._get_board_stats(board_id)

            return MiroData(
                board_id=board_id,
                board_name=board.get("name", "Untitled Board"),
                description=board.get("description"),
                created_at=created_at,
                modified_at=modified_at,
                owner=owner,
                team_id=board.get("team", {}).get("id"),
                item_count=stats.get("item_count", 0),
                frame_count=stats.get("frame_count", 0),
                url=board.get("viewLink"),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse board: {str(e)}")
            return None

    async def _get_board_stats(self, board_id: str) -> Dict[str, int]:
        """Get statistics for a board (item count, frame count)"""
        try:
            # Get items
            items_url = f"{self.api_url}/boards/{board_id}/items"
            items_response = await self.http_client.get(items_url, params={"limit": 1})

            item_count = 0
            if items_response.status_code == 200:
                items_data = items_response.json()
                item_count = items_data.get("total", 0)

            # Count frames (a type of item in Miro)
            frames_url = f"{self.api_url}/boards/{board_id}/items"
            frames_response = await self.http_client.get(
                frames_url,
                params={"type": "frame", "limit": 1}
            )

            frame_count = 0
            if frames_response.status_code == 200:
                frames_data = frames_response.json()
                frame_count = frames_data.get("total", 0)

            return {
                "item_count": item_count,
                "frame_count": frame_count,
            }

        except Exception as e:
            self.logger.warning(f"Failed to get board stats: {str(e)}")
            return {"item_count": 0, "frame_count": 0}

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Miro"""
        try:
            url = f"{self.api_url}/boards"
            response = await self.http_client.get(url, params={"limit": 1})

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
