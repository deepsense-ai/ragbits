# How to Use LLMs with Ragbits

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

## Setting up and using a local models
To use a local LLMs, you need to install the 'local' extra requirements:

```bash
pip install ragbits[local]
```

Local LLMs in Ragbits use [`AutoModelForCausalLM`](https://huggingface.co/docs/transformers/model_doc/auto#transformers.AutoModelForCausalLM) with `device_map="auto"`. This setting automatically fills all available space on the GPU(s) first, then the CPU, and finally the hard drive (the absolute slowest option) if there is still not enough memory. See the [Hugging Face documentation](https://huggingface.co/docs/transformers/model_doc/auto#transformers.AutoModelForCausalLM) for more details.

Using a local model is as simple as:
```python
from ragbits.core.llms.local import LocalLLM

local_llm = LocalLLM(model_name="mistral-7b")
response = local_llm.generate("Tell me a science fact.")
print(response)
```

The `model_name` parameter can be specified in several ways:
- a string representing the model ID of a pretrained model hosted on Hugging Face Hub, such as `"mistral-7b"`,
- a path to a directory containing a model, e.g., `"./my_model_directory/"`,
- a path or URL to a saved configuration JSON file, e.g., `"./my_model_directory/configuration.json"`.

## Configuring LLM Options

Both local and remote LLMs in Ragbits allow you to customize the behavior of the model using various options. These options are passed during initialization or when calling the `generate` method.

### Local LLM Options

The `LocalLLMOptions` class provides a set of parameters to fine-tune the behavior of local LLMs. These options described in the [HuggingFace documentation](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation).

Example usage:
```python
from ragbits.core.llms.local import LocalLLM, LocalLLMOptions

options = LocalLLMOptions(
    temperature=0.7,
    max_new_tokens=100,
    do_sample=True,
    top_p=0.9
)

local_llm = LocalLLM(model_name="mistral-7b", default_options=options)
response = local_llm.generate("Explain quantum mechanics in simple terms.")
print(response)
```

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

# Calling LLM Classes with prompts, raw strings and conversations

Ragbits provides a flexible way to interact with LLMs by allowing you to use [`Prompt`](https://ragbits.deepsense.ai/api_reference/core/prompt/#ragbits.core.prompt.Prompt) instances, raw strings, or conversation formats (like OpenAI's chat format) when calling the `generate` method. This section explains how to use these different input types effectively.


## Using prompts with LLMs

Prompts in Ragbits are powerful tools for structuring inputs and outputs when interacting with LLMs. They allow you to define **system prompts**, **user prompts**, and even **structured output formats** using Pydantic models. For more details on using prompts, check out the [Prompting Guide](https://ragbits.deepsense.ai/how-to/use_prompting/).

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

For simpler use cases, you can directly pass a raw string to the `generate` method. This is useful when you don't need the additional structure provided by prompts.

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

Ragbits also supports OpenAI-style chat formats, where you can pass a list of message dictionaries to the `generate` method. This is useful for conversational applications.

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