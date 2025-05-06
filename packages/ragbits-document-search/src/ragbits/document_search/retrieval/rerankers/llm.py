import math
from collections.abc import Sequence
from itertools import chain

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.llms.base import LLM
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.document_search.documents.element import Element
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions


class RerankerInput(BaseModel):
    """
    Input data for the document reranker.
    """

    query: str
    document: str


class RerankerPrompt(Prompt[RerankerInput, str]):
    """
    Prompt for reranking documents.
    """

    system_prompt = """
        You are an Assistant responsible for helping detect whether the retrieved document is relevant to the query.
        For a given input, you need to output a single token: "Yes" or "No" indicating the retrieved document is relevant to the query.
    """  # noqa: E501
    user_prompt = """
        Query: {{query}}
        Document: {{document}}
        Relevant:
    """


class LLMReranker(Reranker[RerankerOptions]):
    """
    Reranker based on LLM.
    """

    options_cls = RerankerOptions

    def __init__(
        self,
        llm: LiteLLM,
        *,
        prompt: type[Prompt[RerankerInput, str]] | None = None,
        llm_options: LiteLLMOptions | None = None,
        default_options: RerankerOptions | None = None,
    ) -> None:
        """
        Initialize the LLMReranker instance.

        Args:
            llm: The LLM instance to handle reranking.
            prompt: The prompt to use for reranking elements.
            llm_options: The LLM options to override.
            default_options: The default options for reranking.
        """
        super().__init__(default_options=default_options)
        self._llm = llm
        self._prompt = prompt or RerankerPrompt
        self._llm_options = LiteLLMOptions(
            temperature=0.0,
            logprobs=True,
            max_tokens=1,
            logit_bias={
                self._llm.get_token_id("Yes"): 1,
                self._llm.get_token_id("No"): 1,
            },
        )
        if llm_options:
            self._llm_options |= llm_options

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initialize the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            The initialized instance of LLMReranker.

        Raises:
            ValidationError: If the configuration doesn't follow the expected format.
            InvalidConfigError: If llm or prompt can't be found or are not the correct type.
        """
        config["llm"] = LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
        config["prompt"] = import_by_path(config["prompt"]) if "prompt" in config else None
        return super().from_config(config)

    @traceable
    async def rerank(
        self,
        elements: Sequence[Sequence[Element]],
        query: str,
        options: RerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        Rerank elements with LLM.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The RerankerOptions to use for reranking.

        Returns:
            The reranked elements.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        flat_elements = list(chain.from_iterable(elements))
        scores = await self._score_elements(flat_elements, query)

        scored_elements = list(zip(flat_elements, scores, strict=True))
        scored_elements.sort(key=lambda x: x[1], reverse=True)

        return [element for element, _ in scored_elements[: merged_options.top_n]]

    async def _score_elements(self, elements: Sequence[Element], query: str) -> Sequence[float]:
        """
        Score the elements according to their relevance to the query using LLM.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.

        Returns:
            The elements scores.
        """
        merged_llm_options = self._llm.default_options | self._llm_options

        scores = []
        for element in elements:
            if element.text_representation:
                prompt = self._prompt(RerankerInput(query=query, document=element.text_representation))
                response = await self._llm.generate_with_metadata(prompt=prompt, options=merged_llm_options)
                prob = math.exp(response.metadata["logprobs"][0]["logprob"])
                score = prob if response.content == "Yes" else 1 - prob
            else:
                score = 0.0

            scores.append(score)

        return scores
