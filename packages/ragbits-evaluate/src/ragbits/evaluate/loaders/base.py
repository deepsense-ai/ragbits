from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from omegaconf import DictConfig

DataT = TypeVar("DataT")


class DataLoader(Generic[DataT], ABC):
    """
    Data loader.
    """

    def __init__(self, config: DictConfig) -> None:
        self.config = config

    @abstractmethod
    async def load(self) -> DataT:
        """
        Load the data.

        Returns:
            The loaded data.
        """
