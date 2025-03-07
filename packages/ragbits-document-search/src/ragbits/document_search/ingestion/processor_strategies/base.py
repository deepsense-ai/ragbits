import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import ClassVar

from pydantic import BaseModel, Field

from ragbits.core.embeddings.base import Embedder, EmbeddingType
from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element, ImageElement
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion import processor_strategies
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider


class ProcessingExecutionResult(BaseModel):
    """
    Represents the result of the documents processing execution.
    """

    successful: list = Field(default_factory=list)
    failed: list = Field(default_factory=list)


class ProcessingExecutionStrategy(WithConstructionConfig, ABC):
    """
    Base class for processing execution strategies that define how documents are processed to become indexed.
    The processing execution strategy is responsible for orchiesting the tasks required to index the document.
    """

    default_module: ClassVar = processor_strategies

    def __init__(self, num_retries: int = 3) -> None:
        """
        Initialize the ProcessingExecutionStrategy instance.

        Args:
            num_retries: The number of retries per document processing task error.
        """
        self.num_retries = num_retries

    @abstractmethod
    async def process(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        embedder: Embedder,
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> ProcessingExecutionResult:
        """
        Process documents for indexing.

        Args:
            documents: The documents to process.
            embedder: The embedder to produce chunk embeddings.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The processing excution result.
        """

    @staticmethod
    async def _parse_document(
        document: DocumentMeta | Document | Source,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        """
        Parse a single document and return the elements.

        Args:
            document: The document to parse.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.
        """
        document_meta = (
            await DocumentMeta.from_source(document)
            if isinstance(document, Source)
            else document
            if isinstance(document, DocumentMeta)
            else document.metadata
        )
        processor = processor_overwrite or processor_router.get_provider(document_meta)
        return await processor.process(document_meta)

    @staticmethod
    async def _remove_entries_with_same_sources(elements: list[Element], vector_store: VectorStore) -> None:
        """
        Remove entries from the vector store whose source id is present in the elements' metadata.

        Args:
            elements: List of elements whose source ids will be checked and removed from the vector store if present.
            vector_store: The vector store to store document chunks.
        """
        unique_source_ids = {element.document_meta.source.id for element in elements}

        ids_to_delete = []
        # TODO: Pass 'where' argument to the list method to filter results and optimize search
        for entry in await vector_store.list():
            if entry.metadata.get("document_meta", {}).get("source", {}).get("id") in unique_source_ids:
                ids_to_delete.append(entry.id)

        if ids_to_delete:
            await vector_store.remove(ids_to_delete)

    @staticmethod
    async def _insert_elements(elements: list[Element], embedder: Embedder, vector_store: VectorStore) -> None:
        """
        Insert Elements into the vector store.

        Args:
            elements: The list of Elements to insert.
            embedder: The embedder to produce chunk embeddings.
            vector_store: The vector store to store document chunks.
        """
        elements_with_text = [element for element in elements if element.key]
        images_with_text = [element for element in elements_with_text if isinstance(element, ImageElement)]
        vectors = await embedder.embed_text([element.key for element in elements_with_text])  # type: ignore

        image_elements = [element for element in elements if isinstance(element, ImageElement)]

        entries = [
            element.to_vector_db_entry(vector, EmbeddingType.TEXT)
            for element, vector in zip(elements_with_text, vectors, strict=False)
        ]
        not_embedded_image_elements = [
            image_element for image_element in image_elements if image_element not in images_with_text
        ]

        if image_elements and embedder.image_support():
            image_vectors = await embedder.embed_image([element.image_bytes for element in image_elements])
            entries.extend(
                [
                    element.to_vector_db_entry(vector, EmbeddingType.IMAGE)
                    for element, vector in zip(image_elements, image_vectors, strict=False)
                ]
            )
            not_embedded_image_elements = []

        for image_element in not_embedded_image_elements:
            warnings.warn(f"Image: {image_element.id} could not be embedded")

        await vector_store.store(entries)
