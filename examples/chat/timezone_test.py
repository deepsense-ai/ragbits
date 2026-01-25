"""Simple chat to test timezone functionality."""

from collections.abc import AsyncGenerator

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.prompt import ChatFormat


class TimezoneTestChat(ChatInterface):
    """Chat that displays the received timezone."""

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        timezone = context.timezone
        yield self.create_text_response(f"Your browser timezone: **{timezone}**")
