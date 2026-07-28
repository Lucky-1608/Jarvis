import json
import os
import httpx
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
import structlog

logger = structlog.get_logger(__name__)

class N8nTool(Tool):
    """
    Tool to manage n8n workflows via the n8n REST API.
    Supports listing, creating, reading, and updating workflows.
    """

    def __init__(self, base_url: str = "http://localhost:5678/api/v1"):
        self.base_url = base_url
        self.api_key = os.environ.get("N8N_API_KEY")

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="n8n_workflows",
            description="Manage n8n workflows. Use this tool to list, create, get, or update workflows in the local n8n instance.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="The action to perform: 'list', 'get', 'create', or 'update'.",
                    enum=["list", "get", "create", "update"]
                ),
                ToolParameter(
                    name="workflow_id",
                    type="string",
                    description="The ID of the workflow (required for 'get' and 'update').",
                    required=False
                ),
                ToolParameter(
                    name="payload",
                    type="string",
                    description="JSON string representing the workflow configuration (name, nodes, connections). Required for 'create' and 'update'.",
                    required=False
                )
            ]
        )

    def _get_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    async def execute(self, **params: Any) -> ToolResult:
        action = params.get("action")
        workflow_id = params.get("workflow_id")
        payload_str = params.get("payload")

        if not action:
            return ToolResult(success=False, error="Missing required parameter 'action'.")

        payload = None
        if payload_str:
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                return ToolResult(success=False, error=f"Invalid JSON payload: {str(e)}")

        async with httpx.AsyncClient() as client:
            try:
                if action == "list":
                    res = await client.get(f"{self.base_url}/workflows", headers=self._get_headers())
                    res.raise_for_status()
                    return ToolResult(success=True, output=res.json())

                elif action == "get":
                    if not workflow_id:
                        return ToolResult(success=False, error="'workflow_id' is required for 'get' action.")
                    res = await client.get(f"{self.base_url}/workflows/{workflow_id}", headers=self._get_headers())
                    res.raise_for_status()
                    return ToolResult(success=True, output=res.json())

                elif action == "create":
                    if not payload:
                        return ToolResult(success=False, error="'payload' is required for 'create' action.")
                    res = await client.post(f"{self.base_url}/workflows", headers=self._get_headers(), json=payload)
                    res.raise_for_status()
                    return ToolResult(success=True, output=res.json())

                elif action == "update":
                    if not workflow_id or not payload:
                        return ToolResult(success=False, error="'workflow_id' and 'payload' are required for 'update' action.")
                    res = await client.put(f"{self.base_url}/workflows/{workflow_id}", headers=self._get_headers(), json=payload)
                    res.raise_for_status()
                    return ToolResult(success=True, output=res.json())

                else:
                    return ToolResult(success=False, error=f"Unknown action '{action}'.")

            except httpx.HTTPStatusError as e:
                return ToolResult(success=False, error=f"API Error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                return ToolResult(success=False, error=f"Request failed: {str(e)}")

def get_n8n_tools() -> list[Tool]:
    """Return all n8n tools."""
    return [N8nTool()]
