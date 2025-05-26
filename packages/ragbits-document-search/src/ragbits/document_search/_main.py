from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Generic

from pydantic import BaseModel
from typing_extensions import Self

from ragbits import document_search
from ragbits.core.audit.traces import trace, traceable
from ragbits.core.config import CoreConfig
from ragbits.core.options import Options
from ragbits.core.sources.base import Source, SourceResolver
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils._pyproject import get_config_from_yaml
from ragbits.core.utils.config_handling import ConfigurableComponent, NoPreferredConfigError, ObjectConstructionConfig
from ragbits.core.vector_stores.base import VectorStore, VectorStoreOptionsT
from ragbits.document_search.documents.document import Document, DocumentMeta
from ragbits.document_search.documents.element import Element
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter
from ragbits.document_search.ingestion.parsers.router import DocumentParserRouter
from ragbits.document_search.ingestion.strategies.base import (
    IngestExecutionError,
    IngestExecutionResult,
    IngestStrategy,
)
from ragbits.document_search.ingestion.strategies.sequential import SequentialIngestStrategy
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser, QueryRephraserOptionsT
from ragbits.document_search.retrieval.rephrasers.noop import NoopQueryRephraser
from ragbits.document_search.retrieval.rerankers.base import Reranker, RerankerOptionsT
from ragbits.document_search.retrieval.rerankers.noop import NoopReranker


class DocumentSearchOptions(Options, Generic[QueryRephraserOptionsT, VectorStoreOptionsT, RerankerOptionsT]):
    """
    Object representing the options for the document search.

    Attributes:
        query_rephraser_options: The options for the query rephraser.
        vector_store_options: The options for the vector store.
        reranker_options: The options for the reranker.
    """

    query_rephraser_options: QueryRephraserOptionsT | None | NotGiven = NOT_GIVEN
    vector_store_options: VectorStoreOptionsT | None | NotGiven = NOT_GIVEN
    reranker_options: RerankerOptionsT | None | NotGiven = NOT_GIVEN


class DocumentSearchConfig(BaseModel):
    """
    Schema for the document search config.
    """

    vector_store: ObjectConstructionConfig
    rephraser: ObjectConstructionConfig = ObjectConstructionConfig(type="NoopQueryRephraser")
    reranker: ObjectConstructionConfig = ObjectConstructionConfig(type="NoopReranker")
    ingest_strategy: ObjectConstructionConfig = ObjectConstructionConfig(type="SequentialIngestStrategy")
    parser_router: dict[str, ObjectConstructionConfig] = {}
    enricher_router: dict[str, ObjectConstructionConfig] = {}


