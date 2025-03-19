from collections.abc import Mapping, Sequence
from typing import Literal
from uuid import UUID

import chromadb
from chromadb.api import ClientAPI, types
from typing_extensions import Self

from ragbits.core.audit import trace
from ragbits.core.embeddings.base import Embedder
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import (
    EmbeddingType,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    VectorStoreWithExternalEmbedder,
    WhereQuery,
)


class ChromaVectorStore(VectorStoreWithExternalEmbedder[VectorStoreOptions]):
    """
    Vector store implementation using [Chroma](https://docs.trychroma.com).
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        embedder: Embedder,
        embedding_type: EmbeddingType = EmbeddingType.TEXT,
        distance_method: Literal["l2", "ip", "cosine"] = "cosine",
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors.
            embedding_type: Which part of the entry to embed, either text or image. The other part will be ignored.
            distance_method: The distance method to use.
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
        self._collection = self._client.get_or_create_collection(
            name=self._index_name,
            metadata={"hnsw:space": self._distance_method},
        )

    def __reduce__(self) -> tuple:
        """
        Enables the ChromaVectorStore to be pickled and unpickled.
        """
        # TODO: To be implemented. Required for Ray processing.
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        client_options = ObjectContructionConfig.model_validate(config["client"])
        client_cls = import_by_path(client_options.type, chromadb)
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        In case entry contains both text and image embeddings,
        only one of them will get embedded - text by default, unless
        the option `prefer_image` is set to True.

        Args:
            entries: The entries to store.
        """
        with trace(
            entries=entries,
            index_name=self._index_name,
            collection=self._collection,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
        ):
            if not entries:
                return

            ids = []
            documents = []
            metadatas: list[Mapping] = []
            embeddings: list[Sequence[float]] = []

            raw_embeddings = await self._create_embeddings(entries)
            for entry in entries:
                if not raw_embeddings.get(entry.id):
                    continue

                embeddings.append(raw_embeddings[entry.id])
                ids.append(str(entry.id))
                documents.append(entry.text or "")
                metadatas.append(
                    self._flatten_metadata(
                        {
                            **entry.metadata,
                            **{
                                "__image": entry.image_bytes.hex() if entry.image_bytes else None,
                            },
                        }
                    )
                )

            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )

    async def retrieve(
        self,
        text: str,
        options: VectorStoreOptions | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            text=text,
            options=merged_options.dict(),
            index_name=self._index_name,
            collection=self._collection,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
        ) as outputs:
            query_vector = (await self._embedder.embed_text([text]))[0]

            results = self._collection.query(
                query_embeddings=query_vector,
                n_results=merged_options.k,
                include=[
                    types.IncludeEnum.metadatas,
                    types.IncludeEnum.embeddings,
                    types.IncludeEnum.distances,
                    types.IncludeEnum.documents,
                ],
            )

            ids = [id for batch in results.get("ids", []) for id in batch]
            distances = [distance for batch in results.get("distances") or [] for distance in batch]
            documents = [document for batch in results.get("documents") or [] for document in batch]
            embeddings = [embedding for batch in results.get("embeddings") or [] for embedding in batch]

            metadatas: Sequence = [dict(metadata) for batch in results.get("metadatas") or [] for metadata in batch]

            # Remove the `# type: ignore` comment when https://github.com/deepsense-ai/ragbits/pull/379/files resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]

            outputs.results = [
                VectorStoreResult(
                    score=distance,
                    vector=vector,
                    entry=VectorStoreEntry(
                        id=id,
                        text=document,
                        image_bytes=image,
                        metadata=metadata,
                    ),
                )
                for id, metadata, distance, document, image, vector in zip(
                    ids, unflattened_metadatas, distances, documents, images, embeddings, strict=True
                )
                if merged_options.max_distance is None or distance <= merged_options.max_distance
            ]

            return outputs.results

    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        with trace(ids=ids, collection=self._collection, index_name=self._index_name):
            self._collection.delete(ids=[str(id) for id in ids])

    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector store. The entries can be filtered, limited and offset.

        Args:
            where: The filter dictionary - the keys are the field names and the values are the values to filter by.
                Not specifying the key means no filtering.
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        with trace(
            where=where, collection=self._collection, index_name=self._index_name, limit=limit, offset=offset
        ) as outputs:
            # Cast `where` to chromadb's Where type
            where_chroma: chromadb.Where | None = dict(where) if where else None

            results = self._collection.get(
                where=where_chroma,
                limit=limit,
                offset=offset,
                include=[types.IncludeEnum.metadatas, types.IncludeEnum.documents],
            )

            ids = results.get("ids") or []
            documents = results.get("documents") or []
            metadatas: Sequence = results.get("metadatas") or []

            # Remove the `# type: ignore` comment when https://github.com/deepsense-ai/ragbits/pull/379/files resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]

            outputs.results = [
                VectorStoreEntry(
                    id=UUID(id),
                    text=document,
                    metadata=metadata,
                    image_bytes=image,
                )
                for id, metadata, document, image in zip(ids, unflattened_metadatas, documents, images, strict=True)
            ]

            return outputs.results

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
