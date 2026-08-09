from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    DriveCreateFolderTool,
    DriveGetFileInfoTool,
    DriveListRecentTool,
    DriveReadFileTool,
    DriveSearchFilesTool,
    DriveShareFileTool,
    DriveUploadFileTool,
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
