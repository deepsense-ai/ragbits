from __future__ import annotations

import logging

from pptx import Presentation

from ragbits.document_search.documents.document import Document, DocumentType, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.parsers.base import DocumentParser
from ragbits.document_search.ingestion.parsers.pptx.extractors import (
    DEFAULT_EXTRACTORS,
    BasePptxExtractor,
)

logger = logging.getLogger(__name__)


class PptxDocumentParser(DocumentParser):
    """
    A comprehensive PPTX parser using python-pptx library with modular extractor architecture.
    """

    supported_document_types = {DocumentType.PPTX}

    def __init__(
        self,
        extractors: list[BasePptxExtractor] | None = None,
    ) -> None:
        """
        Initialize the PPTX parser with configurable extractors.

        Args:
            extractors: List of extractors to use. If None, uses DEFAULT_EXTRACTORS.
        """
        self.extractors = extractors or DEFAULT_EXTRACTORS

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the PPTX document and return extracted elements.

        Args:
            document: The document to parse.

        Returns:
            List of extracted elements.
        """
        self.validate_document_type(document.metadata.document_type)

        document_path = document.local_path
        document_meta = DocumentMeta.from_local_path(document_path)
        extracted_elements: list[Element] = []
        presentation = Presentation(document_path.as_posix())

        for extractor in self.extractors:
            extracted_elements.extend(
                extractor.extract(presentation, document_meta)
            )

        return extracted_elements
