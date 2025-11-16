"""
Ragbits Chat Example: Production PostgreSQL Setup

This example demonstrates production-ready setup of SQLHistoryPersistence with PostgreSQL,
including:

- Environment-based configuration
- Connection pooling and optimization
- Error handling and retry logic
- Schema migration patterns
- Production best practices

Prerequisites:
    - PostgreSQL server running locally or remotely
    - asyncpg driver installed

Setup PostgreSQL (using Docker):
    ```bash
    docker run --name ragbits-postgres \
        -e POSTGRES_PASSWORD=ragbits2024 \
        -e POSTGRES_USER=ragbits \
        -e POSTGRES_DB=chatdb \
        -p 5432:5432 \
        -d postgres:16
    ```

Run the example:
    ```bash
    # Set the database URL
    export DATABASE_URL="postgresql+asyncpg://ragbits:ragbits2024@localhost:5432/chatdb"

    # Run the script
    uv run python examples/chat/chat_with_postgresql.py
    ```

Requirements:
    - asyncpg (for PostgreSQL async support)
    - ragbits-chat
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
#     "asyncpg>=0.30.0",
#     "greenlet>=3.0.0",
# ]
# ///

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence.sql import SQLHistoryPersistence, SQLHistoryPersistenceOptions
from ragbits.core.prompt import ChatFormat


async def mock_llm_response(message: str) -> str:
    """Mock LLM response for demonstration purposes."""
    responses = {
        "What are the best practices for database connection pooling?": (
            "Database connection pooling best practices include: 1) Set appropriate pool size based "
            "on your application's concurrency needs, 2) Configure timeout values to prevent resource "
            "exhaustion, 3) Use connection validation (pool_pre_ping), 4) Recycle connections "
            "periodically, and 5) Monitor pool statistics to optimize settings."
        ),
        "How does PostgreSQL handle concurrent connections?": (
            "PostgreSQL handles concurrent connections through a process-based architecture. Each "
            "connection spawns a new backend process, which provides strong isolation. PostgreSQL uses "
            "MVCC (Multi-Version Concurrency Control) to manage concurrent access to data without "
            "locking, allowing high throughput for read operations."
        ),
        "Tell me about ACID properties in PostgreSQL": (
            "PostgreSQL fully supports ACID properties: Atomicity ensures transactions are "
            "all-or-nothing, Consistency maintains database rules, Isolation prevents transaction "
            "interference, and Durability guarantees committed data persists. PostgreSQL uses WAL "
            "(Write-Ahead Logging) for durability and offers multiple isolation levels."
        ),
    }
    return responses.get(message, f"This is a mock response about: {message}")


class ProductionConfig:
    """Configuration for production database setup."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://ragbits:ragbits2024@localhost:5432/chatdb")

        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        # Retry settings
        self.max_retries = int(os.getenv("DB_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("DB_RETRY_DELAY", "1.0"))

        # Table names
        self.conversations_table = os.getenv("CONVERSATIONS_TABLE", "production_conversations")
        self.interactions_table = os.getenv("INTERACTIONS_TABLE", "production_interactions")


class ProductionChatInterface(ChatInterface):
    """Production-ready chat interface with PostgreSQL persistence."""

    conversation_history = True
    show_usage = True

    def __init__(self, history_persistence: SQLHistoryPersistence) -> None:
        """
        Initialize the production chat interface.

        Args:
            history_persistence: The SQLHistoryPersistence instance
        """
        self.history_persistence = history_persistence

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Process a chat message with production-grade error handling.

        Args:
            message: The current user message
            history: List of previous messages in the conversation
            context: Context containing conversation metadata

        Yields:
            ChatResponse objects
        """
        try:
            # Generate mock response
            response = await mock_llm_response(message)

            # Simulate streaming by yielding the response in chunks
            chunk_size = 20
            for i in range(0, len(response), chunk_size):
                chunk = response[i : i + chunk_size]
                yield self.create_text_response(chunk)
                await asyncio.sleep(0.02)  # Simulate streaming delay

        except Exception as e:
            # In production, log the error and provide a graceful fallback
            print(f"Error generating response: {e}")
            yield self.create_text_response(
                "I apologize, but I encountered an error processing your request. Please try again."
            )


@asynccontextmanager
async def create_database_engine(config: ProductionConfig) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create and configure a production database engine with connection pooling.

    Args:
        config: Production configuration

    Yields:
        Configured AsyncEngine instance
    """
    engine = create_async_engine(
        config.database_url,
        # Connection pool settings
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        # Pre-ping ensures connections are valid before use
        pool_pre_ping=True,
        # Echo SQL queries (disable in production)
        echo=False,
        # PostgreSQL-specific optimizations
        connect_args={
            "server_settings": {
                "application_name": "ragbits_chat",
            },
        },
    )

    try:
        yield engine
    finally:
        # Ensure proper cleanup
        await engine.dispose()


async def create_persistence(
    engine: AsyncEngine,
    config: ProductionConfig,
) -> SQLHistoryPersistence:
    """
    Create and initialize the persistence layer with retry logic.

    Args:
        engine: SQLAlchemy async engine
        config: Production configuration

    Returns:
        Initialized SQLHistoryPersistence instance
    """
    options = SQLHistoryPersistenceOptions(
        conversations_table=config.conversations_table,
        interactions_table=config.interactions_table,
    )

    persistence = SQLHistoryPersistence(
        sqlalchemy_engine=engine,
        options=options,
    )

    # Initialize database with retry logic
    for attempt in range(config.max_retries):
        try:
            await persistence._init_db()
            print("✓ Database initialized successfully")
            return persistence
        except OperationalError as e:
            if attempt < config.max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{config.max_retries}), retrying...")
                await asyncio.sleep(config.retry_delay * (attempt + 1))
            else:
                print(f"✗ Failed to connect to database after {config.max_retries} attempts")
                raise e

    return persistence


def _print_config(config: ProductionConfig) -> None:
    """Print production configuration."""
    print("Configuration:")
    print("-" * 80)
    print(f"Database URL: {config.database_url.split('@')[1] if '@' in config.database_url else 'localhost'}")
    print(f"Pool Size: {config.pool_size}")
    print(f"Max Overflow: {config.max_overflow}")
    print(f"Pool Timeout: {config.pool_timeout}s")
    print(f"Pool Recycle: {config.pool_recycle}s")
    print(f"Conversations Table: {config.conversations_table}")
    print(f"Interactions Table: {config.interactions_table}")
    print()


async def _run_example_conversation(
    chat: ProductionChatInterface,
    persistence: SQLHistoryPersistence,
) -> str | None:
    """Run example conversation and return conversation ID."""
    print("Running Example Conversation:")
    print("-" * 80)

    context = ChatContext()
    history: ChatFormat = []

    messages = [
        "What are the best practices for database connection pooling?",
        "How does PostgreSQL handle concurrent connections?",
        "Tell me about ACID properties in PostgreSQL",
    ]

    conversation_id = None

    for i, user_message in enumerate(messages, 1):
        print(f"\n[{i}/{len(messages)}] User: {user_message}")
        print("Assistant: ", end="", flush=True)

        response_text = ""
        try:
            async for response in chat.chat(user_message, history=history, context=context):
                if text := response.as_text():
                    print(text, end="", flush=True)
                    response_text += text
                elif conv_id := response.as_conversation_id():
                    conversation_id = conv_id

            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": response_text})
            print()

        except Exception as e:
            print(f"\n✗ Error: {e}")
            break

    print()
    print("=" * 80)
    return conversation_id


async def _verify_persistence(persistence: SQLHistoryPersistence, conversation_id: str | None) -> None:
    """Verify data persistence in PostgreSQL."""
    if conversation_id:
        print("\nVerifying Persistence:")
        print("-" * 80)

        interactions = await persistence.get_conversation_interactions(conversation_id)
        print(f"✓ Successfully retrieved {len(interactions)} interactions from PostgreSQL")

        if interactions:
            first = interactions[0]
            print("\nFirst Interaction:")
            print(f"  Message ID: {first['message_id']}")
            print(f"  Message: {first['message'][:50]}...")
            print(f"  Response: {first['response'][:50]}...")
            print(f"  Timestamp: {first['timestamp']}")

        print()


def _print_features() -> None:
    """Print demonstrated production features."""
    print("=" * 80)
    print("Production Features Demonstrated:")
    print("=" * 80)
    print("✓ Environment-based configuration")
    print("✓ Connection pooling with optimized settings")
    print("✓ Retry logic for database initialization")
    print("✓ Proper resource cleanup (connection disposal)")
    print("✓ Error handling and graceful degradation")
    print("✓ Production-grade database settings")
    print()


async def demonstrate_production_setup() -> None:
    """
    Demonstrate production-ready PostgreSQL setup with best practices.
    """
    print("=" * 80)
    print("Production PostgreSQL Setup Example")
    print("=" * 80)
    print()

    config = ProductionConfig()
    _print_config(config)

    async with create_database_engine(config) as engine:
        persistence = await create_persistence(engine, config)
        chat = ProductionChatInterface(history_persistence=persistence)

        conversation_id = await _run_example_conversation(chat, persistence)
        await _verify_persistence(persistence, conversation_id)

    _print_features()


async def demonstrate_migration_pattern() -> None:
    """
    Demonstrate schema migration patterns for production.

    Note: This is a simplified example. In production, use a proper migration
    tool like Alembic for schema changes.
    """
    print("=" * 80)
    print("Schema Migration Pattern Example")
    print("=" * 80)
    print()

    config = ProductionConfig()

    async with create_database_engine(config) as engine:
        from sqlalchemy import inspect

        await create_persistence(engine, config)

        print("Schema Information:")
        print("-" * 80)

        # Inspect schema
        async with engine.begin() as conn:

            def inspect_tables(connection: object) -> list[str]:
                inspector = inspect(connection)
                tables = inspector.get_table_names()
                return tables

            tables = await conn.run_sync(inspect_tables)
            print(f"Tables in database: {', '.join(tables)}")

        # Example: Check if tables exist
        if config.conversations_table in tables:
            print(f"✓ {config.conversations_table} exists")
        if config.interactions_table in tables:
            print(f"✓ {config.interactions_table} exists")

        print()

        # Note: For real migrations, use Alembic
        print("For production schema migrations, use Alembic:")
        print("  1. pip install alembic")
        print("  2. alembic init migrations")
        print("  3. alembic revision --autogenerate -m 'description'")
        print("  4. alembic upgrade head")
        print()


async def demonstrate_performance_monitoring() -> None:
    """
    Demonstrate connection pool monitoring and performance tracking.
    """
    print("=" * 80)
    print("Performance Monitoring Example")
    print("=" * 80)
    print()

    config = ProductionConfig()

    async with create_database_engine(config) as engine:
        print("Connection Pool Status:")
        print("-" * 80)

        # Get pool statistics
        pool = engine.pool
        print(f"Pool Size: {pool.size()}")
        print(f"Checked Out Connections: {pool.checkedout()}")
        print(f"Overflow: {pool.overflow()}")
        print(f"Checked In: {pool.checkedin()}")
        print()

        # Create persistence and run some operations
        persistence = await create_persistence(engine, config)
        chat = ProductionChatInterface(history_persistence=persistence)

        # Simulate concurrent operations
        print("Simulating concurrent operations...")
        print("-" * 80)

        async def create_conversation(msg: str) -> str:
            """Create a single conversation."""
            context = ChatContext()
            async for response in chat.chat(msg, history=[], context=context):
                if conv_id := response.as_conversation_id():
                    return conv_id
            return ""

        # Create multiple conversations concurrently
        tasks = [create_conversation(f"Question {i}") for i in range(5)]

        conversation_ids = await asyncio.gather(*tasks)
        print(f"✓ Created {len(conversation_ids)} conversations concurrently")

        # Check pool status after operations
        print("\nPool Status After Operations:")
        print(f"  Checked Out: {pool.checkedout()}")
        print(f"  Overflow: {pool.overflow()}")
        print()


if __name__ == "__main__":
    print("Make sure PostgreSQL is running and DATABASE_URL is set correctly!")
    print()

    try:
        # Run main demonstration
        asyncio.run(demonstrate_production_setup())

        # Run migration pattern demonstration
        asyncio.run(demonstrate_migration_pattern())

        # Run performance monitoring demonstration
        asyncio.run(demonstrate_performance_monitoring())

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check DATABASE_URL environment variable")
        print("3. Verify database credentials")
        print("4. Ensure asyncpg is installed: pip install asyncpg")
