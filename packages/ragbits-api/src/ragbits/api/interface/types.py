from enum import Enum
from typing import cast

from pydantic import BaseModel


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


class ChatResponseType(str, Enum):
    """Types of responses that can be returned by the chat interface."""

    TEXT = "text"
    REFERENCE = "reference"


class ChatResponse(BaseModel):
    """Container for different types of chat responses."""

    type: ChatResponseType
    content: str | Reference

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
