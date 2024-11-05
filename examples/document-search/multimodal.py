# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-document-search",
#     "ragbits-core[litellm]",
# ]
# ///
import asyncio
from pathlib import Path

from ragbits.core.embeddings.vertex_multimodal import VertexAIMultimodelEmbeddings
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.sources import LocalFileSource
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.dummy import DummyImageProvider

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
        print(f"Type: {result.element_type}, Location: {document.local_path}, Text: {result.get_key()}")


if __name__ == "__main__":
    asyncio.run(main())
