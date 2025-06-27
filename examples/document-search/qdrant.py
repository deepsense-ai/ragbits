"""
Ragbits Document Search Example: Qdrant

This example demonstrates how to use the `DocumentSearch` class to search for documents with a more advanced setup.
We will use the `LiteLLMEmbedder` class to embed the documents and the query, the `QdrantVectorStore` class to store
the embeddings.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/qdrant.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[qdrant]",
# ]
# ///

import asyncio

from qdrant_client import AsyncQdrantClient

from ragbits.core.audit import set_trace_handlers
from ragbits.core.embeddings.dense import LiteLLMEmbedder
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch, DocumentSearchOptions
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
    vector_store = QdrantVectorStore(
        client=AsyncQdrantClient(location=":memory:"),
        index_name="jokes",
        embedder=embedder,
    )
    document_search = DocumentSearch(
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    all_documents = await vector_store.list()

    print()
    print("All documents:")
    print([doc.metadata["content"] for doc in all_documents])

    query = "I'm boiling my water and I need a joke"
    vector_store_options = VectorStoreOptions(
        k=2,
        score_threshold=0.6,
    )
    options = DocumentSearchOptions(vector_store_options=vector_store_options)
    results = await document_search.search(query, options=options)

    print()
    print(f"Documents similar to: {query}")
    print([element.text_representation for element in results])


if __name__ == "__main__":
    asyncio.run(main())
