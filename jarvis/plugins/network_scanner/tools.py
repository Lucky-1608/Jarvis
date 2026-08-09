import socket

from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult


class NetworkScannerTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="NetworkScannerTool",
            description="Scan a host for open ports.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(name="host", type="string", description="IP address or hostname"),
                ToolParameter(name="ports", type="string", description="List of ports to scan")
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        host = kwargs.get("host")
        ports = kwargs.get("ports", [22, 80, 443, 8080])

        open_ports = []
        try:
            for port in ports:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex((host, port)) == 0:
                        open_ports.append(port)
            return ToolResult(success=True, output={"host": host, "open_ports": open_ports})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
