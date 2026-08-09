"""
Jarvis OS — Google Calendar Tools.

Provides 8 tools for Google Calendar interaction via the Calendar API v3.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"


async def _get_client_and_account(account_email: str | None = None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _format_event(event: dict) -> str:
    """Format a single calendar event into readable text."""
    title = event.get("summary", "(No title)")
    location = event.get("location", "")
    description = event.get("description", "")

    # Handle all-day vs timed events
    start = event.get("start", {})
    end = event.get("end", {})
    if start.get("dateTime"):
        start_str = start["dateTime"]
        end_str = end.get("dateTime", "")
        all_day = False
    else:
        start_str = start.get("date", "")
        end_str = end.get("date", "")
        all_day = True

    attendees = event.get("attendees", [])
    attendee_list = ", ".join(a.get("email", "") for a in attendees[:5])
    if len(attendees) > 5:
        attendee_list += f" (+{len(attendees) - 5} more)"

    time_str = f"📅 All day: {start_str}" if all_day else f"🕐 {start_str} → {end_str}"

    parts = [f"**{title}**", time_str]
    if location:
        parts.append(f"📍 {location}")
    if attendee_list:
        parts.append(f"👥 {attendee_list}")
    if description:
        parts.append(f"📝 {description[:200]}")
    parts.append(f"ID: `{event.get('id', '')}`")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool: calendar_list_events
# ---------------------------------------------------------------------------

class CalendarListEventsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_list_events",
            description=(
                "List upcoming Google Calendar events. Can filter by date range. "
                "Defaults to showing events for the rest of today and next 7 days."
            ),
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="time_min", type="string", description="Start time in ISO 8601 format (e.g., '2024-01-15T00:00:00Z'). Defaults to now.", required=False),
                ToolParameter(name="time_max", type="string", description="End time in ISO 8601 format. Defaults to 7 days from now.", required=False),
                ToolParameter(name="max_results", type="integer", description="Maximum events to return (1-50)", required=False, default=20),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID to query. Defaults to 'primary'.", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        now = datetime.now(UTC)
        time_min = kwargs.get("time_min") or now.isoformat()
        time_max = kwargs.get("time_max") or (now + timedelta(days=7)).isoformat()
        max_results = min(int(kwargs.get("max_results", 20)), 50)
        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{CALENDAR_BASE}/calendars/{calendar_id}/events",
                    params={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "maxResults": max_results,
                        "singleEvents": "true",
                        "orderBy": "startTime",
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Calendar API error: {resp.status_code} — {resp.text}")

                events = resp.json().get("items", [])
                if not events:
                    return ToolResult(success=True, output="No upcoming events found in this time range.")

                output = f"📅 **{len(events)} upcoming event(s):**\n\n"
                for i, event in enumerate(events, 1):
                    output += f"{i}. {_format_event(event)}\n\n"

                return ToolResult(success=True, output=output, metadata={"events": events})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_get_event
# ---------------------------------------------------------------------------

class CalendarGetEventTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_get_event",
            description="Get full details of a specific Google Calendar event by its ID.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="event_id", type="string", description="The event ID"),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID (defaults to 'primary')", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.get("event_id")
        if not event_id:
            return ToolResult(success=False, error="event_id is required")

        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(f"{CALENDAR_BASE}/calendars/{calendar_id}/events/{event_id}")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Calendar API error: {resp.status_code}")

                event = resp.json()
                return ToolResult(success=True, output=_format_event(event), metadata=event)
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_create_event
# ---------------------------------------------------------------------------

class CalendarCreateEventTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_create_event",
            description="Create a new Google Calendar event with title, time, attendees, and location.",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="summary", type="string", description="Event title"),
                ToolParameter(name="start_time", type="string", description="Start time in ISO 8601 format (e.g., '2024-01-15T10:00:00+05:30')"),
                ToolParameter(name="end_time", type="string", description="End time in ISO 8601 format"),
                ToolParameter(name="description", type="string", description="Event description", required=False, default=""),
                ToolParameter(name="location", type="string", description="Event location", required=False, default=""),
                ToolParameter(name="attendees", type="string", description="Comma-separated attendee email addresses", required=False, default=""),
                ToolParameter(name="all_day", type="boolean", description="If true, create an all-day event (start_time/end_time should be dates like '2024-01-15')", required=False, default=False),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID (defaults to 'primary')", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        summary = kwargs.get("summary")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        if not all([summary, start_time, end_time]):
            return ToolResult(success=False, error="'summary', 'start_time', and 'end_time' are required.")

        all_day = kwargs.get("all_day", False)
        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        event_body: dict[str, Any] = {
            "summary": summary,
            "description": kwargs.get("description", ""),
            "location": kwargs.get("location", ""),
        }

        if all_day:
            event_body["start"] = {"date": start_time}
            event_body["end"] = {"date": end_time}
        else:
            event_body["start"] = {"dateTime": start_time}
            event_body["end"] = {"dateTime": end_time}

        attendees_str = kwargs.get("attendees", "")
        if attendees_str:
            event_body["attendees"] = [{"email": e.strip()} for e in attendees_str.split(",") if e.strip()]

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.post(
                    f"{CALENDAR_BASE}/calendars/{calendar_id}/events",
                    json=event_body,
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to create event: {resp.status_code} — {resp.text}")

                event = resp.json()
                return ToolResult(
                    success=True,
                    output=f"✅ Event '{summary}' created!\n{_format_event(event)}\nLink: {event.get('htmlLink', '')}",
                    metadata=event,
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_update_event
# ---------------------------------------------------------------------------

class CalendarUpdateEventTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_update_event",
            description="Update an existing Google Calendar event (title, time, location, description, attendees).",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="event_id", type="string", description="The event ID to update"),
                ToolParameter(name="summary", type="string", description="New event title", required=False),
                ToolParameter(name="start_time", type="string", description="New start time (ISO 8601)", required=False),
                ToolParameter(name="end_time", type="string", description="New end time (ISO 8601)", required=False),
                ToolParameter(name="description", type="string", description="New description", required=False),
                ToolParameter(name="location", type="string", description="New location", required=False),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.get("event_id")
        if not event_id:
            return ToolResult(success=False, error="event_id is required")

        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # Fetch current event
                get_resp = await client.get(f"{CALENDAR_BASE}/calendars/{calendar_id}/events/{event_id}")
                if get_resp.status_code != 200:
                    return ToolResult(success=False, error=f"Event not found: {get_resp.status_code}")

                event = get_resp.json()

                # Apply updates
                if kwargs.get("summary"):
                    event["summary"] = kwargs["summary"]
                if kwargs.get("description"):
                    event["description"] = kwargs["description"]
                if kwargs.get("location"):
                    event["location"] = kwargs["location"]
                if kwargs.get("start_time"):
                    event["start"] = {"dateTime": kwargs["start_time"]}
                if kwargs.get("end_time"):
                    event["end"] = {"dateTime": kwargs["end_time"]}

                resp = await client.put(
                    f"{CALENDAR_BASE}/calendars/{calendar_id}/events/{event_id}",
                    json=event,
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Failed to update: {resp.status_code} — {resp.text}")

                updated = resp.json()
                return ToolResult(success=True, output=f"✅ Event updated!\n{_format_event(updated)}", metadata=updated)
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_delete_event
# ---------------------------------------------------------------------------

class CalendarDeleteEventTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_delete_event",
            description="Delete a Google Calendar event by its ID.",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="event_id", type="string", description="The event ID to delete"),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.get("event_id")
        if not event_id:
            return ToolResult(success=False, error="event_id is required")

        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.delete(f"{CALENDAR_BASE}/calendars/{calendar_id}/events/{event_id}")
                if resp.status_code not in (200, 204):
                    return ToolResult(success=False, error=f"Failed to delete: {resp.status_code} — {resp.text}")

                return ToolResult(success=True, output=f"🗑️ Event {event_id} deleted successfully.")
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_check_availability
# ---------------------------------------------------------------------------

class CalendarCheckAvailabilityTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_check_availability",
            description="Check free/busy status for a given time range. Useful for finding open slots or checking if a time is available.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="time_min", type="string", description="Start of range (ISO 8601)"),
                ToolParameter(name="time_max", type="string", description="End of range (ISO 8601)"),
                ToolParameter(name="calendar_id", type="string", description="Calendar ID", required=False, default="primary"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        time_min = kwargs.get("time_min")
        time_max = kwargs.get("time_max")
        if not time_min or not time_max:
            return ToolResult(success=False, error="'time_min' and 'time_max' are required.")

        calendar_id = kwargs.get("calendar_id", "primary")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.post(
                    f"{CALENDAR_BASE}/freeBusy",
                    json={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "items": [{"id": calendar_id}],
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"FreeBusy API error: {resp.status_code}")

                data = resp.json()
                busy_slots = data.get("calendars", {}).get(calendar_id, {}).get("busy", [])

                if not busy_slots:
                    return ToolResult(success=True, output=f"✅ You are FREE for the entire period from {time_min} to {time_max}.")

                output = f"📅 You have {len(busy_slots)} busy period(s):\n"
                for slot in busy_slots:
                    output += f"  🔴 {slot['start']} → {slot['end']}\n"

                return ToolResult(success=True, output=output, metadata={"busy": busy_slots})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_list_calendars
# ---------------------------------------------------------------------------

class CalendarListCalendarsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_list_calendars",
            description="List all calendars the user has access to (primary, shared, subscribed).",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(f"{CALENDAR_BASE}/users/me/calendarList")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Calendar API error: {resp.status_code}")

                calendars = resp.json().get("items", [])
                output = "📅 **Your Calendars:**\n\n"
                for cal in calendars:
                    primary = " ⭐" if cal.get("primary") else ""
                    output += f"  - **{cal.get('summary', '(unnamed)')}**{primary}\n    ID: `{cal['id']}`\n"

                return ToolResult(success=True, output=output, metadata={"calendars": calendars})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: calendar_get_agenda
# ---------------------------------------------------------------------------

class CalendarGetAgendaTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar_get_agenda",
            description="Get today's agenda as a formatted summary. Shows all events for the rest of today.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        account_email = kwargs.get("account_email")
        now = datetime.now(UTC)
        end_of_day = now.replace(hour=23, minute=59, second=59)

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{CALENDAR_BASE}/calendars/primary/events",
                    params={
                        "timeMin": now.isoformat(),
                        "timeMax": end_of_day.isoformat(),
                        "singleEvents": "true",
                        "orderBy": "startTime",
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Calendar API error: {resp.status_code}")

                events = resp.json().get("items", [])
                if not events:
                    return ToolResult(success=True, output="📅 **Today's Agenda:** No more events for today! You're free. 🎉")

                output = f"📅 **Today's Agenda ({len(events)} event(s)):**\n\n"
                for i, event in enumerate(events, 1):
                    output += f"{i}. {_format_event(event)}\n\n"

                return ToolResult(success=True, output=output, metadata={"events": events, "count": len(events)})
        finally:
            await db.close()
