from __future__ import annotations

import logging

from pptx import Presentation

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.parsers.base import DocumentParser
from ragbits.document_search.ingestion.parsers.pptx.extractors import (
    DEFAULT_EXTRACTORS,
    BaseExtractor,
)

logger = logging.getLogger(__name__)


class PptxDocumentParser(DocumentParser):
    """
    A comprehensive PPTX parser using python-pptx library with modular extractor architecture.
    """

    supported_document_types = {DocumentType.PPTX}

    def __init__(
        self,
        extractors: list[BaseExtractor] | None = None,
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

        extracted_elements = []
        presentation = Presentation(document.local_path.as_posix())

        for extractor in self.extractors:
            for slide in presentation.slides:
                extracted_elements.extend(extractor.extract(presentation, slide))

        return extracted_elements
