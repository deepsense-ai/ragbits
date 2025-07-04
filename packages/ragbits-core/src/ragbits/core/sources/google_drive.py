import os # Import os for path joining and potential directory checks
from collections.abc import Iterable
from contextlib import suppress, contextmanager
from pathlib import Path
from typing import ClassVar, Generator, Dict, Any
from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from google.auth import exceptions
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.discovery import Resource as GoogleAPIResource
    from googleapiclient.http import MediaIoBaseDownload
    import io # Needed for downloading file content

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Maps Google-native Drive MIME types → export MIME types
GOOGLE_EXPORT_MIME_MAP = {
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
EXPORT_EXTENSION_MAP = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "image/png": ".png",
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/plain": ".txt",
    "application/json": ".json",
}

LRO_EXPORT_SIZE_THRESHOLD = 9 * 1024 * 1024  # 9MB

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
                creds = service_account.Credentials.from_service_account_file(
                    cls._credentials_file_path, scopes=SCOPES
                )
                cls._google_drive_client = build('drive', 'v3', credentials=creds)
                cls._google_drive_client.files().list(
                    pageSize=1, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
                ).execute()
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
                raise RuntimeError(f"An unexpected error occurred during Google Drive client initialization: {e}") from e
        return cls._google_drive_client

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"{self.protocol}:{self.file_id}/{self.file_name}" if self.file_name else f"{self.protocol}:{self.file_id}"

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
            if "drive api" in lower_error and (
                    "not enabled" in lower_error or "not been used" in lower_error
            ):
                raise Exception(
                        "Google Drive API is not enabled for your project. "
                        "Please enable it in the Google Cloud Console."
                )
            else:
                raise Exception(f"Google Drive API unreachable for an unknown reason: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during API verification: {e}")


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

        file_extension = ""
        export_mime_type = self.mime_type

        if self.mime_type.startswith("application/vnd.google-apps"):
            export_mime_type = GOOGLE_EXPORT_MIME_MAP.get(self.mime_type, "application/pdf")
            file_extension = EXPORT_EXTENSION_MAP.get(export_mime_type, ".bin")
        else:
            if '.' in self.file_name:
                file_extension = Path(self.file_name).suffix
            else:
                file_extension = EXPORT_EXTENSION_MAP.get(self.mime_type, ".bin")

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

                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        # print(f"Download {int(status.progress() * 100)}%.") # Optional progress print

                    fh.seek(0)
                    with open(path, mode="wb") as file_object:
                        file_object.write(fh.read())
                except HttpError as e:
                    if e.resp.status == 404:
                        raise FileNotFoundError(f"File with ID {self.file_id} not found on Google Drive.") from e
                    raise RuntimeError(f"Error downloading file {self.file_id}: {e}") from e
                except Exception as e:
                    raise RuntimeError(f"An unexpected error occurred during file download for {self.file_id}: {e}") from e
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
            all_files_info: Dict[str, Any] = {}

            is_root_folder = False
            is_root_shared_drive = False
            root_file_name = ""

            try:
                file_meta = client.files().get(
                    fileId=drive_id,
                    fields="id, name, mimeType, capabilities/canListChildren",
                    supportsAllDrives=True
                ).execute()

                root_file_name = file_meta['name']
                if file_meta['mimeType'] == "application/vnd.google-apps.folder":
                    is_root_folder = True
                    try:
                        client.drives().get(driveId=drive_id, fields="id").execute()
                        is_root_shared_drive = True
                        print(f"Identified '{root_file_name}' (ID: {drive_id}) as a Shared Drive.")
                    except HttpError as e:
                        if e.resp.status == 404:
                            print(f"Identified '{root_file_name}' (ID: {drive_id}) as a standard Google Drive folder.")
                        else:
                            print(f"Error checking if ID '{drive_id}' is a Shared Drive (ignoring): {e}")
                            print(f"Assuming '{root_file_name}' (ID: {drive_id}) is a standard Google Drive folder.")
                    except Exception as e:
                        print(f"Unexpected error checking if ID '{drive_id}' is a Shared Drive (ignoring): {e}")
                        print(f"Assuming '{root_file_name}' (ID: {drive_id}) is a standard Google Drive folder.")
                else:
                    outputs.results = [cls(file_id=file_meta['id'], file_name=file_meta['name'], mime_type=file_meta['mimeType'], is_folder=False)]
                    return outputs.results
            except HttpError as e:
                if e.resp.status == 404:
                    print(f"Initial Drive ID '{drive_id}' not found. It might be non-existent or a permission issue.")
                else:
                    print(f"Error fetching initial Drive ID '{drive_id}' metadata: {e}")
                outputs.results = []
                return outputs.results
            except Exception as e:
                print(f"An unexpected error occurred checking initial Drive ID '{drive_id}': {e}")
                outputs.results = []
                return outputs.results

            async def _recursive_list(current_folder_id: str, current_path_prefix: str = "", current_root_shared_drive_id: str | None = None):
                page_token = None
                query = f"'{current_folder_id}' in parents and trashed = false"

                while True:
                    try:
                        list_params = {
                            'q': query,
                            'fields': "nextPageToken, files(id, name, mimeType)",
                            'pageSize': 1000,
                            'pageToken': page_token,
                            'supportsAllDrives': True,
                            'includeItemsFromAllDrives': True,
                        }

                        if current_root_shared_drive_id:
                            list_params['corpora'] = 'drive'
                            list_params['driveId'] = current_root_shared_drive_id

                        results = client.files().list(**list_params).execute()

                        items = results.get('files', [])
                        for item in items:
                            full_local_name = os.path.join(current_path_prefix, item["name"])

                            if item["mimeType"] == "application/vnd.google-apps.folder":
                                if recursive:
                                    next_root_shared_drive_id = current_root_shared_drive_id
                                    if not next_root_shared_drive_id and is_root_shared_drive and current_folder_id == drive_id:
                                        next_root_shared_drive_id = drive_id
                                    
                                    await _recursive_list(item["id"], full_local_name, next_root_shared_drive_id)
                            else:
                                if item['id'] not in all_files_info:
                                    all_files_info[item['id']] = {
                                        "id": item["id"],
                                        "name": item["name"],
                                        "mimeType": item["mimeType"],
                                        "is_folder": False,
                                        "path_in_drive": full_local_name
                                    }

                        page_token = results.get('nextPageToken', None)
                        if not page_token:
                            break
                    except HttpError as e:
                        print(f"Error listing folder {current_folder_id} (path: {current_path_prefix}): {e}")
                        if e.resp.status == 403:
                            print(f"Permission denied for folder ID: {current_folder_id}. Skipping this folder.")
                        break
                    except Exception as e:
                        print(f"An unexpected error occurred while listing folder {current_folder_id}: {e}")
                        break
            
            if is_root_folder:
                await _recursive_list(drive_id, current_root_shared_drive_id=(drive_id if is_root_shared_drive else None))
            else:
                outputs.results = []
                return outputs.results

            sources = [
                cls(file_id=info["id"], file_name=info["name"], mime_type=info["mimeType"], is_folder=info["is_folder"])
                for info in all_files_info.values()
            ]
            outputs.results = sources
            return outputs.results

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
        parts = path.split('/')
        drive_id = parts[0]

        if len(parts) == 1:
            client = cls._get_client()
            try:
                file_meta = client.files().get(
                    fileId=drive_id,
                    fields="id, name, mimeType",
                    supportsAllDrives=True
                ).execute()
                is_folder = file_meta['mimeType'] == "application/vnd.google-apps.folder"
                return [cls(file_id=file_meta['id'], file_name=file_meta['name'], mime_type=file_meta['mimeType'], is_folder=is_folder)]
            except HttpError as e:
                if e.resp.status == 404:
                    raise FileNotFoundError(f"Google Drive item with ID '{drive_id}' not found.") from e
                raise RuntimeError(f"Error fetching metadata for ID '{drive_id}': {e}") from e
            except Exception as e:
                raise RuntimeError(f"An unexpected error occurred for ID '{drive_id}': {e}") from e

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
            filtered_sources = [
                source for source in all_direct_files
                if source.file_name.startswith(prefix_pattern)
            ]
            return filtered_sources

        elif len(parts) > 1 and parts[-1] == "*":
            folder_id = parts[0]
            if not folder_id:
                raise ValueError("Folder ID cannot be empty for listing all direct children.")
            return await cls.list_sources(drive_id=folder_id, recursive=False)

        else:
            raise ValueError(f"Unsupported Google Drive URI pattern: {path}")

