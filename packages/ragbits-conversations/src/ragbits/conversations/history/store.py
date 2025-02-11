import hashlib
import json

import sqlalchemy

from ragbits.core.prompt import ChatFormat

from .models import Conversation, Message


class ConversationHistoryStore:
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

    @staticmethod
    def generate_conversation_id(messages: ChatFormat) -> str:
        """
        Generates a unique conversation ID based on the provided messages.

        Args:
            messages: A list of message objects in the chat format.

        Returns:
            A unique string representing the conversation ID.
        """
        json_obj = json.dumps(messages, separators=(",", ":"))
        return hashlib.sha256(json_obj.encode()).hexdigest()

    def create_conversation(self, messages: ChatFormat) -> str:
        """
        Creates a new conversation in the database or returns an existing one.

        Args:
            messages: A list of dictionaries, where each dictionary represents a message with 'role' and 'content' keys.

        Returns:
            The ID of the conversation.
        """
        conversation_id = self.generate_conversation_id(messages)

        with self.sqlalchemy_engine.connect() as connection:
            if connection.execute(sqlalchemy.select(Conversation).filter_by(id=conversation_id)).fetchone():
                return conversation_id

            connection.execute(sqlalchemy.insert(Conversation).values(id=conversation_id))
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
