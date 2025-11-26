from collections.abc import AsyncGenerator
from logging import getLogger

from ragbits.agents import Agent
from ragbits.agents.tool import ToolCallResult
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.llms.base import Usage
from ragbits.core.prompt import ChatFormat

from . import HotelPrompt, HotelPromptInput
from . import tools as hotel_fixtures

logger = getLogger(__name__)


class HotelChat(ChatInterface):
    """A simple example implementation of the ChatInterface for hotel booking agent."""

    def __init__(self, model_name: str, api_key: str) -> None:
        self.llm = LiteLLM(model_name=model_name, use_structured_output=True, api_key=api_key)
        self.agent = Agent(
            llm=self.llm,
            prompt=HotelPrompt,
            tools=[
                hotel_fixtures.list_cities,
                hotel_fixtures.list_hotels,
                hotel_fixtures.get_hotel_details,
                hotel_fixtures.search_available_rooms,
                hotel_fixtures.create_reservation,
                hotel_fixtures.list_reservations,
                hotel_fixtures.get_reservation,
                hotel_fixtures.cancel_reservation,
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
                yield self.create_text_response(response)
            if isinstance(response, ToolCallResult):
                yield response

        if stream.usage and isinstance(stream.usage, Usage):
            yield stream.usage

    async def generate_conversation_summary(self, message: str, history: ChatFormat, context: ChatContext) -> str:
        """Delegate to the configured summary generator."""
        if not self.summary_generator:
            return "Dummy summary: No summary generator configured."

        return await self.summary_generator.generate(message, history, context)
