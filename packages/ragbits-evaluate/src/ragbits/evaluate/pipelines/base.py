from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from omegaconf import DictConfig


@dataclass
class EvaluationResult:
    """
    Represents the result of a single evaluation.
    """


class EvaluationPipeline(ABC):
    """
    Collection evaluation pipeline.
    """

    def __init__(self, config: Optional[DictConfig] = None) -> None:
        """
        Initializes the evaluation pipeline.

        Args:
            config: The evaluation pipeline configuration.
        """
        super().__init__()
        self.config = config or {}

    @abstractmethod
    async def __call__(self, data: dict[str, Any]) -> EvaluationResult:
        """
        Runs the evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
