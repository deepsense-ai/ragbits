from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from ragbits.chat.interface.types import ChatContext, ChatResponse


class HistoryPersistenceStrategy(ABC):
    """Base class for history persistence strategies."""

    @abstractmethod
    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: Sequence[ChatResponse],
        context: ChatContext,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction including the input message and responses.

        Args:
            message: The user's input message.
            response: The main response text.
            extra_responses: List of additional responses (references, state updates, etc.).
            context: Context dictionary containing metadata.
            timestamp: Unix timestamp of when the interaction occurred.
        """

    @abstractmethod
    async def get_conversation_interactions(self, conversation_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all interactions for a given conversation.

        Args:
            conversation_id: The ID of the conversation to fetch.

        Returns:
            A list of interaction dictionaries with deserialized data.
        """

    @abstractmethod
    async def get_conversation_count(self) -> int:
        """
        Get the total number of conversations.

        Returns:
            The total count of conversations.
        """

    @abstractmethod
    async def get_total_interactions_count(self) -> int:
        """
        Get the total number of chat interactions across all conversations.

        Returns:
            The total count of interactions.
        """

    @abstractmethod
    async def get_recent_conversations(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent conversations.

        Args:
            limit: Maximum number of conversations to retrieve.

        Returns:
            List of conversation dictionaries with metadata including id, created_at,
            and interaction_count.
        """

    @abstractmethod
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
            query: Text to search for.
            search_in_messages: Whether to search in user messages.
            search_in_responses: Whether to search in assistant responses.
            limit: Maximum number of results.

        Returns:
            List of matching interactions with id, conversation_id, message_id,
            message, response, and timestamp.
        """

    @abstractmethod
    async def get_interactions_by_date_range(
        self,
        start_timestamp: float,
        end_timestamp: float,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get interactions within a specific time range.

        Args:
            start_timestamp: Start of the time range (Unix timestamp).
            end_timestamp: End of the time range (Unix timestamp).
            conversation_id: Optional conversation ID to filter by.

        Returns:
            List of interactions in the time range.
        """

    @abstractmethod
    async def export_conversation(
        self,
        conversation_id: str,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """
        Export a complete conversation with all metadata.

        Args:
            conversation_id: The conversation to export.
            include_metadata: Whether to include extra metadata in interactions.

        Returns:
            Dictionary containing conversation_id, export_timestamp, interaction_count,
            and interactions list.
        """

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its interactions.

        Args:
            conversation_id: The conversation to delete.

        Returns:
            True if the conversation was deleted, False if it didn't exist.
        """

    @abstractmethod
    async def get_conversation_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics about stored conversations.

        Returns:
            Dictionary containing total_conversations, total_interactions,
            avg_interactions_per_conversation, first_interaction, last_interaction,
            avg_message_length, and avg_response_length.
        """
