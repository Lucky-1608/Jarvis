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
            from jarvis.integrations.google_client import get_all_google_accounts
            from jarvis.database.core import AsyncSessionLocal

            db = AsyncSessionLocal()
            try:
                accounts = await get_all_google_accounts(db)
            finally:
                await db.close()

            if not accounts:
                logger.warning("email_briefing.no_accounts")
                return

            # Get unread emails
            query = "is:unread"
            if self._last_analysis_time:
                epoch = int(self._last_analysis_time.timestamp())
                query += f" after:{epoch}"
                
            self._last_analysis_time = datetime.datetime.now()

            all_messages = []
            for account in accounts:
                list_result = await self._list_tool.execute(query=query, account_email=account.account_id)
                if not list_result.success:
                    logger.error("email_briefing.list_failed", account=account.account_id, error=list_result.error)
                    continue
                
                messages_str = list_result.data.get("output", "")
                if "No messages found matching your query." not in messages_str and messages_str.strip():
                    all_messages.append(f"=== {account.account_id} ===\n{messages_str}")

            if not all_messages:
                summary = "You have no new unread important emails."
                message_count = 0
            else:
                combined_messages = "\n\n".join(all_messages)
                summary = f"📧 Email Briefing:\n\n{combined_messages}\n\n(Generated autonomously by Jarvis)"
                message_count = combined_messages.count("ID:")

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

            logger.info("email_briefing.execute.completed", message_count=message_count)
        except Exception as e:
            logger.error("email_briefing.execute.failed", error=str(e))
