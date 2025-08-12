from __future__ import annotations

import logging
from pathlib import Path

from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, TextItem
from pptx.presentation import Presentation
from pptx.shapes.group import GroupShape

from ragbits.document_search.ingestion.parsers.pptx.callbacks import PptxCallback
from ragbits.document_search.ingestion.parsers.pptx.exceptions import PptxExtractionError

logger = logging.getLogger(__name__)


class LinkCallback(PptxCallback):
    """
    Callback to extract hyperlinks from PPTX shapes.
    """

    name = "link_callback"

    def __call__(
        self, pptx_path: Path, presentation: Presentation, docling_document: DoclingDocument
    ) -> DoclingDocument:
        """
        Extract hyperlinks from all shapes and add them to the docling document.

        Args:
            pptx_path: Path to the PPTX file.
            presentation: Loaded PPTX presentation.
            docling_document: Document to enhance with hyperlinks.

        Returns:
            Enhanced docling document with hyperlinks.
        """
        hyperlinks_added = 0

        for slide_idx, slide in enumerate(presentation.slides, start=1):
            for shape in slide.shapes:
                try:
                    hyperlink_address = self._extract_hyperlink_address(shape)
                    if hyperlink_address:
                        link_text = f"Link: {hyperlink_address}"
                        hyperlink_item = TextItem(
                            self_ref=f"#/links/{slide_idx + hyperlinks_added}",
                            text=link_text,
                            orig=link_text,
                            label=DocItemLabel.TEXT,
                            prov=[
                                ProvenanceItem(
                                    page_no=slide_idx,
                                    bbox=BoundingBox(l=0.0, t=0.0, r=1.0, b=1.0),
                                    charspan=(0, len(link_text)),
                                )
                            ],
                        )

                        docling_document.texts.append(hyperlink_item)
                        hyperlinks_added += 1

                        logger.debug("Added hyperlink from slide %d: %s", slide_idx, hyperlink_address)

                except (AttributeError, TypeError) as e:
                    extraction_error = PptxExtractionError(self.name, slide_idx, "hyperlink from shape", e)
                    logger.debug(
                        "Failed to extract hyperlink from shape on slide %d: %s", slide_idx, str(extraction_error)
                    )
                    continue

        if hyperlinks_added > 0:
            logger.info("Successfully added %d hyperlinks to docling document", hyperlinks_added)
        else:
            logger.debug("No hyperlinks found in presentation")

        return docling_document

    @staticmethod
    def _extract_hyperlink_address(shape: object) -> str | None:
        if not hasattr(shape, "click_action") or isinstance(shape, GroupShape):
            return None
        if not shape.click_action.hyperlink or not shape.click_action.hyperlink.address:
            return None
        return shape.click_action.hyperlink.address
