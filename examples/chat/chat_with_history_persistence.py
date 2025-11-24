"""
Ragbits Chat Example: Chat Interface with SQL History Persistence

This example demonstrates how to use the `ChatInterface` with `SQLHistoryPersistence`
to persist chat interactions to a SQL database. It showcases:

- Setting up SQLHistoryPersistence with SQLite (aiosqlite)
- Saving chat interactions automatically through the ChatInterface
- Retrieving conversation history from the database
- Resuming conversations using persisted history

To run the script, execute the following command:

    ```bash
    uv run python examples/chat/chat_with_history_persistence.py
    ```

Requirements:
    - aiosqlite (for async SQLite support)
    - ragbits-chat
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
#     "aiosqlite>=0.21.0",
#     "greenlet>=3.0.0",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig
from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType
from ragbits.chat.persistence.sql import SQLHistoryPersistence, SQLHistoryPersistenceOptions
from ragbits.core.prompt import ChatFormat


async def mock_llm_response(message: str) -> str:
    """
    Mock LLM response for demonstration purposes (avoids needing API keys).

    In a real application, replace this with actual LLM calls.
    """
    responses = {
        "What is the capital of France?": (
            "The capital of France is Paris. Paris is known for its iconic landmarks like the Eiffel "
            "Tower, the Louvre Museum, and Notre-Dame Cathedral."
        ),
        "What about Germany?": (
            "The capital of Germany is Berlin. Berlin is a vibrant city known for its history, "
            "culture, and nightlife. It was divided during the Cold War but is now reunited."
        ),
        "And what about Italy?": (
            "The capital of Italy is Rome. Rome is an ancient city with a rich history spanning over "
            "2,500 years. It's home to the Colosseum, Vatican City, and the Trevi Fountain."
        ),
        "Tell me a fact about number 1": (
            "The number 1 is the first and smallest positive integer. It is the multiplicative "
            "identity, meaning any number multiplied by 1 equals itself."
        ),
        "Tell me a fact about number 2": (
            "The number 2 is the smallest and only even prime number. It is also the base of the "
            "binary numeral system used in computing."
        ),
    }
    return responses.get(message, f"This is a mock response to: {message}")


class SimpleChatWithPersistence(ChatInterface):
    """
    A simple chat interface that demonstrates SQL history persistence.

    This interface automatically saves all chat interactions to a SQLite database,
    including messages, responses, and metadata like conversation IDs.
    """

    feedback_config = FeedbackConfig(
        like_enabled=True,
        dislike_enabled=True,
    )

    # Enable conversation history to show previous messages
    conversation_history = True
    show_usage = True

    def __init__(self, history_persistence: SQLHistoryPersistence) -> None:
        """
        Initialize the chat interface with history persistence.

        Args:
            history_persistence: The SQLHistoryPersistence instance to use for storing interactions
        """
        self.history_persistence = history_persistence

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Process a chat message and yield responses.

        All interactions are automatically saved to the database via the
        @with_chat_metadata decorator.

        Args:
            message: The current user message
            history: List of previous messages in the conversation
            context: Context containing conversation metadata

        Yields:
            ChatResponse objects containing text chunks and usage information
        """
        # Add a reference to show the conversation ID being used
        yield self.create_reference(
            title="Conversation Info",
            content=f"Conversation ID: {context.conversation_id}\nMessage ID: {context.message_id}",
            url=None,
        )

        # Generate mock response (in real usage, use an actual LLM)
        response = await mock_llm_response(message)

        # Simulate streaming by yielding the response in chunks
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield self.create_text_response(chunk)
            await asyncio.sleep(0.05)  # Simulate streaming delay


async def _setup_persistence() -> tuple:
    """Setup database and persistence components."""
    database_url = "sqlite+aiosqlite:///./chat_history.db"
    engine = create_async_engine(database_url, echo=False)

    persistence_options = SQLHistoryPersistenceOptions(
        conversations_table="my_conversations",
        interactions_table="my_chat_interactions",
    )

    persistence = SQLHistoryPersistence(
        sqlalchemy_engine=engine,
        options=persistence_options,
    )

    chat = SimpleChatWithPersistence(history_persistence=persistence)
    return engine, persistence, persistence_options, chat, database_url


async def _run_first_message(chat: SimpleChatWithPersistence) -> tuple:
    """Execute first message in a new conversation."""
    conversation_id = None
    message_ids = []
    history: ChatFormat = []
    context = ChatContext()

    user_message_1 = "What is the capital of France?"
    print(f"User: {user_message_1}")
    print("Assistant: ", end="", flush=True)

    response_text_1 = ""
    async for response in chat.chat(user_message_1, history=history, context=context):
        if text := response.as_text():
            print(text, end="", flush=True)
            response_text_1 += text
        elif conv_id := response.as_conversation_id():
            conversation_id = conv_id
        elif response.type == ChatResponseType.MESSAGE_ID:
            message_ids.append(str(response.content))

    print()
    print()

    history.append({"role": "user", "content": user_message_1})
    history.append({"role": "assistant", "content": response_text_1})
    return conversation_id, message_ids, history, context


async def _run_second_message(
    chat: SimpleChatWithPersistence,
    history: ChatFormat,
    context: ChatContext,
    message_ids: list,
) -> ChatFormat:
    """Execute second message in the conversation."""
    user_message_2 = "What about Germany?"
    print(f"User: {user_message_2}")
    print("Assistant: ", end="", flush=True)

    response_text_2 = ""
    async for response in chat.chat(user_message_2, history=history, context=context):
        if text := response.as_text():
            print(text, end="", flush=True)
            response_text_2 += text
        elif response.type == ChatResponseType.MESSAGE_ID:
            message_ids.append(str(response.content))

    print()
    print()

    history.append({"role": "user", "content": user_message_2})
    history.append({"role": "assistant", "content": response_text_2})
    return history


