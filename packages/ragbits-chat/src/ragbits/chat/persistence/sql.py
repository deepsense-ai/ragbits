import json
import uuid
from typing import Any, TypeVar, cast

import sqlalchemy
from sqlalchemy import TIMESTAMP, Column, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self

from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence.base import HistoryPersistenceStrategy
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ObjectConstructionConfig


class _Base(DeclarativeBase):
    @classmethod
    def set_table_name(cls, name: str) -> None:
        cls.__tablename__ = name


class Conversation(_Base):
    """
    Represents a conversation in the database.

    Attributes:
        id: The unique identifier for the conversation.
        created_at: The timestamp when the conversation was created.

    Table:
        conversations: Stores conversation records.
    """

    __tablename__ = "ragbits_conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(TIMESTAMP, server_default=func.now())


class ChatInteraction(_Base):
    """
    Represents a chat interaction in the database.

    Attributes:
        id: The unique identifier for the interaction.
        conversation_id: The ID of the conversation to which the interaction belongs.
        message_id: The unique message ID for this interaction.
        message: The user's input message.
        response: The main response text.
        extra_responses: JSON-serialized list of additional responses.
        context: JSON-serialized context dictionary.
        timestamp: The Unix timestamp when the interaction occurred.
        created_at: The timestamp when the record was created.

    Table:
        interactions: Stores chat interaction records.
    """

    __tablename__ = "ragbits_chat_interactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("ragbits_conversations.id", ondelete="CASCADE"), nullable=True)
    message_id = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    extra_responses = Column(Text, nullable=False)  # JSON string
    context = Column(Text, nullable=False)  # JSON string
    timestamp = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


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

        # Set custom table names if provided
        Conversation.set_table_name(self.options.conversations_table)
        ChatInteraction.set_table_name(self.options.interactions_table)

    async def init_db(self) -> None:
        """
        Initializes the database tables by creating them in the database.
        Conditional by default, will not attempt to recreate tables already
        present in the target database.
        """
        async with self.sqlalchemy_engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

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
        async with AsyncSession(self.sqlalchemy_engine) as session, session.begin():
            # Ensure conversation exists if conversation_id is provided
            if context.conversation_id:
                await self._ensure_conversation_exists(session, context.conversation_id)

            # Serialize complex data to JSON
            extra_responses_json = json.dumps([r.model_dump(mode="json") for r in extra_responses])
            context_json = json.dumps(context.model_dump(mode="json"))

            # Create interaction record
            interaction = ChatInteraction(
                conversation_id=context.conversation_id,
                message_id=context.message_id,
                message=message,
                response=response,
                extra_responses=extra_responses_json,
                context=context_json,
                timestamp=timestamp,
            )

            session.add(interaction)
            await session.commit()

    @staticmethod
    async def _ensure_conversation_exists(session: AsyncSession, conversation_id: str) -> None:
        """
        Ensures that a conversation with the given ID exists in the database.

        Args:
            session: The database session to use.
            conversation_id: The ID of the conversation to check/create.
        """
        # Check if conversation exists
        result = await session.execute(sqlalchemy.select(Conversation).filter_by(id=conversation_id).limit(1))
        existing_conversation = result.scalar_one_or_none()

        # Create conversation if it doesn't exist
        if not existing_conversation:
            conversation = Conversation(id=conversation_id)
            session.add(conversation)

    async def get_conversation_interactions(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all interactions for a given conversation.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of interaction dictionaries with deserialized data.
        """
        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(ChatInteraction)
                .filter_by(conversation_id=conversation_id)
                .order_by(ChatInteraction.timestamp)
            )
            interactions = result.scalars().all()

            return [
                {
                    "id": interaction.id,
                    "message_id": interaction.message_id,
                    "message": interaction.message,
                    "response": interaction.response,
                    "extra_responses": json.loads(cast(str, interaction.extra_responses)),
                    "context": json.loads(cast(str, interaction.context)),
                    "timestamp": interaction.timestamp,
                    "created_at": interaction.created_at,
                }
                for interaction in interactions
            ]

    async def get_recent_interactions(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve the most recent interactions across all conversations.

        Args:
            limit: Maximum number of interactions to return.

        Returns:
            A list of interaction dictionaries with deserialized data.
        """
        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(ChatInteraction).order_by(ChatInteraction.timestamp.desc()).limit(limit)
            )
            interactions = result.scalars().all()

            return [
                {
                    "id": interaction.id,
                    "conversation_id": interaction.conversation_id,
                    "message_id": interaction.message_id,
                    "message": interaction.message,
                    "response": interaction.response,
                    "extra_responses": json.loads(cast(str, interaction.extra_responses)),
                    "context": json.loads(cast(str, interaction.context)),
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
