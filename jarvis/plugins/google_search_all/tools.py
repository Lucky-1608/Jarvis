"""
Jarvis OS — Google Cross-Service Search.

Provides a unified search tool across Gmail and Drive.
"""

import asyncio

from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


class GlobalSearchTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="google_search_all",
            description="Search for a query across both Gmail and Google Drive simultaneously.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="The search query"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(success=False, error="Search query is required.")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # 1. Search Gmail
                gmail_task = client.get(
                    f"{GMAIL_BASE}/messages",
                    params={"q": query, "maxResults": 5},
                )

                # 2. Search Drive
                drive_task = client.get(
                    f"{DRIVE_BASE}/files",
                    params={
                        "q": f"name contains '{query}' or fullText contains '{query}'",
                        "pageSize": 5,
                        "fields": "files(id,name,mimeType,webViewLink)",
                    },
                )

                # Execute concurrently
                gmail_resp, drive_resp = await asyncio.gather(gmail_task, drive_task, return_exceptions=True)

                output_parts = [f"🔍 **Search Results for '{query}':**\n"]

                # Process Gmail Results
                if isinstance(gmail_resp, Exception) or gmail_resp.status_code != 200:
                    output_parts.append("📧 **Gmail:** (Error fetching results)\n")
                else:
                    messages = gmail_resp.json().get("messages", [])
                    if not messages:
                        output_parts.append("📧 **Gmail:** No matching emails.\n")
                    else:
                        output_parts.append(f"📧 **Gmail ({len(messages)} result(s)):**")
                        for i, msg_ref in enumerate(messages, 1):
                            # Fetch headers for summary
                            msg_resp = await client.get(
                                f"{GMAIL_BASE}/messages/{msg_ref['id']}",
                                params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
                            )
                            if msg_resp.status_code == 200:
                                msg_data = msg_resp.json()
                                headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                                subject = headers.get("subject", "(no subject)")
                                from_addr = headers.get("from", "")
                                output_parts.append(f"  {i}. {subject} (From: {from_addr})")
                            else:
                                output_parts.append(f"  {i}. [Message ID: {msg_ref['id']}]")
                        output_parts.append("")

                # Process Drive Results
                if isinstance(drive_resp, Exception) or drive_resp.status_code != 200:
                    output_parts.append("📁 **Drive:** (Error fetching results)\n")
                else:
                    files = drive_resp.json().get("files", [])
                    if not files:
                        output_parts.append("📁 **Drive:** No matching files.\n")
                    else:
                        output_parts.append(f"📁 **Drive ({len(files)} result(s)):**")
                        for i, f in enumerate(files, 1):
                            is_folder = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
                            output_parts.append(f"  {i}. {is_folder} {f.get('name')} (Link: {f.get('webViewLink', 'N/A')})")

                return ToolResult(success=True, output="\n".join(output_parts))
        finally:
            await db.close()
