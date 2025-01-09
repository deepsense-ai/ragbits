from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from omegaconf import DictConfig, OmegaConf

from ragbits.core.utils.config_handling import WithConstructionConfig

DataT = TypeVar("DataT")


class DataLoader(WithConstructionConfig, Generic[DataT], ABC):
    """
    Data loader.
    """

    def __init__(self, config: dict) -> None:
        self.config = OmegaConf.create(config)

    @abstractmethod
    async def load(self) -> DataT:
        """
        Load the data.

        Returns:
            The loaded data.
        """
