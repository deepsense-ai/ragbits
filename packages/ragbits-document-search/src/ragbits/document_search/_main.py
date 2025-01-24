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


class DocumentSearchOptions(BaseModel):
    """
    Options for document search.
    """

    k: int = 5
    max_distance: float | None = None
    rerank: bool = False


class DocumentSearch(WithConstructionConfig):
    """
    A class for searching through documents.
    """

    default_module: ClassVar = document_search
    configuration_key: ClassVar = "document_search"

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embeddings,
        document_processor_router: DocumentProcessorRouter | None = None,
        processing_strategy: ProcessingExecutionStrategy | None = None,
        source_resolver: SourceResolver | None = None,
        default_options: DocumentSearchOptions | None = None,
    ) -> None:
        """
        Constructs a new DocumentSearch instance.

        Args:
            vector_store: The vector store to use.
            embedder: The embedder to use.
            document_processor_router: The document processor router to use.
            processing_strategy: The processing strategy to use.
            source_resolver: The source resolver to use.
            default_options: The default options for searching.
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.document_processor_router = document_processor_router or DocumentProcessorRouter()
        self.processing_strategy = processing_strategy or SequentialProcessing()
        self.source_resolver = source_resolver or SourceResolver()
        self.default_options = default_options or DocumentSearchOptions()

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Creates and returns an instance of the DocumentSearch class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the DocumentSearch instance.

        Returns:
            An initialized instance of the DocumentSearch class.

        Raises:
            ValidationError: The configuration doesn't follow the expected format.
            InvalidConfigError: The class can't be found or is not the correct type.
        """
        vector_store = VectorStore.subclass_from_config(ObjectContructionConfig.model_validate(config["vector_store"]))
        embedder = Embeddings.subclass_from_config(ObjectContructionConfig.model_validate(config["embedder"]))

        document_processor_router = None
        if "document_processor_router" in config:
            document_processor_router = DocumentProcessorRouter.from_config(config["document_processor_router"])

        processing_strategy = None
        if "processing_strategy" in config:
            processing_strategy = ProcessingExecutionStrategy.subclass_from_config(
                ObjectContructionConfig.model_validate(config["processing_strategy"])
            )

        source_resolver = None
        if "source_resolver" in config:
            source_resolver = SourceResolver.from_config(config["source_resolver"])

        default_options = None
        if "default_options" in config:
            default_options = DocumentSearchOptions(**config["default_options"])

        return cls(
            vector_store=vector_store,
            embedder=embedder,
            document_processor_router=document_processor_router,
            processing_strategy=processing_strategy,
            source_resolver=source_resolver,
            default_options=default_options,
        )

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        """
        Creates and returns an instance of the DocumentSearch class from the given YAML configuration file.

        Args:
            path: The path to the YAML configuration file.

        Returns:
            An initialized instance of the DocumentSearch class.

        Raises:
            ValidationError: The configuration doesn't follow the expected format.
            InvalidConfigError: The class can't be found or is not the correct type.
        """
        config = get_config_from_yaml(path)
        if not config:
            raise NoDefaultConfigError("No configuration found in YAML file")
        return cls.from_config(config)

    @traceable
    async def search(self, query: str, options: DocumentSearchOptions | None = None) -> list[Element]:
        """
        Search for elements matching the query.

        Args:
            query: The query to search for.
            options: The options for searching.

        Returns:
            The matching elements.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        vector = (await self.embedder.embed_text([query]))[0]
        vector_store_options = VectorStoreOptions(k=merged_options.k, max_distance=merged_options.max_distance)
        results = await self.vector_store.retrieve(vector=vector, options=vector_store_options)
        return [Element.from_vector_db_entry(result.entry) for result in results]

    @traceable
    async def ingest(
        self,
        documents: Sequence[Document | Source],
        document_processor: BaseProvider | None = None,
    ) -> None:
        """
        Ingest documents into the vector store.

        Args:
            documents: The documents to ingest.
            document_processor: The document processor to use.
        """
        if not documents:
            return

        sources = []
        for document in documents:
            if isinstance(document, Document):
                sources.append(await document.to_source())
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
