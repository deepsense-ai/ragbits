from typing import ClassVar
from pydantic import BaseModel, PrivateAttr
from azure.core.exceptions import ResourceNotFoundError
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.document_search.documents.sources import Source, get_local_storage_dir
import boto3
from botocore.client import BaseClient
import botocore
from pathlib import Path
from typing import Sequence
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
class AWSSource(Source):
    """
    An object representing an AWS S3 Storage dataset source.
    """

    protocol: ClassVar[str] = "s3"
    bucket_name: str
    key: str
    _s3_client: ClassVar[BaseClient | None] = None

    @property
    def id(self) -> str:
        """
        Get the source ID, which is the full blob URL.
        """
        return f"s3://{self.bucket_name}/{self.key}"


    @classmethod
    def _set_client(cls, bucket_name: str) -> None:
        """
       Set the boto3 S3 client if it hasn't been initialized yet.
        """

        if cls._s3_client is None:
            try:
                cls._s3_client = boto3.client("s3")


                cls._s3_client.head_bucket(Bucket=bucket_name)  # This triggers a credentials check
            except (NoCredentialsError, PartialCredentialsError) as e:
                raise RuntimeError("AWS credentials are missing or incomplete. Please configure them.") from e

            except Exception as e:
                raise RuntimeError(f"Failed to initialize AWS S3 client: {e}") from e







# def _download_file(self, s3_key: str, local_path: str) -> None:
#     """
#     Download a single file from S3.
#
#     :param s3_key: The key (path) of the file in the S3 bucket.
#     :param local_path: The local path where the file will be saved.
#     """
#     if self._s3_client is None:
#         self._set_client()
#
#     if self._s3_client:
#         try:
#             # Ensure the directory exists
#             os.makedirs(os.path.dirname(local_path), exist_ok=True)
#
#             # Download the file
#             self._s3_client.download_file(self.bucket_name, s3_key, local_path)
#             print(f"Downloaded: s3://{self.bucket_name}/{s3_key} -> {local_path}")
#         except Exception as e:
#             print(f"Error downloading file {s3_key}: {e}")
#
#     def _list_files(self, prefix: str) -> List[str]:
#         """
#         List all files in the S3 bucket under the given prefix.
#
#         :param prefix: The prefix (path) in the S3 bucket to list files from.
#         :return: List of file keys (paths) in the specified S3 prefix.
#         """
#         if self._s3_client is None:
#             self._set_client()
#
#         file_keys = []
#         if self._s3_client:
#             try:
#                 # Paginate through all objects in the bucket under the given prefix
#                 paginator = self._s3_client.get_paginator("list_objects_v2")
#                 for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
#                     if "Contents" in page:
#                         for obj in page["Contents"]:
#                             file_keys.append(obj["Key"])
#             except Exception as e:
#                 print(f"Error listing files: {e}")
#
#         return file_keys
#
#     def fetch(self, local_dir: str = "./downloads") -> str:
#         """
#         Download all files in the given bucket_name and key.
#         If the key is a file, download the file.
#         If the key is a directory, download all files recursively.
#
#         :param local_dir: The local directory where files will be downloaded.
#         :return: Path to the downloaded file or directory.
#         """
#         if self._s3_client is None:
#             self._set_client()
#
#         if self._s3_client is None:
#             raise RuntimeError("S3 client is not initialized.")
#
#         # Normalize the key (remove leading/trailing slashes)
#         normalized_key = self.key.strip("/")
#
#         # Check if the key points to a file or directory
#         try:
#             # Try to fetch the object metadata
#             self._s3_client.head_object(Bucket=self.bucket_name, Key=normalized_key)
#             is_file = True
#         except self._s3_client.exceptions.ClientError:
#             # If the object doesn't exist, assume it's a directory
#             is_file = False
#
#         if is_file:
#             # Key points to a file
#             local_path = os.path.join(local_dir, os.path.basename(normalized_key))
#             self._download_file(normalized_key, local_path)
#             return local_path
#         else:
#             # Key points to a directory
#             files = self._list_files(normalized_key)
#             if not files:
#                 print(f"No files found under s3://{self.bucket_name}/{normalized_key}/")
#                 return local_dir
#
#             for file_key in files:
#                 # Construct the local path for each file
#                 relative_path = os.path.relpath(file_key, normalized_key)
#                 local_path = os.path.join(local_dir, relative_path)
#                 self._download_file(file_key, local_path)
#
#             return local_dir
#
    @classmethod
    async def from_uri(cls, path: str) -> Sequence["AWSSource"]:
        pass

    async def fetch(self) -> Path:
        pass

