import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class GitHubPRTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="GitHubPRTool",
            description="Create a pull request on GitHub.",
            category=ToolCategory.CODE,
            dangerous=True,
            parameters=[
                ToolParameter(name="repo", type="string", description="e.g., owner/repo"),
                ToolParameter(name="title", type="string", description="PR Title"),
                ToolParameter(name="head", type="string", description="Branch containing changes"),
                ToolParameter(name="base", type="string", description="Branch to merge into")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return ToolResult(success=False, error="GITHUB_TOKEN environment variable not set.")
            
        repo = kwargs.get("repo")
        try:
            import requests
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            url = f"https://api.github.com/repos/{repo}/pulls"
            payload = {
                "title": kwargs.get("title"),
                "head": kwargs.get("head"),
                "base": kwargs.get("base")
            }
            res = requests.post(url, json=payload, headers=headers)
            if res.status_code == 201:
                return ToolResult(success=True, output={"pr_url": res.json().get("html_url")})
            return ToolResult(success=False, error=res.text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GitHubReviewTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="GitHubReviewTool",
            description="Stub for GitHub PR Reviews.",
            category=ToolCategory.CODE,
            dangerous=False,
            parameters=[]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output={"message": "GitHub review functionality deferred."})
