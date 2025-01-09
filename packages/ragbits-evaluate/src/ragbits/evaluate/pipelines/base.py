from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig, OmegaConf
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

    def __init__(self, config: dict | None) -> None:
        """
        Initializes the evaluation pipeline.

        Args:
            config: The evaluation pipeline configuration.
        """
        super().__init__()

        self.config = OmegaConf.create(config) if config else DictConfig({})

    @abstractmethod
    async def __call__(self, data: dict[str, Any] | None = None) -> EvaluationResult | None:
        """
        Runs the evaluation pipeline.

        Args:
            data: The evaluation data.

        Returns:
            The evaluation result.
        """
