from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import date, datetime
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class CollectionResult(BaseModel):
    """Result of data collection from a source"""
    source_name: str
    success: bool
    items_collected: int = 0
    error_message: Optional[str] = None
    collected_at: datetime
    data: Optional[Any] = None


class BaseCollector(ABC):
    """
    Base class for data collectors.
    Collectors orchestrate MCP clients to gather data from various sources.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize collector with configuration

        Args:
            config: Dictionary containing API keys, tokens, and other config
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def collect(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> CollectionResult:
        """
        Collect data from the source

        Args:
            start_date: Start date for data collection
            end_date: End date for data collection (optional, defaults to start_date)
            **kwargs: Additional source-specific parameters

        Returns:
            CollectionResult with status and collected data
        """
        pass

    def get_collector_name(self) -> str:
        """Get the name of this collector"""
        return self.__class__.__name__.replace("Collector", "").lower()
