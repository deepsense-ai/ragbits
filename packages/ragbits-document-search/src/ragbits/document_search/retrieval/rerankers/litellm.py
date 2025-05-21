from collections.abc import Sequence
from itertools import chain

import litellm

from ragbits.core.audit.traces import traceable
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class LiteLLMRerankerOptions(RerankerOptions):
    """
    Object representing the options for the litellm reranker.

    Attributes:
        top_n: The number of entries to return.
        score_threshold: The minimum relevance score for an entry to be returned.
        override_score: If True reranking will override element score.
        max_chunks_per_doc: The maximum amount of tokens a document can have before truncation.
    """

    max_chunks_per_doc: int | None | NotGiven = NOT_GIVEN


class LiteLLMReranker(Reranker[LiteLLMRerankerOptions]):
    """
    A [LiteLLM](https://docs.litellm.ai/docs/rerank) reranker for providers such as Cohere, Together AI, Azure AI.
    """

    options_cls: type[LiteLLMRerankerOptions] = LiteLLMRerankerOptions

    def __init__(
        self,
        model: str,
        default_options: LiteLLMRerankerOptions | None = None,
    ) -> None:
        """
        Initialize the LiteLLMReranker instance.

        Args:
            model: The reranker model to use.
            default_options: The default options for reranking.
        """
        super().__init__(default_options=default_options)
        self.model = model

    @traceable
    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: LiteLLMRerankerOptions | None = None,
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
        merged_options = (self.default_options | options) if options else self.default_options
        flat_elements = list(chain.from_iterable(elements))
        documents = [element.text_representation or "" for element in flat_elements]

        response = await litellm.arerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=merged_options.top_n or None,
            max_chunks_per_doc=merged_options.max_chunks_per_doc or None,
        )

        results = []
        for result in response.results:
            if not merged_options.score_threshold or result["relevance_score"] >= merged_options.score_threshold:
                if merged_options.override_score:
                    flat_elements[result["index"]].score = result["relevance_score"]
                results.append(flat_elements[result["index"]])

        return results
