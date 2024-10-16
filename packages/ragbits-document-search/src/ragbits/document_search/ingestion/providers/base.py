from abc import ABC, abstractmethod

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element


class DocumentTypeNotSupportedError(Exception):
    """
    Raised when the document type is not supported by the provider.
    """

    def __init__(self, provider_name: str, document_type: DocumentType) -> None:
        message = f"Document type {document_type} is not supported by the {provider_name}"
        super().__init__(message)


class BaseProvider(ABC):
    """
    A base class for the document processing providers.
    """

    SUPPORTED_DOCUMENT_TYPES: set[DocumentType]

    @abstractmethod
    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Process the document.

        Args:
            document_meta: The document to process.

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
