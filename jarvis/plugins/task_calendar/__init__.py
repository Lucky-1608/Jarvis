from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from .tools import (
    TasksListTasklistsTool,
    TasksGetTasksTool,
    TasksCreateTaskTool,
    TasksUpdateTaskTool,
    TasksDeleteTaskTool,
)

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register Google Tasks tools."""
    registry.register(TasksListTasklistsTool())
    registry.register(TasksGetTasksTool())
    registry.register(TasksCreateTaskTool())
    registry.register(TasksUpdateTaskTool())
    registry.register(TasksDeleteTaskTool())
