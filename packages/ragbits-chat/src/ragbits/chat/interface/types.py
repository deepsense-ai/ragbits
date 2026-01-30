import warnings
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar, cast
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ragbits.agents.confirmation import ConfirmationRequest
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
    """Base class for all chat response content types.

    Extend this class to create custom response types with full type safety and validation.
    Each content type must implement the `get_type()` method to return a unique type identifier.

    Example:
        Create a custom analytics content type::

            from pydantic import Field
            from ragbits.chat.interface.types import ResponseContent, ChatResponse

            class AnalyticsContent(ResponseContent):
                \"\"\"Custom analytics data content.\"\"\"

                user_count: int = Field(..., description="Number of users")
                page_views: int = Field(..., description="Number of page views")
                avg_session_time: float = Field(..., description="Average session time in seconds")

                def get_type(self) -> str:
                    return "analytics"

            class AnalyticsResponse(ChatResponse[AnalyticsContent]):
                \"\"\"Analytics response for streaming to clients.\"\"\"

            # Use it in your chat interface:
            analytics_data = AnalyticsContent(user_count=1500, page_views=25000, avg_session_time=180.5)
            yield AnalyticsResponse(content=analytics_data)

    Notes:
        - The type identifier returned by `get_type()` should be unique and descriptive
        - All fields are automatically validated by Pydantic
        - Content is automatically serialized for transmission to clients
        - Frontend handlers can use the type identifier to determine how to render the response
    """

    @abstractmethod
    def get_type(self) -> str:  # noqa: D102, PLR6301
        """Return the type identifier for this content.

        This identifier is used by clients to determine how to handle and render the response.
        It should be a unique, descriptive string (e.g., "analytics", "chart_data", "user_profile").

        Returns:
            A unique string identifier for this content type.
        """


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


class ConfirmationRequestContent(ResponseContent):
    """Confirmation request content wrapper."""

    confirmation_request: ConfirmationRequest

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "confirmation_request"


class ErrorContent(ResponseContent):
    """Error content wrapper for displaying error messages to users."""

    message: str

    def get_type(self) -> str:  # noqa: D102, PLR6301
        return "error"


class ChatResponseType(str, Enum):
    """Types of responses that can be returned by the chat interface.

    .. deprecated:: 1.4.0
        Use specific response classes (TextResponse, ReferenceResponse, etc.) instead.
        This enum is kept for backward compatibility and will be removed in version 2.0.0.

        Migration guide:

        Old code::

            if response.type == ChatResponseType.TEXT:
                print(response.as_text())

        New code::

            if isinstance(response, TextResponse):
                print(response.content.text)
    """

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
    TODO_ITEM = "todo_item"
    CONFIRMATION_REQUEST = "confirmation_request"
    ERROR = "error"


class ChatContext(BaseModel):
    """Represents the context of a chat conversation."""

    conversation_id: str | None = None
    message_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    user: User | None = None
    session_id: str | None = None
    tool_confirmations: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of confirmed/declined tool executions from the frontend. Each entry has 'confirmation_id' "
        "and 'confirmed' (bool)",
    )
    timezone: str | None = Field(
        default=None,
        description="User's timezone in IANA format (e.g., 'Europe/Warsaw', 'America/New_York')",
    )
    model_config = ConfigDict(extra="allow")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        """Validate that timezone is a valid IANA timezone identifier."""
        if v is not None and v not in available_timezones():
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone.")
        return v


# Generic type variable for content, bounded to ResponseContent
ChatResponseContentT = TypeVar("ChatResponseContentT", bound=ResponseContent)


