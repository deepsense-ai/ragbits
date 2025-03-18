from collections.abc import Mapping
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.utils.config_handling import ObjectContructionConfig, WithConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.parsers.base import BaseProvider
from ragbits.document_search.ingestion.parsers.unstructured.default import UnstructuredDefaultProvider
from ragbits.document_search.ingestion.parsers.unstructured.images import UnstructuredImageProvider
from ragbits.document_search.ingestion.parsers.unstructured.pdf import UnstructuredPdfProvider

_default_parser = UnstructuredDefaultProvider()
_default_img_parser = UnstructuredImageProvider()
_default_pdf_parser = UnstructuredPdfProvider()

_DEFAULT_PARSERS: dict[DocumentType, BaseProvider] = {
    DocumentType.TXT: _default_parser,
    DocumentType.MD: _default_parser,
    DocumentType.PDF: _default_pdf_parser,
    DocumentType.DOCX: _default_parser,
    DocumentType.DOC: _default_parser,
    DocumentType.PPTX: _default_parser,
    DocumentType.PPT: _default_parser,
    DocumentType.XLSX: _default_parser,
    DocumentType.XLS: _default_parser,
    DocumentType.CSV: _default_parser,
    DocumentType.HTML: _default_parser,
    DocumentType.EPUB: _default_parser,
    DocumentType.ORG: _default_parser,
    DocumentType.ODT: _default_parser,
    DocumentType.RST: _default_parser,
    DocumentType.RTF: _default_parser,
    DocumentType.TSV: _default_parser,
    DocumentType.XML: _default_parser,
    DocumentType.JPG: _default_img_parser,
    DocumentType.PNG: _default_img_parser,
}


class DocumentParserRouter(WithConstructionConfig):
    """
    The class responsible for routing the document to the correct parser based on the document type.
    """

    configuration_key: ClassVar[str] = "parsers"

    _parsers: Mapping[DocumentType, BaseProvider]

    def __init__(self, parsers: Mapping[DocumentType, BaseProvider] | None = None) -> None:
        """
        Initialize the DocumentParserRouter instance.

        Args:
            parsers: The mapping of document types and their parsers. To override default Unstructured parsers.

        Example:
                {
                    DocumentType.PDF: CustomPDFParser(),
                    DocumentType.TXT: CustomTextParser(),
                }
        """
        self._parsers = {**_DEFAULT_PARSERS, **parsers} if parsers else _DEFAULT_PARSERS

    @classmethod
    def from_config(cls, config: dict[str, ObjectContructionConfig]) -> Self:
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
            DocumentType(document_type): BaseProvider.subclass_from_config(parser_config)
            for document_type, parser_config in config.items()
        }
        return cls(parsers=parsers)

    def get(self, document_meta: DocumentMeta) -> BaseProvider:
        """
        Get the parser for the document.

        Args:
            document_meta: The document metadata.

        Returns:
            The parser for processing the document.

        Raises:
            ValueError: If no parser is found for the document type.
        """
        parser = self._parsers.get(document_meta.document_type)

        if isinstance(parser, BaseProvider):
            return parser

        raise ValueError(f"No parser found for the document type {document_meta.document_type}")
