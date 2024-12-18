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


RerankerOptionsType = TypeVar("RerankerOptionsType", bound=RerankerOptions)


class Reranker(ConfigurableComponent[RerankerOptionsType], ABC):
    """
    Reranks elements retrieved from vector store.
    """

    default_module: ClassVar = rerankers
    options_cls: type[RerankerOptionsType]
    configuration_key: ClassVar = "reranker"

    @abstractmethod
    async def rerank(
        self,
        elements: Sequence[Element],
        query: str,
        options: RerankerOptionsType | None = None,
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
