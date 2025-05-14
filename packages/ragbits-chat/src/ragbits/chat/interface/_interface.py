import base64
import functools
import hmac
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, Literal, TypeVar

from ragbits.core.prompt.base import ChatFormat
from ragbits.core.utils import get_secret_key

from ..persistence import HistoryPersistenceStrategy
from .forms import FeedbackConfig
from .types import ChatContext, ChatResponse, ChatResponseType, Reference, StateUpdate

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_chat_metadata(
    func: Callable[..., Awaitable[AsyncGenerator[ChatResponse, None]]],
) -> Callable[..., Awaitable[AsyncGenerator[ChatResponse, None]]]:
    """
    Decorator that adds message and conversation metadata to the chat method and handles history persistence.
    Generates message_id and conversation_id (if first message) and stores them in context.
    Also handles history persistence if configured.
    """

    @functools.wraps(func)
    async def wrapper(
        self: "ChatInterface", message: str, history: ChatFormat | None = None, context: dict[str, Any] | None = None
    ) -> AsyncGenerator[ChatResponse, None]:
        # Initialize context if None
        if context is None:
            context = {}

        # Convert context to ChatContext
        chat_context = ChatContext(**context)

        # Generate message_id if not present
        if not chat_context.message_id:
            chat_context.message_id = str(uuid.uuid4())
            yield ChatResponse(type=ChatResponseType.MESSAGE_ID, content=chat_context.message_id)

        # Generate conversation_id if this is the first message
        if not chat_context.conversation_id and (not history or len(history) == 0):
            chat_context.conversation_id = str(uuid.uuid4())
            yield ChatResponse(type=ChatResponseType.CONVERSATION_ID, content=chat_context.conversation_id)

        # Convert back to dict for the chat method
        context_dict = chat_context.model_dump()

        responses = []
        main_response = ""
        extra_responses = []
        timestamp = time.time()

        try:
            async for response in func(self, message, history, context_dict):
                responses.append(response)
                if response.type == ChatResponseType.TEXT:
                    main_response = main_response + response.content
                else:
                    extra_responses.append(response)
                yield response
        finally:
            if self.history_persistence:
                await self.history_persistence.save_interaction(
                    message=message,
                    response=main_response,
                    extra_responses=extra_responses,
                    context=context_dict,
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
    history_persistence: HistoryPersistenceStrategy | None = None

    def __init_subclass__(cls, **kwargs):
        """Automatically apply the with_chat_metadata decorator to the chat method in subclasses."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "chat"):
            cls.chat = with_chat_metadata(cls.chat)

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
        return hmac.compare_digest(expected_signature, signature)

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: ChatFormat | None = None,
        context: dict[str, Any] | None = None,
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
        logger.info(f"[{self.__class__.__name__}] Saving {feedback} for message {message_id} with payload {payload}")
