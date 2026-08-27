"""
Jarvis OS — Gmail Tools.

Provides 8 tools for Gmail interaction via the Gmail API v1.
All tools use the shared GoogleClient for authenticated requests.
"""

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.security.guardian import FraudScanner
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_client_and_account(account_email: str | None = None):
    """Get a DB session, account, and GoogleClient. Caller must manage lifecycle."""
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _parse_message_payload(payload: dict) -> dict:
    """Extract subject, from, to, date, and body from a Gmail message payload."""
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    # Extract body text
    body = ""
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
        if not body:
            # Fallback to HTML
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

    # List attachments
    attachments = []
    for part in payload.get("parts", []):
        if part.get("filename"):
            attachments.append({
                "filename": part["filename"],
                "mimeType": part.get("mimeType"),
                "size": part.get("body", {}).get("size", 0),
            })

    return {
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
        "body": body[:5000],  # Cap at 5000 chars to avoid flooding context
        "attachments": attachments,
    }


def _create_raw_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "", thread_id: str = "") -> str:
    """Create a base64url-encoded raw email message."""
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw


# ---------------------------------------------------------------------------
# Tool: gmail_list_messages
# ---------------------------------------------------------------------------

class GmailListMessagesTool(Tool):
    """Search and list Gmail messages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_list_messages",
            description=(
                "Search and list emails in Gmail. Use Gmail search syntax for the query "
                "(e.g., 'from:john@example.com', 'subject:invoice', 'is:unread', "
                "'after:2024/01/01 before:2024/12/31'). Returns message summaries."
            ),
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Gmail search query (e.g., 'is:unread', 'from:boss@company.com')", required=False, default="is:inbox"),
                ToolParameter(name="max_results", type="integer", description="Maximum number of messages to return (1-50)", required=False, default=10),
                ToolParameter(name="account_email", type="string", description="Specific Google account email to use, or 'all' to search across all connected accounts. (optional, uses default if not provided)", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "is:inbox")
        max_results = min(int(kwargs.get("max_results", 10)), 50)
        account_email = kwargs.get("account_email")

        if account_email == "all":
            from jarvis.integrations.google_client import get_all_google_accounts
            db = AsyncSessionLocal()
            try:
                accounts = await get_all_google_accounts(db)
            finally:
                await db.close()
                
            if not accounts:
                return ToolResult(success=False, error="No Google account connected. Please connect one in Settings → Integrations.")
                
            all_summaries = []
            all_result_texts = []
            
            for acc in accounts:
                res = await self._execute_for_account(acc.account_id, query, max_results)
                if res.success:
                    if "No messages found" not in res.output:
                        all_result_texts.append(f"=== {acc.account_id} ===\n{res.output}")
                        if "messages" in res.metadata:
                            all_summaries.extend(res.metadata["messages"])
                            
            if not all_summaries:
                return ToolResult(success=True, output="No messages found matching your query across any account.")
                
            return ToolResult(success=True, output="\n\n".join(all_result_texts), metadata={"messages": all_summaries})
        else:
            return await self._execute_for_account(account_email, query, max_results)

    async def _execute_for_account(self, account_email: str | None, query: str, max_results: int) -> ToolResult:
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected. Please connect one in Settings → Integrations.")

        try:
            async with client:
                # List message IDs
                resp = await client.get(
                    f"{GMAIL_BASE}/messages",
                    params={"q": query, "maxResults": max_results},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Gmail API error: {resp.status_code} — {resp.text}")

                data = resp.json()
                messages = data.get("messages", [])

                if not messages:
                    return ToolResult(success=True, output="No messages found matching your query.")

                # Fetch headers for each message
                summaries = []
                for msg_ref in messages:
                    msg_resp = await client.get(
                        f"{GMAIL_BASE}/messages/{msg_ref['id']}",
                        params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                    )
                    if msg_resp.status_code == 200:
                        msg_data = msg_resp.json()
                        headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                        snippet = msg_data.get("snippet", "")
                        labels = msg_data.get("labelIds", [])
                        summaries.append({
                            "id": msg_ref["id"],
                            "subject": headers.get("subject", "(no subject)"),
                            "from": headers.get("from", ""),
                            "date": headers.get("date", ""),
                            "snippet": snippet,
                            "unread": "UNREAD" in labels,
                        })

                result_text = f"Found {len(summaries)} message(s):\n\n"
                for i, s in enumerate(summaries, 1):
                    unread_marker = "📩 " if s["unread"] else "  "
                    result_text += f"{unread_marker}{i}. **{s['subject']}**\n   From: {s['from']}\n   Date: {s['date']}\n   Preview: {s['snippet'][:100]}...\n   ID: `{s['id']}`\n\n"

                return ToolResult(success=True, output=result_text, metadata={"messages": summaries})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_read_message
# ---------------------------------------------------------------------------

class GmailReadMessageTool(Tool):
    """Read the full content of a specific email."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_read_message",
            description="Read the full content of a specific email by its message ID. Returns subject, sender, body text, and attachments list.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="message_id", type="string", description="The Gmail message ID to read"),
                ToolParameter(name="account_email", type="string", description="Specific Google account email to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message_id = kwargs.get("message_id")
        if not message_id:
            return ToolResult(success=False, error="message_id is required")

        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{GMAIL_BASE}/messages/{message_id}",
                    params={"format": "full"},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Gmail API error: {resp.status_code} — {resp.text}")

                data = resp.json()
                parsed = _parse_message_payload(data.get("payload", {}))
                parsed["thread_id"] = data.get("threadId", "")
                parsed["labels"] = data.get("labelIds", [])

                output = (
                    f"**Subject:** {parsed['subject']}\n"
                    f"**From:** {parsed['from']}\n"
                    f"**To:** {parsed['to']}\n"
                    f"**Date:** {parsed['date']}\n"
                    f"**Labels:** {', '.join(parsed['labels'])}\n\n"
                    f"---\n\n{parsed['body']}"
                )

                if parsed["attachments"]:
                    output += "\n\n**Attachments:**\n"
                    for att in parsed["attachments"]:
                        output += f"  - {att['filename']} ({att['mimeType']}, {att['size']} bytes)\n"
                        
                is_suspicious, output = FraudScanner.scan(output, source="Gmail")

                return ToolResult(success=True, output=output, metadata=parsed)
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_send_message
# ---------------------------------------------------------------------------

class GmailSendMessageTool(Tool):
    """Send an email via Gmail."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_send_message",
            description="Compose and send an email via Gmail. Requires recipient, subject, and body.",
            category=ToolCategory.COMMUNICATION,
            dangerous=True,  # Sends email on behalf of user
            parameters=[
                ToolParameter(name="to", type="string", description="Recipient email address(es), comma-separated"),
                ToolParameter(name="subject", type="string", description="Email subject line"),
                ToolParameter(name="body", type="string", description="Email body text (plain text)"),
                ToolParameter(name="cc", type="string", description="CC recipients, comma-separated", required=False),
                ToolParameter(name="bcc", type="string", description="BCC recipients, comma-separated", required=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to send from", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        if not all([to, subject, body]):
            return ToolResult(success=False, error="'to', 'subject', and 'body' are all required.")

        cc = kwargs.get("cc", "")
        bcc = kwargs.get("bcc", "")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            raw = _create_raw_email(to, subject, body, cc, bcc)
            async with client:
                resp = await client.post(
                    f"{GMAIL_BASE}/messages/send",
                    json={"raw": raw},
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to send: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"Email sent successfully to {to}. Message ID: {data.get('id')}",
                    metadata={"message_id": data.get("id"), "thread_id": data.get("threadId")},
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_draft_message
# ---------------------------------------------------------------------------

class GmailDraftMessageTool(Tool):
    """Create an email draft without sending."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_draft_message",
            description="Create an email draft in Gmail without sending it. The draft will appear in the user's Drafts folder.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="to", type="string", description="Recipient email address(es)"),
                ToolParameter(name="subject", type="string", description="Email subject line"),
                ToolParameter(name="body", type="string", description="Email body text"),
                ToolParameter(name="cc", type="string", description="CC recipients", required=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        if not all([to, subject, body]):
            return ToolResult(success=False, error="'to', 'subject', and 'body' are all required.")

        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            raw = _create_raw_email(to, subject, body, kwargs.get("cc", ""))
            async with client:
                resp = await client.post(
                    f"{GMAIL_BASE}/drafts",
                    json={"message": {"raw": raw}},
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to create draft: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"Draft created for '{subject}' to {to}. Draft ID: {data.get('id')}",
                    metadata={"draft_id": data.get("id")},
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_reply_to_message
# ---------------------------------------------------------------------------

class GmailReplyToMessageTool(Tool):
    """Reply to a specific email thread."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_reply_to_message",
            description="Reply to a specific email thread in Gmail. Uses the thread ID to maintain conversation context.",
            category=ToolCategory.COMMUNICATION,
            dangerous=True,
            parameters=[
                ToolParameter(name="thread_id", type="string", description="The thread ID to reply to"),
                ToolParameter(name="to", type="string", description="Recipient email address"),
                ToolParameter(name="body", type="string", description="Reply body text"),
                ToolParameter(name="subject", type="string", description="Reply subject (usually 'Re: ...')", required=False, default=""),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        thread_id = kwargs.get("thread_id")
        to = kwargs.get("to")
        body = kwargs.get("body")
        if not all([thread_id, to, body]):
            return ToolResult(success=False, error="'thread_id', 'to', and 'body' are all required.")

        subject = kwargs.get("subject", "")
        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            raw = _create_raw_email(to, subject, body)
            async with client:
                resp = await client.post(
                    f"{GMAIL_BASE}/messages/send",
                    json={"raw": raw, "threadId": thread_id},
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to reply: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"Reply sent to {to} in thread {thread_id}.",
                    metadata={"message_id": data.get("id"), "thread_id": data.get("threadId")},
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_get_labels
# ---------------------------------------------------------------------------

class GmailGetLabelsTool(Tool):
    """List all Gmail labels."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_get_labels",
            description="List all Gmail labels (Inbox, Sent, Spam, custom labels, etc.).",
            category=ToolCategory.COMMUNICATION,
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
                resp = await client.get(f"{GMAIL_BASE}/labels")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Gmail API error: {resp.status_code}")

                labels = resp.json().get("labels", [])
                output = "Gmail Labels:\n"
                for label in labels:
                    label_type = label.get("type", "user")
                    output += f"  - {label['name']} (ID: {label['id']}, type: {label_type})\n"

                return ToolResult(success=True, output=output, metadata={"labels": labels})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_modify_labels
# ---------------------------------------------------------------------------

class GmailModifyLabelsTool(Tool):
    """Add or remove labels from messages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_modify_labels",
            description=(
                "Add or remove labels from Gmail messages. Common uses: archive (remove INBOX), "
                "mark as read (remove UNREAD), mark as unread (add UNREAD), star (add STARRED)."
            ),
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="message_id", type="string", description="The message ID to modify"),
                ToolParameter(name="add_labels", type="string", description="Comma-separated label IDs to add (e.g., 'STARRED,IMPORTANT')", required=False, default=""),
                ToolParameter(name="remove_labels", type="string", description="Comma-separated label IDs to remove (e.g., 'UNREAD,INBOX')", required=False, default=""),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        message_id = kwargs.get("message_id")
        if not message_id:
            return ToolResult(success=False, error="message_id is required")

        add_labels = [l.strip() for l in kwargs.get("add_labels", "").split(",") if l.strip()]
        remove_labels = [l.strip() for l in kwargs.get("remove_labels", "").split(",") if l.strip()]

        if not add_labels and not remove_labels:
            return ToolResult(success=False, error="Specify at least one of add_labels or remove_labels.")

        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.post(
                    f"{GMAIL_BASE}/messages/{message_id}/modify",
                    json={"addLabelIds": add_labels, "removeLabelIds": remove_labels},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Failed to modify labels: {resp.status_code} — {resp.text}")

                actions = []
                if add_labels:
                    actions.append(f"added [{', '.join(add_labels)}]")
                if remove_labels:
                    actions.append(f"removed [{', '.join(remove_labels)}]")

                return ToolResult(success=True, output=f"Labels modified on message {message_id}: {', '.join(actions)}")
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: gmail_get_unread_count
# ---------------------------------------------------------------------------

class GmailGetUnreadCountTool(Tool):
    """Get the count of unread messages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="gmail_get_unread_count",
            description="Get the count of unread emails in Gmail, optionally filtered by label.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="label", type="string", description="Label to filter by (e.g., 'INBOX', 'IMPORTANT')", required=False, default="INBOX"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        label = kwargs.get("label", "INBOX")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{GMAIL_BASE}/messages",
                    params={"q": f"is:unread label:{label}", "maxResults": 1},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Gmail API error: {resp.status_code}")

                data = resp.json()
                total = data.get("resultSizeEstimate", 0)

                return ToolResult(
                    success=True,
                    output=f"You have approximately {total} unread message(s) in {label}.",
                    metadata={"unread_count": total, "label": label},
                )
        finally:
            await db.close()
