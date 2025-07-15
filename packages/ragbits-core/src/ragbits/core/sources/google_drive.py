import os  # Import os for path joining and potential directory checks
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar

from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from google.auth import exceptions
    from google.oauth2 import service_account
    from googleapiclient.discovery import Resource as GoogleAPIResource
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload

_SCOPES = ["https://www.googleapis.com/auth/drive"]

# HTTP status codes
_HTTP_NOT_FOUND = 404
_HTTP_FORBIDDEN = 403

# Maps Google-native Drive MIME types → export MIME types
_GOOGLE_EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # noqa: E501
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
    "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # noqa: E501
    "application/vnd.google-apps.drawing": "image/png",
    "application/vnd.google-apps.script": "application/vnd.google-apps.script+json",
    "application/vnd.google-apps.site": "text/html",
    "application/vnd.google-apps.map": "application/json",
    "application/vnd.google-apps.form": "application/pdf",
}

# Maps export MIME types → file extensions
_EXPORT_EXTENSION_MAP = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "image/png": ".png",
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/plain": ".txt",
    "application/json": ".json",
}


class GoogleDriveSource(Source):
    """
    Handles source connection for Google Drive and provides methods to fetch files.
    """

    file_id: str
    file_name: str
    mime_type: str
    is_folder: bool = False
    protocol: ClassVar[str] = "google_drive"

    _google_drive_client: ClassVar["GoogleAPIResource | None"] = None
    _credentials_file_path: ClassVar[str | None] = None

    @classmethod
    def set_credentials_file_path(cls, path: str) -> None:
        """Set the path to the service account credentials file."""
        cls._credentials_file_path = path

    @classmethod
    def _initialize_client_from_creds(cls) -> None:
        """
        Initialize the Google Drive API client using service account credentials.

        This method creates and configures the Google Drive API client using the service account
        credentials file path that was previously set. It also performs a lightweight API call
        to verify that the client is properly configured and can access the Google Drive API.

        Raises:
            GoogleAuthError: If the service account credentials are invalid or incomplete.
            HttpError: If the Google Drive API is not enabled or accessible.
            Exception: If any other error occurs during client initialization.
        """
        creds = service_account.Credentials.from_service_account_file(cls._credentials_file_path, scopes=_SCOPES)
        cls._google_drive_client = build("drive", "v3", credentials=creds)
        cls._google_drive_client.files().list(
            pageSize=1, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()

    @classmethod
    @requires_dependencies(["googleapiclient", "google.oauth2"], "google_drive")
    def _get_client(cls) -> "GoogleAPIResource":
        """
        Get the Google Drive API client. Initializes it if not already set.

        Raises:
            ValueError: If credentials file path is not set or file does not exist.
            RuntimeError: If another error occurs during client initialization or API verification.
        """
        if cls._google_drive_client is None:
            if not cls._credentials_file_path or not Path(cls._credentials_file_path).is_file():
                raise ValueError(
                    "Google Drive credentials file path is not set or file does not exist. "
                    "Use GoogleDriveSource.set_credentials_file_path('/path/to/your/key.json')."
                )
            try:
                cls._initialize_client_from_creds()
            except exceptions.GoogleAuthError as e:
                raise ValueError("Google Drive credentials are missing or incomplete. Please configure them.") from e
            except HttpError as e:
                error_content = e.content.decode() if hasattr(e, "content") else ""
                lower_error = error_content.lower()
                if "drive api" in lower_error and ("not enabled" in lower_error or "not been used" in lower_error):
                    raise RuntimeError(
                        "Google Drive API is not enabled for your project. "
                        "Please enable it in the Google Cloud Console."
                    ) from e
                raise RuntimeError(f"Failed to initialize Google Drive client: {e}") from e
            except Exception as e:
                raise RuntimeError(
                    f"An unexpected error occurred during Google Drive client initialization: {e}"
                ) from e
        return cls._google_drive_client

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return (
            f"{self.protocol}:{self.file_id}/{self.file_name}" if self.file_name else f"{self.protocol}:{self.file_id}"
        )

    @classmethod
    @requires_dependencies(["googleapiclient"], "google_drive")
    def verify_drive_api_enabled(cls) -> None:
        """
        Makes a lightweight API call to verify that the Drive API is enabled.
        If the API is not enabled, an HttpError should be raised.
        """
        try:
            client = cls._get_client()
            client.files().list(
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                spaces="drive",
                pageSize=1,
                fields="files(id)",
            ).execute()
        except HttpError as e:
            error_content = e.content.decode() if hasattr(e, "content") else ""
            lower_error = error_content.lower()
            if "drive api" in lower_error and ("not enabled" in lower_error or "not been used" in lower_error):
                raise Exception(
                    "Google Drive API is not enabled for your project. " "Please enable it in the Google Cloud Console."
                ) from e
            else:
                raise Exception(f"Google Drive API unreachable for an unknown reason: {e}") from e
        except Exception as e:
            raise Exception(f"An unexpected error occurred during API verification: {e}") from e

    @traceable
    @requires_dependencies(["googleapiclient"], "google_drive")
    async def fetch(self) -> Path:
        """
        Fetch the file from Google Drive and store it locally.

        The file is downloaded to a local directory specified by `local_dir`. If the file already exists locally,
        it will not be downloaded again. If the file doesn't exist locally, it will be fetched from Google Drive.
        The local directory is determined by the environment variable `LOCAL_STORAGE_DIR`. If this environment
        variable is not set, a temporary directory is used.

        Returns:
            The local path to the downloaded file.

        Raises:
            ValueError: If the source instance represents a folder.
            FileNotFoundError: If the file is not found on Google Drive.
            RuntimeError: If an error occurs during download.
        """
        if self.is_folder:
            raise ValueError(f"Cannot directly fetch a folder. Use list_sources and iterate. Folder ID: {self.file_id}")

        local_dir = get_local_storage_dir()
        file_local_dir = local_dir / self.file_id
        file_local_dir.mkdir(parents=True, exist_ok=True)

        export_mime_type, file_extension = self._determine_file_extension()
        local_file_name = f"{self.file_name}{file_extension}"
        path = file_local_dir / local_file_name

        with trace(file_id=self.file_id, file_name=self.file_name, mime_type=self.mime_type) as outputs:
            if not path.is_file():
                client = self._get_client()
                try:
                    request = None
                    if self.mime_type.startswith("application/vnd.google-apps"):
                        request = client.files().export_media(fileId=self.file_id, mimeType=export_mime_type)
                    else:
                        request = client.files().get_media(fileId=self.file_id)

                    with open(path, "wb") as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            _, done = downloader.next_chunk()

                except HttpError as e:
                    if e.resp.status == _HTTP_NOT_FOUND:
                        raise FileNotFoundError(f"File with ID {self.file_id} not found on Google Drive.") from e
                    raise RuntimeError(f"Error downloading file {self.file_id}: {e}") from e
                except Exception as e:
                    raise RuntimeError(
                        f"An unexpected error occurred during file download for {self.file_id}: {e}"
                    ) from e
            outputs.path = path
        return path

    @classmethod
    @requires_dependencies(["googleapiclient"], "google_drive")
    async def list_sources(cls, drive_id: str, recursive: bool = True) -> Iterable[Self]:
        """
        Lists all files (and optionally recursively, subfolders and their files)
        within a given Google Drive folder/Shared Drive ID.

        Args:
            drive_id: The ID of the folder or Shared Drive to list files from.
            recursive: If True, lists files in subfolders recursively.

        Returns:
            An iterable of GoogleDriveSource instances representing the found files.
        """
        with trace(drive_id=drive_id, recursive=recursive) as outputs:
            client = cls._get_client()

            # Check if the drive_id is a folder, shared drive, or file
            is_folder, is_shared_drive, root_file_name = await cls._check_drive_type(client, drive_id)

            # If it's not a folder, return the single file
            if not is_folder:
                if not root_file_name:  # Error occurred in _check_drive_type
                    outputs.results = []
                    return outputs.results

                file_meta = (
                    client.files().get(fileId=drive_id, fields="id, name, mimeType", supportsAllDrives=True).execute()
                )
                outputs.results = [
                    cls(
                        file_id=file_meta["id"],
                        file_name=file_meta["name"],
                        mime_type=file_meta["mimeType"],
                        is_folder=False,
                    )
                ]
                return outputs.results

            # Process folder contents
            all_files_info: dict[str, Any] = {}

            await cls._recursive_list_files(client, drive_id, all_files_info, recursive, is_shared_drive)

            sources = [
                cls(file_id=info["id"], file_name=info["name"], mime_type=info["mimeType"], is_folder=info["is_folder"])
                for info in all_files_info.values()
            ]
            outputs.results = sources
            return outputs.results

    @classmethod
    async def _recursive_list_files(
        cls,
        client: "GoogleAPIResource",
        drive_id: str,
        all_files_info: dict[str, Any],
        recursive: bool,
        is_shared_drive: bool,
    ) -> None:
        """Helper method to recursively list files in a drive/folder."""

        async def _recursive_list(
            current_folder_id: str, current_path_prefix: str = "", current_root_shared_drive_id: str | None = None
        ) -> None:
            page_token = None
            query = f"'{current_folder_id}' in parents and trashed = false"

            while True:
                try:
                    list_params = {
                        "q": query,
                        "fields": "nextPageToken, files(id, name, mimeType)",
                        "pageSize": 1000,
                        "pageToken": page_token,
                        "supportsAllDrives": True,
                        "includeItemsFromAllDrives": True,
                    }

                    if current_root_shared_drive_id:
                        list_params["corpora"] = "drive"
                        list_params["driveId"] = current_root_shared_drive_id

                    results = client.files().list(**list_params).execute()

                    items = results.get("files", [])
                    for item in items:
                        full_local_name = os.path.join(current_path_prefix, item["name"])

                        if item["mimeType"] == "application/vnd.google-apps.folder":
                            if recursive:
                                next_root_shared_drive_id = current_root_shared_drive_id
                                if not next_root_shared_drive_id and is_shared_drive and current_folder_id == drive_id:
                                    next_root_shared_drive_id = drive_id

                                await _recursive_list(item["id"], full_local_name, next_root_shared_drive_id)
                        elif item["id"] not in all_files_info:
                            all_files_info[item["id"]] = {
                                "id": item["id"],
                                "name": item["name"],
                                "mimeType": item["mimeType"],
                                "is_folder": False,
                                "path_in_drive": full_local_name,
                            }

                    page_token = results.get("nextPageToken", None)
                    if not page_token:
                        break
                except HttpError as e:
                    with trace("folder_listing_error") as outputs:
                        outputs.error = f"Error listing folder {current_folder_id} (path: {current_path_prefix}): {e}"
                    if e.resp.status == _HTTP_FORBIDDEN:
                        with trace("folder_permission_denied") as outputs:
                            outputs.message = (
                                f"Permission denied for folder ID: {current_folder_id}. Skipping this folder."
                            )
                    break
                except Exception as e:
                    with trace("folder_listing_unexpected_error") as outputs:
                        outputs.error = f"An unexpected error occurred while listing folder {current_folder_id}: {e}"
                    break

        await _recursive_list(drive_id, current_root_shared_drive_id=(drive_id if is_shared_drive else None))

    @classmethod
    async def _check_drive_type(cls, client: "GoogleAPIResource", drive_id: str) -> tuple[bool, bool, str]:
        """
        Check if the drive ID is a folder, shared drive, or regular file.

        Returns:
            Tuple of (is_folder, is_shared_drive, file_name)
        """
        try:
            file_meta = (
                client.files()
                .get(
                    fileId=drive_id,
                    fields="id, name, mimeType, capabilities/canListChildren",
                    supportsAllDrives=True,
                )
                .execute()
            )

            root_file_name = file_meta["name"]
            is_folder = file_meta["mimeType"] == "application/vnd.google-apps.folder"
            is_shared_drive = False

            if is_folder:
                try:
                    client.drives().get(driveId=drive_id, fields="id").execute()
                    is_shared_drive = True
                    with trace("drive_type_identification") as outputs:
                        outputs.message = f"Identified '{root_file_name}' (ID: {drive_id}) as a Shared Drive."
                except HttpError as e:
                    if e.resp.status == _HTTP_NOT_FOUND:
                        with trace("drive_type_identification") as outputs:
                            outputs.message = (
                                f"Identified '{root_file_name}' (ID: {drive_id}) as a standard Google Drive folder."
                            )
                    else:
                        with trace("drive_type_identification_error") as outputs:
                            outputs.error = f"Error checking if ID '{drive_id}' is a Shared Drive (ignoring): {e}"
                            outputs.fallback = (
                                f"Assuming '{root_file_name}' (ID: {drive_id}) is a standard Google Drive folder."
                            )
                except Exception as e:
                    with trace("drive_type_identification_error") as outputs:
                        outputs.error = (
                            f"Unexpected error checking if ID '{drive_id}' is a Shared Drive (ignoring): {e}"
                        )
                        outputs.fallback = (
                            f"Assuming '{root_file_name}' (ID: {drive_id}) is a standard Google Drive folder."
                        )

            return is_folder, is_shared_drive, root_file_name

        except HttpError as e:
            if e.resp.status == _HTTP_NOT_FOUND:
                with trace("drive_not_found") as outputs:
                    outputs.error = (
                        f"Initial Drive ID '{drive_id}' not found. It might be non-existent or a permission issue."
                    )
            else:
                with trace("drive_metadata_error") as outputs:
                    outputs.error = f"Error fetching initial Drive ID '{drive_id}' metadata: {e}"
            return False, False, ""
        except Exception as e:
            with trace("drive_check_error") as outputs:
                outputs.error = f"An unexpected error occurred checking initial Drive ID '{drive_id}': {e}"
            return False, False, ""

    @classmethod
    async def _handle_single_id(cls, drive_id: str) -> Iterable[Self]:
        """
        Handle a single Google Drive ID, returning a source for the file or folder.

        Args:
            drive_id: The Google Drive file or folder ID.

        Returns:
            An iterable containing a single GoogleDriveSource instance.

        Raises:
            FileNotFoundError: If the Google Drive item with the given ID is not found.
            RuntimeError: If an error occurs during metadata fetching.
        """
        client = cls._get_client()
        try:
            file_meta = (
                client.files().get(fileId=drive_id, fields="id, name, mimeType", supportsAllDrives=True).execute()
            )
            is_folder = file_meta["mimeType"] == "application/vnd.google-apps.folder"
            return [
                cls(
                    file_id=file_meta["id"],
                    file_name=file_meta["name"],
                    mime_type=file_meta["mimeType"],
                    is_folder=is_folder,
                )
            ]
        except HttpError as e:
            if e.resp.status == _HTTP_NOT_FOUND:
                raise FileNotFoundError(f"Google Drive item with ID '{drive_id}' not found.") from e
            raise RuntimeError(f"Error fetching metadata for ID '{drive_id}': {e}") from e
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred for ID '{drive_id}': {e}") from e

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create GoogleDriveSource instances from a URI path.

        The supported URI formats:
        - <drive_id> - Matches a single file or folder by ID.
        - <folder_id>/*" - Matches all files directly within the folder/Shared Drive.
        - <folder_id>/<prefix>*" - Matches all files directly within the folder/Shared Drive starting with prefix.
        - <folder_id>/**" - Matches all files recursively within the folder/Shared Drive.

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from Google Drive.

        Raises:
            ValueError: If an unsupported pattern is used or path format is incorrect.
        """
        parts = path.split("/")
        drive_id = parts[0]

        if len(parts) == 1:
            return await cls._handle_single_id(drive_id)

        elif len(parts) > 1 and parts[-1] == "**":
            folder_id = parts[0]
            if not folder_id:
                raise ValueError("Folder ID cannot be empty for recursive listing.")
            return await cls.list_sources(drive_id=folder_id, recursive=True)

        elif len(parts) > 1 and parts[-1].endswith("*"):
            folder_id = parts[0]
            prefix_pattern = parts[-1][:-1]
            if not folder_id:
                raise ValueError("Folder ID cannot be empty for prefix listing.")

            all_direct_files = await cls.list_sources(drive_id=folder_id, recursive=False)
            filtered_sources = [source for source in all_direct_files if source.file_name.startswith(prefix_pattern)]
            return filtered_sources

        elif len(parts) > 1 and parts[-1] == "*":
            folder_id = parts[0]
            if not folder_id:
                raise ValueError("Folder ID cannot be empty for listing all direct children.")
            return await cls.list_sources(drive_id=folder_id, recursive=False)

        else:
            raise ValueError(f"Unsupported Google Drive URI pattern: {path}")

    def _determine_file_extension(self) -> tuple[str, str]:
        """
        Determine the appropriate file extension and export MIME type for the file.

        Returns:
            A tuple of (export_mime_type, file_extension)
        """
        export_mime_type = self.mime_type
        file_extension = ""

        if self.mime_type.startswith("application/vnd.google-apps"):
            export_mime_type = _GOOGLE_EXPORT_MIME_MAP.get(self.mime_type, "application/pdf")
            file_extension = _EXPORT_EXTENSION_MAP.get(export_mime_type, ".bin")
        elif "." in self.file_name:
            file_extension = Path(self.file_name).suffix
        else:
            file_extension = _EXPORT_EXTENSION_MAP.get(self.mime_type, ".bin")

        return export_mime_type, file_extension
