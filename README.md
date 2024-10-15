# Ragbits

*A stack of ready-to-use libraries for building chatbots and other LLM-powered applications*

[![PyPI - License](https://img.shields.io/pypi/l/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Version](https://img.shields.io/pypi/v/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ragbits)](https://pypi.org/project/ragbits)

## What's Included?

- [X] **[Core](packages/ragbits-core)** - Fundamental tools for working with prompts and LLMs.
- [X] **[Document Search](packages/ragbits-document-search)** - Handles vector search to retrieve relevant documents.
- [X] **[CLI](packages/ragbits-cli)** - The `ragbits` shell command, enabling tools such as GUI prompt management.
- [ ] **Flow Controls** - Manages multi-stage chat flows for performing advanced actions (coming soon).
- [ ] **Structured Querying** - Queries structured data sources in a predictable manner (coming soon).
- [ ] **Caching** - Adds a caching layer to reduce costs and response times (coming soon).
- [ ] **Observability & Audit** - Tracks user queries and events for easier troubleshooting (coming soon).
- [ ] **Guardrails** - Ensures response safety and relevance (coming soon).

## Installation

To use the complete Ragbits stack, install the `ragbits` package:

```sh
pip install ragbits
```

Alternatively, you can use individual components of the stack by installing their respective packages: `ragbits-core`, `ragbits-document-search`, `ragbits-cli`.

## Quickstart

First, create a prompt and a model for the data used in the prompt:

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

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
```

Next, create an instance of the LLM and the prompt:

```python
from ragbits.core.llms.litellm import LiteLLM

llm = LiteLLM("gpt-4o")
example_dog = Dog(breed="Golden Retriever", age=3, temperament="friendly")
prompt = DogNamePrompt(example_dog)
```

Finally, generate a response from the LLM using the prompt:

```python
response = await llm.generate(prompt)
print(f"Generated dog name: {response}")
```

<!--
TODO:
Add links to quickstart guides for individual packages, demonstrating how to extend this with their functionality.
Add a link to the full tutorial.
-->

## Documentation

Full documentation is available at [ragbits.deepsense.ai/](https://ragbits.deepsense.ai/).

## License

Ragbits is licensed under the [MIT License](LICENSE).

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for more information.
