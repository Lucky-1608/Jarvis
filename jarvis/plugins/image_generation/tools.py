import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class GenerateImageTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="GenerateImageTool",
            description="Generate an image using OpenAI DALL-E.",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="prompt", type="string", description="Description of the image")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="OPENAI_API_KEY environment variable not set.")
            
        prompt = kwargs.get("prompt")
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"prompt": prompt, "n": 1, "size": "1024x1024"}
            res = requests.post("https://api.openai.com/v1/images/generations", json=payload, headers=headers)
            if res.status_code == 200:
                url = res.json()["data"][0]["url"]
                return ToolResult(success=True, output={"image_url": url})
            return ToolResult(success=False, error=res.text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
