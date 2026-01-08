from typing import Dict, List, Any, Optional
from datetime import date, datetime
import logging
from anthropic import Anthropic
from models.briefing import (
    Briefing,
    BriefingSection,
    BriefingSummary,
    BriefingStatus,
    DataSourceStatus,
)
from models.data_sources import CollectedData

logger = logging.getLogger(__name__)


class BriefingAgent:
    """
    LangGraph-based agent for processing collected data
    and generating intelligent daily briefings.
    """

    def __init__(self, anthropic_api_key: str):
        """
        Initialize the briefing agent

        Args:
            anthropic_api_key: Anthropic API key for Claude
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.logger = logger
        self.model = "claude-sonnet-4-20250514"  # Latest Claude model

    async def generate_briefing(
        self,
        collected_data: CollectedData,
        target_date: date,
        source_statuses: List[DataSourceStatus],
        include_raw_data: bool = False,
    ) -> Briefing:
        """
        Generate a briefing from collected data

        Args:
            collected_data: All data collected from various sources
            target_date: Date this briefing covers
            source_statuses: Status of each data source collection
            include_raw_data: Whether to include raw data in the briefing

        Returns:
            Complete Briefing object
        """
        self.logger.info(f"Generating briefing for {target_date}")

        start_time = datetime.utcnow()

        # Create briefing ID
        briefing_id = f"briefing-{target_date.isoformat()}"

        # Initialize briefing
        briefing = Briefing(
            id=briefing_id,
            date=target_date,
            status=BriefingStatus.PROCESSING,
            data_sources=source_statuses,
        )

        try:
            # Step 1: Analyze and categorize data
            self.logger.info("Step 1: Analyzing data...")
            sections = await self._analyze_and_create_sections(collected_data, target_date)
            briefing.sections = sections

            # Step 2: Generate executive summary
            self.logger.info("Step 2: Generating summary...")
            summary = await self._generate_summary(collected_data, sections, target_date)
            briefing.summary = summary

            # Mark as completed
            briefing.status = BriefingStatus.COMPLETED
            briefing.generated_at = datetime.utcnow()
            briefing.processing_time_seconds = (datetime.utcnow() - start_time).total_seconds()

            # Optionally include raw data
            if include_raw_data:
                briefing.raw_data = collected_data.model_dump()

            self.logger.info(
                f"Briefing generated successfully in {briefing.processing_time_seconds:.2f}s"
            )

            return briefing

        except Exception as e:
            self.logger.error(f"Failed to generate briefing: {str(e)}")
            briefing.status = BriefingStatus.FAILED
            return briefing

    async def _analyze_and_create_sections(
        self,
        collected_data: CollectedData,
        target_date: date
    ) -> List[BriefingSection]:
        """Analyze collected data and create briefing sections"""

        sections = []

        # Create sections for different data types
        if collected_data.emails:
            email_section = await self._create_email_section(collected_data.emails, target_date)
            if email_section:
                sections.append(email_section)

        if collected_data.calendar_events:
            calendar_section = await self._create_calendar_section(
                collected_data.calendar_events, target_date
            )
            if calendar_section:
                sections.append(calendar_section)

        if collected_data.slack_messages:
            slack_section = await self._create_slack_section(
                collected_data.slack_messages, target_date
            )
            if slack_section:
                sections.append(slack_section)

        if collected_data.gong_calls:
            gong_section = await self._create_gong_section(collected_data.gong_calls, target_date)
            if gong_section:
                sections.append(gong_section)

        if collected_data.monday_items:
            monday_section = await self._create_monday_section(
                collected_data.monday_items, target_date
            )
            if monday_section:
                sections.append(monday_section)

        if collected_data.notion_pages:
            notion_section = await self._create_notion_section(
                collected_data.notion_pages, target_date
            )
            if notion_section:
                sections.append(notion_section)

        if collected_data.miro_boards:
            miro_section = await self._create_miro_section(collected_data.miro_boards, target_date)
            if miro_section:
                sections.append(miro_section)

        if collected_data.weather:
            weather_section = await self._create_weather_section(collected_data.weather, target_date)
            if weather_section:
                sections.append(weather_section)

        if collected_data.news_articles:
            news_section = await self._create_news_section(collected_data.news_articles, target_date)
            if news_section:
                sections.append(news_section)

        if collected_data.calendar_events:
            conflicts_section = await self._create_calendar_conflicts_section(
                collected_data.calendar_events, target_date
            )
            if conflicts_section:
                sections.append(conflicts_section)

        # Sort sections by priority (descending)
        sections.sort(key=lambda s: s.priority, reverse=True)

        return sections

    async def _create_email_section(self, emails: List[Any], target_date: date) -> Optional[BriefingSection]:
        """Create briefing section from emails"""
        if not emails:
            return None

        # Prepare email data for Claude
        email_summaries = []
        for email in emails[:50]:  # Limit to 50 most recent
            email_summaries.append({
                "from": f"{email.from_name or email.from_email}",
                "subject": email.subject,
                "snippet": email.snippet or email.body[:200],
                "is_important": email.is_important,
            })

        prompt = f"""Analyze these {len(emails)} emails from {target_date} and create a concise briefing section.

