"""
Ragbits Agents Example: Filesystem MCP

This example demonstrates how to integrate Model Context Protocol (MCP) servers
with ragbits agents to provide dynamic tool capabilities. The agent connects to
an MCP server that provides filesystem access tools, allowing it to interact
with the local file system through natural language queries.

Before running the script, make sure you have Node.js installed on your machine.

To run the script, execute the following command:

    ```bash
    uv run examples/agents/filesystem_mcp.py
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

from ragbits.agents import Agent
from ragbits.agents.mcp import MCPServerStdio
from ragbits.core.llms import LiteLLM


async def main() -> None:
    """
    Run the example.
    """
    async with MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        }
    ) as server:
        llm = LiteLLM(model_name="gpt-4o-2024-08-06")
        agent = Agent(llm=llm, mcp_servers=[server])
        response = await agent.run("List all files in a current directory.")
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
