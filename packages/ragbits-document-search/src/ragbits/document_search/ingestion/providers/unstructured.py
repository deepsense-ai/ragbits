import os
from typing import Optional

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.staging.base import elements_from_dicts
from unstructured_client import UnstructuredClient

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
UNSTRUCTURED_SERVER_URL_ENV = "UNSTRUCTURED_SERVER_URL"


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
        self._client = None

    @property
    def client(self) -> UnstructuredClient:
        """Get the UnstructuredClient instance. If the client is not initialized, it will be created.

        Returns:
            The UnstructuredClient instance.

        Raises:
            ValueError: If the UNSTRUCTURED_API_KEY_ENV environment variable is not set.
            ValueError: If the UNSTRUCTURED_SERVER_URL_ENV environment variable is not set.
        """
        if self._client is not None:
            return self._client
        if (api_key := os.getenv(UNSTRUCTURED_API_KEY_ENV)) is None:
            print(api_key)
            print("I should raise here")
            raise ValueError(f"{UNSTRUCTURED_API_KEY_ENV} environment variable is not set")
        if (server_url := os.getenv(UNSTRUCTURED_SERVER_URL_ENV)) is None:
            raise ValueError(f"{UNSTRUCTURED_SERVER_URL_ENV} environment variable is not set")
        self._client = UnstructuredClient(api_key_auth=api_key, server_url=server_url)
        return self._client

    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """Process the document using the Unstructured API.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            DocumentTypeNotSupportedError: If the document type is not supported.

        """
        self.validate_document_type(document_meta.document_type)
        document = await document_meta.fetch()

        res = await self.client.general.partition_async(
            request={
                "partition_parameters": {
                    "files": {
                        "content": document.local_path.read_bytes(),
                        "file_name": document.local_path.name,
                    },
                    **self.partition_kwargs,
                }
            }
        )
        elements = chunk_elements(elements_from_dicts(res.elements), **self.chunking_kwargs)
        return [_to_text_element(element, document_meta) for element in elements]


def _to_text_element(element: UnstructuredElement, document_meta: DocumentMeta) -> TextElement:
    return TextElement(
        document_meta=document_meta,
        content=element.text,
    )
