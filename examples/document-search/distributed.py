"""
Ragbits Document Search Example: Qdrant Distributed Ingest

This example is based on the "Qdrant" example, but it demonstrates how to ingest documents in a distributed manner.
The distributed ingest is provided by "RayDistributedIngestStrategy" which uses Ray to parallelize the ingest process.

The script performs the following steps:

    1. Create a list of documents.
    2. Initialize the `LiteLLMEmbedder` class with the OpenAI `text-embedding-3-small` embedding model.
    3. Initialize the `QdrantVectorStore` class with a `AsyncQdrantClient` HTTP instance and an index name.
    4. Initialize the `RayDistributedIngestStrategy` class with a standard params.
    5. Initialize the `DocumentSearch` class with the embedder and the vector store.
    6. Ingest the documents into the `DocumentSearch` instance using Ray distributed strategy.
    7. Search for documents using a query.
    8. Print the search results.

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/distributed.py
    ```

The script ingests data to the Qdrant instance running on `http://localhost:6333`. The recommended way
to run it is using the official Docker image:

    1. Run Qdrant Docker container:

        ```bash
        docker run -p 6333:6333 qdrant/qdrant
        ```

    2. Open Qdrant dashboard in your browser:

        ```
        http://localhost:6333/dashboard
        ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search[ray]",
#     "ragbits-core",
# ]
# ///

import asyncio

from qdrant_client import AsyncQdrantClient

from ragbits.core import audit
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.ingestion.strategies import RayDistributedIngestStrategy

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
    )
    vector_store = QdrantVectorStore(
        client=AsyncQdrantClient(
            host="localhost",
            port=6333,
        ),
        index_name="jokes",
        embedder=embedder,
    )
    ingest_strategy = RayDistributedIngestStrategy()
    document_search = DocumentSearch(
        vector_store=vector_store,
        ingest_strategy=ingest_strategy,
    )

    await document_search.ingest(documents)

    results = await document_search.search("I'm boiling my water and I need a joke")
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
