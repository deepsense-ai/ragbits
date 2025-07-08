# Tutorial: Multi-Agent System with A2A and MCP

Let's build a multi-agent system for automated trip planning with Ragbits. In this tutorial, we'll create:

1. A Flight Finder Agent that searches for available flights
2. A City Explorer Agent that gathers information about destinations  
3. An Orchestrator Agent that coordinates both agents to create comprehensive trip plans

**What you'll learn:**

- How to create specialized agents with [tools/function calling](https://platform.openai.com/docs/guides/function-calling?api-mode=responses)
- How to use the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) for external data
- How to expose agents through [Agent-to-Agent (A2A)](https://github.com/a2aproject/A2A) protocol
- How to build an orchestrator that manages conversation context

By the end of this tutorial, our system will be able to handle conversation like this:

**USER**:  I'm from New York and want to explore Europe. What is interesting in Paris? <br>
**ASSISTANT**: (Orchestrator + City Finder Agent + MCP): Paris is a very interesting... <br>
**USER**: Are there any flights available? <br>
**ASSISTANT** (history + Flight Agents + Tools): Here are some available flight from New York to Paris... <br>

## Configuring the environment

Install the latest Ragbits via `pip install -U ragbits` and `pip install ragbits-agents[mcp]` to follow along.

During development, we will use OpenAI's `gpt-4o-2024-08-06` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this with [other providers](../how-to/llms/use_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Building the Flight Finder Agent

We start by defining the [prompt](../how-to/prompts/use_prompting.md) that will lead this agent.

```py title="flight_agent.py"
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/a2a/flight_agent.py:37:53"

print(FlightPrompt(FlightPromptInput(input="I need to fly from New York to Paris. What flights are available?")).chat)
# [{'role': 'system', 'content': 'You are a helpful travel assistant that finds available flights between two cities.'}, 
# {'role': 'user', 'content': 'I need to fly from New York to Paris. What flights are available?'}]
```

Next, we [define a tool](../how-to/llms/use_tools_with_llms.md) that will provide flight information. **Note**: in a real application, you'd connect to the actual flight APIs:

```py title="flight_agent.py"
import json

--8<-- "examples/agents/a2a/flight_agent.py:11:34"
```

This agent will call this function as needed, and the results will be injected back to the conversation.

Now let's create the agent and test it:

```py title="flight_agent.py"
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

--8<-- "examples/agents/a2a/flight_agent.py:55:59"

async def main() -> None:
    result = await flight_agent.run(FlightPromptInput(input="I need to fly from New York to Paris. What flights are available?"))
    print(result.content)

--8<-- "examples/agents/a2a/flight_agent.py:71:74"
```

Run it:

```bash
python flight_agent.py
```

A typical response looks like this:
```text
Here are some available flights from New York to Paris:

1. **British Airways**
   - **Departure:** 10:00 AM
   - **Arrival:** 10:00 PM

2. **Delta**
   - **Departure:** 1:00 PM
   - **Arrival:** 1:00 AM
```

**Please note** that the results may differ among the runs due to undeterministic nature of LLM.

!!! example "Try it yourself"
    You can try to connect this agents to a real flight API, such as [aviationstack](https://aviationstack.com/).

## Building the City Explorer Agent

Let's create a City Explorer Agent that gather and synthesize city information from the internet. Again we start with the prompt:

```py title="city_explorer_agent.py"
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/a2a/city_explorer_agent.py:9:31"
```

Now define the agent, We will not [build an MCP server from scratch](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#quickstart), but run an already existing one - [Web Fetcher](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch). Start by installing it with:

```bash
pip install mcp-server-fetch
```

```py title="city_explorer_agent.py"
from ragbits.agents import Agent
from ragbits.agents.mcp import MCPServerStdio
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt
--8<-- "examples/agents/a2a/city_explorer_agent.py:34:47"
        result = await city_explorer_agent.run(CityExplorerPromptInput(city="Paris"))
        print(result.content)

--8<-- "examples/agents/a2a/city_explorer_agent.py:59:63"
```

Test this agent by running:
```bash
python city_explorer_agent.py
```

```text
Paris is the capital and largest city of France, located in the Île-de-France region. Renowned for its historical landmarks, the city is a significant cultural and economic center in Europe. Key attractions include the Eiffel Tower, Notre-Dame Cathedral, the Louvre Museum, and the Arc de Triomphe. Known for its romantic ambiance, Paris is often referred to as "The City of Light."

The city is characterized by its extensive urban area and is densely populated, with a population of over 2 million within city limits and approximately 13 million in the metropolitan area as of 2021. Paris is divided into 20 districts, known as arrondissements. The current mayor is Anne Hidalgo. The city's motto is "Fluctuat nec mergitur," meaning "Tossed by the waves but never sunk," reflecting its resilience.

Paris is a hub for art, fashion, gastronomy, and culture, drawing millions of visitors each year who seek to experience its heritage and vibrant lifestyle.
```

**Notice** that we didn't have to write any tool, just reuse already existing one. This is the magic of MCP protocol.

## Exposing Agents through A2A

Now we need to expose our agents through the Agent-to-Agent (A2A) protocol so they can be called remotely. We'll create [agent cards](https://a2aproject.github.io/A2A/v0.2.5/specification/#55-agentcard-object-structure) and servers for both agents. Let's start with the flight agent. **Update the main function with**:

```python title="flight_agent.py"
from ragbits.agents.a2a.server import create_agent_server

--8<-- "examples/agents/a2a/flight_agent.py:62:69"
```

and then run.

```bash
python flight_agent.py
```

Now, your server with agent should be up and running

```
INFO:     Started server process [1473119]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

You can go to your browser and type `http://127.0.0.1:8000/.well-known/agent.json` to see and agent card:

```json
{
  "additionalInterfaces": null,
  "capabilities": {
    "extensions": null,
    "pushNotifications": null,
    "stateTransitionHistory": null,
    "streaming": null
  },
  // More text...
  "supportsAuthenticatedExtendedCard": null,
  "url": "http://127.0.0.1:8000",
  "version": "0.0.0"
}
```

!!! warning
    Do not kill this process, open a new terminal for the next parts.

Next, do the same for the City Explorer agent

```python title="city_explorer_agent.py"
from ragbits.agents.a2a.server import create_agent_server

--8<-- "examples/agents/a2a/city_explorer_agent.py:49:58"
```

and run in another terminal

```bash
python city_explorer_agent.py
```

## Building the Orchestrator Agent

Now let's create the orchestrator agent that will be trip planning chat which utilises our specialized agents.

First we need to gather information about all of our available agents

```python title="orchestrator.py"
import requests

--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:11:29"
print(AGENTS_INFO)
```

```text
name: Flight Info Agent, description: Provides available flight information between two cities., skills: [{'description': "Returns flight information between two locations.\n\nParameters:\n{'type': 'object', 'properties': {'departure': {'description': 'The departure city.', 'title': 'Departure', 'type':...
name: City Explorer Agent, description: Provides information about a city., skills: [{'description': "Fetches a URL from the internet and optionally extracts its contents as markdown.\n\nAlthough originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.\n\nParameters:\n{'description': 'Parameters...
```

Next, we create the prompt

```python title="orchestrator.py"
from pydantic import BaseModel
from ragbits.core.prompt import Prompt


--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:32:56"
```

To finally create a tool that will call agents 
```python title="orchestrator.py"
import json

--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:59:92"
```

Now let's put it all together:

```python title="orchestrator.py"
from ragbits.agents import Agent, ToolCallResult
from ragbits.core.llms import LiteLLM, ToolCall
import asyncio

--8<-- "examples/agents/a2a/agent_orchestrator_with_tools.py:95:121"
```

Now you can test the complete system by running (assuming city and flight agents are running in another terminals):

```bash
python orchestrator.py
```

Then interact with the orchestrator with `I want to visit Paris from New York. Please give me some info about it and suggest recommended flights`:

1. The orchestrator calls city explorer and flight finder agents
1. The city explorer agent fetches Paris information via MCP
1. The flight finder agent searches for New York → Paris flights
1. The orchestrator combines everything into a comprehensive trip plan and streams the response


**Good job, you've done it!**

Feel free to extend this system with additional agents for activities, restaurants, weather information, or any other travel-related services.

!!! tip
    Full working example of this code can be found at:

    * `examples/agents/a2a/agent_orchestrator_with_tools.py`
    * `examples/agents/a2a/flight_agent.py`
    * `examples/agents/a2a/city_explorer_agent.py`
