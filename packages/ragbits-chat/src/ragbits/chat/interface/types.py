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


class LiveUpdateType(str, Enum):
    """Types of live update events."""

    START = "START"
    FINISH = "FINISH"


class LiveUpdateContent(BaseModel):
    """Represents content of a live update."""

    label: str
    description: str | None


class LiveUpdate(BaseModel):
    """Represents an live update performed by an agent."""

    update_id: str
    type: LiveUpdateType
    content: LiveUpdateContent


class ChatResponseType(str, Enum):
    """Types of responses that can be returned by the chat interface."""

    TEXT = "text"
    REFERENCE = "reference"
    STATE_UPDATE = "state_update"
    MESSAGE_ID = "message_id"
    CONVERSATION_ID = "conversation_id"
    LIVE_UPDATE = "live_update"
    FOLLOWUP_MESSAGES = "followup_messages"


class ChatResponse(BaseModel):
    """Container for different types of chat responses."""

    type: ChatResponseType
    content: str | Reference | StateUpdate | LiveUpdate | list[str]

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

    def as_conversation_id(self) -> str | None:
        """
        Return the content as ConversationID if this is a conversation id, else None.
        """
        return cast(str, self.content) if self.type == ChatResponseType.CONVERSATION_ID else None

    def as_live_update(self) -> LiveUpdate | None:
        """
        Return the content as LiveUpdate if this is a live update, else None.

        Example:
            if live_update := response.as_live_update():
                print(f"Got live update: {live_update.content.label}")
        """
        return cast(LiveUpdate, self.content) if self.type == ChatResponseType.LIVE_UPDATE else None

    def as_followup_messages(self) -> list[str] | None:
        """
        Return the content as list of strings if this is a followup messages response, else None.

        Example:
            if followup_messages := response.as_followup_messages():
                print(f"Got followup messages: {followup_messages}")
        """
        return cast(list[str], self.content) if self.type == ChatResponseType.FOLLOWUP_MESSAGES else None


class ChatContext(BaseModel):
    """Represents the context of a chat conversation."""

    conversation_id: str | None = None
    message_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")
