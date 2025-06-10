from collections.abc import Mapping
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.utils.config_handling import ObjectConstructionConfig, WithConstructionConfig
from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.parsers.base import DocumentParser
from ragbits.document_search.ingestion.parsers.docling import DoclingDocumentParser
from ragbits.document_search.ingestion.parsers.exceptions import ParserNotFoundError

_default_parser = DoclingDocumentParser()

_DEFAULT_PARSERS: dict[DocumentType, DocumentParser] = {
    DocumentType.TXT: _default_parser,
    DocumentType.MD: _default_parser,
    DocumentType.PDF: _default_parser,
    DocumentType.DOCX: _default_parser,
    DocumentType.PPTX: _default_parser,
    DocumentType.XLSX: _default_parser,
    DocumentType.HTML: _default_parser,
    DocumentType.JPG: _default_parser,
    DocumentType.PNG: _default_parser,
}


class DocumentParserRouter(WithConstructionConfig):
    """
    The class responsible for routing the document to the correct parser based on the document type.
    """

    configuration_key: ClassVar[str] = "parser_router"

    _parsers: Mapping[DocumentType, DocumentParser]

    def __init__(self, parsers: Mapping[DocumentType, DocumentParser] | None = None) -> None:
        """
        Initialize the DocumentParserRouter instance.

        Args:
            parsers: The mapping of document types and their parsers. To override default Unstructured parsers.
        """
        self._parsers = {**_DEFAULT_PARSERS, **parsers} if parsers else _DEFAULT_PARSERS

    @classmethod
    def from_config(cls, config: dict[str, ObjectConstructionConfig]) -> Self:
        """
        Initialize the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            The DocumentParserRouter.

        Raises:
            InvalidConfigError: If any of the provided parsers cannot be initialized.
        """
        parsers = {
            DocumentType(document_type): DocumentParser.subclass_from_config(parser_config)
            for document_type, parser_config in config.items()
        }
        return super().from_config({"parsers": parsers})

    def get(self, document_type: DocumentType) -> DocumentParser:
        """
        Get the parser for the document.

        Args:
            document_type: The document type.

        Returns:
            The parser for processing the document.

        Raises:
            ParserNotFoundError: If no parser is found for the document type.
        """
        parser = self._parsers.get(document_type)

        if isinstance(parser, DocumentParser):
            return parser

        raise ParserNotFoundError(document_type)
