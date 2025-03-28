from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from ragbits.core.utils.config_handling import WithConstructionConfig

EvaluationTargetT = TypeVar("EvaluationTargetT", bound=WithConstructionConfig)


@dataclass
class EvaluationResult(ABC):
    """
    Represents the result of a single evaluation.
    """


class EvaluationPipeline(Generic[EvaluationTargetT], WithConstructionConfig, ABC):
    """
    Collection evaluation pipeline.
    """

    def __init__(self, evaluation_target: EvaluationTargetT):
        self.evaluation_target = evaluation_target

    @abstractmethod
    async def __call__(self, data: dict) -> EvaluationResult:
        """
        Runs the evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """

    async def prepare(self) -> None:
        """
        Prepares pipeline for evaluation.
        """
        pass
