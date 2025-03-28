from typing import TypeAlias

from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict, load_dataset

from .base import DataLoader

HFData: TypeAlias = DatasetDict | Dataset | IterableDatasetDict | IterableDataset


class LocalDataLoader(DataLoader[DatasetDict]):
    """
    Local data loader.
    """

    AVAILABLE_BUILDERS = {
        "json",
        "csv",
        "parquet",
        "arrow",
        "text",
        "xml",
        "webdataset",
        "imagefolder",
        "audiofolder",
        "videofolder",
    }

    def __init__(self, path: str, split: str, builder: str) -> None:
        self.path = path
        self.split = split
        self.builder = builder

        if self.builder not in self.AVAILABLE_BUILDERS:
            raise ValueError(
                f"Unsupported builder '{self.builder}'. Available builders: {', '.join(self.AVAILABLE_BUILDERS)}"
            )

    async def load(self) -> DatasetDict:
        """
        Load the data from the local file.

        Returns:
            The loaded data.
        """
        return load_dataset(self.builder, data_files=self.path, split=self.split)