Focus on:
- Important communications from customers, partners, or leadership
- Action items or requests that need attention
- Key updates or decisions

Emails:
{email_summaries}

Return a markdown-formatted section that highlights the most important points."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Email Highlights",
                content=content,
                priority=8,
                source_count=1,
                metadata={"total_emails": len(emails)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create email section: {str(e)}")
            return None

    async def _create_calendar_section(
        self, events: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create briefing section from calendar events"""
        if not events:
            return None

        event_summaries = []
        for event in events:
            event_summaries.append({
                "title": event.summary,
                "start": event.start_time.strftime("%H:%M"),
                "end": event.end_time.strftime("%H:%M"),
                "attendees_count": len(event.attendees),
            })

        prompt = f"""Analyze these {len(events)} calendar events from {target_date}.

Identify:
- Important customer/prospect meetings
- Internal strategy sessions
- Deadlines or milestones
- Schedule conflicts or back-to-back meetings

Events:
{event_summaries}

Return a markdown-formatted section."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Calendar Overview",
                content=content,
                priority=7,
                source_count=1,
                metadata={"total_events": len(events)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create calendar section: {str(e)}")
            return None

    async def _create_slack_section(
        self, messages: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create enhanced briefing section from Slack messages with DMs/mentions/VIP focus"""
        if not messages:
            return None

        # Categorize messages
        unanswered_dms = []
        mentions = []
        vip_threads = []
        other_messages = []

        for msg in messages:
            if msg.is_dm and msg.is_dm_unanswered:
                unanswered_dms.append({
                    "from": msg.user_name or msg.user_id,
                    "text": msg.text[:200],
                    "time": msg.timestamp.strftime("%H:%M"),
                })
            elif msg.is_mention:
                mentions.append({
                    "from": msg.user_name or msg.user_id,
                    "channel": msg.channel_name,
                    "text": msg.text[:200],
                    "time": msg.timestamp.strftime("%H:%M"),
                })
            elif msg.is_vip_thread:
                vip_threads.append({
                    "channel": msg.channel_name,
                    "from": msg.user_name or msg.user_id,
                    "text": msg.text[:200],
                    "reactions": msg.reactions,
                    "replies": msg.reply_count,
                    "time": msg.timestamp.strftime("%H:%M"),
                })
            else:
                other_messages.append({
                    "channel": msg.channel_name,
                    "from": msg.user_name or msg.user_id,
                    "text": msg.text[:150],
                })

        prompt = f"""Analyze Slack activity from {target_date} with focus on high-priority communications.

**UNANSWERED DIRECT MESSAGES** ({len(unanswered_dms)} requiring response):
{unanswered_dms if unanswered_dms else "None"}

**MENTIONS** ({len(mentions)} times you were mentioned):
{mentions if mentions else "None"}

**VIP THREADS** ({len(vip_threads)} high-engagement discussions):
{vip_threads if vip_threads else "None"}

**Other Activity** ({len(other_messages)} messages):
{other_messages[:10] if other_messages else "None"}  # Sample only

Create a briefing organized by:
1. **Unanswered DMs** - Messages requiring your response, with context (who, what, when)
2. **Mentions** - Where you were @mentioned, why it matters
3. **VIP Threads** - High-engagement discussions you should be aware of
4. **Key Updates** - Other important team communications

Be concise and actionable. Highlight urgent items first.

Return in markdown format with clear sections."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Team Communications",
                content=content,
                priority=6,
                source_count=1,
                metadata={
                    "total_messages": len(messages),
                    "unanswered_dms": len(unanswered_dms),
                    "mentions": len(mentions),
                    "vip_threads": len(vip_threads),
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to create Slack section: {str(e)}")
            return None

    async def _create_gong_section(self, calls: List[Any], target_date: date) -> Optional[BriefingSection]:
        """Create briefing section from Gong calls with enhanced customer insights"""
        if not calls:
            return None

        call_summaries = []
        for call in calls:
            call_summaries.append({
                "title": call.title,
                "customer": call.customer_name or "Unknown",
                "duration": f"{call.duration_minutes} min",
                "key_topics": call.key_topics,
                "action_items": call.action_items,
                "sentiment": call.sentiment_score,
                "summary": call.summary,
                "next_steps": call.next_steps,
            })

        prompt = f"""Analyze these {len(calls)} customer/prospect calls from {target_date} and extract critical insights.

For each call, identify and summarize:
1. **Customer Use Case** - What business problem are they trying to solve? What's their goal?
2. **Pain Points** - What specific challenges or frustrations did they express?
3. **Competitors Mentioned** - Any competing products or solutions discussed?
4. **Objections Raised** - Concerns, pushback, or hesitations expressed?
5. **Next Steps** - Agreed follow-up actions and timeline

Calls Data (with Gong's AI-extracted topics):
{call_summaries}

IMPORTANT: Rely primarily on the key_topics field which contains Gong's AI extraction. This already includes competitor mentions, objections, and pain points identified by Gong's analysis.

Create a concise, actionable briefing organized by call. Highlight deal-critical information and competitive intelligence.

Max 2500 tokens.

Return in markdown format with clear sections for each call."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Customer Calls & Insights",
                content=content,
                priority=11,  # Highest priority (updated from 10)
                source_count=1,
                metadata={"total_calls": len(calls)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create Gong section: {str(e)}")
            return None

    async def _create_monday_section(
        self, items: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create briefing section from Monday.com items"""
        if not items:
            return None

        item_summaries = []
        for item in items[:30]:
            item_summaries.append({
                "board": item.board_name,
                "item": item.item_name,
                "status": item.status,
                "owner": item.owner,
                "due_date": item.due_date.strftime("%Y-%m-%d") if item.due_date else None,
            })

        prompt = f"""Analyze these {len(items)} project/task updates from Monday.com for {target_date}.

Focus on:
- High-priority tasks or blockers
- Upcoming deadlines
- Status changes
- Items requiring attention

Items:
{item_summaries}

Return a markdown-formatted section."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Project Updates",
                content=content,
                priority=7,
                source_count=1,
                metadata={"total_items": len(items)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create Monday section: {str(e)}")
            return None

    async def _create_notion_section(
        self, pages: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create briefing section from Notion pages"""
        if not pages:
            return None

        page_summaries = []
        for page in pages[:20]:
            page_summaries.append({
                "title": page.title,
                "content_preview": page.content[:200] if page.content else "",
                "last_edited": page.last_edited_time.strftime("%H:%M"),
            })

        prompt = f"""Analyze these {len(pages)} Notion page updates from {target_date}.

Focus on:
- New documentation or resources
- Strategy or planning documents
- Content drafts requiring review
- Knowledge base updates

Pages:
{page_summaries}

Return a markdown-formatted section."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Documentation & Content",
                content=content,
                priority=5,
                source_count=1,
                metadata={"total_pages": len(pages)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create Notion section: {str(e)}")
            return None

    async def _create_miro_section(
        self, boards: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create briefing section from Miro boards"""
        if not boards:
            return None

        board_summaries = []
        for board in boards:
            board_summaries.append({
                "name": board.board_name,
                "item_count": board.item_count,
                "modified": board.modified_at.strftime("%H:%M"),
            })

        prompt = f"""Analyze these {len(boards)} Miro board updates from {target_date}.

Focus on:
- Active brainstorming or planning sessions
- Design or workflow updates
- Collaboration activity

Boards:
{board_summaries}

Return a markdown-formatted section."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Visual Collaboration",
                content=content,
                priority=4,
                source_count=1,
                metadata={"total_boards": len(boards)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create Miro section: {str(e)}")
            return None

    async def _create_weather_section(self, weather: Any, target_date: date) -> Optional[BriefingSection]:
        """Create briefing section from weather data"""
        if not weather:
            return None

        try:
            location_name = f"{weather.location.get('city', 'Unknown')}, {weather.location.get('region', '')}"

            # Format forecast data
            forecast_items = []
            for item in weather.forecast[:4]:  # Next 12 hours (4 x 3-hour intervals)
                forecast_items.append({
                    "time": item.get("time", ""),
                    "temp": item.get("temperature", 0),
                    "description": item.get("description", ""),
                    "precip_chance": item.get("precipitation_chance", 0)
                })

            # Create weather.com link for the location
            city = weather.location.get('city', 'Unknown').replace(' ', '-').lower()
            region = weather.location.get('region', '').replace(' ', '-').lower()
            weather_link = f"https://weather.com/weather/today/l/{weather.location.get('lat', 0)},{weather.location.get('lon', 0)}"

            prompt = f"""Create a CONCISE weather summary for {location_name} on {target_date}.

Current Conditions:
- Temperature: {weather.current_temperature}°F (feels like {weather.feels_like}°F)
- Conditions: {weather.description}
- Humidity: {weather.humidity}%
- Wind: {weather.wind_speed} mph
- Visibility: {weather.visibility} miles

Forecast (next 12 hours):
{forecast_items}

Provide 1-2 sentences summarizing the weather and any important considerations for the day.
End with: [View detailed forecast]({weather_link})

Keep it brief and actionable. Return in markdown format."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Local Weather",
                content=content,
                priority=3,
                source_count=1,
                metadata={"location": location_name, "temperature": weather.current_temperature},
            )

        except Exception as e:
            self.logger.error(f"Failed to create weather section: {str(e)}")
            return None

    async def _create_news_section(self, articles: List[Any], target_date: date) -> Optional[BriefingSection]:
        """Create briefing section from news articles"""
        if not articles:
            return None

        try:
            article_summaries = []
            for article in articles[:5]:  # Top 5 headlines
                article_summaries.append({
                    "title": article.title,
                    "content": article.content[:200],  # Brief snippet
                    "url": article.url,
                    "score": article.score
                })

            prompt = f"""Create a CONCISE bullet list of today's top 5 world news headlines.

Articles:
{article_summaries}

For each headline, provide:
- **[Headline Title](URL)** - One sentence summary

Format example:
- **[Mexico Hit by 6.5 Magnitude Earthquake](https://example.com)** - Major seismic event affects southern regions, no casualties reported

Keep it brief - just headline with link and one-sentence summary. No extra analysis needed."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="World News Headlines",
                content=content,
                priority=2,
                source_count=1,
                metadata={"article_count": len(articles)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create news section: {str(e)}")
            return None

    async def _create_calendar_conflicts_section(
        self, events: List[Any], target_date: date
    ) -> Optional[BriefingSection]:
        """Create briefing section from calendar conflict analysis"""
        if not events:
            return None

        try:
            from utils.calendar_analyzer import analyze_calendar

            # Analyze calendar for conflicts
            analysis = analyze_calendar(events)

            # Only create section if there are conflicts
            if analysis["total_conflicts"] == 0:
                return None

            prompt = f"""Analyze these calendar conflicts for {target_date}.

Analysis:
- Total events: {analysis['total_events']}
- Total conflicts: {analysis['total_conflicts']}
- Overlapping events: {analysis['overlapping_events']}
- Back-to-back meetings: {analysis['back_to_back_meetings']}
- High severity: {analysis['high_severity_conflicts']}
- Medium severity: {analysis['medium_severity_conflicts']}

Conflicts:
{analysis['conflicts']}

Create a briefing section that:
1. Lists the most critical conflicts (high severity first)
2. Highlights schedule issues requiring attention
3. Suggests breaks or adjustments where needed

Be concise and actionable. Max 1000 tokens.

Return in markdown format."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Calendar Conflicts & Scheduling Issues",
                content=content,
                priority=9,  # High priority
                source_count=1,
                metadata={
                    "total_conflicts": analysis["total_conflicts"],
                    "high_severity": analysis["high_severity_conflicts"],
                    "needs_attention": analysis["needs_attention"]
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to create calendar conflicts section: {str(e)}")
            return None

    async def _generate_summary(
        self,
        collected_data: CollectedData,
        sections: List[BriefingSection],
        target_date: date
    ) -> BriefingSummary:
        """Generate executive summary from all sections"""

        # Compile all section content
        all_content = "\n\n".join([f"## {s.title}\n{s.content}" for s in sections])

        prompt = f"""Based on this daily briefing for {target_date}, create an executive summary focused on actionable work items.

IMPORTANT: Focus ONLY on items related to the user's role as Head of Product Marketing at Port.

Provide:
1. 3-5 key highlights from EMAILS, CALENDAR, SLACK, and GONG CALLS (ignore news/weather)
2. 3-5 action items that require the user's attention TODAY (emails to respond to, meetings to prepare for, DMs to answer, follow-ups from calls)
3. Overall sentiment (positive/neutral/negative)

Ignore world news and weather in the summary. Focus on:
- Email follow-ups needed
- Meeting preparation or scheduling issues
- Slack messages requiring response
- Customer call follow-ups from Gong

Briefing content:
{all_content[:8000]}  # Limit to avoid token limits

Return as JSON with keys: key_highlights (array), action_items (array), overall_sentiment (string)"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Parse JSON response - handle markdown code blocks
            import json
            import re

            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                # Try to find raw JSON in the response
                content = content.strip()
                if not content.startswith('{'):
                    start = content.find('{')
                    end = content.rfind('}')
                    if start != -1 and end != -1:
                        content = content[start:end+1]

            summary_data = json.loads(content)

            return BriefingSummary(
                key_highlights=summary_data.get("key_highlights", []),
                action_items=summary_data.get("action_items", []),
                overall_sentiment=summary_data.get("overall_sentiment", "neutral"),
            )

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {str(e)}")
            self.logger.error(f"Response content: {content if 'content' in locals() else 'N/A'}")
            # Return empty summary on failure
            return BriefingSummary(
                key_highlights=["Summary generation failed"],
                action_items=[],
                overall_sentiment="neutral",
            )
