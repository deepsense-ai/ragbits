from typing import TypeAlias

from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict, load_dataset

from ragbits.evaluate.loaders.base import DataLoader

HFData: TypeAlias = DatasetDict | Dataset | IterableDatasetDict | IterableDataset


class HFDataLoader(DataLoader[HFData]):
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
            path=self.config.path,
            split=self.config.split,
        )
