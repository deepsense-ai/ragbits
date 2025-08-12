from __future__ import annotations

import logging
from pathlib import Path

from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, TextItem
from pptx.presentation import Presentation

from ragbits.document_search.ingestion.parsers.pptx.callbacks import PptxCallback
from ragbits.document_search.ingestion.parsers.pptx.exceptions import PptxExtractionError

logger = logging.getLogger(__name__)


class NotesCallback(PptxCallback):
    """
    Callback to extract speaker notes from PPTX slides.
    """

    name = "notes_callback"

    def __call__(
        self, pptx_path: Path, presentation: Presentation, docling_document: DoclingDocument
    ) -> DoclingDocument:
        """
        Extract speaker notes from all slides and add them to the docling document.

        Args:
            pptx_path: Path to the PPTX file.
            presentation: Loaded PPTX presentation.
            docling_document: Document to enhance with speaker notes.

        Returns:
            Enhanced docling document with speaker notes.
        """
        notes_added = 0

        for slide_idx, slide in enumerate(presentation.slides, start=1):
            try:
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
                    notes_text_frame = slide.notes_slide.notes_text_frame
                    text = getattr(notes_text_frame, "text", None)
                    text = text.strip() if text else None

                    if text:
                        notes_item = TextItem(
                            self_ref=f"#/notes/{slide_idx}",
                            text=text,
                            orig=text,
                            label=DocItemLabel.TEXT,
                            prov=[
                                ProvenanceItem(
                                    page_no=slide_idx,
                                    bbox=BoundingBox(l=0.0, t=0.0, r=1.0, b=1.0),
                                    charspan=(0, len(text)),
                                )
                            ],
                        )

                        docling_document.texts.append(notes_item)
                        notes_added += 1

                        logger.debug("Added speaker notes from slide %d", slide_idx)

            except (AttributeError, TypeError) as e:
                extraction_error = PptxExtractionError(self.name, slide_idx, "speaker notes", e)
                logger.debug("Failed to extract speaker notes from slide %d: %s", slide_idx, str(extraction_error))
                continue

        if notes_added > 0:
            logger.info("Successfully added %d speaker notes to docling document", notes_added)
        else:
            logger.debug("No speaker notes found in presentation")

        return docling_document
