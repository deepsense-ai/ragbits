from dataclasses import dataclass
from uuid import uuid4

from typing_extensions import Self

from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.sources import HuggingFaceSource
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult


@dataclass
class DocumentSearchResult(EvaluationResult):
    """
    Represents the result of a single evaluation.
    """

    question: str
    reference_passages: list[str]
    predicted_passages: list[str]


class DocumentSearchPipeline(EvaluationPipeline[DocumentSearch]):
    """
    Document search evaluation pipeline.
    """

    def __init__(self, evaluation_target: DocumentSearch, source: dict | None = None) -> None:
        """
        Initializes the document search pipeline.

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
        document_search = DocumentSearch.from_config(config)
        return cls(evaluation_target=document_search, source=config.get("source"))

    async def prepare(self) -> None:
        """
        Ingests corpus data for evaluation.
        """
        if self.source:
            # For now we only support HF sources for pre-evaluation ingest
            # TODO: Make it generic to any data source
            sources = await HuggingFaceSource.list_sources(
                path=self.source["config"]["path"],
                split=self.source["config"]["split"],
            )
            await self.evaluation_target.ingest(sources)

    async def __call__(self, data: dict) -> DocumentSearchResult:
        """
        Runs the document search evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
        elements = await self.evaluation_target.search(data["question"])
        predicted_passages = [element.text_representation for element in elements if element.text_representation]
        return DocumentSearchResult(
            question=data["question"],
            reference_passages=data["passage"],
            predicted_passages=predicted_passages,
        )
