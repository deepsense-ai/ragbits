"""
Ragbits Chat Example: Advanced History Persistence with Analytics

This example demonstrates advanced usage of SQLHistoryPersistence including:

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

import sqlalchemy
from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence.sql import SQLHistoryPersistence, SQLHistoryPersistenceOptions
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


class AnalyticsHistoryPersistence(SQLHistoryPersistence):
    """
    Extended SQLHistoryPersistence with analytics and management features.

    This class adds advanced querying, analytics, and management capabilities
    on top of the base SQLHistoryPersistence.
    """

    async def get_conversation_count(self) -> int:
        """Get the total number of conversations."""
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(sqlalchemy.select(func.count()).select_from(self.Conversation))
            return result.scalar() or 0

    async def get_total_interactions_count(self) -> int:
        """Get the total number of chat interactions across all conversations."""
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(sqlalchemy.select(func.count()).select_from(self.ChatInteraction))
            return result.scalar() or 0

    async def get_recent_conversations(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent conversations.

        Args:
            limit: Maximum number of conversations to retrieve

        Returns:
            List of conversation dictionaries with metadata
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(self.Conversation).order_by(desc(self.Conversation.created_at)).limit(limit)
            )
            conversations = result.scalars().all()

            conversation_data = []
            for conv in conversations:
                # Get interaction count for this conversation
                interaction_result = await session.execute(
                    sqlalchemy.select(func.count())
                    .select_from(self.ChatInteraction)
                    .where(self.ChatInteraction.conversation_id == conv.id)
                )
                interaction_count = interaction_result.scalar() or 0

                conversation_data.append(
                    {
                        "id": conv.id,
                        "created_at": conv.created_at,
                        "interaction_count": interaction_count,
                    }
                )

            return conversation_data

    async def search_interactions(
        self,
        query: str,
        search_in_messages: bool = True,
        search_in_responses: bool = True,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for interactions containing specific text.

        Args:
            query: Text to search for
            search_in_messages: Whether to search in user messages
            search_in_responses: Whether to search in assistant responses
            limit: Maximum number of results

        Returns:
            List of matching interactions
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            filters = []
            if search_in_messages:
                filters.append(self.ChatInteraction.message.contains(query))
            if search_in_responses:
                filters.append(self.ChatInteraction.response.contains(query))

            if not filters:
                return []

            result = await session.execute(
                sqlalchemy.select(self.ChatInteraction)
                .where(sqlalchemy.or_(*filters))
                .order_by(desc(self.ChatInteraction.timestamp))
                .limit(limit)
            )
            interactions = result.scalars().all()

            return [
                {
                    "id": interaction.id,
                    "conversation_id": interaction.conversation_id,
                    "message_id": interaction.message_id,
                    "message": interaction.message,
                    "response": interaction.response,
                    "timestamp": interaction.timestamp,
                }
                for interaction in interactions
            ]

    async def get_interactions_by_date_range(
        self,
        start_timestamp: float,
        end_timestamp: float,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get interactions within a specific time range.

        Args:
            start_timestamp: Start of the time range (Unix timestamp)
            end_timestamp: End of the time range (Unix timestamp)
            conversation_id: Optional conversation ID to filter by

        Returns:
            List of interactions in the time range
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            query = sqlalchemy.select(self.ChatInteraction).where(
                and_(
                    self.ChatInteraction.timestamp >= start_timestamp,
                    self.ChatInteraction.timestamp <= end_timestamp,
                )
            )

            if conversation_id:
                query = query.where(self.ChatInteraction.conversation_id == conversation_id)

            query = query.order_by(self.ChatInteraction.timestamp)

            result = await session.execute(query)
            interactions = result.scalars().all()

            return [
                {
                    "id": interaction.id,
                    "conversation_id": interaction.conversation_id,
                    "message_id": interaction.message_id,
                    "message": interaction.message,
                    "response": interaction.response,
                    "timestamp": interaction.timestamp,
                    "created_at": interaction.created_at,
                }
                for interaction in interactions
            ]

    async def export_conversation(
        self,
        conversation_id: str,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """
        Export a complete conversation with all metadata.

        Args:
            conversation_id: The conversation to export
            include_metadata: Whether to include extra metadata

        Returns:
            Dictionary containing the complete conversation data
        """
        interactions = await self.get_conversation_interactions(conversation_id)

        export_data = {
            "conversation_id": conversation_id,
            "export_timestamp": datetime.now().isoformat(),
            "interaction_count": len(interactions),
            "interactions": interactions
            if include_metadata
            else [
                {
                    "message": i["message"],
                    "response": i["response"],
                    "timestamp": i["timestamp"],
                }
                for i in interactions
            ],
        }

        return export_data

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its interactions.

        Args:
            conversation_id: The conversation to delete

        Returns:
            True if the conversation was deleted, False if it didn't exist
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session, session.begin():
            # Check if conversation exists
            result = await session.execute(sqlalchemy.select(self.Conversation).filter_by(id=conversation_id))
            conversation = result.scalar_one_or_none()

            if not conversation:
                return False

            # Delete the conversation (interactions will be cascade deleted)
            await session.delete(conversation)
            await session.commit()
            return True

    async def get_conversation_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics about stored conversations.

        Returns:
            Dictionary containing various statistics
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            # Total counts
            conversation_count = await self.get_conversation_count()
            interaction_count = await self.get_total_interactions_count()

            # Average interactions per conversation
            avg_interactions = interaction_count / conversation_count if conversation_count > 0 else 0

            # Get timestamp range
            timestamp_result = await session.execute(
                sqlalchemy.select(
                    func.min(self.ChatInteraction.timestamp),
                    func.max(self.ChatInteraction.timestamp),
                )
            )
            min_ts, max_ts = timestamp_result.one()

            # Calculate message length statistics
            message_lengths_result = await session.execute(
                sqlalchemy.select(
                    func.avg(func.length(self.ChatInteraction.message)),
                    func.avg(func.length(self.ChatInteraction.response)),
                )
            )
            avg_message_length, avg_response_length = message_lengths_result.one()

            return {
                "total_conversations": conversation_count,
                "total_interactions": interaction_count,
                "avg_interactions_per_conversation": round(avg_interactions, 2),
                "first_interaction": datetime.fromtimestamp(min_ts).isoformat() if min_ts else None,
                "last_interaction": datetime.fromtimestamp(max_ts).isoformat() if max_ts else None,
                "avg_message_length": round(avg_message_length or 0, 2),
                "avg_response_length": round(avg_response_length or 0, 2),
            }


class ChatWithAnalytics(ChatInterface):
    """Simple chat interface for demonstrating analytics."""

    conversation_history = True

    def __init__(self, history_persistence: AnalyticsHistoryPersistence) -> None:
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


async def _setup_database() -> tuple[Any, AnalyticsHistoryPersistence, ChatWithAnalytics, str]:
    """Setup database and chat components."""
    database_url = "sqlite+aiosqlite:///./chat_analytics.db"
    engine = create_async_engine(database_url, echo=False)

    persistence = AnalyticsHistoryPersistence(
        sqlalchemy_engine=engine,
        options=SQLHistoryPersistenceOptions(
            conversations_table="analytics_conversations",
            interactions_table="analytics_interactions",
        ),
    )

    chat = ChatWithAnalytics(history_persistence=persistence)
    return engine, persistence, chat, database_url


async def _demonstrate_overall_statistics(persistence: AnalyticsHistoryPersistence) -> None:
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


async def _demonstrate_recent_conversations(persistence: AnalyticsHistoryPersistence) -> None:
    """Display recent conversations."""
    print("Recent Conversations")
    print("-" * 80)
    recent = await persistence.get_recent_conversations(limit=3)

    for i, conv in enumerate(recent, 1):
        print(f"{i}. Conversation ID: {conv['id'][:8]}...")
        print(f"   Created: {conv['created_at']}")
        print(f"   Interactions: {conv['interaction_count']}")
        print()


async def _demonstrate_search(persistence: AnalyticsHistoryPersistence) -> None:
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


async def _demonstrate_date_range(persistence: AnalyticsHistoryPersistence) -> None:
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


async def _demonstrate_export(persistence: AnalyticsHistoryPersistence, conversation_ids: list[str]) -> None:
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


async def _demonstrate_deletion(persistence: AnalyticsHistoryPersistence, conversation_ids: list[str]) -> None:
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
