"""
Jarvis OS — Built-in System Tools.

Core tools for interacting with the operating system:
  - open_app:      Launch an application
  - run_command:   Execute a shell command
  - system_info:   Get CPU, RAM, disk info
  - list_files:    List directory contents
  - read_file:     Read a file
  - write_file:    Write/create a file
  - search_files:  Search for files by name
  - get_datetime:  Get current date/time
"""

from __future__ import annotations

import asyncio
import datetime
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import psutil
import structlog

from jarvis.tools.base import (
    Tool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------
class SystemInfoTool(Tool):
    """Retrieve system information (CPU, RAM, disk, OS)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="system_info",
            description="Get current system information including CPU, RAM, disk usage, and OS details.",
            category=ToolCategory.SYSTEM,
        )

    async def execute(self, **params: Any) -> ToolResult:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu": {
                    "cores_physical": psutil.cpu_count(logical=False),
                    "cores_logical": psutil.cpu_count(logical=True),
                    "usage_percent": cpu_percent,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.percent, 1),
                },
                "uptime_hours": round((
                    datetime.datetime.now().timestamp() - psutil.boot_time()
                ) / 3600, 1),
            }
            return ToolResult(success=True, output=info)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Open Application
# ---------------------------------------------------------------------------
class OpenAppTool(Tool):
    """Launch a desktop application."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="open_app",
            description="Open/launch a desktop application by name, optionally navigating to a URL if it is a browser.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    description="Name of the application to open (e.g., 'chrome', 'firefox', 'brave', 'edge'). If no app is specified but you want to open a website, set this to the URL.",
                ),
                ToolParameter(
                    name="target_url",
                    type="string",
                    description="(Optional) The URL to open within the application, if the app is a web browser.",
                ),
            ],
        )

    # Common app name → command mappings (Windows)
    _APP_MAP_WINDOWS = {
        "chrome": "start chrome",
        "google chrome": "start chrome",
        "firefox": "start firefox",
        "edge": "start msedge",
        "microsoft edge": "start msedge",
        "brave": "start brave",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "cmd",
        "terminal": "wt",
        "windows terminal": "wt",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "task manager": "taskmgr",
        "paint": "mspaint",
        "word": "start winword",
        "excel": "start excel",
        "powerpoint": "start powerpnt",
        "spotify": "start spotify",
    }

    async def execute(self, **params: Any) -> ToolResult:
        app_name = params.get("app_name", "").strip().lower()
        target_url = params.get("target_url", "").strip()
        
        if not app_name:
            return ToolResult(success=False, error="No application name provided.")

        try:
            if platform.system() == "Windows":
                # Handle URLs provided directly in app_name
                if "." in app_name and " " not in app_name and not app_name.startswith("http"):
                    app_name = f"https://{app_name}"
                    
                cmd = self._APP_MAP_WINDOWS.get(app_name, f"start {app_name}")
                if target_url:
                    cmd = f"{cmd} {target_url}"
                    
                subprocess.Popen(cmd, shell=True)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:  # Linux
                subprocess.Popen(f"{app_name} &", shell=True)

            return ToolResult(
                success=True,
                output=f"Launched '{app_name}' successfully.",
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to open '{app_name}': {exc}")


# ---------------------------------------------------------------------------
# Run Command
# ---------------------------------------------------------------------------
class RunCommandTool(Tool):
    """Execute a shell command."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="run_command",
            description="Execute a shell/terminal command and return the output. Use with caution.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The shell command to execute.",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory for the command.",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds (default: 30).",
                    required=False,
                    default=30,
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        command = params.get("command", "").strip()
        cwd = params.get("cwd")
        timeout = params.get("timeout", 30)

        if not command:
            return ToolResult(success=False, error="No command provided.")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output = {
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
            }

            return ToolResult(
                success=proc.returncode == 0,
                output=output,
                error=output["stderr"] if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s.")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# List Files
# ---------------------------------------------------------------------------
class ListFilesTool(Tool):
    """List contents of a directory."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_files",
            description="List files and directories in a given path.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path to list.",
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Whether to list recursively.",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", ".").strip()
        recursive = params.get("recursive", False)

        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"Path does not exist: {path}")
        if not path.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        try:
            entries = []
            iterator = path.rglob("*") if recursive else path.iterdir()
            for item in iterator:
                try:
                    stat = item.stat()
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else None,
                    })
                except PermissionError:
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "unknown",
                        "error": "permission denied",
                    })
                if len(entries) >= 500:  # safety limit
                    break

            return ToolResult(
                success=True,
                output={"path": str(path), "count": len(entries), "entries": entries},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Read File
# ---------------------------------------------------------------------------
class ReadFileTool(Tool):
    """Read the contents of a text file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read and return the contents of a text file.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read.",
                ),
                ToolParameter(
                    name="max_lines",
                    type="integer",
                    description="Maximum number of lines to read (default: 200).",
                    required=False,
                    default=200,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", "").strip()
        max_lines = params.get("max_lines", 200)

        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not path.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)

            content = "".join(lines)
            return ToolResult(
                success=True,
                output={
                    "path": str(path),
                    "lines": len(lines),
                    "truncated": len(lines) >= max_lines,
                    "content": content,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Write File
# ---------------------------------------------------------------------------
class WriteFileTool(Tool):
    """Write content to a file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write or create a file with the given content.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write.",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file.",
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", "").strip()
        content = params.get("content", "")

        path = Path(path_str).expanduser().resolve()

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Written {len(content)} chars to {path}",
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Search Files
# ---------------------------------------------------------------------------
class SearchFilesTool(Tool):
    """Search for files by name pattern."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_files",
            description="Search for files matching a name pattern in a directory.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Directory to search in.",
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to match (e.g., '*.py', '*.txt').",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        directory = params.get("directory", ".").strip()
        pattern = params.get("pattern", "*").strip()

        path = Path(directory).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")

        try:
            matches = []
            for item in path.rglob(pattern):
                matches.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                })
                if len(matches) >= 200:
                    break

            return ToolResult(
                success=True,
                output={"pattern": pattern, "directory": str(path), "count": len(matches), "matches": matches},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Get Date/Time
# ---------------------------------------------------------------------------
class GetDateTimeTool(Tool):
    """Get current date and time."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_datetime",
            description="Get the current date, time, and timezone.",
            category=ToolCategory.SYSTEM,
        )

    async def execute(self, **params: Any) -> ToolResult:
        now = datetime.datetime.now()
        utc = datetime.datetime.now(datetime.timezone.utc)
        return ToolResult(
            success=True,
            output={
                "local": now.isoformat(),
                "utc": utc.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day": now.strftime("%A"),
                "timezone": str(datetime.datetime.now().astimezone().tzinfo),
            },
        )


# ---------------------------------------------------------------------------
# Factory — register all built-in system tools
# ---------------------------------------------------------------------------
def get_system_tools() -> list[Tool]:
    """Return instances of all built-in system tools."""
    return [
        SystemInfoTool(),
        OpenAppTool(),
        RunCommandTool(),
        ListFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        SearchFilesTool(),
        GetDateTimeTool(),
    ]
