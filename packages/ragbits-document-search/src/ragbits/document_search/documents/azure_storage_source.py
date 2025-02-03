import os
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.document_search.documents.sources import Source, get_local_storage_dir


class AzureBlobStorage(Source):
    """
    An object representing an Azure Blob Storage dataset source.
    """

    protocol: ClassVar[str] = "azure"
    container_name: str
    blob_name: str
    _blob_service: BlobServiceClient | None = None
    account_name: str | None = None

    @property
    def id(self) -> str:
        """
        Get the source ID, which is the full blob URL.
        """
        return f"{self.container_name}/{self.blob_name}"

    @classmethod
    async def _get_blob_service(cls, account_name: str | None = None) -> BlobServiceClient:
        """
        Returns an authenticated BlobServiceClient instance.

        Priority:
        1. DefaultAzureCredential (if account_name is set and authentication succeeds).
        2. Connection string (if authentication with DefaultAzureCredential fails).

        If neither method works, an error is raised.
        """
        # Try DefaultAzureCredential first if account_name is provided

        account_name = account_name if account_name else os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        if account_name:
            try:
                credential = DefaultAzureCredential()
                account_url = f"https://{account_name}.blob.core.windows.net"
                cls._blob_service = BlobServiceClient(account_url=account_url, credential=credential)
                return cls._blob_service
            except Exception as e:
                print(f"Warning: Failed to authenticate using DefaultAzureCredential. \nError: {str(e)}")

        # If DefaultAzureCredential fails or account_name is not provided, try the connection string
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            try:
                cls._blob_service = BlobServiceClient.from_connection_string(conn_str=connection_string)
                return cls._blob_service
            except Exception as e:
                raise ValueError("Failed to authenticate using connection string.") from e

        # If neither method works, raise an error
        raise ValueError(
            "No authentication method available. "
            "Provide an account_name for identity-based authentication or a connection string."
        )

    async def fetch(self) -> Path:
        """
        Downloads the blob to a temporary local file and returns the file path.
        """
        container_local_dir = get_local_storage_dir() / self.container_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        path = container_local_dir / self.blob_name
        try:
            blob_service = await self._get_blob_service(account_name=self.account_name)
            blob_client = blob_service.get_blob_client(container=self.container_name, blob=self.blob_name)

            # Ensure parent directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            # Download and write blob content to a file
            stream = blob_client.download_blob()
            content = stream.readall()
            with open(path, "wb") as file:
                file.write(content)

        except ResourceNotFoundError as e:
            raise SourceNotFoundError(f"Blob {self.blob_name} not found in container {self.container_name}") from e
        except Exception as e:
            raise SourceConnectionError() from e

        return path

    @classmethod
    async def from_uri(cls, path: str) -> Sequence["AzureBlobStorage"]:
        """
        Parses an Azure Blob Storage URI and returns an instance of AzureBlobStorage.
        """
        if "**" in path or "?" in path:
            raise ValueError(
                "AzureSource only supports '*' at the end of path. Patterns like '**' or '?' are not supported."
            )
        parsed = urlparse(path)

        if not parsed.netloc or not parsed.path:
            raise ValueError("Invalid Azure Blob Storage URI format")

        # if parsed.scheme != "azure":
        #     raise ValueError("Invalid scheme, expected 'azure://'")
        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) != 2:  # noqa PLR2004
            raise ValueError("URI must include both container and blob name (azure://container/blob)")

        container_name, blob_name = path_parts
        if "*" in blob_name:
            if not blob_name.endswith("*"):
                raise ValueError(f"AzureSource only supports '*' at the end of path. Invalid pattern: {blob_name}")
            blob_name = blob_name[:-1]
            return await cls.list_sources(container=container_name, blob_name=blob_name)

        # Return a single-element list (consistent with other sources)
        return [cls(container_name=container_name, blob_name=blob_name)]

    @classmethod
    async def list_sources(cls, container: str, blob_name: str = "") -> list["AzureBlobStorage"]:
        """List all sources in the given Azure container, matching the prefix.

        Args:
            container: The Azure container name.
            blob_name: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'azure-storage-blob' package is not installed
            SourceConnectionError: If there's an error connecting to Azure
        """
        blob_service = await cls._get_blob_service()
        try:
            container_client = blob_service.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=blob_name)
            return [AzureBlobStorage(container_name=container, blob_name=blob.name) for blob in blobs]
        except Exception as e:
            raise SourceConnectionError() from e
