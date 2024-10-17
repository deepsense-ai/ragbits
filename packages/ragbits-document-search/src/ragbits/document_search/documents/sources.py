import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

try:
    from datasets import load_dataset
    from datasets.exceptions import DatasetNotFoundError
    from gcloud.aio.storage import Storage
except ImportError:
    pass

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError

LOCAL_STORAGE_DIR_ENV = "LOCAL_STORAGE_DIR"


class Source(BaseModel, ABC):
    """
    An object representing a source.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """
        Get the source ID.

        Returns:
            The source ID.
        """

    @abstractmethod
    async def fetch(self) -> Path:
        """
        Load the source.

        Returns:
            The path to the source.
        """


class LocalFileSource(Source):
    """
    An object representing a local file source.
    """

    source_type: Literal["local_file"] = "local_file"
    path: Path

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"local_file:{self.path.absolute()}"

    async def fetch(self) -> Path:
        """
        Fetch the source.

        Returns:
            The local path to the object fetched from the source.

        Raises:
            SourceNotFoundError: If the source document is not found.
        """
        if not self.path.is_file():
            raise SourceNotFoundError(source_id=self.id)
        return self.path

    @classmethod
    def list_sources(cls, path: Path, file_pattern: str = "*") -> list["LocalFileSource"]:
        """
        List all sources in the given directory, matching the file pattern.

        Args:
            path: The path to the directory.
            file_pattern: The file pattern to match.

        Returns:
            List of source objects.
        """
        return [cls(path=file_path) for file_path in path.glob(file_pattern)]


class GCSSource(Source):
    """
    An object representing a GCS file source.
    """

    source_type: Literal["gcs"] = "gcs"
    bucket: str
    object_name: str

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"gcs:gs://{self.bucket}/{self.object_name}"

    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def fetch(self) -> Path:
        """
        Fetch the file from Google Cloud Storage and store it locally.

        The file is downloaded to a local directory specified by `local_dir`. If the file already exists locally,
        it will not be downloaded again. If the file doesn't exist locally, it will be fetched from GCS.
        The local directory is determined by the environment variable `LOCAL_STORAGE_DIR`. If this environment
        variable is not set, a temporary directory is used.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the 'gcp' extra is not installed.
        """
        local_dir = get_local_storage_dir()
        bucket_local_dir = local_dir / self.bucket
        bucket_local_dir.mkdir(parents=True, exist_ok=True)
        path = bucket_local_dir / self.object_name

        if not path.is_file():
            async with Storage() as client:  # type: ignore
                # TODO: Add error handling for download
                content = await client.download(self.bucket, self.object_name)
                Path(bucket_local_dir / self.object_name).parent.mkdir(parents=True, exist_ok=True)
                with open(path, mode="wb+") as file_object:
                    file_object.write(content)

        return path

    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    @classmethod
    async def list_sources(cls, bucket: str, prefix: str = "") -> list["GCSSource"]:
        """
        List all sources in the given GCS bucket, matching the prefix.

        Args:
            bucket: The GCS bucket.
            prefix: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'gcloud-aio-storage' package is not installed
        """
        async with Storage() as client:
            objects = await client.list_objects(bucket, params={"prefix": prefix})
            sources = []
            for obj in objects["items"]:
                sources.append(cls(bucket=bucket, object_name=obj["name"]))
            return sources


class HuggingFaceSource(Source):
    """
    An object representing a Hugging Face dataset source.
    """

    source_type: Literal["huggingface"] = "huggingface"
    path: str
    split: str = "train"
    row: int

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"huggingface:{self.path}/{self.split}/{self.row}"

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

        return path


def get_local_storage_dir() -> Path:
    """
    Get the local storage directory.

    The local storage directory is determined by the environment variable `LOCAL_STORAGE_DIR`. If this environment
    variable is not set, a temporary directory is used.

    Returns:
        The local storage directory.
    """
    return (
        Path(local_dir_env)
        if (local_dir_env := os.getenv(LOCAL_STORAGE_DIR_ENV)) is not None
        else Path(tempfile.gettempdir()) / "ragbits"
    )
