"""
Jarvis OS — Google Tasks Tools.

Provides 5 tools for Google Tasks API v1 interaction.
"""

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.database.core import AsyncSessionLocal

TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


class TasksListTasklistsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tasks_list_tasklists",
            description="List all Google Tasks task lists for the user.",
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

        try:
            async with client:
                resp = await client.get(f"{TASKS_BASE}/users/@me/lists")
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Tasks API error: {resp.status_code} - {resp.text}")

                items = resp.json().get("items", [])
                if not items:
                    return ToolResult(success=True, output="No task lists found.")

                output = "📋 **Your Task Lists:**\n\n"
                for i, item in enumerate(items, 1):
                    output += f"{i}. **{item.get('title', 'Untitled')}** (ID: `{item.get('id', '')}`)\n"

                return ToolResult(success=True, output=output, metadata={"tasklists": items})
        finally:
            await db.close()


class TasksGetTasksTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tasks_get_tasks",
            description="Get tasks from a specific Google Tasks task list.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="tasklist_id", type="string", description="The ID of the task list (use '@default' for the default list)", required=False, default="@default"),
                ToolParameter(name="show_completed", type="boolean", description="Whether to include completed tasks", required=False, default=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        tasklist_id = kwargs.get("tasklist_id", "@default")
        show_completed = kwargs.get("show_completed", False)
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                params = {"showCompleted": str(show_completed).lower(), "showHidden": "false"}
                resp = await client.get(f"{TASKS_BASE}/lists/{tasklist_id}/tasks", params=params)
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Tasks API error: {resp.status_code} - {resp.text}")

                items = resp.json().get("items", [])
                if not items:
                    return ToolResult(success=True, output="No tasks found in this list.")

                output = f"✅ **Tasks ({len(items)}):**\n\n"
                for item in items:
                    status = "[x]" if item.get("status") == "completed" else "[ ]"
                    title = item.get("title", "(No title)")
                    output += f"{status} **{title}**\n"
                    if item.get("notes"):
                        output += f"    Notes: {item.get('notes')}\n"
                    output += f"    ID: `{item.get('id', '')}`\n\n"

                return ToolResult(success=True, output=output, metadata={"tasks": items})
        finally:
            await db.close()


class TasksCreateTaskTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tasks_create_task",
            description="Create a new task in a Google Tasks list.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="title", type="string", description="Task title"),
                ToolParameter(name="notes", type="string", description="Task notes/description", required=False, default=""),
                ToolParameter(name="due", type="string", description="Due date (RFC 3339 timestamp string, e.g., '2024-12-31T00:00:00.000Z')", required=False, default=""),
                ToolParameter(name="tasklist_id", type="string", description="The ID of the task list (defaults to '@default')", required=False, default="@default"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        if not title:
            return ToolResult(success=False, error="Task title is required.")

        tasklist_id = kwargs.get("tasklist_id", "@default")
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            body = {"title": title, "notes": kwargs.get("notes", "")}
            if kwargs.get("due"):
                body["due"] = kwargs.get("due")

            async with client:
                resp = await client.post(f"{TASKS_BASE}/lists/{tasklist_id}/tasks", json=body)
                if resp.status_code not in (200, 201):
                    return ToolResult(success=False, error=f"Failed to create task: {resp.status_code} - {resp.text}")

                task = resp.json()
                return ToolResult(
                    success=True,
                    output=f"✅ Task created: **{title}** (ID: `{task.get('id', '')}`)",
                    metadata=task
                )
        finally:
            await db.close()


class TasksUpdateTaskTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tasks_update_task",
            description="Update a task (e.g., mark as completed, change title/notes).",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(name="task_id", type="string", description="The ID of the task to update"),
                ToolParameter(name="tasklist_id", type="string", description="The ID of the task list (defaults to '@default')", required=False, default="@default"),
                ToolParameter(name="title", type="string", description="New title", required=False),
                ToolParameter(name="notes", type="string", description="New notes", required=False),
                ToolParameter(name="status", type="string", description="Status ('needsAction' or 'completed')", required=False),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        task_id = kwargs.get("task_id")
        if not task_id:
            return ToolResult(success=False, error="task_id is required.")

        tasklist_id = kwargs.get("tasklist_id", "@default")
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                # First fetch the existing task because PATCH behavior in Tasks API v1
                # is better handled by getting and updating (or using PATCH directly if preferred)
                get_resp = await client.get(f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}")
                if get_resp.status_code != 200:
                    return ToolResult(success=False, error=f"Task not found: {get_resp.status_code}")

                task = get_resp.json()
                
                if "title" in kwargs:
                    task["title"] = kwargs["title"]
                if "notes" in kwargs:
                    task["notes"] = kwargs["notes"]
                if "status" in kwargs:
                    task["status"] = kwargs["status"]

                resp = await client.put(f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}", json=task)
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Failed to update task: {resp.status_code} - {resp.text}")

                updated = resp.json()
                return ToolResult(
                    success=True,
                    output=f"✅ Task updated: **{updated.get('title', '')}** (Status: {updated.get('status', '')})",
                    metadata=updated
                )
        finally:
            await db.close()


class TasksDeleteTaskTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="tasks_delete_task",
            description="Delete a task from Google Tasks.",
            category=ToolCategory.CUSTOM,
            dangerous=True,
            parameters=[
                ToolParameter(name="task_id", type="string", description="The ID of the task to delete"),
                ToolParameter(name="tasklist_id", type="string", description="The ID of the task list (defaults to '@default')", required=False, default="@default"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        task_id = kwargs.get("task_id")
        if not task_id:
            return ToolResult(success=False, error="task_id is required.")

        tasklist_id = kwargs.get("tasklist_id", "@default")
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.delete(f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}")
                if resp.status_code not in (200, 204):
                    return ToolResult(success=False, error=f"Failed to delete task: {resp.status_code} - {resp.text}")

                return ToolResult(success=True, output=f"🗑️ Task {task_id} successfully deleted.")
        finally:
            await db.close()
