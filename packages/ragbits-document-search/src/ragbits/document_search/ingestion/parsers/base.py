from abc import ABC, abstractmethod
from typing import ClassVar

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion import parsers


class DocumentTypeNotSupportedError(Exception):
    """
    Raised when the document type is not supported by the provider.
    """

    def __init__(self, provider_name: str, document_type: DocumentType) -> None:
        message = f"Document type {document_type.value} is not supported by the {provider_name}"
        super().__init__(message)


class DocumentParser(WithConstructionConfig, ABC):
    """
    Base class for document parsers, responsible for converting the document into a list of elements.
    """

    default_module: ClassVar = parsers
    configuration_key: ClassVar = "parser"

    SUPPORTED_DOCUMENT_TYPES: set[DocumentType]

    @abstractmethod
    async def parse(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Parse the document.

        Args:
            document_meta: The document to parse.

        Returns:
            The list of elements extracted from the document.
        """

    def validate_document_type(self, document_type: DocumentType) -> None:
        """
        Check if the provider supports the document type.

        Args:
            document_type: The document type.

        Raises:
            DocumentTypeNotSupportedError: If the document type is not supported.
        """
        if document_type not in self.SUPPORTED_DOCUMENT_TYPES:
            raise DocumentTypeNotSupportedError(provider_name=self.__class__.__name__, document_type=document_type)
