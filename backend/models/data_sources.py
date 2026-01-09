from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class DataSourceType(str, Enum):
    """Supported data source types"""
    GMAIL = "gmail"
    GOOGLE_CALENDAR = "google_calendar"
    SLACK = "slack"
    GONG = "gong"
    MONDAY = "monday"
    NOTION = "notion"
    MIRO = "miro"
    WEATHER = "weather"
    NEWS = "news"


class DataSource(BaseModel):
    """Base data source model"""
    source_type: DataSourceType
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    item_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmailData(BaseModel):
    """Email data from Gmail"""
    id: str = Field(..., description="Email message ID")
    thread_id: str = Field(..., description="Email thread ID")
    subject: str = Field(..., description="Email subject")
    from_email: str = Field(..., description="Sender email")
    from_name: Optional[str] = Field(None, description="Sender name")
    to_emails: List[str] = Field(default_factory=list, description="Recipient emails")
    cc_emails: List[str] = Field(default_factory=list, description="CC emails")
    date: datetime = Field(..., description="Email date")
    body: str = Field(..., description="Email body text")
    labels: List[str] = Field(default_factory=list, description="Gmail labels")
    is_important: bool = Field(default=False, description="Marked as important")
    has_attachments: bool = Field(default=False, description="Has attachments")
    snippet: str = Field(default="", description="Email snippet/preview")


class CalendarEvent(BaseModel):
    """Calendar event from Google Calendar"""
    id: str = Field(..., description="Event ID")
    summary: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    location: Optional[str] = Field(None, description="Event location")
    attendees: List[str] = Field(default_factory=list, description="Attendee emails")
    organizer: Optional[str] = Field(None, description="Organizer email")
    meeting_type: Optional[str] = Field(None, description="Type of meeting (customer call, internal, etc.)")
    is_all_day: bool = Field(default=False, description="All-day event")


class SlackData(BaseModel):
    """Slack message data"""
    channel_id: str = Field(..., description="Slack channel ID")
    channel_name: str = Field(..., description="Slack channel name")
    message_id: str = Field(..., description="Message timestamp/ID")
    user_id: str = Field(..., description="User ID who sent message")
    user_name: Optional[str] = Field(None, description="User display name")
    text: str = Field(..., description="Message text")
    timestamp: datetime = Field(..., description="Message timestamp")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp if in thread")
    reactions: List[str] = Field(default_factory=list, description="Emoji reactions")
    reply_count: int = Field(default=0, description="Number of replies")
    is_mention: bool = Field(default=False, description="User was mentioned")
    is_dm: bool = Field(default=False, description="Message is a direct message")
    is_dm_unanswered: bool = Field(default=False, description="DM has not been answered")
    is_vip_thread: bool = Field(default=False, description="High-engagement thread")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Message attachments")


class GongData(BaseModel):
    """Gong call recording data"""
    call_id: str = Field(..., description="Gong call ID")
    title: str = Field(..., description="Call title")
    date: datetime = Field(..., description="Call date/time")
    duration_minutes: int = Field(..., description="Call duration in minutes")
    participants: List[str] = Field(default_factory=list, description="Call participants")
    customer_name: Optional[str] = Field(None, description="Customer/prospect name")
    deal_stage: Optional[str] = Field(None, description="Deal stage")
    transcript: Optional[str] = Field(None, description="Call transcript")
    summary: Optional[str] = Field(None, description="Call summary")
    key_topics: List[str] = Field(default_factory=list, description="Key topics discussed")
    action_items: List[str] = Field(default_factory=list, description="Action items from call")
    sentiment_score: Optional[float] = Field(None, description="Call sentiment score")
    next_steps: Optional[str] = Field(None, description="Agreed next steps")


class MondayData(BaseModel):
    """Monday.com board/item data"""
    item_id: str = Field(..., description="Monday item ID")
    board_id: str = Field(..., description="Board ID")
    board_name: str = Field(..., description="Board name")
    item_name: str = Field(..., description="Item name")
    status: Optional[str] = Field(None, description="Status column value")
    owner: Optional[str] = Field(None, description="Item owner")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    due_date: Optional[datetime] = Field(None, description="Due date if set")
    priority: Optional[str] = Field(None, description="Priority level")
    column_values: Dict[str, Any] = Field(default_factory=dict, description="All column values")
    updates: List[Dict[str, Any]] = Field(default_factory=list, description="Recent updates/comments")


