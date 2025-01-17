from typing import TypeAlias

from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict, load_dataset

from ragbits.evaluate.dataloaders.base import DataLoader

HFData: TypeAlias = DatasetDict | Dataset | IterableDatasetDict | IterableDataset


class HFDataLoader(DataLoader[HFData]):
    """
    Hugging Face data loader.
    """

    def __init__(self, path: str, split: str) -> None:
        self.path = path
        self.split = split

    async def load(self) -> HFData:
        """
        Load the data from Hugging Face.

        Returns:
            The loaded data.
        """
        return load_dataset(
            path=self.path,
            split=self.split,
        )
