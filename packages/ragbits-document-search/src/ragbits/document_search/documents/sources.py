from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

try:
    from gcloud.aio.storage import Storage

    HAS_GCLOUD_AIO = True
except ImportError:
    HAS_GCLOUD_AIO = False


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


class GoogleCloudStorageSource(Source):
    """
    An object representing a GCS file source.
    """

    source_type: Literal["google_cloud_storage_file"] = "google_cloud_storage_file"

    bucket: str
    object_name: str

    local_dir: Path = Path("tmp/ragbits/")

    def get_id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"bucket_name: {self.bucket}\nobject_name: {self.object_name}"

    async def fetch(self) -> Path:
        """
        Fetch the file from Google Cloud Storage and store it locally.

        The file is downloaded to a local directory specified by `local_dir`. If the file already exists locally,
        it will not be downloaded again. If the file doesn't exist locally, it will be fetched from GCS.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the required 'gcloud' package is not installed for Google Cloud Storage source.
        """

        if not HAS_GCLOUD_AIO:
            raise ImportError("You need to install the 'gcloud' package to use Google Cloud Storage")

        bucket_local_dir = self.local_dir / self.bucket

        bucket_local_dir.mkdir(parents=True, exist_ok=True)
        path = bucket_local_dir / self.object_name

        if not path.is_file():
            async with Storage() as client:
                await client.download_to_filename(bucket=self.bucket, object_name=self.object_name, filename=path)

        return path
