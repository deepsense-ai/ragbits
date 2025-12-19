from collections.abc import AsyncGenerator
from logging import getLogger
from pathlib import Path

from ragbits.agents import Agent
from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat

from .prompt import HotelPrompt, HotelPromptInput
from .service import HotelService
from .tools import (
    cancel_reservation,
    create_reservation,
    get_hotel_details,
    get_reservation,
    list_cities,
    list_hotels,
    list_reservations,
    search_available_rooms,
    set_service,
)

logger = getLogger(__name__)


class HotelChat(ChatInterface):
    """A simple example implementation of the ChatInterface for hotel booking agent.

    This implementation uses an in-memory SQLite database populated from a JSON
    configuration file. No external HTTP API server is required.
    """

    def __init__(self, model_name: str, api_key: str, config_path: Path | str | None = None) -> None:
        """Initialize the hotel chat agent.

        Args:
            model_name: The name of the LLM model to use.
            api_key: The API key for the LLM provider.
            config_path: Optional path to the hotel configuration JSON file.
                        If None, uses the default config path.
        """
        # Initialize the in-memory hotel service
        self._service = HotelService(config_path)
        set_service(self._service)

        self.llm = LiteLLM(model_name=model_name, use_structured_output=True, api_key=api_key)
        self.agent = Agent(
            llm=self.llm,
            prompt=HotelPrompt,
            tools=[
                list_cities,
                list_hotels,
                get_hotel_details,
                search_available_rooms,
                create_reservation,
                list_reservations,
                get_reservation,
                cancel_reservation,
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

    async def generate_conversation_summary(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Delegate to the configured summary generator."""
        return await self.summary_generator.generate(message, history, context)
