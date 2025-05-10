from abc import ABC, abstractmethod

from ragbits.chat.interface.types import ChatResponse


class HistoryPersistenceStrategy(ABC):
    """Base class for history persistence strategies."""

    @abstractmethod
    async def save_interaction(
        self,
        message: str,
        response: str,
        extra_responses: list[ChatResponse],
        context: dict | None,
        timestamp: float,
    ) -> None:
        """
        Save a chat interaction including the input message and responses.

        Args:
            message: The user's input message
            response: The main response (already aggregated by decorator)
            extra_responses: List of additional responses
            context: Optional context dictionary
            timestamp: Unix timestamp of when the interaction occurred
        """
        pass
