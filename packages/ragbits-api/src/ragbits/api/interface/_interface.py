from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from .types import ChatResponse, ChatResponseType, Message, Reference


class ChatInterface(ABC):
    """
    Base interface for chat implementations.

    This interface defines the core functionality required for a chat service
    that can return various types of responses such as:

    * Text: Regular text responses streamed chunk by chunk
    * References: Source documents used to generate the answer
    """

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

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Process a chat message and yield responses asynchronously.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Reference documents used to generate the response

        Example:
            ```python
            chat = MyChatImplementation()
            async for response in chat.chat("What is Python?"):
                if text := response.as_text():
                    print(f"Text: {text}")
                elif ref := response.as_reference():
                    print(f"Reference: {ref.title}")
            ```
        """
        raise NotImplementedError("Chat implementations must implement this method")
