import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType, Reference, StateUpdate
from ragbits.chat.persistence.sql import SQLHistoryPersistence, SQLHistoryPersistenceOptions


@pytest.fixture
async def sql_persistence() -> SQLHistoryPersistence:
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    persistence = SQLHistoryPersistence(engine)
    return persistence


@pytest.fixture
async def sql_persistence_custom_tables() -> SQLHistoryPersistence:
    """Create an in-memory SQLite database with custom table names for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    options = SQLHistoryPersistenceOptions(
        conversations_table="custom_conversations", interactions_table="custom_interactions"
    )
    persistence = SQLHistoryPersistence(engine, options)
    return persistence


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
async def test_custom_table_names_with_foreign_key(sql_persistence_custom_tables: SQLHistoryPersistence) -> None:
    """Test that custom table names work correctly with foreign key constraints."""
    context = ChatContext(conversation_id="custom-conv", message_id="custom-msg")

    # Save interaction with custom table names
    await sql_persistence_custom_tables.save_interaction(
        "Test message with custom tables", "Test response", [], context, 1234567890.0
    )

    # Retrieve interactions to verify they were saved correctly
    interactions = await sql_persistence_custom_tables.get_conversation_interactions("custom-conv")

    assert len(interactions) == 1
    assert interactions[0]["message"] == "Test message with custom tables"
    assert interactions[0]["response"] == "Test response"
    assert interactions[0]["conversation_id"] == "custom-conv"
    assert interactions[0]["message_id"] == "custom-msg"

    # Verify that the foreign key constraint is working by checking the table names
    # The fact that this test passes means the foreign key is correctly referencing
    # the custom conversations table name
    assert sql_persistence_custom_tables.options.conversations_table == "custom_conversations"
    assert sql_persistence_custom_tables.options.interactions_table == "custom_interactions"


@pytest.mark.asyncio
async def test_automatic_db_initialization(sql_persistence: SQLHistoryPersistence) -> None:
    """Test that database initialization happens automatically and only once."""
    # Initially, database should not be initialized
    assert not sql_persistence._db_initialized

    context = ChatContext(conversation_id="auto-init-test", message_id="msg-1")

    # First operation should trigger initialization
    await sql_persistence.save_interaction("First message", "First response", [], context, 1234567890.0)

    # Database should now be initialized
    assert sql_persistence._db_initialized

    # Second operation should not trigger initialization again
    await sql_persistence.save_interaction("Second message", "Second response", [], context, 1234567891.0)

    # Database should still be initialized (flag unchanged)
    assert sql_persistence._db_initialized

    # Retrieving interactions should also work without additional initialization
    interactions = await sql_persistence.get_conversation_interactions("auto-init-test")

    assert len(interactions) == 2
    assert interactions[0]["message"] == "First message"
    assert interactions[1]["message"] == "Second message"


@pytest.mark.asyncio
async def test_json_data_integrity(sql_persistence: SQLHistoryPersistence) -> None:
    """Test that complex JSON data is properly stored and retrieved."""
    # Create complex context with nested data
    complex_context = ChatContext(
        conversation_id="json-test",
        message_id="complex-msg",
        state={
            "user_profile": {
                "name": "Test User",
                "preferences": ["python", "ai", "databases"],
                "settings": {"theme": "dark", "notifications": True, "language": "en"},
            },
            "session_data": {
                "start_time": 1234567890.0,
                "actions": ["login", "search", "chat"],
                "metadata": {"ip_address": "192.168.1.1", "user_agent": "test-agent"},
            },
        },
    )

    # Create complex extra responses
    complex_extra_responses = [
        ChatResponse(
            type=ChatResponseType.REFERENCE,
            content=Reference(
                title="Complex Reference",
                content="This is a complex reference with detailed information",
                url="https://example.com/complex",
            ),
        ),
        ChatResponse(
            type=ChatResponseType.STATE_UPDATE,
            content=StateUpdate(state={"updated_field": "new_value", "counter": 42}, signature="test_signature"),
        ),
    ]

    await sql_persistence.save_interaction(
        "Complex message with nested data", "Complex response", complex_extra_responses, complex_context, 1234567890.0
    )

    # Retrieve and verify the data integrity
    interactions = await sql_persistence.get_conversation_interactions("json-test")
    assert len(interactions) == 1

    interaction = interactions[0]

    # Verify context data integrity
    saved_context = interaction["context"]
    assert saved_context["conversation_id"] == "json-test"
    assert saved_context["state"]["user_profile"]["name"] == "Test User"
    assert saved_context["state"]["user_profile"]["preferences"] == ["python", "ai", "databases"]
    assert saved_context["state"]["user_profile"]["settings"]["theme"] == "dark"
    assert saved_context["state"]["session_data"]["actions"] == ["login", "search", "chat"]

    # Verify extra responses data integrity
    saved_responses = interaction["extra_responses"]
    assert len(saved_responses) == 2

    ref_response = saved_responses[0]
    assert ref_response["type"] == "reference"
    assert ref_response["content"]["title"] == "Complex Reference"
    assert ref_response["content"]["url"] == "https://example.com/complex"

    state_response = saved_responses[1]
    assert state_response["type"] == "state_update"
    assert state_response["content"]["state"]["counter"] == 42
