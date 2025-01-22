from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ragbits.document_search.documents.sources import Source


class SourceResolver:
    """Registry for source URI protocols and their handlers.

    This class provides a mechanism to register and resolve different source protocols (like 'file://', 'gcs://', etc.)
    to their corresponding Source implementations.

    Example:
        >>> SourceResolver.register_protocol("gcs", GCSSource)
        >>> sources = await SourceResolver.resolve("gcs://my-bucket/path/to/files/*")
    """

    _protocol_handlers: ClassVar[dict[str, type["Source"]]] = {}

    @classmethod
    def register_protocol(cls, protocol: str, source_class: type["Source"]) -> None:
        """Register a source class for a specific protocol.

        Args:
            protocol: The protocol identifier (e.g., 'file', 'gcs', 's3')
            source_class: The Source subclass that handles this protocol
        """
        cls._protocol_handlers[protocol] = source_class

    @classmethod
    async def resolve(cls, uri: str) -> Sequence["Source"]:
        """Resolve a URI into a sequence of Source objects.

        The URI format should be: protocol://path
        For example:
        - file:///path/to/files/*
        - gcs://bucket/prefix/*

        Args:
            uri: The URI to resolve

        Returns:
            A sequence of Source objects

        Raises:
            ValueError: If the URI format is invalid or the protocol is not supported
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
