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
def get_weather(location: str) -> str:
    """
    Returns the current weather for a given location.
    """
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})
```

### Define a Prompt
Use a structured prompt to instruct the LLM. For details on writing prompts with Ragbits, see the [Guide to Prompting](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/).

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

class WeatherPromptInput(BaseModel):
    location: str

class WeatherPrompt(Prompt[WeatherPromptInput]):
    system_prompt = """
    You are a helpful assistant that responds to user questions about weather.
    """

    user_prompt = """
    Tell me the temperature in {{ location }}.
    """
```

### Run the Agent
Create the agent, attach the prompt and tool, and run it:
```python
import asyncio
from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    agent = Agent(llm=llm, prompt=WeatherPrompt, tools=[get_weather])
    response = await agent.run(WeatherPromptInput(location="Paris"))
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

The result is an [AgentResult][ragbits.agents.AgentResult], which includes the model's output, additional metadata, conversation history, and any tool calls performed.

You can find the complete code example in the Ragbits repository [here](https://github.com/deepsense-ai/ragbits/blob/main/examples/agents/tool_use.py).
