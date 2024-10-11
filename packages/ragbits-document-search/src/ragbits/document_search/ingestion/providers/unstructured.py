import os
from io import BytesIO

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.partition.api import partition_via_api

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.ingestion.providers.base import BaseProvider

DEFAULT_PARTITION_KWARGS: dict = {
    "strategy": "hi_res",
    "languages": ["eng"],
    "split_pdf_page": True,
    "split_pdf_allow_failed": True,
    "split_pdf_concurrency_level": 15,
}

DEFAULT_CHUNKING_KWARGS: dict = {}

UNSTRUCTURED_API_KEY_ENV = "UNSTRUCTURED_API_KEY"
UNSTRUCTURED_API_URL_ENV = "UNSTRUCTURED_API_URL"


class UnstructuredProvider(BaseProvider):
    """
    A provider that uses the Unstructured API to process the documents.
    """

    SUPPORTED_DOCUMENT_TYPES = {
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
        DocumentType.XML,
    }

    def __init__(self, partition_kwargs: Optional[dict] = None, chunking_kwargs: Optional[dict] = None):
        """Initialize the UnstructuredProvider.

        Args:
            partition_kwargs: The additional arguments for the partitioning. Refer to the Unstructured API documentation
                for the available options: https://docs.unstructured.io/api-reference/api-services/api-parameters
        """
        self.partition_kwargs = partition_kwargs or DEFAULT_PARTITION_KWARGS
        self.chunking_kwargs = chunking_kwargs or DEFAULT_CHUNKING_KWARGS

    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """Process the document using the Unstructured API.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            ValueError: If the UNSTRUCTURED_API_KEY or UNSTRUCTURED_API_URL environment variables are not set.
            DocumentTypeNotSupportedError: If the document type is not supported.

        """
        self.validate_document_type(document_meta.document_type)
        if (api_key := os.getenv(UNSTRUCTURED_API_KEY_ENV)) is None:
            raise ValueError(f"{UNSTRUCTURED_API_KEY_ENV} environment variable is not set")
        if (api_url := os.getenv(UNSTRUCTURED_API_URL_ENV)) is None:
            raise ValueError(f"{UNSTRUCTURED_API_URL_ENV} environment variable is not set")

        document = await document_meta.fetch()

        # TODO: Currently this is a blocking call. It should be made async.
        elements = partition_via_api(
            file=BytesIO(document.local_path.read_bytes()),
            metadata_filename=document.local_path.name,
            api_key=api_key,
            api_url=api_url,
            **self.partition_kwargs,
        )
        elements = chunk_elements(elements, **self.chunking_kwargs)
        return [_to_text_element(element, document_meta) for element in elements]


def _to_text_element(element: UnstructuredElement, document_meta: DocumentMeta) -> TextElement:
    return TextElement(
        document_meta=document_meta,
        content=element.text,
    )
