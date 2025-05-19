from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate import pipelines

EvaluationDataT = TypeVar("EvaluationDataT", bound="EvaluationData")
EvaluationResultT = TypeVar("EvaluationResultT", bound="EvaluationResult")
EvaluationTargetT = TypeVar("EvaluationTargetT", bound=WithConstructionConfig)


class EvaluationData(BaseModel, ABC):
    """
    Represents the data for a single evaluation.
    """


@dataclass
class EvaluationResult(ABC):
    """
    Represents the result of a single evaluation.
    """


class EvaluationPipeline(WithConstructionConfig, Generic[EvaluationTargetT, EvaluationDataT, EvaluationResultT], ABC):
    """
    Evaluation pipeline.
    """

    default_module: ClassVar[ModuleType | None] = pipelines
    configuration_key: ClassVar[str] = "pipeline"

    def __init__(self, evaluation_target: EvaluationTargetT) -> None:
        """
        Initialize the evaluation pipeline.

        Args:
            evaluation_target: Evaluation target instance.
        """
        super().__init__()
        self.evaluation_target = evaluation_target

    async def prepare(self) -> None:
        """
        Prepare pipeline for evaluation. Optional step.
        """
        pass

    @abstractmethod
    async def __call__(self, data: Iterable[EvaluationDataT]) -> Iterable[EvaluationResultT]:
        """
        Run the evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
