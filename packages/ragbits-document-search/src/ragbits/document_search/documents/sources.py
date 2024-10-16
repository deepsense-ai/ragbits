import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

try:
    from gcloud.aio.storage import Storage

    HAS_GCLOUD_AIO = True
except ImportError:
    HAS_GCLOUD_AIO = False

LOCAL_STORAGE_DIR_ENV = "LOCAL_STORAGE_DIR_ENV"


class Source(BaseModel, ABC):
    """
    An object representing a source.
    """

    @abstractmethod
    def get_id(self) -> str:
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

    def get_id(self) -> str:
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
        """
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
        sources = []
        for file_path in path.glob(file_pattern):
            sources.append(cls(path=file_path))
        return sources


class GCSSource(Source):
    """
    An object representing a GCS file source.
    """

    source_type: Literal["gcs"] = "gcs"

    bucket: str
    object_name: str

    def get_id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"gcs:gs://{self.bucket}/{self.object_name}"

    async def fetch(self) -> Path:
        """
        Fetch the file from Google Cloud Storage and store it locally.

        The file is downloaded to a local directory specified by `local_dir`. If the file already exists locally,
        it will not be downloaded again. If the file doesn't exist locally, it will be fetched from GCS.
        The local directory is determined by the environment variable `LOCAL_STORAGE_DIR_ENV`. If this environment
        variable is not set, a temporary directory is used.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the required 'gcloud' package is not installed for Google Cloud Storage source.
        """

        if not HAS_GCLOUD_AIO:
            raise ImportError("You need to install the 'gcloud-aio-storage' package to use Google Cloud Storage")

        if (local_dir_env := os.getenv(LOCAL_STORAGE_DIR_ENV)) is None:
            local_dir = Path(tempfile.gettempdir()) / "ragbits"
        else:
            local_dir = Path(local_dir_env)

        bucket_local_dir = local_dir / self.bucket
        bucket_local_dir.mkdir(parents=True, exist_ok=True)
        path = bucket_local_dir / self.object_name

        if not path.is_file():
            async with Storage() as client:
                content = await client.download(self.bucket, self.object_name)
                Path(bucket_local_dir / self.object_name).parent.mkdir(parents=True, exist_ok=True)
                with open(path, mode="wb+") as file_object:
                    file_object.write(content)

        return path

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
        if not HAS_GCLOUD_AIO:
            raise ImportError("You need to install the 'gcloud-aio-storage' package to use Google Cloud Storage")

        async with Storage() as client:
            objects = await client.list_objects(bucket, params={"prefix": prefix})
            sources = []
            for obj in objects["items"]:
                sources.append(cls(bucket=bucket, object_name=obj["name"]))
            return sources
