import warnings
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar, cast
from uuid import UUID

import weaviate
import weaviate.classes as wvc
from typing_extensions import Self
from weaviate import WeaviateAsyncClient
from weaviate.auth import AuthCredentials
from weaviate.classes.config import Configure, DataType, Property, Tokenization, VectorDistances
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.collections.classes.filters import FilterReturn
from weaviate.config import AdditionalConfig, Proxies
from weaviate.connect.base import ConnectionParams
from weaviate.embedded import EmbeddedOptions

from ragbits.core.audit.traces import trace
from ragbits.core.embeddings import Embedder
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    VectorStoreWithEmbedder,
    WhereQuery,
)


class WeaviateVectorStoreOptions(VectorStoreOptions):
    """
    An object representing the options for the Weaviate vector store.

    Attributes:
        k: The number of entries to return.
        score_threshold: The minimum similarity score for an entry to be returned.
            Note that this is based on score, which may be different from the raw
            similarity metric used by the vector store (see `VectorStoreResult`
            for more details).
        where: The filter dictionary - the keys are the field names and the values are the values to filter by.
            Not specifying the key means no filtering.
        use_keyword_search: If set to True in options passed to retrieve method then
            keyword search for text string is used instead of vector similarity search for text vector
            (Weaviate doesn't support sparse vector search, only vector similarity search and keyword search),
            keyword search in Weaviate is described here - https://weaviate.io/developers/weaviate/search/bm25.
    """

    use_keyword_search: bool = False


WeaviateVectorStoreOptionsT = TypeVar("WeaviateVectorStoreOptionsT", bound=WeaviateVectorStoreOptions)