class ChatResponse(BaseModel, ABC, Generic[ChatResponseContentT]):
    r"""Base class for all chat responses with typed, validated content.

    This generic base class provides type-safe response handling. Extend it with your custom
    ResponseContent type to create application-specific responses that integrate seamlessly
    with the chat interface.

    The generic approach provides several benefits:
        - Full type safety and IDE autocomplete for response content
        - Automatic validation through Pydantic
        - Clear separation between different response types
        - Easy extension without modifying core code

    Example:
        Create a custom user profile response::

            from pydantic import Field
            from ragbits.chat.interface.types import ResponseContent, ChatResponse

            class UserProfileContent(ResponseContent):
                \"\"\"User profile information.\"\"\"

                name: str = Field(..., min_length=1)
                age: int = Field(..., ge=0, le=150)
                email: str = Field(..., pattern=r".+@.+\\..+")
                bio: str | None = None

                def get_type(self) -> str:
                    return "user_profile"

            class UserProfileResponse(ChatResponse[UserProfileContent]):
                \"\"\"User profile response for streaming to clients.\"\"\"

            # Use in your ChatInterface.chat() method:
            async def chat(self, message: str, history: list, context: ChatContext) -> AsyncGenerator:
                # ... process message ...

                profile = UserProfileContent(
                    name="Alice Johnson",
                    age=28,
                    email="alice@example.com",
                    bio="Software engineer passionate about AI"
                )
                yield UserProfileResponse(content=profile)

        Create a chart data response::

            class ChartDataContent(ResponseContent):
                \"\"\"Chart visualization data.\"\"\"

                labels: list[str]
                values: list[float]
                chart_type: Literal["line", "bar", "pie"]

                def get_type(self) -> str:
                    return "chart_data"

            class ChartDataResponse(ChatResponse[ChartDataContent]):
                \"\"\"Chart data response.\"\"\"

            # Use it:
            chart = ChartDataContent(
                labels=["Q1", "Q2", "Q3", "Q4"],
                values=[100.5, 150.2, 120.0, 180.3],
                chart_type="line"
            )
            yield ChartDataResponse(content=chart)

    Attributes:
        content: The typed content for this response. Type is validated automatically.
    """

    content: ChatResponseContentT

    def get_type(self) -> str:  # noqa: D102, PLR6301
        """Return the response type identifier from content.

        This method delegates to the content's get_type() method, ensuring consistent
        type identification across the response hierarchy.

        Returns:
            The unique type identifier for this response.
        """
        return self.content.get_type()

    @property
    def type(self) -> ChatResponseType:
        """Return the response type as ChatResponseType enum.

        .. deprecated:: 1.4.0
            Use isinstance() checks instead of comparing .type attribute.
            This property is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The ChatResponseType enum value for this response.
        """
        warnings.warn(
            "The 'type' property is deprecated. Use isinstance() checks instead "
            "(e.g., isinstance(response, TextResponse)). "
            "This property will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        type_str = self.get_type()
        return ChatResponseType(type_str)

    def as_text(self) -> str | None:
        """Return the content as text if this is a text response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Example (deprecated)::

            if text := response.as_text():
                print(f"Got text: {text}")

        Example (new approach)::

            if isinstance(response, TextResponse):
                print(f"Got text: {response.content.text}")

        Returns:
            The text content if this is a TextResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_text()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, TextResponse): text = response.content.text). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, TextContent):
            return self.content.text
        return None

    def as_reference(self) -> Reference | None:
        """Return the content as Reference if this is a reference response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Example (deprecated)::

            if ref := response.as_reference():
                print(f"Got reference: {ref.title}")

        Example (new approach)::

            if isinstance(response, ReferenceResponse):
                print(f"Got reference: {response.content.title}")

        Returns:
            The Reference content if this is a ReferenceResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_reference()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ReferenceResponse): ref = response.content). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, Reference):
            return cast(Reference, self.content)
        return None

    def as_state_update(self) -> StateUpdate | None:
        """Return the content as StateUpdate if this is a state update, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Example (deprecated)::

            if state_update := response.as_state_update():
                verify_state(state_update)

        Example (new approach)::

            if isinstance(response, StateUpdateResponse):
                verify_state(response.content)

        Returns:
            The StateUpdate content if this is a StateUpdateResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_state_update()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, StateUpdateResponse): state = response.content). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, StateUpdate):
            return cast(StateUpdate, self.content)
        return None

    def as_conversation_id(self) -> str | None:
        """Return the conversation ID if this is a conversation ID response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The conversation ID if this is a ConversationIdResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_conversation_id()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ConversationIdResponse): id = response.content.conversation_id). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, ConversationIdContent):
            return self.content.conversation_id
        return None

    def as_live_update(self) -> LiveUpdate | None:
        """Return the content as LiveUpdate if this is a live update, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Example (deprecated)::

            if live_update := response.as_live_update():
                print(f"Got live update: {live_update.content.label}")

        Example (new approach)::

            if isinstance(response, LiveUpdateResponse):
                print(f"Got live update: {response.content.content.label}")

        Returns:
            The LiveUpdate content if this is a LiveUpdateResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_live_update()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, LiveUpdateResponse): update = response.content). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, LiveUpdate):
            return cast(LiveUpdate, self.content)
        return None

    def as_followup_messages(self) -> list[str] | None:
        """Return the content as list of strings if this is a followup messages response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Example (deprecated)::

            if followup_messages := response.as_followup_messages():
                print(f"Got followup messages: {followup_messages}")

        Example (new approach)::

            if isinstance(response, FollowupMessagesResponse):
                print(f"Got followup messages: {response.content.messages}")

        Returns:
            The followup messages if this is a FollowupMessagesResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_followup_messages()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, FollowupMessagesResponse): messages = response.content.messages). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, FollowupMessagesContent):
            return self.content.messages
        return None

    def as_image(self) -> Image | None:
        """Return the content as Image if this is an image response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The Image content if this is an ImageResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_image()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ImageResponse): image = response.content). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, Image):
            return cast(Image, self.content)
        return None

    def as_clear_message(self) -> None:
        """Return the content of clear_message response, which is None.

        .. deprecated:: 1.4.0
            Use isinstance() checks instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            None if this is a ClearMessageResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_clear_message()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ClearMessageResponse): ...). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, ClearMessageContent):
            return None
        return None

    def as_usage(self) -> dict[str, MessageUsage] | None:
        """Return the content as dict from model name to Usage if this is an usage response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The usage dict if this is a UsageResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_usage()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, UsageResponse): usage = response.content.usage). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, UsageContent):
            return self.content.usage
        return None

    def as_task(self) -> Task | None:
        """Return the content as Task if this is an todo_item response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The Task content if this is a TodoItemResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_task()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, TodoItemResponse): task = response.content.task). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, TodoItemContent):
            return self.content.task
        return None

    def as_confirmation_request(self) -> ConfirmationRequest | None:
        """Return the content as ConfirmationRequest if this is a confirmation request, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The ConfirmationRequest content if this is a ConfirmationRequestResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_confirmation_request()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ConfirmationRequestResponse): "
            "req = response.content.confirmation_request). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, ConfirmationRequestContent):
            return self.content.confirmation_request
        return None

    def as_conversation_summary(self) -> str | None:
        """Return the content as string if this is an conversation summary response, else None.

        .. deprecated:: 1.4.0
            Use isinstance() checks and typed access instead.
            This method is kept for backward compatibility and will be removed in version 2.0.0.

        Returns:
            The conversation summary if this is a ConversationSummaryResponse, None otherwise.
        """
        warnings.warn(
            "The 'as_conversation_summary()' method is deprecated. Use isinstance() checks instead "
            "(e.g., if isinstance(response, ConversationSummaryResponse): summary = response.content.summary). "
            "This method will be removed in version 2.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(self.content, ConversationSummaryContent):
            return self.content.summary
        return None


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


class ConfirmationRequestResponse(ChatResponse[ConfirmationRequestContent]):
    """Confirmation request response."""


class ErrorResponse(ChatResponse[ErrorContent]):
    """Error response for displaying error messages to users."""


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
    | ConfirmationRequestResponse
    | ErrorResponse
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
    OAUTH2 = "oauth2"


class OAuth2ProviderConfig(BaseModel):
    """Configuration for an OAuth2 provider including visual configuration."""

    name: str = Field(..., description="Provider name (e.g., 'discord')")
    display_name: str | None = Field(None, description="Display name for the provider (e.g., 'Discord')")
    color: str | None = Field(None, description="Brand color for the provider (e.g., '#5865F2')")
    button_color: str | None = Field(None, description="Button background color (defaults to color)")
    text_color: str | None = Field(None, description="Button text color (defaults to white)")
    icon_svg: str | None = Field(None, description="SVG icon as string")


class AuthenticationConfig(BaseModel):
    """Configuration for authentication."""

    enabled: bool = Field(default=False, description="Enable/disable authentication")
    auth_types: list[AuthType] = Field(default=[], description="List of available authentication types")
    oauth2_providers: list[OAuth2ProviderConfig] = Field(
        default_factory=list, description="List of available OAuth2 providers"
    )


class ConfigResponse(BaseModel):
    """Configuration response from the API."""

    feedback: FeedbackConfig = Field(..., description="Feedback configuration")
    customization: UICustomization | None = Field(default=None, description="UI customization")
    user_settings: UserSettings = Field(default_factory=UserSettings, description="User settings")
    supports_upload: bool = Field(default=False, description="Flag indicating whether API supports file upload")
    debug_mode: bool = Field(default=False, description="Debug mode flag")
    conversation_history: bool = Field(default=False, description="Flag to enable conversation history")
    show_usage: bool = Field(default=False, description="Flag to enable usage statistics")
    authentication: AuthenticationConfig = Field(..., description="Authentication configuration")
