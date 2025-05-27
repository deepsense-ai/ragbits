import asyncio
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from uuid import uuid4

from typing_extensions import Self

from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.element import Element
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


class DocumentSearchData(EvaluationData):
    """
    Represents the evaluation data for document search.
    """

    question: str
    reference_document_ids: list[str | int] | None = None
    reference_passages: list[str] | None = None
    reference_page_numbers: list[int] | None = None


@dataclass
class DocumentSearchResult(EvaluationResult):
    """
    Represents the result of a single evaluation.
    """

    question: str
    predicted_elements: Sequence[Element]
    reference_document_ids: list[str | int] | None = None
    reference_passages: list[str] | None = None
    reference_page_numbers: list[int] | None = None


class DocumentSearchPipeline(EvaluationPipeline[DocumentSearch, DocumentSearchData, DocumentSearchResult]):
    """
    Document search evaluation pipeline.
    """

    def __init__(self, evaluation_target: DocumentSearch, source: dict | None = None) -> None:
        """
        Initialize the document search evaluation pipeline.

        Args:
            evaluation_target: Document Search instance.
            source: Source data config for ingest.
        """
        super().__init__(evaluation_target=evaluation_target)
        self.source = source or {}

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `DocumentSearchPipeline` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the pipeline.

        Returns:
            An instance of the pipeline class initialized with the provided configuration.
        """
        # At this point, we assume that if the source is set, the pipeline is run in experimental mode
        # and create random indexes for testing
        # TODO: optimize this for cases with duplicated document search configs between runs
        if config.get("source"):
            config["vector_store"]["config"]["index_name"] = str(uuid4())
        evaluation_target: DocumentSearch = DocumentSearch.from_config(config)
        return cls(evaluation_target=evaluation_target, source=config.get("source"))

    async def prepare(self) -> None:
        """
        Ingest corpus data for evaluation.
        """
        if self.source:
            # For now we only support HF sources for pre-evaluation ingest
            # TODO: Make it generic to any data source
            sources = await HuggingFaceSource.list_sources(
                path=self.source["config"]["path"],
                split=self.source["config"]["split"],
            )
            await self.evaluation_target.ingest(sources)

    async def __call__(self, data: Iterable[DocumentSearchData]) -> Iterable[DocumentSearchResult]:
        """
        Run the document search evaluation pipeline.

        Args:
            data: The evaluation data batch.

        Returns:
            The evaluation result batch.
        """
        results = await asyncio.gather(*[self.evaluation_target.search(row.question) for row in data])
        return [
            DocumentSearchResult(
                question=row.question,
                predicted_elements=elements,
                reference_document_ids=row.reference_document_ids,
                reference_passages=row.reference_passages,
                reference_page_numbers=row.reference_page_numbers,
            )
            for row, elements in zip(data, results, strict=False)
        ]
