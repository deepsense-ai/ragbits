import uuid
from typing import Any, Protocol, TypeVar

import sqlalchemy
from sqlalchemy import JSON, TIMESTAMP, Column, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self

from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence.base import HistoryPersistenceStrategy
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ObjectConstructionConfig


class _Base(DeclarativeBase):
    pass


class ConversationProtocol(Protocol):
    """Protocol for Conversation model."""

    id: str
    created_at: Any


class ChatInteractionProtocol(Protocol):
    """Protocol for ChatInteraction model."""

    id: int
    conversation_id: str | None
    message_id: str | None
    message: str
    response: str
    extra_responses: Any
    context: Any
    timestamp: float
    created_at: Any


def create_conversation_model(table_name: str, base_class: type[DeclarativeBase]) -> type[DeclarativeBase]:
    """
    Creates a Conversation model with the specified table name.

    Args:
        table_name: The name of the table for conversations.
        base_class: The DeclarativeBase class to inherit from.

    Returns:
        A Conversation model class with the specified table name.
    """

    class Conversation(base_class):  # type: ignore[misc, valid-type]
        """
        Represents a conversation in the database.

        Attributes:
            id: The unique identifier for the conversation.
            created_at: The timestamp when the conversation was created.

        Table:
            conversations: Stores conversation records.
        """

        __tablename__ = table_name
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        created_at = Column(TIMESTAMP, server_default=func.now())

    return Conversation


def create_chat_interaction_model(
    table_name: str, conversations_table_name: str, base_class: type[DeclarativeBase]
) -> type[DeclarativeBase]:
    """
    Creates a ChatInteraction model with the specified table name and foreign key reference.

    Args:
        table_name: The name of the table for chat interactions.
        conversations_table_name: The name of the conversations table to reference.
        base_class: The DeclarativeBase class to inherit from.

    Returns:
        A ChatInteraction model class with the specified table name and foreign key.
    """

    class ChatInteraction(base_class):  # type: ignore[misc, valid-type]
        """
        Represents a chat interaction in the database.

        Attributes:
            id: The unique identifier for the interaction.
            conversation_id: The ID of the conversation to which the interaction belongs.
            message_id: The unique message ID for this interaction.
            message: The user's input message.
            response: The main response text.
            extra_responses: JSON/JSONB array of additional responses.
            context: JSON/JSONB object containing context dictionary.
            timestamp: The Unix timestamp when the interaction occurred.
            created_at: The timestamp when the record was created.

        Table:
            interactions: Stores chat interaction records.
        """

        __tablename__ = table_name
        id = Column(Integer, primary_key=True, autoincrement=True)
        conversation_id = Column(
            String,
            ForeignKey(f"{conversations_table_name}.id", ondelete="CASCADE"),
            nullable=True,
        )
        message_id = Column(String, nullable=True)
        message = Column(Text, nullable=False)
        response = Column(Text, nullable=False)
        extra_responses = Column(JSON, nullable=False)  # JSON/JSONB type for better performance
        context = Column(JSON, nullable=False)  # JSON/JSONB type for better performance
        timestamp = Column(Float, nullable=False)
        created_at = Column(TIMESTAMP, server_default=func.now())

    return ChatInteraction


class SQLHistoryPersistenceOptions(Options):
    """
    Configuration options for SQLHistoryPersistence.
    """

    conversations_table: str = "ragbits_conversations"
    interactions_table: str = "ragbits_chat_interactions"


SQLHistoryPersistenceOptionsT = TypeVar("SQLHistoryPersistenceOptionsT", bound=SQLHistoryPersistenceOptions)


class SQLHistoryPersistence(HistoryPersistenceStrategy):
    """
    A SQL-based implementation of HistoryPersistenceStrategy.

    This class provides methods to save chat interactions to a SQLAlchemy-backed
    database. It stores conversations and their associated interactions with
    full context and response data.
    """

    def __init__(
        self,
        sqlalchemy_engine: AsyncEngine,
        options: SQLHistoryPersistenceOptions | None = None,
    ) -> None:
        """
        Initializes the SQLHistoryPersistence with a SQLAlchemy engine.

        Args:
            sqlalchemy_engine: The SQLAlchemy engine used to interact with the database.
            options: Configuration options for table names and other settings.
        """
        self.sqlalchemy_engine = sqlalchemy_engine
        self.options = options or SQLHistoryPersistenceOptions()
        self._db_initialized = False

        # Create a unique DeclarativeBase for this instance to avoid table conflicts
        class _Base(DeclarativeBase):
            pass

        self._base = _Base

        # Create model classes with custom table names and foreign key references
        self.Conversation: Any = create_conversation_model(self.options.conversations_table, self._base)
        self.ChatInteraction: Any = create_chat_interaction_model(
            self.options.interactions_table, self.options.conversations_table, self._base
        )

    async def _init_db(self) -> None:
        """
        Initializes the database tables by creating them in the database.
        Conditional by default, will not attempt to recreate tables already
        present in the target database.

        This method is called automatically on first usage.
        """
        if not self._db_initialized:
            async with self.sqlalchemy_engine.begin() as conn:
                await conn.run_sync(self._base.metadata.create_all)
            self._db_initialized = True

    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: list[ChatResponse],
        context: ChatContext,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction to the database.

        Args:
            message: The user's input message
            response: The main response text
            extra_responses: List of additional responses (references, state updates, etc.)
            context: Context dictionary containing metadata
            timestamp: Unix timestamp of when the interaction occurred
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session, session.begin():
            # Ensure conversation exists if conversation_id is provided
            if context.conversation_id:
                await self._ensure_conversation_exists(session, context.conversation_id)

            # Convert to JSON-serializable format (SQLAlchemy will handle the JSON serialization)
            extra_responses_data = [r.model_dump(mode="json") for r in extra_responses]
            context_data = context.model_dump(mode="json")

            # Create interaction record
            interaction = self.ChatInteraction(
                conversation_id=context.conversation_id,
                message_id=context.message_id,
                message=message,
                response=response,
                extra_responses=extra_responses_data,
                context=context_data,
                timestamp=timestamp,
            )

            session.add(interaction)
            await session.commit()

    async def _ensure_conversation_exists(self, session: AsyncSession, conversation_id: str) -> None:
        """
        Ensures that a conversation with the given ID exists in the database.

        Args:
            session: The database session to use.
            conversation_id: The ID of the conversation to check/create.
        """
        # Check if conversation exists
        result = await session.execute(sqlalchemy.select(self.Conversation).filter_by(id=conversation_id).limit(1))
        existing_conversation = result.scalar_one_or_none()

        # Create conversation if it doesn't exist
        if not existing_conversation:
            conversation = self.Conversation(id=conversation_id)
            session.add(conversation)

    async def get_conversation_interactions(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all interactions for a given conversation.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of interaction dictionaries with deserialized data.
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(self.ChatInteraction)
                .filter_by(conversation_id=conversation_id)
                .order_by(self.ChatInteraction.timestamp)
            )
            interactions = result.scalars().all()

            return [
                {
                    "id": interaction.id,
                    "conversation_id": interaction.conversation_id,
                    "message_id": interaction.message_id,
                    "message": interaction.message,
                    "response": interaction.response,
                    "extra_responses": interaction.extra_responses,
                    "context": interaction.context,
                    "timestamp": interaction.timestamp,
                    "created_at": interaction.created_at,
                }
                for interaction in interactions
            ]

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        engine_options = ObjectConstructionConfig.model_validate(config["sqlalchemy_engine"])
        config["sqlalchemy_engine"] = create_async_engine(engine_options.config["url"])
        return cls(**config)
