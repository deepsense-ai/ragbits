from enum import Enum
from typing import Annotated, Any, Literal, cast, get_args, get_origin, overload

from pydantic import BaseModel, ConfigDict, Field, RootModel

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


_CHAT_RESPONSE_REGISTRY: dict[ChatResponseType, type[BaseModel]] = {}


class ChatResponseBase(BaseModel):
    """Base class for all ChatResponse variants with auto-registration."""

    type: ChatResponseType

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        type_ann = cls.model_fields["type"].annotation
        origin = get_origin(type_ann)
        value = get_args(type_ann)[0] if origin is Literal else getattr(cls, "type", None)

        if value is None:
            raise ValueError(f"Cannot determine ChatResponseType for {cls.__name__}")

        _CHAT_RESPONSE_REGISTRY[value] = cls


class TextChatResponse(ChatResponseBase):
    """Represents text chat response"""

    type: Literal[ChatResponseType.TEXT] = ChatResponseType.TEXT
    content: str


class ReferenceChatResponse(ChatResponseBase):
    """Represents reference chat response"""

    type: Literal[ChatResponseType.REFERENCE] = ChatResponseType.REFERENCE
    content: Reference


class StateUpdateChatResponse(ChatResponseBase):
    """Represents state update chat response"""

    type: Literal[ChatResponseType.STATE_UPDATE] = ChatResponseType.STATE_UPDATE
    content: StateUpdate


class ConversationIdChatResponse(ChatResponseBase):
    """Represents conversation_id chat response"""

    type: Literal[ChatResponseType.CONVERSATION_ID] = ChatResponseType.CONVERSATION_ID
    content: str


class LiveUpdateChatResponse(ChatResponseBase):
    """Represents live update chat response"""

    type: Literal[ChatResponseType.LIVE_UPDATE] = ChatResponseType.LIVE_UPDATE
    content: LiveUpdate


class FollowupMessagesChatResponse(ChatResponseBase):
    """Represents followup messages chat response"""

    type: Literal[ChatResponseType.FOLLOWUP_MESSAGES] = ChatResponseType.FOLLOWUP_MESSAGES
    content: list[str]


class ImageChatResponse(ChatResponseBase):
    """Represents image chat response"""

    type: Literal[ChatResponseType.IMAGE] = ChatResponseType.IMAGE
    content: Image


class ClearMessageChatResponse(ChatResponseBase):
    """Represents clear message event"""

    type: Literal[ChatResponseType.CLEAR_MESSAGE] = ChatResponseType.CLEAR_MESSAGE
    content: None = None


class UsageChatResponse(ChatResponseBase):
    """Represents usage chat response"""

    type: Literal[ChatResponseType.USAGE] = ChatResponseType.USAGE
    content: dict[str, MessageUsage]


class MessageIdChatResponse(ChatResponseBase):
    """Represents message_id chat response"""

    type: Literal[ChatResponseType.MESSAGE_ID] = ChatResponseType.MESSAGE_ID
    content: str


class ChunkedContentChatResponse(ChatResponseBase):
    """Represents chunked_content event that contains chunked event of different type"""

    type: Literal[ChatResponseType.CHUNKED_CONTENT] = ChatResponseType.CHUNKED_CONTENT
    content: ChunkedContent


ChatResponseUnion = Annotated[
    TextChatResponse
    | ReferenceChatResponse
    | StateUpdateChatResponse
    | ConversationIdChatResponse
    | LiveUpdateChatResponse
    | FollowupMessagesChatResponse
    | ImageChatResponse
    | ClearMessageChatResponse
    | UsageChatResponse
    | MessageIdChatResponse
    | ChunkedContentChatResponse,
    Field(discriminator="type"),
]


class ChatResponse(RootModel[ChatResponseUnion]):
    """Container for different types of chat responses."""

    root: ChatResponseUnion

    @property
    def content(self) -> object:
        """Returns content of a response, use dedicated `as_*` methods to get type hints."""
        return self.root.content

    @property
    def type(self) -> ChatResponseType:
        """Returns type of the ChatResponse"""
        return self.root.type

    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.TEXT],
        content: str,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.REFERENCE],
        content: Reference,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.STATE_UPDATE],
        content: StateUpdate,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.CONVERSATION_ID],
        content: str,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.LIVE_UPDATE],
        content: LiveUpdate,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.FOLLOWUP_MESSAGES],
        content: list[str],
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.IMAGE],
        content: Image,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.CLEAR_MESSAGE],
        content: None,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.USAGE],
        content: dict[str, MessageUsage],
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.MESSAGE_ID],
        content: str,
    ) -> None: ...
    @overload
    def __init__(
        self,
        type: Literal[ChatResponseType.CHUNKED_CONTENT],
        content: ChunkedContent,
    ) -> None: ...
    def __init__(
        self,
        type: ChatResponseType,
        content: Any,
    ) -> None:
        """
        Backward-compatible constructor.

        Allows creating a ChatResponse directly with:
            ChatResponse(type=ChatResponseType.TEXT, content="hello")
        """
        model_cls = _CHAT_RESPONSE_REGISTRY.get(type)
        if model_cls is None:
            raise ValueError(f"Unsupported ChatResponseType: {type}")

        model_instance = model_cls(type=type, content=content)
        super().__init__(root=cast(ChatResponseUnion, model_instance))

    def as_text(self) -> str | None:
        """
        Return the content as text if this is a text response, else None.

        Example:
            if text := response.as_text():
                print(f"Got text: {text}")
        """
        return self.root.content if isinstance(self.root, TextChatResponse) else None

    def as_reference(self) -> Reference | None:
        """
        Return the content as Reference if this is a reference response, else None.

        Example:
            if ref := response.as_reference():
                print(f"Got reference: {ref.title}")
        """
        return self.root.content if isinstance(self.root, ReferenceChatResponse) else None

    def as_state_update(self) -> StateUpdate | None:
        """
        Return the content as StateUpdate if this is a state update, else None.

        Example:
            if state_update := response.as_state_update():
                state = verify_state(state_update)
        """
        return self.root.content if isinstance(self.root, StateUpdateChatResponse) else None

    def as_conversation_id(self) -> str | None:
        """
        Return the content as ConversationID if this is a conversation id, else None.
        """
        return self.root.content if isinstance(self.root, ConversationIdChatResponse) else None

    def as_live_update(self) -> LiveUpdate | None:
        """
        Return the content as LiveUpdate if this is a live update, else None.

        Example:
            if live_update := response.as_live_update():
                print(f"Got live update: {live_update.content.label}")
        """
        return self.root.content if isinstance(self.root, LiveUpdateChatResponse) else None

    def as_followup_messages(self) -> list[str] | None:
        """
        Return the content as list of strings if this is a followup messages response, else None.

        Example:
            if followup_messages := response.as_followup_messages():
                print(f"Got followup messages: {followup_messages}")
        """
        return self.root.content if isinstance(self.root, FollowupMessagesChatResponse) else None

    def as_image(self) -> Image | None:
        """
        Return the content as Image if this is an image response, else None.
        """
        return self.root.content if isinstance(self.root, ImageChatResponse) else None

    def as_clear_message(self) -> None:
        """
        Return the content of clear_message response, which is None
        """
        return self.root.content if isinstance(self.root, ClearMessageChatResponse) else None

    def as_usage(self) -> dict[str, MessageUsage] | None:
        """
        Return the content as dict from model name to Usage if this is an usage response, else None
        """
        return self.root.content if isinstance(self.root, UsageChatResponse) else None


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
