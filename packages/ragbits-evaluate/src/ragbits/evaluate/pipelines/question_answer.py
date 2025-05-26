import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Generic

from typing_extensions import Self

from ragbits.agents._main import AgentResult
from ragbits.agents.types import (
    QuestionAnswerAgent,
    QuestionAnswerPromptInput,
    QuestionAnswerPromptOutputT,
)
from ragbits.core.llms.base import LLMClientOptionsT
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


class QuestionAnswerData(EvaluationData):
    """
    Represents the evaluation data for question answer.
    """

    question: str
    reference_answer: str
    reference_context: Any | None = None


@dataclass
class QuestionAnswerResult(EvaluationResult, Generic[QuestionAnswerPromptOutputT]):
    """
    Represents the result of a single evaluation.
    """

    question: str
    predicted_result: AgentResult[QuestionAnswerPromptOutputT]
    reference_answer: str
    reference_context: Any | None = None


class QuestionAnswerPipeline(
    EvaluationPipeline[
        QuestionAnswerAgent[LLMClientOptionsT, QuestionAnswerPromptInput, QuestionAnswerPromptOutputT],
        QuestionAnswerData,
        QuestionAnswerResult,
    ]
):
    """
    Question answer evaluation pipeline.
    """

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `QuestionAnswerPipeline` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the pipeline.

        Returns:
            An instance of the pipeline class initialized with the provided configuration.
        """
        config["evaluation_target"] = QuestionAnswerAgent.from_config(config)
        return super().from_config(config)

    async def __call__(
        self, data: Iterable[QuestionAnswerData]
    ) -> Iterable[QuestionAnswerResult[QuestionAnswerPromptOutputT]]:
        """
        Run the question answer evaluation pipeline.

        Args:
            data: The evaluation data batch.

        Returns:
            The evaluation result batch.
        """
        results = await asyncio.gather(
            *[
                self.evaluation_target.run(
                    QuestionAnswerPromptInput(
                        question=row.question,
                        context=row.reference_context,
                    )
                )
                for row in data
            ]
        )
        return [
            QuestionAnswerResult(
                question=row.question,
                predicted_result=result,
                reference_answer=row.reference_answer,
                reference_context=row.reference_context,
            )
            for row, result in zip(data, results, strict=False)
        ]
