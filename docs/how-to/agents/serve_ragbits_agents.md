# How-To: Serve Ragbits agents for A2A communication
Ragbits agents can be deployed as HTTP servers to enable [A2A (Agent-to-Agent) communication](https://a2aprotocol.ai/#about]). By exposing a FastAPI-based API, agents can receive structured requests, perform reasoning or tool-based operations, and return structured responses — enabling seamless interoperability between agents or external services.

This guide walks through serving a Ragbits agent using FastAPI and Uvicorn, making it compliant with the A2A specification, including the discovery endpoint `.well-known/agent.json`.

## Define the agent
Start by creating a simple weather agent using a structured prompt and tool function:

```python
from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/tool_use.py:31:70"
```

## Generate the agent card
The Agent Card defines the agent’s name, description, and endpoint. It’s automatically served at `/.well-known/agent.json` and is required for A2A discovery. You can generate the Agent Card using the [`get_agent_card`][ragbits.agents.Agent.get_agent_card] method:

```python
agent_card = agent.get_agent_card(
    name="Weather Agent",
    description="Provides current weather for a given location.",
    port="8000",
)
```

## Serve the Agent
To serve the agent over HTTP with A2A-compliant endpoints, use the built-in [`create_agent_server`][ragbits.agents.a2a.server.create_agent_server] utility. The agent server exposes two endpoints:

| Endpoint                  | Method | Description                                                                          |
| ------------------------- | ------ | ------------------------------------------------------------------------------------ |
| `/.well-known/agent.json` | `GET`  | Returns the agent's `AgentCard` metadata                                             |
| `/`                       | `POST` | Accepts a structured input `params: dict` and returns the agent's reasoning output |

!!! note

    By default, the server runs on port `8000`. This can be customized by setting the `port` parameter when generating the agent card.

To launch the agent as an A2A-compatible HTTP server, run the following code:
```python
from ragbits.agents.a2a.server import create_agent_server

async def main():
    server = create_agent_server(agent, agent_card, WeatherPromptInput)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```
This starts a FastAPI-based server on port `8000`, serving the agent’s capabilities at the `.well-known/agent.json` discovery endpoint and handling structured `POST /` requests in compliance with the A2A specification.
