import base64
import functools
import hmac
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from typing import Any

from fastapi import UploadFile

from ragbits.agents.tools.todo import Task
from ragbits.chat.interface.summary import HeuristicSummaryGenerator, SummaryGenerator
from ragbits.chat.interface.ui_customization import UICustomization
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType
from ragbits.core.llms.base import Usage
from ragbits.core.prompt.base import ChatFormat
from ragbits.core.utils import get_secret_key

from ..metrics import ChatCounterMetric, ChatHistogramMetric
from ..persistence import HistoryPersistenceStrategy
from .forms import FeedbackConfig, UserSettings
from .types import (
    ChatContext,
    ChatResponseUnion,
    ClearMessageContent,
    ClearMessageResponse,
    ConversationIdContent,
    ConversationIdResponse,
    ConversationSummaryContent,
    ConversationSummaryResponse,
    FeedbackType,
    FollowupMessagesContent,
    FollowupMessagesResponse,
    Image,
    ImageResponse,
    LiveUpdate,
    LiveUpdateContent,
    LiveUpdateResponse,
    LiveUpdateType,
    MessageIdContent,
    MessageIdResponse,
    MessageUsage,
    Reference,
    ReferenceResponse,
    StateUpdate,
    StateUpdateResponse,
    TextContent,
    TextResponse,
    TodoItemContent,
    TodoItemResponse,
    UsageContent,
    UsageResponse,
)

logger = logging.getLogger(__name__)


def with_chat_metadata(  # noqa: PLR0915
    func: Callable[["ChatInterface", str, ChatFormat, ChatContext], AsyncGenerator[ChatResponseUnion, None]],
) -> Callable[["ChatInterface", str, ChatFormat | None, ChatContext | None], AsyncGenerator[ChatResponseUnion, None]]:
    """
    Decorator that adds message and conversation metadata to the chat method and handles history persistence.
    Generates message_id and conversation_id (if first message) and stores them in context.
    Also handles history persistence if configured.
    """

    @functools.wraps(func)
    async def wrapper(  # noqa: PLR0915
        self: "ChatInterface", message: str, history: ChatFormat | None = None, context: ChatContext | None = None
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        start_time = time.time()

        # Assure history and context are not None
        history = history or []
        context = context or ChatContext()

        # Track history length
        history_length = len(history)
        record_metric(
            ChatHistogramMetric.CHAT_HISTORY_LENGTH,
            history_length,
            metric_type=MetricType.HISTOGRAM,
            interface_class=self.__class__.__name__,
        )

        # Generate message_id if not present
        if not context.message_id:
            context.message_id = str(uuid.uuid4())
            yield MessageIdResponse(content=MessageIdContent(message_id=context.message_id))

        # Generate conversation_id if this is the first message
        is_new_conversation = False
        if not context.conversation_id:
            context.conversation_id = str(uuid.uuid4())
            is_new_conversation = True
            yield ConversationIdResponse(content=ConversationIdContent(conversation_id=context.conversation_id))

            # Track new conversation
            record_metric(
                ChatCounterMetric.CHAT_CONVERSATION_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                interface_class=self.__class__.__name__,
            )

            # Generate summary to serve as title for new conversations
            try:
                summary = await self.generate_conversation_summary(message, history, context)
                if summary:
                    yield ConversationSummaryResponse(content=ConversationSummaryContent(summary=summary))
            except Exception:
                logger.exception("Failed to generate conversation title")

        responses, main_response, extra_responses = [], "", []
        timestamp = time.time()
        response_token_count, first_token_time = 0.0, None

        try:
            async for response in func(self, message, history, context):
                responses.append(response)
                if isinstance(response, TextResponse):
                    # Record time to first token on the first TEXT response
                    if first_token_time is None and response.content.text:
                        first_token_time = time.time() - start_time
                        record_metric(
                            ChatHistogramMetric.CHAT_TIME_TO_FIRST_TOKEN,
                            first_token_time,
                            metric_type=MetricType.HISTOGRAM,
                            interface_class=self.__class__.__name__,
                            is_new_conversation=str(is_new_conversation),
                            history_length=str(history_length),
                        )

                    main_response = main_response + response.content.text
                    # Rough token estimation (words * 1.3 for subword tokens)
                    response_token_count += len(response.content.text.split()) * 1.3
                else:
                    extra_responses.append(response)
                yield response

            # Track successful message processing
            record_metric(
                ChatCounterMetric.CHAT_MESSAGE_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                interface_class=self.__class__.__name__,
                is_new_conversation=str(is_new_conversation),
            )

            # Track response tokens
            if response_token_count > 0:
                record_metric(
                    ChatHistogramMetric.CHAT_RESPONSE_TOKENS,
                    response_token_count,
                    metric_type=MetricType.HISTOGRAM,
                    interface_class=self.__class__.__name__,
                )

        except Exception as e:
            # Track errors
            record_metric(
                ChatCounterMetric.CHAT_ERROR_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                interface_class=self.__class__.__name__,
                error_type=type(e).__name__,
            )
            raise
        finally:
            # Track request duration
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.CHAT_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                interface_class=self.__class__.__name__,
                is_new_conversation=str(is_new_conversation),
                history_length=str(history_length),
            )

            if self.history_persistence:
                await self.history_persistence.save_interaction(
                    message=message,
                    response=main_response,
                    extra_responses=extra_responses,
                    context=context,
                    timestamp=timestamp,
                )

    return wrapper


