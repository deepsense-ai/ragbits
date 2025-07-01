from types import TracebackType
from typing import Any

from aiohttp import ClientSession
from gcloud.aio.storage import Storage as StorageClient

from ragbits.core.sources.gcs import GCSSource


class MockStorage(StorageClient):
    """Mock GCS storage client."""

    def __init__(self) -> None:
        """Initialize mock storage."""
        self.objects: dict[str, bytes] = {}
        self.downloaded_files: list[tuple[str, str]] = []

    async def download(
        self,
        bucket: str,
        object_name: str,
        *,
        headers: dict[str, Any] | None = None,
        timeout: int = 60,
        session: ClientSession | None = None,  # type: ignore
    ) -> bytes:
        """Mock download method."""
        key = f"{bucket}/{object_name}"
        self.downloaded_files.append((bucket, object_name))
        return self.objects.get(key, b"This is the content of the file.")

    async def list_objects(
        self,
        bucket: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, Any] | None = None,
        session: ClientSession | None = None,  # type: ignore
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Mock list_objects method."""
        prefix = params.get("prefix", "") if params else ""
        items = []
        for key in self.objects:
            if key.startswith(f"{bucket}/{prefix}"):
                items.append({"name": key.split("/", 1)[1]})
        return {"items": items}

    async def __aenter__(self) -> "MockStorage":
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context."""
        pass


async def test_gcs_source_fetch() -> None:
    """Test fetching a file from GCS."""
    mock_storage = MockStorage()
    source = GCSSource(bucket="test-bucket", object_name="doc.md")
    source.set_storage(mock_storage)

    path = await source.fetch()

    assert source.id == "gcs:test-bucket/doc.md"
    assert path.name == "doc.md"
    assert path.read_text() == "This is the content of the file."
    assert mock_storage.downloaded_files == [("test-bucket", "doc.md")]
