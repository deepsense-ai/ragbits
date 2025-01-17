from abc import ABC, abstractmethod
from dataclasses import dataclass

from ragbits.core.utils.config_handling import WithConstructionConfig


@dataclass
class EvaluationResult(ABC):
    """
    Represents the result of a single evaluation.
    """


class EvaluationPipeline(WithConstructionConfig, ABC):
    """
    Collection evaluation pipeline.
    """

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
