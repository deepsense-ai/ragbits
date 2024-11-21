import json
from typing import Literal, Any, Dict, Union

import chromadb
from chromadb.api import ClientAPI

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores import get_metadata_store
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


class ChromaVectorStore(VectorStore):
    """
    Vector store implementation using [Chroma](https://docs.trychroma.com).
    """

    @staticmethod
    def _flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Union[str, int, float, bool]]:
        """
        Recursively flatten a nested dictionary, converting non-primitive types to strings.

        Args:
            d: The dictionary to flatten
            parent_key: The parent key for nested keys
            sep: The separator between nested keys

        Returns:
            A flattened dictionary with primitive types and stringified complex types
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(ChromaVectorStore._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, (str, int, float, bool)):
                items.append((new_key, v))
            else:
                # Convert other types to string
                items.append((new_key, str(v)))

        return dict(items)

    @staticmethod
    def _unflatten_dict(d: Dict[str, Any], sep: str = '.') -> Dict[str, Any]:
        """
        Convert a flattened dictionary back to a nested dictionary.

        Args:
            d: The flattened dictionary to unflatten
            sep: The separator used between nested keys

        Returns:
            An unflattened nested dictionary
        """
        result: Dict[str, Any] = {}
        
        for key, value in d.items():
            parts = key.split(sep)
            target = result
            
            # Navigate through the parts except the last one
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            
            # Set the value at the final level
            if isinstance(value, str):
                # Try to parse string values that might be JSON
                try:
                    target[parts[-1]] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    target[parts[-1]] = value
            else:
                target[parts[-1]] = value
        
        return result

    def __init__(
        self,
        client: ClientAPI,
        index_name: str,
        distance_method: Literal["l2", "ip", "cosine"] = "cosine",
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new ChromaVectorStore instance.

        Args:
            client: The ChromaDB client.
            index_name: The name of the index.
            distance_method: The distance method to use.
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use. If None, the metadata will be stored in ChromaDB.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
        self._client = client
        self._index_name = index_name
        self._distance_method = distance_method
        self._collection = self._client.get_or_create_collection(
            name=self._index_name,
            metadata={"hnsw:space": self._distance_method},
        )

    @classmethod
    def from_config(cls, config: dict) -> "ChromaVectorStore":
        """
        Creates and returns an instance of the ChromaVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the ChromaVectorStore instance.

        Returns:
            An initialized instance of the ChromaVectorStore class.
        """
        client_cls = get_cls_from_config(config["client"]["type"], chromadb)
        return cls(
            client=client_cls(**config["client"].get("config", {})),
            index_name=config["index_name"],
            distance_method=config.get("distance_method", "cosine"),
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=get_metadata_store(config.get("metadata_store")),
        )

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Stores entries in the ChromaDB collection.

        Args:
            entries: The entries to store.
        """
        if not entries:
            return

        ids = [entry.id for entry in entries]
        documents = [entry.key for entry in entries]
        embeddings = [entry.vector for entry in entries]
        metadatas = [entry.metadata for entry in entries]

        # Flatten metadata
        flattened_metadatas = [self._flatten_dict(metadata) for metadata in metadatas]

        metadatas = (
            flattened_metadatas
            if self._metadata_store is None
            else await self._metadata_store.store(ids, flattened_metadatas)  # type: ignore
        )

        self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)  # type: ignore

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreEntry]:
        """
        Retrieves entries from the ChromaDB collection.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The retrieved entries.

        Raises:
            MetadataNotFoundError: If the metadata is not found.
        """
        options = self._default_options if options is None else options

        results = self._collection.query(
            query_embeddings=vector,
            n_results=options.k,
            include=["metadatas", "embeddings", "distances", "documents"],
        )

        ids = results.get("ids") or []
        embeddings = results.get("embeddings") or []
        distances = results.get("distances") or []
        documents = results.get("documents") or []
        metadatas = [
            [metadata for batch in results.get("metadatas", []) for metadata in batch]  # type: ignore
            if self._metadata_store is None
            else await self._metadata_store.get(*ids)
        ]

        return [
            VectorStoreEntry(
                id=id,
                key=document,
                vector=list(embeddings),
                metadata=self._unflatten_dict(metadata) if metadata else {},  # type: ignore
            )
            for batch in zip(ids, metadatas, embeddings, distances, documents, strict=True)
            for id, metadata, embeddings, distance, document in zip(*batch, strict=True)
            if options.max_distance is None or distance <= options.max_distance
        ]

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
        metadatas = (
            [json.loads(metadata["__metadata"]) for metadata in results.get("metadatas", [])]  # type: ignore
            if self._metadata_store is None
            else await self._metadata_store.get(ids)
        )

        return [
            VectorStoreEntry(
                id=id,
                key=document,
                vector=list(embedding),
                metadata=self._unflatten_dict(metadata) if metadata else {},  # type: ignore
            )
            for id, metadata, embedding, document in zip(ids, metadatas, embeddings, documents, strict=True)
        ]
