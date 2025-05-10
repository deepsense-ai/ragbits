import functools
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from ragbits.core.prompt.base import ChatFormat

if TYPE_CHECKING:
    from ragbits.chat.interface import ChatInterface

from ragbits.chat.interface.types import ChatResponse, ChatResponseType

T = TypeVar("T")


def with_history_persistence(
    func: Callable[..., Awaitable[AsyncGenerator[ChatResponse, None]]],
) -> Callable[..., Awaitable[AsyncGenerator[ChatResponse, None]]]:
    """
    Decorator that adds history persistence functionality to the chat method.
    Only applies persistence if history_persistence is configured on the instance.
    """

    @functools.wraps(func)
    async def wrapper(
        self: "ChatInterface", message: str, history: ChatFormat | None = None, context: dict | None = None
    ) -> AsyncGenerator[ChatResponse, None]:
        if not self.history_persistence:
            async for response in func(self, message, history, context):
                yield response
            return

        responses = []
        main_response = ""
        extra_responses = []
        timestamp = time.time()

        try:
            async for response in func(self, message, history, context):
                responses.append(response)
                if response.type == ChatResponseType.TEXT:
                    main_response = main_response + response.content
                else:
                    extra_responses.append(response)
                yield response
        finally:
            await self.history_persistence.save_interaction(
                message=message,
                response=main_response,
                extra_responses=extra_responses,
                context=context,
                timestamp=timestamp,
            )

    return wrapper
