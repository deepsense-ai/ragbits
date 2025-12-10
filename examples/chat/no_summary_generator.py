"""
Ragbits Chat Example: No Summary Generator

This example demonstrates how to use the `ChatInterface` without a SummaryGenerator.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///

from collections.abc import AsyncGenerator

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt.base import ChatFormat


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    conversation_history = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Example implementation of the ChatInterface.
        """
        streaming_result = self.llm.generate_streaming([*history, {"role": "user", "content": message}])
        async for chunk in streaming_result:
            yield self.create_text_response(chunk)
