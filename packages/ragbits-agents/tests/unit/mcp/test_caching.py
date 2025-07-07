from unittest.mock import AsyncMock, patch

from mcp.types import ListToolsResult
from mcp.types import Tool as MCPTool

from ragbits.agents.mcp.server import MCPServerStdio

from .helpers import DummyStreamsContextManager, tee


@patch("mcp.client.stdio.stdio_client", return_value=DummyStreamsContextManager())
@patch("mcp.client.session.ClientSession.initialize", new_callable=AsyncMock, return_value=None)
@patch("mcp.client.session.ClientSession.list_tools")
async def test_server_caching_works(
    mock_list_tools: AsyncMock, mock_initialize: AsyncMock, mock_stdio_client: AsyncMock
):
    """Test that if we turn caching on, the list of tools is cached and not fetched from the server
    on each call to `list_tools()`.
    """
    server = MCPServerStdio(
        params={
            "command": tee,
        },
        cache_tools_list=True,
    )

    tools = [
        MCPTool(name="tool1", inputSchema={}),
        MCPTool(name="tool2", inputSchema={}),
    ]

    mock_list_tools.return_value = ListToolsResult(tools=tools)

    async with server:
        # Call list_tools() multiple times
        assert tools == await server.list_tools()

        assert mock_list_tools.call_count == 1, "list_tools() should have been called once"

        # Call list_tools() again, should return the cached value
        assert tools == await server.list_tools()

        assert mock_list_tools.call_count == 1, "list_tools() should not have been called again"

        # Invalidate the cache and call list_tools() again
        server.invalidate_tools_cache()
        assert tools == await server.list_tools()

        assert mock_list_tools.call_count == 2, "list_tools() should be called again"

        # Without invalidating the cache, calling list_tools() again should return the cached value
        assert tools == await server.list_tools()
