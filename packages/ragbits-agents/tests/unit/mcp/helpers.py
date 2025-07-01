import json
import shutil
from types import TracebackType
from typing import Any

from mcp import Tool as MCPTool
from mcp.types import CallToolResult, TextContent

from ragbits.agents.mcp.server import MCPServer

tee = shutil.which("tee") or ""
assert tee, "tee not found"


# Added dummy stream classes for patching stdio_client to avoid real I/O during tests
class DummyStream:
    async def send(self, msg: str) -> None: ...

    @staticmethod
    async def receive() -> str:
        raise Exception("Dummy receive not implemented")


class DummyStreamsContextManager:
    async def __aenter__(self) -> tuple[DummyStream, DummyStream]:
        return (DummyStream(), DummyStream())

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class FakeMCPServer(MCPServer):
    def __init__(self, tools: list[MCPTool] | None = None):
        self.tools: list[MCPTool] = tools or []
        self.tool_calls: list[str] = []
        self.tool_results: list[str] = []

    def add_tool(self, name: str, input_schema: dict[str, Any]):
        self.tools.append(MCPTool(name=name, inputSchema=input_schema))

    async def connect(self) -> None: ...

    async def cleanup(self) -> None: ...

    async def list_tools(self) -> list[MCPTool]:
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        self.tool_calls.append(tool_name)
        self.tool_results.append(f"result_{tool_name}_{json.dumps(arguments)}")
        return CallToolResult(
            content=[TextContent(text=self.tool_results[-1], type="text")],
        )

    @property
    def name(self) -> str:
        return "fake_mcp_server"
