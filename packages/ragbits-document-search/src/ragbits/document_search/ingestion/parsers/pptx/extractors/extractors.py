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
from ragbits.document_search.documents.element import Element, ElementLocation, ImageElement, TextElement


class BasePptxExtractor(ABC):
    """Base class for all PPTX content extractors."""

    @staticmethod
    def _get_slides(presentation: Presentation, slide: Slide | None = None) -> list[tuple[int, Slide]]:
        """Get slides with their indices."""
        slides = [slide] if slide else list(presentation.slides)
        return list(enumerate(slides, start=1))


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

    @staticmethod
    def _get_coordinates(shape: BaseShape | None) -> dict[str, Any]:
        """Extract coordinates from a shape."""
        if shape is None:
            return {}
        try:
            return {"left": shape.left, "top": shape.top, "width": shape.width, "height": shape.height}
        except AttributeError:
            return {}

    @staticmethod
    def _create_image_element(
        document_meta: DocumentMeta,
        image_bytes: bytes,
        slide_idx: int,
        shape: BaseShape | None = None,
        description: str | None = None,
        coordinates: dict[str, Any] | None = None,
    ) -> ImageElement:
        """Create an ImageElement with standardized location."""
        if coordinates is None:
            coordinates = BasePptxExtractor._get_coordinates(shape)

        location = ElementLocation(page_number=slide_idx, coordinates=coordinates)

        return ImageElement(
            document_meta=document_meta,
            location=location,
            image_bytes=image_bytes,
            description=description,
        )

    def _extract_from_shapes(
        self,
        presentation: Presentation,
        document_meta: DocumentMeta,
        slide: Slide | None,
        content_extractor: Callable[[BaseShape], str | None],
        element_type: str = "text",
    ) -> list[Element]:
        """Generic method to extract content from shapes based on extractor."""
        elements: list[Element] = []
        
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
                    pass

        return elements

    @abstractmethod
    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[Element]:
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
    ) -> list[Element]:
        """Extract text content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            content_extractor=self._extract_text_content,
        )

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
    ) -> list[Element]:
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

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[Element]:
        """Extract image content from the presentation or a specific slide."""
        elements: list[Element] = []
        
        for slide_idx, sld in self._get_slides(presentation, slide):
            for shape in sld.shapes:
                try:
                    if isinstance(shape, Picture) and hasattr(shape, "image") and shape.image is not None:
                        image_bytes = shape.image.blob
                        filename = shape.image.filename if hasattr(shape.image, "filename") else "embedded_image"
                        description = f"Image: {filename}"
                        
                        element = self._create_image_element(
                            document_meta=document_meta,
                            image_bytes=image_bytes,
                            slide_idx=slide_idx,
                            shape=shape,
                            description=description,
                        )
                        elements.append(element)
                except (AttributeError, TypeError):
                    pass

        return elements

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
    ) -> list[Element]:
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
    ) -> list[Element]:
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

        elements: list[Element] = []
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

    @staticmethod
    def get_extractor_name() -> str:
        """Get the name of this extractor."""
        return "pptx_metadata_extractor"


class PptxSpeakerNotesExtractor(BasePptxExtractor):
    """Extracts speaker notes from slides."""

    def extract(
        self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None
    ) -> list[Element]:
        """Extract speaker notes from the presentation or a specific slide."""
        elements: list[Element] = []

        for slide_idx, sld in self._get_slides(presentation, slide):
            try:
                if sld.has_notes_slide and sld.notes_slide.notes_text_frame is not None:
                    notes_slide = sld.notes_slide
                    notes_text_frame = notes_slide.notes_text_frame
                    text = getattr(notes_text_frame, "text", None)
                    text = text.strip() if text else None

                    if text:
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
            except (AttributeError, TypeError):
                pass

        return elements

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
