from dataclasses import dataclass
from functools import cached_property

from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.element import TextElement
from ragbits.evaluate.pipelines.base import EvaluationPipeline, EvaluationResult


@dataclass
class DocumentSearchResult(EvaluationResult):
    """
    Represents the result of a single evaluation.
    """

    question: str
    reference_passages: list[str]
    predicted_passages: list[str]


class DocumentSearchPipeline(EvaluationPipeline):
    """
    Document search evaluation pipeline.
    """

    @cached_property
    def document_search(self) -> "DocumentSearch":
        """
        Returns the document search instance.

        Returns:
            The document search instance.
        """
        return DocumentSearch.from_config(self.config)  # type: ignore

    async def __call__(self, data: dict) -> DocumentSearchResult:
        """
        Runs the document search evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
        elements = await self.document_search.search(data["question"])
        predicted_passages = [element.content for element in elements if isinstance(element, TextElement)]
        return DocumentSearchResult(
            question=data["question"],
            reference_passages=data["passages"],
            predicted_passages=predicted_passages,
        )
