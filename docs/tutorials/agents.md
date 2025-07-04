# Tutorial: Multi-Agent System with A2A and MCP

Let's build a multi-agent system for automated trip planning with Ragbits. In this tutorial, we'll:

1. Build Flight Finder Agent that searches and recommends available flights between destinations with tools
1. Create City Explorer Agent that uses Model-Content-Provider (MCP) to gather and synthesize city information from the internet
1. Expose these agents through Agent-to-Agent (A2A) Protocol
1. Build an orchestrator with memory management that coordinates these specialized agents to create comprehensive trip plans

## Configuring the environment

Install the latest Ragbits via `pip install -U ragbits` and follow along.

During development, we will use OpenAI's `gpt-4o-2024-08-06` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Building the Flight Finder Agent

We start by defining the prompt that will lead this agent. The prompt needs to handle structured input for departure and arrival cities:

```python
# In flight_agent.py
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/a2a/flight_agent.py:37:53"
```

Next, we define tool that will provide flight information:

```python
# In flight_agent.py
import json

--8<-- "examples/agents/a2a/flight_agent.py:11:34"
```

Now let's create the agent and test it:

```python
#In flight_agent.py
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

--8<-- "examples/agents/a2a/flight_agent.py:56:60"

async def main() -> None:
    result = await flight_agent.run(FlightPromptInput(departure="New York", arrival="Paris"))
    print(result.content)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

Go and run

```bash
python flight_agent.py
```

```text
Here are some available flights from New York to Paris:

1. **British Airways**
   - **Departure:** 10:00 AM
   - **Arrival:** 10:00 PM

2. **Delta**
   - **Departure:** 1:00 PM
   - **Arrival:** 1:00 AM
```

## Building the City Explorer Agent


We will not [build an MCP server from scratch](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#quickstart), but run an already existing one - [Web Fetcher](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) and make it available to one of our agents. Please install it with

```bash
pip install mcp-server-fetch
```

Now, let's create a City Explorer Agent that gather and synthesize city information from the internet. Again we start with the prompt

```python
# In city_explorer_agent.py
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/a2a/city_explorer_agent.py:9:30"
```

Now define the agent

```python
# In city_explorer_agent.py
--8<-- "examples/agents/a2a/city_explorer_agent.py:36:47"
        result = await city_explorer_agent.run(CityExplorerPromptInput(city="Paris"))
        print(result.content)

--8<-- "examples/agents/a2a/city_explorer_agent.py:56:58"
```

Test this agent by running

```bash
python city_explorer_agent.py
```
```text

```

**Notice** that we didn't have to write any tool, just reuse already existing one. This is the magic of MCP protocol.

## Exposing Agents Through A2A

Now we need to expose our agents through the Agent-to-Agent (A2A) protocol so they can be called remotely. We'll create agent cards and servers for both agents:

```python
#In both files
from ragbits.agents.a2a.server import create_agent_app, create_agent_server

#In flight_agent.py
--8<-- "examples/agents/a2a/flight_agent.py:62:66"

#In city_explorer_agent.py inside the def main
--8<-- "examples/agents/a2a/city_explorer_agent.py:49:53"
```

To run these servers, you can write
```python
# In flight_agent.py
--8<-- "examples/agents/a2a/flight_agent.py:68:69"

#In city_explorer_agent.py
--8<-- "examples/agents/a2a/city_explorer_agent.py:54:58"
```

and then run

```bash
python flight_agent.py
```

After running you should see

```
INFO:     Started server process [1473119]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Now you can go to your browser and type `http://127.0.0.1:8000/.well-known/agent.json` and you should see and agent card looking like this

```json
{
  "additionalInterfaces": null,
  "capabilities": {
    "extensions": null,
    "pushNotifications": null,
    "stateTransitionHistory": null,
    "streaming": null
  },
  "defaultInputModes": [
    "text"
  ],
  "defaultOutputModes": [
    "text"
  ],
  "description": "Provides available flight information between two cities.",
  "documentationUrl": null,
  "iconUrl": null,
  "name": "Flight Info Agent",
  "preferredTransport": null,
  "protocolVersion": "0.2.5",
  "provider": null,
  "security": null,
  "securitySchemes": null,
  "skills": [
    {
      "description": "Returns flight information between two locations.\n\nArgs:\n    departure: The departure city.\n    arrival: The arrival city.\n\nReturns:\n    A JSON string with mock flight details.",
      "examples": null,
      "id": "get_flight_info",
      "inputModes": null,
      "name": "Get Flight Info",
      "outputModes": null,
      "tags": []
    }
  ],
  "supportsAuthenticatedExtendedCard": null,
  "url": "http://127.0.0.1:8000",
  "version": "0.0.0"
}
```

## Building the Orchestrator Agent

Now let's create the orchestrator agent that will be trip planning chat which utilises our specialized agents.

First we need to gather information about all of our available agents

```python
# In orchestrator.py
import requests

--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:15:29"
print(AGENTS_INFO)
```

```text
Output of agents_info
```

Next, we create the prompt

```python
# In orchestrator.py
from pydantic import BaseModel
from ragbits.core.prompt import Prompt


--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:32:57"
```

To finally create a tool that will call expected agents 

```python
# In orchestrator.py
--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:60:93"
```

Now let's put it all together in the main orchestrator:

```python
# In orchestrator.py
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM
import asyncio

async def main() -> None:
--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:120:134"
```

## Testing the Multi-Agent System

Now you can test the complete system by running:

```bash
# Terminal 1: Start the flight agent
python flight_agent.py

# Terminal 2: Start the city explorer agent 
python city_explorer_agent.py

# Terminal 3: Run the orchestrator
python orchestrator.py
```

Then interact with the orchestrator:

```
USER: I'm from New York and want to explore Europe. What is interesting in Paris?
```

Assistant will use the city explorer agent through a2a, which will use MCP to fetch Paris wikipedia page and give the answet to the orchestrator which in turn will bring it back to you.

Then in the same chat ask

```
USER: Are there any flights available?
```

Assistant now have entire conversation in context so it remembers you are from New York and will ask flight agent throught a2a to return flight info about New York -> Paris.


## Conclusions

This tutorial demonstrates how to build a sophisticated multi-agent system with Ragbits that:

- **Specializes agents** for specific tasks (flight search, hotel recommendations)
- **Exposes agents** through the A2A protocol for remote communication
- **Orchestrates coordination** between agents with memory and context management
- **Maintains conversation history** in the orchestrator while keeping specialized agents stateless

The system can be extended with additional agents for activities, restaurants, weather information, or any other travel-related services. Each agent can be developed, tested, and deployed independently while the orchestrator provides a unified interface for users.

!!! tip
    Full working example of this code can be found at:

    * `examples/agents/a2a/agent_orchestrator_with_tools.py`
    * `examples/agents/a2a/flight_agent.py`
    * `examples/agents/a2a/city_explorer_agent.py`
