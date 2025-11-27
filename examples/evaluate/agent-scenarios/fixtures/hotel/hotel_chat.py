import inspect
from collections.abc import AsyncGenerator, Callable
from functools import wraps
from logging import getLogger

from ragbits.agents import Agent
from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat

from .prompt import HotelPrompt, HotelPromptInput
from .tools import (
    cancel_reservation,
    create_reservation,
    get_hotel_details,
    get_reservation,
    list_cities,
    list_hotels,
    list_reservations,
    search_available_rooms,
)

logger = getLogger(__name__)


class HotelChat(ChatInterface):
    """A simple example implementation of the ChatInterface for hotel booking agent."""

    def __init__(self, model_name: str, api_key: str, process_id: int | str | None = None) -> None:
        self.llm = LiteLLM(model_name=model_name, use_structured_output=True, api_key=api_key)
        self.agent = Agent(
            llm=self.llm,
            prompt=HotelPrompt,
            tools=[
                self._preconfigure_tool(list_cities, process_id),
                self._preconfigure_tool(list_hotels, process_id),
                self._preconfigure_tool(get_hotel_details, process_id),
                self._preconfigure_tool(search_available_rooms, process_id),
                self._preconfigure_tool(create_reservation, process_id),
                self._preconfigure_tool(list_reservations, process_id),
                self._preconfigure_tool(get_reservation, process_id),
                self._preconfigure_tool(cancel_reservation, process_id),
            ],
        )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Example implementation of the ChatInterface.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - ToolCallResult objects for tool calls
            - Usage object for token usage
        """
        stream = self.agent.run_streaming(HotelPromptInput(input=message))

        async for response in stream:
            if isinstance(response, str):
                yield response
            if isinstance(response, ToolCallResult):
                yield response

        if stream.usage and isinstance(stream.usage, Usage):
            yield stream.usage

    @staticmethod
    def _preconfigure_tool(func: Callable[..., object], process_id: int | str | None) -> Callable[..., object]:
        """Return a callable that calls `func(process_id, *args, **kwargs)` and
        preserves original function metadata (like __name__ and __doc__).

        If process_id is None we return the original function unchanged.
        Supports both sync and async functions.
        """
        if process_id is None:
            return func

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _wrapped(*args, **kwargs) -> object:
                return await func(process_id, *args, **kwargs)

            return _wrapped

        @wraps(func)
        def _wrapped(*args, **kwargs) -> object:
            return func(process_id, *args, **kwargs)

        return _wrapped

    async def generate_conversation_summary(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Delegate to the configured summary generator."""
        if not self.summary_generator:
            return "Dummy summary: No summary generator configured."

        return await self.summary_generator.generate(message, history, context)
