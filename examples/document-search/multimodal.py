"""
Ragbits Document Search Example: Multimodal search

This example demonstrates how to use the `DocumentSearch` to index and search for images and text documents.

It employes the "multimodalembedding" from VertexAI. In order to use it, make sure that you are
logged in to Google Cloud (using the `gcloud auth login` command) and that you have the necessary permissions.

The script performs the following steps:
    1. Create a list of example documents.
    2. Initialize the `VertexAIMultimodelEmbedder` class (which uses the VertexAI multimodal embeddings).
    3. Initialize `HybridSearchVectorStore` with two `InMemoryVectorStore` instances (one for text and one for images).
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance.
    6. List all embeddings in the vector store.
    7. Search for documents using a query.
    8. Print the search results.

To run the script, execute the following command:

    ```bash
    uv run python examples/document-search/multimodal_basic.py
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
from pathlib import Path

from ragbits.core.embeddings.vertex_multimodal import VertexAIMultimodelEmbedder
from ragbits.core.vector_stores.base import EmbeddingType
from ragbits.core.vector_stores.hybrid import HybridSearchVectorStore
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.sources import LocalFileSource
from ragbits.document_search.ingestion.parsers.base import ImageDocumentParser
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter

IMAGES_PATH = Path(__file__).parent / "images"

documents = [
    DocumentMeta(document_type=DocumentType.JPG, source=LocalFileSource(path=IMAGES_PATH / "bear.jpg")),
    DocumentMeta(document_type=DocumentType.JPG, source=LocalFileSource(path=IMAGES_PATH / "game.jpg")),
    DocumentMeta(document_type=DocumentType.JPG, source=LocalFileSource(path=IMAGES_PATH / "tree.jpg")),
    DocumentMeta.create_text_document_from_literal("A beautiful teady bear."),
    DocumentMeta.create_text_document_from_literal("The constitution of the United States."),
]


async def main() -> None:
    """
    Run the example.
    """
    # Has to support both text and image embeddings
    embedder = VertexAIMultimodelEmbedder()

    # You can replace InMemoryVectorStore with other vector store implementations
    vector_store_text = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.TEXT)
    vector_store_image = InMemoryVectorStore(embedder=embedder, embedding_type=EmbeddingType.IMAGE)

    vector_store_hybrid = HybridSearchVectorStore(vector_store_text, vector_store_image)

    # For this example, we want to skip OCR and make sure that we test direct image embeddings.
    parser_router = DocumentParserRouter({DocumentType.JPG: ImageDocumentParser()})

    document_search = DocumentSearch(
        vector_store=vector_store_hybrid,
        parser_router=parser_router,
    )

    await document_search.ingest(documents)

    all_entries = await vector_store_hybrid.list()
    for entry in all_entries:
        print(f"ID: {entry.id}")
        print(f"Document: {entry.metadata['document_meta']}")
        print()

    results = await document_search.search("Fluffy teady bear")
    print("Results for 'Fluffy teady bear':")
    for result in results:
        document = await result.document_meta.fetch()
        print(f"Type: {result.element_type}, Location: {document.local_path}, Text: {result.text_representation}")


if __name__ == "__main__":
    asyncio.run(main())
