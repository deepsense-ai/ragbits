from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Any

from pptx.presentation import Presentation
from pptx.slide import Slide
from pptx.shapes.base import BaseShape

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
        coordinates: dict[str, Any] | None = None
    ) -> TextElement:
        """Create a TextElement with standardized location."""
        if coordinates is None and shape is not None:
            coordinates = {
                "left": shape.left,
                "top": shape.top,
                "width": shape.width,
                "height": shape.height
            }
        
        location = ElementLocation(
            page_number=slide_idx,
            coordinates=coordinates or {}
        )
        
        return TextElement(
            element_type=element_type,
            document_meta=document_meta,
            location=location,
            content=content
        )

    def _extract_from_shapes(
        self,
        presentation: Presentation,
        document_meta: DocumentMeta,
        slide: Slide | None,
        shape_filter: Callable[[BaseShape], bool],
        content_extractor: Callable[[BaseShape], str],
        element_type: str = "text"
    ) -> list[TextElement]:
        """Generic method to extract content from shapes based on filter and extractor."""
        elements: list[TextElement] = []
        
        for slide_idx, sld in self._get_slides(presentation, slide):
            for shape in sld.shapes:
                if shape_filter(shape):
                    try:
                        content = content_extractor(shape)
                        if content.strip():
                            element = self._create_text_element(
                                element_type=element_type,
                                document_meta=document_meta,
                                content=content,
                                slide_idx=slide_idx,
                                shape=shape
                            )
                            elements.append(element)
                    except (AttributeError, TypeError):
                        continue
        
        return elements

    @abstractmethod
    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract content from the presentation or specific slide."""

    @abstractmethod
    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""


class PptxTextExtractor(BasePptxExtractor):
    """Extracts text content from text frames."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract text content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            shape_filter=lambda shape: shape.has_text_frame,
            content_extractor=lambda shape: str(shape.text_frame.text).strip()
        )

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_text_extractor"


class PptxHyperlinkExtractor(BasePptxExtractor):
    """Extracts hyperlink addresses from shapes."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract hyperlink content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            shape_filter=lambda shape: hasattr(shape, 'click_action') and shape.click_action.hyperlink.address,
            content_extractor=lambda shape: shape.click_action.hyperlink.address,
            element_type="hyperlink"
        )

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_hyperlink_extractor"


class PptxImageExtractor(BasePptxExtractor):
    """Extracts image information from shapes."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract image content from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            shape_filter=lambda shape: shape.image and shape.image is not None,
            content_extractor=lambda shape: f"Image: {shape.image.filename if hasattr(shape.image, 'filename') else 'embedded_image'}",
            element_type="image"
        )

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_image_extractor"


class PptxShapeExtractor(BasePptxExtractor):
    """Extracts shape information and metadata."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract shape metadata from the presentation or a specific slide."""
        return self._extract_from_shapes(
            presentation=presentation,
            document_meta=document_meta,
            slide=slide,
            shape_filter=lambda shape: hasattr(shape, 'shape_type'),
            content_extractor=lambda shape: f"Shape: {shape.shape_type}",
            element_type="shape"
        )

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_shape_extractor"


class PptxMetadataExtractor(BasePptxExtractor):
    """Extracts document metadata."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
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
                    slide_idx=0
                )
                elements.append(element)

        return elements

    def get_extractor_name(self) -> str:
        """Get the name of this extractor."""
        return "pptx_metadata_extractor"


class PptxSpeakerNotesExtractor(BasePptxExtractor):
    """Extracts speaker notes from slides."""

    def extract(self, presentation: Presentation, document_meta: DocumentMeta, slide: Slide | None = None) -> list[TextElement]:
        """Extract speaker notes from the presentation or a specific slide."""
        elements: list[TextElement] = []
        
        for slide_idx, sld in self._get_slides(presentation, slide):
            if sld.has_notes_slide and sld.notes_slide.notes_text_frame is not None:
                notes_slide = sld.notes_slide
                notes_text_frame = notes_slide.notes_text_frame
                text = notes_text_frame.text.strip() if notes_text_frame is not None else None
                
                if text and notes_text_frame is not None:
                    coordinates = {
                        "left": notes_text_frame.margin_left,
                        "right": notes_text_frame.margin_right,
                        "top": notes_text_frame.margin_top,
                        "bottom": notes_text_frame.margin_bottom
                    }
                    
                    element = self._create_text_element(
                        element_type="speaker_notes",
                        document_meta=document_meta,
                        content=text,
                        slide_idx=slide_idx,
                        coordinates=coordinates
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