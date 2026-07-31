import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class SmartHomeTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SmartHomeTool",
            description="Trigger smart home actions via HomeAssistant.",
            category=ToolCategory.SYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(name="entity_id", type="string", description="Entity ID"),
                ToolParameter(name="action", type="string", description="Action to perform")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        url = os.getenv("HOMEASSISTANT_URL")
        token = os.getenv("HOMEASSISTANT_TOKEN")
        if not url or not token:
            return ToolResult(success=False, error="HOMEASSISTANT_URL and HOMEASSISTANT_TOKEN environment variables required.")
            
        entity_id = kwargs.get("entity_id")
        action = kwargs.get("action")
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            domain = entity_id.split('.')[0]
            endpoint = f"{url}/api/services/{domain}/{action}"
            res = requests.post(endpoint, headers=headers, json={"entity_id": entity_id})
            if res.status_code == 200:
                return ToolResult(success=True, output={"message": f"Successfully called {action} on {entity_id}"})
            return ToolResult(success=False, error=res.text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
