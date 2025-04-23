from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig

EvaluationDataT = TypeVar("EvaluationDataT", bound="EvaluationData")
EvaluationResultT = TypeVar("EvaluationResultT", bound="EvaluationResult")


class EvaluationData(BaseModel, ABC):
    """
    Represents the data for a single evaluation.
    """


@dataclass
class EvaluationResult(ABC):
    """
    Represents the result of a single evaluation.
    """


class EvaluationPipeline(Generic[EvaluationDataT, EvaluationResultT], WithConstructionConfig, ABC):
    """
    Evaluation pipeline.
    """

    async def prepare(self) -> None:
        """
        Prepares pipeline for evaluation. Optional step.
        """
        pass

    @abstractmethod
    async def __call__(self, data: EvaluationDataT) -> EvaluationResultT:
        """
        Runs the evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
