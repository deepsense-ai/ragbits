from abc import ABC, abstractmethod
from types import ModuleType
from typing import ClassVar

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, ImageElement, TextElement
from ragbits.document_search.ingestion import parsers
from ragbits.document_search.ingestion.parsers.exceptions import ParserDocumentNotSupportedError


class DocumentParser(WithConstructionConfig, ABC):
    """
    Base class for document parsers, responsible for converting the document into a list of elements.
    """

    default_module: ClassVar[ModuleType | None] = parsers
    configuration_key: ClassVar[str] = "parser"

    supported_document_types: set[DocumentType] = set()

    @abstractmethod
    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the document.

        Args:
            document: The document to parse.

        Returns:
            The list of elements extracted from the document.

        Raises:
            ParserError: If the parsing of the document failed.
        """

    @classmethod
    def validate_document_type(cls, document_type: DocumentType) -> None:
        """
        Check if the parser supports the document type.

        Args:
            document_type: The document type to validate against the parser.

        Raises:
            ParserDocumentNotSupportedError: If the document type is not supported.
        """
        if document_type not in cls.supported_document_types:
            raise ParserDocumentNotSupportedError(parser_name=cls.__name__, document_type=document_type)


class TextDocumentParser(DocumentParser):
    """
    Simple parser that maps a text to the text element.
    """

    supported_document_types = {DocumentType.TXT, DocumentType.MD}

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the document.

        Args:
            document: The document to parse.

        Returns:
            List with an text element with the text content.

        Raises:
            ParserDocumentNotSupportedError: If the document type is not supported by the parser.
        """
        self.validate_document_type(document.metadata.document_type)
        return [TextElement(content=document.local_path.read_text(), document_meta=document.metadata)]


class ImageDocumentParser(DocumentParser):
    """
    Simple parser that maps an image to the image element.
    """

    supported_document_types = {DocumentType.JPG, DocumentType.PNG}

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the document.

        Args:
            document: The document to parse.

        Returns:
            List with an image element with the image content.

        Raises:
            ParserDocumentNotSupportedError: If the document type is not supported by the parser.
        """
        self.validate_document_type(document.metadata.document_type)
        return [ImageElement(image_bytes=document.local_path.read_bytes(), document_meta=document.metadata)]
