import os
import platform
import subprocess

from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.tools.registry import ToolRegistry


class ExecuteCommandTool(Tool):
    """Executes a local system command."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="execute_command",
            description="Run a shell command on the local system.",
            category=ToolCategory.SYSTEM,
            dangerous=True, # Requires user confirmation
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The shell command to execute, e.g. 'dir' or 'ls -la'."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command")
        if not command:
            return ToolResult(success=False, error="No command provided.")

        try:
            # Use shell=True to allow shell builtins and pipes
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30.0
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr}"

            return ToolResult(success=result.returncode == 0, output=output.strip() or "Command executed successfully with no output.")
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command '{command}' timed out.")
        except Exception as e:
            return ToolResult(success=False, error=f"Error executing command: {str(e)}")

class GetSystemStatsTool(Tool):
    """Gets basic system statistics."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_system_stats",
            description="Get basic system information (OS, CPU architecture, etc.).",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[]
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            stats = {
                "os": os.name,
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            }
            # Optional: if psutil is installed, we can get CPU/RAM
            try:
                import psutil
                stats["cpu_percent"] = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                stats["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
                stats["memory_used_percent"] = mem.percent
            except ImportError:
                stats["note"] = "psutil module not installed; CPU/RAM usage not available."

            return ToolResult(success=True, output=stats)
        except Exception as e:
            return ToolResult(success=False, error=f"Error getting system stats: {str(e)}")

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the system controller tools."""
    registry.register(ExecuteCommandTool())
    registry.register(GetSystemStatsTool())
