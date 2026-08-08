from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import (
    DriveSearchFilesTool,
    DriveReadFileTool,
    DriveUploadFileTool,
    DriveCreateFolderTool,
    DriveShareFileTool,
    DriveListRecentTool,
    DriveGetFileInfoTool,
)

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register all Google Drive tools."""
    registry.register(DriveSearchFilesTool())
    registry.register(DriveReadFileTool())
    registry.register(DriveUploadFileTool())
    registry.register(DriveCreateFolderTool())
    registry.register(DriveShareFileTool())
    registry.register(DriveListRecentTool())
    registry.register(DriveGetFileInfoTool())
