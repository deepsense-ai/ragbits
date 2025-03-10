import uuid
from typing import TypeVar

import sqlalchemy
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, func
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self

from ragbits.conversations.history.stores.base import HistoryStore
from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat
from ragbits.core.utils.config_handling import ObjectContructionConfig


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


class Message(_Base):
    """
    Represents a message in a conversation.

    Attributes:
        id: The unique identifier for the message.
        conversation_id: The ID of the conversation to which the message belongs.
        role: The role of the sender (e.g., 'user', 'assistant').
        content: The content of the message.
        created_at: The timestamp when the message was created.

    Table:
        messages: Stores message records.
    """

    __tablename__ = "ragbits_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("ragbits_conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SQLHistoryStoreOptions(Options):
    """
    Stores table names for the database models in SQLHistoryStore.
    """

    conversations_table: str = "conversations"
    messages_table: str = "messages"


SQLHistoryStoreOptionsT = TypeVar("SQLHistoryStoreOptionsT", bound=SQLHistoryStoreOptions)


class SQLHistoryStore(HistoryStore[SQLHistoryStoreOptions]):
    """
    A class to manage storing, retrieving, and updating conversation histories.

    This class provides methods to create a new conversation, fetch an existing conversation,
    and update a conversation with new messages. The conversations are stored in a SQLAlchemy-backed
    database, and a unique conversation ID is generated based on the message contents.
    """

    options_cls = SQLHistoryStoreOptions

    def __init__(self, sqlalchemy_engine: AsyncEngine, default_options: SQLHistoryStoreOptionsT | None = None) -> None:
        """
        Initializes the ConversationHistoryStore with a SQLAlchemy engine.

        Args:
            sqlalchemy_engine: The SQLAlchemy engine used to interact with the database.
            default_options: An optional SQLHistoryStoreOptions specifying table names.
        """
        super().__init__(default_options=default_options)
        self.sqlalchemy_engine = sqlalchemy_engine

        Conversation.set_table_name(self.default_options.conversations_table)
        Message.set_table_name(self.default_options.messages_table)

    async def init_db(self) -> None:
        """
        Initializes the database tables by creating them in the database.
        Conditional by default, will not attempt to recreate tables already
        present in the target database.
        """
        async with self.sqlalchemy_engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def create_conversation(self, messages: ChatFormat) -> str:
        """
        Creates a new conversation in the database with an auto-generated ID.

        Args:
            messages: A list of dictionaries, where each dictionary represents a message
            with 'role' and 'content' keys.

        Returns:
            The database-generated ID of the conversation.

        Raises:
            ValueError: If the conversation could not be generated.
        """
        async with AsyncSession(self.sqlalchemy_engine) as session:
            async with session.begin():
                result = await session.execute(sqlalchemy.insert(Conversation).returning(Conversation.id))
                conversation_id = result.scalar()

                if not conversation_id:
                    raise ValueError("Failed to generate conversation.")

                await session.execute(
                    sqlalchemy.insert(Message).values(
                        [
                            {"conversation_id": conversation_id, "role": msg["role"], "content": msg["content"]}
                            for msg in messages
                        ]
                    )
                )
                await session.commit()
            return conversation_id

    async def fetch_conversation(self, conversation_id: str) -> ChatFormat:
        """
        Fetches a conversation by its ID.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of message dictionaries, each containing 'role' and 'content'.
        """
        async with AsyncSession(self.sqlalchemy_engine) as session:
            result = await session.execute(
                sqlalchemy.select(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at)
            )
            rows = result.scalars().all()
            return [{"role": row.role, "content": row.content} for row in rows] if rows else []

    async def update_conversation(self, conversation_id: str, new_messages: ChatFormat) -> str:
        """
        Updates a conversation with new messages.

        Args:
            conversation_id: The ID of the conversation to update.
            new_messages: A list of new message objects in the chat format.

        Returns:
            The ID of the updated conversation.
        """
        async with AsyncSession(self.sqlalchemy_engine) as session:
            async with session.begin():
                await session.execute(
                    sqlalchemy.insert(Message).values(
                        [
                            {"conversation_id": conversation_id, "role": msg["role"], "content": msg["content"]}
                            for msg in new_messages
                        ]
                    )
                )
                await session.commit()
            return conversation_id

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Initializes the class with the provided configuration.

        Args:
            config: A dictionary containing configuration details for the class.

        Returns:
            An instance of the class initialized with the provided configuration.
        """
        engine_options = ObjectContructionConfig.model_validate(config["sqlalchemy_engine"])
        config["sqlalchemy_engine"] = create_async_engine(engine_options.config["url"])
        return cls(**config)
