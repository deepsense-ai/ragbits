import asyncio
from collections.abc import Coroutine, Mapping, Sequence
from typing import Literal
from uuid import UUID

import chromadb
from chromadb.api import ClientAPI
from pyparsing import Any
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
        distance_method: Literal["l2", "ip", "cosine"] = "cosine",
        default_options: VectorStoreOptions | None = None,
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
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

    @staticmethod
    def _internal_id(entry_id: UUID, embedding_type: EmbeddingType) -> str:
        return f"{entry_id}-{embedding_type.value}"

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
                for embedding_type in EmbeddingType:
                    if not raw_embeddings[entry.id].get(embedding_type):
                        continue

                    embeddings.append(raw_embeddings[entry.id][embedding_type])
                    ids.append(self._internal_id(entry.id, embedding_type))
                    documents.append(entry.text or "")
                    metadatas.append(
                        self._flatten_metadata(
                            {
                                **entry.metadata,
                                **{
                                    "__id": str(entry.id),
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
        text: str | None = None,
        image: bytes | None = None,
        options: VectorStoreOptions | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            text: The text to query the vector store with.
            image: The image to query the vector store with.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        with trace(
            text=text,
            image=image,
            options=merged_options.dict(),
            index_name=self._index_name,
            collection=self._collection,
            distance_method=self._distance_method,
            embedder=repr(self._embedder),
        ) as outputs:
            vector_coroutines: list[Coroutine[Any, Any, list[list[float]]]] = []
            if text:
                vector_coroutines.append(self._embedder.embed_text([text]))
            if image:
                vector_coroutines.append(self._embedder.embed_image([image]))

            if not vector_coroutines:
                raise ValueError("Either text or image should be provided.")

            query_vectors: list[Sequence[float]] = [vectors[0] for vectors in await asyncio.gather(*vector_coroutines)]

            results = self._collection.query(
                query_embeddings=query_vectors,
                n_results=merged_options.k * 2,  # double the number of results to account for duplicates
                include=["metadatas", "embeddings", "distances", "documents"],
            )

            internal_ids = [id for batch in results.get("ids", []) for id in batch]
            distances = [distance for batch in results.get("distances") or [] for distance in batch]
            documents = [document for batch in results.get("documents") or [] for document in batch]
            embeddings = [embedding for batch in results.get("embeddings") or [] for embedding in batch]

            metadatas: Sequence = [dict(metadata) for batch in results.get("metadatas") or [] for metadata in batch]

            # Remove the `# type: ignore` comment when https://github.com/deepsense-ai/ragbits/pull/379/files resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]
            ids = [UUID(metadata.pop("__id", internal_ids[i])) for i, metadata in enumerate(unflattened_metadatas)]

            vs_results = [
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

            outputs.results = []
            seen_ids = set()
            for result in vs_results:
                if result.entry.id not in seen_ids:
                    seen_ids.add(result.entry.id)
                    outputs.results.append(result)

                if len(outputs.results) >= merged_options.k:
                    break

            return outputs.results

    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        with trace(ids=ids, collection=self._collection, index_name=self._index_name):
            self._collection.delete(
                ids=[self._internal_id(id, embedding_type) for id in ids for embedding_type in EmbeddingType]
            )

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
                include=["metadatas", "documents"],
            )

            internal_ids = results.get("ids") or []
            documents = results.get("documents") or []
            metadatas: Sequence = results.get("metadatas") or []

            # Remove the `# type: ignore` comment when https://github.com/deepsense-ai/ragbits/pull/379/files resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]
            ids = [UUID(metadata.pop("__id", internal_ids[i])) for i, metadata in enumerate(unflattened_metadatas)]

            vs_results = [
                VectorStoreEntry(
                    id=id,
                    text=document,
                    metadata=metadata,
                    image_bytes=image,
                )
                for id, metadata, document, image in zip(ids, unflattened_metadatas, documents, images, strict=True)
            ]

            outputs.results = list({r.id: r for r in vs_results}.values())

            return outputs.results

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
