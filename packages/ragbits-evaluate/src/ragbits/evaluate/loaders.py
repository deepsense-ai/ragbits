from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Union

from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict, load_dataset
from omegaconf import DictConfig

DataT = TypeVar("DataT")
HFData = Union[DatasetDict, Dataset, IterableDatasetDict, IterableDataset]


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


class HuggingFaceDataLoader(DataLoader[HFData]):
    """
    Hugging Face data loader.
    """

    async def load(self) -> HFData:
        """
        Load the data from Hugging Face.

        Returns:
            The loaded data.
        """
        return load_dataset(
            path=self.config.data.eval.path,
            split=self.config.data.eval.split,
        )
