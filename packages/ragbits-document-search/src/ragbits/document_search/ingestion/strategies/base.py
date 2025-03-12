import asyncio
import random
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterable
from typing import ClassVar, ParamSpec, TypeVar

from pydantic import BaseModel, Field

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.core.vector_stores.base import VectorStore
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion import strategies
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider

_CallP = ParamSpec("_CallP")
_CallReturnT = TypeVar("_CallReturnT")


class IngestTaskResult(BaseModel):
    """
    Represents the result of the document ingest tast.
    """

    class Config:  # noqa: D106
        arbitrary_types_allowed = True

    document_uri: str
    response: list[Element] | BaseException


class IngestSummaryResult(BaseModel):
    """
    Represents the result of the document ingest execution.
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

    async def _call_with_error_handling(
        self,
        executable: Callable[_CallP, Awaitable[_CallReturnT]],
        return_exception: bool = False,
        *executable_args: _CallP.args,
        **executable_kwargs: _CallP.kwargs,
    ) -> _CallReturnT | BaseException:
        """
        Call executable with standarized error handling.
        If an error occurs, the executable is retried `num_retries` times using randomized exponential backoff.

        Args:
            executable: The callable function to execute.
            return_exception: If True, return the exception instead of raising it after all retries.
            executable_args: Positional arguments to pass to the executable.
            executable_kwargs: Keyword arguments to pass to the executable.

        Returns:
            The result of the executable if successful.
            If all retries fail and `return_exception` is True, returns the last encountered exception.
            Otherwise, raises the exception after all retries are exhausted.
        """
        for i in range(max(0, self.num_retries) + 1):
            try:
                return await executable(*executable_args, **executable_kwargs)
            except Exception as exc:
                if i == self.num_retries:
                    if return_exception:
                        return exc
                    else:
                        raise exc

                delay = min(2**i * self.backoff_multiplier, self.backoff_max)
                delay = random.uniform(0, delay) if delay < self.backoff_max else random.uniform(0, self.backoff_max)  # noqa S311
                await asyncio.sleep(delay)

        raise RuntimeError("Unreachable code reached")  # mypy quirk

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
            The list of elements.
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
        # TODO: Pass 'where' argument to the list method to filter results and optimize search
        ids_to_delete = [
            entry.id
            for entry in await vector_store.list()
            if entry.metadata.get("document_meta", {}).get("source", {}).get("id") in unique_source_ids
        ]
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
