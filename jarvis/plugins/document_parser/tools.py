import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class DocumentParserTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="DocumentParserTool",
            description="Extract text from local PDF or CSV files.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(name="file_path", type="string", description="Absolute path to file")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("file_path")
        if not path or not os.path.exists(path):
            return ToolResult(success=False, error=f"File not found: {path}")
            
        try:
            if path.endswith(".csv"):
                import csv
                with open(path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    data = [row for row in reader]
                return ToolResult(success=True, output={"csv_rows": data[:10]})
            elif path.endswith(".txt"):
                with open(path, "r", encoding="utf-8") as f:
                    return ToolResult(success=True, output={"text": f.read(1000)})
            else:
                return ToolResult(success=False, error="Unsupported file type.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
