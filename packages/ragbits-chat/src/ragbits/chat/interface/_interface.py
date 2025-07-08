import base64
import functools
import hmac
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from typing import Any, Literal

from ragbits.chat.interface.ui_customization import UICustomization
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType
from ragbits.core.prompt.base import ChatFormat
from ragbits.core.utils import get_secret_key

from ..metrics import ChatCounterMetric, ChatHistogramMetric
from ..persistence import HistoryPersistenceStrategy
from .forms import FeedbackConfig, UserSettings
from .types import (
    ChatContext,
    ChatResponse,
    ChatResponseType,
    LiveUpdate,
    LiveUpdateContent,
    LiveUpdateType,
    Reference,
    StateUpdate,
)

logger = logging.getLogger(__name__)


def with_chat_metadata(
    func: Callable[["ChatInterface", str, ChatFormat | None, ChatContext | None], AsyncGenerator[ChatResponse, None]],
) -> Callable[["ChatInterface", str, ChatFormat | None, ChatContext | None], AsyncGenerator[ChatResponse, None]]:
    """
    Decorator that adds message and conversation metadata to the chat method and handles history persistence.
    Generates message_id and conversation_id (if first message) and stores them in context.
    Also handles history persistence if configured.
    """

    @functools.wraps(func)
    async def wrapper(
        self: "ChatInterface", message: str, history: ChatFormat | None = None, context: ChatContext | None = None
    ) -> AsyncGenerator[ChatResponse, None]:
        start_time = time.time()

        # Initialize context if None
        if context is None:
            context = ChatContext()

        # Track history length
        history_length = len(history) if history else 0
        record_metric(
            ChatHistogramMetric.CHAT_HISTORY_LENGTH,
            history_length,
            metric_type=MetricType.HISTOGRAM,
            interface_class=self.__class__.__name__,
        )

        # Generate message_id if not present
        if not context.message_id:
            context.message_id = str(uuid.uuid4())
            yield ChatResponse(type=ChatResponseType.MESSAGE_ID, content=context.message_id)

        # Generate conversation_id if this is the first message
        is_new_conversation = False
        if not context.conversation_id and (not history or len(history) == 0):
            context.conversation_id = str(uuid.uuid4())
            is_new_conversation = True
            yield ChatResponse(type=ChatResponseType.CONVERSATION_ID, content=context.conversation_id)

            # Track new conversation
            record_metric(
                ChatCounterMetric.CHAT_CONVERSATION_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                interface_class=self.__class__.__name__,
            )

        responses = []
        main_response = ""
        extra_responses = []
        timestamp = time.time()
        response_token_count = 0.0
        first_token_time = None

        try:
            async for response in func(self, message, history, context):
                responses.append(response)
                if response.type == ChatResponseType.TEXT and isinstance(response.content, str):
                    # Record time to first token on the first TEXT response
                    if first_token_time is None and response.content:
                        first_token_time = time.time() - start_time
                        record_metric(
                            ChatHistogramMetric.CHAT_TIME_TO_FIRST_TOKEN,
                            first_token_time,
                            metric_type=MetricType.HISTOGRAM,
                            interface_class=self.__class__.__name__,
                            is_new_conversation=str(is_new_conversation),
                            history_length=str(history_length),
                        )

                    main_response = main_response + response.content
                    # Rough token estimation (words * 1.3 for subword tokens)
                    response_token_count += len(response.content.split()) * 1.3
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
    """

    feedback_config: FeedbackConfig = FeedbackConfig()
    user_settings: UserSettings = UserSettings()
    ui_customization: UICustomization | None = None
    history_persistence: HistoryPersistenceStrategy | None = None

    def __init_subclass__(cls, **kwargs: dict) -> None:
        """Automatically apply the with_chat_metadata decorator to the chat method in subclasses."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "chat"):
            cls.chat = functools.wraps(cls.chat)(with_chat_metadata(cls.chat))  # type: ignore

    @staticmethod
    def create_text_response(text: str) -> ChatResponse:
        """Helper method to create a text response."""
        return ChatResponse(type=ChatResponseType.TEXT, content=text)

    @staticmethod
    def create_reference(
        title: str,
        content: str,
        url: str | None = None,
    ) -> ChatResponse:
        """Helper method to create a reference response."""
        return ChatResponse(
            type=ChatResponseType.REFERENCE,
            content=Reference(title=title, content=content, url=url),
        )

    @staticmethod
    def create_state_update(state: dict[str, Any]) -> ChatResponse:
        """Helper method to create a state update response with signature."""
        signature = ChatInterface._sign_state(state)
        return ChatResponse(
            type=ChatResponseType.STATE_UPDATE,
            content=StateUpdate(state=state, signature=signature),
        )

    @staticmethod
    def create_live_update(
        update_id: str, type: LiveUpdateType, label: str, description: str | None = None
    ) -> ChatResponse:
        """Helper method to create a live update response."""
        return ChatResponse(
            type=ChatResponseType.LIVE_UPDATE,
            content=LiveUpdate(
                update_id=update_id, type=type, content=LiveUpdateContent(label=label, description=description)
            ),
        )

    @staticmethod
    def create_followup_messages(messages: list[str]) -> ChatResponse:
        """Helper method to create a live update response."""
        return ChatResponse(type=ChatResponseType.FOLLOWUP_MESSAGES, content=messages)

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
        history: ChatFormat | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
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
                if text := response.as_text():
                    print(f"Text: {text}")
                elif ref := response.as_reference():
                    print(f"Reference: {ref.title}")
                elif state := response.as_state_update():
                    if verify_state(state.state, state.signature):
                        # Update client state
                        pass
            ```
        """
        yield ChatResponse(type=ChatResponseType.TEXT, content="Ragbits cannot respond - please implement chat method!")
        raise NotImplementedError("Chat implementations must implement chat method")

    async def save_feedback(
        self,
        message_id: str,
        feedback: Literal["like", "dislike"],
        payload: dict,
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
