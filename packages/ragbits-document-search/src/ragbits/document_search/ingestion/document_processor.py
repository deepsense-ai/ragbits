import copy
from collections.abc import Callable, Mapping, MutableMapping
from typing import cast

from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.providers.unstructured.default import UnstructuredDefaultProvider
from ragbits.document_search.ingestion.providers.unstructured.images import UnstructuredImageProvider
from ragbits.document_search.ingestion.providers.unstructured.pdf import UnstructuredPdfProvider

# TODO consider defining with some defined schema
ProvidersConfig = Mapping[DocumentType, Callable[[], BaseProvider] | BaseProvider]


DEFAULT_PROVIDERS_CONFIG: MutableMapping[DocumentType, Callable[[], BaseProvider] | BaseProvider] = {
    DocumentType.TXT: UnstructuredDefaultProvider,
    DocumentType.MD: UnstructuredDefaultProvider,
    DocumentType.PDF: UnstructuredPdfProvider,
    DocumentType.DOCX: UnstructuredDefaultProvider,
    DocumentType.DOC: UnstructuredDefaultProvider,
    DocumentType.PPTX: UnstructuredDefaultProvider,
    DocumentType.PPT: UnstructuredDefaultProvider,
    DocumentType.XLSX: UnstructuredDefaultProvider,
    DocumentType.XLS: UnstructuredDefaultProvider,
    DocumentType.CSV: UnstructuredDefaultProvider,
    DocumentType.HTML: UnstructuredDefaultProvider,
    DocumentType.EPUB: UnstructuredDefaultProvider,
    DocumentType.ORG: UnstructuredDefaultProvider,
    DocumentType.ODT: UnstructuredDefaultProvider,
    DocumentType.RST: UnstructuredDefaultProvider,
    DocumentType.RTF: UnstructuredDefaultProvider,
    DocumentType.TSV: UnstructuredDefaultProvider,
    DocumentType.XML: UnstructuredDefaultProvider,
    DocumentType.JPG: UnstructuredImageProvider,
    DocumentType.PNG: UnstructuredImageProvider,
}


class DocumentProcessorRouter:
    """
    The DocumentProcessorRouter is responsible for routing the document to the correct provider based on the document
    metadata such as the document type.
    """

    def __init__(self, providers: ProvidersConfig):
        self._providers = providers

    @staticmethod
    def from_dict_to_providers_config(dict_config: dict[str, ObjectContructionConfig]) -> ProvidersConfig:
        """
        Creates ProvidersConfig from dictionary that maps document types to the provider configuration.

        Args:
            dict_config: The dictionary with configuration.

        Returns:
            ProvidersConfig object.

        Raises:
            InvalidConfigError: If a provider class can't be found or is not the correct type.
        """
        providers_config = {}

        for document_type, config in dict_config.items():
            providers_config[DocumentType(document_type)] = cast(
                Callable[[], BaseProvider] | BaseProvider,
                BaseProvider.subclass_from_config(config),
            )

        return providers_config

    @classmethod
    def from_config(cls, providers: ProvidersConfig | None = None) -> "DocumentProcessorRouter":
        """
        Create a DocumentProcessorRouter from a configuration. If the configuration is not provided, the default
        configuration will be used. If the configuration is provided, it will be merged with the default configuration,
        overriding the default values for the document types that are defined in the configuration.
        Example of the configuration:
        {
            DocumentType.TXT: YourCustomProviderClass(),
            DocumentType.PDF: UnstructuredProvider(),
        }

        Args:
            providers: The dictionary with the providers configuration, mapping the document types to the
                provider class.

        Returns:
            The DocumentProcessorRouter.
        """
        config: MutableMapping[DocumentType, Callable[[], BaseProvider] | BaseProvider] = copy.deepcopy(
            DEFAULT_PROVIDERS_CONFIG
        )
        config.update(providers if providers is not None else {})

        return cls(providers=config)

    def get_provider(self, document_meta: DocumentMeta) -> BaseProvider:
        """
        Get the provider for the document.

        Args:
            document_meta: The document metadata.

        Returns:
            The provider for processing the document.

        Raises:
            ValueError: If no provider is found for the document type.
        """
        provider_class_or_provider = self._providers.get(document_meta.document_type)
        if provider_class_or_provider is None:
            raise ValueError(f"No provider found for the document type {document_meta.document_type}")
        elif isinstance(provider_class_or_provider, BaseProvider):
            provider = provider_class_or_provider
        else:
            provider = provider_class_or_provider()
        return provider