class ChatInterface(ABC):
    """
    Base interface for chat implementations.

    This interface defines the core functionality required for a chat service
    that can return various types of responses such as:

    * Text: Regular text responses streamed chunk by chunk
    * References: Source documents used to generate the answer
    * State updates: Updates to the conversation state

    Attributes:
        upload_handler: Optional async callback for handling file uploads.
            Should accept an UploadFile parameter.

            Example::

                async def upload_handler(self, file: UploadFile) -> None:
                    content = await file.read()
                    # process content
    """

    feedback_config: FeedbackConfig = FeedbackConfig()
    user_settings: UserSettings = UserSettings()
    conversation_history: bool = False
    show_usage: bool = False
    ui_customization: UICustomization | None = None
    history_persistence: HistoryPersistenceStrategy | None = None
    summary_generator: SummaryGenerator = HeuristicSummaryGenerator()
    upload_handler: Callable[[UploadFile], Any] | None = None

    def __init_subclass__(cls, **kwargs: dict) -> None:
        """Automatically apply the with_chat_metadata decorator to the chat method in subclasses."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "chat"):
            cls.chat = functools.wraps(cls.chat)(with_chat_metadata(cls.chat))  # type: ignore

    @staticmethod
    def create_text_response(text: str) -> TextResponse:
        """Helper method to create a text response."""
        return TextResponse(content=TextContent(text=text))

    @staticmethod
    def create_reference(
        title: str,
        content: str,
        url: str | None = None,
    ) -> ReferenceResponse:
        """Helper method to create a reference response."""
        return ReferenceResponse(content=Reference(title=title, content=content, url=url))

    @staticmethod
    def create_state_update(state: dict[str, Any]) -> StateUpdateResponse:
        """Helper method to create a state update response with signature."""
        signature = ChatInterface._sign_state(state)
        return StateUpdateResponse(content=StateUpdate(state=state, signature=signature))

    @staticmethod
    def create_live_update(
        update_id: str, type: LiveUpdateType, label: str, description: str | None = None
    ) -> LiveUpdateResponse:
        """Helper method to create a live update response."""
        return LiveUpdateResponse(
            content=LiveUpdate(
                update_id=update_id, type=type, content=LiveUpdateContent(label=label, description=description)
            )
        )

    @staticmethod
    def create_followup_messages(messages: list[str]) -> FollowupMessagesResponse:
        """Helper method to create a live update response."""
        return FollowupMessagesResponse(content=FollowupMessagesContent(messages=messages))

    @staticmethod
    def create_image_response(image_id: str, image_url: str) -> ImageResponse:
        """Helper method to create an image response."""
        return ImageResponse(content=Image(id=image_id, url=image_url))

    @staticmethod
    def create_clear_message_response() -> ClearMessageResponse:
        """Helper method to create an clear message response."""
        return ClearMessageResponse(content=ClearMessageContent())

    @staticmethod
    def create_usage_response(usage: Usage) -> UsageResponse:
        return UsageResponse(
            content=UsageContent(
                usage={model: MessageUsage.from_usage(usage) for model, usage in usage.model_breakdown.items()}
            )
        )

    @staticmethod
    def create_todo_item_response(task: Task) -> TodoItemResponse:
        return TodoItemResponse(content=TodoItemContent(task=task))

    @staticmethod
    def _sign_state(state: dict[str, Any]) -> str:
        """
        Sign the state with HMAC to ensure integrity.

        Args:
            state: The state dictionary to sign

        Returns:
            Base64-encoded signature
        """
        state_json = json.dumps(state, sort_keys=True)
        secret_key = get_secret_key()
        signature = hmac.new(secret_key.encode(), state_json.encode(), digestmod="sha256").digest()
        return base64.b64encode(signature).decode()

    @staticmethod
    def verify_state(state: dict[str, Any], signature: str) -> bool:
        """
        Verify that a state and signature match.

        Args:
            state: The state dictionary to verify
            signature: The signature to check against

        Returns:
            True if the signature is valid, False otherwise
        """
        expected_signature = ChatInterface._sign_state(state)
        is_valid = hmac.compare_digest(expected_signature, signature)

        # Track state verification
        record_metric(
            ChatCounterMetric.CHAT_STATE_VERIFICATION_COUNT,
            1,
            metric_type=MetricType.COUNTER,
            verification_result="success" if is_valid else "failure",
        )

        return is_valid

    async def setup(self) -> None:  # noqa: B027
        """
        Set up the chat interface.

        This method is called after the chat interface is initialized and before the chat method is called.
        It is used to set up the chat interface, such as loading the model or initializing the vector store.

        This method is optional and can be overridden by subclasses.
        """
        pass

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponseUnion, None]:
        """
        Process a chat message and yield responses asynchronously.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context containing conversation metadata and state.
                    Will be automatically populated with message_id and conversation_id.

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Reference documents used to generate the response
            - State updates when the conversation state changes

        Example:
            ```python
            chat = MyChatImplementation()
            async for response in chat.chat("What is Python?"):
                if isinstance(response, TextResponse):
                    print(f"Text: {response.content}")
                elif isinstance(response, ReferenceResponse):
                    print(f"Reference: {response.content.title}")
                elif isinstance(response, StateUpdateResponse):
                    if verify_state(response.content.state, response.content.signature):
                        # Update client state
                        pass
            ```
        """
        yield TextResponse(content=TextContent(text="Ragbits cannot respond - please implement chat method!"))
        raise NotImplementedError("Chat implementations must implement chat method")

    async def save_feedback(
        self,
        message_id: str,
        feedback: FeedbackType,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Save feedback about a chat message.

        Args:
            message_id: The ID of the message
            feedback: The type of feedback
            payload: The payload of the feedback
        """
        # Track feedback submission
        record_metric(
            ChatCounterMetric.CHAT_FEEDBACK_COUNT,
            1,
            metric_type=MetricType.COUNTER,
            interface_class=self.__class__.__name__,
            feedback_type=feedback,
        )

        logger.info(f"[{self.__class__.__name__}] Saving {feedback} for message {message_id} with payload {payload}")

    async def generate_conversation_summary(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Handles conversation summary generation using the configured summary_generator."""
        return await self.summary_generator.generate(message, history, context)
