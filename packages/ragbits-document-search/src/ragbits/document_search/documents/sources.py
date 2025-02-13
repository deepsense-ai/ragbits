import os
import re
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, GetCoreSchemaHandler, computed_field
from pydantic.alias_generators import to_snake
from pydantic_core import CoreSchema, core_schema

with suppress(ImportError):
    from gcloud.aio.storage import Storage as StorageClient

with suppress(ImportError):
    from datasets import load_dataset
    from datasets.exceptions import DatasetNotFoundError


from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError
from ragbits.document_search.documents.source_resolver import SourceResolver

LOCAL_STORAGE_DIR_ENV = "LOCAL_STORAGE_DIR"


class Source(BaseModel, ABC):
    """
    An object representing a source.
    """

    # Registry of all subclasses by their unique identifier
    _registry: ClassVar[dict[str, type["Source"]]] = {}
    protocol: ClassVar[str | None] = None

    @classmethod
    def class_identifier(cls) -> str:
        """
        Get an identifier for the source type.
        """
        return to_snake(cls.__name__)

    @computed_field
    def source_type(self) -> str:
        """
        Pydantic field based on the class identifier.
        """
        return self.class_identifier()

    @property
    @abstractmethod
    def id(self) -> str:
        """
        Get the source ID.

        Returns:
            The source ID.
        """

    @abstractmethod
    async def fetch(self) -> Path:
        """
        Load the source.

        Returns:
            The path to the source.
        """

    @classmethod
    @abstractmethod
    async def from_uri(cls, path: str) -> Sequence["Source"]:
        """Create Source instances from a URI path.

        The path can contain glob patterns (asterisks) to match multiple sources, but pattern support
        varies by source type. Each source implementation defines which patterns it supports:

        - LocalFileSource: Supports full glob patterns ('*', '**', etc.) via Path.glob
        - GCSSource: Supports simple prefix matching with '*' at the end of path
        - HuggingFaceSource: Does not support glob patterns

        Args:
            path: The path part of the URI (after protocol://). Pattern support depends on source type.

        Returns:
            A sequence of Source objects matching the path pattern

        Raises:
            ValueError: If the path contains unsupported pattern for this source type
        """

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init_subclass__(**kwargs)
        Source._registry[cls.class_identifier()] = cls
        if cls.protocol is not None:
            SourceResolver.register_protocol(cls.protocol, cls)


class SourceDiscriminator:
    """
    Pydantic type annotation that automatically creates the correct subclass of Source based on the source_type field.
    """

    @staticmethod
    def _create_instance(
        fields: dict[str, Any],
        validator: core_schema.ValidatorFunctionWrapHandler,
    ) -> Source:
        source_type = fields.get("source_type")
        if source_type is None:
            raise ValueError("source_type is required to create a Source instance")

        source_subclass = Source._registry.get(source_type)
        if source_subclass is None:
            raise ValueError(f"Unknown source type: {source_type}")
        return source_subclass.model_validate(fields)

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:  # noqa: ANN401
        create_instance_validator = core_schema.no_info_wrap_validator_function(
            self._create_instance,
            schema=core_schema.any_schema(),
        )

        return core_schema.json_or_python_schema(
            json_schema=create_instance_validator,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(Source),
                    create_instance_validator,
                ]
            ),
        )


