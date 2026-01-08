from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import EmailData, CalendarEvent


class GoogleMCPClient(BaseMCPClient):
    """
    MCP Client for Google Workspace (Gmail + Calendar)
    Uses OAuth 2.0 with refresh token
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config.get("GOOGLE_CLIENT_ID")
        self.client_secret = config.get("GOOGLE_CLIENT_SECRET")
        self.refresh_token = config.get("GOOGLE_REFRESH_TOKEN")
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Establish connection and get access token"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)
            await self._refresh_access_token()
            self.logger.info("Google MCP client connected successfully")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Google: {str(e)}")

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def _refresh_access_token(self) -> None:
        """Refresh OAuth access token"""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        response = await self.http_client.post(token_url, data=data)
        if response.status_code != 200:
            raise MCPClientError(f"Failed to refresh token: {response.text}")

        token_data = response.json()
        self.access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

    async def _ensure_token_valid(self) -> None:
        """Ensure access token is valid, refresh if needed"""
        if not self.access_token or (
            self.token_expiry and datetime.utcnow() >= self.token_expiry - timedelta(minutes=5)
        ):
            await self._refresh_access_token()

    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> Dict[str, List[Any]]:
        """
        Fetch both Gmail and Calendar data

        Returns:
            Dictionary with 'emails' and 'calendar_events' keys
        """
        if end_date is None:
            end_date = start_date

        emails = await self.fetch_emails(start_date, end_date, **kwargs)
        calendar_events = await self.fetch_calendar_events(start_date, end_date, **kwargs)

        return {
            "emails": emails,
            "calendar_events": calendar_events,
        }

    async def fetch_emails(
        self,
        start_date: date,
        end_date: date,
        max_results: int = 100
    ) -> List[EmailData]:
        """Fetch emails from Gmail"""
        await self._ensure_token_valid()

        # Build Gmail API query
        query_parts = [
            f"after:{start_date.strftime('%Y/%m/%d')}",
            f"before:{(end_date + timedelta(days=1)).strftime('%Y/%m/%d')}",
        ]
        query = " ".join(query_parts)

        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"q": query, "maxResults": max_results}

        try:
            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            emails = []
            for msg in data.get("messages", []):
                email_data = await self._fetch_email_details(msg["id"], headers)
                if email_data:
                    emails.append(email_data)

            self.logger.info(f"Fetched {len(emails)} emails from Gmail")
            return emails

        except Exception as e:
            self.logger.error(f"Error fetching emails: {str(e)}")
            raise MCPClientError(f"Failed to fetch emails: {str(e)}")

    async def _fetch_email_details(self, message_id: str, headers: Dict[str, str]) -> Optional[EmailData]:
        """Fetch detailed information for a single email"""
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            params = {"format": "full"}

            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            msg = response.json()

            # Parse headers
            headers_dict = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Extract body
            body = self._extract_email_body(msg.get("payload", {}))

            # Parse date
            date_str = headers_dict.get("Date", "")
            email_date = self._parse_email_date(date_str)

            return EmailData(
                id=message_id,
                thread_id=msg.get("threadId", ""),
                subject=headers_dict.get("Subject", ""),
                from_email=self._extract_email(headers_dict.get("From", "")),
                from_name=self._extract_name(headers_dict.get("From", "")),
                to_emails=self._parse_email_list(headers_dict.get("To", "")),
                cc_emails=self._parse_email_list(headers_dict.get("Cc", "")),
                date=email_date,
                body=body,
                labels=msg.get("labelIds", []),
                is_important="IMPORTANT" in msg.get("labelIds", []),
                snippet=msg.get("snippet", ""),
            )

        except Exception as e:
            self.logger.warning(f"Failed to fetch email {message_id}: {str(e)}")
            return None

    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from message payload"""
        if "body" in payload and payload["body"].get("data"):
            import base64
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    if part.get("body", {}).get("data"):
                        import base64
                        return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")

        return ""

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.utcnow()

    def _extract_email(self, email_string: str) -> str:
        """Extract email address from 'Name <email@domain.com>' format"""
        import re
        match = re.search(r'<([^>]+)>', email_string)
        return match.group(1) if match else email_string

    def _extract_name(self, email_string: str) -> Optional[str]:
        """Extract name from 'Name <email@domain.com>' format"""
        import re
        match = re.match(r'^([^<]+)<', email_string)
        return match.group(1).strip() if match else None

    def _parse_email_list(self, email_string: str) -> List[str]:
        """Parse comma-separated email list"""
        if not email_string:
            return []
        return [self._extract_email(e.strip()) for e in email_string.split(",")]

    async def fetch_calendar_events(
        self,
        start_date: date,
        end_date: date,
        max_results: int = 100
    ) -> List[CalendarEvent]:
        """Fetch calendar events from Google Calendar"""
        await self._ensure_token_valid()

        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

        time_min = datetime.combine(start_date, datetime.min.time()).isoformat() + "Z"
        time_max = datetime.combine(end_date, datetime.max.time()).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        try:
            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            events = []
            for item in data.get("items", []):
                event = self._parse_calendar_event(item)
                if event:
                    events.append(event)

            self.logger.info(f"Fetched {len(events)} calendar events")
            return events

        except Exception as e:
            self.logger.error(f"Error fetching calendar events: {str(e)}")
            raise MCPClientError(f"Failed to fetch calendar events: {str(e)}")

    def _parse_calendar_event(self, item: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Parse calendar event from API response"""
        try:
            start = item.get("start", {})
            end = item.get("end", {})

            # Handle all-day events
            is_all_day = "date" in start

            if is_all_day:
                start_time = datetime.fromisoformat(start["date"])
                end_time = datetime.fromisoformat(end["date"])
            else:
                start_time = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))

            attendees = [a.get("email", "") for a in item.get("attendees", [])]
            organizer = item.get("organizer", {}).get("email")

            return CalendarEvent(
                id=item.get("id", ""),
                summary=item.get("summary", "No Title"),
                description=item.get("description"),
                start_time=start_time,
                end_time=end_time,
                location=item.get("location"),
                attendees=attendees,
                organizer=organizer,
                is_all_day=is_all_day,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse calendar event: {str(e)}")
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Google APIs"""
        try:
            await self._ensure_token_valid()

            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Test Gmail
            gmail_url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
            gmail_response = await self.http_client.get(gmail_url, headers=headers)
            gmail_ok = gmail_response.status_code == 200

            # Test Calendar
            cal_url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
            cal_response = await self.http_client.get(cal_url, headers=headers)
            cal_ok = cal_response.status_code == 200

            return {
                "connected": gmail_ok and cal_ok,
                "gmail": gmail_ok,
                "calendar": cal_ok,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
