from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import ClassVar

from pydantic import BaseModel, Field

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion import strategies
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider


class IngestTaskResult(BaseModel):
    """
    Represents the successful result of the documents ingest execution.
    """

    class Config:  # noqa: D106
        arbitrary_types_allowed = True

    document_uri: str
    response: list[Element] | BaseException


class IngestSummaryResult(BaseModel):
    """
    Represents the successful result of the documents ingest execution.
    """

    class Config:  # noqa: D106
        arbitrary_types_allowed = True

    document_uri: str
    num_elements: int = 0
    error: BaseException | None = None


class IngestExecutionResult(BaseModel):
    """
    Represents the result of the documents ingest execution.
    """

    successful: list[IngestSummaryResult] = Field(default_factory=list)
    failed: list[IngestSummaryResult] = Field(default_factory=list)


class IngestStrategy(WithConstructionConfig, ABC):
    """
    Base class for ingest strategies, responsible for orchiesting the tasks required to index the document.
    """

    default_module: ClassVar = strategies

    def __init__(self, num_retries: int = 3) -> None:
        """
        Initialize the IngestStrategy instance.

        Args:
            num_retries: The number of retries per document ingest task error.
        """
        self.num_retries = num_retries

    @abstractmethod
    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> IngestExecutionResult:
        """
        Ingest documents.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            The ingest execution result.
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
    async def _remove_elements(elements: list[Element], vector_store: VectorStore) -> None:
        """
        Remove entries from the vector store whose source id is present in the elements metadata.

        Args:
            elements: The list of elements whose source ids will be removed from the vector store.
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
    async def _insert_elements(elements: list[Element], vector_store: VectorStore) -> None:
        """
        Insert Elements into the vector store.

        Args:
            elements: The list of elements to insert.
            vector_store: The vector store to store document chunks.
        """
        await vector_store.store([element.to_vector_db_entry() for element in elements])
