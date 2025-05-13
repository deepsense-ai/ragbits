import os
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.sources.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from azure.core.exceptions import ResourceNotFoundError
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ExponentialRetry


class AzureBlobStorageSource(Source):
    """
    Source for data stored in the Azure Blob Storage.
    """

    protocol: ClassVar[str] = "azure"
    account_name: str
    container_name: str
    blob_name: str

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"azure:{self.account_name}/{self.container_name}/{self.blob_name}"

    @requires_dependencies(["azure.storage.blob", "azure.core.exceptions"], "azure")
    async def fetch(self) -> Path:
        """
        Downloads the blob to a temporary local file and returns the file path.

        Returns:
            The local path to the downloaded file.

        Raises:
            SourceNotFoundError: If the blob source is not available.
            SourceConnectionError: If the blob service connection is not available.
        """
        container_local_dir = get_local_storage_dir() / self.account_name / self.container_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        path = container_local_dir / self.blob_name
        with trace(account_name=self.account_name, container=self.container_name, blob=self.blob_name) as outputs:
            try:
                blob_service = self._get_blob_service(self.account_name)
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
    @requires_dependencies(["azure.storage.blob"], "azure")
    async def list_sources(
        cls,
        account_name: str,
        container: str,
        blob_name: str = "",
    ) -> Iterable[Self]:
        """
        List all sources in the given Azure container, matching the prefix.

        Args:
            account_name: The Azure storage account name.
            container: The Azure container name.
            blob_name: The prefix to match.

        Returns:
            The iterable of sources from the Azure Blob Storage container.

        Raises:
            SourceConnectionError: If there's an error connecting to Azure
        """
        with trace(account_name=account_name, container=container, blob_name=blob_name) as outputs:
            try:
                blob_service = cls._get_blob_service(account_name)
                container_client = blob_service.get_container_client(container)
                blobs = container_client.list_blobs(name_starts_with=blob_name)
                outputs.results = [
                    cls(container_name=container, blob_name=blob.name, account_name=account_name) for blob in blobs
                ]
                return outputs.results
            except Exception as e:
                raise SourceConnectionError() from e

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create AzureBlobStorageSource instances from a URI path.

        The supported URI formats:
        - https://<account-name>.blob.core.windows.net/<container-name>/<blob-name>

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from the Azure Blob Storage container.

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

    @staticmethod
    def _get_blob_service(account_name: str) -> "BlobServiceClient":
        """
        Returns an authenticated BlobServiceClient instance.

        Priority:
            1. DefaultAzureCredential.
            2. Connection string.

        Args:
            account_name: The name of the Azure Blob Storage account.

        Returns:
            The authenticated Blob Storage client.
        """
        try:
            credential = DefaultAzureCredential()
            account_url = f"https://{account_name}.blob.core.windows.net"
            blob_service = BlobServiceClient(
                account_url=account_url,
                credential=credential,
                retry_policy=ExponentialRetry(retry_total=0),
            )
            blob_service.get_account_information()
            return blob_service
        except Exception as first_exc:
            if conn_str := os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""):
                try:
                    service = BlobServiceClient.from_connection_string(
                        conn_str=conn_str,
                        retry_policy=ExponentialRetry(retry_total=0),
                    )
                    service.get_account_information()
                    return service
                except Exception as second_error:
                    raise second_error from first_exc

            raise first_exc
