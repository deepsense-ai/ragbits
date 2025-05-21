from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from typing import ClassVar, Optional
from urllib.parse import urlparse

from typing_extensions import Self

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    import boto3
    from botocore.client import BaseClient
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


class S3Source(Source):
    """
    Source for data stored in the AWS S3 bucket.
    """

    protocol: ClassVar[str] = "s3"
    bucket_name: str
    key: str

    _s3_client: ClassVar[Optional["BaseClient"]] = None

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"s3:{self.bucket_name}/{self.key}"

    @classmethod
    @requires_dependencies(["boto3"], "s3")
    def _set_client(cls, bucket_name: str) -> None:
        """
        Set the boto3 S3 client if it hasn't been initialized yet.

        Args:
            bucket_name: The name of the S3 bucket to use.

        Raises:
            ValueError: If credentials are incomplete.
            RuntimeError: If another error occurs.
        """
        if cls._s3_client is None:
            try:
                cls._s3_client = boto3.client("s3")
                cls._s3_client.head_bucket(Bucket=bucket_name)  # This triggers a credentials check
            except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
                raise ValueError("AWS credentials are missing or incomplete. Please configure them.") from e
            except Exception as e:
                raise RuntimeError(f"Failed to initialize AWS S3 client: {e}") from e

    @requires_dependencies(["boto3"], "s3")
    async def fetch(self) -> Path:
        """
        Download a file in the given bucket name and key.

        Returns:
            The local path to the downloaded file.

        Raises:
            ClientError: If the file doesn't exist or credentials are incomplete.
            NoCredentialsError: If no credentials are available.
        """
        if self._s3_client is None:
            self._set_client(self.bucket_name)

        if self._s3_client is None:
            raise RuntimeError("S3 client is not initialized.")

        local_dir = get_local_storage_dir()
        container_local_dir = local_dir / self.bucket_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        normalized_key = self.key.replace("/", "_")
        path = container_local_dir / normalized_key
        with trace(bucket=self.bucket_name, key=self.key) as outputs:
            try:
                self._s3_client.download_file(self.bucket_name, self.key, path)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    raise FileNotFoundError(f"The object does not exist: {self.key}") from e
                elif e.response["Error"]["Code"] == "403":
                    raise PermissionError(f"Access denied. No permission to download: {self.key}") from e
                else:
                    raise RuntimeError(f"S3 Client Error: {e}") from e
            except (NoCredentialsError, PartialCredentialsError) as e:
                raise ValueError("AWS credentials are missing or invalid.") from e
            outputs.path = path
        return path

    @classmethod
    @requires_dependencies(["boto3"], "s3")
    async def list_sources(cls, bucket_name: str, prefix: str) -> Iterable[Self]:
        """
        List all files under the given bucket name and with the given prefix.

        Args:
            bucket_name: The name of the S3 bucket to use.
            prefix: The path to the files and prefix to look for.

        Returns:
            The iterable of sources from the S3 bucket.

        Raises:
            ClientError: If the source doesn't exist.
            NoCredentialsError: If no credentials are available.
            PartialCredentialsError: If credentials are incomplete.
        """
        cls._set_client(bucket_name)
        if cls._s3_client is None:
            raise RuntimeError("S3 client is not initialized.")
        with trace(bucket=bucket_name, key=prefix) as outputs:
            try:
                aws_sources_list = []
                paginator = cls._s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        aws_sources_list.append(cls(bucket_name=bucket_name, key=key))
                outputs.sources = aws_sources_list
                return aws_sources_list
            except (NoCredentialsError, PartialCredentialsError) as e:
                raise ValueError("AWS credentials are missing or incomplete. Please configure them.") from e
            except ClientError as e:
                raise RuntimeError(f"Failed to list files in bucket {bucket_name}: {e}") from e

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create S3Source instances from a URI path.

        The supported URI formats:
        - s3://<bucket-name>/<key>
        - https://<bucket-name>s3.<region>.amazonaws.com/<key>
        - https://s3.<region>.amazonaws.com/<bucket-name>/<key>

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from the S3 bucket.

        Raises:
            ValueError: If the path has invalid format
        """
        if "**" in path or "?" in path:
            raise ValueError(
                "S3Source only supports '*' at the end of path. Patterns like '**' or '?' are not supported."
            )

        parsed = urlparse(path)
        if not parsed.netloc or not parsed.path:
            raise ValueError("Invalid AWS Source URI format.")
        if parsed.scheme not in {"s3", "https"}:
            raise ValueError("Invalid AWS Source URI format.")

        if parsed.scheme == "s3":
            bucket_name = parsed.netloc
            path_to_file = parsed.path.lstrip("/")
        elif parsed.scheme == "https":
            if not parsed.netloc.endswith("amazonaws.com"):
                raise ValueError("Invalid AWS Source URI format.")
            elif parsed.netloc.startswith("s3"):
                parts = parsed.path.split("/")
                bucket_name = parts[1]
                path_to_file = "/".join(parts[2:])
            else:
                bucket_name = parsed.netloc.split(".")[0]
                path_to_file = parsed.path.lstrip("/")

        else:
            raise ValueError("Invalid AWS Source URI format.")

        if "*" in path_to_file:
            if not path_to_file.endswith("*") or "*" in path_to_file[:-1]:
                raise ValueError(f"AWS Source only supports '*' at the end of path. Invalid pattern: {[path_to_file]}.")
            path_to_file = path_to_file[:-1]
            return await cls.list_sources(bucket_name=bucket_name, prefix=path_to_file)

        return [cls(bucket_name=bucket_name, key=path_to_file)]
