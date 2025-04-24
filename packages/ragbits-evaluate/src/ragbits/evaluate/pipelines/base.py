from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import ModuleType
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate import pipelines

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


class EvaluationPipeline(WithConstructionConfig, Generic[EvaluationDataT, EvaluationResultT], ABC):
    """
    Evaluation pipeline.
    """

    default_module: ClassVar[ModuleType | None] = pipelines
    configuration_key: ClassVar[str] = "pipeline"

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
