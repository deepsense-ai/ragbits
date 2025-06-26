"""
Ragbits Document Search Example: Basic

This example demonstrates how to use the `DocumentSearch` class to search for documents with a minimal setup.
We will use the `LiteLLMEmbedder` class to embed the documents and the query and the `InMemoryVectorStore` class
to store the embeddings.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/basic.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core",
# ]
# ///

import asyncio

from ragbits.core.audit import set_trace_handlers
from ragbits.core.embeddings.dense import LiteLLMEmbedder
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

set_trace_handlers("cli")

documents = [
    DocumentMeta.from_literal(
        """
        RIP boiled water. You will be mist.
        """
    ),
    DocumentMeta.from_literal(
        """
        Why doesn't James Bond fart in bed? Because it would blow his cover.
        """
    ),
    DocumentMeta.from_literal(
        """
        Why programmers don't like to swim? Because they're scared of the floating points.
        """
    ),
    DocumentMeta.from_literal(
        """
        This one is completely unrelated.
        """
    ),
]


async def main() -> None:
    """
    Run the example.
    """
    embedder = LiteLLMEmbedder(
        model_name="text-embedding-3-small",
    )
    vector_store = InMemoryVectorStore(embedder=embedder)
    document_search = DocumentSearch(
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
