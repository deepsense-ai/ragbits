import uuid

import sqlalchemy
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self

from ragbits.conversations.history.stores.base import HistoryStore
from ragbits.core.prompt import ChatFormat


class _Base(DeclarativeBase):
    pass


class Conversation(_Base):
    """
    Represents a conversation in the database.

    Attributes:
        id: The unique identifier for the conversation.
        created_at: The timestamp when the conversation was created.

    Table:
        conversations: Stores conversation records.
    """

    __tablename__ = "conversations"

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

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SQLHistoryStore(HistoryStore):
    """
    A class to manage storing, retrieving, and updating conversation histories.

    This class provides methods to create a new conversation, fetch an existing conversation,
    and update a conversation with new messages. The conversations are stored in a SQLAlchemy-backed
    database, and a unique conversation ID is generated based on the message contents.
    """

    def __init__(self, sqlalchemy_engine: sqlalchemy.Engine):
        """
        Initializes the ConversationHistoryStore with a SQLAlchemy engine.

        Args:
            sqlalchemy_engine: The SQLAlchemy engine used to interact with the database.
        """
        self.sqlalchemy_engine = sqlalchemy_engine

    def create_conversation(self, messages: ChatFormat) -> str | None:
        """
        Creates a new conversation in the database with an auto-generated ID.

        Args:
            messages: A list of dictionaries, where each dictionary represents a message
            with 'role' and 'content' keys.

        Returns:
            The database-generated ID of the conversation.
        """
        with self.sqlalchemy_engine.connect() as connection:
            rows = connection.execute(sqlalchemy.insert(Conversation).returning(Conversation.id))
            conversation_id = rows.scalar()

            connection.execute(
                sqlalchemy.insert(Message).values(
                    [
                        {"conversation_id": conversation_id, "role": msg["role"], "content": msg["content"]}
                        for msg in messages
                    ]
                )
            )
            connection.commit()

            return conversation_id

    def fetch_conversation(self, conversation_id: str) -> ChatFormat:
        """
        Fetches a conversation by its ID.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of message dictionaries, each containing 'role' and 'content'.
        """
        with self.sqlalchemy_engine.connect() as connection:
            rows = connection.execute(
                sqlalchemy.select(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at)
            ).fetchall()
            return [{"role": row.role, "content": row.content} for row in rows] if rows else []

    def update_conversation(self, conversation_id: str, new_messages: ChatFormat) -> str:
        """
        Updates a conversation with new messages.

        Args:
            conversation_id: The ID of the conversation to update.
            new_messages: A list of new message objects in the chat format.

        Returns:
            The ID of the updated conversation.
        """
        with self.sqlalchemy_engine.connect() as connection:
            connection.execute(
                sqlalchemy.insert(Message).values(
                    [
                        {"conversation_id": conversation_id, "role": msg["role"], "content": msg["content"]}
                        for msg in new_messages
                    ]
                )
            )
            connection.commit()

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
        engine_options = config["sqlalchemy_engine"]["config"]
        config["sqlalchemy_engine"] = create_engine(**engine_options)
        return super().from_config(config)
