from enum import Enum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from ragbits.chat.auth.types import User
from ragbits.chat.interface.forms import UserSettings
from ragbits.chat.interface.ui_customization import UICustomization
from ragbits.core.llms.base import Usage


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


class Image(BaseModel):
    """Represents an image in the conversation."""

    id: str
    url: str


class ChunkedContent(BaseModel):
    """Represents a chunk of large content being transmitted."""

    id: str
    content_type: str
    chunk_index: int
    total_chunks: int
    mime_type: str
    data: str


class MessageUsage(BaseModel):
    """Represents usage for a message. Reflects `Usage` computed properties."""

    n_requests: int
    estimated_cost: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @classmethod
    def from_usage(cls, usage: Usage) -> "MessageUsage":
        """
        Create a MessageUsage object from Usage.

        Args:
            usage: Usage object to be transformed.

        Returns:
            The corresponding MessageUsage.
        """
        return cls(
            completion_tokens=usage.completion_tokens,
            estimated_cost=usage.estimated_cost,
            n_requests=usage.n_requests,
            prompt_tokens=usage.prompt_tokens,
            total_tokens=usage.total_tokens,
        )


class ChatResponseType(str, Enum):
    """Types of responses that can be returned by the chat interface."""

    TEXT = "text"
    REFERENCE = "reference"
    STATE_UPDATE = "state_update"
    MESSAGE_ID = "message_id"
    CONVERSATION_ID = "conversation_id"
    CONVERSATION_SUMMARY = "conversation_summary"
    LIVE_UPDATE = "live_update"
    FOLLOWUP_MESSAGES = "followup_messages"
    IMAGE = "image"
    CHUNKED_CONTENT = "chunked_content"
    CLEAR_MESSAGE = "clear_message"
    USAGE = "usage"


class ChatContext(BaseModel):
    """Represents the context of a chat conversation."""

    conversation_id: str | None = None
    message_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    user: User | None = None
    session_id: str | None = None
    model_config = ConfigDict(extra="allow")


class ChatResponse(BaseModel):
    """Container for different types of chat responses."""

    type: ChatResponseType
    content: (
        str | Reference | StateUpdate | LiveUpdate | list[str] | Image | dict[str, MessageUsage] | ChunkedContent | None
    )

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

    def as_image(self) -> Image | None:
        """
        Return the content as Image if this is an image response, else None.
        """
        return cast(Image, self.content) if self.type == ChatResponseType.IMAGE else None

    def as_clear_message(self) -> None:
        """
        Return the content of clear_message response, which is None
        """
        return cast(None, self.content)

    def as_usage(self) -> dict[str, MessageUsage] | None:
        """
        Return the content as dict from model name to Usage if this is an usage response, else None
        """
        return cast(dict[str, MessageUsage], self.content) if self.type == ChatResponseType.USAGE else None

    def as_conversation_summary(self) -> str | None:
        """
        Return the content as string if this is an conversation summary response, else None
        """
        return cast(str, self.content) if self.type == ChatResponseType.CONVERSATION_SUMMARY else None


class ChatMessageRequest(BaseModel):
    """Client-side chat request interface."""

    message: str = Field(..., description="The current user message")
    history: list["Message"] = Field(default_factory=list, description="Previous message history")
    context: dict[str, Any] = Field(default_factory=dict, description="User context information")


class FeedbackType(str, Enum):
    """Feedback types for user feedback."""

    LIKE = "like"
    DISLIKE = "dislike"


class FeedbackResponse(BaseModel):
    """Response from feedback submission."""

    status: str = Field(..., description="Status of the feedback submission")


class FeedbackRequest(BaseModel):
    """
    Request body for feedback submission
    """

    message_id: str = Field(..., description="ID of the message receiving feedback")
    feedback: FeedbackType = Field(..., description="Type of feedback (like or dislike)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Additional feedback details")


class FeedbackItem(BaseModel):
    """Individual feedback configuration (like/dislike)."""

    enabled: bool = Field(..., description="Whether this feedback type is enabled")
    form: dict[str, Any] | None = Field(..., description="Form schema for this feedback type")


class FeedbackConfig(BaseModel):
    """Feedback configuration containing like and dislike settings."""

    like: FeedbackItem = Field(..., description="Like feedback configuration")
    dislike: FeedbackItem = Field(..., description="Dislike feedback configuration")


class AuthType(str, Enum):
    """Defines the available authentication types."""

    CREDENTIALS = "credentials"


class AuthenticationConfig(BaseModel):
    """Configuration for authentication."""

    enabled: bool = Field(default=False, description="Enable/disable authentication")
    auth_types: list[AuthType] = Field(default=[], description="List of available authentication types")


class ConfigResponse(BaseModel):
    """Configuration response from the API."""

    feedback: FeedbackConfig = Field(..., description="Feedback configuration")
    customization: UICustomization | None = Field(default=None, description="UI customization")
    user_settings: UserSettings = Field(default_factory=UserSettings, description="User settings")
    debug_mode: bool = Field(default=False, description="Debug mode flag")
    conversation_history: bool = Field(default=False, description="Flag to enable conversation history")
    show_usage: bool = Field(default=False, description="Flag to enable usage statistics")
    authentication: AuthenticationConfig = Field(..., description="Authentication configuration")
