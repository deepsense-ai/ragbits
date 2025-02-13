from abc import ABC, abstractmethod
from typing import ClassVar

from ragbits.conversations.history import stores
from ragbits.core.prompt import ChatFormat
from ragbits.core.utils.config_handling import WithConstructionConfig


class HistoryStore(WithConstructionConfig, ABC):
    """
    Abstract base class for conversation history stores.
    """

    default_module: ClassVar = stores
    configuration_key: ClassVar = "store"

    @abstractmethod
    def create_conversation(self, messages: ChatFormat) -> str:
        """
        Creates a new conversation and stores the given messages.

        Args:
            messages: A list of message objects representing the conversation history.

        Returns:
            A unique identifier for the created conversation.
        """

    @abstractmethod
    def fetch_conversation(self, conversation_id: str) -> ChatFormat:
        """
        Retrieves a conversation by its unique identifier.

        Args:
            conversation_id: The unique ID of the conversation to fetch.

        Returns:
            A list of message objects representing the retrieved conversation history.
        """

    @abstractmethod
    def update_conversation(self, conversation_id: str, new_messages: ChatFormat) -> str:
        """
        Updates an existing conversation with new messages.

        Args:
            conversation_id: The unique ID of the conversation to update.
            new_messages: A list of new message objects to append to the conversation.

        Returns:
            The ID of the updated conversation.
        """
