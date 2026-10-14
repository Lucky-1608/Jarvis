import os
import httpx
import structlog
from typing import Any

from jarvis.plugins.sdk import Plugin, PluginMetadata, PluginHealth
from jarvis.tools.base import Tool, ToolMetadata, ToolCategory, ToolParameter, ToolResult
from jarvis.events.bus import EventBus

logger = structlog.get_logger(__name__)

class VNexusApiCallTool(Tool):
    """Tool to interact with the V_Nexus API."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="v_nexus_api_call",
            description="Call the V_Nexus API to read or write tasks, notes, goals, resources, etc. Note for tasks: statuses are 'Todo', 'In Progress', and 'Done'. Pending tasks include BOTH 'Todo' and 'In Progress' (all tasks that are not 'Done').",
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="resource_type",
                    type="string",
                    description="The resource type endpoint (e.g., tasks, notes, goals, habits, finances, projects, resources, roadmaps, paths, timetable, analytics).",
                    enum=["tasks", "notes", "goals", "habits", "finances", "projects", "resources", "roadmaps", "paths", "timetable", "analytics"]
                ),
                ToolParameter(
                    name="method",
                    type="string",
                    description="The HTTP method (GET to read, POST to create, PATCH to edit, DELETE to delete).",
                    enum=["GET", "POST", "PATCH", "DELETE"]
                ),
                ToolParameter(
                    name="payload",
                    type="object",
                    description="The payload for POST/PATCH (e.g., {'title': 'Buy groceries', 'status': 'in_progress'}). For DELETE, pass {'id': '...'} or pass id in query. Omit for GET.",
                    required=False
                ),
                ToolParameter(
                    name="resource_id",
                    type="string",
                    description="Optional ID of the specific resource to fetch, update (PATCH), or delete.",
                    required=False
                )
            ]
        )

    async def execute(
        self,
        resource_type: str,
        method: str,
        payload: dict[str, Any] | None = None,
        resource_id: str | None = None,
        **kwargs: Any
    ) -> ToolResult:
        base_url = os.getenv("VNEXUS_BASE_URL", "https://v-nexus.vercel.app")
        token = os.getenv("VNEXUS_PAT")

        if not token:
            return ToolResult(
                success=False, 
                error="VNEXUS_PAT environment variable is not set. Please add it to your .env file."
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        target_id = resource_id or (payload.get("id") if isinstance(payload, dict) else None)
        url = f"{base_url}/api/v1/{resource_type}"
        if target_id and method.upper() in ["GET", "PATCH", "DELETE"]:
            url = f"{url}?id={target_id}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=payload or {})
                elif method.upper() == "PATCH":
                    response = await client.patch(url, headers=headers, json=payload or {})
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return ToolResult(success=False, error=f"Unsupported method: {method}")

                response.raise_for_status()
                data = response.json()
                return ToolResult(success=True, output=data)
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f": {error_data}"
            except Exception:
                error_msg += f": {e.response.text}"
            return ToolResult(success=False, error=error_msg)
        except Exception as e:
            logger.error("v_nexus_api_error", error=str(e), exc_info=True)
            return ToolResult(success=False, error=f"Request failed: {str(e)}")


class VNexusPlugin(Plugin):
    """Jarvis Plugin for V_Nexus Personal System integration."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="v_nexus",
            version="1.0.0",
            description="Integration with the V_Nexus personal system API via Personal Access Tokens.",
            author="Jarvis"
        )

    async def register(self, bus: EventBus) -> None:
        """Register the plugin. No event bus subscriptions needed yet."""
        logger.info("v_nexus_plugin.registered")

    def tools(self) -> list[Tool]:
        """Return the tools provided by this plugin."""
        return [VNexusApiCallTool()]

    async def health_check(self) -> PluginHealth:
        """Check if the plugin is correctly configured."""
        token = os.getenv("VNEXUS_PAT")
        if not token:
            return PluginHealth(name="v_nexus", healthy=False, message="VNEXUS_PAT environment variable not set")
        return PluginHealth(name="v_nexus", healthy=True, message="OK")

def create_plugin() -> Plugin:
    return VNexusPlugin()