class LocalFileSource(Source):
    """
    An object representing a local file source.
    """

    path: Path
    protocol: ClassVar[str] = "file"

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"local_file:{self.path.absolute()}"

    async def fetch(self) -> Path:
        """
        Fetch the source.

        Returns:
            The local path to the object fetched from the source.

        Raises:
            SourceNotFoundError: If the source document is not found.
        """
        if not self.path.is_file():
            raise SourceNotFoundError(source_id=self.id)
        return self.path

    @classmethod
    def list_sources(cls, path: Path, file_pattern: str = "*") -> list["LocalFileSource"]:
        """
        List all sources in the given directory, matching the file pattern.

        Args:
            path: The path to the directory.
            file_pattern: The file pattern to match.

        Returns:
            List of source objects.
        """
        return [cls(path=file_path) for file_path in path.glob(file_pattern)]

    @classmethod
    async def from_uri(cls, path: str) -> Sequence["LocalFileSource"]:
        """Create LocalFileSource instances from a URI path.

        Supports full glob patterns via Path.glob:
        - "**/*.txt" - all .txt files in any subdirectory
        - "*.py" - all Python files in the current directory
        - "**/*" - all files in any subdirectory
        - '?' matches exactly one character

        Args:
            path: The path part of the URI (after file://). Pattern support depends on source type.

        Returns:
            A sequence of LocalFileSource objects
        """
        path_obj: Path = Path(path)
        base_path, pattern = cls._split_path_and_pattern(path=path_obj)
        if base_path.is_file():
            return [cls(path=base_path)]
        if not pattern:
            return []
        return [cls(path=f) for f in base_path.glob(pattern) if f.is_file()]

    @staticmethod
    def _split_path_and_pattern(path: Path) -> tuple[Path, str]:
        parts = path.parts
        # Find the first part containing '*' or '?'
        for i, part in enumerate(parts):
            if "*" in part or "?" in part:
                base_path = Path(*parts[:i])
                pattern = str(Path(*parts[i:]))
                return base_path, pattern
        return path, ""


class GCSSource(Source):
    """An object representing a GCS file source."""

    bucket: str
    object_name: str
    protocol: ClassVar[str] = "gcs"
    _storage: "StorageClient | None" = None  # Storage client for dependency injection

    @classmethod
    def set_storage(cls, storage: "StorageClient | None") -> None:
        """Set the storage client for all instances.

        Args:
            storage: The `gcloud-aio-storage` `Storage` object to use as the storage client.
                By default, the object will be created automatically.
        """
        cls._storage = storage

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def _get_storage(cls) -> "StorageClient":
        """Get the storage client.

        Returns:
            The storage client to use. If none was injected, creates a new one.
        """
        if cls._storage is None:
            cls._storage = StorageClient()
        return cls._storage

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"gcs:gs://{self.bucket}/{self.object_name}"

    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def fetch(self) -> Path:
        """
        Fetch the file from Google Cloud Storage and store it locally.

        The file is downloaded to a local directory specified by `local_dir`. If the file already exists locally,
        it will not be downloaded again. If the file doesn't exist locally, it will be fetched from GCS.
        The local directory is determined by the environment variable `LOCAL_STORAGE_DIR`. If this environment
        variable is not set, a temporary directory is used.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the 'gcp' extra is not installed.
        """
        local_dir = get_local_storage_dir()
        bucket_local_dir = local_dir / self.bucket
        bucket_local_dir.mkdir(parents=True, exist_ok=True)
        path = bucket_local_dir / self.object_name

        if not path.is_file():
            storage = await self._get_storage()
            async with storage as client:
                content = await client.download(self.bucket, self.object_name)
                Path(bucket_local_dir / self.object_name).parent.mkdir(parents=True, exist_ok=True)
                with open(path, mode="wb+") as file_object:
                    file_object.write(content)

        return path

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def list_sources(cls, bucket: str, prefix: str = "") -> list["GCSSource"]:
        """List all sources in the given GCS bucket, matching the prefix.

        Args:
            bucket: The GCS bucket.
            prefix: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'gcloud-aio-storage' package is not installed
        """
        async with await cls._get_storage() as storage:
            result = await storage.list_objects(bucket, params={"prefix": prefix})
            items = result.get("items", [])
            return [cls(bucket=bucket, object_name=item["name"]) for item in items]

    @classmethod
    async def from_uri(cls, path: str) -> Sequence["GCSSource"]:
        """Create GCSSource instances from a URI path.

        Supports simple prefix matching with '*' at the end of path.
        For example:
        - "bucket/folder/*" - matches all files in the folder
        - "bucket/folder/prefix*" - matches all files starting with prefix

        More complex patterns like '**' or '?' are not supported.

        Args:
            path: The path part of the URI (after gcs://). Can end with '*' for pattern matching.

        Returns:
            A sequence of GCSSource objects matching the pattern

        Raises:
            ValueError: If an unsupported pattern is used
        """
        if "**" in path or "?" in path:
            raise ValueError(
                "GCSSource only supports '*' at the end of path. Patterns like '**' or '?' are not supported."
            )

        # Split into bucket and prefix
        bucket, prefix = path.split("/", 1) if "/" in path else (path, "")

        if "*" in prefix:
            if not prefix.endswith("*"):
                raise ValueError(f"GCSSource only supports '*' at the end of path. Invalid pattern: {prefix}")
            # Remove the trailing * for GCS prefix listing
            prefix = prefix[:-1]
            return await cls.list_sources(bucket=bucket, prefix=prefix)

        return [cls(bucket=bucket, object_name=prefix)]


