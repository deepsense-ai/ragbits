---
hide:
  - navigation
---

# Ragbits docs

<style>
.md-content .md-typeset #ragbits-docs { display: none; }

#main-header {
    font-size: 3em;
    margin-bottom: 0;
}
</style>

<h1 align="center" id="main-header">🐰 ragbits</h1>

<p align="center">
  <em size="">Building blocks for rapid development of GenAI applications.</em>
</p>

<div align="center">

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - License" src="https://img.shields.io/pypi/l/ragbits">
</a>

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/ragbits">
</a>

<a href="https://pypi.org/project/ragbits" target="_blank">
  <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/ragbits">
</a>

</div>
---

## Features


### 🔨 Build Reliable & Scalable GenAI Apps
- **Swap LLMs anytime** – Switch between [100+ LLMs via LiteLLM](https://ragbits.deepsense.ai/how-to/core/use_llms/) or run [local models](https://ragbits.deepsense.ai/how-to/core/use_llms/#using-local-llms).
- **Type-safe LLM calls** – Use Python generics to [enforce strict type safety](https://ragbits.deepsense.ai/how-to/core/use_prompting/#how-to-configure-prompts-output-data-type) in model interactions.
- **Bring your own vector store** – Connect to [Qdrant](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), [PgVector](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.pgvector.PgVectorStore), and more with built-in support.
- **Developer tools included** – [Manage vector stores](https://ragbits.deepsense.ai/cli/main/#ragbits-vector-store), query pipelines, and [test prompts from your terminal](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/#testing-the-prompt-from-the-cli).
- **Modular installation** – Install only what you need, reducing dependencies and improving performance.

### 📚 Fast & Flexible RAG Processing
- **Ingest 20+ formats** – Process PDFs, HTML, spreadsheets, presentations, and more. Process data using [unstructured](https://unstructured.io/) or create a custom provider.
- **Handle complex data** – Extract tables, images, and structured content with built-in VLM support.
- **Connect to any data source** – Use prebuilt connectors for S3, GCS, Azure, or implement your own.
- **Scale ingestion** – Process large datasets quickly with [Ray-based parallel processing](https://ragbits.deepsense.ai/how-to/document_search/distributed_ingestion/#how-to-ingest-documents-in-a-distributed-fashion).

### 🚀 Deploy & Monitor with Confidence
- **Real-time observability** – Track performance with [OpenTelemetry](https://ragbits.deepsense.ai/how-to/core/use_tracing/#opentelemetry-trace-handler) and [CLI insights](https://ragbits.deepsense.ai/how-to/core/use_tracing/#opentelemetry-trace-handler).
- **Built-in testing** – Validate prompts [with promptfoo](https://ragbits.deepsense.ai/how-to/core/promptfoo/) before deployment.
- **Auto-optimization** – Continuously evaluate and refine model performance.
- **Visual testing UI (Coming Soon)** – Test and optimize applications with a visual interface.

## Installation

You can install the latest version of **Ragbits** using pip:

```bash
pip install ragbits
```

Additionally, you can install one of the extensions to **Ragbits**:

- `ragbits[document-search]` - provides tools for building document search applications.

## Quickstart

To build the simplest documents search, you can use the following code snippet:

```python
import asyncio

from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.vector_stores import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

documents = [
    DocumentMeta.create_text_document_from_literal("RIP boiled water. You will be mist."),
    DocumentMeta.create_text_document_from_literal(
        "Why doesn't James Bond fart in bed? Because it would blow his cover."
    ),
    DocumentMeta.create_text_document_from_literal(
        "Why programmers don't like to swim? Because they're scared of the floating points."
    ),
]


async def main():
    document_search = DocumentSearch(embedder=LiteLLMEmbedder(), vector_store=InMemoryVectorStore())

    await document_search.ingest(documents)

    return await document_search.search("I'm boiling my water and I need a joke")


if __name__ == "__main__":
    print(asyncio.run(main()))
```

## How Ragbits documentation is organized

- [Quickstart](quickstart/quickstart1_prompts.md) - Get started with Ragbits in a few minutes
- [How-to guides](how-to/core/use_prompting.md) - Learn how to use Ragbits in your projects
- [CLI](cli/main.md) - Learn how to manage Ragbits from the command line
- [API reference](api_reference/core/prompt.md) - Explore the underlying API of Ragbits