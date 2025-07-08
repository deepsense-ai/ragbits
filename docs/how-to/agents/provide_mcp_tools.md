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

For example, this is how you'd use the [official MCP filesystem server](https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem).

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

## Using MCP servers

MCP servers can be added to Agents. Ragbits will call `list_tools()` on the MCP servers each time the Agent is run. This makes the LLM aware of the MCP server's tools. When the LLM calls a tool from an MCP server, Ragbits calls `call_tool()` on that server.

```python
from ragbits.agents import Agent

agent = Agent(
    prompt="Use the tools to achieve the task",
    mcp_servers=[mcp_server_1, mcp_server_2]
)
```

## Caching

Every time an Agent runs, it calls `list_tools()` on the MCP server. This can be a latency hit, especially if the server is a remote server. To automatically cache the list of tools, you can pass `cache_tools_list=True` to [`MCPServerStdio`][ragbits.agents.mcp.server.MCPServerStdio], [`MCPServerSse`][ragbits.agents.mcp.server.MCPServerSse], and [`MCPServerStreamableHttp`][ragbits.agents.mcp.server.MCPServerStreamableHttp]. You should only do this if you're certain the tool list will not change.

If you want to invalidate the cache, you can call `invalidate_tools_cache()` on the servers.
