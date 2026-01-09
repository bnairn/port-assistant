from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    # FastAPI
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    API_PORT: int = 8000

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]

    # Anthropic (Required)
    ANTHROPIC_API_KEY: str

    # Google Workspace (Optional - required for Gmail/Calendar integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REFRESH_TOKEN: str = ""

    # Slack (Optional - required for Slack integration)
    SLACK_BOT_TOKEN: str = ""
    SLACK_APP_TOKEN: str = ""

    # Gong (Optional - required for call recording integration)
    GONG_ACCESS_KEY: str = ""
    GONG_ACCESS_KEY_SECRET: str = ""
    GONG_BASE_URL: str = "https://api.gong.io/v2"

    # Monday.com (Optional - required for project management integration)
    MONDAY_API_KEY: str = ""

    # Notion (Optional - required for Notion integration)
    NOTION_API_TOKEN: str = ""

    # Miro (Optional - required for Miro board integration)
    MIRO_ACCESS_TOKEN: str = ""

    # Database (optional for now)
    DATABASE_URL: Optional[str] = None

    # Pinecone (optional for now)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None

    # Weather (optional)
    OPENWEATHER_API_KEY: Optional[str] = None

    # News (optional)
    NEWSAPI_API_KEY: Optional[str] = None

    # Email (optional - for sending daily briefings)
    SENDER_EMAIL: Optional[str] = None
    SENDER_APP_PASSWORD: Optional[str] = None
    RECIPIENT_EMAIL: Optional[str] = None


settings = Settings()
