from abc import ABC, abstractmethod
from typing import ClassVar, Generic

from typing_extensions import Self

from ragbits.core.sources.base import Source
from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.evaluate.pipelines.base import EvaluationDataT


class DataLoader(WithConstructionConfig, Generic[EvaluationDataT], ABC):
    """
    Evaluation data loader.
    """

    configuration_key: ClassVar[str] = "dataloader"

    def __init__(self, source: Source) -> None:
        """
        Initializes the data loader.

        Args:
            source: The source to load the evaluation data from.
        """
        self.source = source

    @classmethod
    def from_config(cls, config: dict) -> Self:
        source_config = ObjectConstructionConfig.model_validate(config["source"])
        config["source"] = Source.subclass_from_config(source_config)
        return super().from_config(config)

    @abstractmethod
    async def load(self) -> list[EvaluationDataT]:
        """
        Load the data.

        Returns:
            The loaded data.
        """
