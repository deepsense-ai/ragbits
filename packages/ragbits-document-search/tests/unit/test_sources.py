import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from unittest.mock import MagicMock, patch

from ragbits.document_search.documents.sources import (
    LOCAL_STORAGE_DIR_ENV,
    GCSSource,
    HuggingFaceSource,
)

os.environ[LOCAL_STORAGE_DIR_ENV] = Path(__file__).parent.as_posix()


@runtime_checkable
class MockStorageProtocol(Protocol):
    """Protocol for mocking GCS storage client in tests."""

    async def download(self, bucket: str, object_name: str, timeout: int | None = None) -> bytes:
        """Download a file from storage."""
        ...

    async def list_objects(self, bucket: str, params: dict[str, str] | None = None) -> dict[str, list[dict[str, str]]]:
        """List objects in a bucket."""
        ...

    async def __aenter__(self) -> "MockStorageProtocol":
        """Enter async context."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # noqa: ANN401
        """Exit async context."""
        ...


class MockStorage(MockStorageProtocol):
    """Mock storage client for testing GCSSource."""

    def __init__(self, download_response: bytes | None = None):
        self.download_response = download_response or b"This is the content of the file."
        self.downloaded_files: list[tuple[str, str]] = []  # [(bucket, object_name), ...]
        self.listed_buckets: list[tuple[str, dict[str, str] | None]] = []  # [(bucket, params), ...]

    async def download(self, bucket: str, object_name: str, timeout: int | None = None) -> bytes:
        """Record download call and return mock response."""
        self.downloaded_files.append((bucket, object_name))
        return self.download_response

    async def list_objects(self, bucket: str, params: dict[str, str] | None = None) -> dict[str, list[dict[str, str]]]:
        """Record list call and return mock response."""
        self.listed_buckets.append((bucket, params))
        return {"items": [{"name": "doc.md"}]}

    async def __aenter__(self) -> "MockStorageProtocol":
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:  # noqa: ANN401
        """Exit async context."""
        pass


async def test_gcs_source_fetch() -> None:
    """Test fetching a file from GCS."""
    mock_storage = MockStorage()
    source = GCSSource(bucket="test-bucket", object_name="doc.md")
    source.set_storage(mock_storage)

    path = await source.fetch()

    assert source.id == "gcs:gs://test-bucket/doc.md"
    assert path.name == "doc.md"
    assert path.read_text() == "This is the content of the file."
    assert mock_storage.downloaded_files == [("test-bucket", "doc.md")]

    path.unlink()


async def test_huggingface_source_fetch() -> None:
    take = MagicMock(return_value=[{"content": "This is the content of the file.", "source": "doc.md"}])
    skip = MagicMock(return_value=MagicMock(take=take))
    data = MagicMock(skip=skip)
    source = HuggingFaceSource(path="org/docs", split="train", row=1)

    with patch("ragbits.document_search.documents.sources.load_dataset", return_value=data):
        path = await source.fetch()

    assert source.id == "huggingface:org/docs/train/1"
    assert path.name == "doc.md"
    assert path.read_text() == "This is the content of the file."

    path.unlink()
