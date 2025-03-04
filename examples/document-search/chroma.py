"""
Ragbits Document Search Example: Chroma

This example demonstrates how to use the `DocumentSearch` class to search for documents with a more advanced setup.
We will use the `LiteLLMEmbedder` class to embed the documents and the query, the `ChromaVectorStore` class to store
the embeddings.

The script performs the following steps:

    1. Create a list of documents.
    2. Initialize the `LiteLLMEmbedder` class with the OpenAI `text-embedding-3-small` embedding model.
    3. Initialize the `ChromaVectorStore` class with a `EphemeralClient` instance and an index name.
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance.
    6. List all documents in the vector store.
    7. Search for documents using a query.
    8. Print the list of all documents and the search results.

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

from ragbits.core import audit
from ragbits.core.embeddings.litellm import LiteLLMEmbedder, LiteLLMEmbedderOptions
from ragbits.core.vector_stores.chroma import ChromaVectorStore, ChromaVectorStoreOptions
from ragbits.document_search import DocumentSearch, SearchConfig
from ragbits.document_search.documents.document import DocumentMeta

audit.set_trace_handlers("cli")

documents = [
    DocumentMeta.create_text_document_from_literal(
        """
        RIP boiled water. You will be mist.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why doesn't James Bond fart in bed? Because it would blow his cover.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
        """
        Why programmers don't like to swim? Because they're scared of the floating points.
        """
    ),
    DocumentMeta.create_text_document_from_literal(
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
        model="text-embedding-3-small",
        default_options=LiteLLMEmbedderOptions(
            dimensions=1024,
            timeout=1000,
        ),
    )
    vector_store = ChromaVectorStore(
        client=EphemeralClient(),
        index_name="jokes",
        default_options=ChromaVectorStoreOptions(
            k=10,
            max_distance=0.22,
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
    vector_store_kwargs = {
        "k": 2,
        "max_distance": 0.6,
    }
    results = await document_search.search(
        query,
        config=SearchConfig(vector_store_kwargs=vector_store_kwargs),
    )

    print()
    print(f"Documents similar to: {query}")
    print([element.text_representation for element in results])


if __name__ == "__main__":
    asyncio.run(main())
