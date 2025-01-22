import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field
from typing_extensions import Self

from ragbits import document_search
from ragbits.core.audit import traceable
from ragbits.core.config import CoreConfig
from ragbits.core.embeddings import Embeddings, EmbeddingType
from ragbits.core.utils._pyproject import get_config_from_yaml
from ragbits.core.utils.config_handling import NoDefaultConfigError, ObjectContructionConfig, WithConstructionConfig
from ragbits.core.vector_stores import VectorStore
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element, ImageElement
from ragbits.document_search.documents.source_resolver import SourceResolver
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.processor_strategies import (
    ProcessingExecutionStrategy,
    SequentialProcessing,
)
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptions
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker


class SearchConfig(BaseModel):
    """
    Configuration for the search process.
    """

    reranker_kwargs: dict[str, Any] = Field(default_factory=dict)
    vector_store_kwargs: dict[str, Any] = Field(default_factory=dict)
    embedder_kwargs: dict[str, Any] = Field(default_factory=dict)


class DocumentSearchConfig(BaseModel):
    """
    Schema for for the dict taken by DocumentSearch.from_config method.
    """

    embedder: ObjectContructionConfig
    vector_store: ObjectContructionConfig
    rephraser: ObjectContructionConfig = ObjectContructionConfig(type="NoopQueryRephraser")
    reranker: ObjectContructionConfig = ObjectContructionConfig(type="NoopReranker")
    processing_strategy: ObjectContructionConfig = ObjectContructionConfig(type="SequentialProcessing")
    providers: dict[str, ObjectContructionConfig] = {}


