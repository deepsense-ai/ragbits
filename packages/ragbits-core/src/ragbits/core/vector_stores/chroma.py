from collections.abc import Iterable, Mapping, Sequence
from typing import Literal, cast

import chromadb
from chromadb.api import ClientAPI
from typing_extensions import Self

from ragbits.core.audit import traceable
from ragbits.core.embeddings.base import Embedder
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.core.utils.dict_transformations import flatten_dict, unflatten_dict
from ragbits.core.vector_stores.base import (
    VectorStoreEntry,
    VectorStoreNeedingEmbedder,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)


class ChromaVectorStoreOptions(VectorStoreOptions):
    """
    An object representing the options for the Chroma vector store.
    """

    # Whether to choose images over text when both are available
    prefer_image: bool = False


class ChromaVectorStore(VectorStoreNeedingEmbedder[ChromaVectorStoreOptions]):
    """
    Vector store implementation using [Chroma](https://docs.trychroma.com).
    """

    options_cls = ChromaVectorStoreOptions

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        embedder: Embedder,
        distance_method: Literal["l2", "ip", "cosine"] = "cosine",
        default_options: ChromaVectorStoreOptions | None = None,
        embedding_name_text: str = "text",
        embedding_name_image: str = "image",
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            embedder: The embedder to use for converting entries to vectors.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            embedding_name_text: The name under which the text embedding is stored in the resulting object.
            embedding_name_image: The name under which the image embedding is stored in the resulting object.
        """
        super().__init__(
            default_options=default_options,
            embedder=embedder,
            embedding_name_text=embedding_name_text,
            embedding_name_image=embedding_name_image,
        )
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        self._collection = self._client.get_or_create_collection(
            name=self._index_name,
            metadata={"hnsw:space": self._distance_method},
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
        client_options = ObjectContructionConfig.model_validate(config["client"])
        client_cls = import_by_path(client_options.type, chromadb)
        config["client"] = client_cls(**client_options.config)
        return super().from_config(config)

    async def _flatten_embeddings(self, embeddings: dict[str, dict[str, list[float]]]) -> dict[str, list[float]]:
        """
        Creates embeddings for the provided entries, similar to `_create_embeddings`,
        but only returns one embedding per entry. If both text and image embeddings are
        available, chooses text unless `prefer_image` is set to True.

        Args:
            embeddings: The embeddings to flatten.

        Returns:
            The embeddings.
        """
        default_embedding_key = (
            self._embedding_name_text if not self.default_options.prefer_image else self._embedding_name_image
        )
        fallback_embedding_key = (
            self._embedding_name_image if not self.default_options.prefer_image else self._embedding_name_text
        )
        return {
            key: entry.get(default_embedding_key, entry[fallback_embedding_key]) for key, entry in embeddings.items()
        }

    @traceable
    async def store(self, entries: Iterable[VectorStoreEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        In case entry contains both text and image embeddings,
        only one of them will get embedded - text by default, unless
        the option `prefer_image` is set to True.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return

        ids = []
        documents = []
        metadatas: list[Mapping] = []
        embeddings: list[Sequence[float]] = []

        raw_embeddings = await self._create_embeddings(entries)
        ids_to_embeddings = await self._flatten_embeddings(raw_embeddings)
        for entry in entries:
            if entry not in ids_to_embeddings:
                continue
            embeddings.append(ids_to_embeddings[entry.id])
            ids.append(entry.id)
            documents.append(entry.text or "")
            metadatas.append(
                self._flatten_metadata(
                    {**entry.metadata, **{"__embeddings": raw_embeddings[entry.id], "__image": entry.image_bytes}}
                )
            )

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    @traceable
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

        if image and text:
            raise ValueError("Either text or image should be provided, not both.")

        if text:
            vector = await self._embedder.embed_text([text])
        elif image:
            vector = await self._embedder.embed_image([image])
        else:
            raise ValueError("Either text or image should be provided.")

        results = self._collection.query(
            query_embeddings=cast(list[Sequence[float]], vector),
            n_results=merged_options.k,
            include=["metadatas", "embeddings", "distances", "documents"],
        )

        ids = [id for batch in results.get("ids", []) for id in batch]
        distances = [distance for batch in results.get("distances") or [] for distance in batch]
        documents = [document for batch in results.get("documents") or [] for document in batch]

        metadatas: Sequence = [dict(metadata) for batch in results.get("metadatas") or [] for metadata in batch]
        raw_embeddings: list[dict] = [cast(dict, metadata.pop("__embeddings", {})) for metadata in metadatas]
        images: list[bytes | None] = [metadata.pop("__image") for metadata in metadatas]

        # Remove the `# type: ignore` comment when https://github.com/deepsense-ai/ragbits/pull/379/files is resolved
        unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

        return [
            VectorStoreResult(
                score=distance,
                vectors=vectors,
                entry=VectorStoreEntry(
                    id=id,
                    text=document,
                    image_bytes=image,
                    metadata=metadata,
                ),
            )
            for id, metadata, distance, document, image, vectors in zip(
                ids, unflattened_metadatas, distances, documents, images, raw_embeddings, strict=True
            )
            if merged_options.max_distance is None or distance <= merged_options.max_distance
        ]

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        self._collection.delete(ids=ids)

    @traceable
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
        # Cast `where` to chromadb's Where type
        where_chroma: chromadb.Where | None = dict(where) if where else None

        results = self._collection.get(
            where=where_chroma,
            limit=limit,
            offset=offset,
            include=["metadatas", "embeddings", "documents"],
        )

        ids = results.get("ids") or []
        embeddings = results.get("embeddings") or []
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []

        return [
            VectorStoreEntry(
                id=id,
                key=document,
                vector=list(embedding),
                metadata=unflatten_dict(metadata) if metadata else {},  # type: ignore
            )
            for id, metadata, embedding, document in zip(ids, metadatas, embeddings, documents, strict=True)
        ]

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
