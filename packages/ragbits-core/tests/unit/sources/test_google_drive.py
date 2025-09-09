import json
import os
from pathlib import Path

import pytest
from googleapiclient.errors import HttpError

from ragbits.core.sources.google_drive import GoogleDriveExportFormat, GoogleDriveSource


@pytest.fixture(autouse=True)
def setup_clientid_json():
    """
    Saves the content of the GOOGLE_DRIVE_CLIENTID_JSON environment variable
    to a test JSON file, without modifying the environment variable itself.
    """
    clientid_json_content = os.environ.get("GOOGLE_DRIVE_CLIENTID_JSON")
    test_clientid_json_filename = "test_clientid.json"

    if clientid_json_content is not None:
        try:
            json.loads(clientid_json_content)

            with open(test_clientid_json_filename, "w") as f:
                f.write(clientid_json_content)
            print(f"Saved GOOGLE_DRIVE_CLIENTID_JSON content to '{test_clientid_json_filename}'.")
        except json.JSONDecodeError:
            print("Warning: GOOGLE_DRIVE_CLIENTID_JSON content is not valid JSON. Not saving to file.")
        except OSError as e:
            print(f"Error writing test_clientid.json file: {e}")
    else:
        print(f"Warning: GOOGLE_DRIVE_CLIENTID_JSON was not set. '{test_clientid_json_filename}' will not be created.")

    yield

    if os.path.exists(test_clientid_json_filename):
        os.remove(test_clientid_json_filename)
        print(f"Cleaned up test file: '{test_clientid_json_filename}'")


@pytest.fixture(autouse=True)
def setup_local_storage_dir(tmp_path: Path):
    """Set up a temporary local storage directory for tests."""
    original_local_storage_dir = os.environ.get("LOCAL_STORAGE_DIR")
    os.environ["LOCAL_STORAGE_DIR"] = str(tmp_path)
    yield
    if original_local_storage_dir is not None:
        os.environ["LOCAL_STORAGE_DIR"] = original_local_storage_dir
    else:
        del os.environ["LOCAL_STORAGE_DIR"]


@pytest.mark.asyncio
async def test_google_drive_impersonate():
    """Test service account impersonation with better error handling."""
    target_email = os.environ.get("GOOGLE_DRIVE_TARGET_EMAIL")
    credentials_file = "test_clientid.json"

    GoogleDriveSource.set_credentials_file_path(credentials_file)

    if target_email is None:
        pytest.skip("GOOGLE_DRIVE_TARGET_EMAIL environment variable not set")

    GoogleDriveSource.set_impersonation_target(target_email)

    unit_test_folder_id = os.environ.get("GOOGLE_SOURCE_UNIT_TEST_FOLDER")

    if unit_test_folder_id is None:
        pytest.skip("GOOGLE_SOURCE_UNIT_TEST_FOLDER environment variable not set")

    sources_to_download = await GoogleDriveSource.from_uri(f"{unit_test_folder_id}/**")
    downloaded_count = 0

    try:
        # Iterate through each source (file or folder) found
        for source in sources_to_download:
            # Only attempt to fetch files, as folders cannot be "downloaded" in the same way
            if not source.is_folder:
                try:
                    # Attempt to fetch (download) the file.
                    local_path = await source.fetch()
                    print(f"    Downloaded: '{source.file_name}' (ID: {source.file_id}) to '{local_path}'")
                    downloaded_count += 1
                except HttpError as e:
                    # Catch Google API specific HTTP errors (e.g., permission denied, file not found)
                    print(f"    Google API Error downloading '{source.file_name}' (ID: {source.file_id}): {e}")
                except Exception as e:
                    # Catch any other general exceptions during the download process
                    print(f"    Failed to download '{source.file_name}' (ID: {source.file_id}): {e}")
            else:
                print(f"    Skipping folder: '{source.file_name}' (ID: {source.file_id})")

    except Exception as e:
        # Catch any exceptions that occur during the initial setup or `from_uri` call
        print(f"An error occurred during test setup or source retrieval: {e}")

    finally:
        # This block ensures the final summary is printed regardless of errors
        print(f"\n--- Successfully downloaded {downloaded_count} files from '{unit_test_folder_id}' ---")
        # Assert that at least one file was downloaded if that's an expectation for the test
        # If no files are expected, or it's acceptable for 0 files to be downloaded, remove or adjust this assertion.
        assert downloaded_count > 0, "Expected to download at least one file, but downloaded 0."


