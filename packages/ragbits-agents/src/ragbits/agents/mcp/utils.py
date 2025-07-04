from contextlib import suppress
from functools import partial
from typing import Any

from ragbits.agents.mcp.server import MCPServer
from ragbits.agents.tool import Tool

with suppress(ImportError):
    from mcp import Tool as MCPTool
    from mcp.types import CallToolResult


async def get_tools(server: MCPServer) -> list[Tool]:
    """
    Get all function tools from a single MCP server.

    Args:
        server: The MCP server to retrieve tools from.

    Returns:
        List of Tool instances from the server.
    """
    tools = await server.list_tools()
    return [
        Tool(
            name=tool.name,
            description=tool.description,
            # MCP spec doesn't require the inputSchema to have `properties`, but OpenAI spec does.
            parameters={**tool.inputSchema, "properties": tool.inputSchema.get("properties", {})},
            on_tool_call=partial(call_mcp_tool, server, tool),
        )
        for tool in tools
    ]


async def call_mcp_tool(server: MCPServer, tool: "MCPTool", **arguments: Any) -> "CallToolResult":  # noqa: ANN401
    """
    Call an MCP tool.

    Args:
        server: The MCP server containing the tool.
        tool: The MCP tool to call.
        **arguments: Keyword arguments to pass to the tool.

    Returns:
        The result of the tool execution.
    """
    return await server.call_tool(tool.name, arguments)
