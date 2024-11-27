import os
import tempfile
from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, GetCoreSchemaHandler, computed_field
from pydantic.alias_generators import to_snake
from pydantic_core import CoreSchema, core_schema

with suppress(ImportError):
    from gcloud.aio.storage import Storage

with suppress(ImportError):
    from datasets import load_dataset
    from datasets.exceptions import DatasetNotFoundError

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceConnectionError, SourceNotFoundError

LOCAL_STORAGE_DIR_ENV = "LOCAL_STORAGE_DIR"


class Source(BaseModel, ABC):
    """
    An object representing a source.
    """

    # Registry of all subclasses by their unique identifier
    _registry: ClassVar[dict[str, type["Source"]]] = {}

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
    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        Source._registry[cls.class_identifier()] = cls
        super().__init_subclass__(**kwargs)


class SourceDiscriminator:
    """
    Pydantic type annotation that automatically creates the correct subclass of Source based on the source_type field.
    """

    @staticmethod
    def _create_instance(fields: dict[str, Any]) -> Source:
        source_type = fields.get("source_type")
        if source_type is None:
            raise ValueError("source_type is required to create a Source instance")

        source_subclass = Source._registry.get(source_type)
        if source_subclass is None:
            raise ValueError(f"Unknown source type: {source_type}")
        return source_subclass(**fields)

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:  # noqa: ANN401
        create_instance_validator = core_schema.no_info_plain_validator_function(self._create_instance)

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


class GCSSource(Source):
    """
    An object representing a GCS file source.
    """

    bucket: str
    object_name: str

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
            async with Storage() as client:  # type: ignore
                # TODO: Add error handling for download
                content = await client.download(self.bucket, self.object_name)
                Path(bucket_local_dir / self.object_name).parent.mkdir(parents=True, exist_ok=True)
                with open(path, mode="wb+") as file_object:
                    file_object.write(content)

        return path

    @classmethod
    @requires_dependencies(["gcloud.aio.storage"], "gcs")
    async def list_sources(cls, bucket: str, prefix: str = "") -> list["GCSSource"]:
        """
        List all sources in the given GCS bucket, matching the prefix.

        Args:
            bucket: The GCS bucket.
            prefix: The prefix to match.

        Returns:
            List of source objects.

        Raises:
            ImportError: If the required 'gcloud-aio-storage' package is not installed
        """
        async with Storage() as client:
            objects = await client.list_objects(bucket, params={"prefix": prefix})
            sources = []
            for obj in objects["items"]:
                sources.append(cls(bucket=bucket, object_name=obj["name"]))
            return sources


class HuggingFaceSource(Source):
    """
    An object representing a Hugging Face dataset source.
    """

    path: str
    split: str = "train"
    row: int

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