@pytest.mark.asyncio
async def test_google_drive_source_fetch_file_not_found():
    """Test fetching a non-existent file."""
    import json
    import tempfile
    from unittest.mock import MagicMock, patch

    file_id = "nonexistent_file"
    file_name = "missing.txt"
    mime_type = "text/plain"

    # Create a temporary credentials file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_creds:
        json.dump({"type": "service_account", "client_email": "test@example.com"}, temp_creds)
        temp_creds.flush()

        GoogleDriveSource.set_credentials_file_path(temp_creds.name)
        source = GoogleDriveSource(file_id=file_id, file_name=file_name, mime_type=mime_type)

        # Mock HttpError
        mock_response = MagicMock()
        mock_response.status = 404
        http_error = HttpError(mock_response, b"File not found")

        # Mock the Google Drive client to simulate file not found
        with patch.object(GoogleDriveSource, "_get_client") as mock_client:
            mock_service = mock_client.return_value
            mock_service.files.return_value.get_media.return_value = MagicMock()

            with patch("ragbits.core.sources.google_drive.MediaIoBaseDownload") as mock_downloader:
                mock_downloader_instance = MagicMock()
                mock_downloader.return_value = mock_downloader_instance
                mock_downloader_instance.next_chunk.side_effect = http_error

                with pytest.raises(FileNotFoundError, match=f"File with ID {file_id} not found on Google Drive."):
                    await source.fetch()

    # Clean up the temporary file
    import os

    os.unlink(temp_creds.name)


@pytest.mark.asyncio
async def test_google_drive_source_fetch_folder_raises_error():
    """Test attempting to fetch a folder directly."""
    folder_id = "folder_abc"
    folder_name = "MyFolder"
    mime_type = "application/vnd.google-apps.folder"

    source = GoogleDriveSource(file_id=folder_id, file_name=folder_name, mime_type=mime_type, is_folder=True)

    with pytest.raises(ValueError, match="Cannot directly fetch a folder"):
        await source.fetch()


@pytest.mark.asyncio
async def test_google_drive_source_unsupported_uri_pattern():
    """Test handling of unsupported URI patterns."""
    with pytest.raises(ValueError, match="Unsupported Google Drive URI pattern:"):
        await GoogleDriveSource.from_uri("folder_id/invalid_pattern")

    with pytest.raises(ValueError, match="Unsupported Google Drive URI pattern:"):
        await GoogleDriveSource.from_uri("just_a_path/to/a/file.txt")


@pytest.mark.asyncio
async def test_google_drive_source_fetch_file():
    """
    Test fetching files from a specified Google Drive folder.

    This test iterates through items in a Google Drive folder, attempts to
    download files (skipping folders), and reports on the success or failure
    of each download. It also tracks the total number of successfully
    downloaded files.
    """
    unit_test_folder_id = os.environ.get("GOOGLE_SOURCE_UNIT_TEST_FOLDER")

    if unit_test_folder_id is None:
        pytest.skip("GOOGLE_SOURCE_UNIT_TEST_FOLDER environment variable not set")

    # Initialize a counter for successfully downloaded files
    downloaded_count = 0

    print(f"\n--- Starting download test from Google Drive folder ID: '{unit_test_folder_id}' ---")

    try:
        # Create a GoogleDriveSource instance to fetch all items within the specified folder.
        # The "**" pattern indicates a recursive search within the folder.
        sources_to_download = await GoogleDriveSource.from_uri(f"{unit_test_folder_id}/**")

        if not sources_to_download:
            print(f"No sources found in folder ID: {unit_test_folder_id}. Please check the folder ID and permissions.")
            return  # Exit if no sources are found

        # Iterate through each source (file or folder) found
        for source in sources_to_download:
            # Only attempt to fetch files, as folders cannot be "downloaded" in the same way
            if not source.is_folder:
                try:
                    # Attempt to fetch (download) the file.
                    local_path = await source.fetch()
                    print(f"    Downloaded: '{source.file_name}' (ID: {source.file_id}) to '{local_path}'")
                    downloaded_count += 1
                except HttpError as e:
                    # Catch Google API specific HTTP errors (e.g., permission denied, file not found)
                    print(f"    Google API Error downloading '{source.file_name}' (ID: {source.file_id}): {e}")
                except Exception as e:
                    # Catch any other general exceptions during the download process
                    print(f"    Failed to download '{source.file_name}' (ID: {source.file_id}): {e}")
            else:
                print(f"    Skipping folder: '{source.file_name}' (ID: {source.file_id})")

    except Exception as e:
        # Catch any exceptions that occur during the initial setup or `from_uri` call
        print(f"An error occurred during test setup or source retrieval: {e}")

    finally:
        # This block ensures the final summary is printed regardless of errors
        print(f"\n--- Successfully downloaded {downloaded_count} files from '{unit_test_folder_id}' ---")
        # Assert that at least one file was downloaded if that's an expectation for the test
        # If no files are expected, or it's acceptable for 0 files to be downloaded, remove or adjust this assertion.
        assert downloaded_count > 0, "Expected to download at least one file, but downloaded 0."


def test_determine_file_extension_override():
    """Ensure overriding export MIME type yields expected extension."""
    src = GoogleDriveSource(
        file_id="dummy",
        file_name="MyDoc",
        mime_type="application/vnd.google-apps.document",
    )

    export_mime, extension = src._determine_file_extension(override_mime=GoogleDriveExportFormat.PDF.value)

    assert export_mime == GoogleDriveExportFormat.PDF.value
    assert extension == ".pdf"
