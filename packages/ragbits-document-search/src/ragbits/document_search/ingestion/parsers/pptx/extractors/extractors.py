from __future__ import annotations

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


class BasePptxExtractor(ABC):
    """Base class for all PPTX content extractors."""

    def _get_slides(self, presentation: Presentation, slide: Slide | None = None) -> list[tuple[int, Slide]]:
        """Get slides with their indices."""
        slides = [slide] if slide else list(presentation.slides)
        return list(enumerate(slides, start=1))

    def _create_text_element(
        self,
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

        for slide_idx, sld in self._get_slides(presentation, slide):
            for shape in sld.shapes:
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
                except (AttributeError, TypeError):
                    continue

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

    def _extract_text_content(self, shape: BaseShape) -> str | None:
        """Extract text content from a shape."""
        if not isinstance(shape, Shape):
            return None
        return str(shape.text_frame.text).strip() if shape.text_frame.text else None

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract text content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            content_extractor=self._extract_text_content,
        )

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_text_extractor"


class PptxHyperlinkExtractor(BasePptxExtractor):
    """Extracts hyperlink addresses from shapes."""

    def _extract_hyperlink_content(self, shape: BaseShape) -> str | None:
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

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_hyperlink_extractor"


class PptxImageExtractor(BasePptxExtractor):
    """Extracts image information from shapes."""

    def _extract_image_content(self, shape: BaseShape) -> str | None:
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

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_image_extractor"


class PptxShapeExtractor(BasePptxExtractor):
    """Extracts shape information and metadata."""

    def _extract_shape_content(self, shape: BaseShape) -> str | None:
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

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_shape_extractor"


class PptxMetadataExtractor(BasePptxExtractor):
    """Extracts document metadata."""

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract metadata from the presentation."""
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

        return elements

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_metadata_extractor"


class PptxSpeakerNotesExtractor(BasePptxExtractor):
    """Extracts speaker notes from slides."""

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[TextElement]:
        """Extract speaker notes from the presentation or a specific slide."""
        elements: list[TextElement] = []

        for slide_idx, sld in self._get_slides(presentation, slide):
            if sld.has_notes_slide and sld.notes_slide.notes_text_frame is not None:
                notes_slide = sld.notes_slide
                notes_text_frame = notes_slide.notes_text_frame
                text = getattr(notes_text_frame, "text", None)
                text = text.strip() if text else None

                if text:
                    coordinates = {
                        "left": notes_text_frame.margin_left,
                        "right": notes_text_frame.margin_right,
                        "top": notes_text_frame.margin_top,
                        "bottom": notes_text_frame.margin_bottom,
                    }

                    element = self._create_text_element(
                        element_type="speaker_notes",
                        document_meta=document_meta,
                        content=text,
                        slide_idx=slide_idx,
                        coordinates=coordinates,
                    )
                    elements.append(element)

        return elements

    def get_extractor_name(self) -> str:
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
