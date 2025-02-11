import uuid

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    This class represents the base of the database.
    """


class Conversation(Base):
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


class Message(Base):
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
