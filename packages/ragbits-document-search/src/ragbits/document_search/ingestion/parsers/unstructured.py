import base64
import inspect
import os
from io import BytesIO

from PIL import Image
from typing_extensions import Self

try:
    from unstructured import utils
finally:
    # Unstructured does super slow call to scarf analytics, including checking nvidia-smi,
    # which adds couple of seconds of importing time.
    # This is a hack to disable it.
    utils.scarf_analytics = lambda *args: True

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.documents.elements import ElementType
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_from_dicts
from unstructured_client import UnstructuredClient
from unstructured_client.models.operations import PartitionRequestTypedDict
from unstructured_client.models.shared import FilesTypedDict, PartitionParametersTypedDict, Strategy

from ragbits.core.audit.traces import traceable
from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, ElementLocation, ImageElement, TextElement
from ragbits.document_search.ingestion.parsers.base import DocumentParser

UNSTRUCTURED_API_KEY_ENV = "UNSTRUCTURED_API_KEY"
UNSTRUCTURED_SERVER_URL_ENV = "UNSTRUCTURED_SERVER_URL"


class UnstructuredDocumentParser(DocumentParser):
    """
    Parser that uses the Unstructured API or local SDK to process the documents.
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
        """
        Initialize the UnstructuredDocumentParser instance.

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
        self.partition_kwargs = partition_kwargs or {}
        self.chunking_kwargs = chunking_kwargs or {}
        self.api_key = api_key or os.getenv(UNSTRUCTURED_API_KEY_ENV)
        self.api_server = api_server or os.getenv(UNSTRUCTURED_SERVER_URL_ENV)
        self.use_api = use_api
        self.ignore_images = ignore_images
        self._client = UnstructuredClient(api_key_auth=self.api_key, server_url=self.api_server)

    def __reduce__(self) -> tuple[type[Self], tuple]:
        """
        Enables the UnstructuredDocumentParser to be pickled and unpickled.

        Returns:
            The tuple of class and its arguments that allows object reconstruction.
        """
        return self.__class__, tuple(
            self.__getattribute__(param_name)
            for param_name in list(inspect.signature(self.__class__.__init__).parameters)[1:]
        )

    @traceable
    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the document using the Unstructured API.

        Args:
            document: The document to parse.

        Returns:
            The list of elements extracted from the document.

        Raises:
            ParserDocumentNotSupportedError: If the document type is not supported by the parser.
        """
        self.validate_document_type(document.metadata.document_type)
        elements = await self._partition(document)
        return self._chunk(elements, document)

    async def _partition(self, document: Document) -> list[UnstructuredElement]:
        """
        Partition the document.

        Args:
            document: The document to parse.

        Returns:
            The list of extracted elements.
        """
        if self.use_api:
            request = PartitionRequestTypedDict(
                partition_parameters=PartitionParametersTypedDict(
                    files=FilesTypedDict(
                        content=document.local_path.read_bytes(),
                        file_name=document.local_path.name,
                    ),
                    coordinates=True,
                    strategy=Strategy.HI_RES,
                    languages=["eng"],
                    extract_image_block_types=["Image", "Table"],
                    split_pdf_allow_failed=True,
                    split_pdf_concurrency_level=15,
                    split_pdf_page=True,
                    include_orig_elements=True,
                ),
            )
            request["partition_parameters"].update(**self.partition_kwargs)  # type: ignore
            response = await self._client.general.partition_async(request=request)
            return elements_from_dicts(response.elements) if response.elements else []

        return partition(
            filename=str(document.local_path),
            metadata_filename=document.local_path.name,
            extract_image_block_types=["Image", "Table"],
            extract_image_block_to_payload=True,
            include_orig_elements=True,
            **self.partition_kwargs,
        )

    def _chunk(self, elements: list[UnstructuredElement], document: Document) -> list[Element]:
        """
        Chunk the list of elements.

        Args:
            elements: The list of unstructured elements.
            document: The document to parse.

        Returns:
            The list of chunked elements.
        """
        nonimage_elements = [element for element in elements if element.category != ElementType.IMAGE]

        text_elements: list[Element] = [
            TextElement(
                document_meta=document.metadata,
                location=self._extract_element_location(element),
                content=element.text,
            )
            for element in chunk_elements(nonimage_elements, **self.chunking_kwargs)
        ]

        if self.ignore_images:
            return text_elements

        return text_elements + [
            ImageElement(
                document_meta=document.metadata,
                location=self._extract_element_location(element),
                image_bytes=self._extract_image_element_bytes(element, document),
                ocr_extracted_text=element.text,
            )
            for element in elements
            if element.category == ElementType.IMAGE
        ]

    @staticmethod
    def _extract_element_location(element: UnstructuredElement) -> ElementLocation:
        """
        Convert unstructured element to element location.

        Args:
            element: The element from unstructured.

        Returns:
            The element location.
        """
        metadata = element.metadata.to_dict()
        return ElementLocation(
            page_number=metadata.get("page_number"),
            coordinates=metadata.get("coordinates"),
        )

    @staticmethod
    def _extract_image_element_bytes(element: UnstructuredElement, document: Document) -> bytes:
        """
        Extract image data using alternative methods when element.metadata.image_base64 is empty.

        This handles cases where the Unstructured doesn't properly extract image data,
        requiring additional processing.

        Args:
            element: The Unstructured image element.
            document: The Document to parse.

        Return:
            The raw image data.
        """
        if element.metadata.image_base64:
            return base64.b64decode(element.metadata.image_base64)

        if element.metadata.coordinates and element.metadata.coordinates.points:
            buffered = BytesIO()
            Image.open(document.local_path).convert("RGB").crop(
                (
                    min(element.metadata.coordinates.points[0][0], element.metadata.coordinates.points[1][0]),
                    min(element.metadata.coordinates.points[0][1], element.metadata.coordinates.points[3][1]),
                    max(element.metadata.coordinates.points[2][0], element.metadata.coordinates.points[3][0]),
                    max(element.metadata.coordinates.points[1][1], element.metadata.coordinates.points[2][1]),
                )
            ).save(buffered, format="JPEG")
            return buffered.getvalue()

        return b""
