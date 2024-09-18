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

    path: Path

    def get_id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"bucket_name: {self.bucket}\nobject_name: {self.path}"

    async def fetch(self) -> Path:
        """
        Fetch the source.

        Returns:
            Tuple containing bucket name and file path.

        Raises:
            ImportError: If the required 'gcloud' package is not installed for Google Cloud Storage source.
        """

        if not HAS_GCLOUD_AIO:
            raise ImportError("You need to install the 'gcloud' package to use Google Cloud Storage")

        async with Storage() as client:
            await client.download_to_filename(bucket=self.bucket, object_name=self.object_name, filename=self.path)

        return self.path
