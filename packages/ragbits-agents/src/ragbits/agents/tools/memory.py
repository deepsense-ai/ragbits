"""
Long-term memory functionality for agents.

This module provides tools for agents to store and retrieve information
across conversations using vector stores and key-based organization.
"""

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ragbits.core.vector_stores.base import VectorStore, VectorStoreEntry, VectorStoreOptions, WhereQuery


class MemoryEntry(BaseModel):
    """Represents a memory entry with key-based organization."""

    key: str = Field(..., description="The key used to organize memories (user_id)")
    content: str = Field(..., description="The content to be remembered")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this memory was created")
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this memory")


class LongTermMemory:
    """
    Allows to store and retrieve long-term memories.
    Use create_memory_tools() to get a list of functions available for agents.

    Uses a vector store to enable semantic search of stored memories
    and organizes them by keys (e.g., user_id) for context-aware retrieval.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        max_retrieval_results: int = 5,
    ):
        """
        Args:
            vector_store: The vector store to use for storing and retrieving memories
            max_retrieval_results: Default maximum number of memories to retrieve per query
        """
        self.vector_store = vector_store
        self.max_retrieval_results = max_retrieval_results

    async def store_memory(self, user_id: str, content: str) -> str:
        """
        Args:
            user_id: The user ID to store the memory for
            content: The content to remember

        Returns:
            The memory ID of the stored memory
        """
        memory = MemoryEntry(key=user_id, content=content)

        # Create vector store entry and store it
        vector_entry = LongTermMemory._create_vector_entry(memory)
        await self.vector_store.store([vector_entry])

        return memory.memory_id

    async def retrieve_memories(self, user_id: str, query: str, limit: int | None = None) -> list[MemoryEntry]:
        """
        Retrieve memories using the provided user_id and semantic search.

        Args:
            user_id: The user ID to search memories for
            query: The query to search for relevant memories
            limit: Maximum number of memories to return (uses max_retrieval_results if None)

        Returns:
            List of relevant memories ordered by relevance
        """
        limit = limit or self.max_retrieval_results

        # Create vector store options with key filter
        options = VectorStoreOptions(
            k=limit,
            where={"key": user_id},  # Filter by user_id
        )

        # Search the vector store with key filter
        results = await self.vector_store.retrieve(query, options)

        # Convert to MemoryEntry
        memories = []
        for result in results:
            memory = MemoryEntry(
                key=result.entry.metadata["key"],
                content=result.entry.text or "",
                timestamp=datetime.fromisoformat(result.entry.metadata["timestamp"]),
                memory_id=result.entry.metadata["memory_id"],
            )
            memories.append(memory)

        return memories

    async def get_all_memories(self, user_id: str) -> list[MemoryEntry]:
        """
        Get all memories for the provided user_id from the vector store.

        Args:
            user_id: The user ID to get memories for

        Returns:
            List of all memories for the user_id
        """
        where_query: WhereQuery = {"key": user_id}
        entries = await self.vector_store.list(where=where_query)

        memories = []
        for entry in entries:
            memory = MemoryEntry(
                key=entry.metadata["key"],
                content=entry.text or "",
                timestamp=datetime.fromisoformat(entry.metadata["timestamp"]),
                memory_id=entry.metadata["memory_id"],
            )
            memories.append(memory)

        return memories

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """
        Delete a specific memory for the provided user_id.

        Args:
            user_id: The user ID the memory belongs to
            memory_id: The ID of the memory to delete

        Returns:
            True if memory was deleted, False if not found
        """
        # Check if it exists
        all_memories = await self.get_all_memories(user_id)
        memory_to_delete = None
        for memory in all_memories:
            if memory.memory_id == memory_id:
                memory_to_delete = memory
                break

        if memory_to_delete is None:
            return False

        memory_uuid = UUID(memory_to_delete.memory_id)
        await self.vector_store.remove([memory_uuid])
        return True

    @staticmethod
    def _create_vector_entry(memory: MemoryEntry) -> VectorStoreEntry:
        """Create a VectorStoreEntry from a MemoryEntry."""
        return VectorStoreEntry(
            id=UUID(memory.memory_id),
            text=memory.content,
            metadata={
                "key": memory.key,
                "timestamp": memory.timestamp.isoformat(),
                "memory_id": memory.memory_id,
                "element_type": "TextElement",
            },
        )


def create_memory_tools(memory_tool: LongTermMemory, user_id: str) -> list[Any]:
    """
    Create tool functions bound to a specific memory tool instance and user_id.

    Args:
        memory_tool: The memory tool instance to bind to
        user_id: The user ID to use for memory operations

    Returns:
        List of tool functions available for agent
    """

    async def store_memory(content: str) -> str:
        """
        Store a memory entry using the provided user_id.

        Args:
            content: The content to remember

        Returns:
            The memory ID of the stored memory
        """
        return await memory_tool.store_memory(user_id, content)

    async def retrieve_memories(query: str, limit: int | None = None) -> str:
        """
        Retrieve memories using the provided user_id and semantic search.

        Args:
            query: The query to search for relevant memories
            limit: Maximum number of memories to return

        Returns:
            Formatted string of retrieved memories
        """
        memories = await memory_tool.retrieve_memories(user_id, query, limit)

        if not memories:
            return f"No memories found for user '{user_id}' with given query"

        # Sort memories by timestamp (oldest to newest)
        sorted_memories = sorted(memories, key=lambda m: m.timestamp)

        result = f"Found {len(sorted_memories)} relevant memories for user '{user_id}':\n\n"
        for i, memory in enumerate(sorted_memories, 1):
            result += f"{i}. {memory.content}\n"
            result += f"   Created: {memory.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return result

    return [store_memory, retrieve_memories]
