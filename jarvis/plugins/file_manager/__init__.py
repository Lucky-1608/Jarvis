import os
from pathlib import Path

from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.tools.registry import ToolRegistry


class ReadFileTool(Tool):
    """Reads the contents of a local file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read the text content of a local file.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="The absolute path to the file."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        if not file_path:
            return ToolResult(success=False, error="No file path provided.")

        try:
            path = Path(file_path)
            if not path.is_file():
                return ToolResult(success=False, error=f"File not found: {file_path}")

            with open(path, encoding='utf-8') as f:
                content = f.read()

            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, error=f"Error reading file: {str(e)}")

class WriteFileTool(Tool):
    """Writes text content to a local file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write text content to a local file. Overwrites if it exists.",
            category=ToolCategory.FILE,
            dangerous=True, # Modifying files could be destructive
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="The absolute path to the file to create or overwrite."
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="The text content to write."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content", "")
        if not file_path:
            return ToolResult(success=False, error="No file path provided.")

        try:
            path = Path(file_path)
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ToolResult(success=True, output=f"Successfully wrote {len(content)} characters to {file_path}")
        except Exception as e:
            return ToolResult(success=False, error=f"Error writing file: {str(e)}")

class ListDirectoryTool(Tool):
    """Lists files and folders in a local directory."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_directory",
            description="List the contents of a local directory.",
            category=ToolCategory.FILE,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="dir_path",
                    type="string",
                    description="The absolute path to the directory."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        dir_path = kwargs.get("dir_path")
        if not dir_path:
            return ToolResult(success=False, error="No directory path provided.")

        try:
            path = Path(dir_path)
            if not path.is_dir():
                return ToolResult(success=False, error=f"Directory not found: {dir_path}")

            contents = []
            for item in path.iterdir():
                contents.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else 0
                })

            return ToolResult(success=True, output=contents)
        except Exception as e:
            return ToolResult(success=False, error=f"Error listing directory: {str(e)}")

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the file manager tools."""
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())
