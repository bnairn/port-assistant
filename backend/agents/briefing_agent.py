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
            # Analyze and create briefing sections
            self.logger.info("Analyzing data and creating briefing sections...")
            sections = await self._analyze_and_create_sections(collected_data, target_date)
            briefing.sections = sections

            # No executive summary - Critical Items and Action Items sections replace it

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

        # PRIORITY ORDERED SECTIONS (1=highest at top, 7=lowest at bottom)

        # 1. Local Weather (Priority 1)
        if collected_data.weather:
            weather_section = await self._create_weather_section(collected_data.weather, target_date)
            if weather_section:
                sections.append(weather_section)

        # 2. AI News (Priority 2) - Industry AI headlines
        if collected_data.news_articles:
            ai_news_section = await self._create_ai_news_section(collected_data, target_date)
            if ai_news_section:
                sections.append(ai_news_section)

        # 3. Competitor News (Priority 3) - IDP and competitor headlines
        if collected_data.news_articles:
            competitor_news_section = await self._create_competitor_news_section(collected_data, target_date)
            if competitor_news_section:
                sections.append(competitor_news_section)

        # 4. Agenda with conflicts (Priority 4) - What's happening today
        agenda_section = await self._create_agenda_section(collected_data, target_date)
        if agenda_section:
            sections.append(agenda_section)

        # 5. Slack Summary (Priority 5) - Critical messages needing attention
        if collected_data.slack_messages:
            slack_section = await self._create_slack_section(
                collected_data.slack_messages, target_date
            )
            if slack_section:
                sections.append(slack_section)

        # 6. Email Summary (Priority 6) - Overnight emails and meeting invites
        if collected_data.emails:
            email_section = await self._create_email_section(collected_data.emails, target_date)
            if email_section:
                sections.append(email_section)

        # 7. New Customer Calls (Priority 7) - Customer insights
        if collected_data.gong_calls:
            gong_section = await self._create_gong_section(collected_data.gong_calls, target_date)
            if gong_section:
                sections.append(gong_section)

        # REMOVED SECTIONS:
        # - Calendar Overview (redundant with Agenda)
        # - Project Updates (Monday.com - not needed right now)
        # - Notion integration (not needed)
        # - Miro boards (keeping for now but can remove if needed)

        # Sort sections by priority (ascending - lower number = higher priority, 1 is highest)
        sections.sort(key=lambda s: s.priority)

        return sections

    async def _create_email_section(self, emails: List[Any], target_date: date) -> Optional[BriefingSection]:
        """Create briefing section from emails with focus on meeting invites"""
        if not emails:
            return None

        # Categorize emails
        meeting_invites = []
        other_emails = []

        for email in emails[:50]:  # Limit to 50 most recent
            subject_lower = email.subject.lower() if email.subject else ""

            # Check if it's a meeting invite
            if any(keyword in subject_lower for keyword in ["invitation:", "invited:", "meeting:", "calendar:"]) or \
               (hasattr(email, 'is_calendar_invite') and email.is_calendar_invite):
                meeting_invites.append({
                    "from": f"{email.from_name or email.from_email}",
                    "subject": email.subject,
                    "snippet": email.snippet or email.body[:200],
                })
            else:
                other_emails.append({
                    "from": f"{email.from_name or email.from_email}",
                    "subject": email.subject,
                    "snippet": email.snippet or email.body[:200],
                    "is_important": email.is_important,
                })

        total_emails = len(emails)

        prompt = f"""Summarize email activity from {target_date}. Total emails analyzed: {total_emails}

**NEW MEETING INVITES** ({len(meeting_invites)} invitations):
{meeting_invites if meeting_invites else "None"}

**OTHER KEY EMAILS** ({len(other_emails)} emails):
{other_emails[:20] if other_emails else "None"}

Format the briefing as:

**New Meeting Invites**:
- [List each new meeting invite with organizer and meeting topic]

**Other Key Emails**:
[Brief summary of important non-meeting emails - requests, key updates, notifications]

Keep it concise and focused. Max 1200 tokens."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Email Summary",
                content=content,
                priority=6,
                source_count=1,
                metadata={
                    "total_emails": total_emails,
                    "meeting_invites": len(meeting_invites),
                    "other_emails": len(other_emails)
                },
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

        total_messages = len(messages)

        prompt = f"""Summarize Slack activity from {target_date}. Total messages analyzed: {total_messages}

