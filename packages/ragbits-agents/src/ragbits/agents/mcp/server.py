import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AsyncExitStack, suppress
from datetime import timedelta
from pathlib import Path
from types import TracebackType
from typing import Any, Literal

from typing_extensions import NotRequired, Self, TypedDict

with suppress(ImportError):
    from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
    from mcp import ClientSession, StdioServerParameters, stdio_client
    from mcp import Tool as MCPTool
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import GetSessionIdCallback, streamablehttp_client
    from mcp.shared.message import SessionMessage
    from mcp.types import CallToolResult, InitializeResult

logger = logging.getLogger(__name__)


class MCPServer(ABC):
    """
    Base class for Model Context Protocol servers.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the server. For example, this might mean spawning a subprocess or
        opening a network connection. The server is expected to remain connected until `cleanup()` is called.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        A readable name for the server.
        """

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Cleanup the server. For example, this might mean closing a subprocess or closing a network connection.
        """

    @abstractmethod
    async def list_tools(self) -> list["MCPTool"]:
        """
        List the tools available on the server.
        """

    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> "CallToolResult":
        """
        Invoke a tool on the server.
        """


class _MCPServerWithClientSession(MCPServer, ABC):
    """
    Base class for MCP servers that use a `ClientSession` to communicate with the server.
    """

    def __init__(self, cache_tools_list: bool, client_session_timeout_seconds: float | None) -> None:
        """
        Args:
            cache_tools_list: Whether to cache the tools list. If `True`, the tools list will be
                cached and only fetched from the server once. If `False`, the tools list will be
                fetched from the server on each call to `list_tools()`. The cache can be invalidated
                by calling `invalidate_tools_cache()`. You should set this to `True` if you know the
                server will not change its tools list, because it can drastically improve latency
                (by avoiding a round-trip to the server every time).
            client_session_timeout_seconds: the read timeout passed to the MCP ClientSession.
        """
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self._cleanup_lock = asyncio.Lock()
        self.cache_tools_list = cache_tools_list
        self.server_initialize_result: InitializeResult | None = None
        self.client_session_timeout_seconds = client_session_timeout_seconds

        # The cache is always dirty at startup, so that we fetch tools at least once
        self._cache_dirty = True
        self._tools_list: list[MCPTool] | None = None

    @abstractmethod
    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            "MemoryObjectReceiveStream[SessionMessage | Exception]",
            "MemoryObjectSendStream[SessionMessage]",
            "GetSessionIdCallback | None",
        ]
    ]:
        """
        Create the streams for the server.
        """

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.cleanup()

    def invalidate_tools_cache(self) -> None:
        """
        Invalidate the tools cache.
        """
        self._cache_dirty = True

    async def connect(self) -> None:
        """
        Connect to the server.
        """
        try:
            transport = await self.exit_stack.enter_async_context(self.create_streams())
            # streamablehttp_client returns (read, write, get_session_id)
            # sse_client returns (read, write)

            read, write, *_ = transport

            session = await self.exit_stack.enter_async_context(
                ClientSession(
                    read,
                    write,
                    timedelta(seconds=self.client_session_timeout_seconds)
                    if self.client_session_timeout_seconds
                    else None,
                )
            )
            server_result = await session.initialize()
            self.server_initialize_result = server_result
            self.session = session
        except Exception as e:
            logger.error(f"Error initializing MCP server: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> list["MCPTool"]:
        """
        List the tools available on the server.
        """
        if not self.session:
            raise RuntimeError("Server not initialized. Make sure you call `connect()` first.")

        # Return from cache if caching is enabled, we have tools, and the cache is not dirty
        if self.cache_tools_list and not self._cache_dirty and self._tools_list:
            return self._tools_list

        # Reset the cache dirty to False
        self._cache_dirty = False

        # Fetch the tools from the server
        self._tools_list = (await self.session.list_tools()).tools
        return self._tools_list

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> "CallToolResult":
        """
        Invoke a tool on the server.
        """
        if not self.session:
            raise RuntimeError("Server not initialized. Make sure you call `connect()` first.")

        return await self.session.call_tool(tool_name, arguments)

    async def cleanup(self) -> None:
        """
        Cleanup the server.
        """
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.error(f"Error cleaning up server: {e}")
            finally:
                self.session = None


class MCPServerStdioParams(TypedDict):
    """
    Mirrors `mcp.client.stdio.StdioServerParameters`, but lets you pass params without another import.
    """

    command: str
    """The executable to run to start the server. For example, `python` or `node`."""

    args: NotRequired[list[str]]
    """Command line args to pass to the `command` executable. For example, `['foo.py']` or
    `['server.js', '--port', '8080']`."""

    env: NotRequired[dict[str, str]]
    """The environment variables to set for the server. ."""

    cwd: NotRequired[str | Path]
    """The working directory to use when spawning the process."""

    encoding: NotRequired[str]
    """The text encoding used when sending/receiving messages to the server. Defaults to `utf-8`."""

    encoding_error_handler: NotRequired[Literal["strict", "ignore", "replace"]]
    """The text encoding error handler. Defaults to `strict`.

    See https://docs.python.org/3/library/codecs.html#codec-base-classes for
    explanations of possible values.
    """


class MCPServerStdio(_MCPServerWithClientSession):
    """
    MCP server implementation that uses the stdio transport.
    See the [spec](https://modelcontextprotocol.io/specification/2025-06-18#stdio) for details.
    """

    def __init__(
        self,
        params: MCPServerStdioParams,
        cache_tools_list: bool = False,
        name: str | None = None,
        client_session_timeout_seconds: float | None = 5,
    ) -> None:
        """
        Create a new MCP server based on the stdio transport.

        Args:
            params: The params that configure the server. This includes the command to run to
                start the server, the args to pass to the command, the environment variables to
                set for the server, the working directory to use when spawning the process, and
                the text encoding used when sending/receiving messages to the server.
            cache_tools_list: Whether to cache the tools list. If `True`, the tools list will be
                cached and only fetched from the server once. If `False`, the tools list will be
                fetched from the server on each call to `list_tools()`. The cache can be
                invalidated by calling `invalidate_tools_cache()`. You should set this to `True`
                if you know the server will not change its tools list, because it can drastically
                improve latency (by avoiding a round-trip to the server every time).
            name: A readable name for the server. If not provided, we'll create one from the
                command.
            client_session_timeout_seconds: the read timeout passed to the MCP ClientSession.
        """
        super().__init__(cache_tools_list, client_session_timeout_seconds)

        self.params = StdioServerParameters(
            command=params["command"],
            args=params.get("args", []),
            env=params.get("env"),
            cwd=params.get("cwd"),
            encoding=params.get("encoding", "utf-8"),
            encoding_error_handler=params.get("encoding_error_handler", "strict"),
        )

        self._name = name or f"stdio: {self.params.command}"

    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            "MemoryObjectReceiveStream[SessionMessage | Exception]",
            "MemoryObjectSendStream[SessionMessage]",
            "GetSessionIdCallback | None",
        ]
    ]:
        """
        Create the streams for the server.
        """
        return stdio_client(self.params)

    @property
    def name(self) -> str:
        """
        A readable name for the server.
        """
        return self._name


class MCPServerSseParams(TypedDict):
    """
    Mirrors the params in`mcp.client.sse.sse_client`.
    """

    url: str
    """The URL of the server."""

    headers: NotRequired[dict[str, str]]
    """The headers to send to the server."""

    timeout: NotRequired[float]
    """The timeout for the HTTP request. Defaults to 5 seconds."""

    sse_read_timeout: NotRequired[float]
    """The timeout for the SSE connection, in seconds. Defaults to 5 minutes."""


class MCPServerSse(_MCPServerWithClientSession):
    """
    MCP server implementation that uses the HTTP with SSE transport.
    See the [spec](https://modelcontextprotocol.io/specification/2025-06-18#http-with-sse) for details.
    """

    def __init__(
        self,
        params: MCPServerSseParams,
        cache_tools_list: bool = False,
        name: str | None = None,
        client_session_timeout_seconds: float | None = 5,
    ) -> None:
        """
        Create a new MCP server based on the HTTP with SSE transport.

        Args:
            params: The params that configure the server. This includes the URL of the server,
                the headers to send to the server, the timeout for the HTTP request, and the
                timeout for the SSE connection.
            cache_tools_list: Whether to cache the tools list. If `True`, the tools list will be
                cached and only fetched from the server once. If `False`, the tools list will be
                fetched from the server on each call to `list_tools()`. The cache can be
                invalidated by calling `invalidate_tools_cache()`. You should set this to `True`
                if you know the server will not change its tools list, because it can drastically
                improve latency (by avoiding a round-trip to the server every time).
            name: A readable name for the server. If not provided, we'll create one from the
                URL.
            client_session_timeout_seconds: the read timeout passed to the MCP ClientSession.
        """
        super().__init__(cache_tools_list, client_session_timeout_seconds)

        self.params = params
        self._name = name or f"sse: {self.params['url']}"

    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            "MemoryObjectReceiveStream[SessionMessage | Exception]",
            "MemoryObjectSendStream[SessionMessage]",
            "GetSessionIdCallback | None",
        ]
    ]:
        """
        Create the streams for the server.
        """
        return sse_client(
            url=self.params["url"],
            headers=self.params.get("headers", None),
            timeout=self.params.get("timeout", 5),
            sse_read_timeout=self.params.get("sse_read_timeout", 60 * 5),
        )

    @property
    def name(self) -> str:
        """
        A readable name for the server.
        """
        return self._name


class MCPServerStreamableHttpParams(TypedDict):
    """
    Mirrors the params in`mcp.client.streamable_http.streamablehttp_client`.
    """

    url: str
    """The URL of the server."""

    headers: NotRequired[dict[str, str]]
    """The headers to send to the server."""

    timeout: NotRequired[timedelta | float]
    """The timeout for the HTTP request. Defaults to 5 seconds."""

    sse_read_timeout: NotRequired[timedelta | float]
    """The timeout for the SSE connection, in seconds. Defaults to 5 minutes."""

    terminate_on_close: NotRequired[bool]
    """Terminate on close"""


class MCPServerStreamableHttp(_MCPServerWithClientSession):
    """
    MCP server implementation that uses the Streamable HTTP transport.
    See the [spec](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)
    for details.
    """

    def __init__(
        self,
        params: MCPServerStreamableHttpParams,
        cache_tools_list: bool = False,
        name: str | None = None,
        client_session_timeout_seconds: float | None = 5,
    ) -> None:
        """
        Create a new MCP server based on the Streamable HTTP transport.

        Args:
            params: The params that configure the server. This includes the URL of the server,
                the headers to send to the server, the timeout for the HTTP request, and the
                timeout for the Streamable HTTP connection and whether we need to
                terminate on close.
            cache_tools_list: Whether to cache the tools list. If `True`, the tools list will be
                cached and only fetched from the server once. If `False`, the tools list will be
                fetched from the server on each call to `list_tools()`. The cache can be
                invalidated by calling `invalidate_tools_cache()`. You should set this to `True`
                if you know the server will not change its tools list, because it can drastically
                improve latency (by avoiding a round-trip to the server every time).
            name: A readable name for the server. If not provided, we'll create one from the
                URL.
            client_session_timeout_seconds: the read timeout passed to the MCP ClientSession.
        """
        super().__init__(cache_tools_list, client_session_timeout_seconds)

        self.params = params
        self._name = name or f"streamable_http: {self.params['url']}"

    def create_streams(
        self,
    ) -> AbstractAsyncContextManager[
        tuple[
            "MemoryObjectReceiveStream[SessionMessage | Exception]",
            "MemoryObjectSendStream[SessionMessage]",
            "GetSessionIdCallback | None",
        ]
    ]:
        """
        Create the streams for the server.
        """
        return streamablehttp_client(
            url=self.params["url"],
            headers=self.params.get("headers", None),
            timeout=self.params.get("timeout", 5),
            sse_read_timeout=self.params.get("sse_read_timeout", 60 * 5),
            terminate_on_close=self.params.get("terminate_on_close", True),
        )

    @property
    def name(self) -> str:
        """
        A readable name for the server.
        """
        return self._name
