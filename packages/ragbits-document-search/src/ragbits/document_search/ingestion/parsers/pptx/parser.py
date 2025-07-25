from __future__ import annotations

import logging

from pptx import Presentation

from ragbits.document_search.documents.document import Document, DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.parsers.base import DocumentParser
from ragbits.document_search.ingestion.parsers.pptx.exceptions import (
    PptxPresentationError,
)
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
        logger.debug("Initialized PptxDocumentParser with %d extractors", len(self.extractors))

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the PPTX document and return extracted elements.

        Args:
            document: The document to parse.

        Returns:
            List of extracted elements.

        Raises:
            PptxPresentationError: If the PPTX file cannot be loaded or processed.
            PptxExtractorError: If an extractor fails completely.
        """
        self.validate_document_type(document.metadata.document_type)

        document_path = document.local_path
        document_meta = DocumentMeta.from_local_path(document_path)
        extracted_elements: list[Element] = []

        logger.info("Starting PPTX parsing for document: %s", document_path.name)

        try:
            presentation = Presentation(document_path.as_posix())
            logger.debug("Successfully loaded PPTX presentation with %d slides", len(presentation.slides))
        except Exception as e:
            logger.error("Failed to load PPTX presentation from %s: %s", document_path, str(e), exc_info=True)
            raise PptxPresentationError(str(document_path), e) from e

        successful_extractors = 0
        failed_extractors = 0
        total_elements_extracted = 0

        for extractor in self.extractors:
            extractor_name = extractor.get_extractor_name()
            logger.debug("Running extractor: %s", extractor_name)

            try:
                extractor_elements = extractor.extract(presentation, document_meta)
                extracted_elements.extend(extractor_elements)
                successful_extractors += 1
                total_elements_extracted += len(extractor_elements)

                logger.debug(
                    "Extractor %s completed successfully: %d elements extracted",
                    extractor_name,
                    len(extractor_elements),
                )

            except Exception as e:
                failed_extractors += 1
                logger.error(
                    "Extractor %s failed completely: %s",
                    extractor_name,
                    str(e),
                    exc_info=True,
                )

                # For now, we continue with other extractors instead of raising
                # This allows partial extraction if some extractors fail
                logger.warning("Continuing with remaining extractors despite %s failure", extractor_name)

        logger.info(
            "PPTX parsing completed for %s: %d total elements extracted, %d/%d extractors successful",
            document_path.name,
            total_elements_extracted,
            successful_extractors,
            len(self.extractors),
        )

        if failed_extractors > 0:
            logger.warning(
                "Some extractors failed during parsing: %d successful, %d failed",
                successful_extractors,
                failed_extractors,
            )

        if not extracted_elements:
            logger.warning("No elements were extracted from the PPTX document: %s", document_path.name)

        return extracted_elements