class DocumentSearch(
    ConfigurableComponent[DocumentSearchOptions[QueryRephraserOptionsT, VectorStoreOptionsT, RerankerOptionsT]]
):
    """
    Main entrypoint to the document search functionality. It provides methods for document retrieval and ingestion.

    Retrieval:
        1. Uses QueryRephraser to rephrase the query.
        2. Uses VectorStore to retrieve the most relevant elements.
        3. Uses Reranker to rerank the elements.

    Ingestion:
        1. Uses IngestStrategy to orchestrate ingestion process.
        2. Uses DocumentParserRouter to route the document to the appropriate DocumentParser to parse the content.
        3. Uses ElementEnricherRouter to redirect the element to the appropriate ElementEnricher to enrich the element.
    """

    options_cls: type[DocumentSearchOptions] = DocumentSearchOptions
    default_module: ClassVar[ModuleType | None] = document_search
    configuration_key: ClassVar[str] = "document_search"

    def __init__(
        self,
        vector_store: VectorStore[VectorStoreOptionsT],
        *,
        query_rephraser: QueryRephraser[QueryRephraserOptionsT] | None = None,
        reranker: Reranker[RerankerOptionsT] | None = None,
        default_options: DocumentSearchOptions[
            QueryRephraserOptionsT,
            VectorStoreOptionsT,
            RerankerOptionsT,
        ]
        | None = None,
        ingest_strategy: IngestStrategy | None = None,
        parser_router: DocumentParserRouter | None = None,
        enricher_router: ElementEnricherRouter | None = None,
    ) -> None:
        """
        Initialize the DocumentSearch instance.

        Args:
            vector_store: The vector store to use for retrieval.
            query_rephraser: The query rephraser to use for retrieval.
            reranker: The reranker to use for retrieval.
            default_options: The default options for the search.
            ingest_strategy: The ingestion strategy to use for ingestion.
            parser_router: The document parser router to use for ingestion.
            enricher_router: The element enricher router to use for ingestion.
        """
        super().__init__(default_options=default_options)
        self.vector_store = vector_store
        self.query_rephraser = query_rephraser or NoopQueryRephraser()
        self.reranker = reranker or NoopReranker()
        self.ingest_strategy = ingest_strategy or SequentialIngestStrategy()
        self.parser_router = parser_router or DocumentParserRouter()
        self.enricher_router = enricher_router or ElementEnricherRouter()

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

        query_rephraser: QueryRephraser = QueryRephraser.subclass_from_config(model.rephraser)
        vector_store: VectorStore = VectorStore.subclass_from_config(model.vector_store)
        reranker: Reranker = Reranker.subclass_from_config(model.reranker)

        ingest_strategy = IngestStrategy.subclass_from_config(model.ingest_strategy)
        parser_router = DocumentParserRouter.from_config(model.parser_router)
        enricher_router = ElementEnricherRouter.from_config(model.enricher_router)

        return cls(
            vector_store=vector_store,
            query_rephraser=query_rephraser,
            reranker=reranker,
            ingest_strategy=ingest_strategy,
            parser_router=parser_router,
            enricher_router=enricher_router,
        )

    @classmethod
    def preferred_subclass(
        cls,
        config: CoreConfig,
        factory_path_override: str | None = None,
        yaml_path_override: Path | None = None,
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
            preferences = get_config_from_yaml(yaml_path_override)

            # Look for explicit document search configuration
            if type_config := preferences.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectConstructionConfig.model_validate(type_config))

            # Instantiate the class with the preferred configuration for each component
            return cls.from_config(preferences)

        if factory_path_override:
            return cls.subclass_from_factory(factory_path_override)

        if preferred_factory := config.component_preference_factories.get(cls.configuration_key):
            return cls.subclass_from_factory(preferred_factory)

        if config.component_preference_config_path is not None:
            # Look for explicit document search configuration
            if preferred_config := config.preferred_instances_config.get(cls.configuration_key):
                return cls.subclass_from_config(ObjectConstructionConfig.model_validate(preferred_config))

            # Instantiate the class with the preferred configuration for each component
            return cls.from_config(config.preferred_instances_config)

        raise NoPreferredConfigError(f"Could not find preferred factory or configuration for {cls.configuration_key}")

    async def search(
        self,
        query: str,
        options: DocumentSearchOptions[QueryRephraserOptionsT, VectorStoreOptionsT, RerankerOptionsT] | None = None,
    ) -> Sequence[Element]:
        """
        Search for the most relevant chunks for a query.

        Args:
            query: The query to search for.
            options: The document search retrieval options.

        Returns:
            A list of chunks.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        query_rephraser_options = merged_options.query_rephraser_options or None
        vector_store_options = merged_options.vector_store_options or None
        reranker_options = merged_options.reranker_options or None

        with trace(query=query, options=merged_options) as outputs:
            queries = await self.query_rephraser.rephrase(query, query_rephraser_options)
            elements = [
                [
                    Element.from_vector_db_entry(result.entry, result.score)
                    for result in await self.vector_store.retrieve(query, vector_store_options)
                ]
                for query in queries
            ]
            outputs.results = await self.reranker.rerank(
                elements=elements,
                query=query,
                options=reranker_options,
            )

        return outputs.results

    @traceable
    async def ingest(
        self,
        documents: str | Iterable[DocumentMeta | Document | Source],
        fail_on_error: bool = True,
    ) -> IngestExecutionResult:
        """
        Ingest documents into the search index.

        Args:
            documents: A string representing a source-specific URI (e.g., "gcs://bucket/*") or an iterable of
                       `Document`, `DocumentMeta`, or `Source` objects. Examples of URI formats include:
                       - "file:///path/to/files/*.txt"
                       - "gcs://bucket/folder/*"
                       - "huggingface://dataset/split/row"
            fail_on_error: If True, raises IngestExecutionError when any errors are encountered during ingestion.
                           If False, returns all errors encountered in the IngestExecutionResult.

        Returns:
            An IngestExecutionResult containing the results of the ingestion process.

        Raises:
            IngestExecutionError: If fail_on_error is True and any errors are encountered during ingestion.
        """
        resolved_documents = await SourceResolver.resolve(documents) if isinstance(documents, str) else documents
        results = await self.ingest_strategy(
            documents=resolved_documents,
            vector_store=self.vector_store,
            parser_router=self.parser_router,
            enricher_router=self.enricher_router,
        )

        if fail_on_error and results.failed:
            raise IngestExecutionError(results.failed)

        return results
