import math
from collections.abc import Sequence
from itertools import chain

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.llms.base import LLM
from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.core.prompt.prompt import Prompt
from ragbits.core.types import NOT_GIVEN, NotGiven
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


class LLMRerankerOptions(RerankerOptions):
    """
    Object representing the options for the llm reranker.

    Attributes:
        top_n: The number of entries to return.
        score_threshold: The minimum relevance score for an entry to be returned.
        override_score: If True reranking will override element score.
        llm_options: The options for the LLM.
    """

    llm_options: LiteLLMOptions | None | NotGiven = NOT_GIVEN


class LLMReranker(Reranker[LLMRerankerOptions]):
    """
    Reranker based on LLM.
    """

    options_cls: type[LLMRerankerOptions] = LLMRerankerOptions

    def __init__(
        self,
        llm: LiteLLM,
        *,
        prompt: type[Prompt[RerankerInput, str]] | None = None,
        default_options: LLMRerankerOptions | None = None,
    ) -> None:
        """
        Initialize the LLMReranker instance.

        Args:
            llm: The LLM instance to handle reranking.
            prompt: The prompt to use for reranking elements.
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
                self._llm.get_token_id(" Yes"): 1,
                self._llm.get_token_id(" No"): 1,
            },
        )

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
        options: LLMRerankerOptions | None = None,
    ) -> Sequence[Element]:
        """
        Rerank elements with LLM.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            options: The options for reranking.

        Returns:
            The reranked elements.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = (
            self._llm_options | merged_options.llm_options if merged_options.llm_options else self._llm_options
        )

        flat_elements = list(chain.from_iterable(elements))
        scores = await self._score_elements(flat_elements, query, llm_options)

        scored_elements = list(zip(flat_elements, scores, strict=True))
        scored_elements.sort(key=lambda x: x[1], reverse=True)

        results = []
        for element, score in scored_elements[: merged_options.top_n or None]:
            if not merged_options.score_threshold or score >= merged_options.score_threshold:
                if merged_options.override_score:
                    element.score = score
                results.append(element)
        return results

    async def _score_elements(
        self,
        elements: Sequence[Element],
        query: str,
        llm_options: LiteLLMOptions,
    ) -> Sequence[float]:
        """
        Score the elements according to their relevance to the query using LLM.

        Args:
            elements: The elements to rerank.
            query: The query to rerank the elements against.
            llm_options: The LLM options to use for scoring.

        Returns:
            The elements scores.
        """
        scores = []
        for element in elements:
            if element.text_representation:
                prompt = self._prompt(RerankerInput(query=query, document=element.text_representation))
                response = await self._llm.generate_with_metadata(prompt=prompt, options=llm_options)
                prob = math.exp(response.metadata["logprobs"][0]["logprob"])
                score = prob if response.content == "Yes" else 1 - prob
            else:
                score = 0.0

            scores.append(score)

        return scores