class NotionData(BaseModel):
    """Notion page data"""
    page_id: str = Field(..., description="Notion page ID")
    title: str = Field(..., description="Page title")
    parent_id: Optional[str] = Field(None, description="Parent page/database ID")
    parent_type: Optional[str] = Field(None, description="Parent type (page/database/workspace)")
    created_time: datetime = Field(..., description="Creation timestamp")
    last_edited_time: datetime = Field(..., description="Last edit timestamp")
    created_by: Optional[str] = Field(None, description="Creator user ID")
    last_edited_by: Optional[str] = Field(None, description="Last editor user ID")
    content: str = Field(default="", description="Page content (markdown)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Page properties")
    tags: List[str] = Field(default_factory=list, description="Tags/categories")
    url: Optional[str] = Field(None, description="Public URL if shared")


class MiroData(BaseModel):
    """Miro board data"""
    board_id: str = Field(..., description="Miro board ID")
    board_name: str = Field(..., description="Board name")
    description: Optional[str] = Field(None, description="Board description")
    created_at: datetime = Field(..., description="Creation timestamp")
    modified_at: datetime = Field(..., description="Last modification timestamp")
    owner: Optional[str] = Field(None, description="Board owner")
    team_id: Optional[str] = Field(None, description="Team ID")
    item_count: int = Field(default=0, description="Number of items on board")
    frame_count: int = Field(default=0, description="Number of frames")
    tags: List[str] = Field(default_factory=list, description="Board tags")
    recent_activity: Optional[str] = Field(None, description="Summary of recent activity")
    url: Optional[str] = Field(None, description="Board URL")


class WeatherData(BaseModel):
    """Weather data from OpenWeather"""
    location: Dict[str, Any] = Field(..., description="Location information")
    current_temperature: float = Field(..., description="Current temperature (F)")
    feels_like: float = Field(..., description="Feels like temperature (F)")
    humidity: int = Field(..., description="Humidity percentage")
    description: str = Field(..., description="Weather description")
    wind_speed: float = Field(..., description="Wind speed (mph)")
    visibility: float = Field(..., description="Visibility (miles)")
    forecast: List[Dict[str, Any]] = Field(default_factory=list, description="24-hour forecast")


class NewsArticle(BaseModel):
    """News article data from NewsAPI"""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    content: str = Field(..., description="Article content/summary")
    source: str = Field(default="", description="Article source/publication")
    published_date: Optional[str] = Field(None, description="Published date")


class CollectedData(BaseModel):
    """Container for all collected data from various sources"""
    collection_date: datetime = Field(default_factory=datetime.utcnow)

    # Data from each source
    emails: List[EmailData] = Field(default_factory=list)
    calendar_events: List[CalendarEvent] = Field(default_factory=list)
    slack_messages: List[SlackData] = Field(default_factory=list)
    gong_calls: List[GongData] = Field(default_factory=list)
    monday_items: List[MondayData] = Field(default_factory=list)
    notion_pages: List[NotionData] = Field(default_factory=list)
    miro_boards: List[MiroData] = Field(default_factory=list)
    weather: Optional[WeatherData] = None
    news_articles: List[NewsArticle] = Field(default_factory=list)
    ai_news_articles: List[NewsArticle] = Field(default_factory=list)
    competitor_news_articles: List[NewsArticle] = Field(default_factory=list)

    def get_total_items(self) -> int:
        """Get total number of items collected across all sources"""
        return (
            len(self.emails)
            + len(self.calendar_events)
            + len(self.slack_messages)
            + len(self.gong_calls)
            + len(self.monday_items)
            + len(self.notion_pages)
            + len(self.miro_boards)
            + (1 if self.weather else 0)
            + len(self.news_articles)
            + len(self.ai_news_articles)
            + len(self.competitor_news_articles)
        )

    def get_source_counts(self) -> Dict[str, int]:
        """Get count of items per source"""
        return {
            "gmail": len(self.emails),
            "google_calendar": len(self.calendar_events),
            "slack": len(self.slack_messages),
            "gong": len(self.gong_calls),
            "monday": len(self.monday_items),
            "notion": len(self.notion_pages),
            "miro": len(self.miro_boards),
            "weather": 1 if self.weather else 0,
            "news": len(self.news_articles),
        }
