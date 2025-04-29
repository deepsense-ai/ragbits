from abc import ABC, abstractmethod
from collections.abc import Iterable
from types import ModuleType
from typing import ClassVar, Generic

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.sources.base import Source
from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.evaluate import dataloaders
from ragbits.evaluate.pipelines.base import EvaluationDataT


class DataLoaderConfig(BaseModel):
    """
    Schema for the data loader config.
    """

    source: ObjectConstructionConfig


class DataLoader(WithConstructionConfig, Generic[EvaluationDataT], ABC):
    """
    Evaluation data loader.
    """

    default_module: ClassVar[ModuleType | None] = dataloaders
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
        """
        Create an instance of `DataLoader` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the data loader.

        Returns:
            An instance of the data loader class initialized with the provided configuration.
        """
        dataloader_config = DataLoaderConfig.model_validate(config)
        config["source"] = Source.subclass_from_config(dataloader_config.source)
        return super().from_config(config)

    @abstractmethod
    async def load(self) -> Iterable[EvaluationDataT]:
        """
        Load the data.

        Returns:
            The loaded data.
        """
