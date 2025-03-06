# How to use LLMs with Ragbits

This guide will walk you through configuring and using both local and remote LLMs in Ragbits. It covers initializing models, calling LLM classes using Prompts and raw string inputs, and handling different response formats.

## Setting up and using a remote LLMs

To interact with a remote LLM (e.g., OpenAI, Azure, or other providers), provide an API key and specify the endpoint. Ragbits uses [LiteLLM](https://docs.litellm.ai/) as an abstraction layer, allowing you to call models from multiple providers seamlessly. You can see the full list of supported providers [here](https://docs.litellm.ai/docs/providers).

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    response = await llm.generate("Tell me a joke.")
    print(response)

asyncio.run(main())
```

With LiteLLM, you can switch between different LLM providers by changing the `model_name` parameter and configuring authentication accordingly. See the [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for details on calling models from different providers.

## Configuring LLM Options

LLMs in Ragbits allow you to customize the behavior of the model using various options. These options are passed during initialization or when calling the [`generate`](ragbits.core.llms.LLM.generate) method.

### LiteLLM Options

The `LiteLLMOptions` class provides options for remote LLMs, aligning with the LiteLLM API. These options allow you to control the behavior of models from various providers. Each of the option is described in the [LiteLLM documentation](https://docs.litellm.ai/docs/completion/input).

Example usage:
```python
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions

options = LiteLLMOptions(
    temperature=0.5,
    max_tokens=150,
    top_p=0.8,
    stop=["\n"]
)

llm = LiteLLM(model_name="gpt-4o-2024-08-06", default_options=options)
response = llm.generate("Write a short story about a robot learning to paint.")
print(response)
```

## Using Local LLMs

For guidance on setting up and using local models in Ragbits, refer to the [Local LLMs Guide](https://ragbits.deepsense.ai/how-to/use_local_llms/).

# Calling LLM Classes with prompts, raw strings and conversations

Ragbits provides a flexible way to interact with LLMs by allowing you to use [`Prompt`](https://ragbits.deepsense.ai/api_reference/core/prompt/#ragbits.core.prompt.Prompt) instances, raw strings, or conversation formats (like OpenAI's chat format) when calling the [`generate`](ragbits.core.llms.LLM.generate) method. This section explains how to use these different input types effectively.


## Using prompts with LLMs

Prompts in Ragbits are powerful tools for structuring inputs and outputs when interacting with LLMs. They allow you to define **system prompts**, **user prompts**, and even **structured output formats** using Pydantic models. For more details on using prompts, check out the [Prompting Guide](https://ragbits.deepsense.ai/how-to/use_prompting/). For more advanced use cases, such as using images in prompts, check out the guide: [How to define and use image prompts in Ragbits](../how-to/core/use_images_in_prompts.md).

```python
from ragbits.core.prompt import Prompt


class JokePrompt(Prompt):
    """
    A prompt that generates jokes.
    """

    system_prompt = """
    You are a joke generator. The jokes you generate should be funny and not offensive.
    """

    user_prompt = """Tell me a joke."""
```

Passing the prompt to a model is then as simple as:

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    static_prompt = JokePrompt()
    print(await llm.generate(static_prompt))

asyncio.run(main())
```

## Using Raw Strings with LLMs

For simpler use cases, you can directly pass a raw string to the [`generate`](ragbits.core.llms.LLM.generate) method. This is useful when you don't need the additional structure provided by prompts.

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    response = await llm.generate("Tell me a fun fact about space.")
    print(response)

asyncio.run(main())
```

## Using Chat Format with LLMs

Ragbits also supports OpenAI-style chat formats, where you can pass a list of message dictionaries to the [`generate`](ragbits.core.llms.LLM.generate) method. This is useful for conversational applications.

```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM(model_name="gpt-4o-2024-08-06")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    response = await llm.generate(messages)
    print(response)

asyncio.run(main())
```