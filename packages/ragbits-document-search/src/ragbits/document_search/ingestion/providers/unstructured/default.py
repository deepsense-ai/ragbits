from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_from_dicts
from unstructured_client import UnstructuredClient

from ragbits.core.audit import trace
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, IntermediateElement
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.providers.unstructured.utils import check_required_argument, to_text_element

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


class UnstructuredDefaultProvider(BaseProvider):
    """
    A provider that uses the Unstructured API or local SDK to process the documents.
    """

    SUPPORTED_DOCUMENT_TYPES = {
        DocumentType.TXT,
        DocumentType.MD,
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

    def __init__(
        self,
        partition_kwargs: dict | None = None,
        chunking_kwargs: dict | None = None,
        api_key: str | None = None,
        api_server: str | None = None,
        use_api: bool = False,
        ignore_images: bool = False,
    ) -> None:
        """Initialize the UnstructuredDefaultProvider.

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

    async def process(self, document_meta: DocumentMeta) -> Sequence[Element | IntermediateElement]:
        """
        Process the document using the Unstructured API.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            DocumentTypeNotSupportedError: If the document type is not supported.

        """
        with trace(
            partition_arg=self.partition_kwargs,
            chunking_arg=self.chunking_kwargs,
            api_server=self.api_server,
            api_key=self.api_key,
            ignore_images=self.ignore_images,
        ) as outputs:
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

            outputs.results = await self._chunk_and_convert(elements, document_meta, document.local_path)
            return outputs.results

    async def _chunk_and_convert(
        # pylint: disable=unused-argument
        self,
        elements: list[UnstructuredElement],
        document_meta: DocumentMeta,
        document_path: Path,
    ) -> Sequence[Element | IntermediateElement]:
        chunked_elements = chunk_elements(elements, **self.chunking_kwargs)
        return [to_text_element(element, document_meta) for element in chunked_elements]
