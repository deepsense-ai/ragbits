import math
from collections.abc import Sequence
from typing import Optional

import tiktoken

from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt.base import SimplePrompt
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class LLMReranker(Reranker):
    """
    Reranking algorithm for documents - based on relevance to the query.
    """

    options_cls = LiteLLMOptions
    default_prompt_template: str = """Is the following document relevant to the query?\n
        Query: {query}\n
        Document: {document}\n
        Answer: Yes or No."""

    llm_default_options = LiteLLMOptions(temperature=0.0, logprobs=True, max_tokens=1)
    reranker_default_options = RerankerOptions(top_n=5)

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        prompt_template: str | None = None,
        reranker_options: RerankerOptions | None = None,
        llm_options: LiteLLMOptions | None = None,
    ):
        self.reranker_options = reranker_options or self.reranker_default_options
        super().__init__(default_options=self.reranker_options)
        self.llm_options = llm_options or self.llm_default_options
        self.prompt_template = prompt_template or self.default_prompt_template
        self.model_name = model_name

    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """Reranking the sequence of elements according to obtain scores.

        Args:
            elements: The sequence of the sequence of elements to rerank.
            query: The query to score elements with.
            options: The RerankerOptions to use for reranking.

        Returns:
            A sequence of elements.

        """
        reranker_options = (self.default_options | options) if options else self.default_options
        flat_elements = [element for item in elements for element in item]
        scored_elements = await self._score_elements(flat_elements, query)
        scoring_results = list(zip(flat_elements, scored_elements, strict=True))
        scoring_results.sort(key=lambda x: x[1], reverse=True)
        return [elem for elem, _ in scoring_results[: reranker_options.top_n]]

    async def _score_elements(self, elements: Sequence[Element], query: str) -> Sequence[float]:
        """
        Scoring the elements according to their relevance to the query
        Args:
            elements: The sequence of elements to score.
            query: The query to score elements with.

        Returns:
            A sequence of assigned scores.
        """
        self.llm_options.logit_bias = self.get_yes_no_token_ids()

        lite_llm = LiteLLM(model_name=self.model_name, default_options=self.llm_options)
        scored_elements = []
        for doc in elements:
            full_prompt = self.prompt_template.format(query=query, document=doc.text_representation)

            prompt = SimplePrompt(content=full_prompt)
            res = await lite_llm._call(prompt=prompt, options=self.llm_options)
            answer = res["response"]
            logprob = res["logprobs"][0]["logprob"]
            prob = math.exp(logprob) if answer == "Yes" else math.exp(logprob)
            scored_elements.append(prob)

        return scored_elements

    def get_yes_no_token_ids(self) -> dict[int, int]:
        """Get token IDs for ' Yes' and ' No' with leading spaces"""
        tokens = [" Yes", " No"]
        tokenizer = tiktoken.encoding_for_model(self.model_name)
        ids = [tokenizer.encode(token) for token in tokens]
        return {ids[0][0]: 1, ids[1][0]: 1}
