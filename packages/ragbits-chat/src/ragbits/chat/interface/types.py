from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from ragbits.agents.tools.todo import Task
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
    extra: dict[str, Any] | None = Field(default=None, description="Extra information about the message")


class ResponseContent(BaseModel, ABC):
    """Base class for all chat response content types."""

    @abstractmethod
    def get_type(self) -> str:  # noqa: D102, PLR6301
        """Return the type identifier for this content."""


class Reference(ResponseContent):
    """Represents a document used as reference for the response."""

    title: str
    content: str
    url: str | None = None

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "reference"


class StateUpdate(ResponseContent):
    """Represents an update to conversation state."""

    state: dict[str, Any]
    signature: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "state_update"


class LiveUpdateType(str, Enum):
    """Types of live update events."""

    START = "START"
    FINISH = "FINISH"


class LiveUpdateContent(BaseModel):
    """Represents content of a live update."""

    label: str
    description: str | None


class LiveUpdate(ResponseContent):
    """Represents an live update performed by an agent."""

    update_id: str
    type: LiveUpdateType
    content: LiveUpdateContent

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "live_update"


class Image(ResponseContent):
    """Represents an image in the conversation."""

    id: str
    url: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "image"


class ChunkedContent(ResponseContent):
    """Represents a chunk of large content being transmitted."""

    id: str
    content_type: str
    chunk_index: int
    total_chunks: int
    mime_type: str
    data: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "chunked_content"


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


# Wrapper content classes for primitive types
class TextContent(ResponseContent):
    """Text content wrapper."""

    text: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "text"


class MessageIdContent(ResponseContent):
    """Message ID content wrapper."""

    message_id: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "message_id"


class ConversationIdContent(ResponseContent):
    """Conversation ID content wrapper."""

    conversation_id: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "conversation_id"


class ConversationSummaryContent(ResponseContent):
    """Conversation summary content wrapper."""

    summary: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "conversation_summary"


class FollowupMessagesContent(ResponseContent):
    """Followup messages content wrapper."""

    messages: list[str]

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "followup_messages"


class UsageContent(ResponseContent):
    """Usage statistics content wrapper."""

    usage: dict[str, MessageUsage]

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "usage"


class ClearMessageContent(ResponseContent):
    """Clear message content wrapper."""

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "clear_message"


class TodoItemContent(ResponseContent):
    """Todo item content wrapper."""

    task: Task

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "todo_item"


class ChatContext(BaseModel):
    """Represents the context of a chat conversation."""

    conversation_id: str | None = None
    message_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    user: User | None = None
    session_id: str | None = None
    model_config = ConfigDict(extra="allow")


# Generic type variable for content, bounded to ResponseContent
ChatResponseContentT = TypeVar("ChatResponseContentT", bound=ResponseContent)


class ChatResponse(BaseModel, ABC, Generic[ChatResponseContentT]):
    """
    Base class for all chat responses with typed content.

    Users can extend this to create custom response types:

    Example:
        class MyAnalyticsContent(ResponseContent):
            user_count: int
            page_views: int

            def get_type(self) -> str:
                return "analytics"

        class AnalyticsResponse(ChatResponse[MyAnalyticsContent]):
            pass  # get_type() is automatically inherited!

        # Use it
        response = AnalyticsResponse(content=MyAnalyticsContent(user_count=100, page_views=500))
    """

    content: ChatResponseContentT

    def get_type(self) -> str:  # noqa: D102, PLR6301
        """Return the response type identifier from content."""
        return self.content.get_type()


class TextResponse(ChatResponse[TextContent]):
    """Text response from the chat."""


class ReferenceResponse(ChatResponse[Reference]):
    """Reference document response."""


class StateUpdateResponse(ChatResponse[StateUpdate]):
    """State update response."""


class MessageIdResponse(ChatResponse[MessageIdContent]):
    """Message ID response."""


class ConversationIdResponse(ChatResponse[ConversationIdContent]):
    """Conversation ID response."""


class ConversationSummaryResponse(ChatResponse[ConversationSummaryContent]):
    """Conversation summary response."""


class LiveUpdateResponse(ChatResponse[LiveUpdate]):
    """Live update response."""


class FollowupMessagesResponse(ChatResponse[FollowupMessagesContent]):
    """Followup messages response."""


class ImageResponse(ChatResponse[Image]):
    """Image response."""


class ChunkedContentResponse(ChatResponse[ChunkedContent]):
    """Chunked content response."""


class ClearMessageResponse(ChatResponse[ClearMessageContent]):
    """Clear message response."""


class UsageResponse(ChatResponse[UsageContent]):
    """Usage statistics response."""


class TodoItemResponse(ChatResponse[TodoItemContent]):
    """Todo item response."""


# Union type for all built-in chat responses
ChatResponseUnion = (
    TextResponse
    | ReferenceResponse
    | StateUpdateResponse
    | MessageIdResponse
    | ConversationIdResponse
    | ConversationSummaryResponse
    | LiveUpdateResponse
    | FollowupMessagesResponse
    | ImageResponse
    | ChunkedContentResponse
    | ClearMessageResponse
    | UsageResponse
    | TodoItemResponse
)


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
    """Request body for feedback submission."""

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
