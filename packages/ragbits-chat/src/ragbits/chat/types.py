from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel

__all__ = [
    "ChatResponse",
    "ChatResponseType",
    "Message",
    "MessageRole",
    "Reference",
    "ServerState",
]


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Represents a single message in a chat conversation."""

    role: MessageRole
    content: str


class Reference(BaseModel):
    """Represents a reference associated with a chat response."""

    title: str
    content: str
    url: str | None = None


class ChatResponseType(str, Enum):
    """Types of chat responses."""

    TEXT = "text"
    REFERENCE = "reference"
    MESSAGE_ID = "message_id"
    CONVERSATION_ID = "conversation_id"
    STATE_UPDATE = "state_update"


class ServerState(BaseModel):
    """Represents the server-side state of a chat conversation."""

    state: dict[str, Any]
    signature: str


class _BaseChatResponse(BaseModel):
    type: ChatResponseType

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
    }


class TextChatResponse(_BaseChatResponse):
    type: Literal[ChatResponseType.TEXT] = ChatResponseType.TEXT
    content: str


class ReferenceChatResponse(_BaseChatResponse):
    type: Literal[ChatResponseType.REFERENCE] = ChatResponseType.REFERENCE
    content: Reference


class MessageIdChatResponse(_BaseChatResponse):
    type: Literal[ChatResponseType.MESSAGE_ID] = ChatResponseType.MESSAGE_ID
    content: str


class ConversationIdChatResponse(_BaseChatResponse):
    type: Literal[ChatResponseType.CONVERSATION_ID] = ChatResponseType.CONVERSATION_ID
    content: str


class StateUpdateChatResponse(_BaseChatResponse):
    type: Literal[ChatResponseType.STATE_UPDATE] = ChatResponseType.STATE_UPDATE
    content: ServerState


ChatResponse = (
    TextChatResponse
    | ReferenceChatResponse
    | MessageIdChatResponse
    | ConversationIdChatResponse
    | StateUpdateChatResponse
)


def map_history_to_messages(history: list[Message]) -> list[Message]:
    """Return a copy of *history* stripped of SYSTEM messages.

    The server does not expect system messages (they are UI-only),
    mirroring `mapHistoryToMessages` util in the TS client.
    """
    return [m for m in history if m.role is not MessageRole.SYSTEM]
