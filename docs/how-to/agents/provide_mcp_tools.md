# How-To: Provide tools with Model Context Protocol (MCP)

The [Model Context Protocol](https://modelcontextprotocol.io/introduction) (aka MCP) is a way to provide tools and context to the LLM. From the MCP docs:

> MCP is an open protocol that standardizes how applications provide context to LLMs. Think of MCP like a USB-C port for AI applications. Just as USB-C provides a standardized way to connect your devices to various peripherals and accessories, MCP provides a standardized way to connect AI models to different data sources and tools.

Ragbits has support for MCP. This enables you to use a wide range of MCP servers to provide tools to your Agents.

## MCP servers

Currently, the MCP spec defines three kinds of servers, based on the transport mechanism they use:

- **stdio** servers run as a subprocess of your application. You can think of them as running "locally".
- **HTTP over SSE** servers run remotely. You connect to them via a URL.
- **Streamable HTTP** servers run remotely using the Streamable HTTP transport defined in the MCP spec.

You can use the [`MCPServerStdio`][ragbits.agents.mcp.server.MCPServerStdio], [`MCPServerSse`][ragbits.agents.mcp.server.MCPServerSse], and [`MCPServerStreamableHttp`][ragbits.agents.mcp.server.MCPServerStreamableHttp] classes to connect to these servers.

For example, this is how you'd use the [official MCP filesystem server](https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem) (before running, make sure you have Node.js installed on your machine).

```python
from ragbits.agents.mcp import MCPServerStdio

async with MCPServerStdio(
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
    }
) as server:
    tools = await server.list_tools()
```

A complete list of working examples is available [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/mcp).

## Using MCP servers

MCP servers can be added to Agents. Ragbits will call `list_tools()` on the MCP servers each time the Agent is run. This makes the LLM aware of the MCP server's tools. When the LLM calls a tool from an MCP server, Ragbits calls `call_tool()` on that server.

```python
from ragbits.agents import Agent
from ragbits.agents.mcp import MCPServerStdio
from ragbits.core.llms import LiteLLM

async with MCPServerStdio(
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
    }
) as server:
    agent = Agent(llm=LiteLLM(model_name="gpt-4.1-nano"), mcp_servers=[server])
    await agent.run("List all files in the current directory.")
```

A complete example for local MCP integration is available [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/mcp/local.py).

## Web search and page fetching

Install `ragbits-agents[mcp]` to use [`MCPServerWebSearch`][ragbits.agents.mcp.search.MCPServerWebSearch].
With no parameters, it connects to [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp),
which provides free web search in Fast mode and page fetching without an account or API key.
The agent discovers the `web_search` and `web_fetch` tools through the existing MCP tool loader.

```python
from ragbits.agents import Agent
from ragbits.agents.mcp import MCPServerWebSearch
from ragbits.core.llms import LiteLLM

async def research() -> str:
    async with MCPServerWebSearch() as server:
        agent = Agent(llm=LiteLLM(model_name="gpt-4.1-nano"), mcp_servers=[server])
        result = await agent.run("Find the latest Ragbits release and read its release notes. Include source URLs.")
        return result.content
```

Run `research()` from your application's async entrypoint. The model above still uses your configured LLM credentials.
Search is enabled by attaching the server to the agent; agents without it keep their existing tools.
The existing OpenAI `get_web_search_tool(model_name=...)` helper remains available explicitly.

For a different Streamable HTTP search server, or authenticated Parallel access, pass `params` explicitly:

```python
import os

server = MCPServerWebSearch(
    params={
        "url": "https://search.parallel.ai/mcp",
        "headers": {"Authorization": f"Bearer {os.environ['PARALLEL_API_KEY']}"},
        "timeout": 30,
    },
    cache_tools_list=False,
    client_session_timeout_seconds=90,
)
```

Explicit parameters replace the default server configuration. Errors from a configured server do not trigger a fallback.
Anonymous access has usage limits; use authenticated access for higher limits.
The MCP response timeout defaults to 60 seconds and can be adjusted with `client_session_timeout_seconds`.

The server does not generate or store a conversation-level `session_id`. If your application supplies this optional
tool argument, generate an opaque UUID once per conversation and reuse it for related searches, fetches and retries.
Use a new ID for a new conversation, even when reusing a connected server. Do not use personal data as the ID.

## Caching

Every time an Agent runs, it calls `list_tools()` on the MCP server. This can be a latency hit, especially if the server is a remote server. To automatically cache the list of tools, you can pass `cache_tools_list=True` to [`MCPServerStdio`][ragbits.agents.mcp.server.MCPServerStdio], [`MCPServerSse`][ragbits.agents.mcp.server.MCPServerSse], and [`MCPServerStreamableHttp`][ragbits.agents.mcp.server.MCPServerStreamableHttp]. You should only do this if you're certain the tool list will not change.

If you want to invalidate the cache, you can call `invalidate_tools_cache()` on the servers.
