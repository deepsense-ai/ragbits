---
hide:
  - navigation
---

# ragbits docs

<style>
.md-content .md-typeset h1 { display: none; }
</style>

<div align="center" markdown="span">
  <!-- TODO: Shouldn't custom assets live in this repo too? -->
  <img alt="ragbits logo" src="./assets/ragbits.png" width="50%">
</div>

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

**ragbits** is a Python package that offers essential "bits" for building powerful Retrieval-Augmented Generation (RAG)
applications.

**ragbits** prioritizes an exceptional developer experience by providing a simple and intuitive API.
It also includes a comprehensive set of tools for seamlessly building, testing, and deploying your RAG applications
efficiently.

## Installation

You can install the latest version of **ragbits** using pip:

```bash
pip install ragbits
```

Additionally, you can install one of the extensions to **ragbits**:

- `ragbits[document-search]` - provides tools for building document search applications.

## Quickstart

To build the simplest documents search, you can use the following code snippet:

```python
import asyncio

from ragbits.core.embeddings import LiteLLMEmbeddings
from ragbits.core.vector_store import InMemoryVectorStore
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
    document_search = DocumentSearch(embedder=LiteLLMEmbeddings(), vector_store=InMemoryVectorStore())

    await document_search.ingest(documents)

    return await document_search.search("I'm boiling my water and I need a joke")


if __name__ == "__main__":
    print(asyncio.run(main()))
```

## How ragbits documentation is organized

- [Quickstart](https://ragbits.deepsense.ai/quickstart/quickstart1_prompts/) - Get started with ragbits in a few minutes
- [How-to guides](https://ragbits.deepsense.ai/how-to/use_prompting/) - Learn how to use ragbits in your projects
- [CLI](https://ragbits.deepsense.ai/cli/main/) - Learn how to run ragbits in your terminal
- [API reference](https://ragbits.deepsense.ai/api_reference/core/prompt/) - Explore the underlying API of ragbits