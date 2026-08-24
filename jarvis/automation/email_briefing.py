"""
Jarvis OS - Email Briefing Automation

Background task for checking emails, analyzing them, and pushing summaries to mobile.
"""
import asyncio
import datetime
import structlog
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.plugins.google_gmail.tools import GmailListMessagesTool, GmailReadMessageTool

logger = structlog.get_logger(__name__)

class EmailBriefingTask:
    """Collects unread emails, summarizes them, and publishes a notification."""

    def __init__(self, target_hour: int = 8, target_minute: int = 0):
        self.target_hour = target_hour
        self.target_minute = target_minute
        self._bus = get_event_bus()
        self._list_tool = GmailListMessagesTool()
        self._read_tool = GmailReadMessageTool()
        self._last_analysis_time = None

    async def execute(self):
        """Run the email analysis collection and publish."""
        logger.info("email_briefing.execute.started")
        
        try:
            # Get unread emails
            query = "is:unread"
            if self._last_analysis_time:
                epoch = int(self._last_analysis_time.timestamp())
                query += f" after:{epoch}"
                
            list_result = await self._list_tool.execute(query=query)
            self._last_analysis_time = datetime.datetime.now()
            
            if not list_result.success:
                logger.error("email_briefing.list_failed", error=list_result.error)
                return
                
            messages_str = list_result.data.get("output", "")
            
            if "No matching emails" in messages_str or not messages_str.strip():
                summary = "You have no new unread important emails."
            else:
                summary = f"📧 Email Briefing:\n\n{messages_str}\n\n(Generated autonomously by Jarvis)"

            await self._bus.publish(Event(
                type=EventTypes.NOTIFICATION_SEND,
                data={
                    "title": "Email Briefing",
                    "content": summary,
                    "priority": "critical",
                    "details": {"source": "gmail"}
                },
                source="email_briefing"
            ))

            logger.info("email_briefing.execute.completed", message_count=messages_str.count("ID:"))
        except Exception as e:
            logger.error("email_briefing.execute.failed", error=str(e))
