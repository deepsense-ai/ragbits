from abc import ABC, abstractmethod

from ragbits.chat.interface.types import ChatContext, ChatResponse


class HistoryPersistenceStrategy(ABC):
    """Base class for history persistence strategies."""

    @abstractmethod
    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: list[ChatResponse],
        context: ChatContext,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction including the input message and responses.

        Args:
            message: The user's input message
            response: The main response text
            extra_responses: List of additional responses (references, state updates, etc.)
            context: Optional context dictionary containing metadata
            timestamp: Unix timestamp of when the interaction occurred
        """
        pass
