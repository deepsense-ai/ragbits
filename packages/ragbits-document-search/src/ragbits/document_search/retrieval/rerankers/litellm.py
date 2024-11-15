from collections.abc import Sequence

import litellm

from ragbits.core.audit import traceable
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class LiteLLMReranker(Reranker):
    """
    A [LiteLLM](https://docs.litellm.ai/docs/rerank) reranker for providers such as Cohere, Together AI, Azure AI.
    """

    def __init__(self, model: str, default_options: RerankerOptions | None = None) -> None:
        """
        Constructs a new LiteLLMReranker instance.

        Args:
            model: The reranker model to use.
            default_options: The default options for reranking.
        """
        super().__init__(default_options)
        self.model = model

    @classmethod
    def from_config(cls, config: dict) -> "LiteLLMReranker":
        """
        Creates and returns an instance of the LiteLLMReranker class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the LiteLLMReranker instance.

        Returns:
            An initialized instance of the LiteLLMReranker class.
        """
        return cls(
            model=config["model"],
            default_options=RerankerOptions(**config.get("default_options", {})),
        )

    @traceable
    async def rerank(
        self,
        elements: Sequence[Element],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        Rerank elements with LiteLLM API.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The options for reranking.

        Returns:
            The reranked elements.
        """
        options = self._default_options if options is None else options
        documents = [element.text_representation for element in elements]

        response = await litellm.arerank(
            model=self.model,
            query=query,
            documents=documents,  # type: ignore
            top_n=options.top_n,
            max_chunks_per_doc=options.max_chunks_per_doc,
        )

        return [elements[result["index"]] for result in response.results]  # type: ignore
