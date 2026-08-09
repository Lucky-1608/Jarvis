from jarvis.events.bus import EventBus
from jarvis.tools.registry import ToolRegistry

from .tools import (
    TasksCreateTaskTool,
    TasksDeleteTaskTool,
    TasksGetTasksTool,
    TasksListTasklistsTool,
    TasksUpdateTaskTool,
)


def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register Google Tasks tools."""
    registry.register(TasksListTasklistsTool())
    registry.register(TasksGetTasksTool())
    registry.register(TasksCreateTaskTool())
    registry.register(TasksUpdateTaskTool())
    registry.register(TasksDeleteTaskTool())
