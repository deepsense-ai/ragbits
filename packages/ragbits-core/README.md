# Ragbits Core

Ragbits Core is a collection of utilities and tools that are used across all Ragbits packages. It includes fundamentals, such as utilities for logging, configuration, prompt creation, classes for comunicating with LLMs, embedders, vector stores, and more.

## Installation

```sh
pip install ragbits-core
```

## Quick Start

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt
from ragbits.core.llms.litellm import LiteLLM


class Dog(BaseModel):
    breed: str
    age: int
    temperament: str

class DogNamePrompt(Prompt[Dog, str]):
    system_prompt = """
    You are a dog name generator. You come up with funny names for dogs given the dog details.
    """

    user_prompt = """
    The dog is a {breed} breed, {age} years old, and has a {temperament} temperament.
    """

async def main() -> None:
    llm = LiteLLM("gpt-4o")
    dog = Dog(breed="Golden Retriever", age=3, temperament="friendly")
    prompt = DogNamePrompt(dog)
    response = await llm.generate(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation
* [Quickstart 1: Working with Prompts and LLMs](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/)
* [How-To Guides - Core](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/)
* [API Reference - Core](https://ragbits.deepsense.ai/api_reference/core/prompt/)
