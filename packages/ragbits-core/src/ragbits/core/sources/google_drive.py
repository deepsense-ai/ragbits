from typing import ClassVar, Generator
from ragbits.core.sources.base import Source

from contextlib import suppress, contextmanager
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
	from google.auth import exceptions
	from google.oath2 import service_account 
	from googleapiclient.discovery import build
	from googleapiclient.errors import HttpError
	from googleapiclient.discovery import Resource as GoogleAPIResource

SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

# Taken from open source
# Maps Google-native Drive MIME types → export MIME types
GOOGLE_EXPORT_MIME_MAP = {
		"application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # noqa: E501
		"application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa: E501
		"application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # noqa: E501
}

# taken from open source
# Maps export MIME types → file extensions
EXPORT_EXTENSION_MAP = {
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
		"application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
		"application/pdf": ".pdf",
		"text/html": ".html",
}

LRO_EXPORT_SIZE_THRESHOLD = 9 * 1024 * 1024  # 9MB

class GoogleDriveSource(Source):
	"""
	Handles source connection for google drive and provides methods to fetch files of specific extensions.
	"""
	
	drive_id: str
	protocol: ClassVar[str] = "google_drive"

	_google_drive_client: ClassVar[GoogleAPIResource] = None
	
	@classmethod
	@requires_dependencies(["googleapiclient"], "s3")
	def _set_client(cls, drive_id: str) -> None:
		"""
		Set the object to google drive api client if it hasn't been initialized yet.

		Args:
				

		Raises:
				ValueError: If credentials are incomplete.
				RuntimeError: If another error occurs.
		"""
		if cls._google_drive_client is None:
			try:
				cls._google_drive_client = build("drive", "v3", credentials=cls.get_credentials())
				cls._google_drive_client.files().get(fileId=drive_id).execute()  # This triggers a credentials check
			except exceptions.GoogleAuthError as e:
				raise ValueError("Google Drive credentials are missing or incomplete. Please configure them.") from e
			except HttpError as e:
				raise RuntimeError(f"Failed to initialize Google Drive client: {e}") from e

	@staticmethod
	def verify_drive_api_enabled(cls) -> None:
		from googleapiclient.errors import HttpError

		"""
		Makes a lightweight API call to verify that the Drive API is enabled.
		If the API is not enabled, an HttpError should be raised.
		"""
		try:
			# A very minimal call: list 1 file from the drive.
			cls._google_drive_client.list(
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
						"Google Drive API is not enabled for your project. \
						Please enable it in the Google Cloud Console."
				)
			else:
				raise Exception("Google drive API unreachable for an unknown reason!")

	

if __name__ == "__main__":
	main()