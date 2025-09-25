# How-To: Stream downstream agents with Ragbits

Ragbits [Agent][ragbits.agents.Agent] can call other agents as tools, creating a chain of reasoning where downstream agents provide structured results to the parent agent.

Using the streaming API, you can observe every chunk of output as it is generated, including tool calls, tool results, and final text - perfect for real-time monitoring or chat interfaces.

## Define a simple tool

A tool is just a Python function returning a JSON-serializable result. Here’s an example tool returning the current time for a given location:

```python
import json

--8<-- "examples/agents/downstream_agents_streaming.py:33:51"
```

## Create a downstream agent

The downstream agent wraps the tool with a prompt, allowing the LLM to use it as a function.

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt
from ragbits.agents import Agent
from ragbits.agents._main import AgentOptions
from ragbits.core.llms import LiteLLM

--8<-- "examples/agents/downstream_agents_streaming.py:54:82"
```

## Create a parent QA agent

The parent agent can call downstream agents as tools. This lets the LLM reason and decide when to invoke the downstream agent.

```python
--8<-- "examples/agents/downstream_agents_streaming.py:85:111"
```

## Streaming output from downstream agents

Use `run_streaming` with an [AgentRunContext][ragbits.agents.AgentRunContext] to see output as it happens. Each chunk contains either text, a tool call, or a tool result. You can print agent names when they change and handle downstream agent events.

```python
import asyncio
from ragbits.agents import DownstreamAgentResult

--8<-- "examples/agents/downstream_agents_streaming.py:114:133"
```
