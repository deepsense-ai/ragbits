import asyncio
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from itertools import chain
from typing import Generic, TypeVar

from continuous_eval.llm_factory import LLMInterface
from continuous_eval.metrics.base import LLMBasedMetric
from continuous_eval.metrics.generation.text import (
    LLMBasedAnswerCorrectness,
    LLMBasedAnswerRelevance,
    LLMBasedFaithfulness,
    LLMBasedStyleConsistency,
)
from typing_extensions import Self

from ragbits.agents.types import QuestionAnswerPromptOutputT
from ragbits.core.llms.base import LLM
from ragbits.core.utils.helpers import batched
from ragbits.evaluate.metrics.base import Metric
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerResult

MetricT = TypeVar("MetricT", bound=LLMBasedMetric)


class _MetricLMM(LLMInterface):
    """
    Implementation of required interface of Relari generative metrics based on LiteLMM.
    """

    def __init__(self, llm: LLM, loop: AbstractEventLoop) -> None:
        self._llm = llm
        self._loop = loop

    def run(self, prompt: dict[str, str], temperature: float = 0, max_tokens: int = 1024) -> str:
        formatted_prompt = [
            {"role": "system", "content": prompt["system_prompt"]},
            {"role": "user", "content": prompt["user_prompt"]},
        ]
        options = self._llm.options_cls(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return asyncio.run_coroutine_threadsafe(
            self._llm.generate(formatted_prompt, options=options),
            self._loop,
        ).result()


class QuestionAnswerMetric(Generic[MetricT], Metric[QuestionAnswerResult], ABC):
    """
    Metric for question answer evaluation based on Relari backend.
    More details can be found [here](https://docs.relari.ai/category/text-generation).
    """

    metric_cls: type[MetricT]

    def __init__(self, llm: LLM, batch_size: int = 15, weight: float = 1.0) -> None:
        """
        Initialize the agent metric.

        Args:
            llm: Judge LLM instance.
            batch_size: Batch size for metric computation.
            weight: Metric value weight in the final score, used during optimization.
        """
        super().__init__(weight=weight)
        self.llm = llm
        self.batch_size = batch_size

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `QuestionAnswerMetric` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the metric.

        Returns:
            An instance of the metric class initialized with the provided configuration.
        """
        config["llm"] = LLM.from_config(config["llm"])
        config["batch_size"] = config.get("batch_size", 15)
        config["weight"] = config.get("weight", 1.0)
        return super().from_config(config)

    async def compute(self, results: list[QuestionAnswerResult[QuestionAnswerPromptOutputT]]) -> dict:
        """
        Compute the metric.

        Args:
            results: The evaluation results.

        Returns:
            The computed metric.
        """
        metric = self.metric_cls(_MetricLMM(self.llm, loop=asyncio.get_running_loop()))
        metric_results = chain.from_iterable(
            [
                await asyncio.gather(*[asyncio.to_thread(self._call_metric, metric, result) for result in batch])
                for batch in batched(results, self.batch_size)
            ]
        )
        return metric.aggregate(list(metric_results))

    @staticmethod
    @abstractmethod
    def _call_metric(metric: MetricT, result: QuestionAnswerResult[QuestionAnswerPromptOutputT]) -> dict:
        """
        Call the metric with the proper arguments.
        """


class QuestionAnswerAnswerCorrectness(QuestionAnswerMetric[LLMBasedAnswerCorrectness]):
    """
    Metric checking answer correctness based on LLM.
    More details can be found [here](https://docs.relari.ai/metrics/Generation/LLM-Based/llm_correctness).
    """

    metric_cls: type[LLMBasedAnswerCorrectness] = LLMBasedAnswerCorrectness

    @staticmethod
    def _call_metric(
        metric: LLMBasedAnswerCorrectness,
        result: QuestionAnswerResult[QuestionAnswerPromptOutputT],
    ) -> dict:
        return metric(
            question=result.question,
            answer=(
                result.predicted_result.content
                if isinstance(result.predicted_result.content, str)
                else result.predicted_result.content.answer
            ),
            ground_truth_answers=result.reference_answer,
        )


class QuestionAnswerAnswerFaithfulness(QuestionAnswerMetric[LLMBasedFaithfulness]):
    """
    Metric checking answer faithfulness based on LLM.
    More details can be found [here](https://docs.relari.ai/metrics/Generation/LLM-Based/llm_faithfulness).
    """

    metric_cls: type[LLMBasedFaithfulness] = LLMBasedFaithfulness

    @staticmethod
    def _call_metric(
        metric: LLMBasedFaithfulness,
        result: QuestionAnswerResult[QuestionAnswerPromptOutputT],
    ) -> dict:
        return metric(
            question=result.question,
            answer=(
                result.predicted_result.content
                if isinstance(result.predicted_result.content, str)
                else result.predicted_result.content.answer
            ),
            retrieved_context=result.reference_context,
        )


class QuestionAnswerAnswerRelevance(QuestionAnswerMetric[LLMBasedAnswerRelevance]):
    """
    Metric checking answer relevance based on LLM.
    More details can be found [here](https://docs.relari.ai/metrics/Generation/LLM-Based/llm_relevance).
    """

    metric_cls: type[LLMBasedAnswerRelevance] = LLMBasedAnswerRelevance

    @staticmethod
    def _call_metric(
        metric: LLMBasedAnswerRelevance,
        result: QuestionAnswerResult[QuestionAnswerPromptOutputT],
    ) -> dict:
        return metric(
            question=result.question,
            answer=(
                result.predicted_result.content
                if isinstance(result.predicted_result.content, str)
                else result.predicted_result.content.answer
            ),
        )


class QuestionAnswerAnswerConsistency(QuestionAnswerMetric[LLMBasedStyleConsistency]):
    """
    Metric checking answer relevance based on LLM.
    More details can be found [here](https://docs.relari.ai/metrics/Generation/LLM-Based/llm_style).
    """

    metric_cls: type[LLMBasedStyleConsistency] = LLMBasedStyleConsistency

    @staticmethod
    def _call_metric(
        metric: LLMBasedStyleConsistency,
        result: QuestionAnswerResult[QuestionAnswerPromptOutputT],
    ) -> dict:
        return metric(
            answer=(
                result.predicted_result.content
                if isinstance(result.predicted_result.content, str)
                else result.predicted_result.content.answer
            ),
            ground_truth_answers=result.reference_answer,
        )
