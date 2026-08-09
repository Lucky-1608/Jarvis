import subprocess

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class DockerRunTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="DockerRunTool",
            description="Run a docker container.",
            category=ToolCategory.SYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(name="image", type="string", description="Docker image name"),
                ToolParameter(name="command", type="string", description="Command to run")
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        image = kwargs.get("image")
        command = kwargs.get("command", "")

        try:
            cmd = ["docker", "run", "--rm", image]
            if command:
                cmd.extend(command.split())
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ToolResult(success=True, output={"stdout": res.stdout})
        except subprocess.CalledProcessError as e:
            return ToolResult(success=False, error=e.stderr)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class DockerBuildTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="DockerBuildTool",
            description="Build a docker image.",
            category=ToolCategory.SYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(name="tag", type="string", description="Tag for the new image"),
                ToolParameter(name="path", type="string", description="Path to Dockerfile")
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        tag = kwargs.get("tag")
        path = kwargs.get("path", ".")

        try:
            cmd = ["docker", "build", "-t", tag, path]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ToolResult(success=True, output={"stdout": res.stdout})
        except subprocess.CalledProcessError as e:
            return ToolResult(success=False, error=e.stderr)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
