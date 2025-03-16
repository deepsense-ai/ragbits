"""
Ragbits Document Search Example: Distributed Ingest

This example is based on the "Basic" example, but it demonstrates how to ingest documents in a distributed manner.
The distributed ingestion is provided by "RayDistributedIngestStrategy" which uses Ray to parallelize the ingestion process.

The script performs the following steps:

    1. Create a list of documents.
    2. Initialize the `LiteLLMEmbedder` class with the OpenAI `text-embedding-3-small` embedding model.
    3. Initialize the `InMemoryVectorStore` class.
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance in a distributed manner.
    6. Search for documents using a query.
    7. Print the search results.


    docker run -p 6333:6333 qdrant/qdrant

To run the script, execute the following command:

    ```bash
    uv run examples/document-search/distributed.py
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
import random

from qdrant_client import AsyncQdrantClient

from ragbits.core import audit
from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.vector_stores.qdrant import QdrantVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy

# ray.init()

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


class Test(BaseProvider):
    """
    A provider handling html files from Hexagon Community forum.
    """

    # Change to JSON after ragbits bump:
    SUPPORTED_DOCUMENT_TYPES = {
        DocumentType.TXT,
    }

    @audit.traceable
    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Processes the Hexagon Community post.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            DocumentTypeNotSupportedError: If the document type is not supported.
        """
        self.validate_document_type(document_meta.document_type)
        document = await document_meta.fetch()
        content = document.local_path.read_text()
        # await asyncio.sleep(random.choice([1, 2, 3]))
        if random.choice([True, False]):
            raise ValueError("Dupa")
        return [TextElement(content=content, document_meta=document_meta) for _ in range(10)]
        # return [IntermediateImageElement(image_bytes=b"addad", ocr_extracted_text="xd", document_meta=document_meta) for _ in range(10)]


async def main() -> None:
    """
    Run the example.
    """
    embedder = LiteLLMEmbedder(
        model="text-embedding-3-small",
    )
    vector_store = QdrantVectorStore(
        embedder=embedder,
        client=AsyncQdrantClient(
            host="localhost",
            port=6333,
        ),
        index_name="jokes",
    )
    # ingest_strategy = RayDistributedIngestStrategy(3)
    ingest_strategy = BatchedIngestStrategy(3)
    parser_router = DocumentProcessorRouter(
        {
            # Change to JSON after ragbits bump:
            DocumentType.TXT: Test(),
        }
    )
    document_search = DocumentSearch(
        vector_store=vector_store,
        parser_router=parser_router,
        ingest_strategy=ingest_strategy,
    )
    import rich

    audit.set_trace_handlers("cli")
    rich.print(await document_search.ingest(documents))

    # results = await document_search.search("I'm boiling my water and I need a joke")
    # print(results)


if __name__ == "__main__":
    asyncio.run(main())
