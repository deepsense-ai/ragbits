"""
Ragbits Document Search Example: Multimodal Embeddings

This example demonstrates how to use the `DocumentSearch` to index and search for images and text documents.

It employes the "multimodalembedding" from VertexAI. In order to use it, make sure that you are
logged in to Google Cloud (using the `gcloud auth login` command) and that you have the necessary permissions.

The script performs the following steps:
    1. Create a list of example documents.
    2. Initialize the `VertexAIMultimodelEmbeddings` class (which uses the VertexAI multimodal embeddings).
    3. Initialize the `InMemoryVectorStore` class, which stores the embeddings for the duration of the script.
    4. Initialize the `DocumentSearch` class with the embedder and the vector store.
    5. Ingest the documents into the `DocumentSearch` instance.
    6. List all embeddings in the vector store.
    7. Search for documents using a query.
    8. Print the search results.

To run the script, execute the following command:

    ```bash
    uv run python examples/document-search/multimodal.py
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

from ragbits.core import audit
from ragbits.core.embeddings.vertex_multimodal import VertexAIMultimodelEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.sources.local import LocalFileSource
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.dummy import DummyImageProvider

audit.set_trace_handlers("cli")

IMAGES_PATH = Path(__file__).parent / "images"


def jpg_example(file_name: str) -> DocumentMeta:
    """
    Create a document from a JPG file in the images directory.
    """
    return DocumentMeta(document_type=DocumentType.JPG, source=LocalFileSource(path=IMAGES_PATH / file_name))


documents = [
    jpg_example("bear.jpg"),
    jpg_example("game.jpg"),
    jpg_example("tree.jpg"),
    DocumentMeta.create_text_document_from_literal("A beautiful teady bear."),
    DocumentMeta.create_text_document_from_literal("The constitution of the United States."),
]


async def main() -> None:
    """
    Run the example.
    """
    embedder = VertexAIMultimodelEmbeddings()
    vector_store = InMemoryVectorStore()
    router = DocumentProcessorRouter.from_config(
        {
            # For this example, we want to skip OCR and make sure
            # that we test direct image embeddings.
            DocumentType.JPG: DummyImageProvider(),
        }
    )

    document_search = DocumentSearch(
        embedder=embedder,
        vector_store=vector_store,
        document_processor_router=router,
    )

    await document_search.ingest(documents)

    all_embeddings = await vector_store.list()
    for embedding in all_embeddings:
        print(f"Embedding: {embedding.metadata['document_meta']}")
        print()

    results = await document_search.search("Fluffy teady bear")
    print("Results for 'Fluffy teady bear toy':")
    for result in results:
        document = await result.document_meta.fetch()
        print(f"Type: {result.element_type}, Location: {document.local_path}, Text: {result.text_representation}")


if __name__ == "__main__":
    asyncio.run(main())
