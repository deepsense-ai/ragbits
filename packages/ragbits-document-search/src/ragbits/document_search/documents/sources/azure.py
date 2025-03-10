import os
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import ClassVar, Optional
from urllib.parse import urlparse

from ragbits.core.audit import trace, traceable

with suppress(ImportError):
    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import get_local_storage_dir


class AzureBlobStorageSource(Source):
    """
    An object representing an Azure Blob Storage dataset source.
    """

    protocol: ClassVar[str] = "azure"
    account_name: str
    container_name: str
    blob_name: str
    _blob_service: Optional["BlobServiceClient"] = None

    @property
    def id(self) -> str:
        """
        Get the source ID, which is the full blob URL.
        """
        return f"azure://{self.account_name}/{self.container_name}/{self.blob_name}"

    @classmethod
    @requires_dependencies(["azure.storage.blob", "azure.identity"], "azure")
    async def _get_blob_service(cls, account_name: str) -> "BlobServiceClient":
        """
        Returns an authenticated BlobServiceClient instance.

        Priority:
        1. DefaultAzureCredential (if account_name is set and authentication succeeds).
        2. Connection string (if authentication with DefaultAzureCredential fails).

        If neither method works, an error is raised.

        Args:
            account_name: The name of the Azure Blob Storage account.

        Returns:
            BlobServiceClient: The authenticated Blob Storage client.

        Raises:
            ValueError: If the authentication fails.
        """
        try:
            credential = DefaultAzureCredential()
            account_url = f"https://{account_name}.blob.core.windows.net"
            cls._blob_service = BlobServiceClient(account_url=account_url, credential=credential)
            return cls._blob_service
        except Exception as e:
            print(f"Warning: Failed to authenticate using DefaultAzureCredential. \nError: {str(e)}")

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

    @requires_dependencies(["azure.storage.blob", "azure.core.exceptions"], "azure")
    async def fetch(self) -> Path:
        """
        Downloads the blob to a temporary local file and returns the file path.

        Returns:
            Path to the downloaded file.

        Raises:
            SourceNotFoundError: If the blob source is not available.
            SourceConnectionError: If the blob service connection is not available.
        """
        container_local_dir = get_local_storage_dir() / self.account_name / self.container_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        path = container_local_dir / self.blob_name
        with trace(account_name=self.account_name, container=self.container_name, blob=self.blob_name) as outputs:
            try:
                blob_service = await self._get_blob_service(account_name=self.account_name)
                blob_client = blob_service.get_blob_client(container=self.container_name, blob=self.blob_name)
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                stream = blob_client.download_blob()
                content = stream.readall()
                with open(path, "wb") as file:
                    file.write(content)

            except ResourceNotFoundError as e:
                raise SourceNotFoundError(f"Blob {self.blob_name} not found in container {self.container_name}") from e
            except Exception as e:
                raise SourceConnectionError() from e
            outputs.path = path
        return path

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Sequence["AzureBlobStorageSource"]:
        """
        Parses an Azure Blob Storage URI and returns an instance of AzureBlobStorageSource.

        Args:
            path (str): The Azure Blob Storage URI.

        Returns:
            Sequence["AzureBlobStorageSource"]: The parsed Azure Blob Storage URI.

        Raises:
            ValueError: If the Azure Blob Storage URI is invalid.
        """
        if "**" in path or "?" in path:
            raise ValueError(
                "AzureBlobStorageSource only supports '*' at the end of path. "
                "Patterns like '**' or '?' are not supported."
            )
        parsed = urlparse(path)
        if not parsed.netloc or not parsed.path:
            raise ValueError("Invalid Azure Blob Storage URI format.")

        if parsed.scheme != "https":
            raise ValueError("Invalid scheme, expected 'https://account_name.blob.core.windows.net'.")

        if parsed.netloc.endswith("blob.core.windows.net"):
            account_name = parsed.netloc.replace(".blob.core.windows.net", "")
        else:
            raise ValueError("Invalid scheme, expected 'https://account_name.blob.core.windows.net'.")

        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) != 2:  # noqa PLR2004
            raise ValueError("URI must include both container and blob name.")

        container_name, blob_name = path_parts
        if "*" in blob_name:
            if not blob_name.endswith("*") or "*" in blob_name[:-1]:
                raise ValueError(
                    f"AzureBlobStorageSource only supports '*' at the end of path. Invalid pattern: {blob_name}."
                )
            blob_name = blob_name[:-1]
            return await cls.list_sources(container=container_name, blob_name=blob_name, account_name=account_name)

        # Return a single-element list (consistent with other sources)
        return [cls(account_name=account_name, container_name=container_name, blob_name=blob_name)]

    @classmethod
    @requires_dependencies(["azure.storage.blob"], "azure")
    async def list_sources(
        cls, account_name: str, container: str, blob_name: str = ""
    ) -> list["AzureBlobStorageSource"]:
        """List all sources in the given Azure container, matching the prefix.

        Args:
            account_name (str): The Azure storage account name.
            container: The Azure container name.
            blob_name: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'azure-storage-blob' package is not installed
            SourceConnectionError: If there's an error connecting to Azure
        """
        with trace(account_name=account_name, container=container, blob_name=blob_name) as outputs:
            blob_service = await cls._get_blob_service(account_name=account_name)
            try:
                container_client = blob_service.get_container_client(container)
                blobs = container_client.list_blobs(name_starts_with=blob_name)
                outputs.results = [
                    AzureBlobStorageSource(container_name=container, blob_name=blob.name, account_name=account_name)
                    for blob in blobs
                ]
                return outputs.results
            except Exception as e:
                raise SourceConnectionError() from e
