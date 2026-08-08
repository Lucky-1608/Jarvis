"""
Jarvis OS — Google Sheets Tools.

Provides 5 tools for Google Sheets API v4 interaction.
"""

import json
from typing import Any

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.database.core import AsyncSessionLocal

SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


class SheetsReadRangeTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sheets_read_range",
            description="Read a range of cells from a Google Spreadsheet. Returns the data as a formatted table.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="spreadsheet_id", type="string", description="The spreadsheet ID (from the URL)"),
                ToolParameter(name="range", type="string", description="Cell range in A1 notation (e.g., 'Sheet1!A1:D10', 'A1:Z100')"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        spreadsheet_id = kwargs.get("spreadsheet_id")
        cell_range = kwargs.get("range")
        if not spreadsheet_id or not cell_range:
            return ToolResult(success=False, error="'spreadsheet_id' and 'range' are required.")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(f"{SHEETS_BASE}/{spreadsheet_id}/values/{cell_range}")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Sheets API error: {resp.status_code} — {resp.text}")

                data = resp.json()
                values = data.get("values", [])
                if not values:
                    return ToolResult(success=True, output="The selected range is empty.")

                # Format as markdown table
                output = f"📊 **{data.get('range', cell_range)}** ({len(values)} rows):\n\n"
                if len(values) > 1:
                    headers = values[0]
                    output += "| " + " | ".join(str(h) for h in headers) + " |\n"
                    output += "| " + " | ".join("---" for _ in headers) + " |\n"
                    for row in values[1:]:
                        padded = row + [""] * (len(headers) - len(row))
                        output += "| " + " | ".join(str(c) for c in padded) + " |\n"
                else:
                    output += str(values[0])

                return ToolResult(success=True, output=output, metadata={"values": values})
        finally:
            await db.close()


class SheetsWriteRangeTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sheets_write_range",
            description="Write data to a range of cells in a Google Spreadsheet.",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="spreadsheet_id", type="string", description="The spreadsheet ID"),
                ToolParameter(name="range", type="string", description="Cell range in A1 notation (e.g., 'Sheet1!A1')"),
                ToolParameter(name="values", type="string", description="JSON array of arrays, e.g., '[[\"Name\",\"Age\"],[\"Alice\",30]]'"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        spreadsheet_id = kwargs.get("spreadsheet_id")
        cell_range = kwargs.get("range")
        values_str = kwargs.get("values")
        if not all([spreadsheet_id, cell_range, values_str]):
            return ToolResult(success=False, error="'spreadsheet_id', 'range', and 'values' are required.")

        try:
            values = json.loads(values_str)
        except json.JSONDecodeError:
            return ToolResult(success=False, error="'values' must be valid JSON (array of arrays).")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.put(
                    f"{SHEETS_BASE}/{spreadsheet_id}/values/{cell_range}",
                    params={"valueInputOption": "USER_ENTERED"},
                    json={"values": values},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Write failed: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(
                    success=True,
                    output=f"✅ Wrote {data.get('updatedRows', 0)} row(s) × {data.get('updatedColumns', 0)} column(s) to {cell_range}.",
                    metadata=data,
                )
        finally:
            await db.close()


class SheetsCreateTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sheets_create",
            description="Create a new Google Spreadsheet.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="title", type="string", description="Spreadsheet title"),
                ToolParameter(name="sheet_names", type="string", description="Comma-separated sheet (tab) names (optional)", required=False, default="Sheet1"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        if not title:
            return ToolResult(success=False, error="Title is required.")

        sheet_names = [s.strip() for s in kwargs.get("sheet_names", "Sheet1").split(",")]
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            body: dict[str, Any] = {
                "properties": {"title": title},
                "sheets": [{"properties": {"title": name}} for name in sheet_names],
            }

            async with client:
                resp = await client.post(SHEETS_BASE, json=body)
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Create failed: {resp.status_code}")

                data = resp.json()
                sid = data.get("spreadsheetId", "")
                url = data.get("spreadsheetUrl", "")
                return ToolResult(
                    success=True,
                    output=f"📊 Spreadsheet **{title}** created!\nID: `{sid}`\nURL: {url}",
                    metadata=data,
                )
        finally:
            await db.close()


class SheetsListSheetsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sheets_list_sheets",
            description="List all sheets (tabs) in a Google Spreadsheet.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="spreadsheet_id", type="string", description="The spreadsheet ID"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        spreadsheet_id = kwargs.get("spreadsheet_id")
        if not spreadsheet_id:
            return ToolResult(success=False, error="spreadsheet_id is required.")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{SHEETS_BASE}/{spreadsheet_id}",
                    params={"fields": "properties.title,sheets.properties"},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Sheets API error: {resp.status_code}")

                data = resp.json()
                title = data.get("properties", {}).get("title", "")
                sheets = data.get("sheets", [])

                output = f"📊 **{title}** — {len(sheets)} sheet(s):\n"
                for s in sheets:
                    props = s.get("properties", {})
                    output += f"  - {props.get('title', '?')} (ID: {props.get('sheetId', '?')}, {props.get('gridProperties', {}).get('rowCount', '?')} rows × {props.get('gridProperties', {}).get('columnCount', '?')} cols)\n"

                return ToolResult(success=True, output=output, metadata=data)
        finally:
            await db.close()


class SheetsAppendRowTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="sheets_append_row",
            description="Append a row of data to the end of a Google Spreadsheet sheet.",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="spreadsheet_id", type="string", description="The spreadsheet ID"),
                ToolParameter(name="range", type="string", description="Sheet name or range (e.g., 'Sheet1')"),
                ToolParameter(name="values", type="string", description="JSON array for the row, e.g., '[\"Alice\", 30, \"Engineer\"]'"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        spreadsheet_id = kwargs.get("spreadsheet_id")
        cell_range = kwargs.get("range")
        values_str = kwargs.get("values")
        if not all([spreadsheet_id, cell_range, values_str]):
            return ToolResult(success=False, error="'spreadsheet_id', 'range', and 'values' are required.")

        try:
            row = json.loads(values_str)
            if not isinstance(row, list):
                row = [row]
        except json.JSONDecodeError:
            return ToolResult(success=False, error="'values' must be a valid JSON array.")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.post(
                    f"{SHEETS_BASE}/{spreadsheet_id}/values/{cell_range}:append",
                    params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                    json={"values": [row]},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Append failed: {resp.status_code} — {resp.text}")

                data = resp.json()
                return ToolResult(success=True, output=f"✅ Row appended to {cell_range}.", metadata=data)
        finally:
            await db.close()