**UNANSWERED DIRECT MESSAGES** ({len(unanswered_dms)} requiring response):
{unanswered_dms if unanswered_dms else "None"}

**MENTIONS** ({len(mentions)} times you were mentioned):
{mentions if mentions else "None"}

**THREADS WITH NEW REPLIES** ({len(vip_threads)} active threads):
{vip_threads if vip_threads else "None"}

Format the briefing in this structure:

**Direct Messages**: {len(unanswered_dms)} unanswered
[Brief summary of who needs responses and about what]

**Mentions**: {len(mentions)} mentions
[Brief summary of where you were mentioned and why]

**Active Threads**: {len(vip_threads)} with new replies
[Brief summary of high-engagement discussions]

Be very concise. Focus only on actionable items. Max 1000 tokens."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Slack Summary",
                content=content,
                priority=5,
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
        """Create briefing section from NEW customer Gong calls only"""
        if not calls:
            return None

        call_summaries = []
        new_customer_calls = []

        for call in calls:
            # Detect customer type from call title
            title_lower = call.title.lower() if call.title else ""
            customer_type = "existing"  # Default

            # Check for "new customer" indicators
            if any(keyword in title_lower for keyword in ["kickoff", "intro", "introduction", "onboarding", "getting started", "initial"]):
                customer_type = "new"
            # Check for "existing customer" indicators (more explicit)
            elif any(keyword in title_lower for keyword in ["sync", "check-in", "follow-up", "follow up", "weekly", "monthly", "quarterly"]):
                customer_type = "existing"

            # Only include NEW customer calls
            if customer_type == "new":
                new_customer_calls.append(call)
                call_summaries.append({
                    "title": call.title,
                    "customer": call.customer_name or "Unknown",
                    "customer_type": customer_type,
                    "duration": f"{call.duration_minutes} min",
                    "key_topics": call.key_topics,
                    "action_items": call.action_items,
                    "sentiment": call.sentiment_score,
                    "summary": call.summary,
                    "next_steps": call.next_steps,
                })

        # If no new customer calls, return None
        if not call_summaries:
            return None

        prompt = f"""Analyze these {len(call_summaries)} NEW customer/prospect calls from {target_date} and extract critical insights.

For each call, create a structured summary with:
1. **Customer Type** - New or Existing (already detected)
2. **Customer Use Case** - What business problem are they trying to solve?
3. **Pain Points** - Specific challenges or frustrations expressed
4. **Competitors Mentioned** - Any competing products or solutions discussed
5. **Objections Raised** - Concerns, pushback, or hesitations
6. **Next Steps** - Agreed follow-up actions and timeline

Calls Data (with Gong's AI-extracted topics and detected customer type):
{call_summaries}

IMPORTANT: The customer_type field indicates if this is a "new" or "existing" customer based on call title analysis.

Format each call as:

## [Customer Name] - [duration]

**Customer Type**: [new | existing]

**Customer Use Case**: [what they're trying to solve]

**Pain Points**: [challenges mentioned]

**Competitors**: [any mentioned, or "None"]

**Objections**: [concerns raised, or "None"]

**Next Steps**: [follow-up actions]

Add blank lines between each field for readability. Max 2500 tokens. Be concise and actionable."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Extract competitive intelligence for metadata
            competitors_mentioned = []
            for call_summary in call_summaries:
                if call_summary.get("key_topics"):
                    for topic in call_summary["key_topics"]:
                        if isinstance(topic, str):
                            topic_lower = topic.lower()
                            if any(comp in topic_lower for comp in ["backstage", "cortex", "opslevel", "roadie", "competitor"]):
                                competitors_mentioned.append(topic)

            return BriefingSection(
                title="New Customer Calls",
                content=content,
                priority=7,
                source_count=1,
                metadata={
                    "total_calls": len(call_summaries),
                    "new_customers": len(call_summaries),
                    "competitors_mentioned": len(competitors_mentioned)
                },
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
                priority=4,
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

            prompt = f"""Create a VERY COMPACT weather summary for {location_name} on {target_date}.

Current Conditions:
- Temperature: {weather.current_temperature}°F (feels like {weather.feels_like}°F)
- Conditions: {weather.description}
- Humidity: {weather.humidity}%
- Wind: {weather.wind_speed} mph
- Visibility: {weather.visibility} miles

