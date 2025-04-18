import math
from collections.abc import Sequence

import litellm
import tiktoken
from transformers import AutoTokenizer

from ragbits.core.llms.exceptions import LLMStatusError
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
        llm: LiteLLM,
        prompt_template: str | None = None,
        reranker_options: RerankerOptions | None = None,
        llm_options: LiteLLMOptions | None = None,
    ):
        self.reranker_options = reranker_options or self.reranker_default_options
        super().__init__(default_options=self.reranker_options)
        self.llm_options = llm_options or self.llm_default_options
        self.prompt_template = prompt_template or self.default_prompt_template
        self.llm = llm

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
        logit_bias = self.get_yes_no_token_ids()
        if logit_bias is not None:
            self.llm_options.logit_bias = logit_bias

        scored_elements = []
        for doc in elements:
            full_prompt = self.prompt_template.format(query=query, document=doc.text_representation)

            prompt = SimplePrompt(content=full_prompt)

            try:
                res = await self.llm.generate_raw(prompt=prompt, options=self.llm_options)
                answer = res["response"]
                logprob = res["logprobs"][0]["logprob"]
                prob = math.exp(logprob) if answer == "Yes" else 1 - math.exp(logprob)
                scored_elements.append(prob)
            except LLMStatusError as e:
                raise NotImplementedError(
                    f"Model {self.llm.model_name} doesn't support logprobs, "
                    "which are crucial for this reranking method. Try to use other reranker."
                ) from e

        return scored_elements

    def get_yes_no_token_ids(self) -> dict[int, int] | None:
        """
        Getting token ids for yes/no.

        Returns:
            logit_bias dict
        """
        tokens = [" Yes", " No"]
        try:
            model_name = litellm.get_llm_provider(self.llm.model_name)[0]
        except Exception:
            model_name = self.llm.model_name
            pass

        try:
            tokenizer = tiktoken.encoding_for_model(model_name)
            ids = [tokenizer.encode(token) for token in tokens]
            print(ids)
            return {ids[0][0]: 1, ids[1][0]: 1}
        except Exception as e:
            print(f"tiktoken tokenizer doesn't work {e}")

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            ids = [tokenizer.encode(token) for token in tokens]

            if len(ids[0]) == 1:
                return {ids[0][0]: 1, ids[1][0]: 1}
            if len(ids[0]) > 1:
                return {ids[0][1]: 1, ids[1][1]: 1}
        except Exception as e:
            print(f"tiktoken tokenizer doesn't work {e}")
        print("No tokenizer found")
        return None
