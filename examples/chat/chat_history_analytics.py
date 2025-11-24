"""
Ragbits Chat Example: Advanced History Persistence with Analytics

This example demonstrates usage of AnalyticsSQLHistoryPersistence including:

- Querying conversation history with custom filters
- Analyzing conversation patterns and metrics
- Exporting conversation data
- Managing conversation lifecycle (archiving, deletion)
- Working with PostgreSQL for production use cases

To run the script, execute the following command:

    ```bash
    uv run python examples/chat/chat_history_analytics.py
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
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence import AnalyticsSQLHistoryPersistence, SQLHistoryPersistenceOptions
from ragbits.core.prompt import ChatFormat


async def mock_llm_response(message: str) -> str:
    """Mock LLM response for demonstration purposes."""
    responses = {
        "What is Python?": (
            "Python is a high-level, interpreted programming language known for its simplicity and "
            "readability. It's widely used in web development, data science, AI, and automation."
        ),
        "How do I install packages?": (
            "You can install Python packages using pip, the package installer for Python. Simply run "
            "'pip install package-name' in your terminal."
        ),
        "Tell me about virtual environments": (
            "Virtual environments are isolated Python environments that allow you to manage project "
            "dependencies separately. Use 'python -m venv myenv' to create one."
        ),
        "What is machine learning?": (
            "Machine learning is a subset of AI that enables systems to learn and improve from "
            "experience without being explicitly programmed. It uses algorithms to find patterns in data."
        ),
        "Explain neural networks": (
            "Neural networks are computing systems inspired by biological neural networks. They consist "
            "of layers of interconnected nodes that process information to learn patterns and make "
            "predictions."
        ),
        "What is the capital of France?": (
            "The capital of France is Paris, known for its art, culture, and iconic landmarks like the " "Eiffel Tower."
        ),
        "Tell me about Paris": (
            "Paris is the capital of France, famous for its museums, architecture, cuisine, and "
            "landmarks like the Louvre, Notre-Dame, and the Eiffel Tower."
        ),
        "How does async/await work in Python?": (
            "Async/await in Python allows you to write asynchronous code that can handle multiple tasks "
            "concurrently. 'async def' defines a coroutine, and 'await' pauses execution until the "
            "awaited task completes."
        ),
        "What are coroutines?": (
            "Coroutines are special functions in Python that can pause and resume their execution. "
            "They're defined with 'async def' and are the building blocks of asynchronous programming."
        ),
        "Explain REST APIs": (
            "REST (Representational State Transfer) APIs are web services that use HTTP methods "
            "(GET, POST, PUT, DELETE) to perform operations on resources. They're stateless and use "
            "standard HTTP protocols."
        ),
        "What is GraphQL?": (
            "GraphQL is a query language for APIs that allows clients to request exactly the data they "
            "need. Unlike REST, it uses a single endpoint and a flexible query syntax."
        ),
        "Compare REST and GraphQL": (
            "REST uses multiple endpoints and fixed data structures, while GraphQL uses a single "
            "endpoint and allows clients to specify exactly what data they need. GraphQL reduces "
            "over-fetching but adds complexity."
        ),
    }
    return responses.get(message, f"This is a mock response to: {message}")


class ChatWithAnalytics(ChatInterface):
    """Simple chat interface for demonstrating analytics."""

    conversation_history = True

    def __init__(self, history_persistence: AnalyticsSQLHistoryPersistence) -> None:
        self.history_persistence = history_persistence

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Generate responses using the mock LLM."""
        # Generate mock response
        response = await mock_llm_response(message)

        # Simulate streaming by yielding the response in chunks
        chunk_size = 15
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield self.create_text_response(chunk)
            await asyncio.sleep(0.03)  # Simulate streaming delay


async def create_sample_conversations(
    chat: ChatWithAnalytics,
    num_conversations: int = 5,
) -> list[str]:
    """
    Create sample conversations for demonstration.

    Args:
        chat: The chat interface to use
        num_conversations: Number of conversations to create

    Returns:
        List of conversation IDs
    """
    print("Creating sample conversations...")
    print("-" * 80)

    conversation_ids = []
    sample_questions = [
        ["What is Python?", "How do I install packages?", "Tell me about virtual environments"],
        ["What is machine learning?", "Explain neural networks"],
        ["What is the capital of France?", "Tell me about Paris"],
        ["How does async/await work in Python?", "What are coroutines?"],
        ["Explain REST APIs", "What is GraphQL?", "Compare REST and GraphQL"],
    ]

    for i in range(num_conversations):
        context = ChatContext()
        history: ChatFormat = []

        questions = sample_questions[i % len(sample_questions)]

        for question in questions:
            response_text = ""
            async for response in chat.chat(question, history=history, context=context):
                if text := response.as_text():
                    response_text += text
                elif (conv_id := response.as_conversation_id()) and conv_id not in conversation_ids:
                    conversation_ids.append(conv_id)

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response_text})

            # Small delay between messages
            await asyncio.sleep(0.1)

        print(f"  Created conversation {i + 1}/{num_conversations}")

    print(f"✓ Created {len(conversation_ids)} conversations")
    print()
    return conversation_ids


