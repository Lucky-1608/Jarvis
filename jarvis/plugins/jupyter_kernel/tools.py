from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class JupyterExecutionTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="JupyterExecutionTool",
            description="Execute python code in a local environment.",
            category=ToolCategory.CODE,
            dangerous=True,
            parameters=[
                ToolParameter(name="code", type="string", description="Python code to run")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        code = kwargs.get("code")
        try:
            import io, sys, contextlib
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(code, globals())
            return ToolResult(success=True, output={"stdout": output.getvalue()})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
