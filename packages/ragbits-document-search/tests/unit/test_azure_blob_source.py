from unittest.mock import AsyncMock, patch

import pytest

from ragbits.document_search.documents.azure_storage_source import AzureBlobStorage


@pytest.mark.asyncio
async def test_from_uri_parsing_error():
    list_of_paths_with_errors = [
        (
            "https://account_name.blob.core.windows.net/container_name/some**",
            "AzureBlobStorage only supports '*' at the end of path. Patterns like '**' or '?' are not supported.",
        ),
        (
            "https://account_name.blob.core.windows.net/container_name/some?",
            "AzureBlobStorage only supports '*' at the end of path. Patterns like '**' or '?' are not supported.",
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
            "AzureBlobStorage only supports '*' at the end of path. Invalid pattern: blob_name_*.json.",
        ),
    ]
    for path in list_of_paths_with_errors:
        with pytest.raises(ValueError) as e:
            await AzureBlobStorage.from_uri(path[0])
        assert path[1] == str(e.value)


@pytest.mark.asyncio
async def test_from_uri():
    good_path = "https://account_name.blob.core.windows.net/container_name/blob_name"
    sources = await AzureBlobStorage.from_uri(good_path)
    assert len(sources) == 1
    assert sources[0].container_name == "container_name"
    assert sources[0].blob_name == "blob_name"


@pytest.mark.asyncio
async def test_from_uri_listing():
    good_path_to_folder = "https://account_name.blob.core.windows.net/container_name/blob_name*"
    with patch.object(AzureBlobStorage, "list_sources", new_callable=AsyncMock) as mock_list_sources:
        await AzureBlobStorage.from_uri(good_path_to_folder)
        mock_list_sources.assert_called_once_with(container="container_name", blob_name="blob_name")
