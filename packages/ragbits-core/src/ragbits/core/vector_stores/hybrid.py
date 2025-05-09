import asyncio
from uuid import UUID

from ragbits.core.audit.traces import traceable
from ragbits.core.vector_stores.base import (
    VectorStore,
    VectorStoreEntry,
    VectorStoreOptions,
    VectorStoreResult,
    WhereQuery,
)
from ragbits.core.vector_stores.hybrid_strategies import HybridRetrivalStrategy, OrderedHybridRetrivalStrategy


class HybridSearchVectorStore(VectorStore):
    """
    A vector store that takes multiple vector store objects and proxies requests to them,
    returning the union of results.
    """

    options_cls = VectorStoreOptions

    def __init__(self, *vector_stores: VectorStore, retrieval_strategy: HybridRetrivalStrategy | None = None) -> None:
        """
        Constructs a new HybridSearchVectorStore instance.

        Args:
            vector_stores: The vector stores to proxy requests to.
            retrieval_strategy: The retrieval strategy to use when combining results,
                uses OrderedHybridRetrivalStrategy by default.
        """
        self.vector_stores = vector_stores
        self.retrieval_strategy = retrieval_strategy or OrderedHybridRetrivalStrategy()

    @traceable
    async def store(self, entries: list[VectorStoreEntry]) -> None:
        """
        Store entries in the vector stores.

        Sends entries to all vector stores to be stored, although individual vector stores are free to implement
        their own logic regarding which entries to store. For example, some vector stores may only store entries
        with specific type of content (images, text, etc.).

        Args:
            entries: The entries to store.
        """
        store_tasks = (vector_store.store(entries) for vector_store in self.vector_stores)
        await asyncio.gather(*store_tasks)

    @traceable
    async def retrieve(
        self,
        text: str,
        options: VectorStoreOptions | None = None,
    ) -> list[VectorStoreResult]:
        """
        Retrieve entries from the vector stores most similar to the provided text. The results are combined using
        the retrieval strategy provided in the constructor.

        Args:
            text: The text to query the vector store with.
            options: The options for querying the vector stores.

        Returns:
            The entries.
        """
        retrieve_tasks = (vector_store.retrieve(text, options) for vector_store in self.vector_stores)
        results = await asyncio.gather(*retrieve_tasks)

        return self.retrieval_strategy.join(results)

    @traceable
    async def remove(self, ids: list[UUID]) -> None:
        """
        Remove entries from all vector stores.

        Args:
            ids: The list of entries' IDs to remove.
        """
        remove_tasks = (vector_store.remove(ids) for vector_store in self.vector_stores)
        await asyncio.gather(*remove_tasks)

    @traceable
    async def list(
        self, where: WhereQuery | None = None, limit: int | None = None, offset: int = 0
    ) -> list[VectorStoreEntry]:
        """
        List entries from the vector stores. The entries can be filtered, limited and offset.
        Vector stores are queried in the order they were provided in the constructor.

        Args:
            where: The filter dictionary - the keys are the field names and the values are the values to filter by.
                Not specifying the key means no filtering.
            limit: The maximum number of entries to return.
            offset: The number of entries to skip.

        Returns:
            The entries.
        """
        retrieved_results: dict[UUID, VectorStoreEntry] = {}
        for vector_store in self.vector_stores:
            if limit is not None and (offset + limit - len(retrieved_results)) <= 0:
                break

            store_results = await vector_store.list(where)
            retrieved_results.update({entry.id: entry for entry in store_results})

        results = list(retrieved_results.values())
        results = results[offset:] if limit is None else results[offset : offset + limit]

        return results
