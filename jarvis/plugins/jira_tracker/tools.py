import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class JiraBoardTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="JiraBoardTool",
            description="Fetch issues from a Jira board.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(name="jql", type="string", description="Jira Query Language string.")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        url = os.getenv("JIRA_URL")
        email = os.getenv("JIRA_EMAIL")
        token = os.getenv("JIRA_API_TOKEN")
        
        if not url or not email or not token:
            return ToolResult(success=False, error="JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables required.")
            
        jql = kwargs.get("jql")
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(email, token)
            headers = {"Accept": "application/json"}
            endpoint = f"{url}/rest/api/3/search"
            res = requests.get(endpoint, headers=headers, auth=auth, params={"jql": jql})
            if res.status_code == 200:
                issues = [{"key": i["key"], "summary": i["fields"]["summary"]} for i in res.json().get("issues", [])]
                return ToolResult(success=True, output={"issues": issues})
            return ToolResult(success=False, error=res.text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
