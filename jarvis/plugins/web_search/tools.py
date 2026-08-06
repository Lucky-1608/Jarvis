from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class WebSearchTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="WebSearchTool",
            description="Search the web for a query and return a summarized markdown report.",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Search query")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(success=False, error="Query is required")
            
        try:
            import os
            import httpx
            from urllib.parse import quote
            
            jina_api_key = os.getenv("JINA_API_KEY")
            
            if jina_api_key:
                encoded_query = quote(query)
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(
                        f"https://s.jina.ai/{encoded_query}",
                        headers={
                            "Authorization": f"Bearer {jina_api_key}",
                            "X-Return-Format": "markdown"
                        }
                    )
                    response.raise_for_status()
                    return ToolResult(success=True, output={"text": response.text[:10000]})
            else:
                return ToolResult(success=False, error="JINA_API_KEY is required for WebSearchTool fallback is not supported.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
