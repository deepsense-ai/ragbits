from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from gcloud.aio.storage import Storage as StorageClient


class GCSSource(Source):
    """
    Source for data stored in the Google Cloud Storage.
    """

    protocol: ClassVar[str] = "gcs"
    bucket: str
    object_name: str

    _storage: ClassVar["StorageClient | None"] = None

    @classmethod
    def set_storage(cls, storage: "StorageClient | None") -> None:
        """
        Set the storage client for all instances.
        """
        cls._storage = storage

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def _get_storage(cls) -> "StorageClient":
        """
        Get the storage client.
        """
        return cls._storage if cls._storage is not None else StorageClient()

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"gcs:{self.bucket}/{self.object_name}"

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
            The local path to the downloaded file.
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
    async def list_sources(cls, bucket: str, prefix: str = "") -> Iterable[Self]:
        """
        List all sources in the given GCS bucket, matching the prefix.

        Args:
            bucket: The GCS bucket.
            prefix: The prefix to match.

        Returns:
            The iterable of sources from the GCS bucket.
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
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create GCSSource instances from a URI path.

        The supported URI formats:
        - <bucket>/<folder>/*" - matches all files in the folder
        - <bucket>/<folder>/<prefix>*" - matches all files starting with prefix

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from the GCS bucket.

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
