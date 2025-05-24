import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType, Reference
from ragbits.chat.persistence.sql import SQLHistoryPersistence


@pytest.fixture
async def sql_persistence() -> SQLHistoryPersistence:
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    persistence = SQLHistoryPersistence(engine)
    await persistence.init_db()
    return persistence


@pytest.mark.asyncio
async def test_save_and_retrieve_interaction(sql_persistence: SQLHistoryPersistence) -> None:
    """Test saving and retrieving a chat interaction."""
    # Create test data
    message = "Hello, how are you?"
    response = "I'm doing well, thank you!"
    extra_responses = [
        ChatResponse(
            type=ChatResponseType.REFERENCE,
            content=Reference(title="Test", content="Content", url="http://example.com"),
        ),
        ChatResponse(type=ChatResponseType.TEXT, content="Additional info"),
    ]
    context = ChatContext(conversation_id="test-conv-123", message_id="msg-456", state={"key": "value"})
    timestamp = 1234567890.0

    # Save interaction
    await sql_persistence.save_interaction(message, response, extra_responses, context, timestamp)

    # Retrieve interactions for the conversation
    interactions = await sql_persistence.get_conversation_interactions("test-conv-123")

    # Verify the interaction was saved correctly
    assert len(interactions) == 1
    interaction = interactions[0]

    assert interaction["message"] == message
    assert interaction["response"] == response
    assert interaction["message_id"] == "msg-456"
    assert interaction["timestamp"] == timestamp

    # Verify extra responses deserialization
    saved_extra_responses = interaction["extra_responses"]
    assert len(saved_extra_responses) == 2
    assert saved_extra_responses[0]["type"] == "reference"
    assert saved_extra_responses[1]["type"] == "text"

    # Verify context deserialization
    saved_context = interaction["context"]
    assert saved_context["conversation_id"] == "test-conv-123"
    assert saved_context["message_id"] == "msg-456"
    assert saved_context["state"] == {"key": "value"}


@pytest.mark.asyncio
async def test_multiple_interactions_same_conversation(sql_persistence: SQLHistoryPersistence) -> None:
    """Test saving multiple interactions in the same conversation."""
    context = ChatContext(conversation_id="conv-multi", message_id="msg-1")

    # Save first interaction
    await sql_persistence.save_interaction("First message", "First response", [], context, 1234567890.0)

    # Save second interaction
    context.message_id = "msg-2"
    await sql_persistence.save_interaction("Second message", "Second response", [], context, 1234567891.0)

    # Retrieve all interactions for the conversation
    interactions = await sql_persistence.get_conversation_interactions("conv-multi")

    # Verify both interactions were saved and ordered by timestamp
    assert len(interactions) == 2
    assert interactions[0]["message"] == "First message"
    assert interactions[0]["timestamp"] == 1234567890.0
    assert interactions[1]["message"] == "Second message"
    assert interactions[1]["timestamp"] == 1234567891.0


@pytest.mark.asyncio
async def test_get_recent_interactions(sql_persistence: SQLHistoryPersistence) -> None:
    """Test retrieving recent interactions across all conversations."""
    # Save interactions in different conversations
    for i in range(5):
        context = ChatContext(conversation_id=f"conv-{i}", message_id=f"msg-{i}")
        await sql_persistence.save_interaction(f"Message {i}", f"Response {i}", [], context, 1234567890.0 + i)

    # Get recent interactions
    recent = await sql_persistence.get_recent_interactions(limit=3)

    # Should return the 3 most recent (highest timestamp)
    assert len(recent) == 3
    assert recent[0]["message"] == "Message 4"  # Most recent
    assert recent[1]["message"] == "Message 3"
    assert recent[2]["message"] == "Message 2"


@pytest.mark.asyncio
async def test_interaction_without_conversation_id(sql_persistence: SQLHistoryPersistence) -> None:
    """Test saving an interaction without a conversation ID."""
    context = ChatContext(message_id="orphan-msg")

    await sql_persistence.save_interaction("Orphan message", "Orphan response", [], context, 1234567890.0)

    # Get recent interactions to verify it was saved
    recent = await sql_persistence.get_recent_interactions(limit=1)
    assert len(recent) == 1
    assert recent[0]["conversation_id"] is None
    assert recent[0]["message"] == "Orphan message"
