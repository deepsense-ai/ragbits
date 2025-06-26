"""
Ragbits Document Search Example: Chroma

This example demonstrates how to use the `DocumentSearch` class to search for documents with a more advanced setup.
We will use the `LiteLLMEmbedder` class to embed the documents and the query, the `ChromaVectorStore` class to store
the embeddings.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/chroma.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[chroma]",
# ]
# ///

import asyncio

from chromadb import EphemeralClient

from ragbits.core.audit import set_trace_handlers
from ragbits.core.embeddings.dense import LiteLLMEmbedder, LiteLLMEmbedderOptions
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore
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
        default_options=LiteLLMEmbedderOptions(
            dimensions=1024,
            timeout=1000,
        ),
    )
    vector_store = ChromaVectorStore(
        client=EphemeralClient(),
        index_name="jokes",
        default_options=VectorStoreOptions(
            k=10,
            score_threshold=0.88,
        ),
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
        score_threshold=0.4,
    )
    options = DocumentSearchOptions(vector_store_options=vector_store_options)
    results = await document_search.search(query, options)

    print()
    print(f"Documents similar to: {query}")
    print([element.text_representation for element in results])


if __name__ == "__main__":
    asyncio.run(main())
