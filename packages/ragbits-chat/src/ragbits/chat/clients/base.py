from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from typing import Any

from .types import ChatResponse

__all__ = [
    "AsyncChatClientBase",
    "SyncChatClientBase",
]


class SyncChatClientBase(ABC):
    """Abstract base class for synchronous chat clients."""

    @abstractmethod
    def new_conversation(self) -> None:
        """Start a fresh conversation, resetting local state."""

    @abstractmethod
    def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Send *message* and return the final assistant reply."""

    @abstractmethod
    def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""

    @abstractmethod
    def stop(self) -> None:
        """Abort a currently running request (if any)."""


class AsyncChatClientBase(ABC):
    """Abstract base class for asynchronous chat clients."""

    @abstractmethod
    def new_conversation(self) -> None:
        """Start a fresh conversation, resetting local state."""

    @abstractmethod
    async def ask(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Send *message* and return the final assistant reply."""

    @abstractmethod
    async def send_message(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""

    @abstractmethod
    async def stop(self) -> None:
        """Abort a currently running request (if any)."""
