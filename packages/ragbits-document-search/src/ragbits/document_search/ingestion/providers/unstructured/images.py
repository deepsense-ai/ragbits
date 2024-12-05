from pathlib import Path

from PIL import Image
from pydantic import BaseModel
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.documents.elements import ElementType

from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.factory import get_default_llm
from ragbits.core.prompt import Prompt
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, ImageElement
from ragbits.document_search.ingestion.providers.unstructured.default import UnstructuredDefaultProvider
from ragbits.document_search.ingestion.providers.unstructured.utils import (
    ImageDescriber,
    crop_and_convert_to_bytes,
    extract_image_coordinates,
    to_text_element,
)

DEFAULT_IMAGE_QUESTION_PROMPT = "Describe the content of the image."


class _ImagePrompt(Prompt):
    user_prompt: str = DEFAULT_IMAGE_QUESTION_PROMPT
    image_input_fields: list[str] = ["images"]


class _ImagePromptInput(BaseModel):
    images: list[bytes]


class UnstructuredImageProvider(UnstructuredDefaultProvider):
    """
    A specialized provider that handles pngs and jpgs using the Unstructured
    """

    SUPPORTED_DOCUMENT_TYPES = {
        DocumentType.JPG,
        DocumentType.PNG,
    }

    def __init__(
        self,
        partition_kwargs: dict | None = None,
        chunking_kwargs: dict | None = None,
        api_key: str | None = None,
        api_server: str | None = None,
        use_api: bool = False,
        llm: LLM | None = None,
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
            use_api: Whether to use the Unstructured API. If False, the provider will only use the local processing.
            llm: llm to use
        """
        super().__init__(partition_kwargs, chunking_kwargs, api_key, api_server, use_api)
        self.image_describer: ImageDescriber | None = None
        self._llm = llm

    async def _chunk_and_convert(
        self, elements: list[UnstructuredElement], document_meta: DocumentMeta, document_path: Path
    ) -> list[Element]:
        image_elements = [e for e in elements if e.category == ElementType.IMAGE]
        other_elements = [e for e in elements if e.category != ElementType.IMAGE]
        chunked_other_elements = chunk_elements(other_elements, **self.chunking_kwargs)

        text_elements: list[Element] = [to_text_element(element, document_meta) for element in chunked_other_elements]
        if self.ignore_images:
            return text_elements
        return text_elements + [
            await self._to_image_element(element, document_meta, document_path) for element in image_elements
        ]

    async def _to_image_element(
        self, element: UnstructuredElement, document_meta: DocumentMeta, document_path: Path
    ) -> ImageElement:
        top_x, top_y, bottom_x, bottom_y = extract_image_coordinates(element)
        image = self._load_document_as_image(document_path)
        top_x, top_y, bottom_x, bottom_y = self._convert_coordinates(
            top_x, top_y, bottom_x, bottom_y, image.width, image.height, element
        )

        img_bytes = crop_and_convert_to_bytes(image, top_x, top_y, bottom_x, bottom_y)
        prompt = _ImagePrompt(_ImagePromptInput(images=[img_bytes]))
        if self.image_describer is None:
            llm_to_use = self._llm if self._llm is not None else get_default_llm(LLMType.VISION)
            self.image_describer = ImageDescriber(llm_to_use)
        image_description = await self.image_describer.get_image_description(prompt=prompt)
        return ImageElement(
            description=image_description,
            ocr_extracted_text=element.text,
            image_bytes=img_bytes,
            document_meta=document_meta,
        )

    @staticmethod
    def _load_document_as_image(
        document_path: Path,
        page: int | None = None,  # pylint: disable=unused-argument
    ) -> Image.Image:
        return Image.open(document_path).convert("RGB")

    @staticmethod
    def _convert_coordinates(
        # pylint: disable=unused-argument
        top_x: float,
        top_y: float,
        bottom_x: float,
        bottom_y: float,
        image_width: int,
        image_height: int,
        element: UnstructuredElement,
    ) -> tuple[float, float, float, float]:
        return top_x, top_y, bottom_x, bottom_y