class DocumentSearch(WithConstructionConfig):
    """
    A main entrypoint to the DocumentSearch functionality.

    It provides methods for both ingestion and retrieval.

    Retrieval:

        1. Uses QueryRephraser to rephrase the query.
        2. Uses VectorStore to retrieve the most relevant chunks.
        3. Uses Reranker to rerank the chunks.
    """

    # WithConstructionConfig configuration
    default_module: ClassVar = document_search
    configuration_key: ClassVar = "document_search"

    embedder: Embeddings
    vector_store: VectorStore
    query_rephraser: QueryRephraser
    reranker: Reranker
    document_processor_router: DocumentProcessorRouter
    processing_strategy: ProcessingExecutionStrategy

    def __init__(
        self,
        embedder: Embeddings,
        vector_store: VectorStore,
        query_rephraser: QueryRephraser | None = None,
        reranker: Reranker | None = None,
        document_processor_router: DocumentProcessorRouter | None = None,
        processing_strategy: ProcessingExecutionStrategy | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()
        self.document_processor_router = document_processor_router or DocumentProcessorRouter.from_config()
        self.processing_strategy = processing_strategy or SequentialProcessing()

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Creates and returns an instance of the DocumentSearch class from the given configuration.

        Args:
            config: A configuration object containing the configuration for initializing the DocumentSearch instance.

        Returns:
            DocumentSearch: An initialized instance of the DocumentSearch class.

        Raises:
            ValidationError: If the configuration doesn't follow the expected format.
            InvalidConfigError: If one of the specified classes can't be found or is not the correct type.
        """
        model = DocumentSearchConfig.model_validate(config)

        embedder: Embeddings = Embeddings.subclass_from_config(model.embedder)
        query_rephraser = QueryRephraser.subclass_from_config(model.rephraser)
        reranker: Reranker = Reranker.subclass_from_config(model.reranker)
        vector_store: VectorStore = VectorStore.subclass_from_config(model.vector_store)
        processing_strategy = ProcessingExecutionStrategy.subclass_from_config(model.processing_strategy)

        providers_config = DocumentProcessorRouter.from_dict_to_providers_config(model.providers)
        document_processor_router = DocumentProcessorRouter.from_config(providers_config)

        return cls(embedder, vector_store, query_rephraser, reranker, document_processor_router, processing_strategy)

    @classmethod
    def subclass_from_defaults(
        cls, defaults: CoreConfig, factory_path_override: str | None = None, yaml_path_override: Path | None = None
    ) -> Self:
        """
        Tries to create an instance by looking at default configuration file, and default factory function.
        Takes optional overrides for both, which takes a higher precedence.

        Args:
            defaults: The CoreConfig instance containing default factory and configuration details.
            factory_path_override: A string representing the path to the factory function
                in the format of "module.submodule:factory_name".
            yaml_path_override: A string representing the path to the YAML file containing
                the Ragstack instance configuration. Looks for the configuration under the key "document_search",
                and if not found, instantiates the class with the default configuration for each component.

        Raises:
            InvalidConfigError: If the default factory or configuration can't be found.
        """
        if yaml_path_override:
            config = get_config_from_yaml(yaml_path_override)

            # Look for explicit document search configuration
            if type_config := config.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectContructionConfig.model_validate(type_config))

            # Instantate the class with the default configuration for each component
            return cls.from_config(config)

        if factory_path_override:
            return cls.subclass_from_factory(factory_path_override)

        if default_factory := defaults.default_factories.get(cls.configuration_key):
            return cls.subclass_from_factory(default_factory)

        if defaults.default_instaces_config_path is not None:
            # Look for explicit document search configuration
            if default_config := defaults.default_instances_config.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectContructionConfig.model_validate(default_config))

            # Instantate the class with the default configuration for each component
            return cls.from_config(defaults.default_instances_config)

        raise NoDefaultConfigError(f"Could not find default factory or configuration for {cls.configuration_key}")

    @traceable
    async def search(self, query: str, config: SearchConfig | None = None) -> Sequence[Element]:
        """
        Search for the most relevant chunks for a query.

        Args:
            query: The query to search for.
            config: The search configuration.

        Returns:
            A list of chunks.
        """
        config = config or SearchConfig()
        queries = await self.query_rephraser.rephrase(query)
        elements = []
        for rephrased_query in queries:
            search_vector = await self.embedder.embed_text([rephrased_query])
            entries = await self.vector_store.retrieve(
                vector=search_vector[0],
                options=VectorStoreOptions(**config.vector_store_kwargs),
            )
            elements.extend([Element.from_vector_db_entry(entry) for entry in entries])

        return await self.reranker.rerank(
            elements=elements,
            query=query,
            options=RerankerOptions(**config.reranker_kwargs),
        )

    @traceable
    async def ingest(
        self,
        documents: str | Sequence[DocumentMeta | Document | Source],
        document_processor: BaseProvider | None = None,
    ) -> None:
        """Ingest documents into the search index.

        Args:
            documents: Either:
                - A sequence of `Document`, `DocumentMetadata`, or `Source` objects
                - A source-specific URI string (e.g., "gcs://bucket/*") to specify source location(s), for example:
                    - "file:///path/to/files/*.txt"
                    - "gcs://bucket/folder/*"
                    - "huggingface://dataset/split/row"
            document_processor: The document processor to use. If not provided, the document processor will be
                determined based on the document metadata.
        """
        if isinstance(documents, str):
            sources: Sequence[DocumentMeta | Document | Source] = await SourceResolver.resolve(documents)
        else:
            sources = documents
        elements = await self.processing_strategy.process_documents(
            sources, self.document_processor_router, document_processor
        )
        await self._remove_entries_with_same_sources(elements)
        await self.insert_elements(elements)

    async def _remove_entries_with_same_sources(self, elements: list[Element]) -> None:
        """
        Remove entries from the vector store whose source id is present in the elements' metadata.

        Args:
            elements: List of elements whose source ids will be checked and removed from the vector store if present.
        """
        unique_source_ids = {element.document_meta.source.id for element in elements}

        ids_to_delete = []
        # TODO: Pass 'where' argument to the list method to filter results and optimize search
        for entry in await self.vector_store.list():
            if entry.metadata.get("document_meta", {}).get("source", {}).get("id") in unique_source_ids:
                ids_to_delete.append(entry.id)

        if ids_to_delete:
            await self.vector_store.remove(ids_to_delete)

    async def insert_elements(self, elements: list[Element]) -> None:
        """
        Insert Elements into the vector store.

        Args:
            elements: The list of Elements to insert.
        """
        elements_with_text = [element for element in elements if element.key]
        images_with_text = [element for element in elements_with_text if isinstance(element, ImageElement)]
        vectors = await self.embedder.embed_text([element.key for element in elements_with_text])  # type: ignore

        image_elements = [element for element in elements if isinstance(element, ImageElement)]

        entries = [
            element.to_vector_db_entry(vector, EmbeddingType.TEXT)
            for element, vector in zip(elements_with_text, vectors, strict=False)
        ]
        not_embedded_image_elements = [
            image_element for image_element in image_elements if image_element not in images_with_text
        ]

        if image_elements and self.embedder.image_support():
            image_vectors = await self.embedder.embed_image([element.image_bytes for element in image_elements])
            entries.extend(
                [
                    element.to_vector_db_entry(vector, EmbeddingType.IMAGE)
                    for element, vector in zip(image_elements, image_vectors, strict=False)
                ]
            )
            not_embedded_image_elements = []

        for image_element in not_embedded_image_elements:
            warnings.warn(f"Image: {image_element.id} could not be embedded")

        await self.vector_store.store(entries)