if __name__ == "__main__":
    import asyncio

    async def main_example():
        # Set your service account credentials file path
        # IMPORTANT: Replace 'google-token-json.json' with the actual path to your service account key file.
        GoogleDriveSource.set_credentials_file_path('google-token-json.json')

        # --- Listing files recursively in the 'prod' folder and downloading them ---
        print("\n--- Listing files recursively in 'prod' folder and downloading ---")
        try:
            prod_folder_id = '13gWkN6NiYx1pTBROV9qlOLSbj_HXzMzk'
            print(f"Attempting recursive listing for ID: {prod_folder_id}")
            sources_to_download = await GoogleDriveSource.from_uri(f"{prod_folder_id}/**")
            
            if sources_to_download:
                print(f"Found {len(sources_to_download)} items recursively in prod folder. Attempting to download files...")
                downloaded_count = 0
                for source in sources_to_download:
                    if not source.is_folder: # Only attempt to fetch files, not folders
                        try:
                            local_path = await source.fetch()
                            print(f"    Downloaded: {source.file_name} (ID: {source.file_id}) to {local_path}")
                            downloaded_count += 1
                        except Exception as e:
                            print(f"    Failed to download {source.file_name} (ID: {source.file_id}): {e}")
                print(f"\n--- Successfully downloaded {downloaded_count} files from '{prod_folder_id}' ---")
            else:
                print(f"No files found in {prod_folder_id} to download.")
        except Exception as e:
            print(f"An error occurred during recursive listing/download from prod folder: {e}")


		# --- Listing files recursively in the 'prod' folder and downloading them ---
        print("\n--- Listing files recursively in 'prod' folder and downloading ---")
        try:
            prod_folder_id = '1R9LzfTpa5jkmQ6mZsEEpBfzpXBOgqKjL'
            print(f"Attempting recursive listing for ID: {prod_folder_id}")
            sources_to_download = await GoogleDriveSource.from_uri(f"{prod_folder_id}/**")
            
            if sources_to_download:
                print(f"Found {len(sources_to_download)} items recursively in prod folder. Attempting to download files...")
                downloaded_count = 0
                for source in sources_to_download:
                    if not source.is_folder: # Only attempt to fetch files, not folders
                        try:
                            local_path = await source.fetch()
                            print(f"    Downloaded: {source.file_name} (ID: {source.file_id}) to {local_path}")
                            downloaded_count += 1
                        except Exception as e:
                            print(f"    Failed to download {source.file_name} (ID: {source.file_id}): {e}")
                print(f"\n--- Successfully downloaded {downloaded_count} files from '{prod_folder_id}' ---")
            else:
                print(f"No files found in {prod_folder_id} to download.")
        except Exception as e:
            print(f"An error occurred during recursive listing/download from prod folder: {e}")



		# 1R9LzfTpa5jkmQ6mZsEEpBfzpXBOgqKjL
       

        # --- Removed the specific invalid single file ID example ---
        print("\n--- Skipping single file fetch example with placeholder ID as requested ---")

    asyncio.run(main_example())