Forecast (next 12 hours):
{forecast_items}

Format as:
**{location_name}**
Currently [temp]°F, [conditions]. [One key consideration if any (e.g., high humidity, poor visibility, wind)].
[View detailed forecast]({weather_link})

Maximum 2 sentences total. Be extremely concise."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Local Weather",
                content=content,
                priority=1,  # Highest priority - user wants weather at top
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

    async def _create_critical_items_section(
        self,
        collected_data: Any,
        target_date: date
    ) -> Optional[BriefingSection]:
        """Create section for critical items with deadlines in next 48 hours"""
        try:
            from datetime import timedelta

            # Calculate 48-hour deadline window
            deadline_end = target_date + timedelta(hours=48)

            critical_items = []

            # Extract from calendar events
            if hasattr(collected_data, 'calendar_events') and collected_data.calendar_events:
                for event in collected_data.calendar_events:
                    title_lower = event.title.lower()
                    # Check for deadline keywords
                    if any(keyword in title_lower for keyword in ['deadline', 'due', 'reminder', 'submit']):
                        # Check if within 48 hours
                        if event.start_time.date() <= deadline_end.date():
                            critical_items.append({
                                "source": "Calendar",
                                "time": event.start_time.strftime("%Y-%m-%d %H:%M"),
                                "description": event.title,
                                "type": "calendar_event"
                            })

            # Extract from emails
            if hasattr(collected_data, 'emails') and collected_data.emails:
                for email in collected_data.emails[:20]:  # Check recent emails
                    subject_lower = email.subject.lower() if email.subject else ""
                    snippet_lower = email.snippet.lower() if email.snippet else ""

                    # Check for deadline/urgency keywords
                    if any(keyword in subject_lower or keyword in snippet_lower
                           for keyword in ['deadline', 'due', 'urgent', 'asap', 'eod', 'today']):
                        critical_items.append({
                            "source": "Email",
                            "time": email.received_at.strftime("%Y-%m-%d") if hasattr(email, 'received_at') else "Recent",
                            "description": f"{email.sender}: {email.subject}",
                            "type": "email"
                        })

            # Extract from Slack
            if hasattr(collected_data, 'slack_messages') and collected_data.slack_messages:
                for msg in collected_data.slack_messages[:20]:
                    text_lower = msg.text.lower() if msg.text else ""

                    if any(keyword in text_lower for keyword in ['deadline', 'due', 'urgent', 'asap']):
                        critical_items.append({
                            "source": "Slack",
                            "time": msg.timestamp.strftime("%Y-%m-%d") if hasattr(msg, 'timestamp') else "Recent",
                            "description": f"{msg.user}: {msg.text[:100]}...",
                            "type": "slack"
                        })

            # If no critical items found, return None
            if not critical_items:
                return None

            # Format for Claude
            items_text = "\n".join([
                f"- [{item['source']}] {item['time']}: {item['description']}"
                for item in critical_items[:10]  # Limit to 10 most critical
            ])

            prompt = f"""Analyze these potential critical items with deadlines in the next 48 hours.

Items identified:
{items_text}

For each TRUE deadline or critical item:
- Extract the actual deadline date/time
- Summarize what is due in 1-2 lines
- Note the source

Format as a bulleted list, ordered by urgency (soonest first):
- **[Deadline Time]** What is due - *Source*

Only include items that are actual actionable deadlines, not general reminders."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Critical Items",
                content=content,
                priority=2,  # Second after weather
                source_count=len(set([item['source'] for item in critical_items])),
                metadata={"total_items": len(critical_items)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create critical items section: {str(e)}")
            return None

    async def _create_new_requests_section(
        self,
        collected_data: Any,
        target_date: date
    ) -> Optional[BriefingSection]:
        """Create section for new incoming requests"""
        try:
            new_requests = []

            # Extract from emails - look for request patterns
            if hasattr(collected_data, 'emails') and collected_data.emails:
                for email in collected_data.emails[:30]:
                    subject_lower = email.subject.lower() if email.subject else ""
                    snippet_lower = email.snippet.lower() if email.snippet else ""
                    combined_text = f"{subject_lower} {snippet_lower}"

                    # Check for request keywords
                    if any(keyword in combined_text for keyword in
                           ['can you', 'could you', 'please', 'need', 'help with', 'requesting', 'request for']):
                        new_requests.append({
                            "source": "Email",
                            "requester": email.sender,
                            "request": f"{email.subject}: {email.snippet[:150]}",
                            "type": "email"
                        })

            # Extract from Slack - unanswered DMs and mentions
            if hasattr(collected_data, 'slack_messages') and collected_data.slack_messages:
                for msg in collected_data.slack_messages:
                    # Prioritize unanswered DMs and mentions
                    if (hasattr(msg, 'is_dm_unanswered') and msg.is_dm_unanswered) or \
                       (hasattr(msg, 'is_mention') and msg.is_mention):
                        new_requests.append({
                            "source": "Slack DM" if hasattr(msg, 'is_dm') and msg.is_dm else "Slack Mention",
                            "requester": msg.user if hasattr(msg, 'user') else "Unknown",
                            "request": msg.text[:150] if msg.text else "",
                            "type": "slack"
                        })

            # Extract from calendar - new meeting invites
            if hasattr(collected_data, 'calendar_events') and collected_data.calendar_events:
                for event in collected_data.calendar_events[:10]:
                    # Check if event was created recently (within last 24 hours as proxy for "new")
                    if hasattr(event, 'created_at'):
                        from datetime import timedelta
                        if event.created_at and (target_date - event.created_at.date()).days <= 1:
                            new_requests.append({
                                "source": "Calendar Invite",
                                "requester": event.organizer if hasattr(event, 'organizer') else "Unknown",
                                "request": f"Meeting: {event.title} at {event.start_time.strftime('%H:%M')}",
                                "type": "calendar"
                            })

            # If no new requests found, return None
            if not new_requests:
                return None

            # Format for Claude
            requests_text = "\n".join([
                f"- [{req['source']}] {req['requester']}: {req['request']}"
                for req in new_requests[:15]  # Limit to 15 requests
            ])

            prompt = f"""Identify new requests requiring action from these incoming messages:

