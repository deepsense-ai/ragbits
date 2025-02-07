from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar, TypeVar

from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ConfigurableComponent
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval import rerankers


class RerankerOptions(Options):
    """
    Options for the reranker.
    """

    top_n: int | None = None
    max_chunks_per_doc: int | None = None


RerankerOptionsT = TypeVar("RerankerOptionsT", bound=RerankerOptions)


class Reranker(ConfigurableComponent[RerankerOptionsT], ABC):
    """
    Reranks elements retrieved from vector store.
    """

    default_module: ClassVar = rerankers
    options_cls: type[RerankerOptionsT]
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
