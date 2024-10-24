from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
from unstructured.documents.coordinates import CoordinateSystem, Orientation
from unstructured.documents.elements import Element as UnstructuredElement

from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.ingestion.providers.unstructured.images import UnstructuredImageProvider


class UnstructuredPdfProvider(UnstructuredImageProvider):
    """
    A specialized provider that handles pdfs using the Unstructured
    """

    SUPPORTED_DOCUMENT_TYPES = {
        DocumentType.PDF,
    }

    @staticmethod
    def _load_document_as_image(document_path: Path, page: int | None = None) -> Image.Image:
        return convert_from_path(document_path, first_page=page, last_page=page)[0]  # type: ignore

    @staticmethod
    def _convert_coordinates(
        top_x: float,
        top_y: float,
        bottom_x: float,
        bottom_y: float,
        image_width: int,
        image_height: int,
        element: UnstructuredElement,
    ) -> tuple[float, float, float, float]:
        new_system = CoordinateSystem(image_width, image_height)
        new_system.orientation = Orientation.SCREEN
        new_top_x, new_top_y = element.metadata.coordinates.system.convert_coordinates_to_new_system(  # type: ignore
            new_system, top_x, top_y
        )
        new_bottom_x, new_bottom_y = element.metadata.coordinates.system.convert_coordinates_to_new_system(  # type: ignore
            new_system, bottom_x, bottom_y
        )
        return new_top_x, new_top_y, new_bottom_x, new_bottom_y