async def _setup_database() -> tuple[Any, AnalyticsSQLHistoryPersistence, ChatWithAnalytics, str]:
    """Setup database and chat components."""
    database_url = "sqlite+aiosqlite:///./chat_analytics.db"
    engine = create_async_engine(database_url, echo=False)

    persistence = AnalyticsSQLHistoryPersistence(
        sqlalchemy_engine=engine,
        options=SQLHistoryPersistenceOptions(
            conversations_table="analytics_conversations",
            interactions_table="analytics_interactions",
        ),
    )

    chat = ChatWithAnalytics(history_persistence=persistence)
    return engine, persistence, chat, database_url


async def _demonstrate_overall_statistics(persistence: AnalyticsSQLHistoryPersistence) -> None:
    """Display overall statistics."""
    print("Overall Statistics")
    print("-" * 80)
    stats = await persistence.get_conversation_statistics()

    print(f"Total Conversations: {stats['total_conversations']}")
    print(f"Total Interactions: {stats['total_interactions']}")
    print(f"Avg Interactions per Conversation: {stats['avg_interactions_per_conversation']}")
    print(f"First Interaction: {stats['first_interaction']}")
    print(f"Last Interaction: {stats['last_interaction']}")
    print(f"Avg Message Length: {stats['avg_message_length']} characters")
    print(f"Avg Response Length: {stats['avg_response_length']} characters")
    print()


async def _demonstrate_recent_conversations(persistence: AnalyticsSQLHistoryPersistence) -> None:
    """Display recent conversations."""
    print("Recent Conversations")
    print("-" * 80)
    recent = await persistence.get_recent_conversations(limit=3)

    for i, conv in enumerate(recent, 1):
        print(f"{i}. Conversation ID: {conv['id'][:8]}...")
        print(f"   Created: {conv['created_at']}")
        print(f"   Interactions: {conv['interaction_count']}")
        print()


async def _demonstrate_search(persistence: AnalyticsSQLHistoryPersistence) -> None:
    """Demonstrate search functionality."""
    print("Search Example: Finding interactions about 'Python'")
    print("-" * 80)
    search_results = await persistence.search_interactions(
        query="Python",
        search_in_messages=True,
        search_in_responses=True,
        limit=3,
    )

    for i, result in enumerate(search_results, 1):
        print(f"{i}. Message: {result['message'][:60]}...")
        print(f"   Response: {result['response'][:60]}...")
        print(f"   Conversation: {result['conversation_id'][:8]}...")
        print()


async def _demonstrate_date_range(persistence: AnalyticsSQLHistoryPersistence) -> None:
    """Demonstrate date range query."""
    print("Date Range Example: Interactions from last hour")
    print("-" * 80)
    now = datetime.now().timestamp()
    one_hour_ago = (datetime.now() - timedelta(hours=1)).timestamp()

    recent_interactions = await persistence.get_interactions_by_date_range(
        start_timestamp=one_hour_ago,
        end_timestamp=now,
    )
    print(f"Found {len(recent_interactions)} interactions in the last hour")
    print()


async def _demonstrate_export(persistence: AnalyticsSQLHistoryPersistence, conversation_ids: list[str]) -> None:
    """Demonstrate conversation export."""
    print("Export Example: Exporting a conversation")
    print("-" * 80)
    if conversation_ids:
        export_data = await persistence.export_conversation(
            conversation_ids[0],
            include_metadata=True,
        )

        # Save to file
        export_filename = "conversation_export.json"
        with open(export_filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"✓ Exported conversation to {export_filename}")
        print(f"  Conversation ID: {export_data['conversation_id'][:8]}...")
        print(f"  Interactions: {export_data['interaction_count']}")
        print()


async def _demonstrate_deletion(persistence: AnalyticsSQLHistoryPersistence, conversation_ids: list[str]) -> None:
    """Demonstrate conversation deletion."""
    print("Management Example: Deleting a conversation")
    print("-" * 80)
    if len(conversation_ids) > 1:
        conversation_to_delete = conversation_ids[-1]
        print(f"Deleting conversation: {conversation_to_delete[:8]}...")

        deleted = await persistence.delete_conversation(conversation_to_delete)
        if deleted:
            print("✓ Conversation deleted successfully")

            # Verify deletion
            new_count = await persistence.get_conversation_count()
            print(f"  Remaining conversations: {new_count}")
        else:
            print("✗ Conversation not found")
        print()


def _print_summary(database_url: str) -> None:
    """Print final summary."""
    print("=" * 80)
    print("Analytics Features Demonstrated:")
    print("=" * 80)
    print("✓ Overall statistics and metrics")
    print("✓ Recent conversations listing")
    print("✓ Full-text search across interactions")
    print("✓ Date range queries")
    print("✓ Conversation export to JSON")
    print("✓ Conversation deletion and management")
    print()
    print(f"Database: {database_url}")
    print()


async def demonstrate_analytics() -> None:
    """Demonstrate the analytics features."""
    print("=" * 80)
    print("Chat History Analytics Example")
    print("=" * 80)
    print()

    # Setup database
    engine, persistence, chat, database_url = await _setup_database()

    # Create sample data
    conversation_ids = await create_sample_conversations(chat, num_conversations=5)

    # Demonstrate various features
    await _demonstrate_overall_statistics(persistence)
    await _demonstrate_recent_conversations(persistence)
    await _demonstrate_search(persistence)
    await _demonstrate_date_range(persistence)
    await _demonstrate_export(persistence, conversation_ids)
    await _demonstrate_deletion(persistence, conversation_ids)

    # Print summary
    _print_summary(database_url)

    # Cleanup
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(demonstrate_analytics())
