from pathlib import Path
from typing import Optional

import pymupdf
from PIL import Image
from unstructured.documents.coordinates import CoordinateSystem, Orientation
from unstructured.documents.elements import Element as UnstructuredElement

from ragbits.core.llms.litellm import LiteLLMOptions
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import ImageElement
from ragbits.document_search.ingestion.providers.unstructured.default import UnstructuredDefaultProvider
from ragbits.document_search.ingestion.providers.unstructured.utils import (
    ImageDescriber,
    crop_and_convert_to_bytes,
    extract_image_coordinates,
)

DEFAULT_LLM_IMAGE_SUMMARIZATION_MODEL = "gpt-4o-mini"
DEFAULT_PDF_DPI = 300
DEFAULT_LLM_OPTIONS = LiteLLMOptions()


class UnstructuredPdfProvider(UnstructuredDefaultProvider):
    """
    A specialized provider that handles pdfs using the Unstructured
    """

    SUPPORTED_DOCUMENT_TYPES = {
        DocumentType.PDF,
    }

    def __init__(
        # pylint: disable=too-many-arguments
        self,
        partition_kwargs: Optional[dict] = None,
        chunking_kwargs: Optional[dict] = None,
        api_key: Optional[str] = None,
        api_server: Optional[str] = None,
        use_api: bool = False,
        llm_model_name: Optional[str] = None,
        llm_options: Optional[LiteLLMOptions] = None,
        pdf_dpi: Optional[int] = None,
    ) -> None:
        """Initialize the UnstructuredPdfProvider.

        Args:
            partition_kwargs: The additional arguments for the partitioning. Refer to the Unstructured API documentation
                for the available options: https://docs.unstructured.io/api-reference/api-services/api-parameters
            chunking_kwargs: The additional arguments for the chunking.
            api_key: The API key to use for the Unstructured API. If not specified, the UNSTRUCTURED_API_KEY environment
                variable will be used.
            api_server: The API server URL to use for the Unstructured API. If not specified, the
                UNSTRUCTURED_SERVER_URL environment variable will be used.
            llm_model_name: name of LLM model to be used.
            llm_options: llm lite options to be used.
            pdf_dpi: How many dpi should be used when rendering pdf. The higher, the better quality but more tokes
                would be used when creating a summary.
        """
        super().__init__(partition_kwargs, chunking_kwargs, api_key, api_server, use_api)
        self.image_summarizer = ImageDescriber(
            llm_model_name or DEFAULT_LLM_IMAGE_SUMMARIZATION_MODEL, llm_options or DEFAULT_LLM_OPTIONS
        )
        self.pdf_dpi = pdf_dpi

    async def _to_image_element(
        self, element: UnstructuredElement, document_meta: DocumentMeta, document_path: Path
    ) -> ImageElement:
        image_coordinates = extract_image_coordinates(element)
        page_number = element.metadata.page_number - 1  # 0-indexed in PyMuPDF

        pdf_document = pymupdf.open(document_path)
        page = pdf_document.load_page(page_number)

        pixel_map = page.get_pixmap(dpi=self.pdf_dpi)
        new_system = CoordinateSystem(pixel_map.width, pixel_map.height)
        new_system.orientation = Orientation.SCREEN
        x0, y0 = element.metadata.coordinates.system.convert_coordinates_to_new_system(
            new_system, image_coordinates[0], image_coordinates[1]
        )
        x1, y1 = element.metadata.coordinates.system.convert_coordinates_to_new_system(
            new_system, image_coordinates[2], image_coordinates[3]
        )

        image = Image.frombytes("RGB", [pixel_map.width, pixel_map.height], pixel_map.samples)
        img_bytes = crop_and_convert_to_bytes(image, x0, y0, x1, y1)
        image_description = await self.image_summarizer.get_image_description(img_bytes)
        return ImageElement(
            description=image_description,
            ocr_extracted_text=element.text,
            image_bytes=img_bytes,
            document_meta=document_meta,
        )
