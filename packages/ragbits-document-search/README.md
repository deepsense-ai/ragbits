# Ragbits Document Search

Ragbits Document Search is a Python package that provides tools for building RAG applications. It helps ingest, index, and search documents to retrieve relevant information for your prompts.

## Installation

You can install the latest version of Ragbits Document Search using pip:

```bash
pip install ragbits-document-search
```

## Quickstart
```python
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch

async def main() -> None:
    """
    Run the example.
    """
    embedder = LiteLLMEmbedder(
        model="text-embedding-3-small",
    )
    vector_store = InMemoryVectorStore(embedder=embedder)
    document_search = DocumentSearch(
        vector_store=vector_store,
    )

    # Ingest all .txt files from the "biographies" directory
    await document_search.ingest("file://biographies/*.txt")

    # Search the documents for the query
    results = await document_search.search("When was Marie Curie-Sklodowska born?")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation
* [Quickstart 2: Adding RAG Capabilities](https://ragbits.deepsense.ai/quickstart/quickstart2_rag/)
* [How-To Guides - Document Search](https://ragbits.deepsense.ai/how-to/document_search/async_processing/)
* [API Reference - Document Search](https://ragbits.deepsense.ai/api_reference/document_search/)
