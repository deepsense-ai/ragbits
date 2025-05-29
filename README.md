<div align="center">

<h1>Ragbits</h1>

*Building blocks for rapid development of GenAI applications*

[Homepage](https://deepsense.ai/rd-hub/ragbits/) | [Documentation](https://ragbits.deepsense.ai) | [Contact](https://deepsense.ai/contact/)

[![PyPI - License](https://img.shields.io/pypi/l/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Version](https://img.shields.io/pypi/v/ragbits)](https://pypi.org/project/ragbits)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ragbits)](https://pypi.org/project/ragbits)

</div>

---

## Features

### 🔨 Build Reliable & Scalable GenAI Apps

- **Swap LLMs anytime** – Switch between [100+ LLMs via LiteLLM](https://ragbits.deepsense.ai/how-to/llms/use_llms/) or run [local models](https://ragbits.deepsense.ai/how-to/llms/use_local_llms/).
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

## Installation

To get started quickly, you can install with:

```sh
pip install ragbits
```

This is a starter bundle of packages, containing:

- [`ragbits-core`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-core) - fundamental tools for working with prompts, LLMs and vector databases.
- [`ragbits-agents`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-agents) - abstractions for building agentic systems.
- [`ragbits-document-search`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-document-search) - retrieval and ingestion piplines for knowledge bases.
- [`ragbits-evaluate`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-evaluate) - unified evaluation framework for Ragbits components.
- [`ragbits-chat`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-chat) - full-stack infrastructure for building conversational AI applications.
- [`ragbits-cli`](https://github.com/deepsense-ai/ragbits/tree/main/packages/ragbits-cli) - `ragbits` shell command for interacting with Ragbits components.

Alternatively, you can use individual components of the stack by installing their respective packages.

## Quickstart

To build a simple vector store index using OpenAI:

```python
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

document_search = DocumentSearch(
    vector_store=InMemoryVectorStore(
        embedder=LiteLLMEmbedder(model_name="text-embedding-3-small"),
    ),
)
```

To ingest the data:

```python
import asyncio

async def run() -> None:
    await document_search.ingest("web://https://arxiv.org/pdf/1706.03762")

if __name__ == "__main__":
    asyncio.run(run())
```

To query the data:

```python
import asyncio

async def run() -> None:
    result = await document_search.search("What are the key findings or results presented in this paper?")
    print(result)

if __name__ == "__main__":
    asyncio.run(run())
```

## Rapid development

Create Ragbits projects from templates:

```sh
uvx create-ragbits-app
```

Explore `create-ragbits-app` repo [here](https://github.com/deepsense-ai/create-ragbits-app). If you have a new idea for a template, feel free to contribute!

## Documentation

- [Quickstart](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/) - Get started with Ragbits in a few minutes
- [How-to](https://ragbits.deepsense.ai/how-to/prompts/use_prompting/) - Learn how to use Ragbits in your projects
- [CLI](https://ragbits.deepsense.ai/cli/main/) - Learn how to run Ragbits in your terminal
- [API reference](https://ragbits.deepsense.ai/api_reference/core/prompt/) - Explore the underlying Ragbits API

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](https://github.com/deepsense-ai/ragbits/tree/main/CONTRIBUTING.md) for more information.

## License

Ragbits is licensed under the [MIT License](https://github.com/deepsense-ai/ragbits/tree/main/LICENSE).
