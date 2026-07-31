import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class SQLQueryTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="SQLQueryTool",
            description="Execute a SQL query against the configured database.",
            category=ToolCategory.SYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(name="query", type="string", description="The SQL query to execute."),
                ToolParameter(name="fetch", type="boolean", description="Whether to fetch results (true for SELECT).")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return ToolResult(success=False, error="DATABASE_URL environment variable is not set.")
            
        query = kwargs.get("query")
        fetch = kwargs.get("fetch", True)
        
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                if fetch and result.returns_rows:
                    rows = [dict(row._mapping) for row in result]
                    conn.commit()
                    return ToolResult(success=True, output={"rows": rows})
                conn.commit()
                return ToolResult(success=True, output={"message": "Query executed successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
