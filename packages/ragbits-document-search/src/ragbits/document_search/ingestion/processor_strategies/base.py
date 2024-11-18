from abc import ABC, abstractmethod
from collections.abc import Sequence

from typing_extensions import Self

from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider


class ProcessingExecutionStrategy(ABC):
    """
    Base class for processing execution strategies that define how documents are processed to become elements.

    Processing execution strategies are responsible for processing documents using the appropriate processor,
    which means that they don't usually determine the business logic of the processing itself, but rather how
    the processing is executed.
    """

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Creates and returns an instance of the ProcessingExecutionStrategy subclass from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the instance.

        Returns:
            An initialized instance of the ProcessingExecutionStrategy subclass.
        """
        return cls(**config)

    @staticmethod
    async def to_document_meta(document: DocumentMeta | Document | Source) -> DocumentMeta:
        """
        Convert a document, document meta or source to a document meta object.

        Args:
            document: The document to convert.

        Returns:
            The document meta object.
        """
        if isinstance(document, Source):
            return await DocumentMeta.from_source(document)
        elif isinstance(document, DocumentMeta):
            return document
        else:
            return document.metadata

    async def process_document(
        self,
        document: DocumentMeta | Document | Source,
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        """
        Process a single document and return the elements.

        Args:
            document: The document to process.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.
        """
        document_meta = await self.to_document_meta(document)
        processor = processor_overwrite or processor_router.get_provider(document_meta)
        return await processor.process(document_meta)

    @abstractmethod
    async def process_documents(
        self,
        documents: Sequence[DocumentMeta | Document | Source],
        processor_router: DocumentProcessorRouter,
        processor_overwrite: BaseProvider | None = None,
    ) -> list[Element]:
        """
        Process documents using the given processor and return the resulting elements.

        Args:
            documents: The documents to process.
            processor_router: The document processor router to use.
            processor_overwrite: Forces the use of a specific processor, instead of the one provided by the router.

        Returns:
            A list of elements.
        """
