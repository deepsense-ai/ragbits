# How-To: Use tool calling with LLMs in Ragbits

This guide will walk you through providing external tools to use by LLMs. This feature enables LLMs to return which of the provided tools to call and with which arguments in order to accomplish a task given in the prompt.


## Using tools with LLMs

Tools for LLMs need to be defined as functions with docstrings describing the function's purpose, its arguments and its return value:

```python
from ragbits.core.prompt import Prompt


def get_weather(location: str, units: str = None) -> dict:
    """
    Returns the current weather for a given location.

    Args:
        location: The location to get the weather for.
        units: The units to use for the weather information.

    Returns:
        The current weather for the given location.
    """
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": "celsius"})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": "celsius"})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


class QueryWithContext(BaseModel):
    query: str


class OutputSchema(BaseModel):
    response: str


class LLMPrompt(Prompt[QueryWithContext, OutputSchema]):
    system_prompt = """
    You are a helpful assistant. Answer the QUESTION that will be provided by the user.
    """

    user_prompt = """
    QUESTION:
    {{ query }}
    """
```

Tools can be passed to LLMs as optional generation argument. If LLM decides to use tools then tool calls will be available in ```tool_calls``` field of the response and there will be no text output. If model decides not to use tools then ```tool_calls``` field won't be present and text output will be returned as usual:

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    query = "Tell me about the temperature in San Francisco."
    prompt = LLMPrompt(QueryWithContext(query=query))
    response = await llm.generate(prompt, tools=[get_weather])
    print(response)

asyncio.run(main())
```

Tools can also be provided in the following JSON format instead of an implemented function:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Returns the current weather for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "description": "The location to get the weather for.",
                        "title": "Location",
                        "type": "string",
                    }
                },
                "required": ["location"],
            },
        },
    }
]
```

## Using tools with LLMs in streaming mode

Tools can be also passed to LLMs in streaming mode. If LLM decides to use tools then tool calls will be available in ```tool_calls``` field of the response and there will be no text output stream. If model decides not to use tools then ```tool_calls``` field won't be present and text output stream will be returned as usual:

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    query = "Tell me about the temperature in San Francisco."
    prompt = LLMPrompt(QueryWithContext(query=query))
    response = llm.generate_streaming(prompt, tools=[get_weather])
    async for resp in response:
        print(resp)

asyncio.run(main())
```

## Using tools with local LLMs

Using tools in local LLMs is not supported - any tools passed as arguments to local LLMs are ignored.