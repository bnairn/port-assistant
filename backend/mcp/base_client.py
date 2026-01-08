from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors"""
    pass


class BaseMCPClient(ABC):
    """
    Base class for all MCP (Model Context Protocol) clients.
    Each data source (Google, Slack, Gong, etc.) will implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the MCP client with configuration

        Args:
            config: Dictionary containing API keys, tokens, and other config
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the data source

        Returns:
            True if connection successful, False otherwise

        Raises:
            MCPClientError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source"""
        pass

    @abstractmethod
    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> List[Any]:
        """
        Fetch data from the source for the specified date range

        Args:
            start_date: Start date for data collection
            end_date: End date for data collection (optional, defaults to start_date)
            **kwargs: Additional source-specific parameters

        Returns:
            List of data items from the source

        Raises:
            MCPClientError: If data fetch fails
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the data source

        Returns:
            Dictionary with connection status and metadata
        """
        pass

    def get_source_name(self) -> str:
        """Get the name of this data source"""
        return self.__class__.__name__.replace("MCPClient", "").lower()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
