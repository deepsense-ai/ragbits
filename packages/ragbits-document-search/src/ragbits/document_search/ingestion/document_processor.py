import copy
from typing import Optional

from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.providers.unstructured import UnstructuredProvider

ProvidersConfig = dict[DocumentType, BaseProvider]

DEFAULT_PROVIDERS_CONFIG: ProvidersConfig = {
    DocumentType.TXT: UnstructuredProvider(),
    DocumentType.MD: UnstructuredProvider(),
    DocumentType.PDF: UnstructuredProvider(),
    DocumentType.DOCX: UnstructuredProvider(),
    DocumentType.DOC: UnstructuredProvider(),
    DocumentType.PPTX: UnstructuredProvider(),
    DocumentType.PPT: UnstructuredProvider(),
    DocumentType.XLSX: UnstructuredProvider(),
    DocumentType.XLS: UnstructuredProvider(),
    DocumentType.CSV: UnstructuredProvider(),
    DocumentType.HTML: UnstructuredProvider(),
    DocumentType.EPUB: UnstructuredProvider(),
    DocumentType.ORG: UnstructuredProvider(),
    DocumentType.ODT: UnstructuredProvider(),
    DocumentType.RST: UnstructuredProvider(),
    DocumentType.RTF: UnstructuredProvider(),
    DocumentType.TSV: UnstructuredProvider(),
    DocumentType.XML: UnstructuredProvider(),
}


class DocumentProcessor:
    """
    A class with an implementation of Document Processor, allowing to process documents.
    """

    def __init__(self, providers: dict[DocumentType, BaseProvider]):
        self._providers = providers

    @classmethod
    def from_config(cls, providers_config: Optional[ProvidersConfig] = None) -> "DocumentProcessor":
        """
        Create a DocumentProcessor from a configuration. If the configuration is not provided, the default configuration
        will be used. If the configuration is provided, it will be merged with the default configuration, overriding
        the default values for the document types that are defined in the configuration.
        Example of the configuration:
        {
            DocumentType.TXT: YourCustomProviderClass(),
            DocumentType.PDF: UnstructuredProvider(),
        }

        Args:
            providers_config: The dictionary with the providers configuration, mapping the document types to the
             provider class.

        Returns:
            The DocumentProcessor.
        """
        config = copy.deepcopy(DEFAULT_PROVIDERS_CONFIG)
        config.update(providers_config if providers_config is not None else {})

        return cls(providers=config)

    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Process the document.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.

        Raises:
            ValueError: If the provider for the document type is not defined in the configuration.
        """
        provider = self._providers.get(document_meta.document_type)
        if provider is None:
            raise ValueError(
                f"Provider for {document_meta.document_type} is not defined in the configuration:" f" {self._providers}"
            )

        return await provider.process(document_meta)
