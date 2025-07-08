import pytest

from ragbits.agents.mcp.server import _MCPServerWithClientSession


class CrashingClientSessionServer(_MCPServerWithClientSession):
    def __init__(self):
        super().__init__(cache_tools_list=False, client_session_timeout_seconds=5)
        self.cleanup_called = False

    def create_streams(self):  # noqa: PLR6301
        raise ValueError("Crash!")

    async def cleanup(self):
        self.cleanup_called = True
        await super().cleanup()

    @property
    def name(self) -> str:
        return "crashing_client_session_server"


async def test_server_errors_cause_error_and_cleanup_called():
    server = CrashingClientSessionServer()

    with pytest.raises(ValueError):
        await server.connect()

    assert server.cleanup_called


async def test_not_calling_connect_causes_error():
    server = CrashingClientSessionServer()

    with pytest.raises(RuntimeError):
        await server.list_tools()

    with pytest.raises(RuntimeError):
        await server.call_tool("foo", {})
