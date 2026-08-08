"""
Jarvis OS — Google Drive Tools.

Provides 7 tools for Google Drive interaction via the Drive API v3.
"""

import base64
import os
from pathlib import Path
from typing import Any

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.database.core import AsyncSessionLocal

DRIVE_BASE = "https://www.googleapis.com/drive/v3"
UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

# Google Docs/Sheets/Slides MIME types and their export formats
EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document": ("text/plain", "Google Doc"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "Google Sheet"),
    "application/vnd.google-apps.presentation": ("text/plain", "Google Slides"),
}


async def _get_client_and_account(account_email: str | None = None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _format_file(f: dict) -> str:
    """Format a Drive file entry into readable text."""
    name = f.get("name", "(unnamed)")
    mime = f.get("mimeType", "")
    size = f.get("size", "")
    modified = f.get("modifiedTime", "")
    file_id = f.get("id", "")

    size_str = f" ({int(size):,} bytes)" if size else ""
    is_folder = "📁" if mime == "application/vnd.google-apps.folder" else "📄"
    google_type = ""
    if "google-apps.document" in mime:
        google_type = " [Google Doc]"
    elif "google-apps.spreadsheet" in mime:
        google_type = " [Google Sheet]"
    elif "google-apps.presentation" in mime:
        google_type = " [Google Slides]"

    return f"{is_folder} **{name}**{google_type}{size_str}\n   Modified: {modified}\n   ID: `{file_id}`"


# ---------------------------------------------------------------------------
# Tool: drive_search_files
# ---------------------------------------------------------------------------

class DriveSearchFilesTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_search_files",
            description=(
                "Search for files in Google Drive by name, content, or type. "
                "Uses Drive search query syntax (e.g., \"name contains 'invoice'\", "
                "\"mimeType='application/pdf'\", \"fullText contains 'budget'\")."
            ),
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Search query. Examples: \"name contains 'report'\", \"mimeType='application/pdf'\", \"fullText contains 'Q3 budget'\""),
                ToolParameter(name="max_results", type="integer", description="Max files to return (1-50)", required=False, default=20),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 20)), 50)
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                params: dict[str, Any] = {
                    "pageSize": max_results,
                    "fields": "files(id,name,mimeType,size,modifiedTime,owners,webViewLink)",
                    "orderBy": "modifiedTime desc",
                }
                if query:
                    params["q"] = query

                resp = await client.get(f"{DRIVE_BASE}/files", params=params)
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Drive API error: {resp.status_code} — {resp.text}")

                files = resp.json().get("files", [])
                if not files:
                    return ToolResult(success=True, output="No files found matching your query.")

                output = f"📁 **Found {len(files)} file(s):**\n\n"
                for i, f in enumerate(files, 1):
                    output += f"{i}. {_format_file(f)}\n\n"

                return ToolResult(success=True, output=output, metadata={"files": files})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_read_file
# ---------------------------------------------------------------------------

class DriveReadFileTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_read_file",
            description=(
                "Read the content of a file from Google Drive. "
                "Automatically exports Google Docs to plain text and Google Sheets to CSV. "
                "For binary files (images, PDFs), returns metadata only."
            ),
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="file_id", type="string", description="The Drive file ID"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_id = kwargs.get("file_id")
        if not file_id:
            return ToolResult(success=False, error="file_id is required")

        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # First get file metadata
                meta_resp = await client.get(
                    f"{DRIVE_BASE}/files/{file_id}",
                    params={"fields": "id,name,mimeType,size"},
                )
                if meta_resp.status_code != 200:
                    return ToolResult(success=False, error=f"File not found: {meta_resp.status_code}")

                meta = meta_resp.json()
                mime = meta.get("mimeType", "")

                # Google Workspace files need export
                if mime in EXPORT_MIME_MAP:
                    export_mime, type_name = EXPORT_MIME_MAP[mime]
                    resp = await client.get(
                        f"{DRIVE_BASE}/files/{file_id}/export",
                        params={"mimeType": export_mime},
                    )
                    if resp.status_code != 200:
                        return ToolResult(success=False, error=f"Export failed: {resp.status_code}")

                    content = resp.text[:10000]  # Cap content
                    return ToolResult(
                        success=True,
                        output=f"📄 **{meta['name']}** ({type_name}):\n\n{content}",
                        metadata=meta,
                    )

                # Plain text / code files
                if mime.startswith("text/") or mime in ("application/json", "application/xml"):
                    resp = await client.get(
                        f"{DRIVE_BASE}/files/{file_id}",
                        params={"alt": "media"},
                    )
                    if resp.status_code != 200:
                        return ToolResult(success=False, error=f"Download failed: {resp.status_code}")

                    content = resp.text[:10000]
                    return ToolResult(
                        success=True,
                        output=f"📄 **{meta['name']}**:\n\n{content}",
                        metadata=meta,
                    )

                # Binary files — metadata only
                return ToolResult(
                    success=True,
                    output=f"📄 **{meta['name']}** is a binary file ({mime}, {meta.get('size', '?')} bytes). Cannot display content inline.",
                    metadata=meta,
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_upload_file
# ---------------------------------------------------------------------------

class DriveUploadFileTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_upload_file",
            description="Upload a local file to Google Drive.",
            category=ToolCategory.FILE,
            dangerous=True,
            parameters=[
                ToolParameter(name="file_path", type="string", description="Absolute path to the local file to upload"),
                ToolParameter(name="folder_id", type="string", description="Drive folder ID to upload into (optional, defaults to root)", required=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult(success=False, error="file_path is required")

        path = Path(file_path)
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")

        folder_id = kwargs.get("folder_id")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            import mimetypes
            content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

            file_metadata: dict[str, Any] = {"name": path.name}
            if folder_id:
                file_metadata["parents"] = [folder_id]

            async with client:
                # Simple upload for files < 5MB
                file_size = path.stat().st_size
                if file_size > 5 * 1024 * 1024:
                    return ToolResult(success=False, error="File too large for simple upload. Max 5MB supported currently.")

                file_content = path.read_bytes()

                # Multipart upload
                import json as json_mod
                boundary = "jarvis_upload_boundary"
                body = (
                    f"--{boundary}\r\n"
                    f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                    f"{json_mod.dumps(file_metadata)}\r\n"
                    f"--{boundary}\r\n"
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode() + file_content + f"\r\n--{boundary}--".encode()

                resp = await client.post(
                    f"{UPLOAD_BASE}/files?uploadType=multipart",
                    content=body,
                    headers={"Content-Type": f"multipart/related; boundary={boundary}"},
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Upload failed: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"✅ Uploaded **{path.name}** to Drive. File ID: `{data.get('id')}`",
                    metadata=data,
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_create_folder
# ---------------------------------------------------------------------------

class DriveCreateFolderTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_create_folder",
            description="Create a new folder in Google Drive.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="name", type="string", description="Folder name"),
                ToolParameter(name="parent_id", type="string", description="Parent folder ID (optional, defaults to root)", required=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        name = kwargs.get("name")
        if not name:
            return ToolResult(success=False, error="Folder name is required")

        parent_id = kwargs.get("parent_id")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            body: dict[str, Any] = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                body["parents"] = [parent_id]

            async with client:
                resp = await client.post(f"{DRIVE_BASE}/files", json=body)
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to create folder: {resp.status_code}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"📁 Folder **{name}** created. ID: `{data.get('id')}`",
                    metadata=data,
                )
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_share_file
# ---------------------------------------------------------------------------

class DriveShareFileTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_share_file",
            description="Share a Google Drive file with specific people or make it publicly accessible.",
            category=ToolCategory.FILE,
            dangerous=True,
            parameters=[
                ToolParameter(name="file_id", type="string", description="The file ID to share"),
                ToolParameter(name="email", type="string", description="Email address to share with (leave empty for public link)", required=False, default=""),
                ToolParameter(name="role", type="string", description="Permission role: 'reader', 'writer', or 'commenter'", required=False, default="reader"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_id = kwargs.get("file_id")
        if not file_id:
            return ToolResult(success=False, error="file_id is required")

        email = kwargs.get("email", "")
        role = kwargs.get("role", "reader")
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            if email:
                permission = {"type": "user", "role": role, "emailAddress": email}
            else:
                permission = {"type": "anyone", "role": role}

            async with client:
                resp = await client.post(
                    f"{DRIVE_BASE}/files/{file_id}/permissions",
                    json=permission,
                )
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Share failed: {resp.status_code} — {resp.text}")

                target = email if email else "anyone (public)"
                return ToolResult(success=True, output=f"✅ Shared file with {target} as {role}.")
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_list_recent
# ---------------------------------------------------------------------------

class DriveListRecentTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_list_recent",
            description="List recently modified files in Google Drive.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="max_results", type="integer", description="Max files to return (1-50)", required=False, default=15),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        max_results = min(int(kwargs.get("max_results", 15)), 50)
        account_email = kwargs.get("account_email")

        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{DRIVE_BASE}/files",
                    params={
                        "pageSize": max_results,
                        "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink)",
                        "orderBy": "modifiedTime desc",
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Drive API error: {resp.status_code}")

                files = resp.json().get("files", [])
                if not files:
                    return ToolResult(success=True, output="No recent files found.")

                output = f"📂 **{len(files)} recently modified file(s):**\n\n"
                for i, f in enumerate(files, 1):
                    output += f"{i}. {_format_file(f)}\n\n"

                return ToolResult(success=True, output=output, metadata={"files": files})
        finally:
            await db.close()


# ---------------------------------------------------------------------------
# Tool: drive_get_file_info
# ---------------------------------------------------------------------------

class DriveGetFileInfoTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="drive_get_file_info",
            description="Get detailed metadata for a Google Drive file (size, owner, sharing, modified date).",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="file_id", type="string", description="The Drive file ID"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_id = kwargs.get("file_id")
        if not file_id:
            return ToolResult(success=False, error="file_id is required")

        account_email = kwargs.get("account_email")
        db, account, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{DRIVE_BASE}/files/{file_id}",
                    params={
                        "fields": "id,name,mimeType,size,createdTime,modifiedTime,owners,shared,webViewLink,parents,description"
                    },
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"File not found: {resp.status_code}")

                f = resp.json()
                owners = ", ".join(o.get("displayName", o.get("emailAddress", "")) for o in f.get("owners", []))
                shared = "Yes" if f.get("shared") else "No"

                output = (
                    f"📄 **{f.get('name', '(unnamed)')}**\n"
                    f"  Type: {f.get('mimeType', 'unknown')}\n"
                    f"  Size: {f.get('size', 'N/A')} bytes\n"
                    f"  Owner: {owners}\n"
                    f"  Shared: {shared}\n"
                    f"  Created: {f.get('createdTime', '')}\n"
                    f"  Modified: {f.get('modifiedTime', '')}\n"
                    f"  Link: {f.get('webViewLink', 'N/A')}\n"
                )
                if f.get("description"):
                    output += f"  Description: {f['description']}\n"

                return ToolResult(success=True, output=output, metadata=f)
        finally:
            await db.close()
