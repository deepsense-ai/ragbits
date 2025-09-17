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

--8<-- "examples/agents/tool_use.py:51:72"
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

### Alternative approach: inheritance with `prompt_config`

In addition to explicitly attaching a Prompt instance, Ragbits also supports defining agents through a combination of inheritance and the `@Agent.prompt_config` decorator.

This approach lets you bind input (and optionally output) models directly to your agent class. The agent then derives its prompt structure automatically, without requiring a prompt argument in the constructor.

```python
from pydantic import BaseModel
from ragbits.agents import Agent

--8<-- "examples/agents/with_decorator.py:51:71"
```

The decorator can also accept an output type, allowing you to strongly type both the inputs and outputs of the agent. If you do not explicitly define a `user_prompt`, Ragbits will default to `{{ input }}`.

Once defined, the agent class can be used directly, just like any other subclass of Agent:

```python
import asyncio
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

--8<-- "examples/agents/with_decorator.py:73:84"
```

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/with_decorator.py).

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

## Binding dependencies via AgentRunContext
You can bind your external dependencies before the first access and safely use them in tools. After first attribute lookup, the dependencies container freezes to prevent mutation during a run.

```python
from dataclasses import dataclass
from ragbits.agents import Agent, AgentRunContext
from ragbits.core.llms.mock import MockLLM, MockLLMOptions

@dataclass
class Deps:
    api_host: str

def get_api_host(context: AgentRunContext | None) -> str:
    """Return the API host taken from the bound dependencies in context."""
    assert context is not None
    return context.deps.api_host

async def main() -> None:
    llm = MockLLM(
        default_options=MockLLMOptions(
            response="Using dependencies from context.",
            tool_calls=[{"name": "get_api_host", "arguments": "{}", "id": "example", "type": "function"}],
        )
    )
    agent = Agent(llm=llm, prompt="Retrieve API host", tools=[get_api_host])

    context = AgentRunContext()
    context.deps.value = Deps(api_host="https://api.local")

    result = await agent.run("What host are we using?", context=context)
    print(result.tool_calls[0].result)
```

See the runnable example in `examples/agents/dependencies.py`.

## Streaming agent responses
For use cases where you want to process partial outputs from the LLM as they arrive (e.g., in chat UIs), the [`Agent`][ragbits.agents.Agent] class supports streaming through the `run_streaming()` method.

This method returns an `AgentResultStreaming` object — an async iterator that yields parts of the LLM response and tool-related events in real time.

## Native OpenAI tools
Ragbits supports selected native OpenAI tools (web_search_preview, image_generation and code_interpreter). You can use them together with your tools.
```python
from ragbits.agents.tools import get_web_search_tool

async def main() -> None:
    """Run the weather agent with additional tool."""
    model_name = "gpt-4o-2024-08-06"
    llm = LiteLLM(model_name=model_name, use_structured_output=True)
    agent = Agent(llm=llm, prompt=WeatherPrompt, tools=[get_web_search_tool(model_name)], keep_history=True)

    response = await agent.run(WeatherPromptInput(location="Paris"))
    print(response)
```

Tool descriptions are available [here](https://platform.openai.com/docs/guides/tools?api-mode=responses). For each of these you can see detailed
information on the corresponding sub-pages (i.e. [here](https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses#user-location) for web search).
You can use default parameters or specify your own as a dict. For web search this might look like that:
```python
from ragbits.agents.tools import get_web_search_tool

tool_params = {
        "user_location": {
            "type": "approximate",
            "country": "GB",
            "city": "London",
            "region": "London",
        }
}
web_search_tool = get_web_search_tool("gpt-4o", tool_params)
```