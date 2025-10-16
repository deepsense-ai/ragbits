import re
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypeAlias

from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.sources.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.core.utils.decorators import requires_dependencies

if TYPE_CHECKING:
    from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict

    HFDataset: TypeAlias = Dataset | DatasetDict | IterableDataset | IterableDatasetDict


class HuggingFaceSource(Source):
    """
    Source for data stored in the Hugging Face repository.

    Supports two formats:
    1. Complete dataset: When no row is specified, downloads the entire dataset. Used for QA datasets.
    2. Single row: When a specific row is specified, downloads only that row. Used for document datasets
        (requires "content" and "source" columns).
    """

    protocol: ClassVar[str] = "hf"
    path: str
    name: str | None = None
    split: str = "train"
    row: int | None = None

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"hf:{self.path}/{self.split}{f'/{self.row}' if self.row is not None else ''}"

    def _load_dataset(self, streaming: bool = False) -> "HFDataset":
        """
        Load the dataset from Hugging Face.

        Args:
            streaming: Whether to stream the dataset.

        Returns:
            The loaded dataset.

        Raises:
            SourceConnectionError: If the source connection fails.
            SourceNotFoundError: If the source dataset is not found.
        """
        from datasets import load_dataset
        from datasets.exceptions import DatasetNotFoundError

        try:
            if self.name is not None and str(self.name).strip():
                return load_dataset(self.path, self.name, split=self.split, streaming=streaming)
            return load_dataset(self.path, split=self.split, streaming=streaming)
        except ConnectionError as exc:
            raise SourceConnectionError() from exc
        except DatasetNotFoundError as exc:
            raise SourceNotFoundError(source_id=self.id) from exc

    @requires_dependencies(["datasets"], "hf")
    async def fetch(self) -> Path:
        """
        Fetch the file from Hugging Face and store it locally.

        Returns:
            The local path to the downloaded file.

        Raises:
            SourceConnectionError: If the source connection fails.
            SourceNotFoundError: If the source document is not found.
        """
        with trace(path=self.path, split=self.split, row=self.row) as outputs:
            if self.row is not None:
                dataset = self._load_dataset(streaming=True)

                try:
                    data = next(iter(dataset.skip(self.row).take(1)))
                except StopIteration as exc:
                    raise SourceNotFoundError(source_id=self.id) from exc

                storage_dir = get_local_storage_dir()
                source_dir = storage_dir / Path(data["source"]).parent
                source_dir.mkdir(parents=True, exist_ok=True)
                path = storage_dir / data["source"]

                if not path.is_file():
                    with open(path, mode="w", encoding="utf-8") as file:
                        file.write(data["content"])
                outputs.path = path
            else:
                storage_dir = get_local_storage_dir()
                source_dir = storage_dir / self.path
                source_dir.mkdir(parents=True, exist_ok=True)
                path = source_dir / f"{self.split}.json"

                if not path.is_file():
                    dataset = self._load_dataset(streaming=False)
                    dataset.to_json(path)
                outputs.path = path

        return outputs.path

    @classmethod
    @traceable
    async def list_sources(cls, path: str, split: str) -> Iterable[Self]:
        """
        List all sources in the Hugging Face repository.

        Args:
            path: Path or name of the dataset.
            split: Dataset split.

        Returns:
            The iterable of sources from the Hugging Face repository.
        """
        from datasets import load_dataset

        sources = load_dataset(path, split=split)
        cleaned_split = re.sub(r"\[.*?\]", "", split)
        return [
            cls(
                path=path,
                split=cleaned_split,
                row=row,
            )
            for row in range(len(sources))
        ]

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create HuggingFaceSource instances from a URI path.

        The supported URI formats:
        - <dataset-path>/<split>/<row>

        Args:
            path: The URI path in the format described above.

        Returns:
           The iterable of sources from the Hugging Face repository.

        Raises:
            ValueError: If the path contains patterns or has invalid format.
        """
        if "*" in path or "?" in path:
            raise ValueError(
                "HuggingFaceSource does not support patterns. Path must be in format: dataset_path/split/row"
            )

        try:
            dataset_path, split, row = path.split("/")
            return [cls(path=dataset_path, split=split, row=int(row))]
        except ValueError as err:
            raise ValueError("Invalid HuggingFace path format. Expected: dataset_path/split/row") from err
