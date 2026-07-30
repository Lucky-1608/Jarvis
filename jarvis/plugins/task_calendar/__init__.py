import json
import os
from pathlib import Path
from datetime import datetime
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus

# Data file for tasks
TASKS_FILE = Path("data/tasks.json")

def load_tasks() -> list:
    if not TASKS_FILE.exists():
        return []
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_tasks(tasks: list) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=2)

class AddTaskTool(Tool):
    """Adds a new task to the local to-do list."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="add_task",
            description="Add a new task to your local to-do list.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="The description of the task."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        if not title:
            return ToolResult(success=False, error="Task title is required.")

        try:
            tasks = load_tasks()
            new_task = {
                "id": len(tasks) + 1,
                "title": title,
                "completed": False,
                "created_at": datetime.now().isoformat()
            }
            tasks.append(new_task)
            save_tasks(tasks)
            return ToolResult(success=True, output=f"Added task #{new_task['id']}: {title}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to add task: {str(e)}")

class ListTasksTool(Tool):
    """Lists all tasks."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_tasks",
            description="List all tasks in your local to-do list.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[]
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            tasks = load_tasks()
            if not tasks:
                return ToolResult(success=True, output="Your to-do list is empty.")
            
            output = "To-Do List:\n"
            for t in tasks:
                status = "[x]" if t.get("completed") else "[ ]"
                output += f"{status} {t['id']}. {t['title']}\n"
            return ToolResult(success=True, output=output.strip())
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list tasks: {str(e)}")

class CompleteTaskTool(Tool):
    """Marks a task as complete."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="complete_task",
            description="Mark a task as completed.",
            category=ToolCategory.CUSTOM,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="task_id",
                    type="integer", # Changed to integer type
                    description="The ID of the task to mark as complete."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        task_id = kwargs.get("task_id")
        if task_id is None:
            return ToolResult(success=False, error="Task ID is required.")

        try:
            task_id = int(task_id)
            tasks = load_tasks()
            found = False
            for t in tasks:
                if t["id"] == task_id:
                    t["completed"] = True
                    found = True
                    break
            
            if found:
                save_tasks(tasks)
                return ToolResult(success=True, output=f"Marked task #{task_id} as complete.")
            else:
                return ToolResult(success=False, error=f"Task #{task_id} not found.")
        except ValueError:
            return ToolResult(success=False, error="Task ID must be an integer.")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to complete task: {str(e)}")

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the task calendar tools."""
    registry.register(AddTaskTool())
    registry.register(ListTasksTool())
    registry.register(CompleteTaskTool())
