"""
Ragbits Agents Example: MCP Streamable HTTP

This example demonstrates how to integrate Model Context Protocol (MCP) servers
with ragbits agents to provide dynamic tool capabilities. The agent connects to
an MCP server via HTTP, which provides weather information tools, allowing it to query
current weather conditions through natural language requests.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/mcp/streamable_http.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "ragbits-agents[mcp]",
# ]
# ///
import asyncio
from threading import Thread

from aiohttp import ClientSession
from mcp.server.fastmcp import FastMCP

from ragbits.agents import Agent
from ragbits.agents.mcp.server import MCPServerStreamableHttp
from ragbits.core.llms import LiteLLM

mcp = FastMCP()


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """
    Returns the current weather for a given city.

    Args:
        city: The city to get the weather for.

    Returns:
        The current weather for the given city.
    """
    endpoint = "https://wttr.in"
    async with ClientSession() as session, session.get(f"{endpoint}/{city}") as response:
        return await response.text()


async def main() -> None:
    """
    Run the example.
    """
    async with MCPServerStreamableHttp(
        params={
            "url": "http://localhost:8000/mcp",
        },
        client_session_timeout_seconds=20,
    ) as server:
        llm = LiteLLM(model_name="gpt-4o-2024-08-06")
        agent = Agent(llm=llm, mcp_servers=[server])
        response = await agent.run("What's the weather in Bydgoszcz?")
        print(response)


if __name__ == "__main__":
    # We'll run the Streamable HTTP server in a another thread. Usually this would be a remote server, but for this
    # demo, we'll run it locally at http://localhost:8000/mcp
    server = Thread(target=lambda: mcp.run(transport="streamable-http"), daemon=True)
    server.start()

    asyncio.run(main())
