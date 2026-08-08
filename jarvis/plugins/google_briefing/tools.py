"""
Jarvis OS — Google Briefing Tools.

Provides orchestration tools that combine data from multiple Google services
to generate comprehensive summaries (e.g., Daily Briefing, Meeting Prep).
"""

import asyncio
from datetime import datetime, timezone

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.database.core import AsyncSessionLocal

# We will directly call the API endpoints here for efficiency,
# rather than instantiating the tools from other plugins.

CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


class DailyBriefingTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="daily_briefing",
            description="Generate a comprehensive morning briefing (calendar events, unread emails).",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        now = datetime.now(timezone.utc)
        end_of_day = now.replace(hour=23, minute=59, second=59)

        try:
            async with client:
                # 1. Fetch Calendar Events
                cal_task = client.get(
                    f"{CALENDAR_BASE}/calendars/primary/events",
                    params={
                        "timeMin": now.isoformat(),
                        "timeMax": end_of_day.isoformat(),
                        "singleEvents": "true",
                        "orderBy": "startTime",
                    },
                )

                # 2. Fetch Unread Email Count
                gmail_count_task = client.get(
                    f"{GMAIL_BASE}/messages",
                    params={"q": "is:unread label:INBOX", "maxResults": 1},
                )

                # Execute concurrently
                cal_resp, gmail_count_resp = await asyncio.gather(cal_task, gmail_count_task, return_exceptions=True)

                # Process Calendar
                agenda_text = ""
                if isinstance(cal_resp, Exception) or cal_resp.status_code != 200:
                    agenda_text = "⚠️ Could not load calendar events."
                else:
                    events = cal_resp.json().get("items", [])
                    if not events:
                        agenda_text = "You have no more events today. 🎉"
                    else:
                        for e in events:
                            title = e.get("summary", "(No title)")
                            start = e.get("start", {}).get("dateTime")
                            if start:
                                time_str = start[11:16] # extract HH:MM
                                agenda_text += f" - {time_str}: {title}\n"
                            else:
                                agenda_text += f" - All day: {title}\n"

                # Process Gmail
                email_text = ""
                if isinstance(gmail_count_resp, Exception) or gmail_count_resp.status_code != 200:
                    email_text = "⚠️ Could not load email count."
                else:
                    total = gmail_count_resp.json().get("resultSizeEstimate", 0)
                    email_text = f"You have **{total}** unread emails in your inbox."

                # Construct Briefing
                output = (
                    f"☀️ **Good Morning! Here is your daily briefing.**\n\n"
                    f"📅 **Agenda for Today:**\n{agenda_text}\n"
                    f"✉️ **Inbox Status:**\n{email_text}\n"
                )

                return ToolResult(success=True, output=output)
        finally:
            await db.close()


class MeetingPrepTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="meeting_prep",
            description="Generate a preparation document for a specific calendar event.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="event_id", type="string", description="The Calendar event ID"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.get("event_id")
        if not event_id:
            return ToolResult(success=False, error="event_id is required")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # 1. Fetch the event details
                event_resp = await client.get(f"{CALENDAR_BASE}/calendars/primary/events/{event_id}")
                if event_resp.status_code != 200:
                    return ToolResult(success=False, error=f"Event not found: {event_resp.status_code}")
                
                event = event_resp.json()
                title = event.get("summary", "(No title)")
                attendees = event.get("attendees", [])
                description = event.get("description", "No description provided.")

                # Extract emails to search
                emails_to_search = [a.get("email") for a in attendees if a.get("email") and not a.get("self")]

                email_context = "No attendees to search."
                if emails_to_search:
                    # Construct a query for recent emails from these attendees
                    query_parts = [f"from:{email} OR to:{email}" for email in emails_to_search]
                    query = f"({ ' OR '.join(query_parts) })"

                    # 2. Search Gmail for recent interactions
                    gmail_resp = await client.get(
                        f"{GMAIL_BASE}/messages",
                        params={"q": query, "maxResults": 3},
                    )
                    
                    if gmail_resp.status_code == 200:
                        messages = gmail_resp.json().get("messages", [])
                        if messages:
                            email_context = "Recent emails with attendees:\n"
                            for msg_ref in messages:
                                msg_resp = await client.get(
                                    f"{GMAIL_BASE}/messages/{msg_ref['id']}",
                                    params={"format": "metadata", "metadataHeaders": ["Subject", "Date"]},
                                )
                                if msg_resp.status_code == 200:
                                    msg_data = msg_resp.json()
                                    headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                                    email_context += f"- {headers.get('date', '')[:10]}: {headers.get('subject', '')}\n"
                        else:
                            email_context = "No recent emails found with attendees."
                    else:
                        email_context = "Failed to fetch email context."

                output = (
                    f"📝 **Meeting Prep: {title}**\n\n"
                    f"**Attendees:** {', '.join(emails_to_search) if emails_to_search else 'None'}\n\n"
                    f"**Description:**\n{description}\n\n"
                    f"**Context:**\n{email_context}"
                )

                return ToolResult(success=True, output=output)
        finally:
            await db.close()
