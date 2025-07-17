from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pptx.presentation import Presentation
from pptx.shapes.autoshape import Shape
from pptx.shapes.base import BaseShape
from pptx.shapes.group import GroupShape
from pptx.shapes.picture import Picture
from pptx.slide import Slide

from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import ElementLocation, TextElement
from ragbits.document_search.ingestion.parsers.pptx.exceptions import (
    PptxExtractorError,
    PptxSlideProcessingError,
)

logger = logging.getLogger(__name__)


class BasePptxExtractor(ABC):
    """Base class for all PPTX content extractors."""

    @staticmethod
    def _get_slides(presentation: Presentation, slide: Slide | None = None) -> list[tuple[int, Slide]]:
        """Get slides with their indices."""
        slides = [slide] if slide else list(presentation.slides)
        return list(enumerate(slides, start=1))

    @staticmethod
    def _get_shape_info(shape: BaseShape) -> str:
        """Get descriptive information about a shape for logging purposes."""
        try:
            shape_type = getattr(shape, "shape_type", "unknown")
            shape_name = getattr(shape, "name", "unnamed")
            shape_id = getattr(shape, "shape_id", "no_id")
            return f"type={shape_type}, name={shape_name}, id={shape_id}"
        except Exception:
            return "unknown_shape"

    @staticmethod
    def _create_text_element(
        element_type: str,
        document_meta: DocumentMeta,
        content: str,
        slide_idx: int,
        shape: BaseShape | None = None,
        coordinates: dict[str, Any] | None = None,
    ) -> TextElement:
        """Create a TextElement with standardized location."""
        if coordinates is None and shape is not None:
            coordinates = {"left": shape.left, "top": shape.top, "width": shape.width, "height": shape.height}

        location = ElementLocation(page_number=slide_idx, coordinates=coordinates or {})

        return TextElement(element_type=element_type, document_meta=document_meta, location=location, content=content)

    def _extract_from_shapes(
        self,
        presentation: Presentation,
        document_meta: DocumentMeta,
        slide: Slide | None,
        content_extractor: Callable[[BaseShape], str | None],
        element_type: str = "text",
    ) -> list[TextElement]:
        """Generic method to extract content from shapes based on extractor."""
        elements: list[TextElement] = []
        extractor_name = self.get_extractor_name()
        total_shapes_processed = 0
        failed_extractions = 0

        logger.debug(
            "Starting shape extraction for %s on %d slides",
            extractor_name,
            len(list(self._get_slides(presentation, slide))),
        )

        for slide_idx, sld in self._get_slides(presentation, slide):
            slide_shapes_count = 0
            slide_extracted_count = 0
            slide_failed_count = 0

            try:
                for shape in sld.shapes:
                    total_shapes_processed += 1
                    slide_shapes_count += 1

                    try:
                        content = content_extractor(shape)
                        if content and content.strip():
                            element = self._create_text_element(
                                element_type=element_type,
                                document_meta=document_meta,
                                content=content,
                                slide_idx=slide_idx,
                                shape=shape,
                            )
                            elements.append(element)
                            slide_extracted_count += 1
                            logger.debug(
                                "Successfully extracted %s content from shape on slide %d", element_type, slide_idx
                            )
                    except (AttributeError, TypeError) as e:
                        failed_extractions += 1
                        slide_failed_count += 1
                        shape_info = self._get_shape_info(shape)
                        logger.warning(
                            "Failed to extract content from shape on slide %d using %s: %s. Shape: %s",
                            slide_idx,
                            extractor_name,
                            str(e),
                            shape_info,
                            exc_info=False,
                        )
                    except Exception as e:
                        failed_extractions += 1
                        slide_failed_count += 1
                        shape_info = self._get_shape_info(shape)
                        logger.error(
                            "Unexpected error extracting content from shape on slide %d using %s: %s. Shape: %s",
                            slide_idx,
                            extractor_name,
                            str(e),
                            shape_info,
                            exc_info=True,
                        )

                logger.debug(
                    "Slide %d processing complete: %d shapes total, %d extracted, %d failed",
                    slide_idx,
                    slide_shapes_count,
                    slide_extracted_count,
                    slide_failed_count,
                )

            except Exception as e:
                logger.error(
                    "Failed to process slide %d with %s: %s",
                    slide_idx,
                    extractor_name,
                    str(e),
                    exc_info=True,
                )
                raise PptxSlideProcessingError(extractor_name, slide_idx, e) from e

        success_rate = (
            ((total_shapes_processed - failed_extractions) / total_shapes_processed * 100)
            if total_shapes_processed > 0
            else 100.0
        )

        logger.info(
            "%s extraction completed: %d elements extracted, %d total shapes processed, "
            "%d failed extractions (%.1f%% success rate)",
            extractor_name,
            len(elements),
            total_shapes_processed,
            failed_extractions,
            success_rate,
        )

        return elements

    @abstractmethod
    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract content from the presentation or specific slide."""

    @abstractmethod
    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""


class PptxTextExtractor(BasePptxExtractor):
    """Extracts text content from text frames."""

    @staticmethod
    def _extract_text_content(shape: BaseShape) -> str | None:
        """Extract text content from a shape."""
        if not isinstance(shape, Shape):
            return None
        return str(shape.text_frame.text).strip() if shape.text_frame.text else None

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract text content from the presentation or a specific slide."""
        logger.debug("Starting text extraction from PPTX document")
        try:
            elements = self._extract_from_shapes(
                presentation=presentation,
                document_meta=document_meta,
                slide=slide,
                content_extractor=self._extract_text_content,
            )
            logger.debug("Text extraction completed: %d elements found", len(elements))
            return elements
        except Exception as e:
            logger.error("Text extraction failed: %s", str(e), exc_info=True)
            raise PptxExtractorError(self.get_extractor_name(), e) from e

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_text_extractor"


