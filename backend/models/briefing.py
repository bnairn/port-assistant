from pydantic import BaseModel, Field
from datetime import datetime
from datetime import date as DateType
from typing import List, Optional, Dict, Any
from enum import Enum


class BriefingStatus(str, Enum):
    """Status of briefing generation"""
    PENDING = "pending"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BriefingSection(BaseModel):
    """Individual section within a briefing"""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content in markdown format")
    priority: int = Field(default=0, description="Priority for ordering (higher = more important)")
    source_count: int = Field(default=0, description="Number of data sources contributing to this section")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BriefingSummary(BaseModel):
    """Executive summary for the briefing"""
    key_highlights: List[str] = Field(default_factory=list, description="Top 3-5 key highlights")
    action_items: List[str] = Field(default_factory=list, description="Recommended actions")
    overall_sentiment: Optional[str] = Field(None, description="Overall sentiment (positive/neutral/negative)")


class DataSourceStatus(BaseModel):
    """Status of data collection from a single source"""
    source_name: str = Field(..., description="Name of the data source")
    status: str = Field(..., description="Collection status (success/failed/pending)")
    items_collected: int = Field(default=0, description="Number of items collected")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    collected_at: Optional[datetime] = Field(None, description="Timestamp of collection")


class Briefing(BaseModel):
    """Complete daily briefing model"""
    id: str = Field(..., description="Unique briefing identifier")
    date: DateType = Field(..., description="Date this briefing covers")
    status: BriefingStatus = Field(default=BriefingStatus.PENDING, description="Current status")

    # Core content
    summary: Optional[BriefingSummary] = Field(None, description="Executive summary")
    sections: List[BriefingSection] = Field(default_factory=list, description="Briefing sections")

    # Metadata
    generated_at: Optional[datetime] = Field(None, description="When briefing was generated")
    processing_time_seconds: Optional[float] = Field(None, description="Time taken to generate")

    # Data source tracking
    data_sources: List[DataSourceStatus] = Field(
        default_factory=list,
        description="Status of each data source"
    )

    # Raw data (for debugging/auditing)
    raw_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw collected data (optional, for debugging)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "briefing-2026-01-07",
                "date": "2026-01-07",
                "status": "completed",
                "summary": {
                    "key_highlights": [
                        "Q1 demo calls show 15% increase in feature requests",
                        "Product marketing campaign draft needs review by EOD",
                        "3 high-priority customer issues escalated from support"
                    ],
                    "action_items": [
                        "Review PMM campaign draft in Notion",
                        "Schedule follow-up calls for top 3 demo prospects"
                    ]
                },
                "sections": [
                    {
                        "title": "Customer Calls & Demos",
                        "content": "## Recent Calls\n- Acme Corp demo went well...",
                        "priority": 10,
                        "source_count": 2
                    }
                ],
                "data_sources": [
                    {
                        "source_name": "gmail",
                        "status": "success",
                        "items_collected": 45,
                        "collected_at": "2026-01-07T09:00:00Z"
                    }
                ]
            }
        }


class BriefingCreateRequest(BaseModel):
    """Request to generate a new briefing"""
    target_date: Optional[DateType] = Field(None, description="Date to generate briefing for (default: today)")
    include_raw_data: bool = Field(default=False, description="Include raw data in response")
    force_regenerate: bool = Field(default=False, description="Force regeneration if already exists")


class BriefingResponse(BaseModel):
    """Response when requesting or generating a briefing"""
    briefing: Briefing
    message: Optional[str] = None
