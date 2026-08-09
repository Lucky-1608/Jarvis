from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    SheetsAppendRowTool,
    SheetsCreateTool,
    SheetsListSheetsTool,
    SheetsReadRangeTool,
    SheetsWriteRangeTool,
)


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    registry.register(SheetsReadRangeTool())
    registry.register(SheetsWriteRangeTool())
    registry.register(SheetsCreateTool())
    registry.register(SheetsListSheetsTool())
    registry.register(SheetsAppendRowTool())