class PptxHyperlinkExtractor(BasePptxExtractor):
    """Extracts hyperlink addresses from shapes."""

    @staticmethod
    def _extract_hyperlink_content(shape: BaseShape) -> str | None:
        """Extract hyperlink content from a shape."""
        if not hasattr(shape, "click_action") or isinstance(shape, GroupShape):
            return None
        if not shape.click_action.hyperlink or not shape.click_action.hyperlink.address:
            return None
        return shape.click_action.hyperlink.address

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract hyperlink content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            content_extractor=self._extract_hyperlink_content,
            element_type="hyperlink",
        )

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_hyperlink_extractor"


class PptxImageExtractor(BasePptxExtractor):
    """Extracts image information from shapes."""

    @staticmethod
    def _extract_image_content(shape: BaseShape) -> str | None:
        """Extract image content from a shape."""
        if not isinstance(shape, Picture):
            return None
        if not hasattr(shape, "image") or shape.image is None:
            return None
        filename = shape.image.filename if hasattr(shape.image, "filename") else "embedded_image"
        return f"Image: {filename}"

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract image content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            content_extractor=self._extract_image_content,
            element_type="image",
        )

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_image_extractor"


class PptxShapeExtractor(BasePptxExtractor):
    """Extracts shape information and metadata."""

    @staticmethod
    def _extract_shape_content(shape: BaseShape) -> str | None:
        """Extract shape metadata from a shape."""
        if not hasattr(shape, "shape_type"):
            return None
        return f"Shape: {shape.shape_type}"

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract shape metadata from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            content_extractor=self._extract_shape_content,
            element_type="shape",
        )

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_shape_extractor"


class PptxMetadataExtractor(BasePptxExtractor):
    """Extracts document metadata."""

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract metadata from the presentation."""
        logger.debug("Starting metadata extraction from PPTX document")
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

            elements = []
            for prop_name, prop_value in properties:
                if prop_value is not None and str(prop_value).strip():
                    element = self._create_text_element(
                        element_type="metadata",
                        document_meta=document_meta,
                        content=f"{prop_name}: {prop_value}",
                        slide_idx=0,
                    )
                    elements.append(element)
                    logger.debug("Extracted metadata property: %s", prop_name)

            logger.debug("Metadata extraction completed: %d properties found", len(elements))
            return elements
        except Exception as e:
            logger.error("Metadata extraction failed: %s", str(e), exc_info=True)
            raise PptxExtractorError(self.get_extractor_name(), e) from e

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_metadata_extractor"


class PptxSpeakerNotesExtractor(BasePptxExtractor):
    """Extracts speaker notes from slides."""

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract speaker notes from the presentation or a specific slide."""
        logger.debug("Starting speaker notes extraction from PPTX document")
        try:
            elements: list[TextElement] = []
            slides_with_notes = 0
            total_slides = len(list(self._get_slides(presentation, slide)))

            for slide_idx, sld in self._get_slides(presentation, slide):
                try:
                    if sld.has_notes_slide and sld.notes_slide.notes_text_frame is not None:
                        notes_slide = sld.notes_slide
                        notes_text_frame = notes_slide.notes_text_frame
                        text = getattr(notes_text_frame, "text", None)
                        text = text.strip() if text else None

                        if text:
                            slides_with_notes += 1
                            try:
                                coordinates = {
                                    "left": getattr(notes_text_frame, "margin_left", 0),
                                    "right": getattr(notes_text_frame, "margin_right", 0),
                                    "top": getattr(notes_text_frame, "margin_top", 0),
                                    "bottom": getattr(notes_text_frame, "margin_bottom", 0),
                                }
                            except (AttributeError, TypeError):
                                coordinates = {}

                            element = self._create_text_element(
                                element_type="speaker_notes",
                                document_meta=document_meta,
                                content=text,
                                slide_idx=slide_idx,
                                coordinates=coordinates,
                            )
                            elements.append(element)
                            logger.debug("Extracted speaker notes from slide %d", slide_idx)
                except Exception as e:
                    logger.warning(
                        "Failed to extract speaker notes from slide %d: %s", slide_idx, str(e), exc_info=False
                    )

            logger.debug(
                "Speaker notes extraction completed: %d slides with notes out of %d total slides",
                slides_with_notes,
                total_slides,
            )
            return elements
        except Exception as e:
            logger.error("Speaker notes extraction failed: %s", str(e), exc_info=True)
            raise PptxExtractorError(self.get_extractor_name(), e) from e

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_speaker_notes_extractor"


DEFAULT_EXTRACTORS = [
    PptxTextExtractor(),
    PptxHyperlinkExtractor(),
    PptxImageExtractor(),
    PptxShapeExtractor(),
    PptxSpeakerNotesExtractor(),
    PptxMetadataExtractor(),
]