# This file was named weaviate_vector.py instead of weaviate.py to avoid name conflicts with weaviate package
class WeaviateVectorStore(VectorStoreWithEmbedder[WeaviateVectorStoreOptions]):
    """
    Vector store implementation using [Weaviate](https://weaviate.io/).
    """

    TYPE_TO_PROPERTY_MAPPING = {int: DataType.INT, str: DataType.TEXT, float: DataType.NUMBER, bool: DataType.BOOL}
    options_cls = WeaviateVectorStoreOptions

    def __init__(
        self,
        client: WeaviateAsyncClient,
        index_name: str,
        embedder: Embedder,
        embedding_type: EmbeddingType = EmbeddingType.TEXT,
        distance_method: VectorDistances = VectorDistances.COSINE,
        default_options: WeaviateVectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new WeaviateVectorStore instance.

        Args:
            client: An instance of the Weaviate client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors. Can be a regular Embedder for dense vectors
                     or a SparseEmbedder for sparse vectors.
            embedding_type: Which part of the entry to embed, either text or image. The other part will be ignored.
            distance_method: The distance metric to use when creating the collection.
            default_options: The default options for querying the vector store.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_type=embedding_type,
        )
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        # Weaviate doesn't support filtering by nested keys and doesn't allow keys with dots,
        # so we use ___ as nested keys separator. It also doesn't allow keys with [],
        # so currently properties containing lists are not supported by ragbits.
        self._separator = "___"

    def __reduce__(self) -> tuple[Callable, tuple]:
        """
        Enables the WeaviateVectorStore to be pickled and unpickled.
        """

        def _reconstruct(
            connection_params: ConnectionParams | None,
            embedded_options: EmbeddedOptions | None,
            auth_client_secret: AuthCredentials | None,
            additional_headers: dict | None,
            additional_config: AdditionalConfig | None,
            skip_init_checks: bool,
            index_name: str,
            embedder: Embedder,
            distance_method: VectorDistances,
            default_options: WeaviateVectorStoreOptions,
        ) -> WeaviateVectorStore:
            return WeaviateVectorStore(
                client=WeaviateAsyncClient(
                    connection_params=connection_params,
                    embedded_options=embedded_options,
                    auth_client_secret=auth_client_secret,
                    additional_headers=additional_headers,
                    additional_config=additional_config,
                    skip_init_checks=skip_init_checks,
                ),
                index_name=index_name,
                embedder=embedder,
                distance_method=distance_method,
                default_options=default_options,
            )

        proxies = self._client._connection._proxies
        return (
            _reconstruct,
            (
                self._client._connection._connection_params,
                self._client._connection.embedded_db.options if self._client._connection.embedded_db else None,
                self._client._connection._auth,
                self._client._connection.additional_headers,
                AdditionalConfig(
                    connection=self._client._connection._ConnectionBase__connection_config,  # type: ignore
                    proxies=Proxies(
                        http=proxies.get("http", None), https=proxies.get("https", None), grpc=proxies.get("grpc", None)
                    ),
                    timeout=self._client._connection.timeout_config,
                    trust_env=self._client._connection._ConnectionBase__trust_env,  # type: ignore
                ),
                self._client._connection._skip_init_checks,
                self._index_name,
                self._embedder,
                self._distance_method,
                self.default_options,
            ),
        )

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        client_options = ObjectConstructionConfig.model_validate(config["client"])
        client_cls = import_by_path(client_options.type, weaviate)
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores vector entries in the Weaviate collection.

        Args:
            entries: List of VectorStoreEntry objects to store
        """
        async with self._client:
            with trace(
                entries=entries,
                index_name=self._index_name,
                distance_method=self._distance_method,
                embedder=repr(self._embedder),
                embedding_type=self._embedding_type,
            ):
                if not entries:
                    return

                embeddings: dict = await self._create_embeddings(entries)

                if not await self._client.collections.exists(self._index_name):
                    properties_with_types: dict[str, DataType] = {}
                    for entry in entries:
                        for k, v in self._flatten_metadata(
                            entry.model_dump(exclude={"id", "text"}, exclude_none=True, mode="json")
                        ).items():
                            value_type = WeaviateVectorStore.TYPE_TO_PROPERTY_MAPPING.get(type(v), None)
                            if not value_type:
                                warnings.warn(
                                    f"Unsupported type of metadata field with key {k}: {type(v)}, it will be ignored."
                                )
                                continue
                            if k in properties_with_types and value_type != properties_with_types[k]:
                                raise ValueError(
                                    f"Key {k} was already mapped to {properties_with_types[k]}"
                                    f", cannot be changed to {value_type}"
                                )
                            properties_with_types[k] = value_type

                    await self._client.collections.create(
                        name=self._index_name,
                        vectorizer_config=Configure.Vectorizer.none(),
                        vector_index_config=Configure.VectorIndex.hnsw(distance_metric=self._distance_method),
                        properties=[
                            Property(
                                name=k, data_type=v, tokenization=Tokenization.FIELD if v == DataType.TEXT else None
                            )
                            for k, v in properties_with_types.items()
                        ],
                    )

                index = self._client.collections.get(self._index_name)

                objects = []
                for entry in entries:
                    if entry.id in embeddings:
                        objects.append(
                            wvc.data.DataObject(
                                uuid=str(entry.id),
                                properties=self._flatten_metadata(
                                    entry.model_dump(exclude={"id"}, exclude_none=True, mode="json")
                                ),
                                vector=embeddings[entry.id],
                            )
                        )

                if objects:
                    await index.data.insert_many(objects)

    async def retrieve(self, text: str, options: WeaviateVectorStoreOptionsT | None = None) -> list[VectorStoreResult]:
        """
        Retrieves entries from the Weaviate collection based on vector similarity.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.
        """
        merged_options = (self.default_options | options) if options else self.default_options

        # Ragbits has a "larger is better" convention for all scores, so we need to reverse the score if the distance
        # method is "smaller is better".
        # Weaviate documentation says that all distance methods are "smaller is better":
        # https://weaviate.io/developers/weaviate/config-refs/distances#available-distance-metrics
        score_multiplier = -1
        score_threshold = merged_options.score_threshold
        async with self._client:
            with trace(
                text=text,
                options=merged_options,
                index_name=self._index_name,
                distance_method=self._distance_method,
                embedder=repr(self._embedder),
                embedding_type=self._embedding_type,
            ) as outputs:
                collection_exists = await self._client.collections.exists(self._index_name)

                if not collection_exists:
                    return []

                index = self._client.collections.get(self._index_name)

                filters = (
                    self._create_weaviate_filter(merged_options.where, self._separator)
                    if merged_options.where
                    else None
                )

                if merged_options.use_keyword_search:
                    results = await index.query.bm25(
                        query=text,
                        filters=filters,
                        limit=merged_options.k,
                        return_metadata=MetadataQuery(score=True),
                        include_vector=True,
                    )
                else:
                    query_vector = (await self._embedder.embed_text([text]))[0]
                    results = await index.query.near_vector(
                        near_vector=cast(Sequence[float], query_vector),
                        filters=filters,
                        limit=merged_options.k,
                        distance=score_threshold,  # max accepted distance
                        return_metadata=MetadataQuery(distance=True),
                        include_vector=True,
                    )

                outputs_results = []
                for object_ in results.objects:
                    entry_raw = {"uuid": object_.uuid, "properties": self._unflatten_metadata(object_.properties)}
                    entry_dict = {
                        "id": entry_raw["uuid"],
                        "text": cast(dict, entry_raw["properties"]).get("text", None),
                        "image_bytes": cast(dict, entry_raw["properties"]).get("image_bytes", None),
                        "metadata": cast(dict, entry_raw["properties"]).get("metadata", {}),
                    }
                    entry = VectorStoreEntry.model_validate(entry_dict)

                    if merged_options.use_keyword_search:
                        # For keyword search score follows "larger is better" rule,
                        # so we don't need to multiply it by score_multiplier
                        score = object_.metadata.score
                    else:
                        score = (
                            object_.metadata.distance * score_multiplier
                            if object_.metadata.distance is not None
                            else None
                        )

                    if score is not None:
                        outputs_results.append(
                            VectorStoreResult(
                                entry=entry,
                                score=score,
                                vector=cast(list[float], object_.vector["default"]),
                            )
                        )

                outputs.results = outputs_results

                return outputs.results

    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        async with self._client:
            with trace(ids=ids, index_name=self._index_name):
                collection_exists = await self._client.collections.exists(self._index_name)
                if collection_exists:
                    index = self._client.collections.get(self._index_name)
                    await index.data.delete_many(where=Filter.by_id().contains_any(ids))

    @staticmethod
    def _create_weaviate_filter(where: WhereQuery, separator: str) -> FilterReturn:
        """
        Creates the Filter from the given WhereQuery.

        Args:
        where: The WhereQuery to filter.
        separator: The separator to use for nested keys.

        Returns:
        The created filter.
        """
        where = flatten_dict(where)  # type: ignore

        filters = Filter.all_of(
            [
                Filter.by_property(f"metadata{separator}{key.replace('.', separator)}").equal(
                    cast(str | int | bool, value)
                )
                for key, value in where.items()
            ]
        )

        return filters

    async def list(
        self,
        where: WhereQuery | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: Conditions for filtering results.
                Reference: https://weaviate.io/developers/weaviate/search/filters
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.
        """
        async with self._client:
            with trace(where=where, index_name=self._index_name, limit=limit, offset=offset) as outputs:
                collection_exists = await self._client.collections.exists(self._index_name)

                if not collection_exists:
                    return []

                index = self._client.collections.get(self._index_name)

                limit = limit or (await index.aggregate.over_all(total_count=True)).total_count
                limit = max(1, limit) if limit is not None else None

                filters = self._create_weaviate_filter(where, self._separator) if where else None

                results = await index.query.fetch_objects(
                    limit=limit, offset=offset, filters=filters, include_vector=True
                )

                results_objects = [
                    {
                        "uuid": object_.uuid,
                        "properties": self._unflatten_metadata(object_.properties),
                    }
                    for object_ in results.objects
                ]

                objects = [
                    {
                        "id": object["uuid"],
                        "text": cast(dict, object["properties"]).get("text", None),
                        "image_bytes": cast(dict, object["properties"]).get("image_bytes", None),
                        "metadata": cast(dict, object["properties"]).get("metadata", {}),
                    }
                    for object in results_objects
                ]
                outputs.results = [VectorStoreEntry.model_validate(object) for object in objects]

                return outputs.results

    def _flatten_metadata(self, metadata: dict) -> dict:
        """Flattens the metadata dictionary."""
        return flatten_dict(metadata, sep=self._separator)

    def _unflatten_metadata(self, metadata: Mapping) -> dict:
        """Unflattens the metadata dictionary."""
        metadata_items_separator_replaced = {
            key.replace(self._separator, "."): value for key, value in metadata.items() if value is not None
        }
        return unflatten_dict(metadata_items_separator_replaced) if metadata_items_separator_replaced else {}
