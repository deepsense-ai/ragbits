# How-To: Define and use agents with Ragbits

Ragbits [`Agent`][ragbits.agents.Agent] combines the reasoning power of LLMs with the ability to execute custom code through *tools*. This makes it possible to handle complex tasks by giving the model access to your own Python functions.

When using tool-enabled agents, the LLM reviews the system prompt and incoming messages to decide whether a tool should be called. Instead of just generating a text response, the model can choose to invoke a tool or combine both approaches.

Before using tools, you can check whether your selected model supports function calling with:
```python
litellm.supports_function_calling(model="your-model-name")
```

If function calling is supported and tools are enabled, the agent interprets the user input, decides whether a tool is needed, executes it if necessary, and returns a final response enriched with tool results.

This response is encapsulated in an [`AgentResult`][ragbits.agents.AgentResult], which includes the model's output, additional metadata, conversation history, and any tool calls performed.

## How to build an agent with Ragbits
This guide walks you through building a simple agent that uses a `get_weather` tool to return weather
data based on a location.

### Define a tool function
First, define the function you want your agent to call. It should take regular Python arguments and return a JSON-serializable result.
```python
import json

--8<-- "examples/agents/tool_use.py:31:48"
```

### Define a prompt
Use a structured prompt to instruct the LLM. For details on writing prompts with Ragbits, see the [Guide to Prompting](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/).

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

--8<-- "examples/agents/tool_use.py:51:70"
```

### Run the agent
Create the agent, attach the prompt and tool, and run it:
```python
import asyncio
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

--8<-- "examples/agents/tool_use.py:73:84"
```

The result is an [AgentResult][ragbits.agents.AgentResult], which includes the model's output, additional metadata, conversation history, and any tool calls performed.

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/tool_use.py).

## Tool choice
To control what tool is used at first call you could use `tool_choice` parameter. There are the following options:
- "auto": let model decide if tool call is needed
- "none": do not call tool
- "required: enforce tool usage (model decides which one)
- Callable: one of provided tools


## Conversation history
[`Agent`][ragbits.agents.Agent]s can retain conversation context across multiple interactions by enabling the `keep_history` flag when initializing the agent. This is useful when you want the agent to understand follow-up questions without needing the user to repeat earlier details.

To enable this, simply set `keep_history=True` when constructing the agent. The full exchange—including messages, tool calls, and results—is stored and can be accessed via the AgentResult.history property.

### Example of context preservation
The following example demonstrates how an agent with history enabled maintains context between interactions:

```python
async def main() -> None:
    """Run the weather agent with conversation history."""
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    agent = Agent(llm=llm, prompt=WeatherPrompt, tools=[get_weather], keep_history=True)

    await agent.run(WeatherPromptInput(location="Paris"))

    # Follow-up question about Tokyo - the agent retains weather context
    response = await agent.run("What about Tokyo?")
    print(response)
```

In this scenario, the agent recognizes that the follow-up question "What about Tokyo?" refers to weather information due to the preserved conversation history. The expected output would be an AgentResult containing the response:

```python
AgentResult(content='The current temperature in Tokyo is 10°C.', ...)
```

## Streaming agent responses
For use cases where you want to process partial outputs from the LLM as they arrive (e.g., in chat UIs), the [`Agent`][ragbits.agents.Agent] class supports streaming through the `run_streaming()` method.

This method returns an `AgentResultStreaming` object — an async iterator that yields parts of the LLM response and tool-related events in real time.
