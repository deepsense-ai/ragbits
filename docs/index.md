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

### 🔨 Build future-proof, consistent GenAI applications

- 🔮 **Hot-swappable LLMs**: Future-proof your applications by easily swapping out the underlying LLMs. ragbits supports [over 100+ LLMs through LiteLLM](https://ragbits.deepsense.ai/how-to/core/use_llms/) or allows you to run [local models](https://ragbits.deepsense.ai/how-to/core/use_llms/#using-local-llms).
- 🎯 **Type-safe LLM calls**: Ensure your LLM calls remain type-safe and consistent, no matter the model. [Leverage Python generics for guaranteed correctness](https://ragbits.deepsense.ai/how-to/core/use_prompting/#how-to-configure-prompts-output-data-type).
- 💾 **Bring your favorite VectorStore**: ragbits supports various vector stores out-of-the-box, including [Qdrant](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), [PgVector](https://ragbits.deepsense.ai/api_reference/core/vector-stores/#ragbits.core.vector_stores.qdrant.QdrantVectorStore), and more. Easily switch between VectorStores to match your requirements.
- 🛠 **Powerful CLI**: Effortlessly execute commands, browse vector stores, run queries against RAG pipelines, and [test prompts directly](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/#testing-the-prompt-from-the-cli) from your terminal.
- 🤏 **Install only what you need**: ragbits is designed to be modular, allowing you to install only the components you actually require. Say goodbye to unnecessary, bulky dependencies that degrade application performance.

### 📚 RAGs in hours - not days

- 📃 **Ingest 20+ document formats**: PDF, HTML, spreadsheets, presentations, and many other formats are supported natively. Process data using [unstructured](https://unstructured.io) or create a custom provider.
- 🖼 **Understands complex data**: Built-in support for tables, images, and more. Agentic document processing using VLM.
- 🔌 **Easily connect data sources**: Quickly integrate your data sources using built-in connectors with native support for [S3, GCS, Azure](), and more. If your particular source isn't included, simply implement a straightforward interface.
- 🚄 **Rapid ingestion of massive payloads**: Leverage Ray-based parallel ingestion to [process massive datasets fast](https://ragbits.deepsense.ai/how-to/document_search/distributed_ingestion/#how-to-ingest-documents-in-a-distributed-fashion).

### 🚀 Deploy with ease and confidence

- 👀 **Built-in observability**: Monitor your applications effortlessly with integrated observability tools. ragbits incorporates integrations [with OpenTelemetry](https://ragbits.deepsense.ai/how-to/core/use_tracing/#opentelemetry-trace-handler), complemented by [beautiful CLI outputs](https://ragbits.deepsense.ai/how-to/core/use_tracing/#opentelemetry-trace-handler).
- ✅ **Integrated testing & evaluation**: Built-in [integration with promptfoo](https://ragbits.deepsense.ai/how-to/core/promptfoo/) to facilitate comprehensive prompt testing and evaluation.
- ♻️ **Evaluation and auto-optimization**: Automatically evaluate and optimize components of your application, ensuring continuous improvement in performance.
- ✨ **Coming soon—intuitive testing UI**: Visualize, test, and optimize your entire application through an intuitive, user-friendly interface (coming soon).

## Installation

You can install the latest version of **ragbits** using pip:

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