"""
Ragbits Document Search Example: Basic

This example demonstrates how to use the `DocumentSearch` class to search for documents with a minimal setup.
We will use the `LiteLLMEmbeddings` class to embed the documents and the query and the `InMemoryVectorStore` class
to store the embeddings.

The script performs the following steps:

    1. Create a list of documents.
    2. Initialize the `LiteLLMEmbeddings` class with the OpenAI `text-embedding-3-small` embedding model.
    3. Initialize the `InMemoryVectorStore` class.
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance.
    6. Search for documents using a query.
    7. Print the search results.

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

from ragbits.core.embeddings.litellm import LiteLLMEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta

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
    embedder = LiteLLMEmbeddings(
        model="text-embedding-3-small",
    )
    vector_store = InMemoryVectorStore()
    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
    )

    await document_search.ingest(documents)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
