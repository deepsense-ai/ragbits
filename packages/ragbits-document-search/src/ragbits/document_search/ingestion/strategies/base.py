import asyncio
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from types import ModuleType
from typing import ClassVar, ParamSpec, TypeVar

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion import strategies
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter

_CallP = ParamSpec("_CallP")
_CallReturnT = TypeVar("_CallReturnT")


@dataclass
class IngestDocumentResult:
    """
    Represents the result of the document ingest execution.
    """

    document_uri: str
    num_elements: int = 0
    error: BaseException | None = None


@dataclass
class IngestExecutionResult:
    """
    Represents the result of the documents ingest execution.
    """

    successful: list[IngestDocumentResult] = field(default_factory=list)
    failed: list[IngestDocumentResult] = field(default_factory=list)


class IngestStrategy(WithConstructionConfig, ABC):
    """
    Base class for ingest strategies, responsible for orchiesting the tasks required to index the document.
    """

    default_module: ClassVar[ModuleType | None] = strategies
    configuration_key: ClassVar[str] = "ingest_strategy"

    def __init__(self, num_retries: int = 3, backoff_multiplier: int = 1, backoff_max: int = 60) -> None:
        """
        Initialize the IngestStrategy instance.

        Args:
            num_retries: The number of retries per document ingest task error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        self.num_retries = num_retries
        self.backoff_multiplier = backoff_multiplier
        self.backoff_max = backoff_max

    @abstractmethod
    async def __call__(
        self,
        documents: Iterable[DocumentMeta | Document | Source],
        vector_store: VectorStore,
        parser_router: DocumentParserRouter,
        enricher_router: ElementEnricherRouter,
    ) -> IngestExecutionResult:
        """
        Ingest documents.

        Args:
            documents: The documents to ingest.
            vector_store: The vector store to store document chunks.
            parser_router: The document parser router to use.
            enricher_router: The intermediate element enricher router to use.

        Returns:
            The ingest execution result.
        """

    async def _call_with_error_handling(
        self,
        executable: Callable[_CallP, Awaitable[_CallReturnT]],
        *executable_args: _CallP.args,
        **executable_kwargs: _CallP.kwargs,
    ) -> _CallReturnT:
        """
        Call executable with a standarized error handling.
        If an error occurs, the executable is retried `num_retries` times using randomized exponential backoff.

        Args:
            executable: The callable function to execute.
            executable_args: Positional arguments to pass to the executable.
            executable_kwargs: Keyword arguments to pass to the executable.

        Returns:
            The result of the executable if successful.

        Raises:
            Exception: The last encountered exception after all retries are exhausted.
        """
        for i in range(max(0, self.num_retries) + 1):
            try:
                return await executable(*executable_args, **executable_kwargs)
            except Exception as exc:
                if i == self.num_retries:
                    raise exc

                delay = min(2**i * self.backoff_multiplier, self.backoff_max)
                delay = random.uniform(0, delay) if delay < self.backoff_max else random.uniform(0, self.backoff_max)  # noqa S311
                await asyncio.sleep(delay)

        raise RuntimeError("Unreachable code reached")  # mypy quirk

    @staticmethod
    async def _parse_document(
        document: DocumentMeta | Document | Source,
        parser_router: DocumentParserRouter,
    ) -> list[Element]:
        """
        Parse a single document and return the elements.

        Args:
            document: The document to parse.
            parser_router: The document parser router to use.

        Returns:
            The list of elements.

        Raises:
            ParserError: If the parsing of the document failed.
            ParserDocumentNotSupportedError: If the document type is not supported.
            ParserNotFoundError: If no parser is found for the document type.
            SourceError: If the download of the document failed.
        """
        document_meta = (
            await DocumentMeta.from_source(document)
            if isinstance(document, Source)
            else document
            if isinstance(document, DocumentMeta)
            else document.metadata
        )
        parser = parser_router.get(document_meta)
        parser.validate_document_type(document_meta.document_type)
        document = await document_meta.fetch()
        return await parser.parse(document)

    @staticmethod
    async def _enrich_elements(
        elements: Iterable[Element],
        enricher_router: ElementEnricherRouter,
    ) -> list[Element]:
        """
        Enrich elements for a single document.

        Args:
            elements: The document elements to enrich.
            enricher_router: The element enricher router to use.

        Returns:
            The list of enriched elements.

        Raises:
            ValueError: If no enricher found for the element type.
        """
        grouped_elements = defaultdict(list)
        for element in elements:
            grouped_elements[type(element)].append(element)

        grouped_enriched_elements = await asyncio.gather(
            *[
                enricher.enrich(elements)
                for element_type, elements in grouped_elements.items()
                if (enricher := enricher_router.get(element_type))
            ]
        )
        return [element for enriched_elements in grouped_enriched_elements for element in enriched_elements]

    @staticmethod
    async def _remove_elements(elements: Iterable[Element], vector_store: VectorStore) -> None:
        """
        Remove entries from the vector store whose source id is present in the elements metadata.

        Args:
            elements: The list of elements whose source ids will be removed from the vector store.
            vector_store: The vector store to store document chunks.
        """
        unique_source_ids = {element.document_meta.source.id for element in elements}
        # TODO: Pass 'where' argument to the list method to filter results and optimize search
        ids_to_delete = [
            entry.id
            for entry in await vector_store.list()
            if entry.metadata.get("document_meta", {}).get("source", {}).get("id") in unique_source_ids
        ]
        if ids_to_delete:
            await vector_store.remove(ids_to_delete)

    @staticmethod
    async def _insert_elements(elements: Iterable[Element], vector_store: VectorStore) -> None:
        """
        Insert elements into the vector store.

        Args:
            elements: The list of elements to insert.
            vector_store: The vector store to store document chunks.
        """
        await vector_store.store([element.to_vector_db_entry() for element in elements])
