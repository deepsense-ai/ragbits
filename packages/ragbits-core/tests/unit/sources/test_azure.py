from pathlib import Path, PosixPath
from unittest.mock import ANY, AsyncMock, MagicMock, mock_open, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential

from ragbits.core.sources.azure import AzureBlobStorageSource
from ragbits.core.sources.exceptions import SourceNotFoundError

ACCOUNT_NAME = "test_account"
BLOB_NAME = "test_blob.txt"
CONTAINER_NAME = "test_container"
SOURCE_ID = "azure:test_account/test_container/test_blob.txt"


def test_id():
    """Tests source id pattern"""
    expected_id = SOURCE_ID
    storage = AzureBlobStorageSource(container_name=CONTAINER_NAME, blob_name=BLOB_NAME, account_name=ACCOUNT_NAME)
    assert expected_id == storage.id


@pytest.mark.asyncio
async def test_from_uri_parsing_error():
    """Tests wrong paths in creating AzureBlobStorageSource from URI"""
    list_of_paths_with_errors = [
        (
            "https://account_name.blob.core.windows.net/container_name/some**",
            "AzureBlobStorageSource only supports '*' at the end of path. Patterns like '**' or '?' are not supported.",
        ),
        (
            "https://account_name.blob.core.windows.net/container_name/some?",
            "AzureBlobStorageSource only supports '*' at the end of path. Patterns like '**' or '?' are not supported.",
        ),
        ("Some string not url", "Invalid Azure Blob Storage URI format."),
        (
            "https://just.some.url.pl/with_potential_container_name/and_blob_name",
            "Invalid scheme, expected 'https://account_name.blob.core.windows.net'.",
        ),
        (
            "htps://account_name.blob.core.windows.net/container_name/blob_name",
            "Invalid scheme, expected 'https://account_name.blob.core.windows.net'.",
        ),
        ("some_path/but_without/scheme", "Invalid Azure Blob Storage URI format."),
        ("https://account_name.blob.core.windows.net/to_short_path", "URI must include both container and blob name."),
        (
            "https://account_name.blob.core.windows.net/container_name/blob_name_*.json",
            "AzureBlobStorageSource only supports '*' at the end of path. Invalid pattern: blob_name_*.json.",
        ),
        (
            "https://account_name.blob.core.windows.net/container_name/blob*_name_*.json",
            "AzureBlobStorageSource only supports '*' at the end of path. Invalid pattern: blob*_name_*.json.",
        ),
    ]
    for path in list_of_paths_with_errors:
        with pytest.raises(ValueError) as e:
            await AzureBlobStorageSource.from_uri(path[0])
        assert path[1] == str(e.value)


@pytest.mark.asyncio
async def test_from_uri():
    """Test creating an Azure Blob Storage from URI."""
    good_path = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{BLOB_NAME}"
    sources = await AzureBlobStorageSource.from_uri(good_path)
    assert sources == [
        AzureBlobStorageSource(
            account_name=ACCOUNT_NAME,
            blob_name=BLOB_NAME,
            container_name=CONTAINER_NAME,
        )
    ]


@pytest.mark.asyncio
async def test_from_uri_listing():
    """Test creating an Azure Blob Storage from a list of paths."""
    good_path_to_folder = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/blob_name*"
    with patch.object(AzureBlobStorageSource, "list_sources", new_callable=AsyncMock) as mock_list_sources:
        await AzureBlobStorageSource.from_uri(good_path_to_folder)
        mock_list_sources.assert_called_once_with(
            container=CONTAINER_NAME, blob_name="blob_name", account_name=ACCOUNT_NAME
        )


def test_get_blob_service_no_credentials():
    """Test that Exception propageted when no credentials are set."""
    with (
        patch.object(DefaultAzureCredential, "__init__", side_effect=Exception("Authentication failed")),
        patch("os.getenv", return_value=None),
        pytest.raises(Exception, match="Authentication failed"),
    ):
        AzureBlobStorageSource._get_blob_service(account_name=ACCOUNT_NAME)


def test_get_blob_service_with_connection_string():
    """Test that connection string is used when AZURE_STORAGE_ACCOUNT_NAME is not set."""
    with (
        patch.object(DefaultAzureCredential, "__init__", side_effect=Exception("Authentication failed")),
        patch("os.getenv", return_value="mock_connection_string"),
        patch("azure.storage.blob.BlobServiceClient.from_connection_string") as mock_from_connection_string,
    ):
        AzureBlobStorageSource._get_blob_service(account_name="account_name")
        mock_from_connection_string.assert_called_once_with(conn_str="mock_connection_string", retry_policy=ANY)


def test_get_blob_service_with_default_credentials():
    """Test that default credentials are used when the account_name and credentials are available."""
    account_url = f"https://{ACCOUNT_NAME}.blob.core.windows.net"

    with (
        patch("ragbits.core.sources.azure.DefaultAzureCredential") as mock_credential,
        patch("ragbits.core.sources.azure.BlobServiceClient") as mock_blob_client,
        patch("azure.storage.blob.BlobServiceClient.from_connection_string") as mock_from_connection_string,
    ):
        AzureBlobStorageSource._get_blob_service(ACCOUNT_NAME)

        mock_credential.assert_called_once()
        mock_blob_client.assert_called_once_with(
            account_url=account_url,
            credential=mock_credential.return_value,
            retry_policy=ANY,
        )
        mock_from_connection_string.assert_not_called()


@pytest.mark.asyncio
async def test_fetch():
    blob_content = b"Sample blob content"

    mock_blob_service_client = MagicMock()
    mock_blob_client = mock_blob_service_client.get_blob_client.return_value
    mock_blob_client.download_blob.return_value.readall = MagicMock(return_value=blob_content)

    with (
        patch.object(AzureBlobStorageSource, "_get_blob_service", return_value=mock_blob_service_client),
        patch(
            "ragbits.core.sources.azure.get_local_storage_dir",
            return_value=Path("/test_path"),
        ),
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()) as mocked_file,
    ):
        storage = AzureBlobStorageSource(account_name=ACCOUNT_NAME, container_name=CONTAINER_NAME, blob_name=BLOB_NAME)
        downloaded_path = await storage.fetch()

        expected_path = PosixPath("/test_path/test_account/test_container/test_blob.txt")
        assert downloaded_path == expected_path
        mocked_file.assert_called_once_with(expected_path, "wb")
        mocked_file().write.assert_called_once_with(blob_content)


@pytest.mark.asyncio
async def test_fetch_raises_error():
    non_existing_blob_name = "non_existent_blob.txt"

    mock_blob_service_client = MagicMock()
    mock_blob_client = mock_blob_service_client.get_blob_client.return_value
    mock_blob_client.download_blob.side_effect = ResourceNotFoundError

    with (
        patch.object(AzureBlobStorageSource, "_get_blob_service", return_value=mock_blob_service_client),
        patch(
            "ragbits.core.sources.azure.get_local_storage_dir",
            return_value=Path("/test_path"),
        ),
        patch("pathlib.Path.mkdir"),
    ):
        storage = AzureBlobStorageSource(
            account_name=ACCOUNT_NAME, container_name=CONTAINER_NAME, blob_name=non_existing_blob_name
        )

        with pytest.raises(
            SourceNotFoundError, match=f"Blob {non_existing_blob_name} not found in container {CONTAINER_NAME}"
        ):
            await storage.fetch()
