from collections.abc import Sequence
from itertools import chain
from typing import Any

from rerankers import Reranker as AnswerReranker

from ragbits.core.audit.traces import trace
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class AnswerAIReranker(Reranker[RerankerOptions]):
    """
    A [rerankers](https://github.com/AnswerDotAI/rerankers) re-ranker covering most popular re-ranking methods.
    """

    options_cls: type[RerankerOptions] = RerankerOptions

    def __init__(
        self,
        model: str,
        default_options: RerankerOptions | None = None,
        **rerankers_kwargs: Any,  # noqa: ANN401
    ) -> None:
        """
        Initialize the AnswerAIReranker instance.

        Args:
            model: The reranker model to use.
            default_options: The default options for reranking.
            **rerankers_kwargs: Additional keyword arguments native to rerankers lib.
        """
        super().__init__(default_options=default_options)
        self.model = model
        self.ranker = AnswerReranker(self.model, **rerankers_kwargs)

    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
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

        Raises:
            ValueError: Raised if the input query is empty or if the list of candidate documents is empty.
            TypeError: Raised if the input types are incorrect, such as if the query is not a string, or List[str].
            IndexError: Raised if docs is an empty List.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        flat_elements = list(chain.from_iterable(elements))
        documents = [element.text_representation or "" for element in flat_elements]

        with trace(
            query=query, documents=documents, elements=elements, model=self.model, options=merged_options
        ) as outputs:
            response = self.ranker.rank(
                query=query,
                docs=documents,
            )
            if merged_options.top_n:
                response = response.top_k(merged_options.top_n)

            results = []
            for result in response:
                if not merged_options.score_threshold or result.score >= merged_options.score_threshold:
                    if merged_options.override_score:
                        flat_elements[result.document.doc_id].score = result.score
                    results.append(flat_elements[result.document.doc_id])

            outputs.results = results

        return outputs.results
