from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import NotionData


class NotionMCPClient(BaseMCPClient):
    """MCP Client for Notion"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_token = config.get("NOTION_API_TOKEN")
        self.api_url = "https://api.notion.com/v1"
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection to Notion"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
            )
            self.logger.info("Notion MCP client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Notion: {str(e)}")

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
    ) -> List[NotionData]:
        """
        Fetch Notion pages modified in specified date range

        Args:
            start_date: Start date
            end_date: End date (defaults to start_date)
        """
        if end_date is None:
            end_date = start_date

        try:
            # Search for pages edited in the date range
            pages = await self._search_pages(start_date, end_date)

            notion_pages = []
            for page in pages:
                notion_page = await self._parse_page(page)
                if notion_page:
                    notion_pages.append(notion_page)

            self.logger.info(f"Fetched {len(notion_pages)} Notion pages")
            return notion_pages

        except Exception as e:
            self.logger.error(f"Error fetching Notion pages: {str(e)}")
            raise MCPClientError(f"Failed to fetch Notion pages: {str(e)}")

    async def _search_pages(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Search for pages in date range"""
        url = f"{self.api_url}/search"

        # Convert to ISO format
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        payload = {
            "filter": {
                "value": "page",
                "property": "object"
            },
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time"
            }
        }

        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Filter by date range
            pages = []
            for page in data.get("results", []):
                last_edited = page.get("last_edited_time", "")
                if last_edited:
                    edited_dt = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                    if start_datetime <= edited_dt <= end_datetime:
                        pages.append(page)

            return pages

        except Exception as e:
            self.logger.warning(f"Failed to search pages: {str(e)}")
            return []

    async def _parse_page(self, page: Dict[str, Any]) -> Optional[NotionData]:
        """Parse Notion page into NotionData model"""
        try:
            page_id = page.get("id", "")

            # Extract title
            title = self._extract_title(page)

            # Parse timestamps
            created_time = datetime.fromisoformat(
                page.get("created_time", "").replace("Z", "+00:00")
            )
            last_edited_time = datetime.fromisoformat(
                page.get("last_edited_time", "").replace("Z", "+00:00")
            )

            # Parent info
            parent = page.get("parent", {})
            parent_type = parent.get("type")
            parent_id = parent.get(parent_type) if parent_type else None

            # Extract properties
            properties = self._extract_properties(page.get("properties", {}))

            # Fetch page content
            content = await self._fetch_page_content(page_id)

            return NotionData(
                page_id=page_id,
                title=title,
                parent_id=parent_id,
                parent_type=parent_type,
                created_time=created_time,
                last_edited_time=last_edited_time,
                created_by=page.get("created_by", {}).get("id"),
                last_edited_by=page.get("last_edited_by", {}).get("id"),
                content=content,
                properties=properties,
                url=page.get("url"),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse page: {str(e)}")
            return None

    def _extract_title(self, page: Dict[str, Any]) -> str:
        """Extract page title from properties"""
        properties = page.get("properties", {})

        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    return "".join([t.get("plain_text", "") for t in title_array])

        return "Untitled"

    def _extract_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and simplify properties"""
        simplified = {}

        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")

            if prop_type == "title":
                title_array = prop_data.get("title", [])
                simplified[prop_name] = "".join([t.get("plain_text", "") for t in title_array])
            elif prop_type == "rich_text":
                text_array = prop_data.get("rich_text", [])
                simplified[prop_name] = "".join([t.get("plain_text", "") for t in text_array])
            elif prop_type == "select":
                select = prop_data.get("select")
                simplified[prop_name] = select.get("name") if select else None
            elif prop_type == "multi_select":
                multi_select = prop_data.get("multi_select", [])
                simplified[prop_name] = [s.get("name") for s in multi_select]
            elif prop_type == "date":
                date_obj = prop_data.get("date")
                if date_obj:
                    simplified[prop_name] = date_obj.get("start")
            else:
                simplified[prop_name] = prop_data

        return simplified

    async def _fetch_page_content(self, page_id: str) -> str:
        """Fetch page content as markdown"""
        try:
            url = f"{self.api_url}/blocks/{page_id}/children"
            response = await self.http_client.get(url)

            if response.status_code != 200:
                return ""

            data = response.json()
            blocks = data.get("results", [])

            # Simple markdown conversion
            content_parts = []
            for block in blocks:
                block_type = block.get("type")
                block_data = block.get(block_type, {})

                if block_type == "paragraph":
                    text = self._extract_text_from_block(block_data)
                    if text:
                        content_parts.append(text)
                elif block_type in ["heading_1", "heading_2", "heading_3"]:
                    text = self._extract_text_from_block(block_data)
                    level = block_type[-1]
                    if text:
                        content_parts.append(f"{'#' * int(level)} {text}")
                elif block_type == "bulleted_list_item":
                    text = self._extract_text_from_block(block_data)
                    if text:
                        content_parts.append(f"- {text}")

            return "\n\n".join(content_parts)

        except Exception as e:
            self.logger.warning(f"Failed to fetch page content: {str(e)}")
            return ""

    def _extract_text_from_block(self, block_data: Dict[str, Any]) -> str:
        """Extract plain text from block"""
        rich_text = block_data.get("rich_text", [])
        return "".join([t.get("plain_text", "") for t in rich_text])

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Notion"""
        try:
            url = f"{self.api_url}/users/me"
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
