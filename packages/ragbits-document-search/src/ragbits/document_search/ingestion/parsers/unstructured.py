import io
import os
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.documents.elements import ElementType
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_from_dicts
from unstructured_client import UnstructuredClient

from ragbits.core.audit import traceable
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, ElementLocation, ImageElement, TextElement
from ragbits.document_search.ingestion.parsers.base import DocumentParser

DEFAULT_PARTITION_KWARGS: dict = {
    "strategy": "hi_res",
    "languages": ["eng"],
    "split_pdf_page": True,
    "split_pdf_allow_failed": True,
    "split_pdf_concurrency_level": 15,
}

DEFAULT_CHUNKING_KWARGS: dict = {}

UNSTRUCTURED_API_KEY_ENV = "UNSTRUCTURED_API_KEY"
UNSTRUCTURED_SERVER_URL_ENV = "UNSTRUCTURED_SERVER_URL"


class UnstructuredDocumentParser(DocumentParser):
    """
    A provider that uses the Unstructured API or local SDK to process the documents.
    """

    supported_document_types = {
        DocumentType.TXT,
        DocumentType.MD,
        DocumentType.PDF,
        DocumentType.DOCX,
        DocumentType.DOC,
        DocumentType.PPTX,
        DocumentType.PPT,
        DocumentType.XLSX,
        DocumentType.XLS,
        DocumentType.CSV,
        DocumentType.HTML,
        DocumentType.EPUB,
        DocumentType.ORG,
        DocumentType.ODT,
        DocumentType.RST,
        DocumentType.RTF,
        DocumentType.TSV,
        DocumentType.JSON,
        DocumentType.XML,
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
        ignore_images: bool = False,
    ) -> None:
        """Initialize the UnstructuredDocumentParser.

        Args:
            partition_kwargs: The additional arguments for the partitioning. Refer to the Unstructured API documentation
                for the available options: https://docs.unstructured.io/api-reference/api-services/api-parameters
            chunking_kwargs: The additional arguments for the chunking.
            api_key: The API key to use for the Unstructured API. If not specified, the UNSTRUCTURED_API_KEY environment
                variable will be used.
            api_server: The API server URL to use for the Unstructured API. If not specified, the
                UNSTRUCTURED_SERVER_URL environment variable will be used.
            use_api: whether to use Unstructured API, otherwise use local version of Unstructured library
            ignore_images: if True images will be skipped
        """
        self.partition_kwargs = partition_kwargs or DEFAULT_PARTITION_KWARGS
        self.chunking_kwargs = chunking_kwargs or DEFAULT_CHUNKING_KWARGS
        self.api_key = api_key
        self.api_server = api_server
        self.use_api = use_api
        self._client: UnstructuredClient | None = None
        self.ignore_images = ignore_images

    @property
    def client(self) -> UnstructuredClient:
        """
        Get the UnstructuredClient instance. If the client is not initialized, it will be created.

        Returns:
            The UnstructuredClient instance.

        Raises:
            ValueError: If the UNSTRUCTURED_API_KEY_ENV environment variable is not set.
            ValueError: If the UNSTRUCTURED_SERVER_URL_ENV environment variable is not set.
        """
        if self._client is not None:
            return self._client
        api_key = check_required_argument(arg_name="api_key", value=self.api_key, fallback_env=UNSTRUCTURED_API_KEY_ENV)
        api_server = check_required_argument(
            arg_name="api_server", value=self.api_server, fallback_env=UNSTRUCTURED_SERVER_URL_ENV
        )
        self._client = UnstructuredClient(api_key_auth=api_key, server_url=api_server)
        return self._client

    @traceable
    async def parse(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Process the document using the Unstructured API.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            DocumentTypeNotSupportedError: If the document type is not supported.

        """
        self.validate_document_type(document_meta.document_type)
        document = await document_meta.fetch()

        if self.use_api:
            res = await self.client.general.partition_async(
                request={
                    "partition_parameters": {
                        "files": {
                            "content": document.local_path.read_bytes(),
                            "file_name": document.local_path.name,
                        },
                        "coordinates": True,
                        **self.partition_kwargs,
                    }
                }
            )
            elements = elements_from_dicts(res.elements)  # type: ignore
        else:
            elements = partition(
                file=BytesIO(document.local_path.read_bytes()),
                metadata_filename=document.local_path.name,
                **self.partition_kwargs,
            )
        return await self._chunk_and_convert(elements, document_meta, document.local_path)

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
            await _to_image_element(element, document_meta, document_path) for element in image_elements
        ]


async def _to_image_element(
    element: UnstructuredElement, document_meta: DocumentMeta, document_path: Path
) -> ImageElement:
    top_x, top_y, bottom_x, bottom_y = extract_image_coordinates(element)

    image = (
        convert_from_path(document_path)[0]
        if document_meta.document_type == DocumentType.PDF
        else Image.open(document_path).convert("RGB")
    )
    img_bytes = crop_and_convert_to_bytes(image, top_x, top_y, bottom_x, bottom_y)
    return ImageElement(
        ocr_extracted_text=element.text,
        image_bytes=img_bytes,
        document_meta=document_meta,
    )


def to_text_element(element: UnstructuredElement, document_meta: DocumentMeta) -> TextElement:
    """
    Converts unstructured element to ragbits text element

    Args:
        element: element from unstructured
        document_meta: metadata of the document

    Returns:
        text element
    """
    location = to_element_location(element)
    return TextElement(
        document_meta=document_meta,
        content=element.text,
        location=location,
    )


def to_element_location(element: UnstructuredElement) -> ElementLocation:
    """
    Converts unstructured element to element location.

    Args:
        element: element from unstructured

    Returns:
        element location
    """
    metadata = element.metadata.to_dict()
    page_number = metadata.get("page_number")
    coordinates = metadata.get("coordinates")
    return ElementLocation(
        page_number=page_number,
        coordinates=coordinates,
    )


def check_required_argument(value: str | None, arg_name: str, fallback_env: str) -> str:
    """
    Checks if given environment variable is set and returns it or raises an error

    Args:
        arg_name: name of the variable
        value: optional default value
        fallback_env: name of the environment variable to get

    Raises:
        ValueError: if environment variable is not set

    Returns:
        environment variable value
    """
    if value is not None:
        return value
    if (env_value := os.getenv(fallback_env)) is None:
        raise ValueError(f"Either pass {arg_name} argument or set the {fallback_env} environment variable")
    return env_value


def extract_image_coordinates(element: UnstructuredElement) -> tuple[float, float, float, float]:
    """
    Extracts image coordinates from unstructured element
    Args:
        element: element from unstructured
    Returns:
        x of top left corner, y of top left corner, x of bottom right corner, y of bottom right corner
    """
    p1, p2, p3, p4 = element.metadata.coordinates.points  # type: ignore
    return min(p1[0], p2[0]), min(p1[1], p4[1]), max(p3[0], p4[0]), max(p2[1], p3[1])


def crop_and_convert_to_bytes(image: Image.Image, x0: float, y0: float, x1: float, y1: float) -> bytes:
    """
    Crops the image and converts to bytes
    Args:
        image: PIL image
        x0: x of top left corner
        y0: y of top left corner
        x1: x of bottom right corner
        y1: y of bottom right corner
    Returns:
        bytes of the cropped image
    """
    image = image.crop((x0, y0, x1, y1))
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()
