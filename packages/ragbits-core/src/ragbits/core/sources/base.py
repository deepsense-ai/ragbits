import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

from pydantic import BaseModel, GetCoreSchemaHandler, computed_field
from pydantic.alias_generators import to_snake
from pydantic_core import CoreSchema, core_schema
from typing_extensions import Self

from ragbits.core import sources
from ragbits.core.utils.config_handling import WithConstructionConfig

LOCAL_STORAGE_DIR_ENV = "LOCAL_STORAGE_DIR"


class Source(WithConstructionConfig, BaseModel, ABC):
    """
    Base class for data sources.
    """

    default_module: ClassVar[ModuleType | None] = sources
    configuration_key: ClassVar[str] = "source"

    # Registry of all subclasses by their unique identifier
    _registry: ClassVar[dict[str, type["Source"]]] = {}
    protocol: ClassVar[str]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """
        This method is automatically called when a subclass is defined. It performs the following tasks:
        - Validates that the subclass has a 'protocol' attribute defined
        - Registers the subclass in Source._registry using its class identifier
        - Registers the subclass protocol with the SourceResolver

        Raises:
            TypeError: If the subclass does not define a 'protocol' attribute.
        """
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "protocol"):
            raise TypeError(f"Class {cls.__name__} is missing the 'protocol' attribute")

        Source._registry[cls.class_identifier()] = cls
        SourceResolver.register_protocol(cls.protocol, cls)

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
        Get the source identifier.
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
    async def list_sources(cls, *args: Any, **kwargs: Any) -> Iterable[Self]:  # noqa: ANN401
        """
        List all sources from the given storage.

        Returns:
            The iterable of Source objects.
        """

    @classmethod
    @abstractmethod
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create Source instances from a URI path.

        The path can contain glob patterns (asterisks) to match multiple sources, but pattern support
        varies by source type. Each source implementation defines which patterns it supports.

        Args:
            path: The path part of the URI (after protocol://). Pattern support depends on source type.

        Returns:
            The iterable of Source objects matching the path pattern.
        """


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


class SourceResolver:
    """
    Registry for source URI protocols and their handlers.

    This class provides a mechanism to register and resolve different source protocols (like 'file://', 'gcs://', etc.)
    to their corresponding Source implementations.

    Example:
        >>> SourceResolver.register_protocol("gcs", GCSSource)
        >>> sources = await SourceResolver.resolve("gcs://my-bucket/path/to/files/*")
    """

    _protocol_handlers: ClassVar[dict[str, type[Source]]] = {}

    @classmethod
    def register_protocol(cls, protocol: str, source_class: type[Source]) -> None:
        """
        Register a source class for a specific protocol.

        Args:
            protocol: The protocol identifier (e.g., 'file', 'gcs', 's3')
            source_class: The Source subclass that handles this protocol
        """
        cls._protocol_handlers[protocol] = source_class

    @classmethod
    async def resolve(cls, uri: str) -> Iterable[Source]:
        """
        Resolve a URI into a iterable of Source objects.

        Args:
            uri: The URI to resolve. The URI should be in the format of `protocol://path`.

        Returns:
            The iterable of Source objects.

        Raises:
            ValueError: If the URI format is invalid or the protocol is not supported.
        """
        try:
            protocol, path = uri.split("://", 1)
        except ValueError as err:
            raise ValueError(f"Invalid URI format: {uri}. Expected format: protocol://path") from err

        if protocol not in cls._protocol_handlers:
            supported = ", ".join(sorted(cls._protocol_handlers.keys()))
            raise ValueError(f"Unsupported protocol: {protocol}. Supported protocols are: {supported}")

        handler_class = cls._protocol_handlers[protocol]
        return await handler_class.from_uri(path)


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
