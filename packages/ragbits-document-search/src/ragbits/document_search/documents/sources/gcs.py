from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import ClassVar

from ragbits.core.audit import trace, traceable
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import get_local_storage_dir

with suppress(ImportError):
    from gcloud.aio.storage import Storage as StorageClient

from ragbits.core.utils.decorators import requires_dependencies


class GCSSource(Source):
    """An object representing a GCS file source."""

    bucket: str
    object_name: str
    protocol: ClassVar[str] = "gcs"
    _storage: ClassVar["StorageClient | None"] = None  # Storage client for dependency injection

    @classmethod
    def set_storage(cls, storage: "StorageClient | None") -> None:
        """Set the storage client for all instances.

        Args:
            storage: The `gcloud-aio-storage` `Storage` object to use as the storage client.
                By default, the object will be created automatically.
        """
        cls._storage = storage

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def _get_storage(cls) -> "StorageClient":
        """Get the storage client.

        Returns:
            The storage client to use. If none was injected, creates a new one.
        """
        if cls._storage is not None:
            return cls._storage

        return StorageClient()

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"gcs:gs://{self.bucket}/{self.object_name}"

    @traceable
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
        with trace(bucket=self.bucket, object=self.object_name) as outputs:
            if not path.is_file():
                storage = await self._get_storage()
                async with storage as client:
                    content = await client.download(self.bucket, self.object_name)
                    Path(bucket_local_dir / self.object_name).parent.mkdir(parents=True, exist_ok=True)
                    with open(path, mode="wb+") as file_object:
                        file_object.write(content)
            outputs.path = path
        return path

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def list_sources(cls, bucket: str, prefix: str = "") -> list["GCSSource"]:
        """List all sources in the given GCS bucket, matching the prefix.

        Args:
            bucket: The GCS bucket.
            prefix: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'gcloud-aio-storage' package is not installed
        """
        with trace() as outputs:
            async with await cls._get_storage() as storage:
                result = await storage.list_objects(bucket, params={"prefix": prefix})
                items = result.get("items", [])
                outputs.results = [
                    cls(bucket=bucket, object_name=item["name"]) for item in items if not item["name"].endswith("/")
                ]
                return outputs.results

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Sequence["GCSSource"]:
        """Create GCSSource instances from a URI path.

        Supports simple prefix matching with '*' at the end of path.
        For example:
        - "bucket/folder/*" - matches all files in the folder
        - "bucket/folder/prefix*" - matches all files starting with prefix

        More complex patterns like '**' or '?' are not supported.

        Args:
            path: The path part of the URI (after gcs://). Can end with '*' for pattern matching.

        Returns:
            A sequence of GCSSource objects matching the pattern

        Raises:
            ValueError: If an unsupported pattern is used
        """
        if "**" in path or "?" in path:
            raise ValueError(
                "GCSSource only supports '*' at the end of path. Patterns like '**' or '?' are not supported."
            )

        # Split into bucket and prefix
        bucket, prefix = path.split("/", 1) if "/" in path else (path, "")

        if "*" in prefix:
            if not prefix.endswith("*"):
                raise ValueError(f"GCSSource only supports '*' at the end of path. Invalid pattern: {prefix}")
            # Remove the trailing * for GCS prefix listing
            prefix = prefix[:-1]
            return await cls.list_sources(bucket=bucket, prefix=prefix)

        return [cls(bucket=bucket, object_name=prefix)]
