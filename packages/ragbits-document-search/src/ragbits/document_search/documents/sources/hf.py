import re
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import ClassVar

from ragbits.core.audit import trace, traceable
from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import get_local_storage_dir

with suppress(ImportError):
    from datasets import load_dataset
    from datasets.exceptions import DatasetNotFoundError


class HuggingFaceSource(Source):
    """
    An object representing a Hugging Face dataset source.
    """

    path: str
    split: str = "train"
    row: int
    protocol: ClassVar[str] = "huggingface"

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"huggingface:{self.path}/{self.split}/{self.row}"

    @traceable
    @requires_dependencies(["datasets"], "huggingface")
    async def fetch(self) -> Path:
        """
        Fetch the file from Hugging Face and store it locally.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the 'huggingface' extra is not installed.
            SourceConnectionError: If the source connection fails.
            SourceNotFoundError: If the source document is not found.
        """
        with trace(path=self.path, split=self.split, row=self.row) as outputs:
            try:
                dataset = load_dataset(self.path, split=self.split, streaming=True)  # type: ignore
            except ConnectionError as exc:
                raise SourceConnectionError() from exc
            except DatasetNotFoundError as exc:  # type: ignore
                raise SourceNotFoundError(source_id=self.id) from exc

            try:
                data = next(iter(dataset.skip(self.row).take(1)))  # type: ignore
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
            return path

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Sequence["HuggingFaceSource"]:
        """Create HuggingFaceSource instances from a URI path.

        Pattern matching is not supported. The path must be in the format:
        huggingface://dataset_path/split/row

        Args:
            path: The path part of the URI (after huggingface://)

        Returns:
            A sequence containing a single HuggingFaceSource

        Raises:
            ValueError: If the path contains patterns or has invalid format
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

    @classmethod
    @traceable
    async def list_sources(cls, path: str, split: str) -> list["HuggingFaceSource"]:
        """
        List all sources in the given Hugging Face repository.

        Args:
            path: Path or name of the dataset.
            split: Dataset split.

        Returns:
            List of source objects.
        """
        sources = load_dataset(path, split=split)  # type: ignore
        cleaned_split = re.sub(r"\[.*?\]", "", split)
        return [
            cls(
                path=path,
                split=cleaned_split,
                row=row,
            )
            for row in range(len(sources))  # type: ignore
        ]
