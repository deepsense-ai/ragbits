import asyncio
import json
from functools import partial
from typing import Any

import httpx
import pytest

from ragbits.agents import Agent
from ragbits.agents.exceptions import AgentToolExecutionError
from ragbits.agents.hooks import EventType, Hook, PreToolCallback
from ragbits.agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams, MCPServerWebSearch
from ragbits.agents.mcp import server as server_module
from ragbits.core.llms.mock import MockLLM, MockLLMOptions


@pytest.fixture
def http_mcp(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Use the real MCP protocol client with a deterministic HTTP peer."""
    state: dict[str, Any] = {"requests": [], "calls": [], "error": None, "started": asyncio.Event()}

    async def handle(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        message = json.loads(request.content)
        method = message["method"]
        if "id" not in message:
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": message["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "search-test-peer", "version": "1"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": name,
                        "description": name,
                        "inputSchema": {"type": "object", "properties": properties},
                    }
                    for name, properties in [
                        ("web_search", {"objective": {"type": "string"}, "search_queries": {"type": "array"}}),
                        ("web_fetch", {"urls": {"type": "array", "items": {"type": "string"}}}),
                    ]
                ]
            }
        else:
            assert method == "tools/call"
            state["calls"].append(message["params"])
            state["started"].set()
            if state["error"] == "wait":
                await asyncio.Event().wait()
            if state["error"] == "protocol":
                return httpx.Response(
                    200,
                    json={"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32602, "message": "bad query"}},
                )
            result = {
                "content": [{"type": "text", "text": "Ragbits release notes https://github.com/deepsense-ai/ragbits"}],
                "isError": state["error"] == "tool",
            }
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(
        server_module,
        "streamablehttp_client",
        partial(server_module.streamablehttp_client, httpx_client_factory=client_factory),
    )
    return state


def search_llm(name: str = "web_search", arguments: dict[str, Any] | None = None) -> MockLLM:
    """Script a tool request and a final answer after the tool result."""
    return MockLLM(
        default_options=MockLLMOptions(
            response="Answer with sources",
            tool_calls=[
                {
                    "name": name,
                    "arguments": json.dumps(
                        arguments or {"objective": "Ragbits release", "search_queries": ["Ragbits"]}
                    ),
                    "id": "search-1",
                    "type": "function",
                }
            ],
        )
    )


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("web_search", {"objective": "Ragbits release", "search_queries": ["Ragbits"]}),
        ("web_fetch", {"urls": ["https://github.com/deepsense-ai/ragbits"]}),
    ],
)
async def test_unconfigured_search_through_agent(
    http_mcp: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    streaming: bool,
    tool_name: str,
    arguments: dict[str, Any],
):
    for key in ("PARALLEL_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    llm = search_llm(tool_name, arguments)
    async with MCPServerWebSearch() as server:
        agent = Agent(llm=llm, mcp_servers=[server])
        if streaming:
            result = agent.run_streaming("Find release notes")
            async for _ in result:
                pass
        else:
            result = await agent.run("Find release notes")
        assert result.content == "Answer with sources"
        assert result.tool_calls
        assert "https://github.com/deepsense-ai/ragbits" in str(result.tool_calls[0].result)
        assert any(message["role"] == "tool" and "release notes" in message["content"] for message in llm.calls[-1])
    assert server.session is None
    assert http_mcp["calls"][0]["name"] == tool_name
    assert http_mcp["calls"][0]["arguments"] == arguments
    assert "session_id" not in http_mcp["calls"][0]["arguments"]
    assert {json.loads(r.content)["method"] for r in http_mcp["requests"]} >= {"tools/list", "tools/call"}
    for request in http_mcp["requests"]:
        assert str(request.url) == "https://search.parallel.ai/mcp"
        assert request.headers["user-agent"] == "ragbits-agents"
        assert "authorization" not in request.headers


async def test_fetch_and_custom_configuration_are_preserved(http_mcp: dict[str, Any]):
    params: MCPServerStreamableHttpParams = {
        "url": "https://search.example.test/mcp?mode=fast",
        "headers": {"Authorization": "Bearer explicit-test-key", "user-agent": "my-ragbits-app"},
        "timeout": 17,
        "sse_read_timeout": 45,
        "terminate_on_close": False,
    }
    async with MCPServerWebSearch(
        params=params, cache_tools_list=False, name="custom", client_session_timeout_seconds=9
    ) as server:
        llm = search_llm("web_fetch", {"urls": ["https://example.org/release?a=1&b=2"]})
        result = await Agent(llm=llm, mcp_servers=[server]).run("Read release notes")
        assert result.tool_calls
        assert server.params == params
        assert server.params is not params
        assert server.params["headers"] is not params["headers"]
        assert server.client_session_timeout_seconds == 9
        assert server.cache_tools_list is False
        assert server.name == "custom"
    assert http_mcp["calls"][0]["arguments"]["urls"] == ["https://example.org/release?a=1&b=2"]
    for request in http_mcp["requests"]:
        assert str(request.url) == params["url"]
        assert request.headers["authorization"] == "Bearer explicit-test-key"
        assert request.headers["user-agent"] == "my-ragbits-app"
        assert request.extensions["timeout"] == {"connect": 17, "read": 45, "write": 17, "pool": 17}


def test_default_headers_do_not_mutate_explicit_params(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "ambient-key-must-not-be-read")
    params: MCPServerStreamableHttpParams = {"url": "https://example.org/mcp", "headers": {"X-Custom": "kept"}}
    server = MCPServerWebSearch(params=params)
    assert server.params["headers"] == {"X-Custom": "kept", "User-Agent": "ragbits-agents"}
    assert params["headers"] == {"X-Custom": "kept"}
    assert "Authorization" not in MCPServerWebSearch().params["headers"]
    assert MCPServerStreamableHttp(params=params).params == params


async def test_search_remains_disabled_without_server(http_mcp: dict[str, Any]):
    result = await Agent(llm=search_llm()).run("Search")
    assert not result.tool_calls
    assert not http_mcp["requests"]


async def test_tool_permission_denial_does_not_search(http_mcp: dict[str, Any], deny_hook: PreToolCallback):
    async with MCPServerWebSearch() as server:
        agent = Agent(
            llm=search_llm(), mcp_servers=[server], hooks=[Hook(event_type=EventType.PRE_TOOL, callback=deny_hook)]
        )
        result = await agent.run("Search")
    assert result.tool_calls[0].result == "Blocked by hook"
    assert not http_mcp["calls"]


@pytest.mark.parametrize("error", ["tool", "protocol", "wait"])
async def test_errors_and_timeout_do_not_fall_back(http_mcp: dict[str, Any], error: str):
    http_mcp["error"] = error
    async with MCPServerWebSearch(
        params={"url": "https://configured.example.test/mcp"}, client_session_timeout_seconds=0.05
    ) as server:
        agent = Agent(llm=search_llm(), mcp_servers=[server])
        if error == "tool":
            result = await agent.run("Search")
            assert result.tool_calls[0].result.isError
        else:
            with pytest.raises(AgentToolExecutionError) as exc_info:
                await agent.run("Search")
            assert ("bad query" if error == "protocol" else "Timed out") in str(exc_info.value)
    assert server.session is None
    assert len(http_mcp["calls"]) == 1
    assert all(str(request.url) == "https://configured.example.test/mcp" for request in http_mcp["requests"])


async def test_cancellation_closes_the_connection(http_mcp: dict[str, Any]):
    http_mcp["error"] = "wait"
    async with MCPServerWebSearch() as server:
        task = asyncio.create_task(Agent(llm=search_llm(), mcp_servers=[server]).run("Search"))
        await asyncio.wait_for(http_mcp["started"].wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert server.session is None
    assert len(http_mcp["calls"]) == 1
