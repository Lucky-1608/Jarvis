from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class WebScraperTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="WebScraperTool",
            description="Scrape basic text from a webpage.",
            category=ToolCategory.RESEARCH,
            dangerous=False,
            parameters=[
                ToolParameter(name="url", type="string", description="URL to scrape")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        try:
            import os
            import httpx
            
            jina_api_key = os.getenv("JINA_API_KEY")
            
            # If Jina API is enabled, use the Reader API for clean markdown
            if jina_api_key:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(
                        f"https://r.jina.ai/{url}",
                        headers={
                            "Authorization": f"Bearer {jina_api_key}",
                            "X-Return-Format": "markdown"
                        }
                    )
                    response.raise_for_status()
                    return ToolResult(success=True, output={"text": response.text[:10000]})
            
            # Fallback to simple HTML parsing
            import urllib.request
            from html.parser import HTMLParser
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                def handle_data(self, data):
                    if data.strip():
                        self.text.append(data.strip())
                        
            parser = TextExtractor()
            parser.feed(html)
            return ToolResult(success=True, output={"text": " ".join(parser.text)[:2000]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
