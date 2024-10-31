from abc import ABC, abstractmethod
from typing import Any


class TraceHandler(ABC):
    """
    Base class for all trace handlers.
    """

    @abstractmethod
    async def on_start(self, **inputs: Any) -> None:
        """
        Log input data at the start of the event.

        Args:
            inputs: The input data.
        """

    @abstractmethod
    async def on_end(self, **outputs: Any) -> None:
        """
        Log output data at the end of the event.

        Args:
            outputs: The output data.
        """

    @abstractmethod
    async def on_error(self, error: Exception) -> None:
        """
        Log error during the event.

        Args:
            error: The error that occurred.
        """
