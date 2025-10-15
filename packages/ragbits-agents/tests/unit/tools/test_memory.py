from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from ragbits.agents.tools.memory import LongTermMemory, MemoryEntry, create_memory_tools
from ragbits.core.embeddings.base import VectorSize
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Fixture for mocking the embedder."""
    mock = MagicMock()
    mock.embed_text = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
    mock.get_vector_size = AsyncMock(return_value=VectorSize(size=5, is_sparse=False))
    return mock


@pytest.fixture
def vector_store(mock_embedder: MagicMock) -> InMemoryVectorStore:
    """Fixture for creating a real InMemoryVectorStore with mocked embedder."""
    return InMemoryVectorStore(embedder=mock_embedder)


@pytest.fixture
def memory_tool(vector_store: InMemoryVectorStore) -> LongTermMemory:
    """Fixture for creating a LongTermMemory instance."""
    return LongTermMemory(vector_store=vector_store)


class TestMemoryEntry:
    """Test cases for MemoryEntry model."""

    @staticmethod
    def test_memory_entry_creation() -> None:
        """Test that MemoryEntry can be created with required fields and auto-generates timestamp and ID."""
        memory = MemoryEntry(
            key="user_123",
            content="Test content",
        )

        assert memory.key == "user_123"
        assert memory.content == "Test content"
        assert isinstance(memory.timestamp, datetime)
        assert isinstance(memory.memory_id, str)
        assert len(memory.memory_id) > 0


class TestLongTermMemory:
    """Test cases for LongTermMemory class."""

    @staticmethod
    async def test_store_memory(memory_tool: LongTermMemory) -> None:
        """Test that store_memory returns a memory ID."""
        memory_id = await memory_tool.store_memory("user_123", "User loves hiking")

        assert isinstance(memory_id, str)
        assert len(memory_id) > 0

    @staticmethod
    async def test_store_and_retrieve_memory(memory_tool: LongTermMemory) -> None:
        """Test storing and retrieving a memory."""
        memory_id = await memory_tool.store_memory("user_123", "User loves hiking in the mountains")
        memories = await memory_tool.retrieve_memories("user_123", "hobbies", 1)

        assert len(memories) == 1
        assert memories[0].content == "User loves hiking in the mountains"
        assert memories[0].key == "user_123"
        assert memories[0].memory_id == memory_id

    @staticmethod
    async def test_retrieve_memories_empty(memory_tool: LongTermMemory) -> None:
        """Test retrieve_memories when no memories are found."""
        memories = await memory_tool.retrieve_memories("user_123", "hiking")

        assert memories == []

    @staticmethod
    async def test_get_all_memories(memory_tool: LongTermMemory) -> None:
        """Test get_all_memories returns all memories for a user."""
        await memory_tool.store_memory("user_123", "User loves hiking")
        await memory_tool.store_memory("user_123", "User loves cooking")
        await memory_tool.store_memory("user_456", "User loves reading")

        memories = await memory_tool.get_all_memories("user_123")

        assert len(memories) == 2
        assert all(memory.key == "user_123" for memory in memories)

    @staticmethod
    async def test_delete_memory(memory_tool: LongTermMemory) -> None:
        """Test delete_memory removes the correct memory."""
        memory_id = await memory_tool.store_memory("user_123", "User loves hiking")

        # Verify it exists
        memories = await memory_tool.get_all_memories("user_123")
        assert len(memories) == 1

        # Delete it
        success = await memory_tool.delete_memory("user_123", memory_id)
        assert success is True

        # Verify it's gone
        memories = await memory_tool.get_all_memories("user_123")
        assert len(memories) == 0

    @staticmethod
    async def test_delete_memory_not_found(memory_tool: LongTermMemory) -> None:
        """Test delete_memory when memory doesn't exist."""
        success = await memory_tool.delete_memory("user_123", "non-existent-id")

        assert success is False


class TestCreateMemoryTools:
    """Test cases for create_memory_tools function."""

    @staticmethod
    async def test_create_memory_tools_returns_functions(memory_tool: LongTermMemory) -> None:
        """Test that create_memory_tools returns a list of callable functions."""
        tools = create_memory_tools(memory_tool, "user_123")

        assert len(tools) == 2
        assert callable(tools[0])  # store_memory
        assert callable(tools[1])  # retrieve_memories

    @staticmethod
    async def test_store_memory_tool(memory_tool: LongTermMemory) -> None:
        """Test that the store_memory tool function works correctly."""
        tools = create_memory_tools(memory_tool, "user_123")
        store_memory = tools[0]

        memory_id = await store_memory("User loves cooking")

        assert isinstance(memory_id, str)

    @staticmethod
    async def test_retrieve_memories_tool_no_memories(memory_tool: LongTermMemory) -> None:
        """Test retrieve_memories tool when no memories are found."""
        tools = create_memory_tools(memory_tool, "user_123")
        retrieve_memories = tools[1]

        result = await retrieve_memories("cooking")

        assert result == "No memories found for user 'user_123' with given query"

    @staticmethod
    async def test_retrieve_memories_tool_with_memories(memory_tool: LongTermMemory) -> None:
        """Test retrieve_memories tool when memories are found."""
        tools = create_memory_tools(memory_tool, "user_123")
        store_memory = tools[0]
        retrieve_memories = tools[1]

        await store_memory("User loves preparing Italian food")
        result = await retrieve_memories("cooking")

        assert "Found 1 relevant memories for user 'user_123':" in result
        assert "User loves preparing Italian food" in result
