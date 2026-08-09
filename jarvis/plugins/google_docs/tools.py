"""
Jarvis OS — Google Docs Tools.

Provides 4 tools for Google Docs API v1 interaction.
"""


from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

DOCS_BASE = "https://docs.googleapis.com/v1/documents"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _extract_doc_text(body: dict) -> str:
    """Extract plain text from a Google Docs document body."""
    text_parts = []

    for element in body.get("content", []):
        paragraph = element.get("paragraph")
        if paragraph:
            for pe in paragraph.get("elements", []):
                text_run = pe.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))

        table = element.get("table")
        if table:
            for row in table.get("tableRows", []):
                row_texts = []
                for cell in row.get("tableCells", []):
                    cell_text = ""
                    for content in cell.get("content", []):
                        para = content.get("paragraph")
                        if para:
                            for pe in para.get("elements", []):
                                tr = pe.get("textRun")
                                if tr:
                                    cell_text += tr.get("content", "")
                    row_texts.append(cell_text.strip())
                text_parts.append(" | ".join(row_texts) + "\n")

    return "".join(text_parts)


class DocsReadTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="docs_read",
            description="Read the full content of a Google Doc as plain text.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="document_id", type="string", description="The Google Doc document ID"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        document_id = kwargs.get("document_id")
        if not document_id:
            return ToolResult(success=False, error="document_id is required")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(f"{DOCS_BASE}/{document_id}")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Docs API error: {resp.status_code} — {resp.text}")

                doc = resp.json()
                title = doc.get("title", "(untitled)")
                text = _extract_doc_text(doc.get("body", {}))

                return ToolResult(
                    success=True,
                    output=f"📄 **{title}**\n\n{text[:10000]}",
                    metadata={"title": title, "document_id": document_id},
                )
        finally:
            await db.close()


class DocsCreateTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="docs_create",
            description="Create a new Google Doc with a title and optional initial content.",
            category=ToolCategory.FILE,
            dangerous=True,
            parameters=[
                ToolParameter(name="title", type="string", description="Document title"),
                ToolParameter(name="content", type="string", description="Initial text content to add to the document", required=False, default=""),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        if not title:
            return ToolResult(success=False, error="Title is required.")

        content = kwargs.get("content", "")
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # Create the document
                resp = await client.post(DOCS_BASE, json={"title": title})
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Create failed: {resp.status_code}")

                doc = resp.json()
                doc_id = doc.get("documentId", "")

                # Insert content if provided
                if content:
                    await client.post(
                        f"{DOCS_BASE}/{doc_id}:batchUpdate",
                        json={
                            "requests": [
                                {
                                    "insertText": {
                                        "location": {"index": 1},
                                        "text": content,
                                    }
                                }
                            ]
                        },
                    )

                return ToolResult(
                    success=True,
                    output=f"📄 Document **{title}** created!\nID: `{doc_id}`\nURL: https://docs.google.com/document/d/{doc_id}/edit",
                    metadata=doc,
                )
        finally:
            await db.close()


class DocsAppendTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="docs_append",
            description="Append text to the end of an existing Google Doc.",
            category=ToolCategory.FILE,
            dangerous=True,
            parameters=[
                ToolParameter(name="document_id", type="string", description="The document ID"),
                ToolParameter(name="text", type="string", description="Text to append"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        document_id = kwargs.get("document_id")
        text = kwargs.get("text")
        if not document_id or not text:
            return ToolResult(success=False, error="'document_id' and 'text' are required.")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # Get current document to find end index
                doc_resp = await client.get(f"{DOCS_BASE}/{document_id}")
                if doc_resp.status_code != 200:
                    return ToolResult(success=False, error=f"Document not found: {doc_resp.status_code}")

                doc = doc_resp.json()
                # The end index of the document body (last content element)
                body_content = doc.get("body", {}).get("content", [])
                if body_content:
                    end_index = body_content[-1].get("endIndex", 1) - 1
                else:
                    end_index = 1

                resp = await client.post(
                    f"{DOCS_BASE}/{document_id}:batchUpdate",
                    json={
                        "requests": [
                            {
                                "insertText": {
                                    "location": {"index": end_index},
                                    "text": "\n" + text,
                                }
                            }
                        ]
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Append failed: {resp.status_code} — {resp.text}")

                return ToolResult(
                    success=True,
                    output=f"✅ Text appended to document `{document_id}`.",
                )
        finally:
            await db.close()


class DocsSearchTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="docs_search",
            description="Search for Google Docs by title. Returns a list of matching documents.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Search query for document title"),
                ToolParameter(name="max_results", type="integer", description="Max results (1-20)", required=False, default=10),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 10)), 20)
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                drive_query = f"name contains '{query}' and mimeType='application/vnd.google-apps.document'"
                resp = await client.get(
                    f"{DRIVE_BASE}/files",
                    params={
                        "q": drive_query,
                        "pageSize": max_results,
                        "fields": "files(id,name,modifiedTime,webViewLink)",
                        "orderBy": "modifiedTime desc",
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Search failed: {resp.status_code}")

                files = resp.json().get("files", [])
                if not files:
                    return ToolResult(success=True, output=f"No Google Docs found matching '{query}'.")

                output = f"📄 Found {len(files)} document(s):\n\n"
                for i, f in enumerate(files, 1):
                    output += f"{i}. **{f['name']}**\n   Modified: {f.get('modifiedTime', '')}\n   ID: `{f['id']}`\n   URL: {f.get('webViewLink', '')}\n\n"

                return ToolResult(success=True, output=output, metadata={"files": files})
        finally:
            await db.close()
