from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import BaseModel

from ragbits.document_search.documents.element import Element


class RerankerOptions(BaseModel):
    """
    Options for the reranker.
    """

    top_n: int | None = None
    max_chunks_per_doc: int | None = None


class Reranker(ABC):
    """
    Reranks elements retrieved from vector store.
    """

    def __init__(self, default_options: RerankerOptions | None = None) -> None:
        """
        Constructs a new Reranker instance.

        Args:
            default_options: The default options for reranking.
        """
        self._default_options = default_options or RerankerOptions()

    @classmethod
    def from_config(cls, config: dict) -> "Reranker":
        """
        Creates and returns an instance of the Reranker class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the Reranker instance.

        Returns:
            An initialized instance of the Reranker class.

        Raises:
            NotImplementedError: If the class cannot be created from the provided configuration.
        """
        raise NotImplementedError(f"Cannot create class {cls.__name__} from config.")

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