Requests:
{requests_text}

For each request:
- Who is requesting
- What they need
- Source (Email/Slack/Calendar)

Format as a bulleted list:
- **[Requester]** needs [what they need] - *via [Source]*

Keep it concise, focus on actionable requests."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="New Requests",
                content=content,
                priority=3,
                source_count=len(set([req['source'] for req in new_requests])),
                metadata={"total_requests": len(new_requests)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create new requests section: {str(e)}")
            return None

    async def _create_agenda_section(
        self,
        collected_data: Any,
        target_date: date
    ) -> Optional[BriefingSection]:
        """Create compact time-ordered agenda from calendar events with conflicts first"""
        try:
            events = []
            if hasattr(collected_data, 'calendar_events') and collected_data.calendar_events:
                # Filter events for target_date
                for event in collected_data.calendar_events:
                    if event.start_time.date() == target_date:
                        events.append(event)

            if not events:
                return None

            # Sort by start time
            events.sort(key=lambda e: e.start_time)

            # Check for conflicts
            conflicts_text = ""
            try:
                from utils.calendar_analyzer import analyze_calendar
                analysis = analyze_calendar(events)

                if analysis["total_conflicts"] > 0:
                    conflicts_text = "**⚠️ CONFLICTS REQUIRING ATTENTION:**\n\n"

                    # Show overlapping meetings
                    if analysis["overlapping_events"]:
                        for conflict in analysis["conflicts"]:
                            if conflict.get("type") == "overlap":
                                conflicts_text += f"- {conflict.get('time', '')}: {conflict.get('description', '')}\n"

                    # Show problematic back-to-back meetings
                    if analysis["high_severity_conflicts"] > 0:
                        for conflict in analysis["conflicts"]:
                            if conflict.get("severity") == "high" and conflict.get("type") == "back_to_back":
                                conflicts_text += f"- {conflict.get('time', '')}: {conflict.get('description', '')}\n"

                    conflicts_text += "\n**TODAY'S SCHEDULE:**\n\n"
                else:
                    conflicts_text = "**TODAY'S SCHEDULE:**\n\n"
            except ImportError:
                # If calendar analyzer not available, just show schedule
                conflicts_text = "**TODAY'S SCHEDULE:**\n\n"

            # Format as: <time> <title> <organizer> <agenda>
            agenda_lines = []
            for event in events:
                time_str = event.start_time.strftime("%I:%M %p").lstrip("0")  # Remove leading zero

                # Get organizer (extract name from email if present)
                organizer = ""
                if hasattr(event, 'organizer') and event.organizer:
                    # Extract name before @ if email format
                    organizer_email = event.organizer
                    if '@' in organizer_email:
                        organizer = organizer_email.split('@')[0].replace('.', ' ').title()
                    else:
                        organizer = organizer_email
                    organizer = f"({organizer})"

                # Get agenda/description if available (strip HTML tags)
                agenda = ""
                if hasattr(event, 'description') and event.description:
                    import re
                    # Strip HTML tags
                    desc = re.sub(r'<[^>]+>', '', event.description.strip())
                    # Take first line or first 80 chars
                    desc = desc.split('\n')[0].strip()
                    if len(desc) > 80:
                        desc = desc[:77] + "..."
                    if desc:
                        agenda = f" - {desc}"

                # Build line: time + title + organizer + agenda
                title = event.summary if hasattr(event, 'summary') else event.title
                line = f"{time_str}  {title}"
                if organizer:
                    line += f" {organizer}"
                if agenda:
                    line += agenda

                agenda_lines.append(line)

            # Join with two spaces + newline for proper markdown line breaks
            content = conflicts_text + "  \n".join(agenda_lines)

            return BriefingSection(
                title="Agenda",
                content=content,
                priority=4,
                source_count=1,
                metadata={"total_events": len(events)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create agenda section: {str(e)}")
            return None

    async def _create_ai_news_section(
        self,
        collected_data: Any,
        target_date: date
    ) -> Optional[BriefingSection]:
        """Create section for AI/ML news from NewsAPI"""
        try:
            # Get AI news articles directly from collected data
            ai_articles = []
            if hasattr(collected_data, 'ai_news_articles') and collected_data.ai_news_articles:
                ai_articles = collected_data.ai_news_articles

            if not ai_articles:
                return None

            # Limit to top 10 most relevant
            ai_articles = ai_articles[:10]

            # Format articles for Claude
            articles_text = "\n\n".join([
                f"Title: {article.title}\nURL: {article.url}\nContent: {article.content or 'N/A'}"
                for article in ai_articles
            ])

            prompt = f"""Summarize these AI/ML news headlines relevant to the tech industry.

Articles:
{articles_text}

For each relevant article, format as:
- **[Headline](URL)** - One sentence summary focusing on key impact or development

Prioritize news about:
- Major AI product launches or updates
- AI regulation or policy changes
- Significant AI research breakthroughs
- Enterprise AI adoption trends
- AI company funding or acquisitions

Keep it concise. Max 800 tokens."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="AI News",
                content=content,
                priority=2,
                source_count=1,
                metadata={"total_articles": len(ai_articles)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create AI news section: {str(e)}")
            return None

    async def _create_competitor_news_section(
        self,
        collected_data: Any,
        target_date: date
    ) -> Optional[BriefingSection]:
        """Create section for Port competitor news from NewsAPI"""
        try:
            # Get competitor news articles directly from collected data
            competitor_articles = []
            if hasattr(collected_data, 'competitor_news_articles') and collected_data.competitor_news_articles:
                competitor_articles = collected_data.competitor_news_articles

            if not competitor_articles:
                return None

            # Limit to top 10 most relevant
            competitor_articles = competitor_articles[:10]

            # Format articles for Claude
            articles_text = "\n\n".join([
                f"Title: {article.title}\nURL: {article.url}\nContent: {article.content or 'N/A'}"
                for article in competitor_articles
            ])

            prompt = f"""Summarize news about internal developer platforms and Port competitors.

Articles:
{articles_text}

For each relevant article, format as:
- **[Headline](URL)** - One sentence summary focusing on competitive implications

Focus on:
- Backstage, Cortex, Opslevel, Roadie, Configure8, DX, Harness announcements
- Internal developer portal (IDP) market trends
- Platform engineering best practices
- Developer experience innovations
- Service catalog and portal launches

Highlight competitive intelligence relevant to Port's positioning. Max 800 tokens."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            return BriefingSection(
                title="Competitor News",
                content=content,
                priority=3,
                source_count=1,
                metadata={"total_articles": len(competitor_articles)},
            )

        except Exception as e:
            self.logger.error(f"Failed to create competitor news section: {str(e)}")
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
                title="Action Items",
                content=content,
                priority=7,
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

