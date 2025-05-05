import math
from collections.abc import Sequence

from ragbits.core.audit import traceable
from ragbits.core.llms.exceptions import LLMStatusError
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt.prompt import FewShotExample, Prompt
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class RerankerPrompt(Prompt):
    """
    A prompt for relevance ranking.
    """

    user_prompt: str = """Is the following document relevant to the query?\n
            Query: {query}\n
            Document: {document}\n
            Answer: Yes or No."""

    def __init__(
        self,
        custom_user_prompt: str | None = None,
        system_prompt: str | None = None,
        few_shots: list[FewShotExample] | None = None,
    ):
        super().__init__()
        self.user_prompt = custom_user_prompt or self.user_prompt
        self.system_prompt = system_prompt
        self.few_shots = few_shots or []

    def format(self, query: str, document: str) -> str:
        """Formats the user_prompt with the given query and document."""
        return self.user_prompt.format(query=query, document=document)


class LLMReranker(Reranker):
    """
    Reranking algorithm for documents - based on relevance to the query.
    """

    options_cls = RerankerOptions

    def __init__(
        self,
        llm: LiteLLM,
        prompt_template: RerankerPrompt | None = None,
        default_options: RerankerOptions | None = None,
        llm_options: LiteLLMOptions | None = None,
    ):
        super().__init__(default_options=default_options)

        self.llm_options = llm_options or LiteLLMOptions(temperature=0.0, logprobs=True, max_tokens=1)
        self.prompt_template = prompt_template or RerankerPrompt()
        self.llm = llm

    @traceable
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
        logit_bias = self.get_yes_no_tokens_ids()
        if logit_bias is not None:
            self.llm_options.logit_bias = logit_bias

        scored_elements = []
        for doc in elements:
            if doc.text_representation is None:
                scored_elements.append(0.0)
                continue
            prompt = self.prompt_template.format(query=query, document=doc.text_representation)
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

    def get_yes_no_tokens_ids(self) -> dict[int, int] | None:
        """
        Gets ids for "yes" and "no" tokens.

        Returns:
            A logit_bias dictionary for yes and no tokens.
        """
        tokens = [" Yes", " No"]
        try:
            ids = [self.llm.get_token_id(token) for token in tokens]

            return {ids[0][-1]: 1, ids[1][-1]: 1}

        except NotImplementedError as e:
            print(f"Failed to get yes/no token IDs: {e}")
            return None
