import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field
from typing_extensions import Self

from ragbits import document_search
from ragbits.core.audit import trace, traceable
from ragbits.core.config import CoreConfig
from ragbits.core.llms.base import LLMType
from ragbits.core.llms.factory import get_preferred_llm
from ragbits.core.utils._pyproject import get_config_from_yaml
from ragbits.core.utils.config_handling import (
    NoPreferredConfigError,
    ObjectContructionConfig,
    WithConstructionConfig,
    import_by_path,
)
from ragbits.core.vector_stores import VectorStore
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search.documents import element
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element, IntermediateElement, IntermediateImageElement
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import SourceResolver
from ragbits.document_search.ingestion import intermediate_handlers
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.intermediate_handlers.base import BaseIntermediateHandler
from ragbits.document_search.ingestion.intermediate_handlers.images import ImageIntermediateHandler
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
    Schema for the dict taken by DocumentSearch.from_config method.
    """

    vector_store: ObjectContructionConfig
    rephraser: ObjectContructionConfig = ObjectContructionConfig(type="NoopQueryRephraser")
    reranker: ObjectContructionConfig = ObjectContructionConfig(type="NoopReranker")
    processing_strategy: ObjectContructionConfig = ObjectContructionConfig(type="SequentialProcessing")
    providers: dict[str, ObjectContructionConfig] = {}
    intermediate_element_handlers: dict[str, ObjectContructionConfig] = {}


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

    vector_store: VectorStore
    query_rephraser: QueryRephraser
    reranker: Reranker
    document_processor_router: DocumentProcessorRouter
    processing_strategy: ProcessingExecutionStrategy
    intermediate_element_handlers: dict[type[IntermediateElement], BaseIntermediateHandler]

    def __init__(
        self,
        vector_store: VectorStore,
        query_rephraser: QueryRephraser | None = None,
        reranker: Reranker | None = None,
        document_processor_router: DocumentProcessorRouter | None = None,
        processing_strategy: ProcessingExecutionStrategy | None = None,
        intermediate_element_handlers: dict[type[IntermediateElement], BaseIntermediateHandler] | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()
        self.document_processor_router = document_processor_router or DocumentProcessorRouter.from_config()
        self.processing_strategy = processing_strategy or SequentialProcessing()
        self.intermediate_element_handlers = intermediate_element_handlers or {
            IntermediateImageElement: ImageIntermediateHandler(llm=get_preferred_llm(llm_type=LLMType.VISION))
        }

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

        query_rephraser = QueryRephraser.subclass_from_config(model.rephraser)
        reranker: Reranker = Reranker.subclass_from_config(model.reranker)
        vector_store: VectorStore = VectorStore.subclass_from_config(model.vector_store)
        processing_strategy = ProcessingExecutionStrategy.subclass_from_config(model.processing_strategy)

        providers_config = DocumentProcessorRouter.from_dict_to_providers_config(model.providers)
        document_processor_router = DocumentProcessorRouter.from_config(providers_config)

        handlers = {
            import_by_path(element_type, element): import_by_path(
                handler_config["type"], intermediate_handlers
            ).from_config(handler_config["config"])
            for element_type, handler_config in config.get("intermediate_handlers", {}).items()
        }

        return cls(vector_store, query_rephraser, reranker, document_processor_router, processing_strategy, handlers)

    @classmethod
    def preferred_subclass(
        cls, config: CoreConfig, factory_path_override: str | None = None, yaml_path_override: Path | None = None
    ) -> Self:
        """
        Tries to create an instance by looking at project's component prefferences, either from YAML
        or from the factory. Takes optional overrides for both, which takes a higher precedence.

        Args:
            config: The CoreConfig instance containing preferred factory and configuration details.
            factory_path_override: A string representing the path to the factory function
                in the format of "module.submodule:factory_name".
            yaml_path_override: A string representing the path to the YAML file containing
                the Ragstack instance configuration. Looks for the configuration under the key "document_search",
                and if not found, instantiates the class with the preferred configuration for each component.

        Raises:
            InvalidConfigError: If the default factory or configuration can't be found.
        """
        if yaml_path_override:
            preferrences = get_config_from_yaml(yaml_path_override)

            # Look for explicit document search configuration
            if type_config := preferrences.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectContructionConfig.model_validate(type_config))

            # Instantate the class with the preferred configuration for each component
            return cls.from_config(preferrences)

        if factory_path_override:
            return cls.subclass_from_factory(factory_path_override)

        if preferred_factory := config.component_preference_factories.get(cls.configuration_key):
            return cls.subclass_from_factory(preferred_factory)

        if config.component_preference_config_path is not None:
            # Look for explicit document search configuration
            if preferred_config := config.preferred_instances_config.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectContructionConfig.model_validate(preferred_config))

            # Instantate the class with the prefereed configuration for each component
            return cls.from_config(config.preferred_instances_config)

        raise NoPreferredConfigError(f"Could not find preferred factory or configuration for {cls.configuration_key}")

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
        with trace(queries=queries, config=config, vectore_store=self.vector_store, reranker=self.reranker) as outputs:
            elements = []

            for rephrased_query in queries:
                results = await self.vector_store.retrieve(
                    text=rephrased_query,
                    options=VectorStoreOptions(**config.vector_store_kwargs),
                )
                elements.append([Element.from_vector_db_entry(result.entry) for result in results])

            outputs.search_results = await self.reranker.rerank(
                elements=elements,
                query=query,
                options=RerankerOptions(**config.reranker_kwargs),
            )
            return outputs.search_results

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
        with trace(
            documents=documents,
            document_processor=document_processor,
            document_processor_router=self.document_processor_router,
            processing_strategy=self.processing_strategy,
        ):
            if isinstance(documents, str):
                sources: Sequence[DocumentMeta | Document | Source] = await SourceResolver.resolve(documents)
            else:
                sources = documents
            raw_elements = await self.processing_strategy.process_documents(
                sources, self.document_processor_router, document_processor
            )

            intermediate_elements: dict[type, list[IntermediateElement]] = {}
            for raw_element in raw_elements:
                if isinstance(raw_element, IntermediateElement):
                    intermediate_elements.setdefault(type(raw_element), []).append(raw_element)

            elements = [raw_element for raw_element in raw_elements if not isinstance(raw_element, IntermediateElement)]

            for element_type, element_list in intermediate_elements.items():
                handler = self.intermediate_element_handlers.get(element_type)
                if handler:
                    processed_elements = await handler.process(element_list)
                    elements.extend(processed_elements)
                else:
                    warnings.warn(
                        f"No handler found for {element_type.__name__}. Keeping unprocessed elements.", RuntimeWarning
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

    @traceable
    async def insert_elements(self, elements: list[Element]) -> None:
        """
        Insert Elements into the vector store.

        Args:
            elements: The list of Elements to insert.
        """
        await self.vector_store.store([element.to_vector_db_entry() for element in elements])
