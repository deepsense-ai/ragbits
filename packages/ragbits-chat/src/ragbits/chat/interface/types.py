from enum import Enum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Defines the role of the message sender in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Represents a single message in the conversation history."""

    role: MessageRole
    content: str


class Reference(BaseModel):
    """Represents a document used as reference for the response."""

    title: str
    content: str
    url: str | None = None


class StateUpdate(BaseModel):
    """Represents an update to conversation state."""

    state: dict[str, Any]
    signature: str


class ChatResponseType(str, Enum):
    """Types of responses that can be returned by the chat interface."""

    TEXT = "text"
    REFERENCE = "reference"
    STATE_UPDATE = "state_update"
    MESSAGE_ID = "message_id"
    CONVERSATION_ID = "conversation_id"


class ChatResponse(BaseModel):
    """Container for different types of chat responses."""

    type: ChatResponseType
    content: str | Reference | StateUpdate

    def as_text(self) -> str | None:
        """
        Return the content as text if this is a text response, else None.

        Example:
            if text := response.as_text():
                print(f"Got text: {text}")
        """
        return str(self.content) if self.type == ChatResponseType.TEXT else None

    def as_reference(self) -> Reference | None:
        """
        Return the content as Reference if this is a reference response, else None.

        Example:
            if ref := response.as_reference():
                print(f"Got reference: {ref.title}")
        """
        return cast(Reference, self.content) if self.type == ChatResponseType.REFERENCE else None

    def as_state_update(self) -> StateUpdate | None:
        """
        Return the content as StateUpdate if this is a state update, else None.

        Example:
            if state_update := response.as_state_update():
                state = verify_state(state_update)
        """
        return cast(StateUpdate, self.content) if self.type == ChatResponseType.STATE_UPDATE else None


class ChatContext(BaseModel):
    """Represents the context of a chat conversation."""

    conversation_id: str | None = None
    message_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")
