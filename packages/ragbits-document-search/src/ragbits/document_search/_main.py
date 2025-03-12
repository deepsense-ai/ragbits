from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field
from typing_extensions import Self

from ragbits import document_search
from ragbits.core.audit import traceable
from ragbits.core.config import CoreConfig
from ragbits.core.utils._pyproject import get_config_from_yaml
from ragbits.core.utils.config_handling import NoPreferredConfigError, ObjectContructionConfig, WithConstructionConfig
from ragbits.core.vector_stores import VectorStore
from ragbits.core.vector_stores.base import VectorStoreOptions
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import SourceResolver
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.ingestion.providers.base import BaseProvider
from ragbits.document_search.ingestion.strategies import (
    IngestStrategy,
    SequentialIngestStrategy,
)
from ragbits.document_search.ingestion.strategies.base import IngestExecutionResult
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

    vector_store: ObjectContructionConfig
    rephraser: ObjectContructionConfig = ObjectContructionConfig(type="NoopQueryRephraser")
    reranker: ObjectContructionConfig = ObjectContructionConfig(type="NoopReranker")
    ingest_strategy: ObjectContructionConfig = ObjectContructionConfig(type="SequentialIngestStrategy")
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

    vector_store: VectorStore
    query_rephraser: QueryRephraser
    reranker: Reranker
    document_processor_router: DocumentProcessorRouter
    ingest_strategy: IngestStrategy

    def __init__(
        self,
        vector_store: VectorStore,
        query_rephraser: QueryRephraser | None = None,
        reranker: Reranker | None = None,
        document_processor_router: DocumentProcessorRouter | None = None,
        ingest_strategy: IngestStrategy | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()
        self.document_processor_router = document_processor_router or DocumentProcessorRouter.from_config()
        self.ingest_strategy = ingest_strategy or SequentialIngestStrategy()

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
        ingest_strategy = IngestStrategy.subclass_from_config(model.ingest_strategy)

        providers_config = DocumentProcessorRouter.from_dict_to_providers_config(model.providers)
        document_processor_router = DocumentProcessorRouter.from_config(providers_config)

        return cls(vector_store, query_rephraser, reranker, document_processor_router, ingest_strategy)

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
            results = await self.vector_store.retrieve(
                text=rephrased_query,
                options=VectorStoreOptions(**config.vector_store_kwargs),
            )
            elements.append([Element.from_vector_db_entry(result.entry) for result in results])

        return await self.reranker.rerank(
            elements=elements,
            query=query,
            options=RerankerOptions(**config.reranker_kwargs),
        )

    @traceable
    async def ingest(
        self,
        documents: str | Iterable[DocumentMeta | Document | Source],
        document_processor: BaseProvider | None = None,
    ) -> IngestExecutionResult:
        """
        Ingest documents into the search index.

        Args:
            documents: Either:
                - A sequence of `Document`, `DocumentMetadata`, or `Source` objects
                - A source-specific URI string (e.g., "gcs://bucket/*") to specify source location(s), for example:
                    - "file:///path/to/files/*.txt"
                    - "gcs://bucket/folder/*"
                    - "huggingface://dataset/split/row"
            document_processor: The document processor to use. If not provided, the document processor will be
                determined based on the document metadata.

        Returns:
            The ingest execution result.
        """
        sources = await SourceResolver.resolve(documents) if isinstance(documents, str) else documents
        return await self.ingest_strategy(
            documents=sources,
            vector_store=self.vector_store,
            processor_router=self.document_processor_router,
            processor_overwrite=document_processor,
        )
