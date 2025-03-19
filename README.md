<div align="center">

<h1>Ragbits</h1>

*Building blocks for rapid development of GenAI applications*

[Documentation](https://ragbits.deepsense.ai) | [Contact](https://deepsense.ai/contact/)

[![PyPI - License](https://img.shields.io/pypi/l/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Version](https://img.shields.io/pypi/v/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ragbits)](https://pypi.org/project/ragbits)

</div>

---

## Features

### 🔨 Build Reliable & Scalable GenAI Apps
- **Swap LLMs anytime** – Switch between [100+ LLMs via LiteLLM](https://ragbits.deepsense.ai/how-to/llms/use_llms/) or run [local models](https://ragbits.deepsense.ai/how-to/llms/use_llms/#using-local-llms).
- **Type-safe LLM calls** – Use Python generics to [enforce strict type safety](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/#how-to-configure-prompts-output-data-type) in model interactions.
- **Bring your own vector store** – Connect to [Qdrant](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), [PgVector](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.pgvector.PgVectorStore), and more with built-in support.
- **Developer tools included** – [Manage vector stores](https://ragbits.deepsense.ai/cli/main/#ragbits-vector-store), query pipelines, and [test prompts from your terminal](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/#testing-the-prompt-from-the-cli).
- **Modular installation** – Install only what you need, reducing dependencies and improving performance.

### 📚 Fast & Flexible RAG Processing
- **Ingest 20+ formats** – Process PDFs, HTML, spreadsheets, presentations, and more. Process data using [unstructured](https://unstructured.io/) or create a custom provider.
- **Handle complex data** – Extract tables, images, and structured content with built-in VLMs support.
- **Connect to any data source** – Use prebuilt connectors for S3, GCS, Azure, or implement your own.
- **Scale ingestion** – Process large datasets quickly with [Ray-based parallel processing](https://ragbits.deepsense.ai/how-to/document_search/distributed_ingestion/#how-to-ingest-documents-in-a-distributed-fashion).

### 🚀 Deploy & Monitor with Confidence
- **Real-time observability** – Track performance with [OpenTelemetry](https://ragbits.deepsense.ai/how-to/project/use_tracing/#opentelemetry-trace-handler) and [CLI insights](https://ragbits.deepsense.ai/how-to/project/use_tracing/#cli-trace-handler).
- **Built-in testing** – Validate prompts [with promptfoo](https://ragbits.deepsense.ai/how-to/prompts/promptfoo/) before deployment.
- **Auto-optimization** – Continuously evaluate and refine model performance.
- **Visual testing UI (Coming Soon)** – Test and optimize applications with a visual interface.


## What's Included?

- [X] **[Core](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-core)** - Fundamental tools for working with prompts and LLMs.
- [X] **[Document Search](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-document-search)** - Handles vector search to retrieve relevant documents.
- [X] **[CLI](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-cli)** - The `ragbits` shell command, enabling tools such as GUI prompt management.
- [x] **[Guardrails](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-guardrails)** - Ensures response safety and relevance.
- [x] **[Evaluation](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-evaluate)** - Unified evaluation framework for Ragbits components.
- [ ] **Flow Controls** - Manages multi-stage chat flows for performing advanced actions *(coming soon)*.
- [ ] **Structured Querying** - Queries structured data sources in a predictable manner *(coming soon)*.
- [ ] **Caching** - Adds a caching layer to reduce costs and response times *(coming soon)*.

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

## How Ragbits documentation is organized

- [Quickstart](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/) - Get started with Ragbits in a few minutes
- [How-to guides](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/) - Learn how to use Ragbits in your projects
- [CLI](https://ragbits.deepsense.ai/cli/main/) - Learn how to run Ragbits in your terminal
- [API reference](https://ragbits.deepsense.ai/api_reference/core/prompt/) - Explore the underlying API of Ragbits


## License

Ragbits is licensed under the [MIT License](https://github.com/deepsense-ai/ragbits/tree/main/LICENSE).

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](https://github.com/deepsense-ai/ragbits/tree/main/CONTRIBUTING.md) for more information.
