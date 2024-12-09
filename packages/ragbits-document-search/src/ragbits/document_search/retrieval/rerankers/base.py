from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval import rerankers


class RerankerOptions(BaseModel):
    """
    Options for the reranker.
    """

    top_n: int | None = None
    max_chunks_per_doc: int | None = None


class Reranker(WithConstructionConfig, ABC):
    """
    Reranks elements retrieved from vector store.
    """

    default_module: ClassVar = rerankers

    def __init__(self, default_options: RerankerOptions | None = None) -> None:
        """
        Constructs a new Reranker instance.

        Args:
            default_options: The default options for reranking.
        """
        self._default_options = default_options or RerankerOptions()

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        default_options = config.pop("default_options", None)
        options = RerankerOptions(**default_options) if default_options else None
        return cls(**config, default_options=options)

    @abstractmethod
    async def rerank(
        self,
        elements: Sequence[Element],
        query: str,
        options: RerankerOptions | None = None,
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