class HuggingFaceSource(Source):
    """
    An object representing a Hugging Face dataset source.
    """

    path: str
    split: str = "train"
    row: int
    protocol: ClassVar[str] = "huggingface"

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"huggingface:{self.path}/{self.split}/{self.row}"

    @requires_dependencies(["datasets"], "huggingface")
    async def fetch(self) -> Path:
        """
        Fetch the file from Hugging Face and store it locally.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ImportError: If the 'huggingface' extra is not installed.
            SourceConnectionError: If the source connection fails.
            SourceNotFoundError: If the source document is not found.
        """
        try:
            dataset = load_dataset(self.path, split=self.split, streaming=True)  # type: ignore
        except ConnectionError as exc:
            raise SourceConnectionError() from exc
        except DatasetNotFoundError as exc:  # type: ignore
            raise SourceNotFoundError(source_id=self.id) from exc

        try:
            data = next(iter(dataset.skip(self.row).take(1)))  # type: ignore
        except StopIteration as exc:
            raise SourceNotFoundError(source_id=self.id) from exc

        storage_dir = get_local_storage_dir()
        source_dir = storage_dir / Path(data["source"]).parent
        source_dir.mkdir(parents=True, exist_ok=True)
        path = storage_dir / data["source"]

        if not path.is_file():
            with open(path, mode="w", encoding="utf-8") as file:
                file.write(data["content"])

        return path

    @classmethod
    async def from_uri(cls, path: str) -> Sequence["HuggingFaceSource"]:
        """Create HuggingFaceSource instances from a URI path.

        Pattern matching is not supported. The path must be in the format:
        huggingface://dataset_path/split/row

        Args:
            path: The path part of the URI (after huggingface://)

        Returns:
            A sequence containing a single HuggingFaceSource

        Raises:
            ValueError: If the path contains patterns or has invalid format
        """
        if "*" in path or "?" in path:
            raise ValueError(
                "HuggingFaceSource does not support patterns. Path must be in format: dataset_path/split/row"
            )

        try:
            dataset_path, split, row = path.split("/")
            return [cls(path=dataset_path, split=split, row=int(row))]
        except ValueError as err:
            raise ValueError("Invalid HuggingFace path format. Expected: dataset_path/split/row") from err

    @classmethod
    async def list_sources(cls, path: str, split: str) -> list["HuggingFaceSource"]:
        """
        List all sources in the given Hugging Face repository.

        Args:
            path: Path or name of the dataset.
            split: Dataset split.

        Returns:
            List of source objects.
        """
        sources = load_dataset(path, split=split)  # type: ignore
        cleaned_split = re.sub(r"\[.*?\]", "", split)
        return [
            cls(
                path=path,
                split=cleaned_split,
                row=row,
            )
            for row in range(len(sources))  # type: ignore
        ]


def get_local_storage_dir() -> Path:
    """
    Get the local storage directory.

    The local storage directory is determined by the environment variable `LOCAL_STORAGE_DIR`. If this environment
    variable is not set, a temporary directory is used.

    Returns:
        The local storage directory.
    """
    return (
        Path(local_dir_env)
        if (local_dir_env := os.getenv(LOCAL_STORAGE_DIR_ENV)) is not None
        else Path(tempfile.gettempdir()) / "ragbits"
    )
