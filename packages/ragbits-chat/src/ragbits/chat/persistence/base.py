from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from ragbits.chat.interface.types import ChatContext, ChatResponse


class HistoryPersistenceStrategy(ABC):
    """Base class for history persistence strategies.

    Implementations are responsible for storing chat interactions. Strategies
    that additionally know about conversation identity and ownership should
    override the optional listing methods below so that higher-level features
    (e.g. conversation sharing) can be built on top of them.
    """

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
            message: The user's input message
            response: The main response text
            extra_responses: List of additional responses (references, state updates, etc.)
            context: Optional context dictionary containing metadata
            timestamp: Unix timestamp of when the interaction occurred
        """

    async def get_conversation_interactions(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return all interactions for a conversation, ordered chronologically.

        Implementations that support conversation retrieval must override this
        method. The default implementation raises `NotImplementedError` so that
        strategies without retrieval capability fail loudly.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support conversation retrieval")

    async def list_conversations(self, user_id: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List conversations owned by a user, ordered by creation time descending.

        Implementations that know about conversation ownership must override
        this method. Each returned dict should contain at least ``id`` and
        ``created_at`` keys.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support listing conversations")

    async def get_conversation_summaries(self, conversation_ids: list[str]) -> dict[str, str]:  # noqa: ARG002, PLR6301
        """Return a display summary for each requested conversation.

        Implementations that support conversation listing should return a dict
        mapping conversation id to a short summary string. Summaries should
        reflect the latest ``ConversationSummaryResponse`` yielded by the
        ``ChatInterface`` during the conversation when one is available; for
        conversations without one, a sensible fallback (such as a truncated
        first user message) is acceptable. The default implementation returns
        an empty dict so that summaries remain optional.
        """
        return {}

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its interactions.

        Returns True when a conversation was deleted. Implementations that do
        not support deletion should override this and raise ``NotImplementedError``.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support conversation deletion")

    async def get_conversation_owner(self, conversation_id: str) -> str | None:  # noqa: ARG002, PLR6301
        """Return the owner user_id for a conversation, or None when unknown.

        Implementations without ownership tracking should leave this default,
        which returns None to signal that ownership cannot be established.
        """
        return None


class SharePersistenceStrategy(ABC):
    """Base class for conversation share persistence strategies.

    Implementations are responsible for storing share records that map a
    conversation to a set of recipients (user identifiers). Recipients may be
    represented by user_id, username, or email; normalisation is the
    responsibility of the persistence layer.
    """

    @abstractmethod
    async def set_shares(
        self,
        conversation_id: str,
        owner_id: str,
        recipients: list[str],
    ) -> list[dict[str, Any]]:
        """Create (or re-enable previously hidden) share records.

        Args:
            conversation_id: The conversation to share.
            owner_id: Identifier of the conversation owner.
            recipients: Recipient identifiers to grant access to.

        Returns:
            The resulting share rows for the requested recipients.
        """

    @abstractmethod
    async def get_shares(self, conversation_id: str, owner_id: str) -> list[dict[str, Any]]:
        """Return active (non-hidden) share rows owned by ``owner_id``."""

    @abstractmethod
    async def remove_shares(
        self,
        conversation_id: str,
        owner_id: str,
        recipients: list[str],
    ) -> None:
        """Delete share rows for the given recipients."""

    @abstractmethod
    async def list_shared_with_me(
        self,
        user_identifiers: Sequence[str],
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return conversations shared with the user, newest first.

        Args:
            user_identifiers: All identifiers the user can be addressed by
                (e.g. user_id, username, email).
            limit: Maximum number of results.
            offset: Number of results to skip.
        """

    @abstractmethod
    async def can_access(self, conversation_id: str, user_identifiers: Sequence[str]) -> bool:
        """Return True if any of ``user_identifiers`` has active access."""

    @abstractmethod
    async def hide_share(self, conversation_id: str, user_identifiers: Sequence[str]) -> bool:
        """Soft-delete the share for the recipient. Returns True when a row was updated."""
