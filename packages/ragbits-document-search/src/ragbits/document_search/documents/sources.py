import os
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
    pass

with suppress(ImportError):
    pass


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
