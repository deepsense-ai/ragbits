from __future__ import annotations

import logging

from docling.datamodel.base_models import InputFormat
from docling.document_converter import FormatOption
from docling_core.transforms.chunker.base import BaseChunker
from docling_core.types.doc import DoclingDocument
from pptx import Presentation

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.ingestion.parsers.docling import DoclingDocumentParser
from ragbits.document_search.ingestion.parsers.pptx.callbacks import PptxCallback
from ragbits.document_search.ingestion.parsers.pptx.exceptions import PptxExtractionError, PptxPresentationError

logger = logging.getLogger(__name__)


class PptxDocumentParser(DoclingDocumentParser):
    """
    Document parser for PPTX files with callback-based enhancement.
    """

    supported_document_types = {DocumentType.PPTX}

    def __init__(
        self,
        ignore_images: bool = False,
        num_threads: int = 1,
        chunker: BaseChunker | None = None,
        format_options: dict[InputFormat, FormatOption] | None = None,
        pptx_callbacks: list[PptxCallback] | None = None,
    ) -> None:
        super().__init__(
            ignore_images=ignore_images,
            num_threads=num_threads,
            chunker=chunker,
            format_options=format_options,
        )

        if pptx_callbacks is None:
            from ragbits.document_search.ingestion.parsers.pptx import DEFAULT_CALLBACKS

            self.pptx_callbacks = DEFAULT_CALLBACKS
        else:
            self.pptx_callbacks = pptx_callbacks

        logger.debug("Initialized PptxDocumentParser with %d callbacks", len(self.pptx_callbacks))

    async def _partition(self, document: Document) -> DoclingDocument:
        docling_document = await super()._partition(document)

        if not self.pptx_callbacks:
            return docling_document

        logger.info("Enhancing docling document with %d callbacks", len(self.pptx_callbacks))

        try:
            presentation = Presentation(document.local_path.as_posix())
        except Exception as e:
            logger.error("Failed to load presentation for callbacks: %s", str(e))
            raise PptxPresentationError(str(document.local_path), e) from e

        successful_callbacks = 0
        for callback in self.pptx_callbacks:
            try:
                logger.debug("Running callback: %s", callback.name)
                docling_document = callback(document.local_path, presentation, docling_document)
                successful_callbacks += 1
                logger.debug("Successfully applied callback: %s", callback.name)
            except Exception as e:
                extraction_error = PptxExtractionError(callback.name, -1, "callback execution", e)
                logger.error(
                    "Callback %s failed: %s. Continuing with other callbacks.",
                    callback.name,
                    str(extraction_error),
                    exc_info=True,
                )

        logger.info(
            "Enhanced docling document with %d/%d successful callbacks",
            successful_callbacks,
            len(self.pptx_callbacks),
        )
        return docling_document
