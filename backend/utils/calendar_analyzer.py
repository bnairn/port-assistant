"""
Calendar analysis utilities for detecting conflicts and issues.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from models.data_sources import CalendarEvent
from pydantic import BaseModel, Field


def normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC if naive)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CalendarConflict(BaseModel):
    """Model for calendar conflicts"""
    conflict_type: str = Field(..., description="Type of conflict (overlap, back_to_back)")
    severity: str = Field(..., description="Severity level (high, medium, low)")
    events: List[Dict[str, Any]] = Field(..., description="Events involved in conflict")
    description: str = Field(..., description="Human-readable description")
    suggestion: Optional[str] = Field(None, description="Suggested resolution")


def detect_overlapping_events(events: List[CalendarEvent]) -> List[CalendarConflict]:
    """
    Detect events with time overlaps.

    Args:
        events: List of calendar events

    Returns:
        List of conflicts for overlapping events
    """
    conflicts = []

    # Sort events by start time
    sorted_events = sorted(events, key=lambda e: e.start_time)

    for i in range(len(sorted_events)):
        for j in range(i + 1, len(sorted_events)):
            event1 = sorted_events[i]
            event2 = sorted_events[j]

            # Normalize datetimes to handle timezone-aware/naive comparison
            e1_start = normalize_datetime(event1.start_time)
            e1_end = normalize_datetime(event1.end_time)
            e2_start = normalize_datetime(event2.start_time)
            e2_end = normalize_datetime(event2.end_time)

            # Check if events overlap
            if e1_end > e2_start and e1_start < e2_end:
                overlap_start = max(e1_start, e2_start)
                overlap_end = min(e1_end, e2_end)
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60

                # Determine severity
                if overlap_minutes >= 30:
                    severity = "high"
                elif overlap_minutes >= 15:
                    severity = "medium"
                else:
                    severity = "low"

                conflicts.append(CalendarConflict(
                    conflict_type="overlap",
                    severity=severity,
                    events=[
                        {
                            "id": event1.id,
                            "summary": event1.summary,
                            "start_time": event1.start_time.isoformat(),
                            "end_time": event1.end_time.isoformat()
                        },
                        {
                            "id": event2.id,
                            "summary": event2.summary,
                            "start_time": event2.start_time.isoformat(),
                            "end_time": event2.end_time.isoformat()
                        }
                    ],
                    description=f"'{event1.summary}' and '{event2.summary}' overlap by {int(overlap_minutes)} minutes",
                    suggestion="Consider rescheduling one of these events or declining if not critical"
                ))

    return conflicts


def find_back_to_back_meetings(
    events: List[CalendarEvent],
    buffer_minutes: int = 5
) -> List[CalendarConflict]:
    """
    Find meetings with no buffer time between them.

    Args:
        events: List of calendar events
        buffer_minutes: Minimum buffer time required (default: 5 minutes)

    Returns:
        List of conflicts for back-to-back meetings
    """
    conflicts = []

    # Sort events by start time
    sorted_events = sorted(events, key=lambda e: e.start_time)

    for i in range(len(sorted_events) - 1):
        event1 = sorted_events[i]
        event2 = sorted_events[i + 1]

        # Normalize datetimes
        e1_start = normalize_datetime(event1.start_time)
        e1_end = normalize_datetime(event1.end_time)
        e2_start = normalize_datetime(event2.start_time)
        e2_end = normalize_datetime(event2.end_time)

        # Calculate gap between meetings
        gap = e2_start - e1_end
        gap_minutes = gap.total_seconds() / 60

        # Check if gap is less than required buffer
        if 0 <= gap_minutes < buffer_minutes:
            # Determine severity based on meeting duration
            total_duration = (e1_end - e1_start).total_seconds() / 60
            total_duration += (e2_end - e2_start).total_seconds() / 60

            if total_duration >= 120:  # 2+ hours of back-to-back meetings
                severity = "high"
            elif total_duration >= 60:  # 1+ hours
                severity = "medium"
            else:
                severity = "low"

            conflicts.append(CalendarConflict(
                conflict_type="back_to_back",
                severity=severity,
                events=[
                    {
                        "id": event1.id,
                        "summary": event1.summary,
                        "start_time": event1.start_time.isoformat(),
                        "end_time": event1.end_time.isoformat()
                    },
                    {
                        "id": event2.id,
                        "summary": event2.summary,
                        "start_time": event2.start_time.isoformat(),
                        "end_time": event2.end_time.isoformat()
                    }
                ],
                description=f"Only {int(gap_minutes)} minute(s) between '{event1.summary}' and '{event2.summary}'",
                suggestion="Consider adding a buffer for breaks, travel time, or preparation"
            ))

    return conflicts


def analyze_calendar(events: List[CalendarEvent]) -> Dict[str, Any]:
    """
    Comprehensive calendar analysis.

    Args:
        events: List of calendar events

    Returns:
        Dictionary with analysis results including all conflicts
    """
    overlaps = detect_overlapping_events(events)
    back_to_back = find_back_to_back_meetings(events)

    all_conflicts = overlaps + back_to_back

    # Calculate statistics
    high_severity = [c for c in all_conflicts if c.severity == "high"]
    medium_severity = [c for c in all_conflicts if c.severity == "medium"]
    low_severity = [c for c in all_conflicts if c.severity == "low"]

    return {
        "total_events": len(events),
        "total_conflicts": len(all_conflicts),
        "overlapping_events": len(overlaps),
        "back_to_back_meetings": len(back_to_back),
        "high_severity_conflicts": len(high_severity),
        "medium_severity_conflicts": len(medium_severity),
        "low_severity_conflicts": len(low_severity),
        "conflicts": [c.model_dump() for c in all_conflicts],
        "needs_attention": len(high_severity) > 0 or len(medium_severity) > 2
    }