#         """
#         Parses an Azure Blob Storage URI and returns an instance of AzureBlobStorage.
#
#         Args:
#             path (str): The Azure Blob Storage URI.
#
#         Returns:
#             Sequence["AzureBlobStorage"]: The parsed Azure Blob Storage URI.
#
#         Raises:
#             ValueError: If the Azure Blob Storage URI is invalid.
#         """
#         pass
#         # if "**" in path or "?" in path:
#         #     raise ValueError(
#         #         "AzureBlobStorage only supports '*' at the end of path. Patterns like '**' or '?' are not supported."
#         #     )
#         # parsed = urlparse(path)
#         # if not parsed.netloc or not parsed.path:
#         #     raise ValueError("Invalid Azure Blob Storage URI format.")
#         #
#         # if parsed.scheme == "https":
#         #     if not parsed.netloc.endswith("blob.core.windows.net"):
#         #         raise ValueError("Invalid scheme, expected 'https://account_name.blob.core.windows.net'.")
#         # else:
#         #     raise ValueError("Invalid scheme, expected 'https://account_name.blob.core.windows.net'.")
#         #
#         # path_parts = parsed.path.lstrip("/").split("/", 1)
#         # if len(path_parts) != 2:  # noqa PLR2004
#         #     raise ValueError("URI must include both container and blob name.")
#         #
#         # container_name, blob_name = path_parts
#         # if "*" in blob_name:
#         #     if not blob_name.endswith("*"):
#         #         raise ValueError(
#         #             f"AzureBlobStorage only supports '*' at the end of path. Invalid pattern: {blob_name}."
#         #         )
#         #     blob_name = blob_name[:-1]
#         #     return await cls.list_sources(container=container_name, blob_name=blob_name)
#         #
#         # # Return a single-element list (consistent with other sources)
#         # return [cls(container_name=container_name, blob_name=blob_name)]
#
#     @classmethod
#     async def list_sources(cls, container: str, blob_name: str = "") -> list["AWSSource"]:
#         pass
#
#
    def download(self, destination: Path) -> Path:
        """
        Download an S3 object or an entire prefix (folder) to the specified destination.

        Args:
            destination: The local file or directory where the object(s) will be saved.

        Returns:
            The path to the downloaded file or directory.
        """
        if self.s3_client is None:
            raise RuntimeError("S3 client is not initialized. Call _set_client() first.")

        # Check if the key is a folder (prefix)
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.key)
        objects = response.get("Contents", [])

        if not objects:
            raise FileNotFoundError(f"No objects found for key '{self.key}' in bucket '{self.bucket_name}'")

        if len(objects) == 1 and objects[0]["Key"] == self.key:
            # Single file case
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.s3_client.download_file(self.bucket_name, self.key, str(destination))
            return destination

        # Folder case - ensure destination is a directory
        destination.mkdir(parents=True, exist_ok=True)

        for obj in objects:
            obj_key = obj["Key"]
            relative_path = obj_key[len(self.key):].lstrip("/")  # Remove prefix
            local_file_path = destination / relative_path

            local_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure subdirectory exists
            self.s3_client.download_file(self.bucket_name, obj_key, str(local_file_path))

        return destination
