from itertools import islice

import numpy as np

from ragbits.core.audit import traceable
from ragbits.core.metadata_stores.base import MetadataStore
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, VectorStoreResult, WhereQuery


class InMemoryVectorStore(VectorStore[VectorStoreOptions]):
    """
    A simple in-memory implementation of VectorStore.
    """

    options_cls = VectorStoreOptions

    def __init__(
        self,
        default_options: VectorStoreOptions | None = None,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        """
        Constructs a new InMemoryVectorStore instance.

        Args:
            default_options: The default options for querying the vector store.
            metadata_store: The metadata store to use.
        """
        super().__init__(default_options=default_options, metadata_store=metadata_store)
        self._storage: dict[str, tuple[VectorStoreEntry, dict[str, list[float]]]] = {}

    @classmethod
    def from_config(cls, config: dict) -> "InMemoryVectorStore":
        """
        Creates and returns an instance of the InMemoryVectorStore class from the given configuration.

        Args:
            config: A dictionary containing the configuration for initializing the InMemoryVectorStore instance.

        Returns:
            An initialized instance of the InMemoryVectorStore class.

        Raises:
            ValidationError: The metadata_store configuration doesn't follow the expected format.
            InvalidConfigError: The metadata_store class can't be found or is not the correct type.
        """
        store = (
            MetadataStore.subclass_from_config(ObjectContructionConfig.model_validate(config["metadata_store"]))
            if "metadata_store" in config
            else None
        )
        return cls(
            default_options=VectorStoreOptions(**config.get("default_options", {})),
            metadata_store=store,
        )

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector store.

        Args:
            entries: The entries to store.
        """
        for entry in entries:
            if "embedding_type" not in entry.metadata:
                raise ValueError("Entry must have embedding_type in metadata")
            if entry.id not in self._storage:
                self._storage[entry.id] = (entry, {})
            self._storage[entry.id][1][entry.metadata["embedding_type"]] = entry.metadata.pop("vector")

    @traceable
    async def retrieve(self, vector: list[float], options: VectorStoreOptions | None = None) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector store.

        Args:
            vector: The vector to query.
            options: The options for querying the vector store.

        Returns:
            The entries with their scores.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        entries = sorted(
            (
                (entry, vectors, float(np.linalg.norm(np.array(list(vectors.values())[0]) - np.array(vector))))
                for entry, vectors in self._storage.values()
            ),
            key=lambda x: x[2],
        )
        return [
            VectorStoreResult(entry=entry, vectors=vectors, score=distance)
            for entry, vectors, distance in entries[: merged_options.k]
            if merged_options.max_distance is None or distance <= merged_options.max_distance
        ]

    @traceable
    async def remove(self, ids: list[str]) -> None:
        """
        Remove entries from the vector store.

        Args:
            ids: The list of entries' IDs to remove.
        """
        for id in ids:
            del self._storage[id]

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
        """
        entries = iter(entry for entry, _ in self._storage.values())

        if where:
            entries = (
                entry for entry in entries if all(entry.metadata.get(key) == value for key, value in where.items())
            )

        if offset:
            entries = islice(entries, offset, None)

        if limit:
            entries = islice(entries, limit)

        return list(entries)
