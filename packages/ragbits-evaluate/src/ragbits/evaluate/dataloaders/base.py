from abc import ABC, abstractmethod
from collections.abc import Iterable
from types import ModuleType
from typing import ClassVar, Generic

from datasets import load_dataset
from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.sources.base import Source
from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.evaluate import dataloaders
from ragbits.evaluate.dataloaders.exceptions import DataLoaderIncorrectFormatDataError
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

    def __init__(self, source: Source, *, split: str = "data", required_keys: set[str] | None = None) -> None:
        """
        Initialize the data loader.

        Args:
            source: The source to load the evaluation data from.
            split: The split to load the data from. Split is fixed for data loaders to "data",
                but you can slice it using the [Hugging Face API](https://huggingface.co/docs/datasets/v1.11.0/splits.html#slicing-api).
            required_keys: The required columns for the evaluation data.
        """
        self.source = source
        self.split = split
        self.required_keys = required_keys or set()

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

    async def load(self) -> Iterable[EvaluationDataT]:
        """
        Load the data.

        Returns:
            The loaded evaluation data.

        Raises:
            DataLoaderIncorrectFormatDataError: If evaluation dataset is incorrectly formatted.
        """
        data_path = await self.source.fetch()
        dataset = load_dataset(
            path=str(data_path.parent),
            data_files={"data": str(data_path.name)},
            split=self.split,
        )
        if not self.required_keys.issubset(dataset.features):
            raise DataLoaderIncorrectFormatDataError(
                required_features=list(self.required_keys),
                data_path=data_path,
            )
        return await self.map(dataset.to_list())

    @abstractmethod
    async def map(self, dataset: Iterable[dict]) -> Iterable[EvaluationDataT]:
        """
        Map the dataset to the evaluation data.

        Args:
            dataset: The dataset to map.

        Returns:
            The evaluation data.
        """
