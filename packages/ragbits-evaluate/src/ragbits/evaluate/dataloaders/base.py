from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ragbits.core.utils.config_handling import WithConstructionConfig

DataT = TypeVar("DataT")


class DataLoader(WithConstructionConfig, Generic[DataT], ABC):
    """
    Data loader.
    """

    @abstractmethod
    async def load(self) -> DataT:
        """
        Load the data.

        Returns:
            The loaded data.
        """
