from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from typing import Any

from ..interface.types import ChatResponse

__all__ = [
    "AsyncChatClientBase",
    "AsyncConversationBase",
    "SyncChatClientBase",
    "SyncConversationBase",
]


class SyncChatClientBase(ABC):
    """Abstract base class for synchronous chat clients."""

    @abstractmethod
    def new_conversation(self) -> SyncConversationBase:
        """Create and return a new conversation instance."""

    @abstractmethod
    def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""

    @abstractmethod
    def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""


class AsyncChatClientBase(ABC):
    """Abstract base class for asynchronous chat clients."""

    @abstractmethod
    def new_conversation(self) -> AsyncConversationBase:
        """Create and return a new conversation instance."""

    @abstractmethod
    async def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""

    @abstractmethod
    def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""


class SyncConversationBase(ABC):
    """Abstract base class for **synchronous** chat conversations.

    Concrete conversation implementations (e.g. :class:`ragbits.chat.clients.conversation.Conversation`)
    should inherit from this class to ensure a consistent public interface.  The
    API mirrors :class:`SyncChatClientBase` but represents a single, *stateful*
    conversation rather than a stateless client.
    """

    @abstractmethod
    def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""

    @abstractmethod
    def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> Generator[ChatResponse, None, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""

    @abstractmethod
    def stop(self) -> None:
        """Abort a currently running stream (if any)."""


class AsyncConversationBase(ABC):
    """Abstract base class for **asynchronous** chat conversations."""

    @abstractmethod
    async def run(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ChatResponse]:
        """Send *message* and return **all** response chunks."""

    @abstractmethod
    def run_streaming(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Send *message* and yield streaming :class:`ChatResponse` chunks."""

    @abstractmethod
    async def stop(self) -> None:
        """Abort a currently running stream (if any)."""
