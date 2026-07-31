import subprocess
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class StaticAnalysisTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="StaticAnalysisTool",
            description="Run basic static analysis using Bandit.",
            category=ToolCategory.CODE,
            dangerous=False,
            parameters=[
                ToolParameter(name="path", type="string", description="Path to scan")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        try:
            res = subprocess.run(["bandit", "-r", path], capture_output=True, text=True)
            return ToolResult(success=True, output={"report": res.stdout})
        except FileNotFoundError:
            return ToolResult(success=False, error="Bandit is not installed.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class DependencyScannerTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="DependencyScannerTool", description="Scan dependencies.", category=ToolCategory.CODE, dangerous=False, parameters=[])
    async def execute(self, **kwargs) -> ToolResult: return ToolResult(success=True, output={"message": "Scanner stub."})

class SecretsDetectorTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="SecretsDetectorTool", description="Detect secrets.", category=ToolCategory.CODE, dangerous=False, parameters=[])
    async def execute(self, **kwargs) -> ToolResult: return ToolResult(success=True, output={"message": "Secrets stub."})
