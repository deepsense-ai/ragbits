from mcp.types import Tool as MCPTool
from pydantic import BaseModel

from ragbits.agents.mcp.server import MCPServer
from ragbits.agents.mcp.utils import call_mcp_tool, get_all_tools
from ragbits.agents.tool import Tool

from .helpers import FakeMCPServer


class Foo(BaseModel):
    bar: str
    baz: int


class Bar(BaseModel):
    qux: dict[str, str]


async def test_get_all_function_tools():
    names = ["test_tool_1", "test_tool_2", "test_tool_3", "test_tool_4", "test_tool_5"]
    schemas = [
        {},
        {},
        {},
        Foo.model_json_schema(),
        Bar.model_json_schema(),
    ]

    server1 = FakeMCPServer()
    server1.add_tool(names[0], schemas[0])
    server1.add_tool(names[1], schemas[1])

    server2 = FakeMCPServer()
    server2.add_tool(names[2], schemas[2])
    server2.add_tool(names[3], schemas[3])

    server3 = FakeMCPServer()
    server3.add_tool(names[4], schemas[4])

    servers: list[MCPServer] = [server1, server2, server3]
    tools = await get_all_tools(servers)
    assert len(tools) == 5
    assert all(tool.name in names for tool in tools)

    for idx, tool in enumerate(tools):
        assert isinstance(tool, Tool)
        if schemas[idx] == {}:
            assert tool.parameters == {"properties": {}}
        else:
            assert tool.parameters == schemas[idx]
        assert tool.name == names[idx]

    # Also make sure it works with strict schemas
    tools = await get_all_tools(servers)
    assert len(tools) == 5
    assert all(tool.name in names for tool in tools)


async def test_call_mcp_tool():
    server = FakeMCPServer()
    server.add_tool("test_tool_1", {})

    tool = MCPTool(name="test_tool_1", inputSchema={})

    await call_mcp_tool(server, tool)
    # Just making sure it doesn't crash


async def test_util_adds_properties():
    schema = {
        "type": "object",
        "description": "Test tool",
    }

    server = FakeMCPServer()
    server.add_tool("test_tool", schema)

    tools = await get_all_tools([server])
    tool = next(tool for tool in tools if tool.name == "test_tool")

    assert isinstance(tool, Tool)
    assert "properties" in tool.parameters
    assert tool.parameters["properties"] == {}

    assert tool.parameters == {"type": "object", "description": "Test tool", "properties": {}}
