from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta
import httpx
from ..base_client import BaseMCPClient, MCPClientError
from models.data_sources import SlackData


class SlackMCPClient(BaseMCPClient):
    """MCP Client for Slack"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("SLACK_BOT_TOKEN")
        self.http_client: Optional[httpx.AsyncClient] = None
        self.bot_user_id: Optional[str] = None

    async def connect(self) -> bool:
        """Establish connection to Slack"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Authorization": f"Bearer {self.bot_token}"}
            )
            # Test auth and get bot user ID
            response = await self.http_client.get("https://slack.com/api/auth.test")
            data = response.json()
            if not data.get("ok"):
                raise MCPClientError(f"Slack auth failed: {data.get('error')}")

            self.bot_user_id = data.get("user_id")
            self.logger.info(f"Slack MCP client connected successfully (Bot ID: {self.bot_user_id})")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Slack: {str(e)}")

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        channels: Optional[List[str]] = None,
        **kwargs
    ) -> List[SlackData]:
        """
        Fetch Slack messages from specified date range

        Args:
            start_date: Start date for messages
            end_date: End date (defaults to start_date)
            channels: List of channel IDs to fetch from (None = all channels)
        """
        if end_date is None:
            end_date = start_date

        # Get channels
        if channels is None:
            channels = await self._get_channels()

        messages = []
        for channel_id in channels:
            channel_messages = await self._fetch_channel_messages(
                channel_id, start_date, end_date
            )
            messages.extend(channel_messages)

        self.logger.info(f"Fetched {len(messages)} Slack messages")
        return messages

    async def _get_channels(self) -> List[str]:
        """Get list of channels the bot is a member of, including DMs"""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/conversations.list",
                params={"types": "public_channel,private_channel,im"}  # Added 'im' for DMs
            )
            data = response.json()

            if not data.get("ok"):
                raise MCPClientError(f"Failed to get channels: {data.get('error')}")

            return [ch["id"] for ch in data.get("channels", [])]

        except Exception as e:
            self.logger.error(f"Error getting channels: {str(e)}")
            return []

    async def _fetch_channel_messages(
        self,
        channel_id: str,
        start_date: date,
        end_date: date
    ) -> List[SlackData]:
        """Fetch messages from a specific channel"""
        try:
            # Convert dates to Unix timestamps
            oldest = datetime.combine(start_date, datetime.min.time()).timestamp()
            latest = datetime.combine(end_date, datetime.max.time()).timestamp()

            response = await self.http_client.get(
                "https://slack.com/api/conversations.history",
                params={
                    "channel": channel_id,
                    "oldest": oldest,
                    "latest": latest,
                    "limit": 1000
                }
            )
            data = response.json()

            if not data.get("ok"):
                self.logger.warning(f"Failed to fetch from {channel_id}: {data.get('error')}")
                return []

            # Get channel info
            channel_info = await self._get_channel_info(channel_id)
            channel_name = channel_info.get("name", channel_id)
            is_dm_channel = channel_info.get("is_im", False)

            messages = []
            for msg in data.get("messages", []):
                slack_msg = await self._parse_message(msg, channel_id, channel_name, is_dm_channel)
                if slack_msg:
                    messages.append(slack_msg)

            return messages

        except Exception as e:
            self.logger.warning(f"Error fetching from channel {channel_id}: {str(e)}")
            return []

    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information"""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/conversations.info",
                params={"channel": channel_id}
            )
            data = response.json()
            return data.get("channel", {})
        except:
            return {}

    async def _parse_message(
        self,
        msg: Dict[str, Any],
        channel_id: str,
        channel_name: str,
        is_dm_channel: bool = False
    ) -> Optional[SlackData]:
        """Parse Slack message into SlackData model"""
        try:
            # Get user info
            user_id = msg.get("user", "")

            # Skip messages from the bot itself
            if user_id == self.bot_user_id:
                return None

            user_name = await self._get_user_name(user_id)

            # Parse timestamp
            ts = float(msg.get("ts", "0"))
            timestamp = datetime.fromtimestamp(ts)

            # Extract reactions
            reactions = [r.get("name", "") for r in msg.get("reactions", [])]

            # Check if bot is mentioned
            text = msg.get("text", "")
            is_mention = self.bot_user_id and f"<@{self.bot_user_id}>" in text

            # Check if DM is unanswered (only for DMs)
            is_dm_unanswered = False
            if is_dm_channel:
                is_dm_unanswered = await self._is_dm_unanswered(channel_id, msg.get("ts", ""))

            # Check if VIP thread
            is_vip_thread = self._is_vip_thread(msg)

            return SlackData(
                channel_id=channel_id,
                channel_name=channel_name,
                message_id=msg.get("ts", ""),
                user_id=user_id,
                user_name=user_name,
                text=text,
                timestamp=timestamp,
                thread_ts=msg.get("thread_ts"),
                reactions=reactions,
                reply_count=msg.get("reply_count", 0),
                is_mention=is_mention,
                is_dm=is_dm_channel,
                is_dm_unanswered=is_dm_unanswered,
                is_vip_thread=is_vip_thread,
                attachments=msg.get("attachments", []),
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse message: {str(e)}")
            return None

    async def _get_user_name(self, user_id: str) -> Optional[str]:
        """Get user display name"""
        try:
            response = await self.http_client.get(
                "https://slack.com/api/users.info",
                params={"user": user_id}
            )
            data = response.json()
            if data.get("ok"):
                user = data.get("user", {})
                return user.get("profile", {}).get("display_name") or user.get("name")
        except:
            pass
        return None

    async def _is_dm_unanswered(self, channel_id: str, message_ts: str) -> bool:
        """
        Check if a DM has been answered by the bot user.

        Args:
            channel_id: Channel ID of the DM
            message_ts: Timestamp of the original message

        Returns:
            True if the DM is unanswered, False if bot has replied
        """
        try:
            # Check if there are any replies in the thread
            response = await self.http_client.get(
                "https://slack.com/api/conversations.replies",
                params={
                    "channel": channel_id,
                    "ts": message_ts
                }
            )
            data = response.json()

            if not data.get("ok"):
                return True  # Assume unanswered if we can't check

            messages = data.get("messages", [])

            # Check if bot has replied in the thread (skip first message which is the original)
            for msg in messages[1:]:
                if msg.get("user") == self.bot_user_id:
                    return False  # Bot has replied

            return True  # No reply from bot

        except Exception as e:
            self.logger.warning(f"Error checking if DM is answered: {str(e)}")
            return True  # Assume unanswered on error

    def _is_vip_thread(self, msg: Dict[str, Any]) -> bool:
        """
        Identify VIP threads based on high engagement.

        Args:
            msg: Message dictionary

        Returns:
            True if message is a VIP thread
        """
        # Count total reactions
        reactions = msg.get("reactions", [])
        total_reaction_count = sum(r.get("count", 0) for r in reactions)

        # Important emojis that signal VIP threads
        important_emojis = ["fire", "eyes", "100", "rocket", "star", "warning", "rotating_light", "sos"]
        has_important_emoji = any(
            r.get("name", "") in important_emojis
            for r in reactions
        )

        # High reply count also signals VIP
        reply_count = msg.get("reply_count", 0)

        # VIP criteria: 3+ reactions OR important emoji OR 5+ replies
        return total_reaction_count >= 3 or has_important_emoji or reply_count >= 5

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Slack"""
        try:
            response = await self.http_client.get("https://slack.com/api/auth.test")
            data = response.json()

            return {
                "connected": data.get("ok", False),
                "team": data.get("team"),
                "user": data.get("user"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
