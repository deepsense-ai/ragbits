import asyncio
import uuid
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

import sqlalchemy
from sqlalchemy import JSON, TIMESTAMP, Column, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self

from ragbits.chat.interface.types import ChatContext, ChatResponse, ConversationSummaryResponse
from ragbits.chat.persistence.base import HistoryPersistenceStrategy
from ragbits.core.options import Options
from ragbits.core.utils.config_handling import ObjectConstructionConfig


class _Base(DeclarativeBase):
    pass


class ConversationProtocol(Protocol):
    """Protocol for Conversation model."""

    id: str
    user_id: str | None
    summary: str | None
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
            user_id: Identifier of the conversation owner, or ``None`` for anonymous.
            summary: Latest summary yielded for this conversation, or ``None``.
            created_at: The timestamp when the conversation was created.

        Table:
            conversations: Stores conversation records.
        """

        __tablename__ = table_name
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        user_id = Column(String, nullable=True, index=True)
        summary = Column(Text, nullable=True)
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
        self._init_lock = asyncio.Lock()

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
        if self._db_initialized:
            return
        async with self._init_lock:
            if self._db_initialized:
                return
            async with self.sqlalchemy_engine.begin() as conn:
                await conn.run_sync(self._base.metadata.create_all)
            self._db_initialized = True

    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: Sequence[ChatResponse],
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
            summary = self._latest_summary_from_responses(extra_responses)
            if context.conversation_id:
                user_id = context.user.user_id if context.user else None
                await self._ensure_conversation_exists(session, context.conversation_id, user_id, summary)

            # Convert to JSON-serializable format with type information
            extra_responses_data = [
                {"type": r.get_type(), "content": r.content.model_dump(mode="json")} for r in extra_responses
            ]
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

    @staticmethod
    def _latest_summary_from_responses(extra_responses: Sequence[ChatResponse]) -> str | None:
        """Return the most recent ``ConversationSummaryResponse`` summary, if any."""
        for response in reversed(extra_responses):
            if isinstance(response, ConversationSummaryResponse):
                summary = response.content.summary
                if summary:
                    return summary
        return None

    async def _ensure_conversation_exists(
        self,
        session: AsyncSession,
        conversation_id: str,
        user_id: str | None = None,
        summary: str | None = None,
    ) -> None:
        """
        Ensures that a conversation with the given ID exists in the database.

        Args:
            session: The database session to use.
            conversation_id: The ID of the conversation to check/create.
            user_id: The owner user ID to associate with a new conversation.
            summary: Latest summary to persist, if available. Existing summaries
                are only overwritten when a new non-empty value is provided.
        """
        result = await session.execute(sqlalchemy.select(self.Conversation).filter_by(id=conversation_id).limit(1))
        existing_conversation = result.scalar_one_or_none()

        if existing_conversation is None:
            conversation = self.Conversation(id=conversation_id, user_id=user_id, summary=summary)
            session.add(conversation)
            await session.flush()
        elif summary is not None and existing_conversation.summary != summary:
            existing_conversation.summary = summary
            await session.flush()

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

    async def list_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """
        List conversations owned by a user, ordered by most recent activity.

        Args:
            user_id: The owner's user ID.
            limit: Maximum number of conversations to return.
            offset: Number of conversations to skip.

        Returns:
            A list of conversation dictionaries.
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            latest_interaction_subquery = (
                sqlalchemy.select(
                    self.ChatInteraction.conversation_id.label("conversation_id"),
                    sqlalchemy.func.max(self.ChatInteraction.timestamp).label("updated_at"),
                )
                .group_by(self.ChatInteraction.conversation_id)
                .subquery()
            )
            result = await session.execute(
                sqlalchemy.select(self.Conversation)
                .join(
                    latest_interaction_subquery,
                    self.Conversation.id == latest_interaction_subquery.c.conversation_id,
                    isouter=True,
                )
                .where(self.Conversation.user_id == user_id)
                .order_by(
                    latest_interaction_subquery.c.updated_at.desc(),
                    self.Conversation.created_at.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
            conversations = result.scalars().all()

            return [
                {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "summary": conv.summary,
                    "created_at": conv.created_at,
                }
                for conv in conversations
            ]

    async def get_conversation_summaries(self, conversation_ids: list[str]) -> dict[str, str]:
        """
        Get a display summary for each conversation.

        Reads the persisted ``summary`` column populated by ``save_interaction``
        when a ``ConversationSummaryResponse`` is yielded. Falls back to a
        truncated version of the first user message for conversations that have
        no stored summary yet.

        Args:
            conversation_ids: List of conversation IDs to fetch summaries for.

        Returns:
            A dict mapping conversation_id → summary string.
        """
        if not conversation_ids:
            return {}

        await self._init_db()

        max_len = 80
        summaries: dict[str, str] = {}
        async with AsyncSession(self.sqlalchemy_engine) as session:
            stored = await session.execute(
                sqlalchemy.select(self.Conversation.id, self.Conversation.summary).filter(
                    self.Conversation.id.in_(conversation_ids)
                )
            )
            for conv_id, summary in stored.all():
                if summary:
                    summaries[conv_id] = summary

            for cid in conversation_ids:
                if cid in summaries:
                    continue
                result = await session.execute(
                    sqlalchemy.select(self.ChatInteraction.message)
                    .filter_by(conversation_id=cid)
                    .order_by(self.ChatInteraction.id.asc())
                    .limit(1)
                )
                first_msg = result.scalar_one_or_none()
                if first_msg:
                    summaries[cid] = first_msg[:max_len] + ("…" if len(first_msg) > max_len else "")
        return summaries

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its interactions.

        Args:
            conversation_id: The ID of the conversation to delete.

        Returns:
            True if the conversation was deleted, False if it didn't exist.
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            await session.execute(sqlalchemy.delete(self.ChatInteraction).filter_by(conversation_id=conversation_id))
            result = await session.execute(sqlalchemy.delete(self.Conversation).filter_by(id=conversation_id))
            await session.commit()
            return result.rowcount > 0  # type: ignore[union-attr]

    async def get_conversation_owner(self, conversation_id: str) -> str | None:
        """
        Get the owner user_id for a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            The owner's user_id, or None if the conversation doesn't exist.
        """
        await self._init_db()

        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(self.Conversation.user_id).filter_by(id=conversation_id).limit(1)
            )
            return result.scalar_one_or_none()

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
