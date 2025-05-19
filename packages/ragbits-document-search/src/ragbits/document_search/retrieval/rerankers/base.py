from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar, TypeVar

from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ConfigurableComponent
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval import rerankers


class RerankerOptions(Options):
    """
    Object representing the options for the reranker.

    Attributes:
        top_n: The number of entries to return.
        score_threshold: The minimum relevance score for an entry to be returned.
        override_score: If True reranking will override element score.
    """

    top_n: int | None | NotGiven = NOT_GIVEN
    score_threshold: float | None | NotGiven = NOT_GIVEN
    override_score: bool = True


RerankerOptionsT = TypeVar("RerankerOptionsT", bound=RerankerOptions)


class Reranker(ConfigurableComponent[RerankerOptionsT], ABC):
    """
    Reranks elements retrieved from vector store.
    """

    options_cls: type[RerankerOptionsT]
    default_module: ClassVar = rerankers
    configuration_key: ClassVar = "reranker"

    @abstractmethod
    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: RerankerOptionsT | None = None,
    ) -> Sequence[Element]:
        """
        Rerank elements.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The options for reranking.

        Returns:
            The reranked elements.
        """
