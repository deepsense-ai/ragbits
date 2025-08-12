from __future__ import annotations

import logging
from pathlib import Path

from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, TextItem
from pptx.presentation import Presentation

from ragbits.document_search.ingestion.parsers.pptx.callbacks import PptxCallback
from ragbits.document_search.ingestion.parsers.pptx.exceptions import PptxExtractionError

logger = logging.getLogger(__name__)


class MetaCallback(PptxCallback):
    """
    Callback to extract presentation metadata from PPTX files.
    """

    name = "meta_callback"

    def __call__(
        self, pptx_path: Path, presentation: Presentation, docling_document: DoclingDocument
    ) -> DoclingDocument:
        """
        Extract presentation metadata and add it to the docling document.

        Args:
            pptx_path: Path to the PPTX file.
            presentation: Loaded PPTX presentation.
            docling_document: Document to enhance with metadata.

        Returns:
            Enhanced docling document with metadata.
        """
        metadata_added = 0

        try:
            core_properties = presentation.core_properties
            properties = [
                ("author", core_properties.author),
                ("title", core_properties.title),
                ("subject", core_properties.subject),
                ("keywords", core_properties.keywords),
                ("category", core_properties.category),
                ("created", str(core_properties.created) if core_properties.created else None),
                ("modified", str(core_properties.modified) if core_properties.modified else None),
            ]

            for prop_name, prop_value in properties:
                if prop_value is not None and str(prop_value).strip():
                    meta_text = f"{prop_name}: {prop_value}"
                    metadata_item = TextItem(
                        self_ref=f"#/metadata/{metadata_added}",
                        text=meta_text,
                        orig=meta_text,
                        label=DocItemLabel.TEXT,
                        prov=[
                            ProvenanceItem(
                                page_no=0, bbox=BoundingBox(l=0.0, t=0.0, r=1.0, b=1.0), charspan=(0, len(meta_text))
                            )
                        ],
                    )

                    docling_document.texts.append(metadata_item)
                    metadata_added += 1

                    logger.debug("Added metadata: %s = %s", prop_name, prop_value)
        except (AttributeError, TypeError) as e:
            extraction_error = PptxExtractionError(self.name, 0, "presentation metadata", e)
            logger.debug("Failed to extract presentation metadata: %s", str(extraction_error))

        if metadata_added > 0:
            logger.info("Successfully added %d metadata properties to docling document", metadata_added)
        else:
            logger.debug("No metadata found in presentation")

        return docling_document
