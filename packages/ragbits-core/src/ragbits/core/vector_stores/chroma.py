from collections.abc import Mapping, Sequence
from typing import Literal, cast
from uuid import UUID

import chromadb
from chromadb.api import ClientAPI
from typing_extensions import Self

from ragbits.core.audit import trace
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


class ChromaVectorStore(VectorStoreNeedingEmbedder[VectorStoreOptions]):
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
        prefer_image_embedding: bool = False,
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
            prefer_image_embedding: Whether to prefer image embeddings over text embeddings when both are available.
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
        self._prefer_image_embedding = prefer_image_embedding

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

    async def _preferred_embeddings(self, embeddings: dict[UUID, dict[str, list[float]]]) -> dict[UUID, list[float]]:
        """
        Returns the preferred embedding type (text or image) for each entry. If the preferred type is not available,
        the other type is returned.
        """
        default_embedding_key = (
            self._embedding_name_text if not self._prefer_image_embedding else self._embedding_name_image
        )
        fallback_embedding_key = (
            self._embedding_name_image if not self._prefer_image_embedding else self._embedding_name_text
        )
        return {
            key: (entry.get(default_embedding_key) or entry[fallback_embedding_key])
            for key, entry in embeddings.items()
            if entry.get(default_embedding_key) or entry.get(fallback_embedding_key)
        }

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
            prefer_image=self._prefer_image_embedding,
            embedder=repr(self._embedder),
            embedder_for_text=self._embedding_name_text,
            embedder_for_image=self._embedding_name_image,
        ):
            if not entries:
                return

            ids = []
            documents = []
            metadatas: list[Mapping] = []
            embeddings: list[Sequence[float]] = []

            raw_embeddings = await self._create_embeddings(entries)
            ids_to_embeddings = await self._preferred_embeddings(raw_embeddings)
            for entry in entries:
                if entry.id not in ids_to_embeddings:
                    continue
                embeddings.append(ids_to_embeddings[entry.id])
                ids.append(str(entry.id))
                documents.append(entry.text or "")
                metadatas.append(
                    self._flatten_metadata(
                        {
                            **entry.metadata,
                            **{
                                "__embeddings": raw_embeddings[entry.id],
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
            embedder_for_text=self._embedding_name_text,
            embedder_for_image=self._embedding_name_image,
        ) as outputs:
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

            # Remove the `# type: ignore` when https://github.com/deepsense-ai/ragbits/pull/379/files is resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            embeddings: list[dict] = [
                cast(dict, metadata.pop("__embeddings", {})) for metadata in unflattened_metadatas
            ]
            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]

            outputs.retrieved_entries = [
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
                    ids, unflattened_metadatas, distances, documents, images, embeddings, strict=True
                )
                if merged_options.max_distance is None or distance <= merged_options.max_distance
            ]
            return outputs.retrieved_entries

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
        # Cast `where` to chromadb's Where type
        where_chroma: chromadb.Where | None = dict(where) if where else None
        with trace(
            where=where_chroma, collection=self._collection, index_name=self._index_name, limit=limit, offset=offset
        ) as outputs:
            results = self._collection.get(
                where=where_chroma,
                limit=limit,
                offset=offset,
                include=["metadatas", "documents"],
            )

            ids = results.get("ids") or []
            documents = results.get("documents") or []
            metadatas: Sequence = results.get("metadatas") or []

            # Remove the `# type: ignore` when https://github.com/deepsense-ai/ragbits/pull/379/files is resolved
            unflattened_metadatas: list[dict] = [unflatten_dict(metadata) if metadata else {} for metadata in metadatas]  # type: ignore[misc]

            images: list[bytes | None] = [metadata.pop("__image", None) for metadata in unflattened_metadatas]

            # remove embeddings from metadata
            for metadata in unflattened_metadatas:
                metadata.pop("__embeddings", None)

            outputs.listed_entries = [
                VectorStoreEntry(
                    id=UUID(id),
                    text=document,
                    metadata=metadata,
                    image_bytes=image,
                )
                for id, metadata, document, image in zip(ids, unflattened_metadatas, documents, images, strict=True)
            ]
            return outputs.listed_entries

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flattens the metadata dictionary. Removes any None values as they are not supported by ChromaDB."""
        return {k: v for k, v in flatten_dict(metadata).items() if v is not None}