async def _retrieve_and_display_history(persistence: SQLHistoryPersistence, conversation_id: str | None) -> None:
    """Retrieve and display conversation history from database."""
    print("Part 2: Retrieving conversation history from database...")
    print("-" * 80)

    if conversation_id:
        interactions = await persistence.get_conversation_interactions(conversation_id)
        print(f"Found {len(interactions)} interactions in the database:")
        print()

        for i, interaction in enumerate(interactions, 1):
            print(f"Interaction #{i}")
            print(f"  Message ID: {interaction['message_id']}")
            print(f"  Timestamp: {interaction['timestamp']}")
            print(f"  User: {interaction['message'][:80]}...")
            print(f"  Assistant: {interaction['response'][:80]}...")
            print(f"  Extra responses: {len(interaction['extra_responses'])} items")
            print()


async def _resume_conversation(
    chat: SimpleChatWithPersistence,
    persistence: SQLHistoryPersistence,
    conversation_id: str | None,
) -> None:
    """Resume conversation with loaded history."""
    print("Part 3: Resuming conversation with loaded history...")
    print("-" * 80)

    if conversation_id:
        loaded_interactions = await persistence.get_conversation_interactions(conversation_id)

        reconstructed_history: ChatFormat = []
        for interaction in loaded_interactions:
            reconstructed_history.append({"role": "user", "content": interaction["message"]})
            reconstructed_history.append({"role": "assistant", "content": interaction["response"]})

        resume_context = ChatContext(conversation_id=conversation_id)

        user_message_3 = "And what about Italy?"
        print(f"User: {user_message_3}")
        print("Assistant: ", end="", flush=True)

        async for response in chat.chat(user_message_3, history=reconstructed_history, context=resume_context):
            if text := response.as_text():
                print(text, end="", flush=True)

        print()
        print()

        updated_interactions = await persistence.get_conversation_interactions(conversation_id)
        print(f"Total interactions after resume: {len(updated_interactions)}")
        print()


def _print_summary(
    conversation_id: str | None,
    message_ids: list,
    database_url: str,
    persistence_options: SQLHistoryPersistenceOptions,
) -> None:
    """Print summary of the example."""
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"✓ Created conversation with ID: {conversation_id}")
    print(f"✓ Saved {len(message_ids)} messages to the database")
    print("✓ Successfully retrieved conversation history")
    print("✓ Resumed conversation and added new message")
    print()
    print(f"Database location: {database_url}")
    print("Tables created:")
    print(f"  - {persistence_options.conversations_table}")
    print(f"  - {persistence_options.interactions_table}")
    print()


async def run_conversation_example() -> None:
    """
    Demonstrates a complete conversation lifecycle with SQL history persistence.

    This example shows:
    1. Creating a new conversation
    2. Saving multiple interactions
    3. Retrieving conversation history from the database
    4. Resuming a conversation with loaded history
    """
    engine, persistence, persistence_options, chat, database_url = await _setup_persistence()

    print("=" * 80)
    print("Chat Example with SQL History Persistence")
    print("=" * 80)
    print()

    print("Part 1: Starting a new conversation...")
    print("-" * 80)

    conversation_id, message_ids, history, context = await _run_first_message(chat)
    history = await _run_second_message(chat, history, context, message_ids)

    print(f"Conversation ID: {conversation_id}")
    print(f"Messages saved: {len(message_ids)}")
    print()

    await _retrieve_and_display_history(persistence, conversation_id)
    await _resume_conversation(chat, persistence, conversation_id)

    _print_summary(conversation_id, message_ids, database_url, persistence_options)

    await engine.dispose()


async def run_multi_conversation_example() -> None:
    """
    Demonstrates managing multiple conversations in the same database.

    This example shows how different conversations are isolated from each other.
    """
    print("\n")
    print("=" * 80)
    print("Multi-Conversation Example")
    print("=" * 80)
    print()

    # Setup database
    database_url = "sqlite+aiosqlite:///./chat_history.db"
    engine = create_async_engine(database_url, echo=False)

    persistence = SQLHistoryPersistence(
        sqlalchemy_engine=engine,
        options=SQLHistoryPersistenceOptions(
            conversations_table="my_conversations",
            interactions_table="my_chat_interactions",
        ),
    )

    chat = SimpleChatWithPersistence(history_persistence=persistence)

    # Start two different conversations
    conversations = []

    for i in range(1, 3):
        print(f"Starting conversation #{i}...")
        context = ChatContext()
        history: ChatFormat = []

        message = f"Tell me a fact about number {i}"
        print(f"User: {message}")
        print("Assistant: ", end="", flush=True)

        conversation_id = None
        async for response in chat.chat(message, history=history, context=context):
            if text := response.as_text():
                print(text, end="", flush=True)
            elif conv_id := response.as_conversation_id():
                conversation_id = conv_id

        print()
        print(f"Conversation ID: {conversation_id}")
        print()

        conversations.append(conversation_id)

    # Verify each conversation has its own history
    print("Verifying isolated conversation histories...")
    print("-" * 80)
    for i, conv_id in enumerate(conversations, 1):
        if conv_id:
            interactions = await persistence.get_conversation_interactions(conv_id)
            print(f"Conversation {i} ({conv_id}): {len(interactions)} interactions")

    print()
    await engine.dispose()


if __name__ == "__main__":
    # Run the main example
    asyncio.run(run_conversation_example())

    # Run the multi-conversation example
    asyncio.run(run_multi_conversation_example())
