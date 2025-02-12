from unittest.mock import AsyncMock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch
from azure.identity import DefaultAzureCredential

from ragbits.document_search.documents.azure_storage_source import AzureBlobStorageSource


def test_set_account_name(monkeypatch: MonkeyPatch):
    """Tests the Value Error when no account name is provided."""
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_NAME", raising=False)
    with pytest.raises(ValueError, match="Account name must be provided"):
        AzureBlobStorageSource(container_name="test_container", blob_name="test_blob")


def test_id():
    """Tests source id pattern"""
    expected_id = "azure://AA/CC/BB"
    storage = AzureBlobStorageSource(container_name="CC", blob_name="BB", account_name="AA")
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
    good_path = "https://account_name.blob.core.windows.net/container_name/blob_name"
    sources = await AzureBlobStorageSource.from_uri(good_path)
    assert len(sources) == 1
    assert sources[0].container_name == "container_name"
    assert sources[0].blob_name == "blob_name"


@pytest.mark.asyncio
async def test_from_uri_listing():
    """Test creating an Azure Blob Storage from a list of paths."""
    good_path_to_folder = "https://account_name.blob.core.windows.net/container_name/blob_name*"
    with patch.object(AzureBlobStorageSource, "list_sources", new_callable=AsyncMock) as mock_list_sources:
        await AzureBlobStorageSource.from_uri(good_path_to_folder)
        mock_list_sources.assert_called_once_with(
            container="container_name", blob_name="blob_name", account_name="account_name"
        )


@pytest.mark.asyncio
async def test_get_blob_service_no_credentials():
    """Test that ValueError is raised when no credentials are set."""
    with (
        patch.object(DefaultAzureCredential, "__init__", side_effect=Exception("Authentication failed")),
        patch("os.getenv", return_value=None),
        pytest.raises(ValueError, match="No authentication method available"),
    ):
        await AzureBlobStorageSource._get_blob_service(account_name="account_name")


@pytest.mark.asyncio
async def test_get_blob_service_with_connection_string():
    """Test that connection string is used when AZURE_STORAGE_ACCOUNT_NAME is not set."""
    with (
        patch.object(DefaultAzureCredential, "__init__", side_effect=Exception("Authentication failed")),
        patch("os.getenv", return_value="mock_connection_string"),
        patch("azure.storage.blob.BlobServiceClient.from_connection_string") as mock_from_connection_string,
    ):
        await AzureBlobStorageSource._get_blob_service(account_name="account_name")
        mock_from_connection_string.assert_called_once_with(conn_str="mock_connection_string")


@pytest.mark.asyncio
async def test_get_blob_service_with_default_credentials():
    """Test that default credentials are used when the account_name and credentials are available."""
    account_name = "test_account"
    account_url = f"https://{account_name}.blob.core.windows.net"

    with (
        patch("ragbits.document_search.documents.azure_storage_source.DefaultAzureCredential") as mock_credential,
        patch("ragbits.document_search.documents.azure_storage_source.BlobServiceClient") as mock_blob_client,
        patch("azure.storage.blob.BlobServiceClient.from_connection_string") as mock_from_connection_string,
    ):
        await AzureBlobStorageSource._get_blob_service(account_name)

        mock_credential.assert_called_once()
        mock_blob_client.assert_called_once_with(account_url=account_url, credential=mock_credential.return_value)
        mock_from_connection_string.assert_not_called()
